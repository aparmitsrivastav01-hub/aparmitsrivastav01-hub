#!/usr/bin/env python3
"""Render standalone animated SVG cards. STATIC=1 produces final-frame SVGs."""
import base64, json, os, subprocess
from pathlib import Path
from collections import defaultdict

ROOT = Path(__file__).resolve().parents[1]
CFG = json.loads((ROOT / "profile.json").read_text(encoding="utf-8"))
COL = CFG["colors"]
OUT = ROOT / "cards"
OUT.mkdir(exist_ok=True)
STATIC = os.getenv("STATIC") == "1"

def esc(s):
    return str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")

def font_css():
    path = os.getenv("FONT_FILE")
    if not path or not Path(path).exists():
        return ""
    target = OUT / "font.woff"
    try:
        subprocess.run(["pyftsubset", path, "--output-file=" + str(target),
                        "--flavor=woff", "--unicodes=U+0000-00FF",
                        "--layout-features=*", "--name-IDs=0,1,2,4,6"],
                       check=True, capture_output=True)
        encoded = base64.b64encode(target.read_bytes()).decode("ascii")
        target.unlink()
        return "@font-face{font-family:ProfileFont;src:url(data:font/woff;base64," + encoded + ") format('woff')}"
    except (OSError, subprocess.CalledProcessError):
        return ""

def svg(title, height, body, delay=0):
    animation = ""
    if not STATIC:
        animation = (
            "<style>@keyframes enter{from{opacity:0;transform:translateY(12px)}}"
            "to{opacity:1;transform:translateY(0)}}"
            f".reveal{{opacity:0;animation:enter 0.9s cubic-bezier(.2,.8,.2,1) {delay}s both}}"
            "@media(prefers-reduced-motion:reduce){.reveal{animation:none!important;"
            "opacity:1!important;transform:none!important}animate,animateTransform{display:none}}</style>"
        )
    family = "ProfileFont,'Instrument Serif','Playfair Display',Georgia,serif" if font_css() else "'Playfair Display',Georgia,serif"
    mono_family = "ProfileFont,'JetBrains Mono','SF Mono',Consolas,monospace" if font_css() else "'JetBrains Mono','SF Mono',Consolas,monospace"
    body_family = "ProfileFont,'Inter Tight',Inter,ui-sans-serif,system-ui,sans-serif" if font_css() else "'Inter Tight',Inter,ui-sans-serif,system-ui,sans-serif"
    font_css_content = font_css()
    css_classes = font_css_content + " .serif{font-family:" + family + "}.mono{font-family:" + mono_family + "}.sans{font-family:" + body_family + "}"
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" '
        f'width="1000" height="{height}" viewBox="0 0 1000 {height}" role="img" aria-label="{esc(title)}">'
        f'<style>{css_classes}</style>{animation}'
        f'<rect x="1" y="1" width="998" height="{height-2}" rx="20" fill="{COL["bg"]}" stroke="{COL["line"]}" stroke-width="0.5"/>'
        f'{body}</svg>'
    )

def write(name, text):
    (OUT / name).write_text(text, encoding="utf-8")

def days_data():
    p = ROOT / "data/contributions.json"
    if not p.exists():
        return []
    try:
        return json.loads(p.read_text(encoding="utf-8")).get("contributions", [])
    except (OSError, ValueError):
        return []

