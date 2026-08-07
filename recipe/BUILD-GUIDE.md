# Build Guide: "Counting Your Actions Before Cloud" PDF

A self-contained spec for the action-count recipe one-pager PDF. With this file you can rebuild the PDF exactly, restyle it, or add content without guessing the conventions. The generator lives beside this file as [`build_pdf.py`](build_pdf.py).

The generator is a single Python file using ReportLab Platypus. Output is a three-page US Letter PDF with clickable links.

---

## 1. Quick start

Requirements: Python 3, `reportlab` (4.x or newer), and `pdftoppm` (poppler-utils) for visual QA.

```bash
# from the repo root
uv run --with reportlab python recipe/build_pdf.py    # writes the PDF beside the script
pdftoppm -png -r 110 recipe/temporal-action-count-recipe.pdf /tmp/qa   # rasterize for review
```

(No uv? `pip install reportlab && python recipe/build_pdf.py` works too.)

The build loop is: edit `build_pdf.py`, rerun, rasterize to PNG, eyeball each page, repeat. Always review the rendered PNGs before shipping. Do not trust the code alone, ReportLab spacing and wrapping need a visual check.

The output path is resolved relative to the script (writes `temporal-action-count-recipe.pdf` next to `build_pdf.py`); change the `OUT = ...` line near the bottom to relocate it.

---

## 2. Design system

### Fonts

The locked brand fonts are Fraunces (headings), IBM Plex Sans (body), JetBrains Mono (code and labels). This build runs in an environment without them and no network, so it substitutes:

| Role | Brand font | Substitute used | Register name |
|---|---|---|---|
| Headings | Fraunces | Lora (variable) | `Serif` |
| Body | IBM Plex Sans | Liberation Sans | `Body`, `Body-B` |
| Code / labels | JetBrains Mono | DejaVu Sans Mono | `Mono`, `Mono-B` |

The register names are what the rest of the script references, so swapping fonts is a one-place change. If the real brand `.ttf` files are available on the machine, point the five `registerFont(TTFont(...))` calls at them and keep the register names identical. Nothing else needs to change. For pixel-true brand rendering the alternative path is to build the same layout in HTML and print-to-PDF from a browser with the fonts installed.

### Color palette

Exact brand values. Do not approximate.

| Token | Hex | Use |
|---|---|---|
| `INDIGO` | `#4C2889` | Primary. Headings, header band, Path A accent, links |
| `INK` | `#1C1526` | Body text |
| `PAPER` | `#F6F4FA` | Paper tone (reference) |
| `AMBER` | `#E0952B` | Kicker labels, note-card accent, header tick |
| `GREEN` | `#2F9E5B` | Path B step accent |
| `CORAL` | `#E0674C` | Accent (available, unused currently) |
| `CODEBG` | `#ECE6F5` | Code-block background (indigo tint) |
| `LINE` | `#DCD5E8` | Hairlines, table rules, footer rule |
| `MUTE` | `#6B6280` | Footer text |

Two inline tints not tokenized: `#FBF3E4` (note-card background, light amber) and `#F0ECF7` (zebra rows in the version table).

### Layout

US Letter, `MARGIN = 0.72 inch` all sides, content width `CONTENT_W = PAGE_W - 2*MARGIN`. Bottom margin is `0.75 inch` to clear the footer. Every page gets a footer rule plus "Temporal · Self-Hosted Action Counting" on the left and "Page N" on the right.

### Type scale

Defined as `ParagraphStyle` objects via the `S()` helper. Key ones: `st_h2` (16pt serif indigo section titles), `st_lead` (10.5pt intro), `st_body` (10pt), `st_step_t` (10.5pt bold step title), `st_step_b` (9.7pt step body), `st_code` (8.6pt mono indigo), `st_kicker` (8.5pt bold amber, all-caps section eyebrow), `st_note_small` (9.3pt note text), plus table styles `st_th`/`st_td`/`st_td_m`.

---

## 3. Component reference

All components return a Platypus flowable (or a list) you append to `story`.

**`HeaderBand(width, title, subtitle)`** — the indigo title band with amber tick, kicker ("TEMPORAL · ACTION SIZING"), serif title, and subtitle. One per document, first item in the story.

