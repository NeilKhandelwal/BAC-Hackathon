"""Build the editable pitch deck: docs/deck/pitch_template.pptx.

Run from the repo root:

    .venv/bin/python docs/deck/build_deck.py

Reads docs/figures/facts.json, results/balanced.csv, results/global_balanced.csv,
docs/figures/map_composite.png, and the app screenshots in docs/deck/img/. Writes
the deck, docs/deck/numbers_to_check.md, and docs/deck/sources.md. Numbers from
facts.json and results/ refresh on a rebuild. Numbers from research write-ups and
reruns are typed in below, next to the file they come from.

Slide text stays plain: no colons, semicolons, or em dashes, at most three bullets
of under 12 words each. The build stops if a string breaks those rules.

A rebuild overwrites the .pptx. Make wording changes here, or edit the .pptx by
hand once the numbers are final.
"""
import csv
import json
from pathlib import Path

from lxml import etree
from PIL import Image
from pptx import Presentation
from pptx.chart.data import CategoryChartData
from pptx.dml.color import RGBColor
from pptx.enum.chart import XL_AXIS_CROSSES, XL_CHART_TYPE, XL_LABEL_POSITION, XL_LEGEND_POSITION, XL_MARKER_STYLE, XL_TICK_MARK
from pptx.enum.shapes import MSO_CONNECTOR, MSO_SHAPE
from pptx.enum.text import MSO_ANCHOR, PP_ALIGN
from pptx.opc.constants import RELATIONSHIP_TYPE as RT
from pptx.oxml.ns import qn
from pptx.util import Emu, Inches, Pt

ROOT = Path(__file__).resolve().parents[2]
DECK = ROOT / "docs/deck"
FIG = ROOT / "docs/figures"
FACTS = json.loads((FIG / "facts.json").read_text())

# ---------------------------------------------------------------------------
# Theme: the cockpit palette from DESIGN.md, so slides and demo match.
# ---------------------------------------------------------------------------
FONT = "Arial"
INK = RGBColor(0x11, 0x15, 0x18)
INK2 = RGBColor(0x46, 0x50, 0x5A)
INK3 = RGBColor(0x5F, 0x6A, 0x74)
RULE = RGBColor(0xD3, 0xD8, 0xD6)
GROUND = RGBColor(0xF3, 0xF5, 0xF4)
WHITE = RGBColor(0xFF, 0xFF, 0xFF)
NAVY = RGBColor(0x0B, 0x3C, 0x6F)
BLUE = RGBColor(0x4F, 0x82, 0xBD)
PALE = RGBColor(0xDC, 0xE3, 0xEA)
GREY = RGBColor(0x8E, 0x8F, 0x8A)
EMBER = RGBColor(0xD9, 0x53, 0x2B)
AMBER = RGBColor(0xB8, 0x62, 0x00)
GREEN = RGBColor(0x23, 0x80, 0x4F)

PILLARS = [  # key, label, hue
    ("energy_carbon", "Energy & carbon", RGBColor(0xB8, 0x62, 0x00)),
    ("water", "Water", RGBColor(0x14, 0x75, 0x8F)),
    ("climate_resilience", "Climate", RGBColor(0xB0, 0x30, 0x3F)),
    ("grid_infrastructure", "Grid", RGBColor(0x5B, 0x4B, 0xA0)),
    ("land", "Land", RGBColor(0x5E, 0x6E, 0x12)),
    ("community", "Community", RGBColor(0x23, 0x80, 0x4F)),
    ("permitting", "Permitting", RGBColor(0x86, 0x52, 0x3A)),
    ("cost", "Cost of power", RGBColor(0x9A, 0x3A, 0x8C)),
]

W, H = Inches(13.333), Inches(7.5)
MX = Inches(0.6)  # side margin
CW = W - 2 * MX  # content width
TOP = Inches(2.05)  # content top, below a two-line headline
BOTTOM = Inches(6.72)  # content bottom

# ---------------------------------------------------------------------------
# Registries: numbers to check, sources, placeholders.
# ---------------------------------------------------------------------------
CHECKS = []  # (slide, what, value, file, field)
SOURCES = {}  # slide -> list of source lines for sources.md
PLACEHOLDERS = []  # (slide, text)
SCRIPT_WORDS = {}  # slide -> words in the spoken script


def fmt(n, d=0):
    return f"{n:,.{d}f}"


def pct(x, d=1):
    return f"{x * 100:.{d}f}%"


# ---------------------------------------------------------------------------
# Quotes. Each one is verified at the URL given, or it becomes a placeholder.
# ---------------------------------------------------------------------------
# Verified 2026-10-04 by opening each primary source and matching the words exactly (ignoring whitespace and
# straight versus curly quotes). An ellipsis marks an omission. Unused quotes stay in the bank for sources.md.
QUOTE_BANK = [
    dict(key="ny_eo62", slide="1",
         text="New Yorkers have expressed legitimate concerns regarding the potential impacts of the siting and "
              "operation of data centers on energy use, water use, water quality…",
         who="New York Executive Order No. 62, Gov. Kathy Hochul, July 14, 2026", cite="New York Executive Order 62, July 2026",
         source="Executive Order No. 62, WHEREAS clause 9",
         url="https://www.governor.ny.gov/executive-order/no-62-establishing-temporary-moratorium-data-centers-new-york-while-state-develops"),
    dict(key="wa_water", slide="6",
         text="The direct water requirements of data centers can be substantial, depending on the size and type of "
              "cooling system used.",
         who="Washington Data Center Workgroup, Preliminary Report, Dec. 2025", cite="Washington Data Center Workgroup, Dec. 2025",
         source="Data Center Workgroup: Preliminary Report (Executive Order 25-05), Finding 19, p. 13",
         url="https://dor.wa.gov/sites/default/files/2025-12/2025DataCntrWrkgrpPrelimReport.pdf"),
    dict(key="pud_speed", slide="unused",
         text="…service cannot always be provided as quickly as customers or developers may prefer.",
         who="Grant County PUD, Data Center FAQs, Aug. 28, 2026", cite="Grant County PUD, Aug. 2026",
         source="Grant PUD & Data Centers: FAQs, Q6",
         url="https://www.grantpud.org/blog/data-center-faqs"),
    dict(key="pud_pays", slide="8",
         text="Large power users, including data centers, are responsible for paying the costs of additional "
              "generation, transmission, and distribution infrastructure needed specifically to serve their loads.",
         who="Grant County PUD, Data Center FAQs, Aug. 28, 2026", cite="Grant County PUD, Aug. 2026",
         source="Grant PUD & Data Centers: FAQs, Q5",
         url="https://www.grantpud.org/blog/data-center-faqs"),
    # Verified, not on a slide. Use in speaker notes, Q&A, or a swap.
    dict(key="iea_us_growth", slide="unused",
         text="In the United States, data centres account for nearly half of electricity demand growth between now and 2030.",
         who="International Energy Agency, Energy and AI, April 10, 2025 (CC BY 4.0)",
         source="Energy and AI, Executive summary", url="https://www.iea.org/reports/energy-and-ai/executive-summary"),
    dict(key="doe_growth", slide="unused",
         text="The report estimates that data center load growth has tripled over the past decade and is projected to "
              "double or triple by 2028.",
         who="U.S. Department of Energy, Dec. 20, 2024",
         source="DOE Releases New Report Evaluating Increase in Electricity Demand from Data Centers, paragraph 1",
         url="https://www.energy.gov/articles/doe-releases-new-report-evaluating-increase-electricity-demand-data-centers"),
    dict(key="lbnl_2023", slide="1 (chart values)",
         text="U.S. data center energy use has continued to grow at an increasing rate, reaching 176 TWh by 2023, "
              "representing 4.4% of total U.S. electricity consumption.",
         who="Shehabi et al., Lawrence Berkeley National Laboratory, Dec. 2024",
         source="2024 United States Data Center Energy Usage Report (LBNL-2001637), Executive Summary, p. 5",
         url="https://eta-publications.lbl.gov/sites/default/files/2024-12/lbnl-2024-united-states-data-center-energy-usage-report_1.pdf"),
    dict(key="lbnl_2028", slide="1 (chart values)",
         text="This annual energy use also represents 6.7% to 12.0% of total U.S. electricity consumption forecasted for 2028.",
         who="Shehabi et al., Lawrence Berkeley National Laboratory, Dec. 2024",
         source="2024 United States Data Center Energy Usage Report, Executive Summary, p. 6",
         url="https://eta-publications.lbl.gov/sites/default/files/2024-12/lbnl-2024-united-states-data-center-energy-usage-report_1.pdf"),
    dict(key="lbnl_water", slide="unused",
         text="However, the water evaporation process in cooling towers has raised concerns regarding data center water "
              "consumption and availability at the local level.",
         who="Shehabi et al., Lawrence Berkeley National Laboratory, Dec. 2024",
         source="2024 United States Data Center Energy Usage Report, cooling-system table, p. 41",
         url="https://eta-publications.lbl.gov/sites/default/files/2024-12/lbnl-2024-united-states-data-center-energy-usage-report_1.pdf"),
    dict(key="wa_load_growth", slide="unused",
         text="Data centers are the largest source of expected load growth in the Pacific Northwest.",
         who="Washington Data Center Workgroup, Preliminary Report, Dec. 2025",
         source="Data Center Workgroup: Preliminary Report, Finding 6, p. 10",
         url="https://dor.wa.gov/sites/default/files/2025-12/2025DataCntrWrkgrpPrelimReport.pdf"),
    dict(key="wa_utc", slide="unused",
         text="Planning now will help the UTC protect customers and ensure electric services stay safe, equitable, "
              "available, reliable, and fairly priced as demand grows.",
         who="Washington Utilities and Transportation Commission, July 28, 2026 (docket UE-260162; covers "
             "investor-owned utilities, not Grant PUD)",
         source="Media advisory: UTC workshop on emerging large electric loads, paragraph 2",
         url="https://www.utc.wa.gov/news/2026/media-advisory-public-invited-join-utc-workshop-emerging-large-electric-loads"),
    dict(key="bpa_nlsl", slide="unused",
         text="…the customer must serve that load, and any increases to it, with either power from Bonneville at "
              "the NR rate or a dedicated nonfederal resource.",
         who="Bonneville Power Administration, Fact Sheet: New large single load, Oct. 2020",
         source="Fact sheet DOE/BP-5045, p. 2",
         url="https://www.bpa.gov/-/media/Aep/about/publications/fact-sheets/fs-202011-New-Large-Single-Load.pdf"),
    dict(key="wa_siting", slide="unused",
         text="Developers can avoid and minimize environmental and other community impacts through coordinated "
              "planning … when designing projects and choosing project sites.",
         who="Washington Data Center Workgroup, Preliminary Report, Dec. 2025",
         source="Data Center Workgroup: Preliminary Report, Finding 18b, p. 13",
         url="https://dor.wa.gov/sites/default/files/2025-12/2025DataCntrWrkgrpPrelimReport.pdf"),
]
QUOTES = {q["key"]: q for q in QUOTE_BANK}

