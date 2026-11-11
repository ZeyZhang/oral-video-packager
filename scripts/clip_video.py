#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Clip editing stage for oral-video-packager.

Cuts a long talking-head source into selected ranges (or removes dead air /
filler time), then remaps every time-coded overlay onto the shortened
timeline so subtitles, animation segments, lower-thirds and audio fades stay
in sync with the picture.

Modes
  keep    : `ranges` are the parts to KEEP
  cut     : `ranges` are the parts to REMOVE (the complement is kept)
  silence : detect silent gaps with ffmpeg silencedetect and remove them

Standalone
  python clip_video.py --source long.mp4 --ranges "0,12 18,33 41,64" --output short.mp4
  python clip_video.py --config config.clip.json --output short.mp4
  python clip_video.py --config config.clip.json --mode silence --output short.mp4

Config (all inside the "clip" object)
  mode        keep | cut | silence          (default keep)
  ranges      [[start,end], ...]           seconds on the ORIGINAL timeline
  pad         seconds of protection around each cut (default 0.08)
  min_gap     merge kept ranges closer than this (default 0.0)
  silence     {noise:"-35dB", min_duration:0.45, keep:0.12}
  batch       also export each kept range as its own clip + config
  output      path of the edited video (default <workdir>/clipped.mp4)
