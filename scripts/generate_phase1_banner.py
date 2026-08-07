#!/usr/bin/env python3
from __future__ import annotations

import math
import re
import urllib.request
from dataclasses import dataclass
from pathlib import Path

from PIL import Image, ImageEnhance, ImageOps, ImageFilter

REPO = Path('/home/runner/work/chandimacbbandara/chandimacbbandara')
PORTRAIT_URL = 'https://github.com/user-attachments/assets/04f145e3-b958-4228-9c6f-a4884fb8ef70'
LOGO_URLS = {
    'Python': 'https://raw.githubusercontent.com/simple-icons/simple-icons/develop/icons/python.svg',
    'Spring Boot': 'https://raw.githubusercontent.com/simple-icons/simple-icons/develop/icons/springboot.svg',
    'React Native': 'https://raw.githubusercontent.com/simple-icons/simple-icons/develop/icons/react.svg',
}


@dataclass(frozen=True)
class Theme:
    name: str
    bg: str
    terminal: str
    terminal_border: str
    titlebar: str
    title_text: str
    chrome: str
    frame: str
    portrait_dot: str
    info_label: str
    info_value: str
    muted: str
    live_red: str
    handle_bg: str
    handle_text: str
    separator: str


def fetch_bytes(url: str) -> bytes:
    req = urllib.request.Request(url, headers={'User-Agent': 'profile-banner-builder'})
    with urllib.request.urlopen(req, timeout=30) as resp:
        return resp.read()


def load_logo_paths() -> list[tuple[str, str]]:
    logos: list[tuple[str, str]] = []
    for name, url in LOGO_URLS.items():
        raw = fetch_bytes(url).decode('utf-8')
        match = re.search(r'd="([^"]+)"', raw)
        if not match:
            raise RuntimeError(f'Failed to extract path for {name} from {url}')
        logos.append((name, match.group(1)))
    return logos


def load_portrait() -> Image.Image:
    data = fetch_bytes(PORTRAIT_URL)
    return Image.open(__import__('io').BytesIO(data)).convert('RGB')


def crop_head_shoulders(img: Image.Image) -> Image.Image:
    w, h = img.size
    left = int(w * 0.19)
    top = int(h * 0.08)
    right = int(w * 0.83)
    bottom = int(h * 0.89)
    return img.crop((left, top, right, bottom))


def preprocess(img: Image.Image) -> Image.Image:
    img = crop_head_shoulders(img)
    img = ImageOps.autocontrast(img, cutoff=1)
    img = ImageEnhance.Contrast(img).enhance(1.3)
    img = img.filter(ImageFilter.UnsharpMask(radius=3, percent=140))
    img = img.resize((300, 340), Image.Resampling.LANCZOS)
    return img.convert('L')


def floyd_steinberg_serpentine(gray: Image.Image) -> list[list[int]]:
    w, h = gray.size
    arr = [[float(gray.getpixel((x, y))) for x in range(w)] for y in range(h)]
    out = [[0 for _ in range(w)] for _ in range(h)]

    for y in range(h):
        left_to_right = y % 2 == 0
        x_range = range(w) if left_to_right else range(w - 1, -1, -1)

        for x in x_range:
            old = arr[y][x]
            new = 0.0 if old < 128 else 255.0
            out[y][x] = 1 if new == 0 else 0
            err = old - new

            if left_to_right:
                neighbors = [
                    (x + 1, y, 7 / 16),
                    (x - 1, y + 1, 3 / 16),
                    (x, y + 1, 5 / 16),
                    (x + 1, y + 1, 1 / 16),
                ]
            else:
                neighbors = [
                    (x - 1, y, 7 / 16),
                    (x + 1, y + 1, 3 / 16),
                    (x, y + 1, 5 / 16),
                    (x - 1, y + 1, 1 / 16),
                ]

            for nx, ny, weight in neighbors:
                if 0 <= nx < w and 0 <= ny < h:
                    arr[ny][nx] += err * weight

    return out


def make_dot_layer(bits: list[list[int]], x0: float, y0: float, step: float, radius: float, color: str) -> str:
    circles: list[str] = []
    for y, row in enumerate(bits):
        cy = y0 + y * step
        for x, black in enumerate(row):
            if black:
                cx = x0 + x * step
                circles.append(f'<circle cx="{cx:.2f}" cy="{cy:.2f}" r="{radius:.2f}" fill="{color}"/>')
    return ''.join(circles)


def dotted_line(label: str, value: str, y: int, theme: Theme) -> str:
    return (
        f'<text x="540" y="{y}" fill="{theme.info_label}" font-size="17" font-family="\'JetBrains Mono\',monospace">{label}</text>'
        f'<line x1="710" y1="{y-5}" x2="860" y2="{y-5}" stroke="{theme.separator}" stroke-width="2" stroke-dasharray="2 7"/>'
        f'<text x="880" y="{y}" fill="{theme.info_value}" font-size="17" font-family="\'JetBrains Mono\',monospace">{value}</text>'
    )


def logo_group(logo_paths: list[tuple[str, str]], theme: Theme) -> str:
    groups = []
    for i, (name, path_d) in enumerate(logo_paths):
        begin_a = f'{5 * i}s;cycle.end+{5 * i}s'
        begin_b = f'{5 * i + 4}s;cycle.end+{5 * i + 4}s'
        groups.append(
            f'''<g opacity="0">
  <animate attributeName="opacity" values="0;1;1;0" keyTimes="0;0.1;0.8;1" dur="5s" begin="{begin_a}" fill="freeze"/>
  <animate attributeName="opacity" values="0" dur="0.01s" begin="{begin_b}" fill="freeze"/>
  <g transform="translate(980 155) scale(4.8)">
    <path d="{path_d}" fill="{theme.chrome}"/>
  </g>
  <text x="944" y="258" fill="{theme.muted}" font-size="13" font-family="'JetBrains Mono',monospace">{name}</text>
</g>'''
        )
    groups.append('<animate id="cycle" attributeName="opacity" from="1" to="1" dur="15s" begin="0s" repeatCount="indefinite"/>')
    return ''.join(groups)