# Openly licensed photos, licenses read on each Commons file page on 2026-10-04. Not placed on a slide:
# every main slide already carries a chart. Listed in sources.md for a swap.
PHOTOS = {
    "Wanapum Dam": dict(credit="Photo: Williamborg, public domain, via Wikimedia Commons", license="Public domain",
                        page="https://commons.wikimedia.org/wiki/File:Wanapum_Dam_from_West_Shore_-_downstream_10360031.jpg"),
    "Quincy, WA aerial": dict(credit="Photo: Tedder, CC BY-SA 4.0, via Wikimedia Commons", license="CC BY-SA 4.0",
                              page="https://commons.wikimedia.org/wiki/File:Quincy_Washington_-_aerial.jpg"),
    "US at night, 2012": dict(credit="Image: NASA Scientific Visualization Studio, public domain", license="Public domain",
                              page="https://commons.wikimedia.org/wiki/File:Earth_at_Night_2012_(SVS30028_-_nightlights2012-united_states_4104).png"),
    "Liquid-cooled HPC data center, NREL ESIF": dict(
        credit="Photo: Dennis Schroeder, NREL / U.S. Department of Energy, public domain, via Wikimedia Commons",
        license="Public domain as a DOE posting (NREL is contractor-run; confirm before use)",
        page="https://commons.wikimedia.org/wiki/File:U.S._Department_of_Energy_-_Science_-_298_029_005_(31681202785).jpg"),
    "Priest Rapids Dam spillway, 1973": dict(
        credit="Photo: David Falconer, U.S. EPA DOCUMERICA / National Archives, public domain", license="Public domain",
        page="https://commons.wikimedia.org/wiki/File:THE_SPILLWAY_AT_PRIEST_RAPODS_DAM_-_NARA_-_548016.jpg"),
}


# ---------------------------------------------------------------------------
# Low-level helpers
# ---------------------------------------------------------------------------
def set_theme(prs):
    """Arial everywhere and the palette as theme colors, so new shapes match."""
    part = prs.slide_master.part.part_related_by(RT.THEME)
    root = etree.fromstring(part.blob)
    a = "http://schemas.openxmlformats.org/drawingml/2006/main"
    for tag in ("majorFont", "minorFont"):
        for el in root.iter(f"{{{a}}}{tag}"):
            el.find(f"{{{a}}}latin").set("typeface", FONT)
    scheme = {"dk1": INK, "lt1": WHITE, "dk2": NAVY, "lt2": GROUND,
              "accent1": NAVY, "accent2": BLUE, "accent3": EMBER, "accent4": GREY,
              "accent5": RGBColor(0x14, 0x75, 0x8F), "accent6": GREEN}
    clr = root.find(f".//{{{a}}}clrScheme")
    clr.set("name", "Site engine")
    for name, rgb in scheme.items():
        el = clr.find(f"{{{a}}}{name}")
        for child in list(el):
            el.remove(child)
        etree.SubElement(el, f"{{{a}}}srgbClr", val=str(rgb))
    part._blob = etree.tostring(root, xml_declaration=True, encoding="UTF-8", standalone=True)


def style_run(run, size, color=INK, bold=False, italic=False):
    f = run.font
    f.name = FONT
    f.size = Pt(size)
    f.bold = bold
    f.italic = italic
    f.color.rgb = color


def textbox(slide, x, y, w, h, text, size=20, color=INK, bold=False, italic=False,
            align=PP_ALIGN.LEFT, anchor=MSO_ANCHOR.TOP, name=None, wrap=True):
    """A real text box. `text` may be a string or a list of (text, overrides) runs per paragraph."""
    tb = slide.shapes.add_textbox(x, y, w, h)
    if name:
        tb.name = name
    tf = tb.text_frame
    tf.word_wrap = wrap
    tf.vertical_anchor = anchor
    tf.margin_left = tf.margin_right = Inches(0.04)
    tf.margin_top = tf.margin_bottom = Inches(0.02)
    paras = text if isinstance(text, list) else [text]
    for i, para in enumerate(paras):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.alignment = align
        runs = para if isinstance(para, list) else [(para, {})]
        for t, o in runs:
            r = p.add_run()
            r.text = t
            style_run(r, o.get("size", size), o.get("color", color), o.get("bold", bold), o.get("italic", italic))
        if i > 0:
            p.space_before = Pt(6)
    return tb


def bullets(slide, x, y, w, h, items, size=22, color=INK, gap=14):
    """At most three bullets, each a real paragraph with a bullet character."""
    assert len(items) <= 3, "three bullets at most"
    tb = slide.shapes.add_textbox(x, y, w, h)
    tb.name = "Bullets"
    tf = tb.text_frame
    tf.word_wrap = True
    tf.margin_left = tf.margin_right = Inches(0.04)
    for i, item in enumerate(items):
        assert len(item.split()) < 12, f"bullet over 11 words: {item}"
        no_marks(item, "bullet")
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.line_spacing = 1.05
        p.space_after = Pt(gap)
        pPr = p._p.get_or_add_pPr()
        pPr.set("marL", str(Inches(0.32)))
        pPr.set("indent", str(-Inches(0.32)))
        buClr = etree.SubElement(pPr, qn("a:buClr"))
        etree.SubElement(buClr, qn("a:srgbClr"), val=str(NAVY))
        etree.SubElement(pPr, qn("a:buSzPct"), val="100000")
        etree.SubElement(pPr, qn("a:buFont"), typeface=FONT)
        etree.SubElement(pPr, qn("a:buChar"), char="■")
        r = p.add_run()
        r.text = item
        style_run(r, size, color)
    return tb


def no_style(shape):
    """Drop the theme style reference, so no theme shadow or outline applies. Fill and line are explicit."""
    style = shape._element.find(qn("p:style"))
    if style is not None:
        shape._element.remove(style)


def hline(slide, x, y, w, color=RULE, weight=0.75, name="Rule"):
    """A hairline drawn as a thin filled rectangle, which renders the same everywhere."""
    return rect(slide, x, y, w, Emu(int(Pt(weight))), fill=color, name=name)


def rect(slide, x, y, w, h, fill=None, line=None, shape=MSO_SHAPE.RECTANGLE, line_w=1.0, dash=False, name=None):
    s = slide.shapes.add_shape(shape, x, y, w, h)
    if name:
        s.name = name
    if fill is None:
        s.fill.background()
    else:
        s.fill.solid()
        s.fill.fore_color.rgb = fill
    if line is None:
        s.line.fill.background()
    else:
        s.line.color.rgb = line
        s.line.width = Pt(line_w)
        if dash:
            s.line.dash_style = 4  # MSO_LINE.DASH
    no_style(s)
    if shape == MSO_SHAPE.ROUNDED_RECTANGLE:
        s.adjustments[0] = 0.12
    return s


def shape_text(s, paras, size=16, color=INK, bold=False, align=PP_ALIGN.CENTER, anchor=MSO_ANCHOR.MIDDLE, margin=0.08):
    tf = s.text_frame
    tf.word_wrap = True
    tf.vertical_anchor = anchor
    tf.margin_left = tf.margin_right = Inches(margin)
    tf.margin_top = tf.margin_bottom = Inches(0.04)
    paras = paras if isinstance(paras, list) else [paras]
    for i, para in enumerate(paras):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.alignment = align
        runs = para if isinstance(para, list) else [(para, {})]
        for t, o in runs:
            r = p.add_run()
            r.text = t
            style_run(r, o.get("size", size), o.get("color", color), o.get("bold", bold), o.get("italic", False))
    return s


def picture_fit(slide, path, x, y, w, h, align="center"):
    iw, ih = Image.open(path).size
    scale = min(w / iw, h / ih)
    pw, ph = int(iw * scale), int(ih * scale)
    px = x + (w - pw) // 2 if align == "center" else x
    py = y + (h - ph) // 2
    pic = slide.shapes.add_picture(str(path), px, py, pw, ph)
    return pic


def placeholder_box(slide, x, y, w, h, label, slide_id):
    s = rect(slide, x, y, w, h, fill=GROUND, line=INK3, dash=True, name="Placeholder")
    shape_text(s, label, size=16, color=INK2)
    PLACEHOLDERS.append((slide_id, label))
    return s


def bar_chart(slide, x, y, w, h, cats, vals, colors, title=None, fmt_code="#,##0", horizontal=True,
              max_val=None, cat_size=16, label_size=18, gap=45, labels=None):
    cd = CategoryChartData()
    cd.categories = cats
    cd.add_series("Value", vals)
    for text in [title or ""] + list(cats):
        no_marks(text, "chart text")
    kind = XL_CHART_TYPE.BAR_CLUSTERED if horizontal else XL_CHART_TYPE.COLUMN_CLUSTERED
    gf = slide.shapes.add_chart(kind, x, y, w, h, cd)
    ch = gf.chart
    ch.has_legend = False
    ch.font.name = FONT
    ch.font.size = Pt(cat_size)
    ch.font.color.rgb = INK2
    if title:
        ch.has_title = True
        tf = ch.chart_title.text_frame
        tf.text = title
        for p in tf.paragraphs:
            p.alignment = PP_ALIGN.LEFT
            for r in p.runs:
                style_run(r, 18, INK, bold=True)
    else:
        ch.has_title = False
    plot = ch.plots[0]
    plot.gap_width = gap
    plot.vary_by_categories = False
    ser = plot.series[0]
    for i, c in enumerate(colors):
        pt = ser.points[i]
        pt.format.fill.solid()
        pt.format.fill.fore_color.rgb = c
    plot.has_data_labels = True
    dl = plot.data_labels
    dl.number_format = fmt_code
    dl.number_format_is_linked = False
    dl.position = XL_LABEL_POSITION.OUTSIDE_END
    dl.font.size = Pt(label_size)
    dl.font.bold = True
    dl.font.color.rgb = INK
    if labels:  # custom label text per point, still editable
        for i, t in enumerate(labels):
            if t is None:
                continue
            tf = ser.points[i].data_label.text_frame
            tf.text = t
            for r in tf.paragraphs[0].runs:
                style_run(r, label_size, INK, bold=True)
            ser.points[i].data_label.position = XL_LABEL_POSITION.OUTSIDE_END
    va = ch.value_axis
    va.has_major_gridlines = False
    va.visible = False
    va.minimum_scale = 0
    if max_val:
        va.maximum_scale = max_val
    ca = ch.category_axis
    ca.tick_labels.font.size = Pt(cat_size)
    ca.tick_labels.font.color.rgb = INK
    ca.major_tick_mark = XL_TICK_MARK.NONE
    ca.format.line.color.rgb = RULE
    if horizontal:
        ca.reverse_order = True
    return ch


def rank_chart(slide, x, y, w, h, stages, series, title, max_rank, log=False):
    """Native line chart of ranks, #1 at the top. Each series: (name, ranks, color, labels, positions)."""
    pos = {"above": XL_LABEL_POSITION.ABOVE, "below": XL_LABEL_POSITION.BELOW,
           "left": XL_LABEL_POSITION.LEFT, "right": XL_LABEL_POSITION.RIGHT}
    cd = CategoryChartData()
    cd.categories = stages
    for name, ranks, *_ in series:
        cd.add_series(name, ranks)
    ch = slide.shapes.add_chart(XL_CHART_TYPE.LINE_MARKERS, x, y + Inches(0.45), w, h - Inches(0.45), cd).chart
    ch.has_legend = False
    ch.font.name = FONT
    ch.font.size = Pt(16)
    ch.has_title = False  # the title sits in a text box above, clear of the rank-1 labels
    textbox(slide, x, y, w, Inches(0.4), title, size=18, bold=True, align=PP_ALIGN.CENTER)
    va = ch.value_axis
    va.reverse_order = True
    va.crosses = XL_AXIS_CROSSES.MAXIMUM  # keeps the category axis at the bottom
    va.minimum_scale = 0.6 if log else -2  # headroom above rank 1 for its label
    if log:  # a log scale shows rank 1 and rank 1,164 on one chart without clipping
        scaling = va._element.find(qn("c:scaling"))
        scaling.insert(0, etree.Element(qn("c:logBase"), val="10"))
    va.maximum_scale = max_rank
    va.has_major_gridlines = False
    va.visible = False
    ca = ch.category_axis
    ca.tick_labels.font.size = Pt(15)
    ca.tick_labels.font.color.rgb = INK
    ca.major_tick_mark = XL_TICK_MARK.NONE
    ca.format.line.color.rgb = RULE
    for ser, (name, ranks, color, labels, where) in zip(ch.plots[0].series, series):
        ser.smooth = False
        ser.format.line.color.rgb = color
        ser.format.line.width = Pt(4)
        ser.marker.style = XL_MARKER_STYLE.CIRCLE
        ser.marker.size = 13
        ser.marker.format.fill.solid()
        ser.marker.format.fill.fore_color.rgb = color
        ser.marker.format.line.color.rgb = color
        for i, (t, wpos) in enumerate(zip(labels, where)):
            dl = ser.points[i].data_label
            dl.text_frame.text = t
            for r in dl.text_frame.paragraphs[0].runs:
                style_run(r, 17, color, bold=True)
            dl.position = pos[wpos]
    return ch




