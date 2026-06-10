# Planning — The Unofficial Guide (FIU Campus Dining)

## Domain

Student knowledge about **dining at and around FIU** — what's good, what's overpriced,
whether the meal plan is worth it, which spots fit dietary restrictions, hours, and which
off-campus places are close enough between classes.

Why this is valuable and hard to find officially: my first year I struggled just to figure out
how to use my meal plan and bonus meals, and I didn't know how to spend most of my dining
dollars for months — until a friend told me you could use them through the GrubHub app. The
official info is so short and ambiguous that you can't really understand or use it without going
and trying things yourself. The candid, practical knowledge (is the meal plan worth it, where to
eat between classes, what works for a dietary restriction) only lives in student-newspaper
opinion pieces and word of mouth — never on the official ShopFIU dining page.

## Documents

10 documents collected, all from PantherNOW (FIU's student newspaper) — a mix of opinion
pieces, news, and food guides spanning 2011–2024. Saved as plain .txt in `data/raw/` with a
metadata header (source, URL, title, author, date). Full list with URLs is in the README.

The mix is deliberate: opinion pieces ("meal plans aren't worth it," "BBC needs more food,"
"FIU needs more diverse options") carry the candid judgments; the guides ("ten iconic food
spots," "summer dining options") carry the factual venue/hours/price details. Together they
answer a *range* of questions, not ten versions of the same one.

## Chunking Strategy

**Decision: paragraph-based chunks, target 500–800 characters**, merging small paragraphs
together and splitting any oversized paragraph on sentence boundaries. Implemented in
`ingest.py` (MIN_CHUNK=200, MAX_CHUNK=800). Result: 44 chunks across 10 docs.

Reasoning: these articles are structured by paragraph, and each paragraph tends to be one
self-contained thought — one venue, one complaint, one price list. Fixed 500-character cuts
would slice a venue's hours away from its name. A whole-article chunk would merge 10 venues
into one blob and dilute retrieval. Paragraph chunks keep "complete, retrievable thoughts."

Overlap: 0 characters. Since I split on paragraph boundaries, chunks already end at natural
breaks, so there's no mid-sentence cut for overlap to protect against. I'd only add overlap
(~10–15%) if I moved to fixed-character chunking.

A bad chunk here would be a fragment like "2. specialTEA Lounge and Café" with the hours and
price cut off into the next chunk — unanswerable on its own — or a blob that merges several
unrelated venues so no single query matches it cleanly.

## Retrieval Approach

**Embedding model: all-MiniLM-L6-v2** via sentence-transformers (runs locally, no API key,
no rate limits). **Vector store: ChromaDB** (persistent, cosine distance). **top-k = 4.**

Reasoning for k=4: the candid answers tend to concentrate in one or two articles (all the
meal-plan opinion is in one doc), so a tight k keeps the LLM focused and avoids pulling in
loosely related venue lists. I'll widen to k=5 only if retrieval misses context that's split
across articles.

Why semantic search works: the embedding model turns text into vectors that capture *meaning*,
not exact words, so "is it worth the money" lands near the meal-plan article's talk about
saving $1,899–$2,099 and food being repetitive even though that article never says "worth it."
It matches on concept overlap, not keyword overlap.

## Evaluation Plan

Five test questions with ground-truth answers I can verify against the documents. These go into
`eval_questions.json` and are run with `eval.py`.

1. **Is the meal plan worth it for students who live on campus?**
   Expected: Documents argue it's often not — the dining hall is repetitive, and students
   could save ~$1,899–$2,099 if it weren't mandatory; only worth it if you can't budget or
   cook. (Source: doc 01)
2. **What dining options does BBC have, and what's the main complaint?**
   Expected: Only four — Roary's Bay Cafe, Starbucks, Vicky's, Chick-fil-A — vs 35+ across
   campuses; complaints are limited hours (some close 3:30pm), food shortages, and price.
   (Source: doc 05)
3. **Where can students with gluten or kosher restrictions eat on campus?**
   Expected: Limited — 8th St. Kitchen only "avoids" gluten (no cross-contamination control);
   the one consistent kosher option is Miro's food truck, closed weekends. (Sources: doc 04, 06)
4. **Name a few late-night food spots near campus.**
   Expected: Night Owl (cookies, open to 2–3am) and Rancho Mateo (open to 2am weekdays).
   (Sources: doc 03, 02)
5. **How much does parking cost at FIU?**
   Expected: Out of scope — no document covers parking, so the system should refuse. A
   deliberate refusal test for the grounding behavior.

## Anticipated Challenges

- **Stale data:** the documents span 2011–2024, so some venues, hours, and prices are out of
  date. The system may state old hours confidently — a known limitation worth flagging.
- **Conflicting sources:** opinion pieces disagree (one student says healthy options exist,
  another says they don't). The system has to present what the documents say rather than
  pretend there's one answer.
- **Off-topic retrieval:** when a question's wording overlaps several venue lists, retrieval can
  pull loosely related chunks — exactly what happened in the Q4 late-night failure case.

## AI Tool Plan

Which parts of the pipeline I used AI to implement, and which I drove myself:
- **Spec decisions (mine):** domain, chunk strategy, k, the 5 eval questions — I chose these;
  AI explained the tradeoffs when I asked.
- **AI-implemented from my spec:** `ingest.py` chunker, `rag.py` embedding/retrieval/generation,
  `app.py` Gradio interface, `eval.py` harness.
- **What I changed/checked:** I set the chunk strategy and sizes myself (paragraph-based,
  500–800 chars) and inspected sample chunks to confirm none were cut mid-venue; I rejected a
  plain fixed-character split. I also required source citations to be built in code, not left to
  the LLM. (Full detail in README AI Usage section.)

## Architecture

See `architecture.md` (Mermaid pipeline diagram): Document Ingestion → Chunking → Embedding
(all-MiniLM-L6-v2) → Vector Store (ChromaDB) → Retrieval (top-k=4) → Generation
(Groq llama-3.3-70b-versatile, grounded).
