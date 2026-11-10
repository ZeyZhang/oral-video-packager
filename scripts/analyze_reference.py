# -*- coding: utf-8 -*-
"""拆解参考成片：输出元信息、缩略图拼板、关键帧，以及待填写的规格骨架。

用法:
  python analyze_reference.py --video 2.mp4 --outdir ./ref_analysis
"""
import argparse
import json
import os
import subprocess

from PIL import Image, ImageDraw, ImageFont


def run(cmd):
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        raise SystemExit(" ".join(cmd) + "\n" + r.stderr[-2000:])
    return r.stdout


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--video", required=True)
    ap.add_argument("--outdir", default="./ref_analysis")
    args = ap.parse_args()
    video = os.path.abspath(args.video)
    out = os.path.abspath(args.outdir)
    os.makedirs(out, exist_ok=True)

    meta = json.loads(run([
        "ffprobe", "-v", "error", "-show_entries",
        "stream=codec_type,width,height,r_frame_rate:format=duration",
        "-of", "json", video]))

    run(["ffmpeg", "-y", "-v", "error", "-i", video,
         "-vf", "fps=1/2,scale=180:320,tile=5x5:padding=4:margin=4:color=white",
         "-frames:v", "1", os.path.join(out, "contact_sheet.png")])

    dur = float(meta["format"]["duration"])
    stamps = [0.5, dur * 0.10, dur * 0.25, dur * 0.40, dur * 0.60, dur * 0.80, dur - 0.6]
    for i, t in enumerate(stamps):
        run(["ffmpeg", "-y", "-v", "error", "-ss", "%.2f" % t, "-i", video,
             "-frames:v", "1", os.path.join(out, "key_%02d.png" % i)])

    sheet = Image.open(os.path.join(out, "contact_sheet.png")).convert("RGB")
    try:
        f = ImageFont.truetype("C:/Windows/Fonts/msyh.ttc", 18)
    except Exception:
        f = ImageFont.load_default()
    d = ImageDraw.Draw(sheet)
    d.text((10, 6), "grid = 2s per cell, left-to-right / top-to-bottom", fill=(20, 20, 20), font=f)
    sheet.save(os.path.join(out, "contact_sheet.png"))

    notes = {
        "source_reference": video,
        "meta": meta,
        "TODO_fill_by_visual_review": {
            "title_card": {"text_color": "", "font_size_px": "", "y_position": ""},
            "subtitle": {"color": "", "outline": "", "highlight_color": "", "y_position": ""},
            "person_bar": {"present": False, "position": "", "content": ""},
            "knowledge_animation": [{"start": "", "end": "", "description": ""}],
            "disclaimer": {"lines": [], "position": ""},
            "ending": {"background": "", "avatar": "", "text": ""},
            "palette": {"primary": "", "accent": ""}
        },
        "instruction": "Inspect contact_sheet.png and key_*.png, then transfer these values into config.json style/segments/ending."
    }
    with open(os.path.join(out, "reference_notes.json"), "w", encoding="utf-8") as f:
        json.dump(notes, f, ensure_ascii=False, indent=2)
    print("Analysis written to:", out)
    print("  contact_sheet.png (2s/grid), key_00..key_06.png, reference_notes.json")
    print("Next: review the sheet, then fill assets/config.example.json -> your config.json")


if __name__ == "__main__":
    main()