**`section_header(kicker, title)`** — returns a two-item list: an amber all-caps kicker and an indigo serif `st_h2` title. Append with `story += section_header(...)` or wrap in `KeepTogether` with the first following card so the header never orphans at a page break.

**`step_card(num, title, body_html, accent, code=None)`** — a numbered step. `num` shows in a rounded `accent`-colored square. `title` is bold, `body_html` is the description (accepts inline HTML including `<a>` links). Optional `code` is a list of strings rendered as a code block beneath the text. Use `INDIGO` accent for Path A, `GREEN` for Path B.

**`code_block(lines)`** — a lavender card with an indigo left bar, mono text. `lines` is a list of strings, one per rendered line. Used standalone (the math block) or inside a step via the `code=` argument.

**`note_card(html)`** — a light-amber strip with an amber left bar for a short aside. Used for the Datadog note. `html` accepts inline links.

**`callout(title, body_html, bg)`** — a filled block with white text on a solid `bg` color, bold title over body. Used for the "Before you start" prerequisites block on `INDIGO`.

**`Rule(width)`** — a thin `LINE`-colored horizontal rule. Used before the closing paragraph.

**`a(url, text)`** — returns an inline hyperlink string (indigo, underlined) for embedding in any `body_html`. This is how all links are added. See the link discipline rules below.

**`S(name, **kw)`** — thin wrapper over `ParagraphStyle` for defining new text styles.

---

## 4. Content model

The story is built top to bottom in this order:

1. `HeaderBand` — title and subtitle
2. Intro `Paragraph` (`st_lead`) — what the doc does, with the estimate-actions doc linked inline
3. `callout` "Before you start" — version and metrics prerequisites
4. Path A section header + four `step_card`s (INDIGO): confirm version, total over window, set window end, capture load shape
5. `note_card` — Datadog alternative
6. Path B section header + three `step_card`s (GREEN): export history, install and run counter, scale and add hidden Actions
7. "THE MATH" section header + standalone `code_block` — the APS to monthly conversion
8. "QUICK REFERENCE" section header + version-accuracy `Table`
9. `Rule` + closing `Paragraph` — handoff to the SA

`KeepTogether` wraps each section header with its first card (or the whole short block) so headers do not strand at the bottom of a page. Vertical rhythm is controlled by `Spacer(1, N)` between blocks.

---

## 5. House rules

These are non-negotiable for this artifact. They reflect the brand system and the quality bar for a shareable one-pager.

- **No em dashes anywhere.** Use commas or restructure. This applies to body copy, titles, and code comments.
- **No AI filler words.** Avoid seamless, robust, leverage, delve, genuinely, and similar. Write plainly.
- **Links inline, not in a trailing list.** Every reference goes where the tool or concept is used, via `a(url, text)`. There is deliberately no "References" section.
- **Only public links in this shared PDF.** Verified public and safe: the three GitHub repos and the docs.temporal.io pages listed in section 7. Internal Google Drive docs and Notion pages must never appear here. If an internal-facing variant is needed, make it a separate file so the two never mix.
- **Verify before you cite.** Any API name, metric name, CLI flag, version threshold, or doc URL added later must be checked against the temporal-docs source and the tool's own README before it ships. The skill this recipe came from had a stale counter command; do not trust secondhand command strings.
- **No pricing.** This version intentionally carries no pricing, rate-card, or cost language. The header kicker is "ACTION SIZING" for this reason. Keep it out.

---

## 6. Common edits

**Add a step to a path.** Call `step_card` with the next number and the path's accent color (`INDIGO` or `GREEN`). Append it after the last step of that path. Renumber following steps if you insert in the middle.

**Add a code block to a step.** Pass `code=['line one', 'line two']`. Each list item is one rendered line. Escape `<`, `>`, `&` (see gotchas).

**Add an inline link.** Wrap the phrase with `a("https://...", "anchor text")` and concatenate into the `body_html` string. Verify the URL resolves and is public first.

**Add a standalone aside.** Use `note_card("text " + a(url, "link") + ".")` and append it with small spacers around it.

