"""Flat illustration PNGs for the presentation (Pillow-drawn, royalty-free)."""

from __future__ import annotations

import math
import textwrap
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont, ImageOps

# Inner viewport for title-slide phone frames (portrait)
PHONE_INNER = (352, 740)

# CloudMLOps design tokens (from frontend/src/index.css)
C_BG = (8, 11, 22)
C_SURFACE = (19, 26, 46)
C_SURFACE2 = (24, 33, 64)
C_BORDER = (35, 45, 77)
C_TEXT = (238, 242, 255)
C_MUTED = (152, 163, 199)
C_BRAND = (99, 102, 241)
C_BRAND_DARK = (79, 70, 229)
C_ACCENT = (34, 211, 238)
C_SUCCESS = (52, 211, 153)

PIPELINE = (
    "Upload PDF, DOCX, or TXT — or paste text",
    "FastAPI extracts text and picks a strategy",
    "FLAN-T5 / extractive summary on AWS",
    "PostgreSQL stores history, search, and ratings",
)
STACK = ("React", "FastAPI", "PostgreSQL", "FLAN-T5", "Docker", "AWS")

OUT = Path(__file__).resolve().parents[1] / "docs" / "presentation_assets" / "illustrations"
SIZE = 640


def _new_canvas(bg=(244, 247, 251)) -> Image.Image:
    img = Image.new("RGBA", (SIZE, SIZE), bg + (255,))
    return img


def thinking() -> None:
    img = _new_canvas()
    d = ImageDraw.Draw(img)
    d.ellipse((180, 220, 420, 460), fill=(79, 70, 229, 255))
    d.ellipse((150, 180, 330, 360), fill=(6, 182, 212, 255))
    d.ellipse((320, 90, 470, 240), fill=(255, 255, 255, 255), outline=(226, 232, 240), width=4)
    d.ellipse((400, 40, 520, 160), fill=(255, 255, 255, 255), outline=(226, 232, 240), width=4)
    d.ellipse((480, 10, 560, 90), fill=(255, 255, 255, 255), outline=(226, 232, 240), width=4)
    d.rounded_rectangle((250, 480, 390, 530), radius=20, fill=(15, 23, 42, 255))
    d.text((270, 495), "Ideas", fill=(255, 255, 255, 255))
    img.save(OUT / "thinking.png")


def cloud_deploy() -> None:
    img = _new_canvas()
    d = ImageDraw.Draw(img)
    d.ellipse((120, 200, 280, 320), fill=(14, 165, 233, 255))
    d.ellipse((220, 170, 420, 330), fill=(14, 165, 233, 255))
    d.ellipse((360, 210, 520, 340), fill=(14, 165, 233, 255))
    d.rounded_rectangle((230, 340, 410, 470), radius=18, fill=(79, 70, 229, 255))
    d.text((265, 385), "AWS", fill=(255, 255, 255, 255))
    d.line((320, 470, 320, 530), fill=(100, 116, 139), width=6)
    d.rounded_rectangle((260, 530, 380, 590), radius=12, fill=(16, 185, 129, 255))
    img.save(OUT / "cloud.png")


def ai_brain() -> None:
    img = _new_canvas()
    d = ImageDraw.Draw(img)
    d.ellipse((170, 140, 470, 440), fill=(244, 63, 94, 240))
    d.ellipse((210, 180, 430, 400), fill=(255, 255, 255, 255))
    for x, y in ((260, 240), (340, 220), (380, 300), (280, 340), (360, 360)):
        d.ellipse((x, y, x + 40, y + 40), fill=(13, 148, 136, 255))
    d.text((250, 470), "FLAN-T5 + Extractive", fill=(30, 41, 59, 255))
    img.save(OUT / "ai_brain.png")


def documents() -> None:
    img = _new_canvas()
    d = ImageDraw.Draw(img)
    for i, col in enumerate(((124, 58, 237), (6, 182, 212), (245, 158, 11))):
        x = 160 + i * 70
        d.rounded_rectangle((x, 180 + i * 20, x + 180, 480 + i * 20), radius=16, fill=col + (255,))
        d.line((x + 30, 240 + i * 20, x + 140, 240 + i * 20), fill=(255, 255, 255), width=4)
        d.line((x + 30, 280 + i * 20, x + 120, 280 + i * 20), fill=(255, 255, 255), width=4)
    d.text((200, 520), "PDF  DOCX  TXT", fill=(30, 41, 59, 255))
    img.save(OUT / "documents.png")