def no_marks(text, where):
    """Slide text stays plain: no colons, semicolons, or em dashes."""
    bad = [c for c in (":", ";", "—") if c in text]
    assert not bad, f"{where} uses {bad}: {text}"
    return text


def frame(prs, headline, source, number, notes, checks=(), sources=()):
    """Blank slide with the headline, source line, rule, and slide number. Notes hold the script and sources."""
    no_marks(headline, f"slide {number} headline")
    no_marks(source, f"slide {number} source line")
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    bg = slide.background.fill
    bg.solid()
    bg.fore_color.rgb = WHITE
    rect(slide, MX, Inches(0.42), Inches(0.5), Inches(0.07), fill=NAVY, name="Accent")
    textbox(slide, MX, Inches(0.6), CW, Inches(1.25), headline, size=30, color=INK, bold=True, name="Headline",
            anchor=MSO_ANCHOR.TOP)
    hline(slide, MX, Inches(6.86), CW)
    textbox(slide, MX, Inches(6.92), CW - Inches(0.8), Inches(0.5), source, size=11, color=INK3, name="Source line")
    textbox(slide, W - MX - Inches(0.7), Inches(6.92), Inches(0.7), Inches(0.3), str(number), size=11, color=INK3,
            align=PP_ALIGN.RIGHT, name="Slide number")
    script = notes.strip().split("\n\nIf someone asks")[0]
    SCRIPT_WORDS[number] = len(script.replace("[Hand over to the live demo.]", "").split())
    lines = [notes.strip()]
    if checks:
        lines += ["", "Where the numbers come from. [[CHECK]] marks a number that could change tonight."]
        for what, value, f, field, check in checks:
            mark = " [[CHECK]]" if check else ", published source"
            lines.append(f"- {what}, {value}{mark} ({f}" + (f", {field})" if field else ")"))
            if check:
                CHECKS.append((number, what, value, f, field))
    if sources:
        lines += ["", "Outside sources"]
        lines.extend(f"- {s}" for s in sources)
        SOURCES[number] = list(sources)
    slide.notes_slide.notes_text_frame.text = "\n".join(lines)
    return slide


def quote_block(slide, x, y, w, h, q, size=20):
    """A verified quote, with a short citation on its own line."""
    rect(slide, x, y, w, h, fill=GROUND, name="Quote")
    rect(slide, x, y, Inches(0.08), h, fill=NAVY, name="Quote bar")
    return textbox(slide, x + Inches(0.3), y + Inches(0.1), w - Inches(0.5), h - Inches(0.2),
                   [[("“" + q["text"] + "”", {"size": size})],
                    [(q.get("cite", q["who"]), {"size": 14, "color": INK2, "bold": True})]],
                   size=size, color=INK, name="Quote text", anchor=MSO_ANCHOR.MIDDLE)


def band(slide, y, h, text, fill=GROUND, color=NAVY, size=20, name="Band"):
    no_marks(text, "band")
    b = rect(slide, MX, y, CW, h, fill=fill, name=name)
    shape_text(b, text, size=size, bold=True, color=color, margin=0.3)
    return b


# ---------------------------------------------------------------------------
# Motion: a fade between slides, and a few builds that run on their own.
# ---------------------------------------------------------------------------
def add_motion(slide, steps=None, first_ms=400, step_ms=450, dur_ms=450):
    """Fade into the slide. If steps are given, fade each group in after the previous one, without clicks."""
    sld = slide._element
    tr = etree.SubElement(sld, qn("p:transition"), spd="med")
    etree.SubElement(tr, qn("p:fade"))
    if not steps:
        return
    counter = iter(range(1, 100000))

    def ctn(parent, **attrs):
        el = etree.SubElement(parent, qn("p:cTn"), id=str(next(counter)))
        for k, v in attrs.items():
            el.set(k, v)
        return el

    def cond(parent, **attrs):
        lst = etree.SubElement(parent, qn("p:stCondLst"))
        return etree.SubElement(lst, qn("p:cond"), **attrs)

    timing = etree.SubElement(sld, qn("p:timing"))
    tn_lst = etree.SubElement(timing, qn("p:tnLst"))
    root = ctn(etree.SubElement(tn_lst, qn("p:par")), dur="indefinite", restart="never", nodeType="tmRoot")
    seq = etree.SubElement(etree.SubElement(root, qn("p:childTnLst")), qn("p:seq"), concurrent="1", nextAc="seek")
    main = ctn(seq, dur="indefinite", nodeType="mainSeq")
    group_par = ctn(etree.SubElement(etree.SubElement(main, qn("p:childTnLst")), qn("p:par")), fill="hold")
    lst = etree.SubElement(group_par, qn("p:stCondLst"))
    etree.SubElement(lst, qn("p:cond"), delay="indefinite")
    on_begin = etree.SubElement(lst, qn("p:cond"), evt="onBegin", delay="0")
    etree.SubElement(on_begin, qn("p:tn"), val=main.get("id"))
    steps_parent = etree.SubElement(group_par, qn("p:childTnLst"))
    t = first_ms
    animated = []
    for group in steps:
        step = ctn(etree.SubElement(steps_parent, qn("p:par")), fill="hold")
        cond(step, delay=str(t))
        effects = etree.SubElement(step, qn("p:childTnLst"))
        for j, shape in enumerate(group):
            spid = str(shape.shape_id)
            eff = ctn(etree.SubElement(effects, qn("p:par")), presetID="10", presetClass="entr", presetSubtype="0",
                      fill="hold", grpId="0", nodeType="afterEffect" if j == 0 else "withEffect")
            cond(eff, delay="0")
            kids = etree.SubElement(eff, qn("p:childTnLst"))
            st = etree.SubElement(kids, qn("p:set"))
            bhvr = etree.SubElement(st, qn("p:cBhvr"))
            cond(ctn(bhvr, dur="1", fill="hold"), delay="0")
            etree.SubElement(etree.SubElement(bhvr, qn("p:tgtEl")), qn("p:spTgt"), spid=spid)
            names = etree.SubElement(bhvr, qn("p:attrNameLst"))
            etree.SubElement(names, qn("p:attrName")).text = "style.visibility"
            etree.SubElement(etree.SubElement(st, qn("p:to")), qn("p:strVal"), val="visible")
            fade = etree.SubElement(kids, qn("p:animEffect"), transition="in", filter="fade")
            fb = etree.SubElement(fade, qn("p:cBhvr"))
            ctn(fb, dur=str(dur_ms))
            etree.SubElement(etree.SubElement(fb, qn("p:tgtEl")), qn("p:spTgt"), spid=spid)
            animated.append(shape)
        t += step_ms
    for evt, tag in (("onPrev", "p:prevCondLst"), ("onNext", "p:nextCondLst")):
        c = etree.SubElement(etree.SubElement(seq, qn(tag)), qn("p:cond"), evt=evt, delay="0")
        etree.SubElement(etree.SubElement(c, qn("p:tgtEl")), qn("p:sldTgt"))
    bld = etree.SubElement(timing, qn("p:bldLst"))
    for shape in animated:
        if shape._element.tag == qn("p:sp"):
            etree.SubElement(bld, qn("p:bldP"), spid=str(shape.shape_id), grpId="0", animBg="1")


# ---------------------------------------------------------------------------
# Data
# ---------------------------------------------------------------------------
F = FACTS
B = F["balanced"]
TOP10 = F["top10"]
GRANT = F["featured"]
GR = F["grant_ranges"]
IMP = F["impact"]
W8 = F["weights"]
PS = F["pick_story"]
GL = F["global"]
UNI = W8["uniform_weightings_top10_share"]  # 5,000 Dirichlet draws, seed 0 (docs/figures/make_figures.py)

with open(ROOT / "results/balanced.csv") as fh:
    BAL = {r["fips"]: r for r in csv.DictReader(fh)}
GRANT_SCORE = float(BAL["53025"]["composite"])
WHITMAN_SCORE = float(BAL["53075"]["composite"])

# Typed-in figures from research write-ups and reruns (file named next to each).
PUD = {  # research/risk.md and research/implementation.md, from the Grant PUD FAQ (2026-08-28)
    "hydro_share_amw": 633, "load_2025_amw": 757, "campus_amw": 279, "queued_mw": 800}
TIE = {  # docs/weighting.md, Recommendation table, 25-year cost at $190/t with sales tax (dollar model, not affected by PR #40)
    "Clark, WA": 4.405, "Grant, WA": 4.452, "Franklin, NY": 4.454}
PRICE_RERUN = {80: 77, 132: 1151}  # build log step 4, balanced preset with only WA counties repriced
EVAP = {"passed": 826, "floor_ok": 502, "first": "Whitman, WA"}  # build log step 4 and docs/demo_script.md
PCTL = {"Grant, WA": (70.4, 93.6), "Franklin, NY": (80.4, 98.7)}  # build log step 4, energy and carbon pillar
FRANKLIN_CO2 = 262168  # research/impact.md, dry cooling table
LAND_BEFORE = {"land": 75.0, "permitting": 53.2}  # research/sensitive_land.md, Grant before PR #40
EC_SHARE = {"$0 per ton": 67, "$190 per ton": 78, "$300 per ton": 88}  # docs/weighting.md, energy plus carbon variance share
BALANCED_EC = 30  # docs/weighting.md, energy_carbon plus cost weight in the balanced preset
APP = DECK / "img"  # Streamlit screenshots taken for this deck (build log step 4)


def build():
    prs = Presentation()
    prs.slide_width, prs.slide_height = W, H
    set_theme(prs)
    for make in (slide_hook, slide_tool, slide_land, slide_example, slide_weights, slide_impact, slide_risk,
                 slide_plan, slide_switch, app_pick, app_tonnes, app_alternatives, app_sources, app_limits,
                 app_extends):
        make(prs)
    cp = prs.core_properties  # clear the library template's defaults
    cp.title = "Sustainable AI data center site selection"
    cp.author = ""
    cp.last_modified_by = ""
    cp.comments = ""
    cp.revision = 1
    out = DECK / "pitch_template.pptx"
    prs.save(out)
    write_checks()
    write_sources()
    print(f"wrote {out.relative_to(ROOT)}: {len(prs.slides)} slides, {len(CHECKS)} numbers to check")
    print("  script words (about 150 a minute, so 75 to 90 for 30 to 35 s):",
          ", ".join(f"{k} {v}" for k, v in SCRIPT_WORDS.items()))


