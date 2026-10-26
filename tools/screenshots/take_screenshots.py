"""Retake docs/assets/screenshots/ from the real CLI against the demo mocks.

Runs `python src/main.py model-sync ...` for real, against the Jamf Pro and Snipe-IT
stand-ins in tools/screenshots/mock_services.py, renders the captured output as a
terminal window in light and dark, and saves metadata-free PNGs. Not part of CI
(needs Chromium). Run with `make screenshots`.

Two things are rewritten so a retake gives the same picture: log lines lose their
timestamp, and the throughput figure of the progress bar is dropped. The temporary
config path is shown as config/config.yaml, the path the docs tell you to use.
"""
from __future__ import annotations

import html
import os
import re
import subprocess
import sys
import tempfile
import threading
from pathlib import Path

from PIL import Image
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(Path(__file__).parent))
import mock_services  # noqa: E402

OUT = ROOT / "docs" / "assets" / "screenshots"
JAMF_PORT, SNIPE_PORT = 8101, 8102
# the CLI runs with the project's own environment (make venv), not the screenshot one
CLI_PYTHON = ROOT / ".venv" / "bin" / "python"

CONFIG = f"""jamf:
  base_url: "http://127.0.0.1:{JAMF_PORT}"
  username: "demo"
  password: "demo"
snipeit:
  base_url: "http://127.0.0.1:{SNIPE_PORT}"
  api_token: "demo"
"""

# name -> (shown command, argv after `model-sync`)
SCENES = {
    "model-sync-check": ("python src/main.py model-sync --check-only", ["--check-only"]),
    "model-sync-dry-run": ("python src/main.py model-sync --dry-run", ["--dry-run"]),
}

THEMES = {
    "light": dict(bg="#f4f5f7", win="#ffffff", bar="#e6e8ec", fg="#1f2328", dim="#6a737d",
                  ok="#1a7f37", bad="#cf222e", warn="#9a6700", bd="#d0d7de"),
    "dark": dict(bg="#0d1117", win="#161b22", bar="#21262d", fg="#e6edf3", dim="#8b949e",
                 ok="#3fb950", bad="#f85149", warn="#d29922", bd="#30363d"),
}

TIMESTAMP = re.compile(r"^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2},\d{3} - ")
RATE = re.compile(r"\s+\(?[\d.]+/s\)?")


def run_scene(argv: list[str], config_path: str) -> str:
    env = dict(os.environ, PYTHONUNBUFFERED="1")
    proc = subprocess.run(
        [str(CLI_PYTHON), "src/main.py", "-c", config_path, "-l", os.devnull, "model-sync", *argv],
        cwd=ROOT, env=env, text=True,
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT, check=False,
    )
    if "Traceback" in proc.stdout:
        sys.exit("the CLI crashed; run `make venv` first:\n" + proc.stdout)
    out: list[str] = []
    for ln in proc.stdout.splitlines():
        ln = TIMESTAMP.sub("", ln).replace(config_path, "config/config.yaml")
        ln = RATE.sub("", ln)
        if ln.strip() or (out and out[-1].strip()):  # collapse runs of blank lines
            out.append(ln)
    return "\n".join(out).strip("\n")


def colour(line: str) -> str:
    esc = html.escape(line)
    if line.lstrip().startswith(("✅", "✓")):
        return f'<span class="ok">{esc}</span>'
    if line.startswith(("ERROR - ", "❌")):
        return f'<span class="bad">{esc}</span>'
    if "[DRY-RUN]" in line or line.startswith("WARNING - "):
        return f'<span class="warn">{esc}</span>'
    if line.startswith("INFO - "):
        return f'<span class="dim">{esc}</span>'
    return esc


def page(theme: str, command: str, output: str) -> str:
    t = THEMES[theme]
    body = "\n".join(colour(ln) for ln in output.splitlines())
    return f"""<!doctype html><meta charset="utf-8"><style>
body{{margin:0;background:{t['bg']};padding:28px;width:max-content}}
.win{{background:{t['win']};border:1px solid {t['bd']};border-radius:10px;overflow:hidden;
  box-shadow:0 8px 24px rgba(0,0,0,.18)}}
.bar{{background:{t['bar']};padding:10px 14px;display:flex;gap:7px;align-items:center;
  border-bottom:1px solid {t['bd']}}}
.dot{{width:11px;height:11px;border-radius:50%;background:{t['dim']};opacity:.55}}
.title{{margin-left:10px;color:{t['dim']};font:12px -apple-system,Helvetica,Arial,sans-serif}}
pre{{margin:0;padding:16px 18px;color:{t['fg']};font:12.5px/1.5 ui-monospace,Menlo,Consolas,monospace;
  white-space:pre-wrap;word-break:break-all;width:1010px}}
.dim{{color:{t['dim']}}}.ok{{color:{t['ok']}}}.bad{{color:{t['bad']}}}.warn{{color:{t['warn']}}}
.cmd{{color:{t['fg']};font-weight:600}}
</style><div class="win"><div class="bar"><span class="dot"></span><span class="dot"></span>
<span class="dot"></span><span class="title">Terminal: demo data, mock Jamf Pro and Snipe-IT</span></div>
<pre><span class="cmd">$ {html.escape(command)}</span>
{body}</pre></div>"""


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    servers = [mock_services.serve(mock_services.JamfHandler, JAMF_PORT),
               mock_services.serve(mock_services.SnipeHandler, SNIPE_PORT)]
    for s in servers:
        threading.Thread(target=s.serve_forever, daemon=True).start()
    try:
        with tempfile.TemporaryDirectory() as td:
            cfg = Path(td) / "config.yaml"
            cfg.write_text(CONFIG)
            captured = {name: run_scene(argv, str(cfg)) for name, (_, argv) in SCENES.items()}
    finally:
        for s in servers:
            s.shutdown()
    with sync_playwright() as p:
        browser = p.chromium.launch()
        for name, (command, _) in SCENES.items():
            for theme in THEMES:
                pg = browser.new_page(device_scale_factor=2)
                pg.set_content(page(theme, command, captured[name]))
                target = OUT / f"{name}-{theme}.png"
                pg.locator("body").screenshot(path=str(target))
                pg.close()
                with Image.open(target) as im:  # re-save without any metadata
                    clean = Image.frombytes(im.mode, im.size, im.tobytes())
                    clean.save(target, optimize=True)
                print("wrote", target.relative_to(ROOT))
        browser.close()


if __name__ == "__main__":
    main()
