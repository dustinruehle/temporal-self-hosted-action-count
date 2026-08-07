#!/usr/bin/env python3
"""Builds the customer-facing "Counting Your Actions Before Cloud" PDF.

Run it with reportlab available, e.g.:

    uv run --with reportlab python recipe/build_pdf.py
    # or: pip install reportlab && python recipe/build_pdf.py

Then rasterize and eyeball every page before shipping:

    pdftoppm -png -r 96 recipe/temporal-action-count-recipe.pdf /tmp/qa

See BUILD-GUIDE.md in this directory for the design system, house rules, and
component reference. Fonts are resolved portably below: brand fonts if present,
otherwise Linux or macOS substitutes.
"""
import os
from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT, TA_CENTER
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    BaseDocTemplate, PageTemplate, Frame, Paragraph, Spacer, Table, TableStyle,
    KeepTogether, Flowable
)
from reportlab.lib.styles import ParagraphStyle

# ---- Fonts ---------------------------------------------------------------
# Brand fonts are Fraunces (headings), IBM Plex Sans (body), JetBrains Mono
# (code). If the real .ttf files are on the machine, add their paths at the
# front of the candidate lists below and the register names stay identical.
# Otherwise we substitute: serif -> Lora/Georgia, sans -> Liberation/Arial,
# mono -> DejaVu/Courier New.
GF = "/usr/share/fonts/truetype/google-fonts/"
LB = "/usr/share/fonts/truetype/liberation/"
DJ = "/usr/share/fonts/truetype/dejavu/"
MAC = "/System/Library/Fonts/Supplemental/"


def reg(name, candidates):
    for p in candidates:
        if p and os.path.exists(p):
            pdfmetrics.registerFont(TTFont(name, p))
            return
    raise SystemExit(f"no font file found for '{name}' among: {candidates}")


reg("Serif",  [GF + "Fraunces-Regular.ttf", GF + "Lora-Variable.ttf", MAC + "Georgia.ttf", MAC + "Times New Roman.ttf"])
reg("Body",   [GF + "IBMPlexSans-Regular.ttf", LB + "LiberationSans-Regular.ttf", MAC + "Arial.ttf"])
reg("Body-B", [GF + "IBMPlexSans-Bold.ttf", LB + "LiberationSans-Bold.ttf", MAC + "Arial Bold.ttf"])
reg("Mono",   [GF + "JetBrainsMono-Regular.ttf", DJ + "DejaVuSansMono.ttf", MAC + "Courier New.ttf"])
reg("Mono-B", [GF + "JetBrainsMono-Bold.ttf", DJ + "DejaVuSansMono-Bold.ttf", MAC + "Courier New Bold.ttf"])

# ---- Brand palette ----
INDIGO = colors.HexColor("#4C2889")
INK    = colors.HexColor("#1C1526")
PAPER  = colors.HexColor("#F6F4FA")
AMBER  = colors.HexColor("#E0952B")
GREEN  = colors.HexColor("#2F9E5B")
CORAL  = colors.HexColor("#E0674C")
CODEBG = colors.HexColor("#ECE6F5")
LINE   = colors.HexColor("#DCD5E8")
MUTE   = colors.HexColor("#6B6280")

PAGE_W, PAGE_H = letter
MARGIN = 0.72 * inch
CONTENT_W = PAGE_W - 2 * MARGIN

# ---- Styles ----
def S(name, **kw):
    return ParagraphStyle(name, **kw)