# ---------------------------------------------------------------------------
# Main slides
# ---------------------------------------------------------------------------
def slide_hook(prs):
    q = QUOTES["ny_eo62"]
    s = frame(
        prs, "Where AI data centers get built locks in their carbon, water, and costs for decades",
        "Data from Lawrence Berkeley National Laboratory, 2024 United States Data Center Energy Usage Report, and New York "
        "Executive Order 62 (July 2026). Grid carbon range from research/impact.md. Links in docs/deck/sources.md.",
        1,
        notes="""
AI is driving a boom in data center construction. Lawrence Berkeley National Lab found that data
centers used 4.4 percent of US electricity in 2023, and it expects 6.7 to 12 percent by 2028.
Communities are pushing back on where these go. This summer New York paused state permits for
large data centers over energy and water. A campus built today runs for 20 to 30 years, so the
county you choose sets its carbon, its water, and its power bill for decades.
""",
        checks=[("US data center share of electricity in 2023", "4.4% (176 TWh)", "LBNL 2024 report, Executive Summary p. 5", None, False),
                ("Projected share in 2028", "6.7% to 12.0%", "LBNL 2024 report, Executive Summary p. 6", None, False),
                ("Grid carbon varies about fourfold across candidate counties", "242 to 911 lb/MWh",
                 "research/impact.md", "dry cooling table", True)],
        sources=[f"LBNL 2024 United States Data Center Energy Usage Report (Shehabi et al.), {QUOTES['lbnl_2023']['url']}",
                 f"New York Executive Order No. 62, {q['url']}"],
    )
    quote_block(s, MX, TOP, Inches(5.7), Inches(2.45), q, size=21)
    bullets(s, MX, TOP + Inches(2.7), Inches(5.7), Inches(1.8),
            ["A campus built today will run for 20 to 30 years.",
             "Grid carbon varies about fourfold between the counties we scored."], size=21, gap=10)
    bar_chart(s, MX + Inches(6.1), TOP, Inches(6.0), Inches(4.5),
              ["2023", "2028, low case", "2028, high case"], [4.4, 6.7, 12.0], [NAVY, BLUE, BLUE],
              title="Data centers' share of US power", fmt_code='0.0"%"', horizontal=False,
              max_val=14, cat_size=18, label_size=22, gap=60)
    add_motion(s)


def slide_tool(prs):
    s = frame(
        prs, f"Our tool ranks all {fmt(B['counties'])} counties for the project you describe",
        "Screenshot from the team's Streamlit app (app/app.py) with the balanced preset. Counts from "
        "docs/figures/facts.json. Weights from engine/conditions/balanced.yaml.",
        2,
        notes=f"""
So we built a tool for that choice. You describe the project, meaning its size, how it's cooled,
the limits you won't cross, and how much each factor matters to you. The tool screens all {fmt(B['counties'])}
counties in the lower 48. Hard limits like flood risk, wildfire, fiber, and the wait for a grid
connection rule out about half. Eight factors then score the rest against the nation, and a
county that's weak on any one of them drops below the others. You get a ranked shortlist, and
every rank comes with its reasons.

If someone asks whether this is machine learning, it isn't. The weights are stated and anyone
can change them. The only model we built was for permitting, and we dropped it because it failed
out of sample.
""",
        checks=[("Counties", fmt(B["counties"]), "docs/figures/facts.json", "balanced.counties", True),
                ("Counties that pass the hard limits", fmt(B["passed"]), "docs/figures/facts.json", "balanced.passed", True),
                ("Counties with no weak factor (pillar floor)", fmt(B["floor_ok"]), "docs/figures/facts.json", "balanced.floor_ok", True),
                ("Balanced weights", ", ".join(f"{k} {v:.3f}" for k, v in W8["balanced"].items()),
                 "docs/figures/facts.json", "weights.balanced", True)],
    )
    shot = picture_fit(s, APP / "app_overview.png", MX, TOP - Inches(0.05), Inches(5.6), Inches(3.3), align="left")
    shot.line.color.rgb = RULE
    shot.line.width = Pt(1)
    x = shot.left + shot.width + Inches(0.35)
    w = MX + CW - x
    steps = [(fmt(B["counties"]), "counties in the lower 48"),
             (fmt(B["passed"]), "pass hard limits like flood risk and fiber"),
             (fmt(B["floor_ok"]), "have no weak spot across eight factors"),
             ("Shortlist", "ranked, with the reasons behind each rank")]
    gap = Inches(0.12)
    bh = int((Inches(3.3) - gap * 3) / 4)
    shapes = []
    for i, (big, small) in enumerate(steps):
        y = TOP - Inches(0.05) + i * (bh + gap)
        b = rect(s, x, y, w, bh, fill=NAVY if i < 3 else BLUE, shape=MSO_SHAPE.ROUNDED_RECTANGLE, name=f"Step {i + 1}")
        shape_text(b, [[(big + "  ", {"size": 24, "bold": True, "color": WHITE}),
                        (small, {"size": 17, "color": WHITE})]], align=PP_ALIGN.LEFT, margin=0.2)
        shapes.append([b])
    textbox(s, MX, TOP + Inches(3.4), CW, Inches(0.4),
            "Eight factors, weighted however you choose. These are our balanced weights.", size=16, color=INK2, bold=True)
    cy = TOP + Inches(3.85)
    cg = Inches(0.1)
    cwid = int((CW - cg * 7) / 8)
    for i, (key, label, hue) in enumerate(PILLARS):
        c = rect(s, MX + i * (cwid + cg), cy, cwid, Inches(0.8), fill=hue, shape=MSO_SHAPE.ROUNDED_RECTANGLE,
                 name=f"Factor {label}")
        shape_text(c, [[(label.replace("&", "and"), {"size": 14, "bold": True, "color": WHITE})],
                       [(f"{int(W8['balanced'][key] * 100 + 0.5)}%", {"size": 18, "bold": True, "color": WHITE})]],
                   margin=0.04)
    add_motion(s, steps=shapes)


def slide_land(prs):
    after = GRANT["pillars"]
    s = frame(
        prs, "It now accounts for protected land, farmland, and wetlands",
        "Protected land from USGS PAD-US 4.1, land cover from NLCD 2021 through IPUMS NHGIS, tribal land from Census "
        "TIGER 2024. Grant's scores from docs/figures/facts.json and research/sensitive_land.md.",
        3,
        notes=f"""
The challenge asks about proximity to sensitive areas and ecosystems, so we added it. The tool now
reads how much of each county is protected for wildlife, how much is farmed, how much is built up,
and how much is forest or wetland, and each one now counts in the score. Grant shows the trade.
It's 43 percent cropland and 13 percent protected, so its land score fell from 75 to 53. It has
almost no forest or wetland, so permitting rose from 53 to 63.

If someone asks about farmland, large campuses often land on it because developers want flat,
big parcels near roads and transmission. That's a habit, not a need. Soil quality does nothing
for a data center, and old power plant sites or industrial parks can work as well. The tool
measures land cover, not prime soil. Building on farmland usually harms habitat less than wild
land does, but it uses up farmland, so we leave the balance to the user. In our opposition
dataset farmland comes up in 7 of 100 cases with stated reasons, mostly inferred from text. The
top reasons are zoning process, water, and grid strain.

If someone asks whether one input drives Grant's rank, scored alone protected land would drop
Grant to 4th and cropland alone to 2nd. Together, as designed, they offset. The protected and
tribal land limits are off in every preset.
""",
        checks=[("Grant land score before and after", f"{LAND_BEFORE['land']} to {after['land']}", "docs/figures/facts.json and research/sensitive_land.md", "featured.pillars.land", True),
                ("Grant permitting score before and after", f"{LAND_BEFORE['permitting']} to {after['permitting']}", "docs/figures/facts.json and research/sensitive_land.md", "featured.pillars.permitting", True),
                ("Grant cropland share", "42.9%", "research/sensitive_land.md", "County shares table", True),
                ("Grant protected share (GAP 1-2)", "12.8%", "research/sensitive_land.md", "County shares table", True),
                ("Grant rank with protected land alone or cropland alone", "4th or 2nd", "research/sensitive_land.md", "Effect on the balanced ranking", True),
                ("Farmland in opposition cases with stated reasons", "7 of 100", "data/processed/opposition_seed_labels.csv", "reasons column", True)],
    )
    bar_chart_clustered(s, MX, TOP - Inches(0.05), Inches(6.4), Inches(4.0), ["Land", "Permitting"],
                        [("Before land cover", [LAND_BEFORE["land"], LAND_BEFORE["permitting"]], GREY),
                         ("After land cover", [after["land"], after["permitting"]], NAVY)],
                        title="Grant County's scores out of 100", max_val=100)
    x = MX + Inches(6.8)
    w = CW - Inches(6.8)
    bullets(s, x, TOP + Inches(0.05), w, Inches(3.5),
            ["Protected land, farmland, and built-up land lower the land score.",
             "Forests and wetlands mean more permits, which lowers permitting.",
             "Users can also rule out protected or tribal land entirely."], size=20, gap=14)
    band(s, TOP + Inches(4.05), Inches(0.62),
         "Building on farmland spares wild habitat but uses up cropland. The tool lets you weigh both.", size=17)
    add_motion(s)


def slide_example(prs):
    s = frame(
        prs, "With balanced weights, two counties in eastern Washington tie for first",
        "Team engine, balanced preset (results/balanced.csv, docs/figures/facts.json). Map from "
        "docs/figures/map_composite.png. Grant PUD data center FAQ, August 2026.",
        4,
        notes=f"""
With balanced weights, Grant and Whitman counties in eastern Washington come out level, {GRANT_SCORE:.2f} to {WHITMAN_SCORE:.2f}. Under equal weights Whitman
comes first and Grant second. We use Grant as our worked example because it already hosts the
Quincy data center cluster, and its power timeline and tax status are documented. It comes with a
condition. The campus has to be sited next to hydro, powered by new clean supply the project
funds, because none of the utility's existing hydro is spare.

If someone asks why not Whitman, it's a fair alternative with almost no protected land and no
water stress. We don't have the same site research for it yet.
""",
        checks=[("Counties that pass the hard limits", fmt(B["passed"]), "docs/figures/facts.json", "balanced.passed", True),
                ("Grant composite", f"{GRANT_SCORE:.2f}", "results/balanced.csv", "composite", True),
                ("Whitman composite", f"{WHITMAN_SCORE:.2f}", "results/balanced.csv", "composite", True),
                ("Rank under equal weights", f"Grant {W8['equal_weights_featured_rank']}nd, Whitman 1st", "docs/figures/facts.json", "weights.equal_weights_featured_rank", True)],
        sources=["Grant PUD data center FAQ, 2026-08-28, https://www.grantpud.org/blog/data-center-faqs"],
    )
    pic = picture_fit(s, FIG / "map_composite.png", MX, TOP - Inches(0.05), Inches(6.4), Inches(4.6))
    map_overlays(s, pic)
    x = MX + Inches(6.75)
    w = CW - Inches(6.75)
    box = rect(s, x, TOP, w, Inches(1.5), fill=NAVY, name="Condition")
    shape_text(box, "Our example is Grant. It works only if the campus is sited next to hydro, powered by new "
                    "clean supply the project funds.", size=19, bold=True, color=WHITE, align=PP_ALIGN.LEFT, margin=0.22)
    bullets(s, x, TOP + Inches(1.8), w, Inches(2.6),
            [f"Grant scores {GRANT_SCORE:.2f} and Whitman {WHITMAN_SCORE:.2f} out of 100.",
             "Under equal weights Whitman comes first and Grant second.",
             "Grant already hosts the Quincy data center cluster."], size=20, gap=12)
    add_motion(s)


