from pathlib import Path
from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from dotenv import load_dotenv

load_dotenv()
from . import llm  # noqa: E402  (after load_dotenv so env vars are visible)
from .ingest import load_chunks, DOCS_DIR  # noqa: E402
from .search import Searcher  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
app = FastAPI(title="Shop-floor SOP Copilot")
chunks = load_chunks()
searcher = Searcher(chunks)

NOT_FOUND = "I couldn't find this in the documents. Please check with your Safety Officer, Maintenance or QC lead."


class Ask(BaseModel):
    question: str


def source_card(h: dict) -> dict:
    pages = f'{h["page"]}' if h["page"] == h["page_end"] else f'{h["page"]}-{h["page_end"]}'
    return {"doc_id": h["doc_id"], "title": h["title"], "revision": h["revision"], "section": h["section"],
            "pages": pages, "file": h["file"], "link": f'/pdfs/{h["file"]}#page={h["page"]}',
            "snippet": h["text"][:600], "latest": h["is_latest"]}


@app.post("/api/ask")
async def ask(body: Ask):
    q = body.question.strip()
    if len(q) < 3:
        return {"found": False, "answer": "Type a question first.", "sources": [], "warnings": []}
    # Without an LLM, only trust strong matches; with one, let it make the final call.
    hits, old_hits = searcher.search(q, k=5, min_cov=0.3 if llm.PROVIDER != "none" else 0.55)
    if not hits:
        return {"found": False, "answer": NOT_FOUND, "sources": [], "warnings": []}

    # IMPROVEMENT: version awareness. Old revisions are never used for the answer,
    # but we tell the supervisor when an older, superseded document also mentions the topic.
    warnings = []
    seen = set()
    for o in old_hits:
        key = (o["doc_id"], o["revision"])
        if key not in seen:
            seen.add(key)
            warnings.append(f'An older version ({o["doc_id"]} Rev {o["revision"]}) also covers this. '
                            f'It is superseded by Rev {o["latest_revision"]}, so the answer above uses Rev {o["latest_revision"]} only.')

    try:
        raw = await llm.ask_llm(q, hits)
    except Exception as e:  # network/key problems should not break the demo
        import traceback; traceback.print_exc()
        detail = f"{e.response.status_code}: {e.response.text[:300]}" if hasattr(e, "response") else repr(e)
        raw, warnings = None, warnings + [f"AI service unavailable ({type(e).__name__} {detail}); showing the best matching section instead."]

    if raw is None:  # no LLM: show the best section as-is
        best = hits[0]
        return {"found": True, "mode": "extract", "answer": best["text"], "sources": [source_card(best)], "warnings": warnings}
    text, used = llm.parse(raw, len(hits))
    if text.strip().upper().startswith("NOT_FOUND"):
        return {"found": False, "answer": NOT_FOUND, "sources": [], "warnings": []}
    used_hits = [hits[i - 1] for i in used] or hits[:1]
    return {"found": True, "mode": llm.PROVIDER, "answer": text, "sources": [source_card(h) for h in used_hits], "warnings": warnings}


@app.get("/api/health")
def health():
    return {"ok": True, "chunks": len(chunks), "llm": llm.PROVIDER}


app.mount("/pdfs", StaticFiles(directory=DOCS_DIR), name="pdfs")


@app.get("/")
def index():
    return FileResponse(ROOT / "static" / "index.html")
