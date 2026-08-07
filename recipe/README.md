# The recipe PDF (and how it's built)

The printable one-pager, **Counting Your Actions Before Cloud**, and its source.

| File | What |
|---|---|
| [`temporal-action-count-recipe.pdf`](temporal-action-count-recipe.pdf) | the deliverable — use this to walk through the two paths |
| `build_pdf.py` | the generator (ReportLab); the PDF is a build artifact of this |
| [`BUILD-GUIDE.md`](BUILD-GUIDE.md) | design system, house rules, component reference, common edits |

## Rebuild

```bash
uv run --with reportlab python recipe/build_pdf.py
# then always eyeball the render before shipping:
pdftoppm -png -r 110 recipe/temporal-action-count-recipe.pdf /tmp/qa && open /tmp/qa-1.png
```

Fonts resolve portably: brand `.ttf`s if present, otherwise Linux (Lora / Liberation /
DejaVu) or macOS (Georgia / Arial / Courier New) substitutes. For pixel-true brand
output, drop the real Fraunces / IBM Plex Sans / JetBrains Mono files in and point the
`reg(...)` calls at them — the register names don't change. See `BUILD-GUIDE.md`.

> The install command in the PDF matches [`../docs/gotchas.md`](../docs/gotchas.md#b1):
> the counter tool is **not on PyPI**, so it's run from git via `uvx`. Keep the PDF and
> the docs in sync when either changes.
