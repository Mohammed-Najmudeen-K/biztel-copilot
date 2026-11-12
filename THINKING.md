# Thinking

> I used AI to tidy up my rough notes, but the actual thinking is mine. I still went through the problem myself first and checked the steps against the plant documents.

## Understand the user

I imagine the user is a shift supervisor who keeps production moving while making sure people follow the right quality, maintenance and safety procedures. They are on the shop floor with a phone, maybe gloves, background noise and very little time to search through long PDFs.

The hard part is not only finding a document. They need the right current instruction, including any exception, and they need to know where it came from. A wrong answer can waste time or create a safety or quality problem. What frustrates them today:

- I lose time because I cannot trust the document I found.
- I do not want to read through five PDFs just to confirm one rule.

**Assumptions:** supervisors use a phone browser, read English, and want short answers. The sample PDFs are the approved documents for this demo. I would check these with the customer.

## User journey

**Scene:** Alarm AL-104 comes up on CNC-06 in the middle of a shift. An operator looks at me and asks what to do.

1. **Stay calm, don't assume.** I don't guess from memory. I check the document before telling the operator anything.
   *What could go wrong:* I panic or rely on memory and give the wrong instruction.

2. **Ask the app like I'd ask a coworker.** I type something like "alarm 104 what to do" or "can I remove his lock, he already went home."
   *What could go wrong:* Typos or typing with gloves; the app doesn't understand my wording; I ask something the documents don't cover. In an emergency or accident the app is not the right tool. I follow the emergency procedure and call the Safety Officer.

3. **Read the answer.** I read the short answer and look at the source under it: document, revision and page.
   *What could go wrong:* It sounds confident but leaves out an exception or cites an old revision. If it says "not found," I don't guess.

4. **Cross-check.** I open the linked PDF page and compare it with the answer. If they match, I continue. If they don't match or look unclear, I stop.
   *What could go wrong:* Poor Wi-Fi so the PDF won't open, or I'm in a hurry and skip this step.

5. **Decide or escalate.** If it's clear, I act on it, for example top up the way lube oil and press RESET. If it's unclear, or the action is risky (lock removal, restarting a machine, accepting a lot), I contact the responsible person: Safety Officer for locks, Maintenance for machine faults, QC for material. I wait for their decision and don't proceed if I can't reach them.
   *What could go wrong:* The person isn't reachable, or I misjudge what counts as risky.

6. **After.** I act only after the checks, and make sure it's recorded: for example form SF-12 for a lock removal, or the QMS record for an inspected lot. I tell the team what was decided.
   *What could go wrong:* I forget the record, or the team isn't told.

## AI challenge

I wrote the journey above first, then asked an AI to act as a skeptical shop-floor supervisor and product manager and criticise it.

**Prompt (short version):** "Act as a skeptical shop-floor supervisor with 15 years of experience, and also as a skeptical product manager. Here is my user journey: [journey]. Critique it harshly: which steps fail in real shift conditions, what risks am I missing, what would make you stop using the app, and what should change before I build it?"

**Excerpts from the critique:**

- “The short answer is not safe if it leaves out the exception. That is where the real rule lives.”
- “A safe answer is not useful if it does not tell me who to call when the answer is unclear.”

**Reflection**

*What I agreed with:* I agreed with the point that the answer cannot hide the exception. I also agreed that safety decisions need a clear escalation path.

*What I disagreed with:* The critique says to return verbatim excerpts instead of summaries. A supervisor with an operator waiting needs a quick answer first, so I kept a short answer but always show the source, with the original text one tap away. Offline mode, QR codes per machine and voice input are good ideas but too big for this assignment.

*What I changed:* In my journey, step 5 now says risky actions always go to the responsible person, and I don't proceed if they can't be reached. In the app I kept the original-text view and the "not found" response, and I fixed the lockout answer (see below).

## The improvement I added, and why

**Version awareness for superseded documents.**

The sample set has QC-SOP-014 in Rev 3 and Rev 4, and their rules differ (Rev 3: 5 samples for every lot and a paper form; Rev 4: sample size depends on lot size, mandatory test certificate, digital form). A supervisor using an old printout or a plain keyword search could easily quote the wrong rule.

How it works: the app marks each document section as latest or old by comparing revision numbers for the same document number. It answers only from the latest revision and shows a warning when an older revision also matched.

Why I chose it: a wrong-but-confident answer is the biggest risk for this user, and an old instruction can lead to a bad quality decision. It also needed no extra infrastructure. The limit is that it assumes the highest revision number is the approved current one, and a real customer would need to confirm that.

The app also says "I couldn't find this in the documents" instead of making something up, and shows who to check with.

## Final reflection

**What I'd build next.** Test with real supervisors using their own wording, and measure how often answers have the right source and include the needed conditions. Add embeddings alongside keyword search for questions worded differently from the PDFs. Add a contact directory so "not found" tells the supervisor exactly who to call. For risky topics (lock removal, restart, lot acceptance), always end the answer with "confirm with the responsible person before acting." Add machine context (for example a QR code on each machine) so alarm codes map to the right manual.

**What I'm unsure about.** How well this works with scanned PDFs, complicated tables, hundreds of documents and other languages (Tamil, Hindi, mixed languages). Whether the highest revision number is really the approved one. How reliable Wi-Fi is on a real shop floor.

**What I'd ask the customer.** How document revisions are approved and retired, and who owns document control. Who should be contacted for each type of question, including at night. Whether documents may be sent to a hosted AI service or must stay on-premises. Which languages the team uses. Whether the app may be used for emergencies (I assume not).

**Biggest challenge and how I handled it.** The biggest challenge was getting correct answers, not only relevant ones. Without an LLM, the coolant question first returned the weekly maintenance checklist instead of the section with the 6-8% range. Search finds related text but not always the right text, so I tuned the keyword search and added a check that the question's rare words actually appear in the section. With Gemini connected, the answer came from the operating-parameters section.

The more serious problem was the lockout question. The model's first answer swapped roles: it said the Shift Supervisor could authorise lock removal together with the Production Manager and Safety Officer, but the SOP says the Shift Supervisor only tries to contact the owner, and the Production Manager and Safety Officer must both authorise. For a safety procedure that is a real error. I added a rule to the prompt: be exact about who does what and never merge or swap roles, titles or numbers. After re-testing, the answer correctly named the Production Manager and Safety Officer, SF-12 and informing the owner. One good run is not proof the app is reliable, so I would still verify safety answers against the source.

Deployment problems: my first run used Linux commands on Windows PowerShell, so I switched to the PowerShell activation commands. I opened `0.0.0.0:8000` in the browser, which fails; the right address is `localhost:8000` on the laptop and `http://192.168.88.16:8000` from the phone on the same Wi-Fi. The Gemini call failed twice: first because `.env` still pointed to a local Ollama model that was not running, then because Google had retired the default model name. I made the app show the real error message, which made both easy to fix. After that, the app worked from my phone.

## Assumptions

- The supervisor uses a phone browser and needs a short answer during a shift.
- The sample PDFs are the approved documents for this demo and are in English.
- The highest revision number for a document is treated as the latest revision. This must be confirmed with the plant's document-control process before real use.
- The copilot helps find instructions. It does not replace the approved procedure, the responsible person, or the supervisor's judgement.