def slide_weights(prs):
    ranked = sorted(UNI.items(), key=lambda kv: -kv[1])
    names = [k for k, _ in ranked]
    vals = [v * 100 for _, v in ranked]
    colors = [NAVY if n == "Grant, WA" else BLUE for n in names]
    s = frame(
        prs, "Different weights favor different counties, so the tool shows the spread",
        "Top 10 shares from 5,000 random weightings of the eight factors (docs/figures/facts.json, computed by "
        "docs/figures/make_figures.py). Cost shares from the 25-year dollar model in docs/weighting.md.",
        5,
        notes=f"""
The obvious question is whether we picked weights that make our example win. So we stopped
choosing. We drew 5,000 random weightings and counted how often each county makes the top 10.
Whitman does most often, at {UNI['Whitman, WA'] * 100:.1f} percent, and Grant sits in a close group
around 36 percent. Near our own weights Grant stays in the top 10 almost every time. When we priced
every county in dollars, energy and carbon drove most of the differences. We didn't tune the weights to get an answer. We tested
how much the answer depends on them.

If someone asks why these weights, we compared five methods. A 25-year dollar model, random
weightings, two data-driven methods, and where industry has already built. Energy and carbon carry
67 to 88 percent of the dollar differences, depending on the carbon price. Our balanced weights give
them about 30 percent.
""",
        checks=[(f"Top 10 share, {n}", f"{v:.1f}%", "docs/figures/facts.json", "weights.uniform_weightings_top10_share", True)
                for n, v in zip(names, vals)]
        + [("Grant in the top 10 near balanced weights", pct(GRANT["robustness"], 2), "docs/figures/facts.json", "featured.robustness (2,000 small perturbations)", True),
           ("Energy and carbon share of 25-year cost differences", "67% to 88%", "docs/weighting.md", "Variance shares, with sales tax", False),
           ("Energy and carbon weight in the balanced preset", "about 30%", "docs/weighting.md", "Variance shares", True)],
    )
    bar_chart(s, MX, TOP - Inches(0.05), Inches(6.6), Inches(3.75), names, vals, colors,
              title="How often each county makes the top 10", fmt_code='0.0"%"', max_val=55, cat_size=17)
    x = MX + Inches(6.95)
    w = CW - Inches(6.95)
    bullets(s, x, TOP + Inches(0.05), w, Inches(3.4),
            ["No county makes the top 10 under most weightings.",
             f"Near our chosen weights, Grant stays in the top 10 ({pct(GRANT['robustness'], 2)}).",
             "Energy and carbon drive most cost differences between counties."], size=20, gap=14)
    band(s, TOP + Inches(3.9), Inches(0.62),
         "We didn't tune weights to get an answer. We tested how much it depends on them.", size=18)
    add_motion(s)


def slide_impact(prs):
    co2_bpa = GR["co2_tonnes"]["bpa"]
    co2_nw = GR["co2_tonnes"]["nwpp_table"]
    lou = IMP["Loudoun, VA"]
    gi = IMP["Grant, WA"]
    cut = 1 - gi["water_million_gal_dry"] / gi["water_million_gal_evap"]
    s = frame(
        prs, f"A dry-cooled campus in Grant would use {cut * 100:.0f}% less water",
        "Modeled with etl/impact.py (300 MW IT, load factor 0.8, PUE and WUE after Lei and Masanet) using eGRID2023. "
        "Quote from the Washington Data Center Workgroup preliminary report, December 2025.",
        6,
        notes=f"""
Against Loudoun County, Virginia, where much of the industry builds today, the example holds up
well on water. An evaporatively cooled campus in Grant would use about
{gi['water_million_gal_evap']:.0f} million gallons of water a year. Dry cooling brings that to about
{gi['water_million_gal_dry']:.0f} million, an {cut * 100:.0f} percent cut, for about 2 percent more
energy. Carbon depends on the power that serves the campus. Before its own clean supply comes
online, it's {co2_bpa / 1000:.0f} to {co2_nw / 1000:.0f} thousand tons a year, against Loudoun's
{lou['co2_tonnes_dry'] / 1000:.0f} thousand. Washington law then requires fully clean retail power by 2045.

If someone asks why not zero carbon, the utility's hydro rate of zero describes its existing
customers. None of that hydro is spare for a new load, so we don't claim it. If someone asks
whether 2045 is an edge over Virginia, it isn't. Virginia's Clean Economy Act also sets 2045 for
Dominion (not verified for this deck). The difference is the new supply the project funds.
""",
        checks=[("Grant water, evaporative", f"{gi['water_million_gal_evap']} million gallons a year", "docs/figures/facts.json", "impact['Grant, WA'].water_million_gal_evap", True),
                ("Grant water, dry", f"{gi['water_million_gal_dry']} million gallons a year", "docs/figures/facts.json", "impact['Grant, WA'].water_million_gal_dry", True),
                ("Loudoun water, evaporative", f"{lou['water_million_gal_evap']} million gallons a year", "docs/figures/facts.json", "impact['Loudoun, VA'].water_million_gal_evap", True),
                ("Water cut, dry against evaporative", f"{cut * 100:.0f}%", "computed from the two Grant values", None, True),
                ("Grant CO2 at BPA's mix", f"{fmt(co2_bpa)} t a year", "docs/figures/facts.json", "grant_ranges.co2_tonnes.bpa", True),
                ("Grant CO2 at the regional average", f"{fmt(co2_nw)} t a year", "docs/figures/facts.json", "grant_ranges.co2_tonnes.nwpp_table", True),
                ("Loudoun CO2, dry", f"{fmt(lou['co2_tonnes_dry'])} t a year", "docs/figures/facts.json", "impact['Loudoun, VA'].co2_tonnes_dry", True),
                ("Dry cooling energy penalty", "about 2%", "research/risk.md", "Water stress row", True),
                ("Washington clean power dates", "2030 neutral, 2045 fully clean", "research/implementation.md", "Carbon over 30 years", False)],
        sources=["Washington Clean Energy Transformation Act, RCW 19.405.040 and 19.405.050, https://app.leg.wa.gov/RCW/default.aspx?cite=19.405",
                 f"Washington Data Center Workgroup, Preliminary Report, Finding 19, p. 13, {QUOTES['wa_water']['url']}"],
    )
    half = int((CW - Inches(0.5)) / 2)
    bar_chart(s, MX, TOP - Inches(0.05), half, Inches(3.15),
              ["Loudoun VA, evaporative", "Grant, evaporative", "Grant, dry (+2% energy)"],
              [lou["water_million_gal_evap"], gi["water_million_gal_evap"], gi["water_million_gal_dry"]],
              [GREY, BLUE, NAVY], title="On-site water, million gallons a year", max_val=400, cat_size=15)
    bar_chart(s, MX + half + Inches(0.5), TOP - Inches(0.05), half, Inches(3.15),
              ["Loudoun VA", "Grant at the regional average", "Grant at BPA's mix"],
              [lou["co2_tonnes_dry"] / 1000, co2_nw / 1000, co2_bpa / 1000],
              [GREY, BLUE, NAVY], title="CO2, thousand metric tons a year", max_val=850, cat_size=15)
    quote_block(s, MX, TOP + Inches(3.22), half, Inches(1.38), QUOTES["wa_water"], size=17)
    bullets(s, MX + half + Inches(0.5), TOP + Inches(3.35), half, Inches(1.1),
            ["Carbon depends on the clean power the project brings online."], size=19)
    add_motion(s)


def slide_risk(prs):
    p = PUD
    s = frame(
        prs, "Power is the biggest risk, so the project has to bring its own",
        "Grant PUD data center FAQ, August 2026. Risk ratings from research/risk.md. Land check from "
        "research/sensitive_land.md (PAD-US 4.1, Census TIGER 2024). Timing from docs/weighting.md.",
        7,
        notes=f"""
For our example, one risk stands out, and it's power. Grant PUD's share of its dams averages about
{p['hydro_share_amw']} average megawatts, already below its {p['load_2025_amw']} megawatt load. The
campus would add {p['campus_amw']}, and about {p['queued_mw']} megawatts of requests are ahead of it. So the
project funds new supply and phases in behind the 2027 and 2029 transmission lines. Heat is a medium
risk. Land is low, with no protected land within 5 kilometers of Quincy, and tribal consultation
starts early. The example holds only if full power arrives by about late 2029, near today's price.

If someone asks about price, a new load this size doesn't get today's average rate. If we reprice
only Washington at BPA's new-load rate of $80 a megawatt-hour, Grant falls to {PRICE_RERUN[80]}th, and
Whitman falls with it. No other state's new-load rate is sourced, so that comparison is lopsided.

If someone asks about timing, each month of delay is priced at $25 million in the dollar model, which
is an assumption. Grant breaks even with Clark at about 10 months past a two-year baseline and with
Franklin at about 12.

If someone asks about tribal land, there's none in Grant County and the nearest is about 75 km away.
Quincy appears to sit in the Yakama Nation's 1855 ceded area, but that's our reading of the treaty
text, not an official map. A federal connection, like a federal permit or a BPA interconnection,
triggers Section 106 consultation, and state funding triggers Washington Executive Order 21-02 review.
Washington's data center workgroup also notes that new load on hydropower competes with tribal and
state fisheries efforts, which is one more reason we don't claim existing hydro.
""",
        checks=[("Grant PUD share of its dams", f"about {p['hydro_share_amw']} aMW", "research/risk.md (Grant PUD FAQ)", "Power availability row", False),
                ("Grant PUD 2025 load", f"{p['load_2025_amw']} aMW", "research/risk.md (Grant PUD FAQ)", "Power availability row", False),
                ("Campus average load", f"{p['campus_amw']} aMW", "research/risk.md and etl/impact.py", "Power availability row", True),
                ("Large-load requests queued", f"about {p['queued_mw']} MW", "research/risk.md (Grant PUD FAQ)", "Power availability row", False),
                ("Days above 95°F", f"{GRANT['horizon_2050_raw']['days_above_95f_hist']['today']:.1f} today, "
                 f"{GRANT['horizon_2050_raw']['days_above_95f_hist']['days_above_95f_2050_rcp85']:.1f} by 2050",
                 "docs/figures/facts.json", "featured.horizon_2050_raw.days_above_95f_hist", True),
                ("Nearest protected land to Quincy", "5.8 km", "research/sensitive_land.md", "Grant County table", True),
                ("Nearest tribal land to Quincy", "74.7 km", "research/sensitive_land.md", "Grant County table", True),
                ("Grant rank with only WA at BPA's $80 and $132 per MWh", f"{PRICE_RERUN[80]} and {fmt(PRICE_RERUN[132])}",
                 "docs/deck_build_log.md", "step 4 price rerun", True),
                ("Delay cost", "$25M a month (assumption)", "docs/weighting.md", "Time to power", True),
                ("Grant break-even with Clark and Franklin", "10.2 and 12.1 months past a 2-year baseline", "docs/weighting.md", "Grant's row", True)],
        sources=["Grant PUD data center FAQ, 2026-08-28, https://www.grantpud.org/blog/data-center-faqs",
                 f"Washington Data Center Workgroup, Preliminary Report, Findings 6 and 19c, {QUOTES['wa_load_growth']['url']}"],
    )
    bar_chart(s, MX, TOP - Inches(0.05), Inches(5.6), Inches(3.5),
              ["Utility's share of its dams", "Utility load in 2025", "Load plus the campus"],
              [p["hydro_share_amw"], p["load_2025_amw"], p["load_2025_amw"] + p["campus_amw"]],
              [BLUE, GREY, EMBER], title="Grant PUD, average megawatts", max_val=1300, cat_size=16, label_size=18)
    x = MX + Inches(5.95)
    w = CW - Inches(5.95)
    rows = [("High", EMBER, f"Power. The dams are spoken for, and {p['queued_mw']} MW of requests wait in line."),
            ("Medium", AMBER, "Heat. Days above 95°F rise from 14 to 36 by 2050."),
            ("Low", GREEN, "Land. No protected land within 5 km, and tribal consultation starts early.")]
    for i, (lvl, c, text) in enumerate(rows):
        no_marks(text, "risk row")
        y = TOP + i * Inches(1.17)
        chip = rect(s, x, y + Inches(0.2), Inches(1.2), Inches(0.5), fill=c, shape=MSO_SHAPE.ROUNDED_RECTANGLE, name=f"Risk {lvl}")
        shape_text(chip, lvl, size=15, bold=True, color=WHITE)
        textbox(s, x + Inches(1.4), y, w - Inches(1.4), Inches(0.95), text, size=19, color=INK, anchor=MSO_ANCHOR.MIDDLE)
    band(s, TOP + Inches(3.65), Inches(0.9),
         "The example holds only if full power arrives by about late 2029, near today's price.",
         fill=NAVY, color=WHITE, size=20)
    add_motion(s)


