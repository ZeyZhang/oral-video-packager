#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Content-driven shot planning and multi-layout frame rendering.

Instead of putting every segment into the same blurred-background + PiP
template, this module splits the timeline into shots and assigns each one a
different screen layout based on what is actually being said:

  full     全屏真人（叙事/动作）
  focus    局部推近（表情/强调）
  pip      模糊背景 + 圆形小真人（讲解，兼容旧模板观感）
  split_v  左右分格：真人 | 数字/对比卡
  split_h  上下分格：真人 / 步骤条
  grid     2x2 宫格：真人 + 三张要点卡
  card     全屏大字卡（金句，真人不出）
  kinetic  全屏真人 + 巨幅关键词动效

Shots can be planned automatically (`shots.mode: "auto"`) from subtitles,
animation segments and keyword heuristics, or supplied manually as a list.
The plan is written to shot_plan.json so a human can review / override it.

Standalone:
  python shot_engine.py --config c.json --plan-only --out plan.json
"""
import argparse
import copy
import glob
import json
import math
import os
import re
import subprocess
import sys

from PIL import Image, ImageDraw, ImageFilter, ImageFont

W, H, FPS = 720, 1280, 30
GOLD = (226, 178, 38)
GOLD_L = (245, 210, 96)
WHITE = (246, 249, 252)
SOFT = (178, 190, 208)
DARK = (10, 18, 32)
PANEL = (20, 34, 56)
BLUE = (46, 132, 226)

LAYOUTS = ("full", "focus", "pip", "split_v", "split_h", "grid", "card", "kinetic")
TRANSITIONS = ("fade", "slide", "cut")

# subtitle placement per layout (ASS \pos anchor, font size)
SUB_STYLE = {
    "full": ((360, 1090), 40),
    "focus": ((360, 1090), 40),
    "pip": ((500, 1080), 32),
    "split_v": ((180, 1130), 30),
    "split_h": ((360, 1160), 31),
    "grid": ((360, 1175), 30),
    "card": ((360, 1160), 30),
    "kinetic": ((360, 1120), 36),
}

FONT_FILES = [
    ("C:/Windows/Fonts/msyhbd.ttc", "C:/Windows/Fonts/msyh.ttc"),
    ("C:/Windows/Fonts/simhei.ttf", "C:/Windows/Fonts/simhei.ttf"),
    ("/System/Library/Fonts/PingFang.ttc", "/System/Library/Fonts/PingFang.ttc"),
    ("/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc",
     "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc"),
    ("DejaVuSans-Bold.ttf", "DejaVuSans.ttf"),
]
_FONT_CACHE = {}


def font(size, bold=True):
    key = (size, bold)
    if key in _FONT_CACHE:
        return _FONT_CACHE[key]
    for a, b in FONT_FILES:
        p = a if bold else b
        try:
            f = ImageFont.truetype(p, size)
            _FONT_CACHE[key] = f
            return f
        except OSError:
            continue
    f = ImageFont.load_default()
    _FONT_CACHE[key] = f
    return f


def run(cmd):
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        sys.stderr.write(" ".join(cmd) + "\n" + r.stderr[-2500:] + "\n")
        raise SystemExit("ffmpeg failed (exit %d)" % r.returncode)
    return r.stdout


def clean(text):
    return re.sub(r"\*\*", "", str(text or "")).strip()


def wrap(d, text, f, max_w):
    """Greedy CJK-aware wrapping."""
    out, cur = [], ""
    for ch in text:
        if ch == "\n":
            out.append(cur)
            cur = ""
            continue
        if d.textlength(cur + ch, font=f) > max_w and cur:
            out.append(cur)
            cur = ch
        else:
            cur += ch
    if cur:
        out.append(cur)
    return out


def text_block(d, xy, text, f, fill, max_w, line_h, align="left",
               shadow=True, anchor_center=False):
    x, y = xy
    for line in wrap(d, text, f, max_w):
        tw = d.textlength(line, font=f)
        lx = x - tw / 2 if anchor_center else (x + (max_w - tw) / 2 if align == "center" else x)
        if shadow:
            d.text((lx + 2, y + 3), line, font=f, fill=(0, 0, 0, 210))
        d.text((lx, y), line, font=f, fill=fill)
        y += line_h


def gradient(size, top, bottom):
    im = Image.new("RGB", size)
    d = ImageDraw.Draw(im)
    for y in range(size[1]):
        k = y / max(1, size[1] - 1)
        d.line((0, y, size[0], y),
               fill=tuple(int(top[i] + (bottom[i] - top[i]) * k) for i in range(3)))
    return im


def rounded(d, box, radius, fill, outline=None, width=1):
    d.rounded_rectangle(box, radius=radius, fill=fill, outline=outline, width=width)


def cover(im, box_w, box_h, center=(0.5, 0.42)):
    """Crop `im` to fill box_w x box_h without distortion."""
    r = max(box_w / im.width, box_h / im.height)
    nw, nh = int(im.width * r), int(im.height * r)
    im = im.resize((nw, nh), Image.LANCZOS)
    cx, cy = int(nw * center[0]), int(nh * center[1])
    x0 = max(0, min(nw - box_w, cx - box_w // 2))
    y0 = max(0, min(nh - box_h, cy - box_h // 2))
    return im.crop((x0, y0, x0 + box_w, y0 + box_h))


def circle(im, size, center):
    m = Image.new("L", size, 0)
    ImageDraw.Draw(m).ellipse((0, 0, size[0], size[1]), fill=255)
    im.paste(Image.new("RGB", size, WHITE), center, m)


# ---------------- planning ----------------

NUM_RE = re.compile(r"\d|[０-９]|百分之|成|倍|年|秒|块|元")
CMP_RE = re.compile(r"比|不如|区别|对比|最|更|左右|相比|反之")
QUOTE_RE = re.compile(r"其实|记住|别|就|才是|关键|真正|一定|千万")
EMO_RE = re.compile(r"[！!？?]|哈哈|哎呀|忍不住")

KIND_LAYOUT = {
    "quote": "card", "points": "grid", "features": "grid",
    "steps": "split_h", "funnel": "split_h", "timeline": "split_h",
    "stats": "split_v", "compare": "split_v", "matrix": "grid",
    "scan": "pip", "resection": "pip",
}


def _seg_items(seg):
    items = []
    for k in ("points", "labels"):
        items += [clean(x) for x in seg.get(k, []) or []]
    for row in seg.get("lines", []) or []:
        if isinstance(row, dict):
            items.append(clean(row.get("text")))
        else:
            items.append(clean(row))
    for c in seg.get("columns", []) or []:
        items.append("%s %s" % (clean(c.get("label")), clean(c.get("value", ""))))
    for b in seg.get("bars", []) or []:
        items.append("%s %s" % (clean(b.get("label")), clean(b.get("value", ""))))
    return [x for x in items if x][:4]


def _cues_in(cfg, a, b):
    return [c for c in cfg.get("subtitles", [])
            if float(c["end"]) > a and float(c["start"]) < b]


def choose_layout(text, seg, prev, index, has_speech):
    if seg:
        base = KIND_LAYOUT.get(seg.get("kind"), "pip")
        if base == prev and index % 2 == 0:
            return "split_v"
        return base
    if not has_speech:
        return "focus" if prev in ("full", "focus") else "full"
    t = clean(text)
    if len(t) <= 9 and (QUOTE_RE.search(t) or EMO_RE.search(t)):
        cand = "kinetic" if prev != "kinetic" else "card"
    elif NUM_RE.search(t) or CMP_RE.search(t):
        cand = "split_v" if prev != "split_v" else "card"
    elif len(t) > 20:
        cand = "full" if prev != "full" else "focus"
    else:
        cand = "full" if prev == "pip" else "pip"
    if cand == prev:
        cand = {"full": "focus", "focus": "full", "pip": "split_v",
                "split_v": "grid", "grid": "full", "card": "kinetic",
                "kinetic": "full"}.get(cand, "full")
    return cand


def build_plan(cfg, opts=None):
    """Split timeline into semantic shots and assign layouts."""
    opts = opts or {}
    dur = float(cfg.get("_duration") or cfg.get("duration") or 0)
    if not dur:
        raise SystemExit("shot planning needs duration; pass --duration or run via package_video.py")
    cues = cfg.get("subtitles", [])
    segs = cfg.get("segments", [])
    if not dur and cues:
        dur = max(float(c["end"]) for c in cues)
    min_len = float(opts.get("min_duration", 1.15))
    transition = opts.get("transition", "fade")
    if transition not in TRANSITIONS:
        transition = "fade"

    def inside_seg(t):
        return any(float(s["start"]) + 1e-3 < t < float(s["end"]) - 1e-3
                   for s in segs)

    # boundaries: cue edges (but never cut through an animation segment)
    bounds = {0.0, round(dur, 3)}
    for c in cues:
        for t in (float(c["start"]), float(c["end"])):
            if not inside_seg(t):
                bounds.add(round(min(dur, max(0, t)), 3))
    for s in segs:
        bounds.add(round(min(dur, max(0, float(s["start"]))), 3))
        bounds.add(round(min(dur, max(0, float(s["end"]))), 3))
    pts = sorted(bounds)
    raw = [(pts[i], pts[i + 1]) for i in range(len(pts) - 1)
           if pts[i + 1] - pts[i] > 0.05]
    # merge tiny slices; a short leading slice joins the following shot
    merged = []
    for a, b in raw:
        if merged and (b - a) < min_len and merged[-1][1] - merged[-1][0] < 6.0:
            merged[-1][1] = b
        else:
            merged.append([a, b])
    if len(merged) > 1 and merged[0][1] - merged[0][0] < min_len:
        merged[1][0] = merged[0][0]
        merged.pop(0)
    raw = [tuple(x) for x in merged]

    plan, prev = [], None
    for i, (a, b) in enumerate(raw):
        seg = next((s for s in segs if float(s["start"]) <= a < float(s["end"])), None)
        cs = _cues_in(cfg, a, b)
        text = " / ".join(clean(x) for c in cs for x in
                          (c.get("lines") if isinstance(c.get("lines"), list)
                           else [c.get("lines")]))
        if seg:
            headline = clean(seg.get("title") or text) or "要点"
            items = _seg_items(seg)
            kicker = clean(seg.get("sub") or "")
        else:
            headline = text.split(" / ")[0] if text else ""
            items = text.split(" / ")[1:4]
            kicker = ""
        speech = sum(max(0.0, min(b, float(c["end"])) -
                         max(a, float(c["start"]))) for c in cs)
        ratio = speech / max(0.1, b - a)
        if seg:
            layout = choose_layout(text, seg, prev, i, bool(cs))
        elif ratio < 0.35:
            layout = "focus" if prev in ("full", "focus") else "full"
        else:
            layout = choose_layout(text, None, prev, i, True)
        if opts.get("layout_override"):
            layout = opts["layout_override"]
        st = SUB_STYLE[layout]
        plan.append({
            "index": i + 1,
            "start": round(a, 3), "end": round(b, 3),
            "layout": layout,
            "transition": "cut" if i == 0 else transition,
            "headline": headline[:28],
            "items": items,
            "kicker": kicker[:34],
            "text": text[:120],
            "segment_kind": seg.get("kind") if seg else None,
            "subtitle": {"pos": list(st[0]), "size": st[1]},
            "reason": _reason(layout, seg, text, ratio >= 0.35),
        })
        prev = layout
    return {"version": 1, "duration": round(dur, 3), "fps": FPS,
            "transition": transition, "shots": plan}


def _reason(layout, seg, text, speech):
    if seg:
        return "知识段 kind=%s → %s" % (seg.get("kind"), layout)
    if not speech:
        return "动作占比高（无台词/长静音）→ %s（保留画面）" % layout
    if EMO_RE.search(text) and len(clean(text)) <= 12:
        return "情绪/语气短句 → %s" % layout
    if NUM_RE.search(text):
        return "含数字/比较信息 → %s" % layout
    if QUOTE_RE.search(text) and len(clean(text)) <= 12:
        return "短金句/强调 → %s" % layout
    if len(clean(text)) > 20:
        return "长句讲解 → %s（少干扰）" % layout
    return "普通口播 → %s" % layout


def subtitle_prefix(plan, a, b):
    """ASS override tag so subtitles move with the layout."""
    if not plan:
        return ""
    shot = shot_at(plan, (float(a) + float(b)) / 2)
    if not shot:
        return ""
    pos, size = shot["subtitle"]["pos"], shot["subtitle"]["size"]
    return "{\\pos(%d,%d)\\fs%d}" % (pos[0], pos[1], size)


def shot_at(plan, t):
    for s in plan["shots"]:
        if s["start"] <= t < s["end"]:
            return s
    return plan["shots"][-1] if plan["shots"] else None


# ---------------- per-layout frame rendering ----------------

def _base(src, shot, cfg, p):
    """Common overlay: kicker, headline, footer hints. Returns RGBA layer."""
    lay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(lay)
    if shot.get("kicker"):
        text_block(d, (56, 92), shot["kicker"], font(24, False),
                   (226, 234, 244, 230), 600, 32, shadow=True)
    return lay


def _title(d, shot, y=170, size=54, center=True, color=GOLD):
    if shot.get("headline"):
        text_block(d, (W // 2 if center else 56, y), shot["headline"],
                   font(size), color + (255,), 620 if center else 600,
                   size + 14, align="center" if center else "left",
                   anchor_center=center, shadow=True)


def render_layout(src, shot, cfg, p):
    """Return a fully composed 720x1280 RGB frame for one shot."""
    lay = shot["layout"]
    im = Image.new("RGB", (W, H), DARK)
    d = ImageDraw.Draw(im, "RGBA")
    items = [x for x in (shot.get("items") or []) if x]
    if lay in ("split_v", "grid") and not items:
        # 没有要点时不要留半块空面板
        lay = "kinetic"

    if lay == "full":
        im.paste(src, (0, 0))
        d = ImageDraw.Draw(im, "RGBA")
        d.rectangle((0, H - 300, W, H), fill=(8, 14, 26, 90))
        return _finish(im, shot, cfg, p, show_title=False)

    if lay == "focus":
        zoom = 1.0 + 0.18 * min(1.0, p * 2.0)
        cw, ch = int(W / zoom), int(H / zoom)
        crop = cover(src, cw, ch, (0.5, 0.40)).resize((W, H), Image.LANCZOS)
        im.paste(crop, (0, 0))
        d = ImageDraw.Draw(im, "RGBA")
        d.rectangle((0, 0, W, 150), fill=(8, 14, 26, 70))
        d.rectangle((0, H - 320, W, H), fill=(8, 14, 26, 110))
        return _finish(im, shot, cfg, p, show_title=False)

    if lay == "pip":
        bg = src.filter(ImageFilter.GaussianBlur(26))
        bg = Image.blend(bg, Image.new("RGB", (W, H), DARK), 0.55)
        im.paste(bg, (0, 0))
        d = ImageDraw.Draw(im, "RGBA")
        _title(d, shot, 150, 54)
        if shot.get("kicker"):
            text_block(d, (W // 2, 232), shot["kicker"], font(28, False),
                       SOFT + (255,), 620, 38, anchor_center=True)
        pip = cover(src, 300, 300, (0.5, 0.38))
        circle(im, (300, 300), (30, 700))
        m = Image.new("L", (300, 300), 0)
        ImageDraw.Draw(m).ellipse((0, 0, 300, 300), fill=255)
        im.paste(pip, (30, 700), m)
        d = ImageDraw.Draw(im, "RGBA")
        d.ellipse((26, 696, 338, 1008), outline=(230, 238, 248, 190), width=3)
        for i, s in enumerate(items[:3]):
            y = 340 + i * 96
            rounded(d, (360, y, 672, y + 76), 16, (24, 40, 66, 225),
                    outline=(70, 100, 140, 180), width=2)
            text_block(d, (380, y + 20), s, font(28),
                       WHITE + (255,), 272, 38, shadow=False)
        return _finish(im, shot, cfg, p, show_title=False)

    if lay == "split_v":
        left = cover(src, 360, H, (0.5, 0.42))
        im.paste(left, (0, 0))
        d.rectangle((360, 0, W, H), fill=PANEL)
        d.rectangle((360, 0, 370, H), fill=GOLD)
        if shot.get("kicker"):
            text_block(d, (392, 190), shot["kicker"], font(24, False),
                       SOFT + (255,), 290, 34, shadow=False)
        text_block(d, (392, 300), shot.get("headline", ""), font(38),
                   WHITE + (255,), 290, 52, shadow=True)
        for i, s in enumerate(items[:3]):
            y = 520 + i * 150
            rounded(d, (392, y, 690, y + 116), 18, (32, 52, 82, 255))
            text_block(d, (410, y + 20), s, font(28), GOLD_L + (255,),
                       260, 38, shadow=False)
            text_block(d, (410, y + 62), "0%d" % (i + 1), font(24, False),
                       SOFT + (255,), 260, 30, shadow=False)
        return _finish(im, shot, cfg, p, show_title=False)

    if lay == "split_h":
        top = cover(src, W, 720, (0.5, 0.40))
        im.paste(top, (0, 0))
        d.rectangle((0, 720, W, H), fill=PANEL)
        d.rectangle((0, 720, W, 730), fill=GOLD)
        _title(d, shot, 780, 50)
        for i, s in enumerate(items[:4]):
            x = 50 + i * 160
            rounded(d, (x, 930, x + 140, 1060), 18, (34, 56, 88, 255),
                    outline=(70, 104, 148, 200), width=2)
            text_block(d, (x + 70, 950), "0%d" % (i + 1), font(34),
                       GOLD + (255,), 130, 40, anchor_center=True)
            text_block(d, (x + 70, 1000), s[:8], font(22, False),
                       WHITE + (255,), 134, 28, anchor_center=True)
        return _finish(im, shot, cfg, p, show_title=False)

    if lay == "grid":
        cells = [(0, 0), (360, 0), (0, 640), (360, 640)]
        for i, (x, y) in enumerate(cells):
            if i == 0:
                im.paste(cover(src, 356, 636, (0.5, 0.42)), (x + 2, y + 2))
            else:
                s = items[i - 1] if i - 1 < len(items) else (shot["headline"] if i == 1 else "")
                rounded(d, (x + 6, y + 6, x + 354, y + 634), 22,
                        (26, 44, 72, 255) if i != 3 else (34, 58, 92, 255))
                text_block(d, (x + 180, y + 110), "0%d" % i, font(56),
                           GOLD + (255,), 300, 66, anchor_center=True)
                text_block(d, (x + 30, y + 300), s, font(34),
                           WHITE + (255,), 300, 46, align="center", shadow=True)
                text_block(d, (x + 180, y + 540), shot.get("kicker", "")[:14],
                           font(20, False), SOFT + (255,), 300, 28,
                           anchor_center=True, shadow=False)
        return _finish(im, shot, cfg, p, show_title=False)

    if lay == "card":
        im = gradient((W, H), (16, 28, 50), (8, 14, 26))
        d = ImageDraw.Draw(im, "RGBA")
        d.ellipse((-160, -160, 260, 260), fill=(226, 178, 38, 26))
        d.ellipse((500, 1050, 900, 1450), fill=(46, 132, 226, 26))
        text_block(d, (W // 2, 300), shot.get("kicker", "") or "划重点",
                   font(26, False), SOFT + (255,), 600, 36,
                   anchor_center=True, shadow=False)
        text_block(d, (W // 2, 430), shot["headline"], font(76),
                   GOLD_L + (255,), 620, 100, anchor_center=True, shadow=True)
        d.line((220, 720, 500, 720), fill=GOLD + (220,), width=4)
        for i, s in enumerate(items[:3]):
            text_block(d, (W // 2, 790 + i * 84), s, font(38),
                       WHITE + (255,), 600, 52, anchor_center=True, shadow=True)
        return _finish(im, shot, cfg, p, show_title=False)

    if lay == "kinetic":
        im.paste(src, (0, 0))
        d = ImageDraw.Draw(im, "RGBA")
        d.rectangle((0, 0, W, H), fill=(8, 14, 26, 60))
        word = shot["headline"][:10]
        scale = 0.86 + 0.14 * min(1.0, p * 3)
        f = font(int(104 * scale))
        text_block(d, (W // 2, 300), word, f, GOLD_L + (255,), 660,
                   int(120 * scale), anchor_center=True, shadow=True)
        d.rounded_rectangle((150, 540, 570, 552), radius=6,
                            fill=GOLD + (230,))
        return _finish(im, shot, cfg, p, show_title=False)

    return _finish(im, shot, cfg, p, show_title=False)


def _finish(im, shot, cfg, p, show_title=False):
    """Shared chrome: shot index chip + global disclaimer + title card."""
    d = ImageDraw.Draw(im, "RGBA")
    sc = cfg.get("shots")
    if isinstance(sc, dict) and sc.get("debug_label"):
        d.rounded_rectangle((40, 40, 168, 88), radius=22,
                            fill=(10, 20, 36, 170))
        d.text((58, 50), "SHOT %02d" % shot["index"], font=font(22),
               fill=(226, 234, 244, 230))
        d.text((580, 50), shot["layout"].upper(), font=font(20, False),
               fill=(226, 178, 38, 220))
    lines = (cfg.get("disclaimer") or [])[:3]
    if lines:
        top = H - 30 * len(lines) - 16
        d.rectangle((0, top, W, H), fill=(0, 0, 0, 110))
        for i, s in enumerate(lines):
            f = font(18, False)
            tw = d.textlength(s, font=f)
            d.text(((W - tw) / 2, top + 8 + i * 28), s, font=f,
                   fill=(232, 238, 246, 220))
    return im


def draw_title_overlay(frame, cfg, t):
    """Title card is time-based, not shot-based."""
    tc = cfg.get("title_card") or {}
    show = tc.get("show")
    if not show or len(show) != 2 or not all(isinstance(v, (int, float)) for v in show):
        return frame
    a, b = show
    if not (a <= t < b):
        return frame
    alpha = min(1.0, max(0.0, (t - a) / 0.4)) * \
        min(1.0, max(0.0, (b - t) / 0.4))
    lay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    td = ImageDraw.Draw(lay, "RGBA")
    text_block(td, (W // 2, 180), tc.get("text", ""), font(60),
               GOLD + (int(255 * alpha),), 640, 76,
               anchor_center=True, shadow=True)
    if tc.get("sub"):
        text_block(td, (W // 2, 276), tc["sub"], font(30, False),
                   WHITE + (int(255 * alpha),), 620, 42,
                   anchor_center=True, shadow=True)
    return Image.alpha_composite(frame.convert("RGBA"), lay).convert("RGB")


# ---------------- rendering ----------------

def render(cfg, plan, work, info, source=None):
    """Render the whole timeline into a video with audio, using the plan."""
    src = source or cfg["source"]
    fps = info["fps"]
    n = int(math.ceil(info["dur"] * fps))
    fd = os.path.join(work, "src_frames")
    od = os.path.join(work, "shot_frames")
    os.makedirs(fd, exist_ok=True)
    os.makedirs(od, exist_ok=True)
    # 不删除旧帧：抽帧显式从 0 编号，渲染按实际文件列表索引，
    # 多余的旧文件排在末尾不会被读到，避免触碰已有文件。
    print("      extracting %d source frames" % n)
    run(["ffmpeg", "-y", "-v", "error", "-i", src,
         "-vf", "scale=%d:%d:force_original_aspect_ratio=decrease,"
                "pad=%d:%d:(ow-iw)/2:(oh-ih)/2,fps=%d" % (W, H, W, H, fps),
         "-start_number", "0", "-q:v", "3", os.path.join(fd, "%05d.jpg")])
    # ffmpeg image2 may start at 0 or 1 depending on build; index by real files
    paths = sorted(glob.glob(os.path.join(fd, "*.jpg")))
    if not paths:
        raise SystemExit("source frame extraction produced no images")
    if len(paths) < n:
        print("      warning: only %d source frames for %d slots" %
              (len(paths), n))

    shots = plan["shots"]
    tw = float(cfg.get("shots", {}).get("transition_duration", 0.28))
    cache = {}
    for i in range(n):
        t = i / fps
        cur = shot_at(plan, t)
        if t - cur["start"] < tw and cur["index"] > 1:
            prev = shots[cur["index"] - 2]
            k = min(1.0, max(0.0, (t - cur["start"]) / tw))
            f1 = _frame(paths, i, prev, cfg, cache, fps)
            f2 = _frame(paths, i, cur, cfg, cache, fps)
            if cur["transition"] == "slide":
                frame = f1.copy()
                off = int((1 - k) * W)
                if off < W:
                    frame.paste(f2.crop((0, 0, W - off, H)), (off, 0))
                if off > 0:
                    frame.paste(f1.crop((W - off, 0, W, H)), (0, 0))
            else:
                frame = Image.blend(f1, f2, k)
        else:
            frame = _frame(paths, i, cur, cfg, cache, fps)
        frame = draw_title_overlay(frame, cfg, t)
        frame.save(os.path.join(od, "%05d.jpg" % i), quality=92)
        if i % 300 == 0:
            print("      rendered %d/%d" % (i, n), flush=True)

    out = os.path.join(work, "shots_main.mp4")
    run(["ffmpeg", "-y", "-v", "error", "-framerate", str(fps),
         "-start_number", "0", "-i", os.path.join(od, "%05d.jpg"),
         "-i", src,
         "-map", "0:v", "-map", "1:a", "-c:v", "libx264",
         "-preset", "medium", "-crf", "19", "-pix_fmt", "yuv420p",
         "-r", str(fps), "-c:a", "aac", "-b:a", "192k",
         "-ar", "48000", "-ac", "2", "-frames:v", str(n),
         "-t", str(info["dur"]), "-movflags", "+faststart", out])
    return out


def _frame(paths, i, shot, cfg, cache, fps=FPS):
    """Render one frame in the given shot layout."""
    src = Image.open(paths[min(i, len(paths) - 1)]).convert("RGB")
    span = max(0.1, shot["end"] - shot["start"])
    local = min(1.0, max(0.0, (i / fps - shot["start"]) / span))
    return render_layout(src, shot, cfg, local)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", required=True)
    ap.add_argument("--duration", type=float)
    ap.add_argument("--plan-only", action="store_true")
    ap.add_argument("--out")
    args = ap.parse_args()
    with open(args.config, "r", encoding="utf-8") as f:
        cfg = json.load(f)
    if args.duration:
        cfg["_duration"] = args.duration
    plan = build_plan(cfg, cfg.get("shots", {}))
    out = args.out or os.path.join(os.path.dirname(args.config), "shot_plan.json")
    with open(out, "w", encoding="utf-8") as f:
        json.dump(plan, f, ensure_ascii=False, indent=2)
    print("PLAN ->", out, "(%d shots)" % len(plan["shots"]))
    for s in plan["shots"]:
        print("  %5.2f-%5.2f  %-8s %-16s %s" %
              (s["start"], s["end"], s["layout"], s["headline"][:16], s["reason"]))


if __name__ == "__main__":
    main()