st_h2   = S("h2", fontName="Serif", fontSize=16, leading=20, textColor=INDIGO, spaceBefore=6, spaceAfter=8)
st_body = S("body", fontName="Body", fontSize=10, leading=15, textColor=INK, spaceAfter=6)
st_lead = S("lead", fontName="Body", fontSize=10.5, leading=16, textColor=INK, spaceAfter=8)
st_step_t = S("stept", fontName="Body-B", fontSize=10.5, leading=14, textColor=INK, spaceAfter=3)
st_step_b = S("stepb", fontName="Body", fontSize=9.7, leading=14, textColor=INK)
st_code = S("code", fontName="Mono", fontSize=8.6, leading=12.5, textColor=INDIGO)
st_note_t = S("notet", fontName="Body-B", fontSize=10, leading=13, textColor=colors.white)
st_note_b = S("noteb", fontName="Body", fontSize=9.5, leading=13.5, textColor=colors.white)
st_link = S("link", fontName="Body", fontSize=9.5, leading=14, textColor=INDIGO)
st_link_lbl = S("linklbl", fontName="Body-B", fontSize=9.5, leading=14, textColor=INK)
st_foot = S("foot", fontName="Body", fontSize=7.6, leading=10, textColor=MUTE)
st_kicker = S("kick", fontName="Body-B", fontSize=8.5, leading=11, textColor=AMBER)
st_note_small = S("notesm", fontName="Body", fontSize=9.3, leading=13.5, textColor=INK)
st_th = S("th", fontName="Body-B", fontSize=8.8, leading=11, textColor=colors.white)
st_td = S("td", fontName="Body", fontSize=8.8, leading=11.5, textColor=INK)
st_td_m = S("tdm", fontName="Mono", fontSize=8.4, leading=11, textColor=INDIGO)


class HeaderBand(Flowable):
    """Indigo title band."""
    def __init__(self, w, title, subtitle):
        Flowable.__init__(self)
        self.w = w; self.h = 1.18 * inch
        self.title = title; self.subtitle = subtitle
    def wrap(self, *a): return (self.w, self.h)
    def draw(self):
        c = self.canv
        c.setFillColor(INDIGO)
        c.roundRect(0, 0, self.w, self.h, 8, stroke=0, fill=1)
        # amber tick
        c.setFillColor(AMBER)
        c.roundRect(0, self.h - 0.34*inch, 0.09*inch, 0.34*inch, 0, stroke=0, fill=1)
        c.setFillColor(colors.HexColor("#C9B8E6"))
        c.setFont("Body-B", 8.5)
        c.drawString(0.28*inch, self.h - 0.34*inch, "TEMPORAL  ·  ACTION SIZING")
        c.setFillColor(colors.white)
        c.setFont("Serif", 21)
        c.drawString(0.28*inch, self.h - 0.72*inch, self.title)
        c.setFillColor(colors.HexColor("#D7CCEA"))
        c.setFont("Body", 10)
        c.drawString(0.28*inch, self.h - 0.98*inch, self.subtitle)


class Rule(Flowable):
    def __init__(self, w, color=LINE, thick=0.6):
        Flowable.__init__(self); self.w=w; self.color=color; self.thick=thick
    def wrap(self,*a): return (self.w, self.thick+4)
    def draw(self):
        self.canv.setStrokeColor(self.color); self.canv.setLineWidth(self.thick)
        self.canv.line(0,2,self.w,2)


def code_block(lines):
    """A lavender code card."""
    txt = "<br/>".join(lines)
    p = Paragraph(txt, st_code)
    t = Table([[p]], colWidths=[CONTENT_W - 0.5*inch])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0,0), (-1,-1), CODEBG),
        ("LEFTPADDING", (0,0), (-1,-1), 10),
        ("RIGHTPADDING", (0,0), (-1,-1), 10),
        ("TOPPADDING", (0,0), (-1,-1), 8),
        ("BOTTOMPADDING", (0,0), (-1,-1), 8),
        ("LINEBEFORE", (0,0), (0,-1), 2.2, INDIGO),
        ("ROUNDEDCORNERS", [3,3,3,3]),
    ]))
    return t


def note_card(html):
    """A subtle light-amber note strip for an inline aside."""
    p = Paragraph(html, st_note_small)
    t = Table([[p]], colWidths=[CONTENT_W])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0,0), (-1,-1), colors.HexColor("#FBF3E4")),
        ("LEFTPADDING", (0,0), (-1,-1), 12),
        ("RIGHTPADDING", (0,0), (-1,-1), 12),
        ("TOPPADDING", (0,0), (-1,-1), 8),
        ("BOTTOMPADDING", (0,0), (-1,-1), 8),
        ("LINEBEFORE", (0,0), (0,-1), 2.2, AMBER),
        ("ROUNDEDCORNERS", [3,3,3,3]),
    ]))
    return t


