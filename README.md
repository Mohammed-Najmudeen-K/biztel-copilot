# Shop-floor SOP Copilot

A small RAG app for supervisors. Ask a question in plain words, get a short answer taken **only** from the plant's PDFs, with the document, revision, page and a link to open the PDF at that page. If the answer isn't in the documents, it says so.

**Stack:** FastAPI · plain HTML/JS (mobile first) · pypdf · BM25 search · Gemini or Ollama (optional)

## Run it
### Windows PowerShell
```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
Copy-Item .env.example .env
# Edit .env and set GEMINI_API_KEY, or configure Ollama; without either, extract mode is used.
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

### macOS / Linux
```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# Edit .env and add GEMINI_API_KEY, or configure Ollama; without either, extract mode is used.
uvicorn app.main:app --host 0.0.0.0 --port 8000
```
Open http://localhost:8000. Without any LLM key the app still works: it shows the best matching section as-is.

## Open it on your phone (same Wi-Fi)
1. Find your laptop's IP: `ipconfig` (Windows) or `ip a` / `ifconfig` (Linux/Mac), e.g. `192.168.1.23`.
2. On the phone open `http://192.168.1.23:8000`.
3. If it doesn't load, allow Python/port 8000 through the laptop firewall and make sure both devices are on the same network (not a guest Wi-Fi).

## How it works
1. **Ingest** (`app/ingest.py`): each PDF is cut into one chunk per numbered section, tagged with doc number, revision, page and whether it's the latest revision.
2. **Search** (`app/search.py`): BM25 keyword search plus a "do the rare words in the question actually appear in this chunk?" check.
3. **Answer** (`app/llm.py`): the top chunks go to the LLM with strict rules: answer only from the excerpts, short, full rule plus exceptions for safety, reply `NOT_FOUND` otherwise.
4. **Show the source** (`static/index.html`): sources used, original text, and a link to the PDF page.

## Improvement: version awareness
`QC-SOP-014` exists as Rev 03 and Rev 04 with different rules. The app answers only from the latest revision and shows a yellow note when an older, superseded revision also matched. Reason: a supervisor quoting the old sampling rule is a real quality risk. See `THINKING.md`.

## Test results
Tested through the running HTTP app (`POST /api/ask`) with all four PDFs loaded (28 chunks). The live server used Gemini. Answers below are the app's returned text; citations list the source document, revision, section and page(s).

### Sample questions
| # | Question | App result (relevant text from returned section) | Source |
|---|---|---|---|
| 1 | Coolant concentration for TX-200? | The recommended coolant concentration for the TX-200 is 6-8%, checked using a refractometer reading with a 1.0 factor. | `MNT-MAN-CNC-02` Rev 2, section 3, p. 1. The app also cited section 1 (Purpose), which is not relevant. On a retry when Gemini returned HTTP 503, fallback returned section 4 (maintenance schedule) and did not provide the concentration value. |
| 2 | Alarm AL-104? | Alarm AL-104 means the way lube oil level is low. Top up with ISO VG 68 oil to the MAX mark, then press RESET. The machine can continue operating after the reset. | `MNT-MAN-CNC-02` Rev 2, section 6, pp. 1-2 |
| 3 | Who can remove a lockout lock? | Each authorised person may remove only their own lock; nobody may remove another person's lock. If the owner has left the plant and cannot be reached by phone, removal is allowed only if both the Production Manager and Safety Officer authorise it, the machine is physically inspected and confirmed safe, the removal is logged on form SF-12, and the owner is informed before their next shift. | `SAF-SOP-003` Rev 5, sections 5 and 6, pp. 1-2 |
| 4 | BH-220 outer diameter tolerance? | +/- 0.050 mm (nominal 90.000 mm). | `QC-SOP-014` Rev 4, section 6, p. 2 |
| 5 | Spindle runout: how often, who? | Monthly, by a maintenance technician. | `MNT-MAN-CNC-02` Rev 2, section 4, p. 1 |

### My 5 questions
| # | Question | Expected (from docs) | App result (relevant text from returned section) |
|---|---|---|---|
| 1 | What happens if the material test certificate is missing? | Lot goes on HOLD and must not be inspected or accepted until the MTC is received. | If the MTC is missing, the lot is put on HOLD. It must not be inspected or accepted until the MTC is received. (`QC-SOP-014` Rev 4, section 5, pp. 1-2). The app also warned that Rev 3 is superseded by Rev 4. |
| 2 | Where do rejected parts go and who holds the key? | Quarantine Cage Q1, Stores Bay 3; Shift QC Supervisor holds key. | Rejected parts are moved to Quarantine Cage Q1 in Stores Bay 3. The key is held by the Shift QC Supervisor. (`QC-SOP-014` Rev 4, section 5, pp. 1-2) |
| 3 | What is the hydraulic oil replacement interval and who does it? | Yearly, maintenance engineer, ISO VG 46. | Hydraulic oil replacement is done yearly by a maintenance engineer. (`MNT-MAN-CNC-02` Rev 2, section 4, p. 1) |
| 4 | How many samples for a lot of 200 pieces? | 13 samples (Rev 4 section 4; Rev 3 is superseded). | For a lot of 200 pieces, you must inspect 13 samples. (`QC-SOP-014` Rev 4, section 4, p. 1) |
| 5 | **Not in documents:** recommended cutting speed for stainless steel on the TX-200? | Not in these documents. | I couldn't find this in the documents. Please check with your Safety Officer, Maintenance or QC lead. No source returned. |

These are observed results from one run, not a statistically meaningful evaluation. Verify safety-critical details against the linked SOP before acting.

## Known limits
- Keyword search can miss questions phrased very differently from the documents (next step: add embeddings).
- Tables are read as text rows; scanned PDFs would need OCR.
- No login, no chat history, English only.
