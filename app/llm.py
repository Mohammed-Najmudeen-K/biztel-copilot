"""Ask an LLM to answer ONLY from the excerpts. Providers: gemini | ollama | none."""
import asyncio
import os
import re
import httpx

PROVIDER = os.getenv("LLM_PROVIDER", "gemini" if os.getenv("GEMINI_API_KEY") else "none").lower()
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-3.8-flash")
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.2")

SYSTEM = """You are a shop-floor assistant for supervisors at a manufacturing plant.
Answer ONLY using the numbered excerpts below. Never use outside knowledge.
Rules:
- Be short and plain: 1-4 sentences or a few short steps. A supervisor is reading this on a phone.
- For safety questions give the full rule AND any exceptions or conditions from the excerpts.
- If the excerpts do not contain the answer, reply with exactly: NOT_FOUND
- If excerpts disagree, trust the one marked LATEST and say so.
- Be exact about who does what. Never merge or swap roles, titles or numbers.
- End with one line: SOURCES: followed by the excerpt numbers you used, e.g. SOURCES: 1,3"""


def build_prompt(question: str, hits: list[dict]) -> str:
    ex = "\n\n".join(
        f'[{i}] {h["doc_id"]} Rev {h["revision"]} ({"LATEST" if h["is_latest"] else "OLD"}), '
        f'{h["section"]}, page {h["page"]}\n{h["text"]}' for i, h in enumerate(hits, 1))
    return f"Excerpts:\n{ex}\n\nQuestion: {question}"


async def ask_llm(question: str, hits: list[dict]) -> str | None:
    if PROVIDER == "none":
        return None
    prompt = build_prompt(question, hits)
    async with httpx.AsyncClient(timeout=120) as client:
        if PROVIDER == "gemini":
            payload = {"systemInstruction": {"parts": [{"text": SYSTEM}]},
                       "contents": [{"role": "user", "parts": [{"text": prompt}]}],
                       "generationConfig": {"temperature": 0}}
            models = [GEMINI_MODEL] + [m for m in os.getenv("GEMINI_FALLBACK_MODELS", "").split(",") if m.strip()]
            last = None
            for model in models:
                for attempt in range(3):
                    try:
                        r = await client.post(
                            f"https://generativelanguage.googleapis.com/v1beta/models/{model.strip()}:generateContent",
                            headers={"x-goog-api-key": os.environ["GEMINI_API_KEY"]}, json=payload)
                        if r.status_code in (429, 500, 503):
                            last = r
                            await asyncio.sleep(1.5 * (attempt + 1))
                            continue
                        r.raise_for_status()
                        return r.json()["candidates"][0]["content"]["parts"][0]["text"].strip()
                    except httpx.ReadTimeout:
                        await asyncio.sleep(1)
            if last is not None:
                last.raise_for_status()
            raise RuntimeError("Gemini did not respond")
        if PROVIDER == "ollama":
            r = await client.post(f"{OLLAMA_URL}/api/chat", json={
                "model": OLLAMA_MODEL, "stream": False, "options": {"temperature": 0},
                "messages": [{"role": "system", "content": SYSTEM}, {"role": "user", "content": prompt}]})
            r.raise_for_status()
            return r.json()["message"]["content"].strip()
    return None


def parse(answer: str, n_hits: int):
    """Split 'text ... SOURCES: 1,3' into (text, [indexes])."""
    m = re.search(r"SOURCES:\s*([\d,\s]+)\s*$", answer, re.I)
    used = [int(x) for x in re.findall(r"\d+", m.group(1))] if m else []
    text = answer[: m.start()].strip() if m else answer.strip()
    return text, [u for u in used if 1 <= u <= n_hits]