def step_card(num, title, body_html, accent, code=None):
    """Numbered step as a bordered card."""
    numcell = Paragraph(str(num), ParagraphStyle(
        "num", fontName="Serif", fontSize=17, leading=19, textColor=colors.white, alignment=TA_CENTER))
    numtbl = Table([[numcell]], colWidths=[0.42*inch], rowHeights=[0.42*inch])
    numtbl.setStyle(TableStyle([
        ("BACKGROUND",(0,0),(-1,-1), accent),
        ("VALIGN",(0,0),(-1,-1),"MIDDLE"),
        ("ROUNDEDCORNERS",[6,6,6,6]),
    ]))
    inner = [Paragraph(title, st_step_t), Paragraph(body_html, st_step_b)]
    if code:
        inner.append(Spacer(1,5))
        inner.append(code_block(code))
    right = Table([[i] for i in inner], colWidths=[CONTENT_W - 0.72*inch])
    right.setStyle(TableStyle([
        ("LEFTPADDING",(0,0),(-1,-1),0),("RIGHTPADDING",(0,0),(-1,-1),0),
        ("TOPPADDING",(0,0),(-1,-1),0),("BOTTOMPADDING",(0,0),(-1,-1),1),
        ("VALIGN",(0,0),(-1,-1),"TOP"),
    ]))
    card = Table([[numtbl, right]], colWidths=[0.56*inch, CONTENT_W - 0.56*inch])
    card.setStyle(TableStyle([
        ("VALIGN",(0,0),(-1,-1),"TOP"),
        ("LEFTPADDING",(0,0),(0,0),0),("LEFTPADDING",(1,0),(1,0),8),
        ("RIGHTPADDING",(0,0),(-1,-1),0),
        ("TOPPADDING",(0,0),(-1,-1),9),("BOTTOMPADDING",(0,0),(-1,-1),9),
        ("BACKGROUND",(0,0),(-1,-1), colors.white),
        ("LINEBELOW",(0,0),(-1,-1),0.6, LINE),
    ]))
    return card


def callout(title, body_html, bg):
    t = Table([[Paragraph(title, st_note_t)],[Paragraph(body_html, st_note_b)]],
              colWidths=[CONTENT_W])
    t.setStyle(TableStyle([
        ("BACKGROUND",(0,0),(-1,-1), bg),
        ("LEFTPADDING",(0,0),(-1,-1),12),("RIGHTPADDING",(0,0),(-1,-1),12),
        ("TOPPADDING",(0,0),(0,0),9),("BOTTOMPADDING",(0,0),(0,0),2),
        ("TOPPADDING",(0,1),(-1,1),0),("BOTTOMPADDING",(0,1),(-1,1),10),
        ("ROUNDEDCORNERS",[7,7,7,7]),
    ]))
    return t


def section_header(kicker, title):
    return [Paragraph(kicker, st_kicker), Paragraph(title, st_h2)]


# ---- Build story ----
story = []
LINKCOLOR = "#4C2889"

def a(url, text):
    return f'<a href="{url}" color="{LINKCOLOR}"><u>{text}</u></a>'

story.append(HeaderBand(CONTENT_W, "Counting Your Actions Before Cloud",
                        "How to measure billable Actions on a self-hosted Temporal Service"))
story.append(Spacer(1, 14))

story.append(Paragraph(
    "Temporal Cloud bills on Actions. A self-hosted Service does not show you an Action total the way "
    "Cloud does, but the number is already in your environment. This recipe walks through the two ways to "
    "pull it: reading the Service's own metric, or counting from exported Workflow histories. Both feed the "
    "same simple conversion to a monthly figure your Temporal team can turn into a Cloud estimate. It "
    "follows " + a("https://docs.temporal.io/cloud/migrate/estimate-actions",
    "Temporal's own guidance for estimating Actions before a migration") + ".", st_lead))
story.append(Spacer(1, 4))

