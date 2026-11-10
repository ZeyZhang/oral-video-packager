# -*- coding: utf-8 -*-
"""用 Remotion 渲染透明动画层（自然的 spring 动效），输出 PNG 帧序列。

用法:
  python render_remotion.py --config config.json [--remotion-dir DIR] [--out DIR]

生成 props.json 后调用 npx remotion render，帧序列交给 package_video.py --animation-frames 叠加。
"""
import argparse
import glob
import json
import os
import subprocess
import sys
from fractions import Fraction

HERE = os.path.dirname(os.path.abspath(__file__))
SKILL = os.path.dirname(HERE)
DEFAULT_REMOTION = os.path.join(SKILL, "remotion")

CHROME_CANDIDATES = [
    "C:/Program Files/Google/Chrome/Application/chrome.exe",
    "C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe",
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
    "/usr/bin/google-chrome",
]


def probe(path):
    out = subprocess.check_output([
        "ffprobe", "-v", "error", "-show_entries",
        "stream=width,height,r_frame_rate,codec_type:format=duration",
        "-of", "json", path], text=True)
    data = json.loads(out)
    v = next(s for s in data["streams"] if s["codec_type"] == "video")
    return {
        "w": int(v["width"]), "h": int(v["height"]),
        "fps": float(Fraction(v["r_frame_rate"])),
        "dur": float(data["format"]["duration"]),
    }


def rgb(c, default):
    c = c or default
    return "rgb(%d,%d,%d)" % tuple(int(x) for x in c)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", required=True)
    ap.add_argument("--remotion-dir", default=DEFAULT_REMOTION)
    ap.add_argument("--out")
    ap.add_argument("--frames", help="只渲染指定帧范围（如 540-545），用于快速验证动效")
    args = ap.parse_args()

    with open(args.config, "r", encoding="utf-8") as f:
        cfg = json.load(f)
    info = probe(os.path.abspath(cfg["source"]))
    st = cfg.get("style", {})
    props = {
        "fps": info["fps"],
        "durationInFrames": int(info["dur"] * info["fps"]),
        "width": info["w"],
        "height": info["h"],
        "gold": rgb(st.get("gold"), [226, 178, 38]),
        "goldLight": rgb(st.get("gold_light"), [245, 210, 96]),
        "segments": cfg.get("segments", []),
    }
    rdir = os.path.abspath(args.remotion_dir)
    out = os.path.abspath(args.out or cfg.get("animation_frames")
                          or os.path.join(rdir, "out", "frames"))
    os.makedirs(out, exist_ok=True)
    props_path = os.path.join(rdir, "props.json")
    with open(props_path, "w", encoding="utf-8") as f:
        json.dump(props, f, ensure_ascii=False, indent=2)

    chrome = next((c for c in CHROME_CANDIDATES if os.path.exists(c)), None)
    # Remotion 4.0.542+ 用 --sequence 输出 PNG 序列，不再支持 --codec=png。
    # 透明背景由组件的 backgroundColor:'transparent' 保证，PNG 天然带 alpha。
    cmd = ["npx", "remotion", "render", "src/index.ts", "Overlay", out,
           "--props=" + props_path, "--sequence", "--image-format=png",
           "--log=error"]
    if chrome:
        cmd.append("--browser-executable=" + chrome)
    if args.frames:
        cmd.append("--frames=" + args.frames)
    print("RUN:", " ".join(cmd), flush=True)
    r = subprocess.run(cmd, cwd=rdir, shell=(os.name == "nt"))
    if r.returncode != 0:
        raise SystemExit("Remotion render failed. Run 'npm install' in %s first." % rdir)

    files = sorted(glob.glob(os.path.join(out, "*.png")))
    print("\nFrames: %d -> %s" % (len(files), out))
    print("Next: python package_video.py --config <config> --animation-frames \"%s\"" % out)


if __name__ == "__main__":
    main()