def render():
    # Hero card - typographic composition matching aparmit.xyz
    hero = (
        f'<g class="reveal">'
        f'<text x="70" y="75" fill="{COL["text"]}" font-size="72" class="serif" font-weight="400" letter-spacing="-1">I build</text>'
        f'<text x="70" y="145" fill="{COL["text"]}" font-size="72" class="serif" font-weight="400" letter-spacing="-1">things that</text>'
        f'<text x="70" y="215" fill="{COL["text"]}" font-size="72" class="serif" font-style="italic" font-weight="400" letter-spacing="-1">think.</text>'
        f'<line x1="70" y1="240" x2="930" y2="240" stroke="{COL["line"]}" stroke-width="0.5"/>'
        f'<text x="70" y="270" fill="{COL["muted"]}" font-size="13" class="sans" letter-spacing="0.3">{esc(CFG["bio"])}</text>'
        f'<text x="930" y="270" fill="{COL["text"]}" font-size="11" class="mono" text-anchor="end" opacity="0.6">{esc(CFG["location"].upper())}</text></g>'
    )
    write("hero.svg", svg("Aparmit Srivastav", 300, hero))

    # Three linked tiles - editorial minimal design with monospace labels
    for i, project in enumerate(CFG["projects"], 1):
        body = (
            f'<g class="reveal">'
            f'<line x1="50" y1="40" x2="950" y2="40" stroke="{COL["line"]}" stroke-width="0.5"/>'
            f'<text x="50" y="70" fill="{COL["text"]}" font-size="10" class="mono" letter-spacing="1.5" opacity="0.5">{esc(project["label"])}</text>'
            f'<text x="50" y="110" fill="{COL["text"]}" font-size="36" class="serif" font-weight="400">{esc(project["name"])}</text>'
            f'<text x="50" y="140" fill="{COL["muted"]}" font-size="13" class="sans" letter-spacing="0.2">{esc(project["description"][:80])}</text>'
            f'<text x="940" y="110" fill="{COL["text"]}" font-size="18" class="serif" font-style="italic" text-anchor="end" opacity="0.7">→</text></g>'
        )
        write(f"tile-{i}.svg", svg(project["name"], 170, body, i * .12))

    # Contribution totals and monthly chart - neutral editorial layout
    days = days_data()
    months = defaultdict(int)
    for item in days:
        if len(str(item.get("date", ""))) >= 7:
            months[str(item["date"])[:7]] += int(item.get("count", 0))
    recent = sorted(months.items())[-12:]
    total = sum(int(x.get("count", 0)) for x in days)
    active = sum(int(x.get("count", 0)) > 0 for x in days)
    busiest = max(days, key=lambda x: int(x.get("count", 0)), default={"count": 0, "date": "N/A"})
    streak = 0
    for item in reversed(days):
        if int(item.get("count", 0)) > 0:
            streak += 1
        elif streak:
            break
    chart = (
        f'<g class="reveal">'
        f'<line x1="60" y1="45" x2="940" y2="45" stroke="{COL["line"]}" stroke-width="0.5"/>'
        f'<text x="60" y="75" fill="{COL["text"]}" font-size="10" class="mono" letter-spacing="1.5" opacity="0.5">GITHUB ACTIVITY</text>'
    )
    for x, (label, value) in zip((60, 290, 520, 750), (
        ("CONTRIBUTIONS", total), ("CURRENT STREAK", streak),
        ("ACTIVE DAYS", active), ("BUSIEST DAY", int(busiest.get("count", 0)))
    )):
        chart += (
            f'<text x="{x}" y="125" fill="{COL["text"]}" font-size="48" class="serif" font-weight="400">{value}</text>'
            f'<text x="{x}" y="150" fill="{COL["muted"]}" font-size="10" class="mono" letter-spacing="1">{label}</text>'
        )
    chart += f'<text x="750" y="170" fill="{COL["muted"]}" font-size="9" class="sans" opacity="0.5">{esc(busiest.get("date", "N/A"))}</text>'
    chart += f'<line x1="60" y1="190" x2="940" y2="190" stroke="{COL["line"]}" stroke-width="0.5"/>'
    if recent:
        maxval = max(v for _, v in recent) or 1
        for i, (month, value) in enumerate(recent):
            x = 70 + i * 72
            height = max(4, 65 * value / maxval)
            opacity = 0.15 + 0.7 * value / maxval
            chart += (
                f'<rect x="{x}" y="{275-height}" width="36" height="{height}" rx="3" fill="{COL["text"]}" opacity="{opacity:.2f}">'
                f'<animate attributeName="height" from="0" to="{height}" dur="0.7s" begin="{i*.05}s" fill="freeze" calcMode="spline" keySplines="0.2 0.8 0.2 1"/></rect>'
                f'<text x="{x+18}" y="295" text-anchor="middle" fill="{COL["muted"]}" font-size="9" class="mono" opacity="0.5">{esc(month[5:])}</text>'
            )
    else:
        chart += f'<text x="500" y="245" text-anchor="middle" fill="{COL["muted"]}" font-size="13" class="sans">Contribution data appears after the first scheduled refresh.</text>'
    chart += "</g>"
    write("monthly.svg", svg("Monthly GitHub contribution chart", 320, chart, .45))

    # Contribution heatmap - neutral shades matching editorial aesthetic
    heat = (
        f'<g class="reveal">'
        f'<line x1="60" y1="45" x2="940" y2="45" stroke="{COL["line"]}" stroke-width="0.5"/>'
        f'<text x="60" y="75" fill="{COL["text"]}" font-size="10" class="mono" letter-spacing="1.5" opacity="0.5">CONTRIBUTION GRAPH</text>'
    )
    max_count = max([int(x.get("count", 0)) for x in days] or [1]) or 1
    for i, item in enumerate(days[-364:]):
        col, row = divmod(i, 7)
        count = int(item.get("count", 0))
        opacity = 0.06 if count == 0 else min(0.85, 0.12 + 0.73 * count / max_count)
        heat += f'<rect x="{60+col*18}" y="{95+row*18}" width="14" height="14" rx="3" fill="{COL["text"]}" opacity="{opacity:.2f}"/>'
    if not days:
        heat += f'<text x="60" y="115" fill="{COL["muted"]}" font-size="12" class="sans">Waiting for first contribution-data refresh.</text>'
    heat += "</g>"
    write("heatmap.svg", svg("GitHub contribution heatmap", 220, heat, .6))

    # One featured-repository card per project - editorial minimal design
    for i, project in enumerate(CFG["projects"], 1):
        body = (
            f'<g class="reveal">'
            f'<line x1="60" y1="45" x2="940" y2="45" stroke="{COL["line"]}" stroke-width="0.5"/>'
            f'<text x="60" y="75" fill="{COL["text"]}" font-size="10" class="mono" letter-spacing="1.5" opacity="0.5">FEATURED REPOSITORY 0{i}</text>'
            f'<text x="60" y="120" fill="{COL["text"]}" font-size="40" class="serif" font-weight="400">{esc(project["name"])}</text>'
            f'<text x="60" y="155" fill="{COL["muted"]}" font-size="13" class="sans" letter-spacing="0.2">{esc(project["description"])}</text>'
            f'<text x="60" y="185" fill="{COL["text"]}" font-size="11" class="mono" letter-spacing="1" opacity="0.5">{esc(project["repo"])}</text>'
            f'<text x="930" y="120" fill="{COL["text"]}" font-size="16" class="serif" font-style="italic" text-anchor="end" opacity="0.7">→</text></g>'
        )
        write(f"repo-{i}.svg", svg(project["name"] + " repository", 220, body, .75 + i * .1))

if __name__ == "__main__":
    render()
    print("Rendered SVG cards in", OUT)