# Prereqs callout
story.append(callout(
    "Before you start",
    "Check your Temporal Server version and confirm whether you have Prometheus or Grafana scraping the "
    "cluster. Version decides accuracy: 1.17 and later emit the metric, and 1.22.3 and later report it "
    "accurately for billing, including Local Activity metering. If you scrape metrics, use Path A. If you "
    "do not, use Path B.", INDIGO))
story.append(Spacer(1, 16))

# ---- Path A ----
pathA = section_header("PATH A  ·  PREFERRED", "Read the Action metric from Prometheus")
pathA.append(Spacer(1,2))
pathA.append(step_card(1,
    "Confirm the Server version",
    "Anything 1.22.3 or newer gives a billing-accurate count. Between 1.17 and 1.22.2 the metric is still "
    "useful for load sizing but runs low on Local Activities, so treat it as an approximation.",
    INDIGO))
story.append(KeepTogether(pathA))

story.append(step_card(2,
    "Total Actions over your window",
    "Run this in Prometheus or Grafana to get the Action count over the last 30 days. The metric is a "
    "counter, so increase() is what gives you the delta across the window. This needs samples spanning the "
    "whole window, so if the Server restarted inside it or your metrics retention is shorter, the number "
    "runs low.",
    INDIGO,
    code=['sum(increase(action{service_name="frontend"}[30d]))']))

story.append(step_card(3,
    "Set the window end correctly",
    "The [30d] in the query defines the range, and Grafana evaluates it at the dashboard end time. So set "
    "the end of the dashboard time range to the end of the period you are measuring. The start you drag to "
    "does not matter, only the end does. Leaving it at now while you meant last month gives the wrong "
    "answer. For a single Namespace, add the label.",
    INDIGO,
    code=['sum(increase(action{service_name="frontend",',
          '                exported_namespace="default"}[30d]))']))

story.append(step_card(4,
    "Capture the shape of the load",
    "Grab mean and peak Actions per second per Namespace too. Peak APS informs your Namespace APS limits, "
    "and it is where elastic scaling pays off versus overprovisioning self-hosted for the spike. If "
    "exported_namespace returns nothing, try the label namespace instead. You can also script this "
    "sampling with " + a("https://github.com/temporal-sa/temporal-server-actions-count",
    "temporal-server-actions-count") + ".",
    INDIGO,
    code=['sum(rate(action{service_name="frontend"}[1m]))',
          '  by (exported_namespace)']))

story.append(Spacer(1, 8))
story.append(note_card(
    "Using Datadog instead of Prometheus? The metric name differs. Grab ready-made widget queries from " +
    a("https://github.com/temporal-sa/datadog-self-hosted-queries", "datadog-self-hosted-queries") + "."))

story.append(Spacer(1, 12))

# ---- Path B ----
pathB = section_header("PATH B  ·  NO METRICS", "Count from exported Workflow histories")
pathB.append(Spacer(1,2))
pathB.append(step_card(1,
    "Export a representative history per Workflow Type",
    "Pull one Event History for each distinct Workflow Type. A single run stands in for the type, and you "
    "scale by volume later. Download from the Web UI with the Download button, or from the CLI. The counter "
    "accepts either the object format or the plain array format that these produce.",
    GREEN,
    code=['temporal workflow show \\',
          '  --workflow-id &lt;id&gt; \\',
          '  --output json &gt; history.json']))
story.append(KeepTogether(pathB))

story.append(step_card(2,
    "Install and run the counter",
    "Run the " + a("https://github.com/temporal-community/temporal-history-action-count",
    "temporal-history-action-count") + " tool against each history file. It is installed from source, not "
    "PyPI, so fetch and run it in one step with uvx. It prints the billable Actions in that run, for "
    "example a total of 7. Child Workflows and Local Activities are handled for you, billed at 2x and "
    "collapsed to one respectively.",
    GREEN,
    code=['uvx --from \\',
          '  git+https://github.com/temporal-community/temporal-history-action-count \\',
          '  temporal-billable history.json']))