def teamwork() -> None:
    img = _new_canvas()
    d = ImageDraw.Draw(img)
    for x, c in ((200, (79, 70, 229)), (320, (6, 182, 212)), (440, (16, 185, 129))):
        d.ellipse((x, 260, x + 100, 360), fill=c + (255,))
        d.rectangle((x + 20, 360, x + 80, 480), fill=c + (255,))
    d.rounded_rectangle((160, 500, 480, 560), radius=20, fill=(15, 23, 42, 255))
    d.text((210, 518), "User  Admin  DevOps", fill=(255, 255, 255, 255))
    img.save(OUT / "teamwork.png")


def rocket() -> None:
    img = _new_canvas()
    d = ImageDraw.Draw(img)
    d.polygon([(320, 80), (380, 360), (260, 360)], fill=(79, 70, 229, 255))
    d.polygon([(320, 360), (420, 420), (320, 400), (220, 420)], fill=(244, 63, 94, 255))
    d.ellipse((295, 200, 345, 250), fill=(255, 255, 255, 255))
    d.text((250, 460), "Ship to Production", fill=(30, 41, 59, 255))
    img.save(OUT / "rocket.png")


def _font(size: int, *, bold: bool = False) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    names = ("segoeuib.ttf", "segoeui.ttf") if bold else ("segoeui.ttf", "arial.ttf")
    for name in names:
        path = Path(r"C:\Windows\Fonts") / name
        if path.is_file():
            return ImageFont.truetype(str(path), size)
    return ImageFont.load_default()


def _text_width(draw: ImageDraw.ImageDraw, text: str, font) -> int:
    return int(draw.textlength(text, font=font))


