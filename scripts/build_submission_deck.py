"""
Build submission-ready CloudMLOps PPT + PDF report.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from fpdf import FPDF
from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_AUTO_SHAPE_TYPE
from pptx.enum.text import MSO_ANCHOR, PP_ALIGN
from pptx.oxml.ns import qn
from pptx.oxml.xmlchemy import OxmlElement
from pptx.util import Inches, Pt

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "docs" / "presentation_assets"
ILL = ASSETS / "illustrations"
OUT_PPT = ROOT / "docs" / "CloudMLOps_Project_Presentation.pptx"
OUT_PPT_ALIASES = (
    ROOT / "docs" / "CloudMLOps_Project_Presentation_v10.pptx",
    ROOT / "docs" / "CloudMLOps_Project_Presentation_v11.pptx",
)
OUT_PDF_REPORT = ROOT / "docs" / "CloudMLOps_Project_Report.pdf"

SLIDE_W = Inches(13.333)
MARGIN_X = Inches(0.72)
CONTENT_W = Inches(11.89)
FONT = "Segoe UI"
TEST_COUNT = 171

AWS_UI = "https://asqmhsdwfs.us-east-2.awsapprunner.com"
AWS_API = "https://p3jivcdmbf.us-east-2.awsapprunner.com"
NETLIFY = "https://cloudmlops.netlify.app"
RENDER = "https://cloudmlops.onrender.com"
GITHUB = "https://github.com/nitya200/CloudMlOps"

# Rich palette (consistent roles, varied accents)
PAL = {
    "ink": RGBColor(0x0B, 0x12, 0x20),
    "ink2": RGBColor(0x15, 0x23, 0x42),
    "teal": RGBColor(0x0D, 0x94, 0x88),
    "cyan": RGBColor(0x06, 0xB6, 0xD4),
    "violet": RGBColor(0x7C, 0x3A, 0xED),
    "indigo": RGBColor(0x4F, 0x46, 0xE5),
    "rose": RGBColor(0xF4, 0x3F, 0x5E),
    "amber": RGBColor(0xF5, 0x9E, 0x0B),
    "emerald": RGBColor(0x10, 0xB9, 0x81),
    "sky": RGBColor(0x0E, 0xA5, 0xE9),
    "bg": RGBColor(0xF4, 0xF7, 0xFB),
    "card": RGBColor(0xFF, 0xFF, 0xFF),
    "text": RGBColor(0x1E, 0x29, 0x3B),
    "muted": RGBColor(0x64, 0x74, 0x8B),
    "line": RGBColor(0xE2, 0xE8, 0xF0),
    "white": RGBColor(0xFF, 0xFF, 0xFF),
}

LIVE_URL_ROWS = [
    ("AWS production UI", AWS_UI, PAL["cyan"]),
    ("AWS production API", AWS_API, PAL["cyan"]),
    ("Health check", f"{AWS_API}/health", PAL["emerald"]),
    ("Swagger API docs", f"{AWS_API}/docs", PAL["indigo"]),
    ("ReDoc API docs", f"{AWS_API}/redoc", PAL["indigo"]),
    ("GitHub repository", GITHUB, PAL["amber"]),
]



@dataclass(frozen=True)
class ProjectMeta:
    title: str = "CLOUDMLOPS"
    subtitle: str = "AI Document Summarization Platform"
    affiliation: str = "APSCHE • Team Project"
    student: str = "Nityanandh Chimmili"
    github: str = "nitya200"
    email: str = "chimmilinityanandh@gmail.com"
    course: str = "CIS 5690 - Cloud MLOps"
    department: str = "Computer Science / Information Systems"
    year: str = "2025-2026"


META = ProjectMeta()


def _ensure_illustrations() -> None:
    import importlib.util

    spec = importlib.util.spec_from_file_location(
        "gen_ill", ROOT / "scripts" / "generate_ppt_illustrations.py"
    )
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    if not (ILL / "thinking.png").is_file():
        mod.main()
    mod.build_phone_mockups(ASSETS)


FRAME_TOP = Inches(1.32)
FRAME_HEIGHT = Inches(5.42)
FRAME_PAD = Inches(0.12)
PIC_HEIGHT = Inches(4.88)


def _cinematic_screen_frame(
    slide,
    img: Path,
    *,
    left=MARGIN_X,
    top=FRAME_TOP,
    width=CONTENT_W,
    height=FRAME_HEIGHT,
) -> None:
    """Dark rounded frame + screenshot (full-width demo slides or title right column)."""
    frame = slide.shapes.add_shape(MSO_AUTO_SHAPE_TYPE.ROUNDED_RECTANGLE, left, top, width, height)
    frame.fill.solid()
    frame.fill.fore_color.rgb = PAL["ink"]
    frame.line.color.rgb = PAL["line"]
    pic_h = height - FRAME_PAD * 2
    if img.is_file():
        slide.shapes.add_picture(
            str(img),
            left + FRAME_PAD,
            top + FRAME_PAD,
            width=width - FRAME_PAD * 2,
            height=pic_h,
        )


def _set_transition(slide, effect: str = "fade") -> None:
    """Advance on click + subtle fade (works in Slide Show)."""
    sld = slide._element
    for child in list(sld):
        if child.tag == qn("p:transition"):
            sld.remove(child)
    transition = OxmlElement("p:transition")
    transition.set("spd", "med")
    transition.set("advClick", "1")
    fx = OxmlElement(f"p:{effect}")
    transition.append(fx)
    sld.append(transition)


def _presenter_note(slide, text: str) -> None:
    notes = slide.notes_slide.notes_text_frame
    notes.text = text


def _set_para(p, text: str, *, size: int = 14, bold: bool = False, color=None, align=PP_ALIGN.LEFT):
    p.text = text
    p.font.name = FONT
    p.font.size = Pt(size)
    p.font.bold = bold
    p.font.color.rgb = color or PAL["text"]
    p.alignment = align
    p.space_after = Pt(6)


def _slide_bg_light(slide) -> None:
    slide.background.fill.solid()
    slide.background.fill.fore_color.rgb = PAL["bg"]
    stripe = slide.shapes.add_shape(MSO_AUTO_SHAPE_TYPE.RECTANGLE, Inches(0), Inches(0), Inches(0.12), Inches(7.5))
    stripe.fill.solid()
    stripe.fill.fore_color.rgb = PAL["teal"]
    stripe.line.fill.background()


def _slide_bg_dark(slide) -> None:
    slide.background.fill.solid()
    slide.background.fill.fore_color.rgb = PAL["ink"]
    for x, y, w, h, col in (
        (9.5, -0.4, 4.5, 4.5, PAL["violet"]),
        (-1.2, 4.8, 3.8, 3.8, PAL["cyan"]),
        (10.2, 5.0, 2.6, 2.6, PAL["rose"]),
    ):
        orb = slide.shapes.add_shape(MSO_AUTO_SHAPE_TYPE.OVAL, Inches(x), Inches(y), Inches(w), Inches(h))
        orb.fill.solid()
        orb.fill.fore_color.rgb = col
        orb.fill.transparency = 0.82
        orb.line.fill.background()


def _title_slide_apsche(slide) -> None:
    """APSCHE title layout (Shopez reference): navy left copy + tilted phone mockups."""
    navy = RGBColor(0x14, 0x1B, 0x2E)
    slide.background.fill.solid()
    slide.background.fill.fore_color.rgb = navy

    left = Inches(0.95)
    title_box = slide.shapes.add_textbox(left, Inches(0.85), Inches(6.5), Inches(1.05))
    _set_para(title_box.text_frame.paragraphs[0], META.title, size=52, bold=True, color=PAL["white"])

    sub_box = slide.shapes.add_textbox(left, Inches(1.92), Inches(6.2), Inches(0.5))
    _set_para(sub_box.text_frame.paragraphs[0], META.subtitle, size=22, color=PAL["white"])

    highlights = slide.shapes.add_textbox(left, Inches(2.65), Inches(5.85), Inches(3.55))
    tf = highlights.text_frame
    tf.word_wrap = True
    for i, line in enumerate(
        (
            "Ingest PDF, DOCX, and TXT in one workspace",
            "FastAPI + FLAN-T5 / extractive summarization",
            "History, ratings, and admin MLOps on AWS",
            "Live on App Runner — demo-ready URLs in-deck",
        )
    ):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.text = f"  •  {line}"
        p.font.name = FONT
        p.font.size = Pt(15)
        p.font.color.rgb = RGBColor(0xCB, 0xD5, 0xE1)
        p.space_after = Pt(14)
        p.line_spacing = 1.15

    # Mobile-native UI: capabilities + summarize flow (aligned copy from the real app)
    phones = (
        (ASSETS / "phone_app.png", Inches(6.75), Inches(0.35), -9),
        (ASSETS / "phone_docs.png", Inches(9.15), Inches(0.85), 12),
    )
    for path, px, py, rot in phones:
        img = path if path.is_file() else ASSETS / "01_aws_app.png"
        if img.is_file():
            pic = slide.shapes.add_picture(str(img), px, py, width=Inches(2.65))
            pic.rotation = rot


def _footer(slide, n: int, total: int) -> None:
    bar = slide.shapes.add_shape(MSO_AUTO_SHAPE_TYPE.RECTANGLE, Inches(0), Inches(7.18), SLIDE_W, Inches(0.32))
    bar.fill.solid()
    bar.fill.fore_color.rgb = PAL["ink2"]
    bar.line.fill.background()
    box = slide.shapes.add_textbox(MARGIN_X, Inches(7.2), CONTENT_W, Inches(0.28))
    _set_para(box.text_frame.paragraphs[0], f"{META.title}  |  {META.course}  |  Slide {n} of {total}", size=9, color=PAL["white"], align=PP_ALIGN.CENTER)


def _metric_strip(slide, items: list[tuple[str, str]]) -> None:
    """Small stat pills under the header band."""
    top = Inches(1.28)
    w = Inches(2.75)
    for i, (value, label) in enumerate(items):
        left = MARGIN_X + Inches(i * 2.95)
        pill = slide.shapes.add_shape(MSO_AUTO_SHAPE_TYPE.ROUNDED_RECTANGLE, left, top, w, Inches(0.72))
        pill.fill.solid()
        pill.fill.fore_color.rgb = PAL["card"]
        pill.line.color.rgb = PAL["line"]
        tf = pill.text_frame
        tf.margin_top = Pt(4)
        _set_para(tf.paragraphs[0], value, size=16, bold=True, color=PAL["indigo"], align=PP_ALIGN.CENTER)
        _set_para(tf.add_paragraph(), label, size=9, color=PAL["muted"], align=PP_ALIGN.CENTER)


def _place_illustration(slide, filename: str, left=Inches(8.35), top=Inches(1.35), width=Inches(4.25)) -> None:
    path = ILL / filename
    if path.is_file():
        slide.shapes.add_picture(str(path), left, top, width=width)


def _link_button(slide, left, top, width, height, label: str, url: str, fill: RGBColor) -> None:
    btn = slide.shapes.add_shape(MSO_AUTO_SHAPE_TYPE.ROUNDED_RECTANGLE, left, top, width, height)
    btn.fill.solid()
    btn.fill.fore_color.rgb = fill
    btn.line.fill.background()
    tf = btn.text_frame
    _set_para(tf.paragraphs[0], label, size=13, bold=True, color=PAL["white"], align=PP_ALIGN.CENTER)
    btn.click_action.hyperlink.address = url


def _header(slide, title: str, subtitle: str, accent: RGBColor) -> None:
    band = slide.shapes.add_shape(MSO_AUTO_SHAPE_TYPE.RECTANGLE, Inches(0.12), Inches(0), SLIDE_W, Inches(1.22))
    band.fill.solid()
    band.fill.fore_color.rgb = accent
    band.line.fill.background()
    glow = slide.shapes.add_shape(MSO_AUTO_SHAPE_TYPE.RECTANGLE, Inches(0.12), Inches(1.12), SLIDE_W, Inches(0.08))
    glow.fill.solid()
    glow.fill.fore_color.rgb = PAL["ink"]
    glow.fill.transparency = 0.15
    glow.line.fill.background()
    tbox = slide.shapes.add_textbox(MARGIN_X, Inches(0.22), CONTENT_W, Inches(0.52))
    _set_para(tbox.text_frame.paragraphs[0], title, size=30, bold=True, color=PAL["white"])
    sbox = slide.shapes.add_textbox(MARGIN_X, Inches(0.72), CONTENT_W, Inches(0.38))
    _set_para(sbox.text_frame.paragraphs[0], subtitle, size=13, color=PAL["white"])


def _card(slide, left, top, width, height, title: str, body: str, accent: RGBColor) -> None:
    shape = slide.shapes.add_shape(MSO_AUTO_SHAPE_TYPE.ROUNDED_RECTANGLE, left, top, width, height)
    shape.fill.solid()
    shape.fill.fore_color.rgb = PAL["card"]
    shape.line.color.rgb = PAL["line"]
    shape.line.width = Pt(1)
    strip = slide.shapes.add_shape(MSO_AUTO_SHAPE_TYPE.RECTANGLE, left, top + Inches(0.08), Inches(0.1), height - Inches(0.16))
    strip.fill.solid()
    strip.fill.fore_color.rgb = accent
    strip.line.fill.background()
    tf = shape.text_frame
    tf.margin_left = Pt(16)
    tf.margin_right = Pt(12)
    tf.margin_top = Pt(10)
    tf.vertical_anchor = MSO_ANCHOR.TOP
    _set_para(tf.paragraphs[0], title, size=14, bold=True, color=accent)
    _set_para(tf.add_paragraph(), body, size=11, color=PAL["text"])


def _bullet_block(
    slide,
    items: list[str],
    top=Inches(1.48),
    width=CONTENT_W,
    *,
    font_size: int = 14,
    spacing: int = 10,
) -> None:
    box = slide.shapes.add_textbox(MARGIN_X, top, width, Inches(5.55))
    tf = box.text_frame
    tf.word_wrap = True
    tf.margin_left = Pt(4)
    for i, item in enumerate(items):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.text = item if item.startswith(" ") else f"  •  {item}"
        p.font.name = FONT
        p.font.size = Pt(font_size)
        p.font.color.rgb = PAL["text"]
        p.space_after = Pt(spacing)
        p.line_spacing = 1.18


def _split_story(
    slide,
    bullets: list[str],
    illustration: str,
    top=Inches(1.48),
    *,
    after_metrics: bool = False,
) -> None:
    if after_metrics:
        top = Inches(2.05)
    n = len(bullets)
    spacing = 14 if n <= 3 else 10
    size = 15 if n <= 3 else 14
    _bullet_block(slide, bullets, top=top, width=Inches(7.05), font_size=size, spacing=spacing)
    ill_top = Inches(1.42) if not after_metrics else Inches(1.88)
    _place_illustration(slide, illustration, left=Inches(8.05), top=ill_top, width=Inches(4.65))


def _url_slide(slide) -> None:
    _slide_bg_light(slide)
    _header(slide, "Live Deployment URLs", "Interactive: click any link or button (Slide Show mode)", PAL["indigo"])
    hint = slide.shapes.add_textbox(MARGIN_X, Inches(1.28), CONTENT_W, Inches(0.35))
    _set_para(
        hint.text_frame.paragraphs[0],
        "Tip: Press F5 in PowerPoint, then click highlighted links to open each service in your browser.",
        size=10,
        color=PAL["muted"],
    )
    _link_button(slide, MARGIN_X, Inches(1.62), Inches(3.6), Inches(0.48), "Open AWS App", AWS_UI, PAL["cyan"])
    _link_button(
        slide,
        MARGIN_X + Inches(3.75),
        Inches(1.62),
        Inches(3.6),
        Inches(0.48),
        "Open API Docs",
        f"{AWS_API}/docs",
        PAL["violet"],
    )
    _link_button(
        slide,
        MARGIN_X + Inches(7.5),
        Inches(1.62),
        Inches(3.6),
        Inches(0.48),
        "Open GitHub",
        GITHUB,
        PAL["amber"],
    )
    _place_illustration(slide, "cloud.png", left=Inches(9.35), top=Inches(2.15), width=Inches(3.35))
    y = Inches(2.12)
    row_h = Inches(0.62)
    row_w = Inches(7.85)
    for label, url, accent in LIVE_URL_ROWS:
        row = slide.shapes.add_shape(MSO_AUTO_SHAPE_TYPE.ROUNDED_RECTANGLE, MARGIN_X, y, row_w, row_h)
        row.fill.solid()
        row.fill.fore_color.rgb = PAL["card"]
        row.line.color.rgb = PAL["line"]
        tag = slide.shapes.add_shape(MSO_AUTO_SHAPE_TYPE.RECTANGLE, MARGIN_X, y, Inches(0.11), row_h)
        tag.fill.solid()
        tag.fill.fore_color.rgb = accent
        tag.line.fill.background()
        lbox = slide.shapes.add_textbox(MARGIN_X + Inches(0.28), y + Inches(0.05), Inches(2.85), Inches(0.28))
        _set_para(lbox.text_frame.paragraphs[0], label, size=11, bold=True, color=PAL["ink2"])
        ubox = slide.shapes.add_textbox(MARGIN_X + Inches(3.15), y + Inches(0.07), Inches(5.75), Inches(0.28))
        p = ubox.text_frame.paragraphs[0]
        p.text = ""
        run = p.add_run()
        run.text = url
        run.font.name = FONT
        run.font.size = Pt(10)
        run.font.color.rgb = PAL["teal"]
        run.font.underline = True
        run.hyperlink.address = url
        y += row_h + Inches(0.08)


def _screenshot_slide(slide, title: str, subtitle: str, accent: RGBColor, img: Path, caption: str) -> None:
    _slide_bg_light(slide)
    _header(slide, title, subtitle, accent)
    _cinematic_screen_frame(slide, img)
    cap = slide.shapes.add_textbox(MARGIN_X, Inches(6.72), CONTENT_W, Inches(0.38))
    _set_para(cap.text_frame.paragraphs[0], caption, size=11, color=PAL["muted"], align=PP_ALIGN.CENTER)


def build_ppt() -> Path:
    _ensure_illustrations()
    prs = Presentation()
    prs.slide_width = SLIDE_W
    prs.slide_height = Inches(7.5)
    blank = prs.slide_layouts[6]
    total = 15

    def finish(slide, num: int, note: str = "") -> None:
        _set_transition(slide)
        if note:
            _presenter_note(slide, note)
        if num > 0:
            _footer(slide, num, total)

    # 1 Title (APSCHE team project layout)
    s = prs.slides.add_slide(blank)
    _title_slide_apsche(s)
    _set_transition(s, "fade")
    _presenter_note(
        s,
        "Shopez-style title: team left; phones show what the app does (pipeline + summarize UI). "
        "Full AWS screenshots on later demo slides. Interactive Demo (F5).",
    )

    accents = [PAL["teal"], PAL["rose"], PAL["violet"], PAL["indigo"], PAL["cyan"], PAL["emerald"], PAL["amber"], PAL["sky"]]

    # 2 Overview
    s = prs.slides.add_slide(blank)
    _slide_bg_light(s)
    _header(s, "Project Overview", "Smart summarization + cloud MLOps in one product", accents[0])
    _metric_strip(
        s,
        [(str(TEST_COUNT), "Automated tests"), ("3", "Architecture tiers"), (str(len(LIVE_URL_ROWS)), "Live URLs"), ("AWS", "Production")],
    )
    _split_story(
        s,
        [
            "Upload PDF / DOCX / TXT — or paste text — get a concise summary in seconds.",
            "Every summary is saved: search history, download, and rate quality.",
            "Admins track usage, manage users, and approve new model versions.",
            "Shipped with Docker, GitHub Actions, Terraform, and AWS App Runner.",
        ],
        "documents.png",
        after_metrics=True,
    )
    finish(s, 2, "Keep this high-level; details come on architecture and demo slides.")

    # 3 Problem
    s = prs.slides.add_slide(blank)
    _slide_bg_light(s)
    _header(s, "Problem Statement", "Why manual reading does not scale", accents[1])
    _split_story(
        s,
        [
            "Reports and papers are too long to read end-to-end under time pressure.",
            "Notes in Word or email are not searchable or shared safely.",
            "Heavy AI models stall on free tiers and HTTP timeouts in the cloud.",
            "Teams need one secure app: extract, summarize, store, and deploy reliably.",
        ],
        "thinking.png",
    )
    finish(s, 3)
    n = 4

    # Objectives
    s = prs.slides.add_slide(blank)
    _slide_bg_light(s)
    _header(s, "Objectives", "What we set out to build", PAL["violet"])
    _place_illustration(s, "teamwork.png", left=Inches(9.85), top=Inches(1.48), width=Inches(3.05))
    objs = [
        ("Three-tier design", "React + FastAPI + PostgreSQL", PAL["cyan"]),
        ("Smart ingestion", "PDF, DOCX, TXT with validation", PAL["rose"]),
        ("AI engine", "FLAN-T5 locally; fast extractive on AWS", PAL["indigo"]),
        ("User experience", "Auth, history, downloads, ratings", PAL["emerald"]),
        ("Admin & MLOps", "Metrics + model approve / promote", PAL["amber"]),
        ("Cloud ship", "CI/CD to App Runner via ECR", PAL["sky"]),
    ]
    for i, (h, b, ac) in enumerate(objs):
        _card(s, MARGIN_X + Inches((i % 3) * 4.02), Inches(1.52 + (i // 3) * 1.98), Inches(3.78), Inches(1.88), h, b, ac)
    finish(s, n)
    n += 1

    # Solution flow
    s = prs.slides.add_slide(blank)
    _slide_bg_light(s)
    _header(s, "Proposed Solution", "From document to deployed insight", PAL["cyan"])
    _place_illustration(s, "rocket.png", left=Inches(9.55), top=Inches(1.45), width=Inches(3.25))
    steps = [
        ("Problem", "Too much text, no system", PAL["rose"]),
        ("Approach", "Clean layers + AI factory", PAL["violet"]),
        ("Build", "Extract, summarize, store", PAL["teal"]),
        ("Launch", "Live AWS + 171 tests", PAL["emerald"]),
    ]
    for i, (st, tx, ac) in enumerate(steps):
        left = MARGIN_X + Inches(i * 2.98)
        sh = s.shapes.add_shape(MSO_AUTO_SHAPE_TYPE.ROUNDED_RECTANGLE, left, Inches(1.52), Inches(2.65), Inches(2.05))
        sh.fill.solid()
        sh.fill.fore_color.rgb = PAL["card"]
        sh.line.color.rgb = ac
        sh.line.width = Pt(2)
        tf = sh.text_frame
        tf.margin_top = Pt(14)
        _set_para(tf.paragraphs[0], st, size=17, bold=True, color=ac, align=PP_ALIGN.CENTER)
        _set_para(tf.add_paragraph(), tx, size=12, color=PAL["text"], align=PP_ALIGN.CENTER)
        if i < 3:
            arr = s.shapes.add_shape(MSO_AUTO_SHAPE_TYPE.CHEVRON, left + Inches(2.68), Inches(2.35), Inches(0.35), Inches(0.45))
            arr.fill.solid()
            arr.fill.fore_color.rgb = ac
            arr.line.fill.background()
    flow = s.shapes.add_shape(MSO_AUTO_SHAPE_TYPE.ROUNDED_RECTANGLE, MARGIN_X, Inches(3.78), Inches(8.95), Inches(2.65))
    flow.fill.solid()
    flow.fill.fore_color.rgb = PAL["card"]
    flow.line.color.rgb = PAL["line"]
    flow_tf = flow.text_frame
    flow_tf.margin_left = Pt(18)
    flow_tf.margin_top = Pt(14)
    _set_para(flow_tf.paragraphs[0], "End-to-end flow", size=15, bold=True, color=PAL["cyan"])
    _set_para(
        flow_tf.add_paragraph(),
        "Users upload or paste documents → FastAPI validates and extracts text → summarizer "
        f"({TEST_COUNT} automated tests) persists output to PostgreSQL → React UI and admin "
        "dashboard expose history, ratings, and model lifecycle on AWS App Runner.",
        size=12,
        color=PAL["text"],
    )
    finish(s, n)
    n += 1

    # Tech stack
    s = prs.slides.add_slide(blank)
    _slide_bg_light(s)
    _header(s, "Technologies Used", "Modern stack — only what the project uses", PAL["indigo"])
    _place_illustration(s, "ai_brain.png", left=Inches(9.55), top=Inches(1.35), width=Inches(3.15))
    groups = [
        ("Frontend", "React 19, Vite, React Router, Axios", PAL["cyan"]),
        ("Backend", "Python 3.12, FastAPI, SQLAlchemy 2", PAL["violet"]),
        ("Database", "PostgreSQL 16, Alembic", PAL["emerald"]),
        ("AI / ML", "Transformers, flan-t5-small, extractive", PAL["rose"]),
        ("Extraction", "PyMuPDF, python-docx", PAL["amber"]),
        ("Cloud / DevOps", "Docker, Actions, ECR, App Runner, Terraform", PAL["sky"]),
    ]
    for i, (h, b, ac) in enumerate(groups):
        _card(s, MARGIN_X + Inches((i % 2) * 6.05), Inches(1.52 + (i // 2) * 1.48), Inches(5.82), Inches(1.32), h, b, ac)
    finish(s, n)
    n += 1

    # Architecture
    s = prs.slides.add_slide(blank)
    _slide_bg_light(s)
    _header(s, "System Architecture", "How traffic flows in production", PAL["teal"])
    _place_illustration(s, "cloud.png", left=Inches(9.55), top=Inches(1.48), width=Inches(3.15))
    layers = [
        ("Browser / User", PAL["cyan"]),
        ("React frontend — AWS App Runner", PAL["indigo"]),
        ("FastAPI backend — AWS App Runner", PAL["violet"]),
        ("PostgreSQL (RDS) + document storage", PAL["emerald"]),
        ("CloudWatch + Secrets Manager", PAL["amber"]),
        ("CI/CD — GitHub Actions → ECR → deploy", PAL["sky"]),
    ]
    y = 1.52
    for label, ac in layers:
        box = s.shapes.add_shape(
            MSO_AUTO_SHAPE_TYPE.ROUNDED_RECTANGLE, MARGIN_X, Inches(y), Inches(8.55), Inches(0.72)
        )
        box.fill.solid()
        box.fill.fore_color.rgb = PAL["card"]
        box.line.color.rgb = ac
        box.line.width = Pt(1.5)
        _set_para(box.text_frame.paragraphs[0], label, size=13, bold=True, color=PAL["ink2"], align=PP_ALIGN.CENTER)
        y += 0.82
    finish(s, n)
    n += 1

    # Features
    s = prs.slides.add_slide(blank)
    _slide_bg_light(s)
    _header(s, "Key Features", "What users and admins can do", PAL["rose"])
    _place_illustration(s, "documents.png", left=Inches(9.85), top=Inches(1.48), width=Inches(3.0))
    feats = [
        ("Authentication", "JWT sessions, admin roles", PAL["indigo"]),
        ("Summarization", "Text + documents, 3 lengths", PAL["cyan"]),
        ("History", "Search and pagination", PAL["violet"]),
        ("Feedback", "Star ratings for quality", PAL["rose"]),
        ("Admin dashboard", "Usage and user management", PAL["emerald"]),
        ("Model lifecycle", "UC-12 / UC-16 ROUGE pipeline", PAL["amber"]),
    ]
    for i, (h, b, ac) in enumerate(feats):
        _card(s, MARGIN_X + Inches((i % 3) * 4.02), Inches(1.52 + (i // 3) * 1.98), Inches(3.78), Inches(1.88), h, b, ac)
    finish(s, n)
    n += 1

    # Interactive demo CTA
    s = prs.slides.add_slide(blank)
    _slide_bg_light(s)
    _header(s, "Interactive Demo", "Click buttons in Slide Show (F5) to open live services", PAL["emerald"])
    _place_illustration(s, "thinking.png", left=Inches(8.85), top=Inches(2.05), width=Inches(3.85))
    demo = s.shapes.add_textbox(MARGIN_X, Inches(1.52), Inches(7.65), Inches(2.35))
    _set_para(demo.text_frame.paragraphs[0], "Try the app while you present:", size=18, bold=True, color=PAL["ink2"])
    _set_para(
        demo.text_frame.add_paragraph(),
        "1. Open AWS frontend and log in\n2. Upload a sample PDF or paste text\n3. Show summary + history\n4. Optional: Swagger /docs for API",
        size=14,
        color=PAL["text"],
    )
    _link_button(s, MARGIN_X, Inches(4.05), Inches(5.45), Inches(0.72), "Launch Web App", AWS_UI, PAL["cyan"])
    _link_button(s, MARGIN_X + Inches(5.55), Inches(4.05), Inches(5.45), Inches(0.72), "Open Swagger UI", f"{AWS_API}/docs", PAL["indigo"])
    _link_button(s, MARGIN_X, Inches(4.92), Inches(5.45), Inches(0.72), "Health Check JSON", f"{AWS_API}/health", PAL["emerald"])
    _link_button(s, MARGIN_X + Inches(5.55), Inches(4.92), Inches(5.45), Inches(0.72), "View Source on GitHub", GITHUB, PAL["amber"])
    tip = s.shapes.add_shape(MSO_AUTO_SHAPE_TYPE.ROUNDED_RECTANGLE, MARGIN_X, Inches(5.78), Inches(7.95), Inches(0.82))
    tip.fill.solid()
    tip.fill.fore_color.rgb = PAL["card"]
    tip.line.color.rgb = PAL["line"]
    _set_para(
        tip.text_frame.paragraphs[0],
        "Presenter tip: keep this slide open during Q&A — every button opens the real production service.",
        size=11,
        color=PAL["muted"],
    )
    finish(s, n, "This is your live demo slide — click buttons during viva.")
    n += 1

    # Live URLs (single page)
    s = prs.slides.add_slide(blank)
    _url_slide(s)
    finish(s, n, "Backup link hub if panel asks for every URL in one place.")
    n += 1

    # Screenshots (no Netlify 404)
    shots = [
        ("Production Application", "AWS App Runner frontend", PAL["cyan"], ASSETS / "01_aws_app.png", "Live CloudMLOps UI on AWS (home / login route)."),
        ("API Documentation", "Interactive OpenAPI on production API", PAL["indigo"], ASSETS / "03_swagger_docs.png", "Swagger UI served from the deployed FastAPI backend."),
    ]
    for title, sub, ac, path, cap in shots:
        s = prs.slides.add_slide(blank)
        _screenshot_slide(s, title, sub, ac, path, cap)
        finish(s, n)
        n += 1

    # Results
    s = prs.slides.add_slide(blank)
    _slide_bg_light(s)
    _header(s, "Results & Outcomes", "What is working today", PAL["emerald"])
    _metric_strip(s, [("Live", "AWS App Runner"), ("OK", "DB connected"), (str(TEST_COUNT), "Tests pass"), ("UC-12", "Model promote")])
    _split_story(
        s,
        [
            f"{TEST_COUNT} pytest cases — auth, uploads, AI paths, admin, migrations.",
            "Production health: database connected; summarizer ready on AWS.",
            "Terraform + GitHub Actions: repeatable deploy pipeline.",
            "Model lifecycle: ROUGE evaluation, approve, promote (UC-12 / UC-16).",
        ],
        "rocket.png",
        after_metrics=True,
    )
    finish(s, n)
    n += 1

    # Future + Conclusion
    for title, sub, accent, bullets in (
        (
            "Future Scope",
            "Planned improvements (not yet implemented)",
            PAL["violet"],
            [
                "GPU App Runner or SageMaker for full FLAN-T5 at scale.",
                "CloudWatch alarms + email/SNS when services degrade.",
                "Richer offline benchmarks when extra compute is available.",
            ],
        ),
        (
            "Conclusion",
            "In one minute",
            PAL["teal"],
            [
                "Built a real cloud app — not just slides — with live URLs you can click.",
                "Solved document overload with extract, summarize, store, and rate.",
                "Proved engineering quality with tests, CI, and AWS MLOps patterns.",
            ],
        ),
    ):
        s = prs.slides.add_slide(blank)
        _slide_bg_light(s)
        _header(s, title, sub, accent)
        ill = "thinking.png" if title.startswith("Future") else "teamwork.png"
        _split_story(s, bullets, ill)
        finish(s, n)
        n += 1

    # Thank you
    s = prs.slides.add_slide(blank)
    _slide_bg_dark(s)
    band = s.shapes.add_shape(MSO_AUTO_SHAPE_TYPE.ROUNDED_RECTANGLE, Inches(1.85), Inches(2.35), Inches(9.6), Inches(2.75))
    band.fill.solid()
    band.fill.fore_color.rgb = PAL["violet"]
    band.line.fill.background()
    tb = s.shapes.add_textbox(Inches(0), Inches(2.85), SLIDE_W, Inches(0.85))
    _set_para(tb.text_frame.paragraphs[0], "Thank You", size=44, bold=True, color=PAL["white"], align=PP_ALIGN.CENTER)
    sub = s.shapes.add_textbox(Inches(0), Inches(3.85), SLIDE_W, Inches(1.05))
    _set_para(sub.text_frame.paragraphs[0], META.title, size=16, color=PAL["cyan"], align=PP_ALIGN.CENTER)
    _set_para(sub.text_frame.add_paragraph(), META.course, size=12, color=PAL["white"], align=PP_ALIGN.CENTER)
    _set_para(sub.text_frame.add_paragraph(), "Questions & Discussion", size=14, color=PAL["white"], align=PP_ALIGN.CENTER)
    _link_button(s, Inches(4.85), Inches(5.35), Inches(3.6), Inches(0.58), "Open Live Demo", AWS_UI, PAL["cyan"])
    _set_transition(s)
    _presenter_note(s, "Thank the panel. Offer to show live demo again from slide 9.")

    OUT_PPT.parent.mkdir(parents=True, exist_ok=True)
    saved: list[Path] = []
    for target in (OUT_PPT, *OUT_PPT_ALIASES):
        try:
            prs.save(str(target))
            saved.append(target)
        except PermissionError:
            continue
    if not saved:
        raise PermissionError("Close open PowerPoint files in docs/ and run the script again.")
    return saved[0]


class ReportPDF(FPDF):
    def header(self) -> None:
        self.set_font("Helvetica", "B", 10)
        self.set_text_color(15, 118, 110)
        self.cell(0, 8, META.title + " - Project Report", align="L")
        self.ln(10)

    def footer(self) -> None:
        self.set_y(-12)
        self.set_font("Helvetica", "I", 9)
        self.set_text_color(100, 116, 139)
        self.cell(0, 8, f"Page {self.page_no()}", align="C")


def _section(pdf: FPDF, title: str, body: str) -> None:
    pdf.set_font("Helvetica", "B", 14)
    pdf.set_text_color(15, 23, 42)
    pdf.cell(0, 8, title, new_x="LMARGIN", new_y="NEXT")
    pdf.ln(2)
    pdf.set_font("Helvetica", "", 11)
    pdf.set_text_color(51, 65, 85)
    pdf.multi_cell(170, 5.5, body)
    pdf.ln(3)


def build_report_pdf() -> Path:
    pdf = ReportPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.set_left_margin(20)
    pdf.set_right_margin(20)
    pdf.add_page()
    pdf.set_font("Helvetica", "B", 22)
    pdf.set_text_color(15, 118, 110)
    pdf.multi_cell(170, 10, META.title)
    pdf.set_font("Helvetica", "", 14)
    pdf.multi_cell(170, 8, META.subtitle)
    pdf.ln(4)
    pdf.set_font("Helvetica", "", 11)
    for line in (f"GitHub: {META.github}", META.course, META.department, f"Academic year: {META.year}"):
        pdf.cell(0, 6, line, new_x="LMARGIN", new_y="NEXT")

    url_block = "\n".join(f"- {label}: {url}" for label, url, _ in LIVE_URL_ROWS)
    sections = [
        ("Abstract", "CloudMLOps is a three-tier AI document summarization platform deployed on AWS App Runner with PostgreSQL, CI/CD, and admin MLOps features."),
        ("Live deployment URLs", url_block),
        (
            "Testing & results",
            f"{TEST_COUNT} pytest cases; production health endpoint reports database connected; AWS URLs listed above.",
        ),
        ("Conclusion", "The project meets academic goals for architecture, AI integration, cloud deployment, and automated quality checks."),
    ]
    for title, body in sections:
        pdf.add_page()
        _section(pdf, title, body)

    figs = [
        ("Figure 1: AWS App Runner UI", ASSETS / "01_aws_app.png"),
        ("Figure 2: Swagger API documentation", ASSETS / "03_swagger_docs.png"),
    ]
    for caption, path in figs:
        pdf.add_page()
        pdf.set_font("Helvetica", "B", 12)
        pdf.cell(0, 8, caption, new_x="LMARGIN", new_y="NEXT")
        pdf.ln(2)
        if path.is_file():
            pdf.image(str(path), w=180)

    OUT_PDF_REPORT.parent.mkdir(parents=True, exist_ok=True)
    pdf.output(str(OUT_PDF_REPORT))
    return OUT_PDF_REPORT


def export_ppt_to_pdf(ppt_path: Path, pdf_path: Path) -> bool:
    try:
        import win32com.client

        app = win32com.client.Dispatch("PowerPoint.Application")
        app.Visible = 1
        pres = app.Presentations.Open(str(ppt_path.resolve()), WithWindow=False)
        pres.SaveAs(str(pdf_path.resolve()), 32)
        pres.Close()
        app.Quit()
        return True
    except Exception:
        return False


def main() -> None:
    ppt = build_ppt()
    report = build_report_pdf()
    slides_pdf = ROOT / "docs" / "CloudMLOps_Project_Presentation.pdf"
    if export_ppt_to_pdf(ppt, slides_pdf):
        print("Presentation PDF:", slides_pdf)
    print("Presentation PPT:", ppt)
    print("Project report PDF:", report)


if __name__ == "__main__":
    main()