story.append(step_card(3,
    "Scale by volume, then add what history hides",
    "Multiply each type's per-run count by how many of those Workflows run per month, then sum across types. "
    "Then add the Actions that never land in Event History, so the counter cannot see them: roughly one "
    "Action per Query, plus Activity Heartbeats that reach the server. If you Query or Heartbeat heavily, "
    "leaving these out understates the total. See " +
    a("https://docs.temporal.io/cloud/actions", "what counts as an Action") + " for the full list.",
    GREEN))

story.append(Spacer(1, 12))

# ---- Conversion ----
conv = section_header("THE MATH", "Actions per second to monthly Actions")
conv.append(Spacer(1,2))
conv.append(code_block([
    'Monthly Actions = Mean APS  ×  60 × 60 × 24 × 30',
    '',
    'Example:  95 APS  ×  2,592,000  =  ~246M Actions / month']))
story.append(KeepTogether(conv))
story.append(Spacer(1, 14))

# ---- Version accuracy table ----
vt = section_header("QUICK REFERENCE", "Accuracy by Server version")
story.append(KeepTogether(vt))
tbl_data = [
    [Paragraph("Server version", st_th), Paragraph("What the metric gives you", st_th)],
    [Paragraph("1.22.3 and later", st_td_m), Paragraph("Billing-accurate, includes Local Activity metering", st_td)],
    [Paragraph("1.17 to 1.22.2", st_td_m), Paragraph("Useful for load sizing, runs low for billing", st_td)],
    [Paragraph("Earlier than 1.17", st_td_m), Paragraph("No action metric, use the Grafana dashboard workaround or Path B", st_td)],
]
vtbl = Table(tbl_data, colWidths=[1.7*inch, CONTENT_W - 1.7*inch])
vtbl.setStyle(TableStyle([
    ("BACKGROUND",(0,0),(-1,0), INDIGO),
    ("BACKGROUND",(0,1),(-1,1), colors.HexColor("#F0ECF7")),
    ("BACKGROUND",(0,2),(-1,2), colors.white),
    ("BACKGROUND",(0,3),(-1,3), colors.HexColor("#F0ECF7")),
    ("LEFTPADDING",(0,0),(-1,-1),9),("RIGHTPADDING",(0,0),(-1,-1),9),
    ("TOPPADDING",(0,0),(-1,-1),7),("BOTTOMPADDING",(0,0),(-1,-1),7),
    ("VALIGN",(0,0),(-1,-1),"MIDDLE"),
    ("LINEBELOW",(0,0),(-1,-1),0.5, LINE),
    ("BOX",(0,0),(-1,-1),0.5, LINE),
]))
story.append(vtbl)
story.append(Spacer(1, 16))

story.append(Rule(CONTENT_W))
story.append(Paragraph(
    "Once you have a monthly Action total and your peak APS, share both with your Temporal Solutions "
    "Architect. The estimate is a starting point for a sizing conversation, not the final number.", st_body))

# ---- Document w/ footer ----
def footer(canvas, doc):
    canvas.saveState()
    canvas.setStrokeColor(LINE); canvas.setLineWidth(0.5)
    canvas.line(MARGIN, 0.55*inch, PAGE_W - MARGIN, 0.55*inch)
    canvas.setFont("Body", 7.6); canvas.setFillColor(MUTE)
    canvas.drawString(MARGIN, 0.4*inch, "Temporal  ·  Self-Hosted Action Counting")
    canvas.drawRightString(PAGE_W - MARGIN, 0.4*inch, f"Page {doc.page}")
    canvas.restoreState()

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "temporal-action-count-recipe.pdf")
doc = BaseDocTemplate(OUT,
                      pagesize=letter,
                      leftMargin=MARGIN, rightMargin=MARGIN,
                      topMargin=MARGIN, bottomMargin=0.75*inch,
                      title="Counting Your Actions Before Cloud",
                      author="Temporal")
frame = Frame(MARGIN, 0.75*inch, CONTENT_W, PAGE_H - MARGIN - 0.75*inch, id="main",
              leftPadding=0, rightPadding=0, topPadding=0, bottomPadding=0)
doc.addPageTemplates([PageTemplate(id="t", frames=[frame], onPage=footer)])
doc.build(story)
print("built", OUT)