def _draw_wrapped(
    draw: ImageDraw.ImageDraw,
    xy: tuple[int, int],
    text: str,
    font,
    fill: tuple[int, int, int],
    max_width: int,
    spacing: int = 6,
) -> int:
    """Draw wrapped text; return y after last line."""
    x, y = xy
    avg = max(12, _text_width(draw, "abcdefghijklmnopqrstuvwxyz", font) // 26)
    chars = max(18, max_width // avg)
    for para in text.split("\n"):
        for line in textwrap.wrap(para, width=chars):
            draw.text((x, y), line, fill=fill, font=font)
            y += font.size + spacing
        y += 4
    return y


def _mobile_bg(size: tuple[int, int]) -> Image.Image:
    w, h = size
    base = Image.new("RGBA", size, C_BG + (255,))
    glow = Image.new("RGBA", size, (0, 0, 0, 0))
    gd = ImageDraw.Draw(glow)
    gd.ellipse((-80, -60, 220, 180), fill=(99, 102, 241, 55))
    gd.ellipse((w - 180, 40, w + 60, 280), fill=(34, 211, 238, 35))
    base.alpha_composite(glow)
    return base.convert("RGB")


def render_mobile_capabilities() -> Image.Image:
    """What CloudMLOps does — mobile layout (auth aside content)."""
    w, h = PHONE_INNER
    img = _mobile_bg((w, h))
    draw = ImageDraw.Draw(img)
    pad = 18
    y = 52

    draw.rounded_rectangle((pad, y, pad + 34, y + 34), radius=9, fill=C_BRAND)
    draw.text((pad + 11, y + 8), "CM", fill=C_TEXT, font=_font(13, bold=True))
    draw.text((pad + 44, y + 4), "CloudMLOps", fill=C_TEXT, font=_font(15, bold=True))
    draw.text((pad + 44, y + 22), "Document AI", fill=C_MUTED, font=_font(10))
    y += 48

    y = _draw_wrapped(
        draw,
        (pad, y),
        "Turn long documents into short answers.",
        _font(20, bold=True),
        C_TEXT,
        w - pad * 2,
        spacing=4,
    )
    y += 6
    y = _draw_wrapped(
        draw,
        (pad, y),
        "React UI, FastAPI + FLAN-T5, PostgreSQL on AWS App Runner.",
        _font(11),
        C_MUTED,
        w - pad * 2,
    )
    y += 14

    for i, step in enumerate(PIPELINE, start=1):
        box_h = 52
        draw.rounded_rectangle((pad, y, w - pad, y + box_h), radius=10, fill=C_SURFACE, outline=C_BORDER)
        draw.rounded_rectangle((pad + 10, y + 14, pad + 34, y + 38), radius=7, fill=(99, 102, 241, 36))
        draw.text((pad + 18, y + 18), str(i), fill=(165, 180, 252), font=_font(11, bold=True))
        _draw_wrapped(draw, (pad + 42, y + 10), step, _font(10), C_TEXT, w - pad * 2 - 44, spacing=3)
        y += box_h + 8

    y += 4
    chip_x = pad
    for label in STACK:
        tw = _text_width(draw, label, _font(9)) + 16
        if chip_x + tw > w - pad:
            chip_x = pad
            y += 26
        draw.rounded_rectangle((chip_x, y, chip_x + tw, y + 22), radius=11, fill=C_SURFACE2, outline=C_BORDER)
        draw.text((chip_x + 8, y + 5), label, fill=C_MUTED, font=_font(9))
        chip_x += tw + 6

    return img


def render_mobile_summarize() -> Image.Image:
    """Summarize workflow + sample result — mobile layout."""
    w, h = PHONE_INNER
    img = _mobile_bg((w, h))
    draw = ImageDraw.Draw(img)
    pad = 16
    y = 48

    draw.text((pad, y), "SUMMARIZE", fill=C_ACCENT, font=_font(9, bold=True))
    y += 16
    draw.text((pad, y), "Generate a summary", fill=C_TEXT, font=_font(18, bold=True))
    y += 26
    y = _draw_wrapped(
        draw,
        (pad, y),
        "Upload or paste text, pick length, save to history.",
        _font(10),
        C_MUTED,
        w - pad * 2,
    )
    y += 12

    card_x2 = w - pad
    draw.rounded_rectangle((pad, y, card_x2, y + 248), radius=14, fill=C_SURFACE, outline=C_BORDER)

    cy = y + 14
    draw.text((pad + 12, cy), "1. Choose your source", fill=C_TEXT, font=_font(12, bold=True))
    cy += 28
    seg_w = (card_x2 - pad - 24) // 2
    draw.rounded_rectangle((pad + 12, cy, pad + 12 + seg_w, cy + 30), radius=8, fill=C_SURFACE2)
    draw.rounded_rectangle((pad + 12 + seg_w, cy, pad + 12 + seg_w * 2, cy + 30), radius=8, fill=C_BRAND_DARK)
    draw.text((pad + 22, cy + 8), "Paste text", fill=C_MUTED, font=_font(9))
    draw.text((pad + 12 + seg_w + 10, cy + 8), "Upload", fill=C_TEXT, font=_font(9, bold=True))
    cy += 40
    draw.rounded_rectangle((pad + 12, cy, card_x2 - 12, cy + 72), radius=10, outline=C_BORDER, width=2)
    draw.text((pad + 28, cy + 22), "Drop PDF, DOCX, or TXT", fill=C_MUTED, font=_font(10))
    draw.text((pad + 28, cy + 40), "Max 10 MB", fill=C_MUTED, font=_font(9))
    cy += 84
    draw.text((pad + 12, cy), "2. Output length", fill=C_TEXT, font=_font(11, bold=True))
    cy += 22
    for j, (lab, on) in enumerate((("Short", False), ("Medium", True), ("Long", False))):
        bx = pad + 12 + j * 72
        fill = C_BRAND_DARK if on else C_SURFACE2
        draw.rounded_rectangle((bx, cy, bx + 64, cy + 28), radius=8, fill=fill)
        draw.text((bx + 14, cy + 7), lab, fill=C_TEXT if on else C_MUTED, font=_font(9))
    cy += 38
    draw.rounded_rectangle((pad + 12, cy, card_x2 - 12, cy + 36), radius=10, fill=C_BRAND_DARK)
    draw.text((pad + 72, cy + 10), "Generate summary", fill=C_TEXT, font=_font(11, bold=True))

    y += 258
    draw.rounded_rectangle((pad, y, card_x2, h - pad - 8), radius=14, fill=C_SURFACE, outline=C_BORDER)
    draw.text((pad + 12, y + 12), "Generated summary", fill=C_TEXT, font=_font(12, bold=True))
    draw.rounded_rectangle((card_x2 - 118, y + 10, card_x2 - 12, y + 30), radius=8, fill=(52, 211, 153, 40))
    draw.text((card_x2 - 108, y + 14), "Saved", fill=C_SUCCESS, font=_font(8, bold=True))
    sample = (
        "The platform ingests documents, extracts text via FastAPI, applies extractive or "
        "FLAN-T5 summarization, and persists results in PostgreSQL for search and ratings."
    )
    _draw_wrapped(draw, (pad + 12, y + 38), sample, _font(10), C_TEXT, w - pad * 2 - 24, spacing=5)
    draw.text((pad + 12, h - pad - 28), "AWS App Runner  ·  extractive on prod", fill=C_MUTED, font=_font(8))

    return img


def phone_mockup(screen_src: Path, output: Path, *, body=(20, 27, 45)) -> None:
    """Phone frame with shadow + notch; screen is pre-sized mobile UI."""
    w, h = 440, 860
    inner_w, inner_h = PHONE_INNER
    pad = 36
    shadow = Image.new("RGBA", (w + 48, h + 48), (0, 0, 0, 0))
    sd = ImageDraw.Draw(shadow)
    sd.rounded_rectangle((pad + 8, pad + 14, w + pad - 8, h + pad - 6), radius=52, fill=(0, 0, 0, 90))
    shadow = shadow.filter(ImageFilter.GaussianBlur(14))

    canvas = Image.new("RGBA", (w + pad * 2, h + pad * 2), (0, 0, 0, 0))
    canvas.alpha_composite(shadow)
    draw = ImageDraw.Draw(canvas)
    ox, oy = pad, pad
    draw.rounded_rectangle((ox + 24, oy + 16, ox + w - 24, oy + h - 16), radius=50, fill=body + (255,))
    sx, sy = ox + 44, oy + 72
    draw.rounded_rectangle((sx, sy, sx + inner_w, sy + inner_h), radius=4, fill=(8, 12, 22, 255))
    if screen_src.is_file():
        screen = Image.open(screen_src).convert("RGB")
        if screen.size != (inner_w, inner_h):
            screen = screen.resize((inner_w, inner_h), Image.Resampling.LANCZOS)
        canvas.paste(screen, (sx, sy))
    cx = ox + w // 2
    draw.rounded_rectangle((cx - 52, oy + 28, cx + 52, oy + 52), radius=14, fill=(12, 18, 30, 255))
    output.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(output)


def build_phone_mockups(assets_dir: Path) -> None:
    assets_dir.mkdir(parents=True, exist_ok=True)
    cap = assets_dir / "_phone_screen_capabilities.png"
    summ = assets_dir / "_phone_screen_summarize.png"
    render_mobile_capabilities().save(cap)
    render_mobile_summarize().save(summ)
    phone_mockup(cap, assets_dir / "phone_app.png")
    phone_mockup(summ, assets_dir / "phone_docs.png")


def _browser_card(
    screenshot: Path,
    width: int,
    height: int,
    *,
    url: str = "cloudmlops.app",
) -> Image.Image:
    """Flat browser window with real screenshot (title slide)."""
    chrome = 46
    card = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(card)
    draw.rounded_rectangle((0, 0, width - 1, height - 1), radius=18, fill=(255, 255, 255, 255))
    draw.rectangle((0, chrome - 6, width, chrome + 4), fill=(30, 41, 59, 255))
    draw.rounded_rectangle((0, 0, width - 1, chrome + 8), radius=18, fill=(30, 41, 59, 255))
    for cx, col in ((16, (239, 68, 68)), (36, (250, 204, 21)), (56, (34, 197, 94))):
        draw.ellipse((cx, 14, cx + 16, 30), fill=col + (255,))
    draw.rounded_rectangle((88, 12, width - 16, 34), radius=8, fill=(51, 65, 85, 255))
    draw.text((98, 16), url, fill=(148, 163, 184, 255))
    inner_w, inner_h = width - 16, height - chrome - 16
    if screenshot.is_file():
        shot = ImageOps.fit(Image.open(screenshot).convert("RGB"), (inner_w, inner_h))
    else:
        shot = Image.new("RGB", (inner_w, inner_h), (241, 245, 249))
        ImageDraw.Draw(shot).text((24, inner_h // 2 - 10), "CloudMLOps", fill=(30, 41, 59))
    card.paste(shot, (8, chrome + 8))
    return card


def _card_shadow(size: tuple[int, int], *, blur: int = 22, alpha: int = 110) -> Image.Image:
    w, h = size
    sh = Image.new("RGBA", (w + 80, h + 80), (0, 0, 0, 0))
    sd = ImageDraw.Draw(sh)
    sd.rounded_rectangle((36, 44, w + 36, h + 44), radius=22, fill=(0, 0, 0, alpha))
    return sh.filter(ImageFilter.GaussianBlur(blur))


def _blit_rotated_card(
    canvas: Image.Image,
    card: Image.Image,
    xy: tuple[int, int],
    angle: float,
    *,
    scale: float = 1.0,
) -> None:
    if scale != 1.0:
        nw, nh = int(card.width * scale), int(card.height * scale)
        card = card.resize((nw, nh), Image.Resampling.LANCZOS)
    shadow = _card_shadow(card.size)
    canvas.alpha_composite(shadow, (xy[0] - 28, xy[1] - 18))
    rotated = card.rotate(angle, expand=True, resample=Image.Resampling.BICUBIC)
    canvas.alpha_composite(rotated, xy)


def _render_title_collage(
    assets_dir: Path,
    *,
    pulse_t: float = 0.0,
    card_drift: float = 0.0,
) -> Image.Image:
    """Layered browser frames + MLOps pipeline icons (title slide)."""
    w, h = 1280, 700
    canvas = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(canvas)

    # Soft accent blobs (transparent — sits on navy slide)
    for cx, cy, r, col in ((900, 220, 200, (6, 182, 212)), (640, 380, 160, (124, 58, 237))):
        for rr in range(r, 0, -6):
            a = int(35 * (1 - rr / r))
            draw.ellipse((cx - rr, cy - rr, cx + rr, cy + rr), fill=col + (a,))

    app = assets_dir / "01_aws_app.png"
    api = assets_dir / "03_swagger_docs.png"
    ill = assets_dir / "illustrations"

    drift_y = int(math.sin(card_drift) * 6)
    back = _browser_card(api, 500, 310, url="api.awsapprunner.com/docs")
    front = _browser_card(app, 640, 400, url="asqmhsdwfs.awsapprunner.com")
    _blit_rotated_card(canvas, back, (520, 70 + drift_y), -11, scale=0.82)
    _blit_rotated_card(canvas, front, (280, 30 + drift_y), 7, scale=1.0)

    # Pipeline strip
    draw.rounded_rectangle((40, 520, w - 40, 660), radius=24, fill=(30, 41, 59, 180))
    draw.line((200, 590, 1080, 590), fill=(71, 85, 105, 255), width=3)
    pulse_x = int(120 + pulse_t * (960 - 120)) if pulse_t >= 0 else None
    for fname, cx, label in (
        ("documents.png", 150, "Ingest"),
        ("ai_brain.png", 640, "Summarize"),
        ("cloud.png", 1130, "Deploy"),
    ):
        glow = 0
        if pulse_x is not None and abs(pulse_x - cx) < 70:
            glow = int(50 * (1 - abs(pulse_x - cx) / 70))
        draw.ellipse((cx - 62 - glow // 3, 528 - glow // 3, cx + 62 + glow // 3, 652 + glow // 3), fill=(13, 148, 136, 35 + glow))
        ip = ill / fname
        if ip.is_file():
            icon = Image.open(ip).convert("RGBA")
            icon = icon.resize((100, 100), Image.Resampling.LANCZOS)
            canvas.alpha_composite(icon, (cx - 50, 540))
        draw.text((cx - 42, 648), label, fill=(226, 232, 240, 255))

    if pulse_x is not None:
        draw.ellipse((pulse_x - 10, 578, pulse_x + 10, 598), fill=(6, 182, 212, 255))
        draw.polygon(
            [(pulse_x + 12, 588), (pulse_x + 28, 588), (pulse_x + 20, 582), (pulse_x + 20, 594)],
            fill=(6, 182, 212, 220),
        )

    return canvas


def build_title_collage(assets_dir: Path) -> None:
    assets_dir.mkdir(parents=True, exist_ok=True)
    static = _render_title_collage(assets_dir, pulse_t=-1)
    static.save(assets_dir / "title_collage.png")

    frames: list[Image.Image] = []
    for i in range(40):
        t = i / 40
        drift = t * 2 * math.pi
        frame = _render_title_collage(assets_dir, pulse_t=t, card_drift=drift)
        frames.append(frame.convert("P", palette=Image.Palette.ADAPTIVE, colors=256))

    frames[0].save(
        assets_dir / "title_collage.gif",
        save_all=True,
        append_images=frames[1:],
        duration=85,
        loop=0,
        disposal=2,
    )


# Backward-compatible alias for deck builder imports
def build_title_hero_3d(assets_dir: Path) -> None:
    build_title_collage(assets_dir)


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    thinking()
    cloud_deploy()
    ai_brain()
    documents()
    teamwork()
    rocket()
    assets = OUT.parent
    build_phone_mockups(assets)
    build_title_collage(assets)
    print("Illustrations saved to", OUT)


if __name__ == "__main__":
    main()