def build_svg(theme: Theme, dots: str, logo_paths: list[tuple[str, str]]) -> str:
    info_rows = [
        ('NAME', 'Chandima Bandara'),
        ('ROLE', 'Full-Stack Developer + AI/ML Engineer'),
        ('STATUS', 'Building + Learning + Shipping'),
        ('LOCATION', 'Kurunagala, Sri Lanka'),
        ('EDUCATION', 'BSc (Hons) IT, Data Science @ SLIIT'),
        ('TOOLCHAIN', 'Git · Postman · VS Code'),
        ('STACK', 'React Native · Spring Boot · Node.js · MySQL'),
    ]
    info = ''.join(dotted_line(label, value, 330 + i * 34, theme) for i, (label, value) in enumerate(info_rows))

    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="1180" height="610" viewBox="0 0 1180 610">
<defs>
  <clipPath id="termClip"><rect x="18" y="18" width="1144" height="574" rx="16"/></clipPath>
  <clipPath id="portraitClip"><rect x="60" y="130" width="390" height="432" rx="12"/></clipPath>
</defs>
<rect width="1180" height="610" fill="{theme.bg}"/>
<rect x="18" y="18" width="1144" height="574" rx="16" fill="{theme.terminal}" stroke="{theme.terminal_border}" stroke-width="2"/>
<rect x="18" y="18" width="1144" height="44" rx="16" fill="{theme.titlebar}"/>
<circle cx="44" cy="40" r="7" fill="#ef4444"/>
<circle cx="68" cy="40" r="7" fill="#f59e0b"/>
<circle cx="92" cy="40" r="7" fill="#22c55e"/>
<text x="590" y="45" text-anchor="middle" fill="{theme.title_text}" font-size="18" font-family="'JetBrains Mono',monospace">profile.sh --live</text>
<g clip-path="url(#termClip)">
  <rect x="45" y="90" width="420" height="490" rx="14" fill="none" stroke="{theme.frame}" stroke-width="2"/>
  <text x="60" y="116" fill="{theme.chrome}" font-size="16" font-family="'JetBrains Mono',monospace">VISUAL.MAP</text>
  <rect x="60" y="130" width="390" height="432" rx="12" fill="none" stroke="{theme.frame}" stroke-width="1.6"/>
  <g clip-path="url(#portraitClip)">{dots}</g>
  <text x="540" y="116" fill="{theme.chrome}" font-size="16" font-family="'JetBrains Mono',monospace">SYSTEM.INFO</text>
  <rect x="540" y="130" width="590" height="160" rx="10" fill="none" stroke="{theme.frame}" stroke-width="1.6"/>
  <rect x="562" y="152" width="92" height="30" rx="15" fill="{theme.live_red}">
    <animate attributeName="opacity" values="0.4;1;0.4" dur="1.2s" repeatCount="indefinite"/>
  </rect>
  <text x="608" y="172" text-anchor="middle" fill="#ffffff" font-size="14" font-family="'JetBrains Mono',monospace" font-weight="700">LIVE</text>
  <rect x="675" y="152" width="310" height="30" rx="15" fill="{theme.handle_bg}"/>
  <text x="830" y="172" text-anchor="middle" fill="{theme.handle_text}" font-size="14" font-family="'JetBrains Mono',monospace">@chandimacbbandara</text>
  <text x="562" y="215" fill="{theme.muted}" font-size="14" font-family="'JetBrains Mono',monospace">Morph cycle: Python → Spring Boot → React Native</text>
  {logo_group(logo_paths, theme)}
  {info}
</g>
</svg>'''


def main() -> None:
    portrait = preprocess(load_portrait())
    bits = floyd_steinberg_serpentine(portrait)
    logos = load_logo_paths()

    themes = [
        Theme(
            name='dark',
            bg='#0A101F',
            terminal='#0f172a',
            terminal_border='#1e293b',
            titlebar='#111827',
            title_text='#cbd5e1',
            chrome='#22D3EE',
            frame='#155e75',
            portrait_dot='#A78BFA',
            info_label='#67e8f9',
            info_value='#e2e8f0',
            muted='#94a3b8',
            live_red='#ef4444',
            handle_bg='#0f766e',
            handle_text='#ccfbf1',
            separator='#164e63',
        ),
        Theme(
            name='light',
            bg='#f8f7ff',
            terminal='#ffffff',
            terminal_border='#dbeafe',
            titlebar='#eef2ff',
            title_text='#334155',
            chrome='#0891B2',
            frame='#cbd5e1',
            portrait_dot='#7C3AED',
            info_label='#0f766e',
            info_value='#0f172a',
            muted='#64748b',
            live_red='#dc2626',
            handle_bg='#cffafe',
            handle_text='#0e7490',
            separator='#bae6fd',
        ),
    ]

    for theme in themes:
        dots = make_dot_layer(bits, x0=68.0, y0=138.0, step=1.28, radius=0.46, color=theme.portrait_dot)
        svg = build_svg(theme, dots, logos)
        (REPO / f'{theme.name}.svg').write_text(svg, encoding='utf-8')


if __name__ == '__main__':
    main()
