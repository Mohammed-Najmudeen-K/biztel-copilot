"""Read the PDFs and cut them into small, searchable pieces (chunks).

One chunk = one numbered section of a document (e.g. "6. Common Alarms"),
tagged with document number, revision, page and whether it is the latest revision.
"""
import re
from pathlib import Path
from pypdf import PdfReader

DOCS_DIR = Path(__file__).resolve().parent.parent / "docs"
HEADER_RE = re.compile(r"^\S+\s*\|\s*Rev\s*\d+\s*\|\s*Uncontrolled.*$", re.I)
SECTION_RE = re.compile(r"^\s*(\d{1,2})\.\s+([A-Z][^\n]{2,80})$")


def _clean(line: str) -> str:
    return re.sub(r"[ \t]{2,}", "  ", line).rstrip()


def load_chunks() -> list[dict]:
    chunks, docs = [], {}
    for pdf in sorted(DOCS_DIR.glob("*.pdf")):
        reader = PdfReader(str(pdf))
        pages = [p.extract_text(extraction_mode="layout") or "" for p in reader.pages]
        first = " ".join(pages[0].split())
        doc_id = re.search(r"Document No\.?\s*(\S+)", first)
        rev = re.search(r"Revision\s*(\d+)", first)
        title = re.search(r"Kaveri[^\n]*?Plant\s*(.+?)\s*Document No", first)
        meta = {
            "doc_id": doc_id.group(1) if doc_id else pdf.stem,
            "revision": int(rev.group(1)) if rev else 0,
            "title": title.group(1).strip() if title else pdf.stem,
            "file": pdf.name,
        }
        docs.setdefault(meta["doc_id"], []).append(meta["revision"])

        # walk lines, remember page, start a new chunk at each section heading
        current = {"heading": "Header", "lines": [], "page": 1, "page_end": 1}
        sections = []
        expected = 1
        for pno, text in enumerate(pages, start=1):
            for raw in text.splitlines():
                line = _clean(raw)
                if not line.strip() or HEADER_RE.match(line.strip()) or re.match(r"^\s*Page \d+\s*$", line):
                    continue
                m = SECTION_RE.match(line)
                # only treat as a new section if its number is the next expected one
                if m and int(m.group(1)) == expected:
                    sections.append(current)
                    head = m.group(2).split("(")[0].strip()
                    current = {"heading": f"{m.group(1)}. {head}", "lines": [], "page": pno, "page_end": pno}
                    expected += 1
                else:
                    current["lines"].append(line.strip())
                    current["page_end"] = pno
        sections.append(current)

        for s in sections:
            body = "\n".join(s["lines"]).strip()
            if s["heading"] == "Header" or len(body) < 20:
                continue
            chunks.append({**meta, "section": s["heading"], "page": s["page"], "page_end": s["page_end"], "text": body})

    latest = {d: max(r) for d, r in docs.items()}
    for c in chunks:
        c["is_latest"] = c["revision"] == latest[c["doc_id"]]
        c["latest_revision"] = latest[c["doc_id"]]
    return chunks


if __name__ == "__main__":
    for c in load_chunks():
        print(f'{c["doc_id"]} rev{c["revision"]} p{c["page"]} [{c["section"]}] latest={c["is_latest"]} len={len(c["text"])}')