def slide_plan(prs):
    s = frame(
        prs, "The campus would grow with new transmission and new clean power",
        "Plan from research/implementation.md (Columbia Basin Herald, Rye Development, RCW 19.405, ASHRAE liquid "
        "cooling classes, Ramboll on Odense). Quote from Grant PUD's data center FAQ, August 2026.",
        8,
        notes="""
So the build starts small, behind the utility's queue. A first phase
comes online after Quincy's 2027 transmission upgrade, and the campus grows toward 300 megawatts
after the 2029 line, only as new supply it pays for comes online. About a gigawatt of new solar
matches its yearly use, though not every hour, so firm clean power like pumped storage follows in
the 2030s. Liquid cooling with dry coolers handles hotter 2050 summers, and the warm return water
heats a food processor next door.
""",
        checks=[("Transmission milestones", "2027 Quincy upgrade, 2029 Wanapum to Quincy line", "research/implementation.md", "The queue and the caps", False),
                ("New solar to match yearly use", "about 1 GW (1,030 MW at 27% capacity factor)", "research/implementation.md", "Where new clean supply comes from", True),
                ("Goldendale pumped storage", "1.2 GW, 2031 to 2032", "research/implementation.md", "Where new clean supply comes from", False),
                ("Dry cooling water", f"{IMP['Grant, WA']['water_million_gal_dry']} million gallons a year", "docs/figures/facts.json", "impact['Grant, WA'].water_million_gal_dry", True),
                ("Liquid cooling return water", "45 to 65°C", "research/implementation.md", "Cooling and water, Heat reuse", False)],
        sources=[f"Grant PUD Data Center FAQs, Q5, {QUOTES['pud_pays']['url']}"],
    )
    ms = [("2027", "Quincy transmission upgrade, first phase online"),
          ("2029", "Wanapum to Quincy line, grow toward 300 MW"),
          ("2030", "State law requires carbon-neutral utility sales"),
          ("2030s", "Firm clean power such as pumped storage"),
          ("2045", "State law requires 100% clean retail power")]
    y_line = TOP + Inches(0.6)
    hline(s, MX + Inches(0.3), y_line - Emu(int(Pt(1.5))), CW - Inches(0.6), color=NAVY, weight=3, name="Timeline")
    slot = int(CW / len(ms))
    steps = []
    for i, (yr, text) in enumerate(ms):
        no_marks(text, "timeline")
        cx = MX + i * slot + slot // 2
        dot = rect(s, cx - Inches(0.14), y_line - Inches(0.14), Inches(0.28), Inches(0.28), fill=NAVY if i < 2 else BLUE,
                   shape=MSO_SHAPE.OVAL, name=f"Milestone {yr}")
        year = textbox(s, cx - slot // 2, TOP - Inches(0.15), slot, Inches(0.5), yr, size=24, bold=True, color=NAVY,
                       align=PP_ALIGN.CENTER, name=f"Year {yr}")
        label = textbox(s, cx - slot // 2 + Inches(0.08), y_line + Inches(0.22), slot - Inches(0.16), Inches(0.85), text,
                        size=16, color=INK, align=PP_ALIGN.CENTER, name=f"Milestone text {yr}")
        steps.append([dot, year, label])
    cards = [("Power", "About 1 GW of new solar to match yearly use"),
             ("Cooling", f"Liquid cooling with dry coolers, about {IMP['Grant, WA']['water_million_gal_dry']:.0f} million gallons a year"),
             ("Heat", "Warm return water heats a neighboring food processor")]
    cg = Inches(0.3)
    cwid = int((CW - cg * 2) / 3)
    cy = TOP + Inches(1.85)
    for i, (head, text) in enumerate(cards):
        no_marks(text, "card")
        c = rect(s, MX + i * (cwid + cg), cy, cwid, Inches(1.45), fill=GROUND, name=f"Card {head}")
        rect(s, MX + i * (cwid + cg), cy, cwid, Inches(0.07), fill=NAVY, name="Card rule")
        shape_text(c, [[(head, {"size": 16, "bold": True, "color": NAVY})], [(text, {"size": 19})]],
                   align=PP_ALIGN.LEFT, anchor=MSO_ANCHOR.MIDDLE, margin=0.22)
    quote_block(s, MX, TOP + Inches(3.45), CW, Inches(1.15), QUOTES["pud_pays"], size=17)
    add_motion(s, steps=steps, first_ms=500, step_ms=400)


def slide_switch(prs):
    s = frame(
        prs, "Change one assumption and the tool gives a new answer with its reasons",
        "Screenshot from the team's Streamlit app (app/app.py), balanced preset with evaporative cooling. Counts "
        "rerun with the engine (docs/deck_build_log.md step 4). Water stress from WRI Aqueduct 4.0.",
        9,
        notes=f"""
That brings us back to the tool. Watch what one change does. Switch the cooling from dry to
evaporative, and the tool adds a limit on water stress. The counties that pass drop from
{fmt(B['passed'])} to {fmt(EVAP['passed'])}. Grant scores 3.6 out of 5 for water stress, so it drops out,
and the app tells you exactly which limit it failed. Whitman, with almost no water stress, moves to
first. Same data, a new answer, with its reasons. Let us show you. [Hand over to the live demo.]

If someone asks about the other presets, speed to power puts Mayes, Oklahoma first, and
sustainability first keeps Whitman first with Grant fourth.
""",
        checks=[("Counties that pass, dry cooling", fmt(B["passed"]), "docs/figures/facts.json", "balanced.passed", True),
                ("Counties that pass, evaporative cooling", fmt(EVAP["passed"]), "docs/deck_build_log.md step 4 and docs/demo_script.md", "evaporative cooling step", True),
                ("Counties with no weak factor, evaporative", fmt(EVAP["floor_ok"]), "docs/deck_build_log.md step 4 and docs/demo_script.md", "evaporative cooling step", True),
                ("Grant water stress", f"{GRANT['horizon_2050_raw']['water_stress_bws']['today']:.1f} of 5", "docs/figures/facts.json", "featured.horizon_2050_raw.water_stress_bws.today", True),
                ("First place under evaporative cooling", EVAP["first"], "docs/deck_build_log.md step 4", None, True),
                ("Preset leaders", "speed_to_power Mayes OK, sustainability_first Whitman WA with Grant 4th", "docs/figures/facts.json and docs/deck.md", "presets", True)],
    )
    shot = picture_fit(s, APP / "app_cooling_switch.png", MX, TOP - Inches(0.05), Inches(5.7), Inches(1.75), align="left")
    shot.line.color.rgb = RULE
    shot.line.width = Pt(1)
    bar_chart(s, MX, TOP + Inches(1.85), Inches(5.7), Inches(1.95), ["Dry cooling", "Evaporative cooling"],
              [B["passed"], EVAP["passed"]], [NAVY, BLUE], title="Counties that pass the hard limits", max_val=2000,
              cat_size=16, label_size=18, gap=40)
    x = MX + Inches(6.1)
    w = CW - Inches(6.1)
    bullets(s, x, TOP + Inches(0.05), w, Inches(3.5),
            ["Evaporative cooling adds a limit on water stress.",
             "Grant drops out, and the app shows which limit it failed.",
             "Whitman, with almost no water stress, moves to first."], size=20, gap=14)
    band(s, TOP + Inches(3.95), Inches(0.75),
         "You set the conditions. The tool ranks every county and explains each result.",
         fill=NAVY, color=WHITE, size=21)
    add_motion(s)


# ---------------------------------------------------------------------------
# Appendix
# ---------------------------------------------------------------------------
def app_pick(prs):
    r = PS["ranks"]
    g, bk = r["Grant, WA"], r["Berkshire, MA"]
    s = frame(
        prs, "How our pick changed as we fixed the inputs",
        "Ranks from docs/figures/facts.json (pick_story). Price rerun in docs/deck_build_log.md step 4. Permitting model "
        "results in research/permitting_model.md.",
        "A1",
        notes=f"""
With seven factors, Berkshire County, Massachusetts ranked first and Grant seventh. Massachusetts closed the tax break Berkshire relied on, and it fell to
{bk[1]}th. When we added the cost of power as its own factor, Grant rose to first and Berkshire fell
to {fmt(bk[2])}th. Then the price check cut against us. A new load this size won't get today's
average price, and if only Washington pays BPA's new-load rate, Grant falls to {PRICE_RERUN[80]}th.
We also tested a machine-learning model of permitting outcomes and dropped it, because out of
sample it did no better than chance.
""",
        checks=[("Berkshire ranks by step", " / ".join(map(str, bk)), "docs/figures/facts.json", "pick_story.ranks['Berkshire, MA']", True),
                ("Grant ranks by step", " / ".join(map(str, g)), "docs/figures/facts.json", "pick_story.ranks['Grant, WA']", True),
                ("Grant rank with only WA at BPA's $80 per MWh", str(PRICE_RERUN[80]), "docs/deck_build_log.md", "step 4 price rerun", True),
                ("Grant energy cost at BPA's new-load rate", f"${GR['energy_cost_musd']['new_load_low']}M to ${GR['energy_cost_musd']['new_load_high']}M a year",
                 "docs/figures/facts.json", "grant_ranges.energy_cost_musd", True),
                ("Permitting model AUC without facility counts", "0.48 to 0.585, below a 0.60 bar", "research/permitting_model.md", None, True)],
    )
    rank_chart(s, MX, TOP - Inches(0.1), Inches(6.9), Inches(4.75),
               ["Seven factors", "Massachusetts tax fix", "Power cost added", "If Washington pays $80/MWh"],
               [("Berkshire, MA", [bk[0], bk[1], bk[2], None], EMBER,
                 [f"Berkshire #{bk[0]}", f"#{bk[1]}", f"#{fmt(bk[2])}"], ["right", "left", "right"]),
                ("Grant, WA", g + [PRICE_RERUN[80]], NAVY,
                 [f"Grant #{g[0]}", f"#{g[1]}", f"Grant #{g[2]}", f"#{PRICE_RERUN[80]}"], ["below", "above", "above", "right"])],
               title="Rank at each step, log scale", max_rank=2500, log=True)
    x = MX + Inches(7.2)
    w = CW - Inches(7.2)
    bullets(s, x, TOP + Inches(0.1), w, Inches(3.2),
            [f"Massachusetts closed a tax break, and Berkshire fell to {bk[1]}th.",
             "Adding the cost of power moved Grant to first.",
             f"Repricing only Washington at BPA's rate drops Grant to {PRICE_RERUN[80]}th."], size=19, gap=12)
    box = rect(s, x, TOP + Inches(3.35), w, Inches(1.3), fill=GROUND, name="Dropped")
    shape_text(box, "We also tested a machine-learning model of permitting and dropped it. Out of sample it did no "
                    "better than chance.", size=17, align=PP_ALIGN.LEFT, margin=0.2)
    add_motion(s)