"""
import argparse
import copy
import json
import os
import re
import subprocess
import sys

# 叠层按 720x1280 / 30fps 设计画布绘制；切片阶段顺手把非标准源统一过来，
# 避免后续 compose() 里 PiP crop / overlay 坐标越界，且只需一次重编码。
DESIGN_W, DESIGN_H, DESIGN_FPS = 720, 1280, 30


def needs_normalize(info):
    return (info["w"] != DESIGN_W or info["h"] != DESIGN_H or
            abs(info["fps"] - DESIGN_FPS) > 0.01)


def run(cmd, capture=False):
    if capture:
        return subprocess.run(cmd, capture_output=True, text=True)
    subprocess.run(cmd, check=True)
    return None


def probe(path):
    out = subprocess.check_output(
        ["ffprobe", "-v", "error", "-show_entries",
         "format=duration:stream=codec_type,width,height,r_frame_rate",
         "-of", "json", path], text=True)
    d = json.loads(out)
    dur = float(d["format"]["duration"])
    v = next((s for s in d["streams"] if s["codec_type"] == "video"), None)
    if v is None:
        raise SystemExit("no video stream: %s" % path)
    num, _, den = (v.get("r_frame_rate") or "30/1").partition("/")
    try:
        fps = float(num) / float(den or 1)
    except (ValueError, ZeroDivisionError):
        fps = 30.0
    has_audio = any(s["codec_type"] == "audio" for s in d["streams"])
    return {"dur": dur, "fps": round(fps, 4), "w": v["width"],
            "h": v["height"], "has_audio": has_audio}


def parse_ranges(text):
    out = []
    for chunk in re.split(r"[\s;]+", text.strip()):
        if not chunk:
            continue
        parts = chunk.replace("-", ",").split(",")
        if len(parts) != 2:
            raise SystemExit("bad range %r, expected 'start,end'" % chunk)
        out.append([float(parts[0]), float(parts[1])])
    return out


def _merge(ranges, min_gap):
    ranges = sorted([list(r) for r in ranges if r[1] > r[0]])
    merged = []
    for a, b in ranges:
        if merged and a - merged[-1][1] <= min_gap:
            merged[-1][1] = max(merged[-1][1], b)
        else:
            merged.append([a, b])
    return merged


def detect_silence(src, opt, dur):
    noise = str(opt.get("noise", "-35dB"))
    min_dur = float(opt.get("min_duration", 0.45))
    keep = float(opt.get("keep", 0.12))
    r = run(["ffmpeg", "-hide_banner", "-i", src, "-af",
             "silencedetect=noise=%s:d=%s" % (noise, min_dur),
             "-f", "null", "-"], capture=True)
    log = (r.stderr or "") + (r.stdout or "")
    starts = [float(x) for x in re.findall(r"silence_start:\s*([0-9.]+)", log)]
    ends = [float(x) for x in re.findall(r"silence_end:\s*([0-9.]+)", log)]
    cuts = []
    for i, a in enumerate(starts):
        b = ends[i] if i < len(ends) else dur
        a2, b2 = a + keep, b - keep
        if b2 > a2:
            cuts.append([a2, b2])
    return cuts


def complement(cuts, dur):
    kept, pos = [], 0.0
    for a, b in _merge(cuts, 0.0):
        a, b = max(0.0, a), min(dur, b)
        if a > pos:
            kept.append([pos, a])
        pos = max(pos, b)
    if pos < dur:
        kept.append([pos, dur])
    return kept


def build_ranges(cfg, info):
    c = cfg.get("clip", {})
    src, dur = cfg["source"], info["dur"]
    mode = c.get("mode", "keep")
    pad = float(c.get("pad", 0.08))
    min_gap = float(c.get("min_gap", 0.0))
    if mode == "silence":
        raw = complement(detect_silence(src, c.get("silence", {}), dur), dur)
        # pad protects the words at both ends of a silence cut: shrink kept parts
        raw = [[a + pad, b - pad] for a, b in raw]
    elif mode == "cut":
        raw = complement(c.get("ranges", []), dur)
        raw = [[a + pad, b - pad] for a, b in raw]
    elif mode == "keep":
        raw = [[float(a) - pad, float(b) + pad]
               for a, b in c.get("ranges", [])]
    else:
        raise SystemExit("unknown clip mode: %s (keep/cut/silence)" % mode)
    raw = [[max(0.0, a), min(dur, b)] for a, b in raw]
    ranges = _merge(raw, min_gap)
    if not ranges:
        raise SystemExit("clip produced no kept ranges; check ranges/mode")
    total = sum(b - a for a, b in ranges)
    print("      mode=%s  kept=%d segments  %.2fs -> %.2fs (removed %.2fs)" %
          (mode, len(ranges), dur, total, dur - total))
    return ranges


class EditMap:
    """Original timeline <-> edited timeline."""

    def __init__(self, ranges, fps):
        self.fps = fps
        self.segs, acc = [], 0.0
        for a, b in ranges:
            s = {"start": a, "end": b, "new_start": acc,
                 "new_end": acc + (b - a)}
            self.segs.append(s)
            acc = s["new_end"]
        self.duration = round(acc, 3)

    def seg_at(self, t):
        for s in self.segs:
            if s["start"] <= t < s["end"]:
                return s
        if self.segs and abs(t - self.segs[-1]["end"]) < 1e-6:
            return self.segs[-1]
        return None

    def point(self, t):
        s = self.seg_at(t)
        return None if s is None else s["new_start"] + (t - s["start"])

    def interval(self, a, b, snap=False):
        """Map [a,b] inside a single kept range; never cross a cut."""
        s = self.seg_at(a)
        if s is None and snap:
            nxt = next((x for x in self.segs if x["start"] >= a), None)
            if nxt and nxt["start"] < b:
                s, a = nxt, nxt["start"]
        if s is None:
            return None
        end = min(b, s["end"])
        if end <= a:
            return None
        return (s["new_start"] + (a - s["start"]),
                s["new_start"] + (end - s["start"]))

    def as_dict(self, source):
        return {"source": source, "fps": self.fps, "duration": self.duration,
                "segments": [{"start": round(s["start"], 3),
                              "end": round(s["end"], 3),
                              "new_start": round(s["new_start"], 3),
                              "new_end": round(s["new_end"], 3)}
                             for s in self.segs]}


def render_segments(src, ranges, out, info):
    """Frame-accurate cut + concat in one pass (video and audio)."""
    if os.path.exists(out):
        os.remove(out)
    os.makedirs(os.path.dirname(out), exist_ok=True)
    fps = info["fps"]
    n = len(ranges)
    fc = ["[0:v]split=%d%s" % (n, "".join("[v%d]" % i for i in range(n)))]
    afade = []
    if info["has_audio"]:
        fc.append("[0:a]asplit=%d%s" %
                  (n, "".join("[a%d]" % i for i in range(n))))
    for i, (a, b) in enumerate(ranges):
        fc.append("[v%d]trim=start=%.4f:end=%.4f,setpts=PTS-STARTPTS,"
                  "fps=%s,format=yuv420p[v%do]" % (i, a, b, fps, i))
        if info["has_audio"]:
            d = max(0.0, b - a)
            fade_out_st = max(0.0, d - 0.025)
            fc.append("[a%d]atrim=start=%.4f:end=%.4f,asetpts=PTS-STARTPTS,"
                      "afade=t=in:st=0:d=0.02,"
                      "afade=t=out:st=%.4f:d=0.02[a%do]" %
                      (i, a, b, fade_out_st, i))
            afade.append("[v%do][a%do]" % (i, i))
    parts = "".join(afade) if info["has_audio"] else \
        "".join("[v%do]" % i for i in range(n))
    fc.append("%sconcat=n=%d:v=1:a=%d[vcat]%s" %
              (parts, n, 1 if info["has_audio"] else 0,
               "[aout]" if info["has_audio"] else ""))
    normal = needs_normalize(info)
    if normal:
        fc.append("[vcat]scale=%d:%d:force_original_aspect_ratio=decrease,"
                  "pad=%d:%d:(ow-iw)/2:(oh-ih)/2:color=black,setsar=1,"
                  "fps=%d[vout]" % (DESIGN_W, DESIGN_H, DESIGN_W, DESIGN_H,
                                    DESIGN_FPS))
        out_fps = DESIGN_FPS
    else:
        fc.append("[vcat]null[vout]")
        out_fps = fps
    cmd = ["ffmpeg", "-y", "-v", "error", "-i", src,
           "-filter_complex", ";".join(fc), "-map", "[vout]"]
    if info["has_audio"]:
        cmd += ["-map", "[aout]"]
    cmd += ["-c:v", "libx264", "-preset", "medium", "-crf", "18",
            "-pix_fmt", "yuv420p", "-r", str(out_fps)]
    if info["has_audio"]:
        cmd += ["-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-ac", "2"]
    cmd += ["-movflags", "+faststart", out]
    run(cmd)
    return out


def remap_config(cfg, m):
    """Re-time every overlay onto the edited timeline."""
    out = copy.deepcopy(cfg)
    dropped_cues, dropped_segs = 0, 0

    cues = []
    for c in out.get("subtitles", []):
        r = m.interval(float(c["start"]), float(c["end"]))
        if r and r[1] - r[0] >= 0.25:
            c = dict(c)
            c["start"], c["end"] = round(r[0], 3), round(r[1], 3)
            cues.append(c)
        else:
            dropped_cues += 1
    out["subtitles"] = cues

    segs = []
    for s in out.get("segments", []):
        a, b = float(s["start"]), float(s["end"])
        r = m.interval(a, b)
        if r and r[1] - r[0] >= (b - a) * 0.4:
            s = dict(s)
            s["start"], s["end"] = round(r[0], 3), round(r[1], 3)
            segs.append(s)
        else:
            dropped_segs += 1
    out["segments"] = segs

    def remap_show(value):
        if not value:
            return value
        pairs = [value] if len(value) == 2 and \
            all(isinstance(x, (int, float)) for x in value) else value
        mapped = []
        for pair in pairs:
            r = m.interval(float(pair[0]), float(pair[1]), snap=True)
            if r and r[1] - r[0] >= 0.2:
                mapped.append([round(r[0], 3), round(r[1], 3)])
        return mapped

    for key in ("title_card", "person"):
        if key in out and "show" in out[key]:
            out[key]["show"] = remap_show(out[key]["show"])

    bt = m.point(float(out.get("background_time", 0)))
    out["background_time"] = round(
        bt if bt is not None else (m.segs[0]["new_end"] / 2.0), 3)

    fade = out.get("audio", {}).get("fade_out")
    if fade:
        d = float(fade[1])
        out["audio"]["fade_out"] = [round(max(0.0, m.duration - d), 3), d]

    out["source"] = out["clip"]["output"]
    if out["clip"].get("packaged_output"):
        out["output"] = out["clip"]["packaged_output"]
    # clipped_config.json must NOT carry the clip section: re-running it would
    # cut the already-edited video a second time with the original timeline.
    out.pop("clip", None)
    out["_clip"] = {
                    "kept_duration": round(
                        sum(s["end"] - s["start"] for s in m.segs), 3),
                    "edited_duration": round(m.duration, 3),
                    "kept_segments": len(m.segs),
                    "dropped_subtitles": dropped_cues,
                    "dropped_animation_segments": dropped_segs}
    if dropped_cues or dropped_segs:
        print("      remap dropped %d subtitle(s), %d animation segment(s) "
              "that fell outside kept ranges" % (dropped_cues, dropped_segs))
    return out


def prepare(cfg, work):
    """Build the edited video, the remapped config and (optionally) single clips."""
    os.makedirs(work, exist_ok=True)
    c = dict(cfg.get("clip", {}))
    if not c.get("ranges") and c.get("mode", "keep") != "silence":
        raise SystemExit("clip.ranges is empty; nothing to cut")
    c["output"] = os.path.abspath(c.get("output") or
                                  os.path.join(work, "clipped.mp4"))
    cfg = dict(cfg)
    cfg["clip"] = c
    info = probe(cfg["source"])
    if needs_normalize(info):
        print("      normalize: %dx%d@%g -> %dx%d@%d" %
              (info["w"], info["h"], info["fps"],
               DESIGN_W, DESIGN_H, DESIGN_FPS))
    ranges = build_ranges(cfg, info)
    render_segments(cfg["source"], ranges, c["output"], info)
    m = EditMap(ranges, info["fps"])
    with open(os.path.join(work, "edit_map.json"), "w", encoding="utf-8") as f:
        json.dump(m.as_dict(cfg["source"]), f, ensure_ascii=False, indent=2)
    new_cfg = remap_config(cfg, m)
    new_cfg["_clip"]["source_duration"] = round(info["dur"], 3)
    new_cfg["source"] = c["output"]
    cfg_path = os.path.join(work, "clipped_config.json")
    with open(cfg_path, "w", encoding="utf-8") as f:
        json.dump(new_cfg, f, ensure_ascii=False, indent=2)
    if c.get("batch"):
        export_batch(cfg, ranges, info, m, work)
    print("      edited video -> %s" % c["output"])
    print("      remapped config -> %s" % cfg_path)
    return new_cfg, m


def export_batch(cfg, ranges, info, m, work):
    """One standalone clip per kept range, each with its own ready-to-run config."""
    base = os.path.join(work, "clips")
    os.makedirs(base, exist_ok=True)
    print("      batch: exporting %d single clips" % len(ranges))
    for i, (a, b) in enumerate(ranges, 1):
        single = os.path.join(base, "clip_%02d.mp4" % i)
        render_segments(cfg["source"], [(a, b)], single, info)
        one_map = EditMap([(a, b)], info["fps"])
        sub = copy.deepcopy(cfg)
        sub.pop("clip", None)
        sub = remap_config_single(sub, one_map, single,
                                  os.path.join(base, "clip_%02d_packaged.mp4" % i))
        with open(os.path.join(base, "clip_%02d.json" % i), "w",
                  encoding="utf-8") as f:
            json.dump(sub, f, ensure_ascii=False, indent=2)


def remap_config_single(cfg, m, source, output):
    cfg["clip"] = {"mode": "keep", "ranges": [[m.segs[0]["start"],
                                               m.segs[0]["end"]]],
                   "output": source, "packaged_output": output}
    out = remap_config(cfg, m)
    out.pop("clip", None)
    out["source"], out["output"] = source, output
    out["_clip"] = {"single_clip": True,
                    "source_range": [m.segs[0]["start"], m.segs[0]["end"]],
                    "edited_duration": round(m.duration, 3)}
    return out


def main():
    ap = argparse.ArgumentParser(description="Cut a talking-head video and remap overlays")
    ap.add_argument("--config", help="config json containing a 'clip' section")
    ap.add_argument("--source", help="source video (standalone mode)")
    ap.add_argument("--ranges", help="e.g. '0,12 18,33 41,64'")
    ap.add_argument("--mode", choices=["keep", "cut", "silence"])
    ap.add_argument("--output", help="edited video path")
    ap.add_argument("--workdir", help="where edit_map.json / clips/ are written")
    ap.add_argument("--batch", action="store_true", help="export each kept range too")
    args = ap.parse_args()

    if args.config:
        with open(args.config, "r", encoding="utf-8") as f:
            cfg = json.load(f)
        c = cfg.setdefault("clip", {})
        if args.mode:
            c["mode"] = args.mode
        if args.ranges:
            c["ranges"] = parse_ranges(args.ranges)
        if args.batch:
            c["batch"] = True
        if args.output:
            c["output"] = os.path.abspath(args.output)
        work = os.path.abspath(args.workdir or cfg.get("workdir") or
                               os.path.join(os.path.dirname(args.config),
                                            ".packager_work"))
        cfg["source"] = os.path.abspath(cfg["source"])
    else:
        if not (args.source and (args.ranges or args.mode == "silence")):
            raise SystemExit("standalone mode needs --source and --ranges "
                             "(or --mode silence)")
        cfg = {"source": os.path.abspath(args.source),
               "clip": {"mode": args.mode or "keep",
                        "ranges": parse_ranges(args.ranges) if args.ranges else [],
                        "output": os.path.abspath(args.output or "clipped.mp4")}}
        work = os.path.abspath(args.workdir or
                               os.path.join(os.path.dirname(cfg["clip"]["output"]),
                                            ".packager_work"))
    print("[clip] source: %s" % cfg["source"])
    new_cfg, m = prepare(cfg, work)
    print("\nDONE -> %s" % new_cfg["source"])
    print("      edited duration: %.2fs (%d kept segments)" %
          (m.duration, len(m.segs)))
    print("      next: python scripts/package_video.py --config %s" %
          os.path.join(work, "clipped_config.json"))
    print("      (clipped_config.json is already retimed; to change cuts, "
          "edit clip.ranges in the original config and re-run)")


if __name__ == "__main__":
    main()