**Add a new section.** `story += section_header("KICKER", "Title")`, then wrap the header plus its first flowable in `KeepTogether`.

**Add a table row.** Append to `tbl_data` using `Paragraph(..., st_td_m)` for the mono left column and `Paragraph(..., st_td)` for the right, then extend the zebra `BACKGROUND` rows in the table style to match the new row count.

**Change a step's accent color.** Pass a different token as the `accent` argument. Keep Path A indigo and Path B green for consistency unless restyling both.

**Retune spacing.** Adjust the `Spacer(1, N)` values. Rerun and check the PNGs; do not eyeball from the code.

---

## 7. Content accuracy reference

These facts were verified against Temporal docs and the tools' READMEs. Do not regress them in edits.

- Metric is `action` with label `service_name="frontend"`. It is a counter, so use `increase()` over a range for totals and `rate()` for APS.
- Namespace label may be `exported_namespace` or `namespace` depending on the exporter.
- Version thresholds: 1.17+ emits the metric; 1.22.3+ is billing-accurate including Local Activity metering; 1.17 to 1.22.2 is load-sizing only; earlier than 1.17 has no metric.
- APS to monthly: `Mean APS × 2,592,000` (that is `60 × 60 × 24 × 30`), a 30-day convention matching Temporal's own examples.
- Export command is `temporal workflow show --output json`. The counter also accepts the Web UI Download output.
- Counter tool is **not on PyPI**; run it from git: `uvx --from git+https://github.com/temporal-community/temporal-history-action-count temporal-billable history.json`. (Do not use `uv add temporal-history-action-count` — it does not resolve.) It handles Child Workflows at 2x and collapses back-to-back Local Activities to one.
- `increase(action[<window>])` only counts a rising edge that exists inside the window. If the Server process is younger than the window, restarted inside it, or Prometheus retention is shorter, it under-reports; sanity-check against the raw counter.
- Queries and some Activity Heartbeats are billable but do not appear in Event History, so add them on top of the counter's number.

Verified public links used in the PDF:

| Anchor | URL |
|---|---|
| Estimate Actions for migration | https://docs.temporal.io/cloud/migrate/estimate-actions |
| What counts as an Action | https://docs.temporal.io/cloud/actions |
| temporal-history-action-count | https://github.com/temporal-community/temporal-history-action-count |
| temporal-server-actions-count | https://github.com/temporal-sa/temporal-server-actions-count |
| datadog-self-hosted-queries | https://github.com/temporal-sa/datadog-self-hosted-queries |

---

## 8. ReportLab gotchas

- **Escape HTML entities in text.** Inside any `Paragraph` or code-block string, write `&lt;` for `<`, `&gt;` for `>`, and `&amp;` for `&`. Raw `<id>` or `>` in a code line will break parsing or vanish. The CLI export block uses `&lt;id&gt;` and `&gt; history.json` for this reason.
- **No Unicode super/subscripts.** The fonts lack those glyphs and they render as black boxes. Use `<super>` / `<sub>` markup if ever needed.
- **Variable fonts register as their default instance.** Lora-Variable comes in at regular weight; headings rely on size and color for hierarchy, not a bold axis.
- **`KeepTogether` on headers only.** Wrap a section header with its first card, not an entire long section, or you force awkward page breaks. Steps flow individually.
- **Links need the `color` attribute.** `a()` sets `color="#4C2889"` on the `<a>` tag; without it links render in the default body color.
- **Rounded corners** use the `("ROUNDEDCORNERS", [r,r,r,r])` table style; radii are per-corner.

---

## 9. Full source

The generator is [`build_pdf.py`](build_pdf.py) in this directory (previously this
section inlined the whole script; it now lives as a runnable file so the guide and the
code cannot drift). Build and QA:

```bash
uv run --with reportlab python recipe/build_pdf.py
pdftoppm -png -r 110 recipe/temporal-action-count-recipe.pdf /tmp/qa   # then eyeball each page
```

Font and output paths are handled portably in the `reg(...)` calls at the top of the
script: brand fonts if present, otherwise Linux or macOS substitutes. The output path is
resolved relative to the script, so it writes the PDF beside itself.
