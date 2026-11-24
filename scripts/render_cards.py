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
            "<style>@keyframes enter{from{opacity:0;transform:translateY(20px)}"
            "to{opacity:1;transform:translateY(0)}}"
            f".reveal{{opacity:0;animation:enter 1s cubic-bezier(.16,1,.3,1) {delay}s both}}"
            "@media(prefers-reduced-motion:reduce){.reveal{animation:none!important;"
            "opacity:1!important;transform:none!important}animate,animateTransform{display:none}}</style>"
        )
    family = "ProfileFont,'Instrument Serif','Playfair Display',Georgia,serif" if font_css() else "'Playfair Display',Georgia,serif"
    body_family = "ProfileFont,'Inter Tight',Inter,ui-sans-serif,system-ui,sans-serif" if font_css() else "'Inter Tight',Inter,ui-sans-serif,system-ui,sans-serif"
    font_css_content = font_css()
    css_classes = font_css_content + " .serif{font-family:" + family + "}.sans{font-family:" + body_family + "}"
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" '
        f'width="1000" height="{height}" viewBox="0 0 1000 {height}" role="img" aria-label="{esc(title)}">'
        f'<style>{css_classes}</style>{animation}'
        f'<rect x="1" y="1" width="998" height="{height-2}" rx="24" fill="{COL["bg"]}" stroke="{COL["line"]}" stroke-width="1"/>'
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
    # Hero card - editorial design with oversized serif typography
    avatar = CFG.get("avatar", "")
    portrait = ""
    if avatar:
        portrait = (
            f'<circle cx="860" cy="100" r="56" fill="{COL["panel"]}" stroke="{COL["accent"]}" stroke-width="1.5"/>'
            f'<image x="806" y="46" width="108" height="108" preserveAspectRatio="xMidYMid slice" '
            f'clip-path="url(#portrait)" xlink:href="{esc(avatar)}"/>'
        )
    hero = (
        '<defs><clipPath id="portrait"><circle cx="860" cy="100" r="54"/></clipPath></defs>'
        f'<g class="reveal">'
        f'<line x1="60" y1="50" x2="940" y2="50" stroke="{COL["line"]}" stroke-width="1"/>'
        f'<text x="60" y="85" fill="{COL["accent"]}" font-size="11" class="sans" letter-spacing="3" opacity="0.8">{esc(CFG["location"].upper())}</text>'
        f'<text x="60" y="145" fill="{COL["text"]}" font-size="58" class="serif" font-weight="400">{esc(CFG["name"])}</text>'
        f'<text x="60" y="185" fill="{COL["text"]}" font-size="26" class="serif" font-style="italic" opacity="0.9">{esc(CFG["tagline"])}</text>'
        f'<text x="60" y="225" fill="{COL["muted"]}" font-size="14" class="sans" letter-spacing="0.5">{esc(CFG["bio"])}</text>'
        f'{portrait}</g>'
    )
    write("hero.svg", svg("Aparmit Srivastav", 260, hero))

    # Three linked tiles (each embedded at 32.5% in README) - editorial minimal design
    for i, project in enumerate(CFG["projects"], 1):
        body = (
            f'<g class="reveal">'
            f'<line x1="40" y1="45" x2="960" y2="45" stroke="{COL["line"]}" stroke-width="1"/>'
            f'<text x="40" y="75" fill="{COL["accent"]}" font-size="10" class="sans" letter-spacing="2.5" opacity="0.7">{esc(project["label"])}</text>'
            f'<text x="40" y="115" fill="{COL["text"]}" font-size="32" class="serif" font-weight="400">{esc(project["name"])}</text>'
            f'<text x="40" y="145" fill="{COL["muted"]}" font-size="13" class="sans" letter-spacing="0.3">{esc(project["description"][:85])}</text>'
            f'<text x="950" y="115" fill="{COL["accent"]}" font-size="20" class="serif" font-style="italic" text-anchor="end">→</text></g>'
        )
        write(f"tile-{i}.svg", svg(project["name"], 170, body, i * .15))

    # Contribution totals and monthly chart - editorial layout
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
        f'<line x1="60" y1="50" x2="940" y2="50" stroke="{COL["line"]}" stroke-width="1"/>'
        f'<text x="60" y="80" fill="{COL["accent"]}" font-size="11" class="sans" letter-spacing="2.5" opacity="0.7">GITHUB ACTIVITY</text>'
    )
    for x, (label, value) in zip((60, 290, 520, 750), (
        ("CONTRIBUTIONS", total), ("CURRENT STREAK", streak),
        ("ACTIVE DAYS", active), ("BUSIEST DAY", int(busiest.get("count", 0)))
    )):
        chart += (
            f'<text x="{x}" y="130" fill="{COL["text"]}" font-size="42" class="serif" font-weight="400">{value}</text>'
            f'<text x="{x}" y="155" fill="{COL["muted"]}" font-size="11" class="sans" letter-spacing="1">{label}</text>'
        )
    chart += f'<text x="750" y="175" fill="{COL["muted"]}" font-size="10" class="sans" opacity="0.6">{esc(busiest.get("date", "N/A"))}</text>'
    chart += f'<line x1="60" y1="195" x2="940" y2="195" stroke="{COL["line"]}" stroke-width="1"/>'
    if recent:
        maxval = max(v for _, v in recent) or 1
        for i, (month, value) in enumerate(recent):
            x = 70 + i * 72
            height = max(4, 65 * value / maxval)
            chart += (
                f'<rect x="{x}" y="{280-height}" width="36" height="{height}" rx="4" fill="{COL["accent"]}" opacity="0.85">'
                f'<animate attributeName="height" from="0" to="{height}" dur="0.8s" begin="{i*.06}s" fill="freeze" calcMode="spline" keySplines="0.16 1 0.3 1"/></rect>'
                f'<text x="{x+18}" y="300" text-anchor="middle" fill="{COL["muted"]}" font-size="10" class="sans" opacity="0.6">{esc(month[5:])}</text>'
            )
    else:
        chart += f'<text x="500" y="250" text-anchor="middle" fill="{COL["muted"]}" font-size="14" class="sans">Contribution data appears after the first scheduled refresh.</text>'
    chart += "</g>"
    write("monthly.svg", svg("Monthly GitHub contribution chart", 320, chart, .5))

    # Brand-colour contribution heatmap - editorial minimal design
    heat = (
        f'<g class="reveal">'
        f'<line x1="60" y1="50" x2="940" y2="50" stroke="{COL["line"]}" stroke-width="1"/>'
        f'<text x="60" y="80" fill="{COL["accent"]}" font-size="11" class="sans" letter-spacing="2.5" opacity="0.7">CONTRIBUTION GRAPH</text>'
    )
    max_count = max([int(x.get("count", 0)) for x in days] or [1]) or 1
    for i, item in enumerate(days[-364:]):
        col, row = divmod(i, 7)
        count = int(item.get("count", 0))
        opacity = .08 if count == 0 else min(.90, .15 + .75 * count / max_count)
        heat += f'<rect x="{60+col*18}" y="{100+row*18}" width="14" height="14" rx="3" fill="{COL["accent"]}" opacity="{opacity:.2f}"/>'
    if not days:
        heat += f'<text x="60" y="120" fill="{COL["muted"]}" font-size="13" class="sans">Waiting for first contribution-data refresh.</text>'
    heat += "</g>"
    write("heatmap.svg", svg("GitHub contribution heatmap", 220, heat, .65))

    # One featured-repository card per project - editorial minimal design
    for i, project in enumerate(CFG["projects"], 1):
        body = (
            f'<g class="reveal">'
            f'<line x1="60" y1="50" x2="940" y2="50" stroke="{COL["line"]}" stroke-width="1"/>'
            f'<text x="60" y="80" fill="{COL["accent"]}" font-size="11" class="sans" letter-spacing="2.5" opacity="0.7">FEATURED REPOSITORY 0{i}</text>'
            f'<text x="60" y="125" fill="{COL["text"]}" font-size="38" class="serif" font-weight="400">{esc(project["name"])}</text>'
            f'<text x="60" y="160" fill="{COL["muted"]}" font-size="14" class="sans" letter-spacing="0.3">{esc(project["description"])}</text>'
            f'<text x="60" y="190" fill="{COL["accent"]}" font-size="12" class="sans" letter-spacing="1" opacity="0.8">{esc(project["repo"])}</text>'
            f'<text x="930" y="125" fill="{COL["accent"]}" font-size="18" class="serif" font-style="italic" text-anchor="end">→</text></g>'
        )
        write(f"repo-{i}.svg", svg(project["name"] + " repository", 220, body, .8 + i * .12))

if __name__ == "__main__":
    render()
    print("Rendered SVG cards in", OUT)
