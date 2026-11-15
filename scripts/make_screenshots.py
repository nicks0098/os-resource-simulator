#!/usr/bin/env python3
"""Runs real commands and renders their output as terminal-style PNG screenshots
into outputs/screenshots/. Re-run any time: python3 scripts/make_screenshots.py"""
import os
import subprocess
import sys
import textwrap

from PIL import Image, ImageDraw, ImageFont

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "outputs", "screenshots")
FONT = "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf"
BOLD = "/usr/share/fonts/truetype/dejavu/DejaVuSansMono-Bold.ttf"

SHOTS = [
    ("01_menu_session", "python3 main.py", "1\n\n\n\n0\n", None),
    ("02_cpu_scheduling_rr", "python3 main.py schedule --algo rr --quantum 4", None, None),
    ("03_cpu_scheduling_srtf", "python3 main.py schedule --algo srtf", None, None),
    ("04_page_replacement_lru", "python3 main.py memory --algo lru", None, 38),
    ("05_deadlock_bankers", "python3 main.py deadlock", None, None),
    ("06_disk_scheduling", "python3 main.py disk --algo all", None, None),
    ("07_analysis_tables", "python3 main.py analyze", None, 60),
    ("08_validation_errors", "python3 main.py memory --refs '1 2 x' --frames 3; python3 main.py disk --input /no/file.json", None, None),
    ("09_unit_tests", "python3 -m unittest discover -s tests 2>&1 | tail -n 8", None, None),
    ("10_bash_system_info", "bash scripts/system_info.sh", None, None),
    ("11_bash_log_report", "bash scripts/log_report.sh", None, None),
]


def render(name, cmd, text, limit=None, width=110):
    lines = [f"$ {cmd}"] + ["" if l == "" else l for l in text.splitlines()]
    if limit:
        lines = lines[:limit] + ["..."]
    wrapped = []
    for l in lines:
        wrapped += textwrap.wrap(l, width, drop_whitespace=False, replace_whitespace=False) or [""]
    f, fb = ImageFont.truetype(FONT, 15), ImageFont.truetype(BOLD, 15)
    lh, pad, bar = 20, 18, 34
    w = int(max(f.getlength(l) for l in wrapped) + 2 * pad)
    h = bar + pad * 2 + lh * len(wrapped)
    img = Image.new("RGB", (max(w, 700), h), (30, 31, 38))
    d = ImageDraw.Draw(img)
    d.rectangle([0, 0, img.width, bar], fill=(52, 54, 64))
    for i, c in enumerate([(255, 95, 86), (255, 189, 46), (39, 201, 63)]):
        d.ellipse([14 + i * 22, 11, 26 + i * 22, 23], fill=c)
    d.text((img.width // 2 - 90, 9), "osim - terminal", font=f, fill=(190, 190, 200))
    y = bar + pad
    for i, l in enumerate(wrapped):
        color = (120, 220, 140) if l.startswith("$ ") else (220, 222, 230)
        if l.startswith(("===", "#####")):
            color = (120, 190, 255)
        if "FAULT" in l or "DENIED" in l or "Error" in l or "Invalid" in l or "FAIL" in l:
            color = (255, 140, 130)
        d.text((pad, y), l, font=fb if l.startswith(("$ ", "===", "#####")) else f, fill=color)
        y += lh
    img.save(os.path.join(OUT, name + ".png"))
    print("saved", name)


def main():
    os.makedirs(OUT, exist_ok=True)
    for name, cmd, stdin, limit in SHOTS:
        r = subprocess.run(cmd, shell=True, capture_output=True, text=True, input=stdin, cwd=ROOT, timeout=180)
        render(name, cmd, (r.stdout + r.stderr).rstrip("\n"), limit)


if __name__ == "__main__":
    sys.exit(main())
