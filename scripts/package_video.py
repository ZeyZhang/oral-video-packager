# -*- coding: utf-8 -*-
"""口播视频包装引擎（配置驱动）。

用法:
  python package_video.py --config config.json
  python package_video.py --config config.json --workdir DIR --output OUT.mp4
  python package_video.py --config config.json --reuse-frames

输入: 一段真人出镜口播视频 + 一个 JSON 配置（字幕、人物条、知识动画、免责、片尾）
输出: 包装成片、可编辑字幕 SRT/ASS、审签清单、质检拼板
"""
import argparse
import glob
import json
import math
import os
import re
import shutil
import subprocess
import sys
from fractions import Fraction

from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageChops

DW, DH = 720, 1280  # 设计画布（9:16 竖屏），实际输出会缩放到源视频尺寸


# ---------------- 基础工具 ----------------
def run(cmd, cwd=None):
    r = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)
    if r.returncode != 0:
        sys.stderr.write(" ".join(cmd) + "\n" + r.stderr[-3000:] + "\n")
        raise SystemExit("ffmpeg/ffprobe failed (exit %d)" % r.returncode)
    return r.stdout


def probe(path):
    data = json.loads(run([
        "ffprobe", "-v", "error", "-show_entries",
        "stream=codec_type,width,height,r_frame_rate:format=duration",
        "-of", "json", path]))
    v = next(s for s in data["streams"] if s["codec_type"] == "video")
    fps = float(Fraction(v["r_frame_rate"]))
    return {"w": int(v["width"]), "h": int(v["height"]),
            "fps": fps, "dur": float(data["format"]["duration"])}


def find_font(bold=True):
    names = (["msyhbd.ttc", "simhei.ttf", "NotoSansCJK-Bold.ttc"]
             if bold else ["msyh.ttc", "simhei.ttf", "NotoSansCJK-Regular.ttc"])
    roots = ["C:/Windows/Fonts/", "/System/Library/Fonts/", "/usr/share/fonts/"]
    for r in roots:
        for n in names:
            p = os.path.join(r, n)
            if os.path.exists(p):
                return p
    return None


_FONT_CACHE = {}


def font(size, bold=True):
    key = (int(size), bold)
    if key not in _FONT_CACHE:
        p = find_font(bold)
        _FONT_CACHE[key] = ImageFont.truetype(p, int(size)) if p else ImageFont.load_default()
    return _FONT_CACHE[key]


def ct(d, xy, text, f, fill, shadow=True):
    x, y = xy
    if shadow:
        d.text((x + 2, y + 3), text, font=f, fill=(0, 0, 0), anchor="mm")
    d.text((x, y), text, font=f, fill=fill, anchor="mm")


def lt(d, xy, text, f, fill, shadow=True):
    x, y = xy
    if shadow:
        d.text((x + 2, y + 3), text, font=f, fill=(0, 0, 0))
    d.text((x, y), text, font=f, fill=fill)


def ease(p):
    return max(0.0, min(1.0, p))


def smooth(p):
    """easeOutCubic：替掉线性进度，让默认 Pillow 后端的动效不生硬。"""
    return 1.0 - (1.0 - ease(p)) ** 3


def fade(t, a, b, d=0.3):
    return smooth((t - a) / d) * smooth((b - t) / d)


def bgr(rgb):
    r, g, b = [int(x) for x in rgb]
    return "%02X%02X%02X" % (b, g, r)


# ---------------- 样式 ----------------
class Style:
    def __init__(self, cfg):
        s = cfg.get("style", {})
        self.gold = tuple(s.get("gold", [226, 178, 38]))
        self.gold_light = tuple(s.get("gold_light", [245, 210, 96]))
        self.white = (255, 255, 255)
        self.soft = (226, 234, 240)
        self.sub_size = int(s.get("subtitle_size", 40))
        self.sub_margin = int(s.get("subtitle_margin_v", 176))
        self.shift_pos = s.get("shifted_pos", [500, 1080])
        self.shift_size = int(s.get("shifted_size", 32))
        self.shift_on = bool(s.get("shift_subtitles_in_segments", True))
        self.pip = s.get("pip", [20, 770, 300, 435])
        self.blur = float(s.get("background_blur", 22))
        self.dark = float(s.get("background_darkness", 0.52))
        self.gold_hex = bgr(self.gold)