def app_tonnes(prs):
    g_score, g_pct = PCTL["Grant, WA"]
    f_score, f_pct = PCTL["Franklin, NY"]
    co2_g = GR["co2_tonnes"]["nwpp_table"]
    ratio = co2_g / FRANKLIN_CO2
    s = frame(
        prs, "Why we also check the leaders in dollars and tons",
        "Pillar scores from the engine on main c239868 (docs/deck_build_log.md step 4). CO2 from research/impact.md "
        "at eGRID2023 regional rates. Cost shares from the 25-year dollar model in docs/weighting.md.",
        "A2",
        notes=f"""
Scores out of 100 can hide physical differences. At regional grid rates, Franklin County, New York
emits {ratio:.1f} times less CO2 than Grant, yet their carbon scores are {f_score} and {g_score}, the
{f_pct:.0f}th and {g_pct:.0f}th percentiles. So for the leaders we also price everything in dollars and
tonnes over 25 years. In that model energy and carbon carry 67 to 88 percent of the cost differences
between counties, depending on the carbon price. Our balanced weights give them about 30 percent.

If someone asks, with BPA-like supply Grant drops to about {GR['co2_tonnes']['bpa'] / 1000:.0f} thousand
tons, below Franklin.
""",
        checks=[("Carbon score, Grant", f"{g_score} ({g_pct}th percentile)", "docs/deck_build_log.md", "step 4", True),
                ("Carbon score, Franklin", f"{f_score} ({f_pct}th percentile)", "docs/deck_build_log.md", "step 4", True),
                ("CO2, Grant at the regional average", f"{fmt(co2_g)} t a year", "docs/figures/facts.json", "grant_ranges.co2_tonnes.nwpp_table", True),
                ("CO2, Franklin", f"{fmt(FRANKLIN_CO2)} t a year", "research/impact.md", "dry cooling table", True),
                ("Energy and carbon share of cost differences", "67%, 78%, 88% at $0, $190, $300 per ton", "docs/weighting.md", "Variance shares", False)],
    )
    half = int((CW - Inches(0.5)) / 2)
    bar_chart(s, MX, TOP - Inches(0.05), half, Inches(3.2), ["Franklin, NY", "Grant, WA"],
              [FRANKLIN_CO2 / 1000, co2_g / 1000], [BLUE, NAVY],
              title="CO2, thousand metric tons a year", max_val=850, cat_size=17)
    textbox(s, MX, TOP + Inches(3.3), half, Inches(1.2),
            f"Their carbon scores are {f_score:.0f} and {g_score:.0f}, only {f_score - g_score:.0f} points apart.",
            size=19, color=INK)
    bar_chart(s, MX + half + Inches(0.5), TOP - Inches(0.05), half, Inches(3.2),
              list(EC_SHARE) + ["Balanced weights"], list(EC_SHARE.values()) + [BALANCED_EC], [NAVY, NAVY, NAVY, GREY],
              title="Energy and carbon share of cost gaps", fmt_code='0"%"', horizontal=False, max_val=100,
              cat_size=15, gap=60)
    textbox(s, MX + half + Inches(0.5), TOP + Inches(3.3), half, Inches(1.2),
            "Dollars show what the scores flatten, so the two views check each other.", size=19, color=INK)
    add_motion(s)


def app_alternatives(prs):
    s = frame(
        prs, "Clark WA and Franklin NY are the alternatives, each with a condition",
        "25-year costs at $190 per ton CO2 with sales tax, at today's average prices (docs/weighting.md). Land checks "
        "from research/sensitive_land.md.",
        "A3",
        notes=f"""
In the 25-year dollar model, Clark, Grant, and Franklin land within 1.1 percent of each other at
today's prices, so the model can't separate them. Grant wins if its power arrives within about a year
of a two-year baseline. Clark wins if its parcel avoids the transit district's higher sales tax and it
gets power in about two and a quarter years. Franklin wins if New York's data center tax exemption
applies, which probably doesn't cover an AI training campus. None of the three has a land conflict
at its reference site.

If someone asks about cheaper states, with sales tax the states that exempt all equipment price
cheaper, but those flags in our state table aren't verified.
""",
        checks=[(f"25-year cost, {k}", f"${v}B", "docs/weighting.md", "Recommendation table", True) for k, v in TIE.items()]
        + [("Grant break-even with Clark and Franklin", "10.2 and 12.1 months", "docs/weighting.md", "Grant's row", True),
           ("Franklin share inside the Adirondack Park", "68%", "research/sensitive_land.md", "Franklin County", True),
           ("Malone distance to the Blue Line", "6.1 km", "research/sensitive_land.md", "Franklin County", True)],
    )
    rows = [("County", "25-year cost", "Wins if", "Land check"),
            ("Grant, WA", f"${TIE['Grant, WA']}B", "Full power arrives within about a year of baseline",
             "Nearest protected land is 5.8 km from Quincy"),
            ("Clark, WA", f"${TIE['Clark, WA']}B", "Its parcel avoids the transit tax and power comes in 2.25 years",
             "Avoid the Gorge Scenic Area and the Ridgefield lowlands"),
            ("Franklin, NY", f"${TIE['Franklin, NY']}B", "New York's data center tax exemption applies",
             "Malone sits 6.1 km outside the Adirondack Park")]
    for row in rows:
        for cell in row:
            no_marks(cell, "A3 table")
    table(s, MX, TOP - Inches(0.05), CW, Inches(3.3), rows, [Inches(2.0), Inches(1.9), Inches(4.2), CW - Inches(8.1)], size=16)
    bullets(s, MX, TOP + Inches(3.5), CW, Inches(1.0),
            ["States that exempt all equipment look cheaper, but that is unverified."], size=19)
    add_motion(s)


def app_sources(prs):
    rows = [("Factor", "Sources"),
            ("Energy and carbon", "eGRID2023 subregions, LBNL interconnection queue, NREL WIND Toolkit, eGRID plants within 100 km"),
            ("Water", "US Drought Monitor, FEMA NRI, WRI Aqueduct 4.0, CMRA"),
            ("Climate resilience", "FEMA NRI loss rates, CMRA projections (LOCA-downscaled CMIP5)"),
            ("Grid and infrastructure", "LBNL queue, FCC fiber, FracTracker, EIA-860"),
            ("Cost of power", "EIA-861 state industrial prices"),
            ("Land", "Census TIGER, USGS PAD-US 4.1 protected areas, NLCD 2021 land cover via IPUMS NHGIS"),
            ("Community", "ACS, BLS LAUS, BEA 1969 employment, Census history since 1950"),
            ("Permitting", "EPA Green Book, state policy tables, NLCD forest and wetland cover"),
            ("Context and optional limits", "Census TIGER 2024 tribal boundaries")]
    s = frame(
        prs, "Every county is scored from public data, and proxies are labeled",
        "Sources and versions in data/processed/county_features.manifest.json. Column definitions in docs/schema.md and "
        "engine/pillars.yaml.",
        "A4",
        notes=f"""
All {fmt(B['counties'])} counties are scored from public sources joined into one county table. This round
added USGS protected areas, NLCD land cover, and Census tribal boundaries. Four inputs are proxies,
and we say so. Home fiber stands in for backbone fiber, plants within 100 kilometers stand in for
power a new load can actually get, a state average price stands in for what a new load pays, and a
heat-demand score stands in for heat reuse. {F['limitations']['scored_columns_present']} of
{F['limitations']['scored_columns_mapped']} planned columns have data, so coverage across the top 10 is
{min(F['limitations']['coverage_top10']) * 100:.0f} to {max(F['limitations']['coverage_top10']) * 100:.0f} percent.
""",
        checks=[("Counties", fmt(B["counties"]), "docs/figures/facts.json", "balanced.counties", True),
                ("Columns with data, of those planned", f"{F['limitations']['scored_columns_present']} of {F['limitations']['scored_columns_mapped']}",
                 "docs/figures/facts.json", "limitations.scored_columns_present and scored_columns_mapped", True),
                ("Coverage across the top 10", f"{min(F['limitations']['coverage_top10']):.2f} to {max(F['limitations']['coverage_top10']):.2f}",
                 "docs/figures/facts.json", "limitations.coverage_top10", True)],
    )
    for row in rows:
        for cell in row:
            no_marks(cell, "A4 table")
    table(s, MX, TOP - Inches(0.1), CW, Inches(4.4), rows, [Inches(3.3), CW - Inches(3.3)], size=15)
    add_motion(s)


def app_limits(prs):
    L = F["limitations"]
    s = frame(
        prs, "The tool screens counties. Choosing a parcel still takes site work.",
        "From docs/deck.md (Limitations), docs/figures/facts.json, research/sensitive_land.md, research/risk.md, and "
        "docs/conditions.md.",
        "A5",
        notes=f"""
Three limits matter most. First, protected land, tribal land, and land cover are county shares. They're
a screen, not a siting check. A 150-acre campus can avoid protected land inside a county, so parcel
checks belong in feasibility. Second, scoring against the nation stretches small gaps. Whitman is 0.2
percent protected and Grant 12.8 percent, and that ends up about 89 percentile points apart. Third,
Grant leads Whitman by {GRANT_SCORE - WHITMAN_SCORE:.2f} points, which is a tie. The engine also sees installed
generation and average prices, which a new 300 megawatt load won't get.
""",
        checks=[("Grant lead over Whitman", f"{GRANT_SCORE - WHITMAN_SCORE:.2f} points", "results/balanced.csv", "composite", True),
                ("Protected share, Whitman and Grant", "0.2% and 12.8%, about 89 percentile points apart", "research/sensitive_land.md", "County shares in the engine", True),
                ("Plant capacity within 100 km of Grant", f"{fmt(L['featured_plant_capacity_mw_100km'])} MW", "docs/figures/facts.json", "limitations.featured_plant_capacity_mw_100km", True),
                ("Loudoun VA", "fails the queue age limit (" + L["loudoun_va"].split(": ")[-1] + ")", "docs/figures/facts.json", "limitations.loudoun_va", True)],
    )
    bullets(s, MX, TOP + Inches(0.05), Inches(6.9), Inches(4.5),
            ["Land shares are county screens, not parcel checks.",
             "National percentiles stretch gaps, like 0.2% against 12.8% protected.",
             f"Grant leads Whitman by {GRANT_SCORE - WHITMAN_SCORE:.2f} points, which is a tie."],
            size=21, gap=18)
    rows = [("What the tool uses", "What it stands in for"),
            ("Home fiber coverage", "Backbone fiber"),
            ("Plants within 100 km", "Power a new load can get"),
            ("State average price", "New-load rate"),
            ("Heat-demand score", "Heat reuse"),
            ("County protected share", "Protected land near a site"),
            ("State permitting values", "Local permitting risk")]
    for row in rows:
        for cell in row:
            no_marks(cell, "A5 table")
    table(s, MX + Inches(7.3), TOP + Inches(0.05), CW - Inches(7.3), Inches(4.4), rows,
          [Inches(2.4), CW - Inches(9.7)], size=14)
    add_motion(s)


