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
            "<style>@keyframes enter{from{opacity:0;transform:translateY(16px)}"
            "to{opacity:1;transform:translateY(0)}}"
            f".reveal{{opacity:0;animation:enter .8s cubic-bezier(.2,.7,.2,1) {delay}s both}}"
            "@media(prefers-reduced-motion:reduce){.reveal{animation:none!important;"
            "opacity:1!important;transform:none!important}animate,animateTransform{display:none}}</style>"
        )
    family = "ProfileFont,Inter,ui-sans-serif,system-ui,sans-serif" if font_css() else "Inter,ui-sans-serif,system-ui,sans-serif"
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" '
        f'width="1000" height="{height}" viewBox="0 0 1000 {height}" role="img" aria-label="{esc(title)}">'
        f'<style>{font_css()} text{{font-family:{family}}}</style>{animation}'
        f'<rect x="1" y="1" width="998" height="{height-2}" rx="22" fill="{COL["bg"]}" stroke="{COL["line"]}"/>'
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
    # Hero card
    avatar = CFG.get("avatar", "")
    portrait = ""
    if avatar:
        portrait = (
            f'<circle cx="880" cy="112" r="62" fill="{COL["panel"]}" stroke="{COL["accent"]}" stroke-width="2"/>'
            f'<image x="820" y="52" width="120" height="120" preserveAspectRatio="xMidYMid slice" '
            f'clip-path="url(#portrait)" xlink:href="{esc(avatar)}"/>'
        )
    hero = (
        '<defs><clipPath id="portrait"><circle cx="880" cy="112" r="60"/></clipPath></defs>'
        f'<g class="reveal"><rect x="28" y="24" width="944" height="194" rx="18" fill="{COL["panel"]}"/>'
        f'<text x="62" y="62" fill="{COL["accent"]}" font-size="13" letter-spacing="4">LUCKNOW, INDIA · IIT MADRAS</text>'
        f'<text x="62" y="119" fill="{COL["text"]}" font-size="46" font-weight="700">{esc(CFG["name"])}</text>'
        f'<text x="62" y="158" fill="{COL["text"]}" font-size="21">{esc(CFG["tagline"])}</text>'
        f'<text x="62" y="190" fill="{COL["muted"]}" font-size="14">{esc(CFG["bio"])}</text>{portrait}</g>'
    )
    write("hero.svg", svg("Aparmit Srivastav", 242, hero))

    # Three linked tiles (each embedded at 32.5% in README)
    for i, project in enumerate(CFG["projects"], 1):
        body = (
            f'<g class="reveal"><rect x="12" y="12" width="976" height="156" rx="16" fill="{COL["panel"]}" stroke="{COL["line"]}"/>'
            f'<text x="38" y="48" fill="{COL["accent"]}" font-size="11" letter-spacing="2">{esc(project["label"])}</text>'
            f'<text x="38" y="91" fill="{COL["text"]}" font-size="29" font-weight="700">{esc(project["name"])}</text>'
            f'<text x="38" y="124" fill="{COL["muted"]}" font-size="14">{esc(project["description"][:90])}</text>'
            f'<text x="944" y="92" fill="{COL["accent"]}" font-size="24" text-anchor="end">↗</text></g>'
        )
        write(f"tile-{i}.svg", svg(project["name"], 180, body, i * .12))

    # Contribution totals and monthly chart
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
        f'<g class="reveal"><text x="42" y="42" fill="{COL["accent"]}" font-size="13" letter-spacing="3">GITHUB ACTIVITY · LAST 12 MONTHS</text>'
    )
    for x, (label, value) in zip((48, 285, 522, 759), (
        ("CONTRIBUTIONS", total), ("CURRENT STREAK", streak),
        ("ACTIVE DAYS", active), ("BUSIEST DAY", int(busiest.get("count", 0)))
    )):
        chart += (
            f'<text x="{x}" y="96" fill="{COL["text"]}" font-size="34" font-weight="700">{value}</text>'
            f'<text x="{x}" y="119" fill="{COL["muted"]}" font-size="11">{label}</text>'
        )
    chart += f'<text x="759" y="141" fill="{COL["muted"]}" font-size="10">{esc(busiest.get("date", "N/A"))}</text>'
    chart += f'<line x1="42" y1="158" x2="958" y2="158" stroke="{COL["line"]}"/>'
    if recent:
        maxval = max(v for _, v in recent) or 1
        for i, (month, value) in enumerate(recent):
            x = 55 + i * 76
            height = max(3, 70 * value / maxval)
            chart += (
                f'<rect x="{x}" y="{245-height}" width="38" height="{height}" rx="5" fill="{COL["accent"]}">'
                f'<animate attributeName="height" from="0" to="{height}" dur=".7s" begin="{i*.055}s" fill="freeze"/></rect>'
                f'<text x="{x+19}" y="266" text-anchor="middle" fill="{COL["muted"]}" font-size="10">{esc(month[5:])}</text>'
            )
    else:
        chart += f'<text x="500" y="215" text-anchor="middle" fill="{COL["muted"]}" font-size="15">Contribution data appears after the first scheduled refresh.</text>'
    chart += "</g>"
    write("monthly.svg", svg("Monthly GitHub contribution chart", 285, chart, .48))

    # Brand-colour contribution heatmap
    heat = f'<g class="reveal"><text x="42" y="42" fill="{COL["accent"]}" font-size="13" letter-spacing="3">CONTRIBUTION GRAPH</text>'
    max_count = max([int(x.get("count", 0)) for x in days] or [1]) or 1
    for i, item in enumerate(days[-364:]):
        col, row = divmod(i, 7)
        count = int(item.get("count", 0))
        opacity = .10 if count == 0 else min(.95, .20 + .75 * count / max_count)
        heat += f'<rect x="{42+col*17}" y="{70+row*17}" width="12" height="12" rx="3" fill="{COL["accent"]}" opacity="{opacity:.2f}"/>'
    if not days:
        heat += f'<text x="42" y="88" fill="{COL["muted"]}" font-size="14">Waiting for first contribution-data refresh.</text>'
    heat += "</g>"
    write("heatmap.svg", svg("GitHub contribution heatmap", 205, heat, .62))

    # One featured-repository card per project
    for i, project in enumerate(CFG["projects"], 1):
        body = (
            f'<g class="reveal"><rect x="26" y="22" width="948" height="176" rx="18" fill="{COL["panel"]}" stroke="{COL["line"]}"/>'
            f'<text x="56" y="59" fill="{COL["accent"]}" font-size="12" letter-spacing="3">FEATURED REPOSITORY 0{i}</text>'
            f'<text x="56" y="106" fill="{COL["text"]}" font-size="34" font-weight="700">{esc(project["name"])}</text>'
            f'<text x="56" y="141" fill="{COL["muted"]}" font-size="15">{esc(project["description"])}</text>'
            f'<text x="56" y="176" fill="{COL["accent"]}" font-size="12">{esc(project["repo"])}</text>'
            f'<text x="930" y="108" fill="{COL["accent"]}" font-size="19" text-anchor="end">OPEN ↗</text></g>'
        )
        write(f"repo-{i}.svg", svg(project["name"] + " repository", 220, body, .76 + i * .13))

if __name__ == "__main__":
    render()
    print("Rendered SVG cards in", OUT)