# ---------------- 静态叠层 ----------------
def static_base(cfg, st):
    im = Image.new("RGBA", (DW, DH), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    lines = cfg.get("disclaimer", [])[:4]
    if lines:
        line_h = 24
        block_h = len(lines) * line_h + 12
        top = DH - block_h
        d.rectangle((0, top, DW, DH), fill=(0, 0, 0, 105))
        f = font(19, False)
        for i, s in enumerate(lines):
            w = d.textlength(s, font=f)
            d.text(((DW - w) / 2, top + 6 + i * line_h), s,
                   font=f, fill=(238, 242, 246, 225))
    return im


def draw_title(im, cfg, st, alpha):
    layer = Image.new("RGBA", (DW, DH), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    t = cfg.get("title_card", {})
    ct(d, (DW / 2, 205), t.get("text", ""), font(48), st.gold)
    if t.get("sub"):
        ct(d, (DW / 2, 292), t["sub"], font(30), st.white)
    if alpha < 1:
        layer.putalpha(layer.getchannel("A").point(lambda v: int(v * alpha)))
    im.alpha_composite(layer)


def vtext(d, x, y0, text, f, fill, line_h, shadow=True):
    """竖排逐字绘制，x 为该列中心。"""
    for i, ch in enumerate(text):
        ct(d, (x, y0 + i * line_h), ch, f, fill, shadow=shadow)


def gradient_rect(im, box, top_rgb, bottom_rgb):
    x0, y0, x1, y1 = box
    d = ImageDraw.Draw(im)
    h = max(1, y1 - y0)
    for y in range(y0, y1):
        k = (y - y0) / h
        rgb = tuple(int(top_rgb[i] + (bottom_rgb[i] - top_rgb[i]) * k) for i in range(3))
        d.line((x0, y, x1, y), fill=rgb + (255,))


def fit_vfont(text, max_h, base, min_size, ratio=1.06):
    """按竖排总高度自动缩字号，避免用户输入的机构名/职称溢出。"""
    for size in range(base, min_size - 1, -1):
        if len(text) * size * ratio <= max_h:
            return font(size), size * ratio
    return font(min_size), min_size * ratio


def in_ranges(t, spec):
    """show 支持 [a,b] 单区间或 [[a,b],[c,d]] 多区间。"""
    if not spec:
        return None
    if len(spec) == 2 and all(isinstance(v, (int, float)) for v in spec):
        spec = [spec]
    for pair in spec:
        if pair[0] <= t < pair[1]:
            return pair
    return None


PROFILES = {
    "medical": {
        "label": "医学科普",
        "disclaimer": [
            "医学科普 · 仅供参考 · 不作为诊疗依据，具体请遵医嘱",
            "如有不适请及时到正规医院就诊；本片示意图为图形动画，非真实医学影像",
        ],
        "checks": [
            "医学结论与口播原意一致，字幕仅删口癖、未新增或改写诊疗建议",
            "由具备资质的医务人员完成内容审签并留档",
            "人物条的姓名、职称、机构与执业信息一致且可核实",
            "发布账号已完成平台医疗科普资质认证",
            "AI 生成合成内容标识由后期/发布环节添加；免责声明与引用来源标注齐全",
            "无疗效承诺、绝对化用语、虚构病例、药品器械导购或购物链接",
        ],
        "kinds": ["timeline", "scan", "resection", "quote", "points"],
    },
    "product": {
        "label": "产品介绍",
        "disclaimer": [
            "产品介绍 · 参数、功能与效果以官方说明及实物为准",
            "价格、活动与库存以页面实时信息为准；示意图为图形动画，非实拍演示",
        ],
        "checks": [
            "产品名、型号、参数与官方资料一致，未夸大或虚构功能",
            "无绝对化用语；比较性表述有可核实依据，未贬低同行",
            "价格、促销、赠品与库存信息标注有效期与适用条件",
            "引用的检测报告、认证、销量数据可溯源，未虚构案例或用户评价",
            "人物肖像、品牌标识、音乐与字体均已获授权",
            "AI 生成合成内容标识由后期/发布环节添加；免责声明与来源标注齐全",
        ],
        "kinds": ["features", "compare", "stats", "steps", "quote", "points"],
    },
    "ecommerce": {
        "label": "电商产品分析",
        "disclaimer": [
            "本视频为数据分析与观点分享，不构成投资或经营建议",
            "数据来源与统计口径以原始平台为准；结论随市场变化可能失效",
        ],
        "checks": [
            "数据来源、时间区间与统计口径已在画面或说明中标注",
            "竞品信息来自公开可核实渠道，未作不当比较或贬低同行",
            "转化率、GMV、销量等数字未夸大，预测值明确标注为预测",
            "价格与排名信息标注采集时间，避免时效误导",
            "无刷单、虚假宣传、诱导交易或规避平台规则的内容",
            "AI 生成合成内容标识由后期/发布环节添加；免责声明与来源标注齐全",
        ],
        "kinds": ["stats", "funnel", "compare", "matrix", "quote", "points"],
    },
    "general": {
        "label": "通用口播",
        "disclaimer": [],
        "checks": [
            "口播内容与字幕一致，未新增事实或改写原意",
            "引用的数据、案例与第三方材料可溯源并已获授权",
            "无绝对化用语、误导性表述或未经验证的承诺",
            "人物信息、肖像、音乐与字体授权齐全",
            "AI 生成合成内容标识由后期/发布环节添加",
        ],
        "kinds": ["stats", "features", "steps", "compare", "quote", "points"],
    },
}

GENERIC_KINDS = ("features", "compare", "stats", "funnel", "steps", "matrix")

CARD = {"x0": 93, "y0": 140, "panel_w": 63, "panel_h": 340,
        "name_w": 54, "name_h": 135}


def draw_person(im, cfg, st, alpha):
    """参考成片式竖排名片：蓝渐变姓名块 + 浅蓝白底双列机构/科室 + 菱形职称。"""
    p = cfg.get("person", {})
    name = p.get("name", "") or ""
    org = p.get("title", "") or ""
    dept = p.get("department") or p.get("subtitle", "") or ""
    rank = p.get("rank", "") or ""
    if not (name or org or dept or rank):
        return
    c = CARD
    x0, y0 = c["x0"], c["y0"]
    px1 = x0 + c["panel_w"]
    nx1 = px1 + c["name_w"]
    py1 = y0 + c["panel_h"]
    ny1 = y0 + c["name_h"]
    layer = Image.new("RGBA", (DW, DH), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    d.rectangle((x0, y0, px1, py1), fill=(238, 247, 255, 236))
    d.line((x0, y0, x0, py1), fill=(150, 205, 245, 255), width=2)
    grad = Image.new("RGBA", (DW, DH), (0, 0, 0, 0))
    gradient_rect(grad, (px1, y0, nx1, ny1), (28, 92, 196), (52, 190, 238))
    layer.alpha_composite(grad)
    d = ImageDraw.Draw(layer)
    if name:
        f, lh = fit_vfont(name, c["name_h"] - 14, 40, 22)
        start = y0 + (c["name_h"] - len(name) * lh) / 2 + lh / 2
        vtext(d, px1 + c["name_w"] / 2, start, name, f, (255, 255, 255, 255), lh)
    if org:
        f, lh = fit_vfont(org, c["panel_h"] - 46, 22, 15)
        vtext(d, px1 - 17, y0 + 34, org, f, (26, 96, 190, 255), lh, shadow=False)
    if dept:
        f, lh = fit_vfont(dept, c["panel_h"] - 46, 22, 15)
        vtext(d, x0 + 17, y0 + 78, dept, f, (26, 96, 190, 255), lh, shadow=False)
    if rank:
        cx = px1 + c["name_w"] / 2
        cy = ny1 + 18
        f, lh = fit_vfont(rank, 160, 22, 15, 1.08)
        d.rectangle((px1, ny1, nx1, cy + 34 + len(rank) * lh),
                    fill=(12, 30, 52, 165))
        d.polygon([(cx, cy - 13), (cx + 11, cy), (cx, cy + 13), (cx - 11, cy)],
                  outline=(255, 255, 255, 235), width=2)
        vtext(d, cx, cy + 36, rank, f, (255, 255, 255, 255), lh)
    if alpha < 1:
        layer.putalpha(layer.getchannel("A").point(lambda v: int(v * alpha)))
    im.alpha_composite(layer)


# ---------------- 知识动画 ----------------
class Animator:
    def __init__(self, cfg, st, bg_path, work):
        self.cfg, self.st, self.work = cfg, st, work
        src = Image.open(bg_path).convert("RGB").resize((DW, DH))
        src = src.filter(ImageFilter.GaussianBlur(st.blur))
        dark = Image.new("RGB", (DW, DH), (16, 24, 36))
        self.bg = Image.blend(src, dark, st.dark).convert("RGBA")
        self.pip = st.pip
        self.win_mask = None
        if self.pip:
            x, y, w, h = self.pip
            m = Image.new("L", (DW, DH), 255)
            ImageDraw.Draw(m).ellipse((x, y, x + w, y + h), fill=0)
            self.win_mask = m

    def border(self, d):
        if not self.pip:
            return
        x, y, w, h = self.pip
        cx, cy, rx, ry = x + w / 2, y + h / 2, w / 2, h / 2
        for deg in range(0, 360, 4):
            if deg % 16 > 9:
                continue
            r = math.radians(deg)
            px, py = cx + rx * math.cos(r), cy + ry * math.sin(r)
            d.ellipse((px - 2.2, py - 2.2, px + 2.2, py + 2.2),
                      fill=(255, 255, 255, 235))

    def background_frame(self, alpha):
        """只生成模糊背景 + 小真人窗口（挖空 + 虚线边框），动画内容由外部帧提供。"""
        im = self.bg.copy()
        d = ImageDraw.Draw(im)
        if self.win_mask is not None:
            im.putalpha(ImageChops.multiply(im.getchannel("A"), self.win_mask))
            d = ImageDraw.Draw(im)
            self.border(d)
        if alpha < 1:
            im.putalpha(im.getchannel("A").point(lambda v: int(v * alpha)))
        return im

    def frame(self, seg, p, alpha):
        st = self.st
        im = self.bg.copy()
        d = ImageDraw.Draw(im)
        p = smooth(p)
        kind = seg.get("kind", "points")
        if seg.get("title"):
            ct(d, (DW / 2, 158), seg["title"], font(52), st.gold)
        if seg.get("sub"):
            ct(d, (DW / 2, 232), seg["sub"], font(28), st.soft)

        if kind == "timeline":
            self._timeline(d, seg, p, st)
        elif kind == "scan":
            self._scan(d, seg, p, st)
        elif kind == "resection":
            self._resection(d, seg, p, st)
        elif kind == "quote":
            self._quote(im, d, seg, p, st)
        elif kind == "points":
            self._points(d, seg, p, st)
        elif kind in GENERIC_KINDS:
            getattr(self, "_" + kind)(d, seg, p, st)

        if seg.get("quote") and kind != "quote":
            ct(d, (DW / 2, 710 if kind != "points" else 690),
               seg["quote"], font(38), st.gold_light)

        d = ImageDraw.Draw(im)
        if self.win_mask is not None:
            im.putalpha(ImageChops.multiply(im.getchannel("A"), self.win_mask))
            d = ImageDraw.Draw(im)
            self.border(d)
        if alpha < 1:
            im.putalpha(im.getchannel("A").point(lambda v: int(v * alpha)))
        return im

    def _timeline(self, d, seg, p, st):
        d.rounded_rectangle((120, 350, 620, 500), radius=60,
                            fill=(238, 176, 176, 255), outline=(255, 225, 225, 255), width=4)
        d.arc((150, 365, 590, 485), 190, 350, fill=(214, 132, 132, 255), width=5)
        r = 8 + 30 * p
        col = (int(238 - 48 * p), int(176 - 104 * p), int(176 - 104 * p))
        d.ellipse((370 - r, 425 - r, 370 + r, 425 + r), fill=col + (255,),
                  outline=(255, 235, 235, 255), width=3)
        d.line((110, 610, 610, 610), fill=(255, 255, 255, 170), width=4)
        d.line((110, 610, 110 + 500 * p, 610), fill=st.gold + (255,), width=7)
        labels = seg.get("labels", ["0 年", "5 年", "10 年"])
        for i, x in enumerate([110, 360, 610]):
            on = p >= [0.0, 0.5, 0.97][min(i, 2)]
            c = st.gold + (255,) if on else (150, 160, 172, 255)
            d.ellipse((x - 9, 601, x + 9, 619), fill=c)
            if i < len(labels):
                ct(d, (x, 650), labels[i], font(24, False), c, shadow=False)

    def _scan(self, d, seg, p, st):
        cx, cy, rr = 360, 445, 175
        d.ellipse((cx - rr, cy - rr, cx + rr, cy + rr),
                  fill=(214, 128, 132, 255), outline=(255, 226, 226, 255), width=6)
        d.ellipse((cx - rr + 34, cy - rr + 34, cx + rr - 34, cy + rr - 34),
                  fill=(168, 74, 82, 255))
        for i in range(5):
            d.arc((cx - rr + 18 + i * 12, cy - rr + 18 + i * 12,
                   cx + rr - 18 - i * 12, cy + rr - 18 - i * 12),
                  i * 40, i * 40 + 70, fill=(240, 170, 170, 170), width=5)
        sx, sy = cx - 110 + 220 * p, cy - 40 + 30 * math.sin(p * math.pi)
        d.ellipse((sx - 26, sy - 26, sx + 26, sy + 26), fill=(255, 250, 220, 90))
        d.ellipse((sx - 12, sy - 12, sx + 12, sy + 12), fill=(255, 252, 230, 230))
        if p > 0.45 and seg.get("marker"):
            k = ease((p - 0.45) / 0.25)
            d.ellipse((402, 442, 458, 498), fill=(240, 92, 92, int(230 * k)),
                      outline=(255, 255, 255, int(255 * k)), width=3)
            d.line((458, 448, 560, 380), fill=(255, 255, 255, int(220 * k)), width=3)
            lt(d, (500, 344), seg["marker"], font(26), st.gold_light)

    def _resection(self, d, seg, p, st):
        d.rounded_rectangle((110, 330, 640, 380), radius=22, fill=(238, 176, 176, 255))
        pr = 34
        d.ellipse((360 - pr, 330 - pr, 360 + pr, 330 + pr),
                  fill=(214, 88, 88, 255), outline=(255, 220, 220, 255), width=3)
        half = 62 - 34 * ease(p / 0.6)
        d.arc((360 - half, 300 - half * 0.7, 360 + half, 300 + half * 0.7),
              0, 180, fill=(235, 240, 245, 255), width=6)
        d.line((360, 300 - half * 0.7, 360, 270), fill=(235, 240, 245, 255), width=6)
        if p > 0.62:
            d.ellipse((360 - pr, 330 - pr, 360 + pr, 330 + pr), fill=(238, 176, 176, 255))
            d.arc((340, 320, 380, 344), 10, 170, fill=(200, 110, 110, 255), width=4)
        self._points(d, seg, p, st, y0=455)

    def _points(self, d, seg, p, st, y0=430):
        pts = seg.get("points", [])
        for i, s in enumerate(pts[:5]):
            k = ease((p - 0.12 - i * 0.16) / 0.18)
            if k <= 0:
                continue
            y = y0 + i * 82
            d.rounded_rectangle((105, y - 28, 630, y + 30), radius=12,
                                fill=(12, 30, 52, int(205 * k)))
            col = st.gold_light if i == len(pts) - 1 and len(pts) > 1 else st.white
            ct(d, (DW / 2, y), s, font(31), col)

    def _quote(self, im, d, seg, p, st):
        rows = seg.get("lines", [])
        for i, row in enumerate(rows[:5]):
            text = row["text"] if isinstance(row, dict) else row
            color = (row.get("color") if isinstance(row, dict) else "white")
            at = (row.get("at", 0.05 + i * 0.18) if isinstance(row, dict) else 0.05 + i * 0.18)
            k = ease((p - at) / 0.18)
            if k <= 0:
                continue
            layer = Image.new("RGBA", (DW, DH), (0, 0, 0, 0))
            ld = ImageDraw.Draw(layer)
            ct(ld, (DW / 2, 320 + i * 92), text, font(41),
               st.gold_light if color == "gold" else st.white)
            layer.putalpha(layer.getchannel("A").point(lambda v: int(v * k)))
            im.alpha_composite(layer)
        d = ImageDraw.Draw(im)
        if seg.get("footer"):
            ct(d, (DW / 2, 660), seg["footer"], font(34), st.soft)
        return d


# ---------------- 字幕 ----------------

    # ---------------- 通用动画（产品 / 电商 / 通用口播） ----------------
    def _features(self, d, seg, p, st):
        pts = seg.get("points", [])[:6]
        for i, s in enumerate(pts):
            k = ease((p - i * 0.12) / 0.3)
            if k <= 0:
                continue
            col, row = i % 2, i // 2
            x0, y0 = 100 + col * 270, 330 + row * 118
            d.rounded_rectangle((x0, y0, x0 + 250, y0 + 100), radius=12,
                                fill=(12, 30, 52, int(215 * k)))
            d.ellipse((x0 + 16, y0 + 26, x0 + 54, y0 + 64), fill=st.gold + (255,))
            ct(d, (x0 + 35, y0 + 45), str(i + 1), font(20), (12, 30, 52, 255), shadow=False)
            f = font(21)
            lt(d, (x0 + 66, y0 + 26), str(s)[:12], f, st.white)
            if len(str(s)) > 12:
                lt(d, (x0 + 66, y0 + 54), str(s)[12:24], f, st.soft)

    def _compare(self, d, seg, p, st):
        cols = seg.get("columns", [])[:3]
        if not cols:
            return
        n = len(cols)
        gap, base_y, max_h = 30, 620, 280
        w = (500 - gap * (n - 1)) / n
        mx = max([float(c.get("value", 1)) for c in cols] + [1.0])
        for i, c in enumerate(cols):
            x0 = 110 + i * (w + gap)
            x1 = x0 + w
            k = ease((p - i * 0.15) / 0.5)
            h = max_h * float(c.get("value", 0)) / mx * k
            col = st.gold + (255,) if i == 0 else (88, 138, 198, 255)
            d.rounded_rectangle((x0, base_y - h, x1, base_y), radius=10, fill=col)
            ct(d, ((x0 + x1) / 2, base_y - h - 28), str(c.get("label", "")),
               font(25), st.white)
            ct(d, ((x0 + x1) / 2, base_y + 32), str(c.get("note", c.get("value", ""))),
               font(21, False), st.soft, shadow=False)

    def _stats(self, d, seg, p, st):
        bars = seg.get("bars", [])[:6]
        if not bars:
            return
        n = len(bars)
        gap, base_y, max_h = 22, 620, 290
        w = (500 - gap * (n - 1)) / n
        mx = max([float(b.get("value", 1)) for b in bars] + [1.0])
        d.line((100, base_y, 620, base_y), fill=(255, 255, 255, 130), width=3)
        unit = seg.get("unit", "")
        for i, b in enumerate(bars):
            x0 = 100 + i * (w + gap)
            k = ease((p - i * 0.1) / 0.5)
            h = max_h * float(b.get("value", 0)) / mx * k
            col = st.gold + (255,) if i == n - 1 else (70, 120, 185, 255)
            d.rounded_rectangle((x0, base_y - h, x0 + w, base_y), radius=8, fill=col)
            ct(d, (x0 + w / 2, base_y - h - 24),
               "%s%s" % (b.get("value", ""), unit), font(21), st.white)
            ct(d, (x0 + w / 2, base_y + 30), str(b.get("label", "")),
               font(20, False), st.soft, shadow=False)

    def _funnel(self, d, seg, p, st):
        stages = seg.get("stages", [])[:5]
        for i, s in enumerate(stages):
            k = ease((p - i * 0.14) / 0.4)
            if k <= 0:
                continue
            y0 = 318 + i * 78
            half = 232 - i * 36
            col = (int(28 + 18 * i), int(92 + 22 * i), int(196 - 18 * i), 235)
            d.polygon([(360 - half, y0), (360 + half, y0),
                       (360 - half + 36, y0 + 64), (360 + half - 36, y0 + 64)], fill=col)
            ct(d, (360, y0 + 32),
               "%s   %s" % (s.get("label", ""), s.get("value", "")), font(23), st.white)

    def _steps(self, d, seg, p, st):
        pts = seg.get("points", [])[:5]
        if not pts:
            return
        y, x0, x1 = 470, 90, 630
        d.line((x0, y, x1, y), fill=(255, 255, 255, 130), width=4)
        for i, s in enumerate(pts):
            k = ease((p - i * 0.15) / 0.35)
            if k <= 0:
                continue
            x = x0 + (x1 - x0) * i / max(1, len(pts) - 1)
            d.ellipse((x - 15, y - 15, x + 15, y + 15), fill=st.gold + (255,))
            ct(d, (x, y - 56), str(s)[:9], font(21), st.white)
            ct(d, (x, y + 50), "STEP %d" % (i + 1), font(18, False), st.soft, shadow=False)

    def _matrix(self, d, seg, p, st):
        cells = seg.get("cells", [])[:4]
        if not cells:
            return
        axes = seg.get("axes", ["", ""])
        for i, c in enumerate(cells):
            k = ease((p - i * 0.14) / 0.4)
            if k <= 0:
                continue
            col, row = i % 2, i // 2
            x0, y0 = 130 + col * 240, 330 + row * 160
            d.rounded_rectangle((x0, y0, x0 + 220, y0 + 140), radius=12,
                                fill=(12, 30, 52, int(210 * k)),
                                outline=st.gold + (255,), width=2)
            ct(d, (x0 + 110, y0 + 44), str(c.get("label", "")), font(24), st.gold_light)
            ct(d, (x0 + 110, y0 + 92), str(c.get("note", "")), font(20, False), st.soft,
               shadow=False)
        if axes[0]:
            ct(d, (360, 300), str(axes[0]), font(20, False), st.soft, shadow=False)
        if axes[1]:
            ct(d, (80, 490), str(axes[1]), font(20, False), st.soft, shadow=False)


def ass_time(t):
    return "%d:%02d:%05.2f" % (int(t // 3600), int(t // 60) % 60, t % 60)


def srt_time(t):
    return "%02d:%02d:%02d,%03d" % (int(t // 3600), int(t // 60) % 60,
                                    int(t % 60), round((t % 1) * 1000))


def overlaps(a, b, segs):
    return any(a < s["end"] and b > s["start"] for s in segs)


def inline(s, gold_hex):
    out, buf, on = "", "", False
    i = 0
    while i < len(s):
        if s[i:i + 2] == "**":
            out += ("{\\c&HFFFFFF&}" if on else "{\\c&H" + gold_hex + "&}") + buf
            buf, on = "", not on
            i += 2
        else:
            buf += s[i]
            i += 1
    return out + buf + ("{\\c&HFFFFFF&}" if on else "")


def build_subtitles(cfg, st, work, outdir):
    cues, segs = cfg.get("subtitles", []), cfg.get("segments", [])
    head = """[Script Info]
ScriptType: v4.00+
PlayResX: 720
PlayResY: 1280
WrapStyle: 2
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,Microsoft YaHei,%d,&H00FFFFFF,&H00FFFFFF,&H00000000,&H90000000,-1,0,0,0,100,100,0,0,1,3,1,2,40,40,%d,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
""" % (st.sub_size, st.sub_margin)
    lines, srt = [], []
    for i, c in enumerate(cues, 1):
        a, b = float(c["start"]), float(c["end"])
        rows = c["lines"] if isinstance(c["lines"], list) else [c["lines"]]
        txt = "\\N".join(inline(r, st.gold_hex) for r in rows)
        prefix = ""
        if st.shift_on and overlaps(a, b, segs) and st.pip:
            prefix = "{\\pos(%d,%d)\\fs%d}" % (st.shift_pos[0], st.shift_pos[1], st.shift_size)
        lines.append("Dialogue: 0,%s,%s,Default,,0,0,0,,%s%s" %
                     (ass_time(a), ass_time(b), prefix, txt))
        clean = "\n".join(r.replace("**", "") for r in rows)
        srt.append("%d\n%s --> %s\n%s\n\n" % (i, srt_time(a), srt_time(b), clean))
    with open(os.path.join(work, "subtitles.ass"), "w", encoding="utf-8") as f:
        f.write(head + "\n".join(lines) + "\n")
    with open(os.path.join(work, "subtitles.srt"), "w", encoding="utf-8") as f:
        f.writelines(srt)
    if outdir:
        shutil.copyfile(os.path.join(work, "subtitles.srt"),
                        os.path.join(outdir, "subtitles.srt"))
        shutil.copyfile(os.path.join(work, "subtitles.ass"),
                        os.path.join(outdir, "subtitles.ass"))


# ---------------- 片尾与蒙版 ----------------
def build_assets(cfg, st, work, info):
    if st.pip:
        _, _, w, h = st.pip
        m = Image.new("L", (int(w), int(h)), 0)
        ImageDraw.Draw(m).ellipse((0, 0, int(w), int(h)), fill=255)
        m.save(os.path.join(work, "pip_mask.png"))

    e = cfg.get("ending", {})
    im = Image.new("RGB", (DW, DH), (0, 0, 0))
    d = ImageDraw.Draw(im)
    avatar = e.get("avatar")
    if avatar:
        src = avatar if isinstance(avatar, str) else avatar.get("path")
        if isinstance(avatar, dict) and avatar.get("from_reference"):
            ref = avatar.get("video", cfg.get("reference"))
            if ref:
                box = avatar["from_reference"]
                run(["ffmpeg", "-y", "-v", "error", "-ss",
                     str(avatar.get("time", 0)), "-i", ref,
                     "-frames:v", "1", os.path.join(work, "ref_frame.png")])
                src = os.path.join(work, "ref_frame.png")
                img = Image.open(src).convert("RGB")
                x1, y1, x2, y2 = box
                scale = img.width / DW
                img = img.crop(tuple(int(v * scale) for v in (x1, y1, x2, y2)))
                img.save(src)
        if src and os.path.exists(src):
            pic = Image.open(src).convert("RGB").resize((300, 300), Image.LANCZOS)
            mask = Image.new("L", (300, 300), 0)
            ImageDraw.Draw(mask).ellipse((0, 0, 300, 300), fill=255)
            im.paste(Image.new("RGB", (300, 300), (255, 255, 255)), (210, 486), mask)
            im.paste(pic, (210, 486), mask)
    d.ellipse((306, 750, 414, 858), fill=(255, 255, 255))
    d.line((334, 802, 352, 820, 388, 782), fill=(228, 46, 46), width=11, joint="curve")
    ct(d, (DW / 2, 930), e.get("text", "点赞  关注  收藏"), font(58), st.white, shadow=False)
    if e.get("footer"):
        ct(d, (DW / 2, 1180), e["footer"], font(21, False), (170, 176, 184), shadow=False)
    im.save(os.path.join(work, "ending.png"))


def build_background(cfg, work, info):
    bg = os.path.join(work, "bg.png")
    t = float(cfg.get("background_time", info["dur"] * 0.35))
    run(["ffmpeg", "-y", "-v", "error", "-ss", str(t), "-i", cfg["source"],
         "-frames:v", "1", bg])
    return bg


# ---------------- 帧序列 ----------------
def build_frames(cfg, st, work, info, reuse, ext_dir=None):
    fdir = os.path.join(work, "frames")
    os.makedirs(fdir, exist_ok=True)
    n = int(math.ceil(info["dur"] * info["fps"]))
    ext = None
    if ext_dir:
        # 同时兼容 frame_%05d.png 与 Remotion 的 element-<frame>.png，按帧号索引而非字典序
        ext = {}
        for p in glob.glob(os.path.join(ext_dir, "*.png")):
            m = re.search(r"(\d+)\.png$", os.path.basename(p))
            if m:
                ext[int(m.group(1))] = p
        reuse = False
        print("      external animation frames: %d" % len(ext))
    if reuse and os.path.exists(os.path.join(fdir, "%05d.png" % (n - 1))):
        return n, fdir, True
    anim = Animator(cfg, st, build_background(cfg, work, info), work)
    base = static_base(cfg, st)
    base_path = os.path.join(work, "base.png")
    base.save(base_path)
    title = cfg.get("title_card", {}).get("show")
    person = cfg.get("person", {}).get("show")
    segs = cfg.get("segments", [])
    for i in range(n):
        t = i / info["fps"]
        path = os.path.join(fdir, "%05d.png" % i)
        active = next(((s, (t - s["start"]) / (s["end"] - s["start"]),
                        fade(t, s["start"], s["end"]))
                       for s in segs if s["start"] <= t < s["end"]), None)
        in_title = title and title[0] <= t < title[1]
        person_range = in_ranges(t, person)
        if active is None and not in_title and person_range is None:
            shutil.copyfile(base_path, path)
            continue
        if active:
            seg, p, al = active
            if ext:
                frame = anim.background_frame(al)
                if i in ext:
                    layer = Image.open(ext[i]).convert("RGBA")
                    if layer.size != (DW, DH):
                        layer = layer.resize((DW, DH), Image.LANCZOS)
                    if al < 1:
                        layer.putalpha(layer.getchannel("A").point(lambda v: int(v * al)))
                    frame = Image.alpha_composite(frame, layer)
            else:
                frame = anim.frame(seg, p, al)
            frame = Image.alpha_composite(frame, base)
        else:
            frame = base.copy()
        if in_title:
            draw_title(frame, cfg, st, fade(t, title[0], title[1], 0.4))
        if person_range is not None:
            draw_person(frame, cfg, st,
                        fade(t, person_range[0], person_range[1], 0.3))
        frame.save(path, compress_level=3)
    return n, fdir, False


# ---------------- 合成 ----------------
def compose(cfg, st, work, info, n, final):
    src, fps = cfg["source"], info["fps"]
    W, H = info["w"], info["h"]
    ov = "[1:v]scale=%d:%d[ovs]" % (W, H)
    enables = "+".join("between(t,%s,%s)" % (s["start"], s["end"])
                       for s in cfg.get("segments", [])) or "0"
    if st.pip:
        x, y, w, h = st.pip
        head = ("[0:v]split=2[base][ps];"
                "[ps]crop=400:580:160:250,scale=%d:%d,format=rgba[pc];"
                "[2:v]format=gray,scale=%d:%d[mg];"
                "[pc][mg]alphamerge[pip];"
                "[base][pip]overlay=%d:%d:enable='%s'[v1];" %
                (int(w), int(h), int(w), int(h), int(x * W / DW), int(y * H / DH), enables))
    else:
        head = "[0:v]null[v1];"
    fade_cfg = cfg.get("audio", {}).get("fade_out")
    af = ",afade=t=out:st=%s:d=%s" % (fade_cfg[0], fade_cfg[1]) if fade_cfg else ""
    fc = (head + ov + ";[v1][ovs]overlay=0:0[v2];"
          "[v2]ass=subtitles.ass[vout];[0:a]anull%s[aout]" % af)
    run(["ffmpeg", "-y", "-v", "warning", "-i", src,
         "-framerate", str(fps), "-start_number", "0",
         "-i", "frames/%05d.png"] +
        (["-i", "pip_mask.png"] if st.pip else []) +
        ["-filter_complex", fc, "-map", "[vout]", "-map", "[aout]",
         "-c:v", "libx264", "-preset", "medium", "-crf", "19",
         "-pix_fmt", "yuv420p", "-r", str(fps),
         "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-ac", "2",
         "-t", str(info["dur"]), "main.mp4"], cwd=work)

    edur = float(cfg.get("ending", {}).get("duration", 2.0))
    run(["ffmpeg", "-y", "-v", "warning", "-loop", "1", "-framerate", str(fps),
         "-i", "ending.png", "-f", "lavfi",
         "-i", "anullsrc=channel_layout=stereo:sample_rate=48000",
         "-t", str(edur), "-c:v", "libx264", "-preset", "medium", "-crf", "19",
         "-pix_fmt", "yuv420p", "-r", str(fps),
         "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-ac", "2",
         "-shortest", "ending.mp4"], cwd=work)
    with open(os.path.join(work, "list.txt"), "w", encoding="utf-8") as f:
        f.write("file 'main.mp4'\nfile 'ending.mp4'\n")
    run(["ffmpeg", "-y", "-v", "warning", "-f", "concat", "-safe", "0",
         "-i", "list.txt", "-c", "copy", "-movflags", "+faststart", final], cwd=work)


def make_sheet(final, work, info, cfg):
    fps = info["fps"]
    edur = float(cfg.get("ending", {}).get("duration", 2.0))
    # 定点覆盖片头、人物条、每段动画中点、结尾真人、片尾，避免等间隔采样漏段
    pts = [1.7, 7.3] + [(s["start"] + s["end"]) / 2 for s in cfg.get("segments", [])[:4]]
    pts += [max(1, info["dur"] - 3), info["dur"] + edur * 0.4]
    while len(pts) < 8:
        pts.append(info["dur"] * (len(pts) + 1) / 9)
    marks = [int(t * fps) for t in pts[:8]]
    sel = "+".join("eq(n,%d)" % m for m in marks)
    run(["ffmpeg", "-y", "-v", "error", "-i", final,
         "-vf", "select='%s',scale=360:640,tile=4x2:padding=4:margin=4:color=white" % sel,
         "-fps_mode", "vfr", "-frames:v", "1", "contact_sheet.png"], cwd=work)


def write_checklist(cfg, work, outdir, final):
    prof = cfg.get("_profile", "medical")
    pdef = cfg.get("_profile_def", PROFILES["medical"])
    data = {
        "status": "DRAFT_PENDING_HUMAN_REVIEW",
        "profile": prof,
        "profile_label": pdef.get("label", prof),
        "output": final,
        "auto_publish": False,
        "ai_disclosure_in_video": any(
            "AI" in s or "人工智能" in s or "生成合成" in s
            for s in cfg.get("disclaimer", [])),
        "ai_disclosure_note": "不在画面烧录；由后期/发布环节按平台要求添加",
        "checks": list(pdef.get("checks", [])),
    }
    for d in (work, outdir):
        if d:
            with open(os.path.join(d, "review_checklist.json"), "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)



def apply_profile(cfg, args):
    """场景预设：显式配置优先，缺省值由 profile 提供，默认 medical 保持向后兼容。"""
    name = args.profile or cfg.get("profile", "medical")
    if name not in PROFILES:
        raise SystemExit("unknown profile: %s (choose from %s)" %
                         (name, ", ".join(PROFILES)))
    pdef = PROFILES[name]
    if "disclaimer" not in cfg:
        cfg["disclaimer"] = list(pdef["disclaimer"])
    cfg["profile"] = name
    cfg["_profile"] = name
    cfg["_profile_def"] = pdef
    return cfg

PERSON_FIELDS = (
    ("name", "person_name", "姓名"),
    ("title", "person_title", "机构 / 单位（名片右列）"),
    ("department", "person_department", "科室（名片左列）"),
    ("rank", "person_rank", "职称（如 副主任医师）"),
)


def resolve_person(cfg, args):
    """三种用户输入入口：配置文件 < 命令行覆盖 < 交互输入。"""
    p = cfg.setdefault("person", {})
    for key, attr, _ in PERSON_FIELDS:
        v = getattr(args, attr, None)
        if v is not None:
            p[key] = v
    if args.person_subtitle is not None:
        p["department"] = args.person_subtitle
    if args.person_show:
        try:
            nums = [float(v) for v in args.person_show.replace(",", " ").split()]
        except ValueError:
            raise SystemExit("--person-show needs seconds like '2,12' or '2,12 36,42'")
        if len(nums) % 2:
            raise SystemExit("--person-show needs start/end pairs")
        p["show"] = [[nums[i], nums[i + 1]] for i in range(0, len(nums), 2)]
    if not p.get("show"):
        p["show"] = [[2.0, 12.0]]
    if args.ask_person:
        if not sys.stdin.isatty():
            print("WARNING: --ask-person needs an interactive terminal; skipped.")
        else:
            for key, _, label in PERSON_FIELDS:
                cur = p.get(key, "")
                v = input("%s [%s]: " % (label, cur)).strip()
                if v:
                    p[key] = v
    return cfg


def preview_card(cfg, st, work, info, out):
    """只出一张名片预览图，便于用户输入后快速校验样式，无需跑完整合成。"""
    bg = os.path.join(work, "preview_bg.png")
    run(["ffmpeg", "-y", "-v", "error", "-ss",
         str(cfg.get("background_time", 5)), "-i", cfg["source"],
         "-frames:v", "1", bg])
    im = Image.open(bg).convert("RGBA")
    if im.size != (DW, DH):
        im = im.resize((DW, DH), Image.LANCZOS)
    im = Image.alpha_composite(im, static_base(cfg, st))
    draw_person(im, cfg, st, 1.0)
    out = os.path.abspath(out)
    os.makedirs(os.path.dirname(out), exist_ok=True)
    im.convert("RGB").save(out)
    print("CARD PREVIEW ->", out)


def main():
    if "--list-profiles" in sys.argv:
        for k, v in PROFILES.items():
            print("%-12s %-12s %s" % (k, v["label"], " / ".join(v["kinds"])))
        return
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", required=True)
    ap.add_argument("--profile", help="场景预设：medical / product / ecommerce / general")
    ap.add_argument("--list-profiles", action="store_true", help="列出全部场景预设")
    ap.add_argument("--workdir")
    ap.add_argument("--output")
    ap.add_argument("--reuse-frames", action="store_true")
    ap.add_argument("--animation-frames",
                    help="外部渲染的透明动画 PNG 序列目录（Remotion / AE / 任意逐帧工具）")
    ap.add_argument("--person-name", help="人物姓名（覆盖配置）")
    ap.add_argument("--person-title", help="机构/单位，名片右列竖排（覆盖配置）")
    ap.add_argument("--person-department", help="科室，名片左列竖排（覆盖配置）")
    ap.add_argument("--person-subtitle", help="--person-department 的兼容别名")
    ap.add_argument("--person-rank", help="职称，如 副主任医师（覆盖配置）")
    ap.add_argument("--person-show", help="显示区间秒数，如 '2,12' 或 '2,12 36,42'")
    ap.add_argument("--ask-person", action="store_true",
                    help="交互式逐项输入人物信息（需终端）")
    ap.add_argument("--preview-card", help="只生成一张名片预览 PNG，不合成视频")
    args = ap.parse_args()
    with open(args.config, "r", encoding="utf-8") as f:
        cfg = json.load(f)
    cfg = apply_profile(cfg, args)
    src = os.path.abspath(cfg["source"])
    cfg["source"] = src
    final = os.path.abspath(args.output or cfg.get("output") or
                            os.path.join(os.path.dirname(src), "packaged.mp4"))
    outdir = os.path.dirname(final)
    os.makedirs(outdir, exist_ok=True)
    work = os.path.abspath(args.workdir or
                           cfg.get("workdir") or os.path.join(outdir, ".packager_work"))
    os.makedirs(work, exist_ok=True)
    info = probe(src)
    if abs(info["w"] / info["h"] - DW / DH) > 0.02:
        print("WARNING: source is not 9:16; overlay is designed for 9:16 and may stretch.")
    st = Style(cfg)
    cfg = resolve_person(cfg, args)
    if args.preview_card:
        preview_card(cfg, st, work, info, args.preview_card)
        return
    print("[0/6] profile: %s (%s)" % (cfg["_profile"], cfg["_profile_def"]["label"]))
    print("[1/6] subtitles")
    build_subtitles(cfg, st, work, outdir)
    print("[2/6] assets")
    build_assets(cfg, st, work, info)
    ext = args.animation_frames or cfg.get("animation_frames")
    print("[3/6] frames (backend: %s)" % ("external" if ext else "builtin-pillow"))
    n, _, reused = build_frames(cfg, st, work, info, args.reuse_frames, ext)
    print("      %d frames%s" % (n, " (reused)" if reused else ""))
    print("[4/6] compose")
    compose(cfg, st, work, info, n, final)
    print("[5/6] contact sheet")
    make_sheet(final, work, info, cfg)
    print("[6/6] review checklist")
    write_checklist(cfg, work, outdir, final)
    print("\nDONE -> %s" % final)
    print("      %s" % os.path.join(work, "contact_sheet.png"))
    print("      %s" % os.path.join(outdir, "review_checklist.json"))
    print("      STATUS: DRAFT_PENDING_HUMAN_REVIEW (do not auto-publish)")


if __name__ == "__main__":
    main()
