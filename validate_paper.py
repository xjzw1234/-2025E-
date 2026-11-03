"""English-paper validator.

The bundled paper_format checker assumes Chinese caption prefixes (图N/表N), which
conflicts with the English-only requirement of MCM/ICM. This script performs the
same checks with English patterns so the deviation is verified rather than ignored.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

from docx import Document

ROOT = Path(__file__).resolve().parent
DOCX = ROOT / "完整论文.docx"


def text_of(doc):
    out = [p.text.strip() for p in doc.paragraphs if p.text.strip()]
    for t in doc.tables:
        for row in t.rows:
            out.extend(c.text.strip() for c in row.cells if c.text.strip())
    return out


def main(pages: int | None = None):
    doc = Document(DOCX)
    texts = text_of(doc)
    body_text = "\n".join(texts)
    issues = []

    if not any(t.lower() in {"summary", "summary sheet"} for t in texts):
        issues.append("missing Summary heading")
    if not any(t.lower() == "references" for t in texts):
        issues.append("missing References heading")

    n_fig = len(doc._element.findall(".//" + "{http://schemas.openxmlformats.org/drawingml/2006/main}blip"))
    fig_caps = {}
    for t in texts:
        m = re.match(r"^Figure\s+(\d+)[.:]", t)
        if m:
            fig_caps[int(m.group(1))] = t
    if set(fig_caps) != set(range(1, n_fig + 1)):
        issues.append(f"figure captions {sorted(fig_caps)} vs {n_fig} images")
    for n in range(1, n_fig + 1):
        if len(re.findall(rf"Figure\s+{n}(?!\d)", body_text)) < 2:
            issues.append(f"Figure {n} not referenced in body")

    tabs = doc.tables
    tab_caps = {}
    for t in texts:
        m = re.match(r"^Table\s+(\d+)[.:]", t)
        if m:
            tab_caps[int(m.group(1))] = t
    if set(tab_caps) != set(range(1, len(tabs) + 1)):
        issues.append(f"table captions {sorted(tab_caps)} vs {len(tabs)} tables")
    for n in range(1, len(tabs) + 1):
        if len(re.findall(rf"Table\s+{n}(?!\d)", body_text)) < 2:
            issues.append(f"Table {n} not referenced in body")

    split = next((i for i, p in enumerate(doc.paragraphs)
                  if p.text.strip().lower() == "references"), None)
    if split is not None:
        body = "\n".join(p.text for p in doc.paragraphs[:split])
        cited = set()
        for group in re.findall(r"\[([0-9,\s\-]+)\]", body):
            for item in re.split(r"[,\s]+", group.strip()):
                if not item:
                    continue
                if "-" in item:
                    a, b = item.split("-")[:2]
                    if a.isdigit() and b.isdigit():
                        cited.update(range(int(a), int(b) + 1))
                elif item.isdigit():
                    cited.add(int(item))
        listed = {int(m.group(1)) for p in doc.paragraphs[split + 1:]
                  if (m := re.match(r"^\[(\d+)\]", p.text.strip()))}
        if cited != listed:
            issues.append(f"citation mismatch cited={sorted(cited)} listed={sorted(listed)}")

    for t in texts:
        if re.search(r"`|\*\*|\$\$|^\s*#", t):
            issues.append(f"markdown residue: {t[:60]}")
        if re.search(r"门禁|质检|Subagent|复现清单|哈希", t, re.IGNORECASE):
            issues.append(f"internal process word: {t[:60]}")

    if pages is not None and pages > 25:
        issues.append(f"rendered pages {pages} > 25")

    print("figures", n_fig, "tables", len(tabs), "pages", pages)
    for i in issues:
        print("ISSUE:", i)
    print("PASS" if not issues else "FAIL")
    return 0 if not issues else 1


if __name__ == "__main__":
    p = int(sys.argv[1]) if len(sys.argv) > 1 else None
    raise SystemExit(main(p))