def app_extends(prs):
    s = frame(
        prs, "The same engine works for other regions and other questions",
        "Global run from docs/global.md and results/global_balanced.csv. Boone County jobs from docs/demo_script.md "
        "(BLS QCEW private manufacturing). Stage 2 described in docs/industrial_reuse.md.",
        "A6",
        notes=f"""
Two extensions. The same engine ranked {GL['countries']} countries after about 40 lines of change, and
{GL['passed']} pass the limits, led by Sweden, Switzerland, and Norway. That shows the method carries to
another region. It isn't a country recommendation, because there's no open global power price. The
second extension adds unscored context after the ranking. Boone County, Illinois lost almost three
quarters of its manufacturing jobs after the Belvidere plant went idle. Economic need isn't evidence
of community support, so local engagement is still required.
""",
        checks=[("Countries, passing, and with no weak factor", f"{GL['countries']}, {GL['passed']}, {GL['floor_ok']}", "docs/figures/facts.json", "global", True),
                ("US global rank", f"{GL['us']['rank']} of {GL['us']['of']}", "docs/figures/facts.json", "global.us", True),
                ("Boone IL manufacturing jobs", "7,761 in 2015 to 2,070 in 2024", "docs/demo_script.md", "Stage 2 table", True)],
    )
    half = int((CW - Inches(0.5)) / 2)
    with open(ROOT / "results/global_balanced.csv") as fh:
        glob = list(csv.DictReader(fh))
    us = next(r for r in glob if r["iso3"] == "USA")
    rows = [("Rank", "Country", "Score", "Weak spot")]
    for r in glob[:5] + [us]:
        rows.append((r["rank"], r["country"], f"{float(r['composite']):.1f}", "none" if r["floor_ok"] == "True" else "climate"))
    textbox(s, MX, TOP - Inches(0.05), half, Inches(0.4),
            f"{GL['countries']} countries, {GL['passed']} pass the limits", size=18, bold=True)
    table(s, MX, TOP + Inches(0.45), half, Inches(3.3), rows,
          [Inches(1.0), half - Inches(3.6), Inches(1.2), Inches(1.4)], size=16)
    bar_chart(s, MX + half + Inches(0.5), TOP - Inches(0.05), half, Inches(3.4), ["2015", "2024"], [7761, 2070], [GREY, EMBER],
              title="Manufacturing jobs, Boone County, IL", horizontal=False, max_val=9000, cat_size=17)
    textbox(s, MX + half + Inches(0.5), TOP + Inches(3.5), half, Inches(1.0),
            "Economic need isn't evidence of community support.", size=18, bold=True, color=INK)
    add_motion(s)


def table(slide, x, y, w, h, rows, col_w, size=16):
    gf = slide.shapes.add_table(len(rows), len(rows[0]), x, y, w, h)
    tbl = gf.table
    for j, cw in enumerate(col_w):
        tbl.columns[j].width = cw
    for i, row in enumerate(rows):
        for j, val in enumerate(row):
            cell = tbl.cell(i, j)
            cell.fill.solid()
            cell.fill.fore_color.rgb = NAVY if i == 0 else (GROUND if i % 2 == 0 else WHITE)
            cell.margin_left = cell.margin_right = Inches(0.1)
            cell.vertical_anchor = MSO_ANCHOR.MIDDLE
            tf = cell.text_frame
            tf.word_wrap = True
            r = tf.paragraphs[0].add_run()
            r.text = val
            style_run(r, size, WHITE if i == 0 else INK, bold=(i == 0 or j == 0))
    return tbl


def bar_chart_clustered(slide, x, y, w, h, cats, series, title, max_val=None):
    """Clustered columns with a legend, one color per series."""
    no_marks(title, "chart title")
    cd = CategoryChartData()
    cd.categories = cats
    for name, vals, _ in series:
        cd.add_series(name, vals)
    ch = slide.shapes.add_chart(XL_CHART_TYPE.COLUMN_CLUSTERED, x, y, w, h, cd).chart
    ch.font.name = FONT
    ch.font.size = Pt(16)
    ch.has_title = True
    ch.chart_title.text_frame.text = title
    for p in ch.chart_title.text_frame.paragraphs:
        for r in p.runs:
            style_run(r, 18, INK, bold=True)
    ch.has_legend = True
    ch.legend.position = XL_LEGEND_POSITION.BOTTOM
    ch.legend.include_in_layout = False
    ch.legend.font.size = Pt(15)
    plot = ch.plots[0]
    plot.gap_width = 70
    plot.overlap = -10
    for ser, (_, _, color) in zip(plot.series, series):
        ser.format.fill.solid()
        ser.format.fill.fore_color.rgb = color
    plot.has_data_labels = True
    dl = plot.data_labels
    dl.number_format = "0.0"
    dl.number_format_is_linked = False
    dl.position = XL_LABEL_POSITION.OUTSIDE_END
    dl.font.size = Pt(18)
    dl.font.bold = True
    va = ch.value_axis
    va.visible = False
    va.has_major_gridlines = False
    va.minimum_scale = 0
    if max_val:
        va.maximum_scale = max_val
    ca = ch.category_axis
    ca.tick_labels.font.size = Pt(17)
    ca.tick_labels.font.color.rgb = INK
    ca.major_tick_mark = XL_TICK_MARK.NONE
    ca.format.line.color.rgb = RULE
    return ch


MAP_BG = RGBColor(0xFC, 0xFC, 0xFB)  # background of docs/figures/map_composite.png
MAP_PX = (1309, 1031)  # its size in pixels; overlay positions below are in these pixels
GRANT_PX, WHITMAN_PX = (221, 189), (255, 205)  # county centroids, located from counties.geojson (build log step 4)


def map_overlays(slide, pic):
    """Readable, editable labels over the team map: a larger title, a ring on the two leaders, and a legend line."""
    sx, sy = pic.width / MAP_PX[0], pic.height / MAP_PX[1]

    def at(px, py):
        return pic.left + int(px * sx), pic.top + int(py * sy)

    x, y = at(0, 0)
    title = rect(slide, x, y, pic.width, int(66 * sy), fill=MAP_BG, name="Map title")
    shape_text(title, "Grant and Whitman circled",
               size=16, bold=True, color=INK, align=PP_ALIGN.LEFT, margin=0.08)
    cx, cy = at((GRANT_PX[0] + WHITMAN_PX[0]) / 2, (GRANT_PX[1] + WHITMAN_PX[1]) / 2)
    rw, rh = Inches(0.62), Inches(0.42)
    rect(slide, cx - rw // 2, cy - rh // 2, rw, rh, line=EMBER, line_w=3, shape=MSO_SHAPE.OVAL, name="Leaders ring")
    lx, ly = at(18, 842)
    legend = rect(slide, lx, ly, int(840 * sx), int(62 * sy), fill=MAP_BG, name="Map legend")
    shape_text(legend, "Grey counties fail a hard limit", size=14, color=INK2, align=PP_ALIGN.LEFT, margin=0.04)


# ---------------------------------------------------------------------------
# Companion files
# ---------------------------------------------------------------------------
def write_checks():
    lines = ["# Numbers to check", "",
             "Generated by `docs/deck/build_deck.py`. Every number below appears on a slide or in its",
             "speaker notes with `[[CHECK]]`, because it comes from the engine, the county table, or a",
             "model run that could change tonight. Recheck each against its source before presenting.",
             "Numbers from published outside sources (statutes, the Grant PUD FAQ, LBNL) are marked as",
             "published in the notes and aren't repeated here.", "",
             "| Slide | Number | Value in the deck | Source file | Field |", "| --- | --- | --- | --- | --- |"]
    for slide, what, value, f, field in CHECKS:
        lines.append(f"| {slide} | {what} | {value} | `{f}` | {field or ''} |")
    (DECK / "numbers_to_check.md").write_text("\n".join(lines) + "\n")


def write_sources():
    lines = ["# Deck sources", "",
             "Generated by `docs/deck/build_deck.py`. Quotes, outside sources, and image credits for",
             "`pitch_template.pptx`.", "",
             "## Quotes", "",
             "Every quote was checked on 2026-10-04 by opening the primary source and matching the words",
             "exactly, ignoring only whitespace and straight versus curly quotation marks. An ellipsis marks",
             "an omission that doesn't change the meaning. Unused quotes are verified and available for",
             "questions or a swap.", ""]
    for q in QUOTE_BANK:
        where = q["slide"].capitalize() if q["slide"].startswith("unused") else f"Slide {q['slide']}"
        lines += [f"- **{where}.** “{q['text']}”",
                  f"  - Attribution. {q['who']}",
                  f"  - Location. {q['source']}",
                  f"  - Link. {q['url']}"]
    lines += ["", "Not used, and why.", "",
              "- “at its water right limits” (City of Quincy). The words come from a Department of Ecology",
              "  meeting summary describing remarks by Bob Davis of the City of Quincy, not a City statement,",
              "  and the same summary attributes 60% of Quincy's water budget to food processing, not data",
              "  centers. Cite it as “Summary of City of Quincy remarks, CRPAG meeting, Oct. 23, 2025” if used.",
              "  https://www.ezview.wa.gov/Portals/_1962/Documents/CRPAG/Oct2025meetingum.pdf",
              "- No verified source says siting choices matter “for decades”. The slide 1 headline is the",
              "  team's claim, not a quote.", "",
              "## Images", "",
              "- `docs/figures/map_composite.png` (slide 4). Team figure from `docs/figures/make_figures.py`, with",
              "  editable overlays drawn on top in PowerPoint (a title band, a ring on Grant and Whitman, a legend line).",
              "- `docs/deck/img/app_overview.png` (slide 2) and `docs/deck/img/app_cooling_switch.png` (slide 9).",
              "  Screenshots of the team's Streamlit app (`app/app.py`) on main `c239868`, taken with headless",
              "  Chrome at 2x. The second is the balanced preset with cooling set to evaporative and Grant selected.",
              "  Each is a crop of one contiguous region, not edited.",
              "- Every other chart is a native PowerPoint chart built from repo data, so its numbers can be edited.", "",
              "Openly licensed photos, checked on each Commons file page on 2026-10-04. None is placed on a",
              "slide, because every main slide already carries a chart or screenshot. Print the credit line",
              "in the slide's source line if you add one.", ""]
    for key, p in PHOTOS.items():
        lines.append(f"- {key}. {p['credit']}. License {p['license']}. {p['page']}")
    lines += ["", "## Outside sources by slide", ""]
    for slide, srcs in SOURCES.items():
        for src in srcs:
            lines.append(f"- Slide {slide}. {src}")
    lines += ["", "## Data claims checked for this deck", "",
              "- Farmland in opposition cases. `data/processed/opposition_seed_labels.csv` has 100 rows with",
              "  stated reasons. Farmland appears in 7, all inferred by keyword (marked with `?`). The most common",
              "  reasons are zoning process (38), water (31), and grid strain (22)."]
    (DECK / "sources.md").write_text("\n".join(lines) + "\n")


if __name__ == "__main__":
    build()
