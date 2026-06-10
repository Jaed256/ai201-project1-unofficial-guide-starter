# The Unofficial Guide — Project 1

A Retrieval-Augmented Generation system that answers plain-language questions about dining at
and around Florida International University, using only student-written documents and citing its
sources every time.

---

## Domain

My system covers **dining at and around FIU** — the meal plan, the dining halls and food
courts, dietary options, and the off-campus spots close enough to hit between classes.

I chose this from personal experience. My first year I struggled just to figure out how to use
my meal plan and bonus meals, and I didn't know how to spend most of my dining dollars for
months — until a friend told me you could use them through the GrubHub app. The official info is
so short and ambiguous that you can't really understand or use it without going and trying things
yourself. That candid, practical knowledge — whether the meal plan is worth it, where to eat
between classes, what works for a dietary restriction — lives in student-newspaper opinion pieces
and word of mouth, not the official ShopFIU dining page (which lists hours but never tells you
the dining hall is repetitive or that BBC runs out of food).

---

## Document Sources

10 documents, all from PantherNOW (FIU's independent student newspaper), mixing opinion pieces
(candid judgments) with food guides and news (factual venue/hours/price detail). Raw text is in
`documents/`, each file carrying a metadata header (source, URL, title, author, date).

| #  | Source | Type | URL or file path |
|----|--------|------|------------------|
| 1  | Meal plans are not as beneficial as they seem | Opinion (2017) | https://panthernow.com/2017/02/24/meal-plans-are-not-as-beneficial-as-they-seem/ |
| 2  | Best places to eat near the Modesto Maidique Campus | Guide (2023) | https://panthernow.com/2023/06/30/best-places-to-eat-near-fius-modesto-maidique-campus/ |
| 3  | Ten iconic food spots around MMC and BBC | Guide (2021) | https://panthernow.com/2021/08/31/ten-iconic-food-spots-you-need-to-try-around-the-mmc-and-bbc-campuses/ |
| 4  | FIU is in dire need of more diverse food options | Opinion (2024) | https://panthernow.com/2024/03/17/from-options-like-the-salty-donut-or-chick-fil-a-it-can-be-difficult-for-students-to-stay-within-their-diet-or-avoid-allergens/ |
| 5  | BBC needs more food options | Opinion (2023) | https://panthernow.com/2023/04/21/bbc-needs-more-food-options/ |
| 6  | New dining hall replaces 'Fresh' (8th St. Kitchen) | News (2018) | https://panthernow.com/2018/09/18/new-dining-hall-replaces-fresh/ |
| 7  | Taking a look into 8th Street Kitchen | News (2022) | https://panthernow.com/2022/08/31/taking-a-look-into-8th-street-kitchen/ |
| 8  | On-campus dining options for students this summer | Guide (2022) | https://panthernow.com/2022/06/22/on-campus-dining-options-for-students-this-summer/ |
| 9  | FIU's food pantry increases in usage | News (2024) | https://panthernow.com/2024/01/25/student-fiu-food-pantry-usage/ |
| 10 | Healthy options available on campus | Letter (2011) | https://panthernow.com/2011/10/21/letter-to-the-editor-healthy-options-available-on-campus/ |

---

## Chunking Strategy

**Chunk size:** 500–800 characters, paragraph-based (`ingest.py`, MIN_CHUNK=200, MAX_CHUNK=800).
Small paragraphs are merged; any paragraph over the max is split on sentence boundaries.

**Overlap:** 0 characters. Overlap exists to avoid losing meaning at an arbitrary cut point, but
because I split on paragraph boundaries rather than a fixed character count, each chunk already
ends at a natural break and stays a complete thought — there's no half-sentence straddling two
chunks for overlap to rescue. Adding overlap would mostly duplicate whole paragraphs and inflate
the index. (If I switched to fixed-character chunking I'd add ~10–15% overlap.)

**Why these choices fit your documents:** these articles are written one-thought-per-paragraph —
one venue with its hours and prices, or one complaint. A fixed 500-character cut would slice a
venue's name away from its hours; a whole-article chunk would merge 10+ venues and dilute
retrieval. **Preprocessing:** each file's metadata header (source/URL/title/author/date) is
parsed into structured metadata and stripped from the body before chunking; whitespace is
normalized.

**Final chunk count:** 44 chunks across 10 documents (observed sizes 253–796 chars).

**Sample chunks (5, labeled with source):**

1. `08_summer_dining_options_2022.txt` (552 chars) — *good, self-contained:* intro + the Almazar
   entry with location and hours, answerable on its own.
2. `01_meal_plans_not_beneficial_2017.txt` (625 chars) — *good:* the candid "ripped off" judgment
   plus Fresh Food hours — one complete opinion.
3. `04_diverse_food_options_needed_2024.txt` (650 chars) — *good:* a full argument about
   allergen-friendly options being worth the investment.
4. `03_ten_iconic_food_spots_2021.txt` (584 chars) — *good:* the Night Owl late-night entry
   (hours + prices) plus the start of the BBC list.
5. `05_bbc_needs_more_food_options_2023.txt` (605 chars) — *good:* the "not much consideration for
   BBC students" judgment with the food-truck reasoning.

---

## Embedding Model

**Model used:** all-MiniLM-L6-v2 (sentence-transformers), stored in ChromaDB with cosine
distance. Chosen because it runs locally with no API key and no rate limits and is well-suited to
short, review-style text.

**Production tradeoff reflection:** all-MiniLM-L6-v2 is great for this project — tiny
(384-dimensional), fast, local. But for a real deployment I'd reconsider two things. First,
language: FIU is heavily bilingual and a lot of real student food talk mixes English and Spanish,
and this model is English-only, so I'd look at a multilingual embedding model even though it's
larger and slower. Second, scale and freshness: a production version would index far more than 44
chunks and need regular re-embedding as venues and prices change, so I'd weigh a hosted embedding
API (simpler to scale, but adds cost and latency) against running a bigger local model myself.

---

## Grounded Generation

**System prompt grounding instruction:** the model is instructed to answer using *only* the
provided documents, and — verbatim — to reply *"I don't have enough information on that in my
documents."* when they don't cover the question, and not to use general knowledge about FIU or
college dining. The retrieved chunks are formatted into the prompt each labeled with their source
document, and answers are kept to 2–4 sentences.

**How source attribution is surfaced in the response:** the source list is built
**programmatically in Python** from the retrieved chunks' metadata, *not* generated by the LLM —
so citations are guaranteed and can't be hallucinated. The Gradio UI shows them in a separate
"Retrieved from" field.

**Retrieval test results (real, from `eval.py` — cosine distance, lower is closer; all top
results below 0.5):**

- *"Is the meal plan worth it?"* → `[0.216]`, `[0.255]`, `[0.289]` all from
  `01_meal_plans_not_beneficial_2017.txt`, then `[0.362]` healthy-options letter. **Relevant** —
  the top 3 are the exact meal-plan chunks, including the cost figure, found even though the query
  never says "mandatory" or "$".
- *"What dining options does BBC have, and the complaint?"* → `[0.236]` and `[0.404]` both from
  `05_bbc_needs_more_food_options_2023.txt`. **Relevant** — both BBC chunks surface on top with
  the four venues and the hours/shortage complaint.
- *"How much does parking cost at FIU?"* (out of scope) → all results `0.6+`. **Off-target by
  design** — nothing in the corpus matches, which correctly drives a refusal.

**Example responses:**

*Grounded answer 1 — "Is the meal plan worth it?"*
> According to the documents, the meal plan may not be worth it for students who live on campus,
> as they could potentially save $1,899 to $2,099 if they weren't required to purchase them… the
> food options at the Fresh Food Company are limited and often the same.
> **Retrieved from:** Meal plans are not as beneficial as they seem — 01_meal_plans_not_beneficial_2017.txt; Healthy options available on campus — 10_healthy_options_letter_2011.txt

*Grounded answer 2 — "What dining options does BBC have, and the main complaint?"*
> The Biscayne Bay Campus (BBC) has four dining locations: Roary's Bay Cafe, Starbucks, Vicky's,
> and Chick-fil-a. The main complaint is limited food options and operating hours, with Vicky's
> and Roary's Bay Cafe closing at 3:30 p.m.
> **Retrieved from:** BBC needs more food options — 05_bbc_needs_more_food_options_2023.txt

*Out-of-scope refusal — "How much does parking cost at FIU?"*
> I don't have enough information on that in my documents.

**Query interface:** a Gradio web UI (`app.py`, run `python app.py` → http://localhost:7860). The
input is a free-text question box; the outputs are an **Answer** field and a **Retrieved from**
field listing the source documents. Sample transcript: asking *"Is the meal plan worth it for
students who live on campus?"* returns the grounded answer 1 above with both sources listed.

---

## Evaluation Report

Five test questions from `planning.md`, run through the system via `eval.py`.

| # | Question | Expected answer | System response (summarized) | Retrieval quality | Response accuracy |
|---|----------|-----------------|------------------------------|-------------------|-------------------|
| 1 | Is the meal plan worth it? | Often not; ~$1,899–2,099 savings, repetitive | Says not worth it, cites the $1,899–2,099 savings + repetitive Fresh Food + budget caveat | Relevant (0.22–0.36) | Accurate |
| 2 | BBC options + main complaint | 4 venues; limited hours/shortages/price | Names all 4 venues + the 3:30pm closing-hours complaint | Relevant (0.24) | Accurate |
| 3 | Gluten/kosher options | Limited; Miro's kosher, closed weekends | Limited gluten options, Miro's kosher closed weekends, Taco Bell detail | Relevant (0.31) | Accurate |
| 4 | Late-night food spots | Night Owl, Rancho Mateo | Gives Rancho Mateo + 107 Taste, **misses Night Owl** | Partially relevant (0.28) | Partially accurate |
| 5 | FIU parking cost (out of scope) | Should refuse | "I don't have enough information on that in my documents." | Off-target by design (0.6+) | Accurate (correct refusal) |

**Retrieval quality:** Relevant / Partially relevant / Off-target
**Response accuracy:** Accurate / Partially accurate / Inaccurate

---

## Failure Case Analysis

**Question that failed:** "What are some late-night food spots near FIU's main campus?" (Q4)

**What the system returned:** Rancho Mateo (open to 2am) and 107 Taste FIU — but it **missed
Night Owl**, the strongest late-night answer (cookies, open to 2–3am).

**Root cause (tied to a specific pipeline stage):** this is a **retrieval** failure, not a
generation failure. Night Owl's text lives in `03_ten_iconic_food_spots_2021.txt`, but the chunk
retrieved from that document at k=4 was the article's *intro* paragraph (distance 0.312), not the
Night Owl chunk — and the top-ranked chunk was actually from the BBC document (0.281), which has
nothing to do with late-night dining. The phrase "late-night" embedded closer to general
"hours / limited options" language than to the specific Night Owl entry, so the right chunk never
entered the top-4 the LLM saw. The model then answered faithfully from the chunks it *did* get.

**What you would change to fix it:** raise k to 5–6 so more of that document's chunks qualify, or
chunk the venue-guide articles so each venue (name + hours) is its own retrievable unit instead
of sharing a chunk with neighbors.

---

## Spec Reflection

**One way the spec helped you during implementation:** writing the chunking strategy down in
`planning.md` before coding kept me from defaulting to a lazy "split every 500 characters."
Because I'd committed on paper to paragraph-based chunks that keep a venue's name with its hours,
I had a clear target to check the generated output against — and I caught and rejected chunks
that didn't meet it instead of accepting whatever the splitter produced.

**One way your implementation diverged from the spec, and why:** my spec set retrieval at k=4 and
I kept it there, but the Q4 late-night failure showed k=4 is genuinely too tight when the answer
is split across an article — the Night Owl chunk lost its top-4 spot to an intro paragraph. The
spec was right as a *starting* point, but building the evaluation surfaced a concrete reason to
revisit it, which is exactly why you evaluate before trusting the number.

---

## AI Usage

**Instance 1**

- *What I gave the AI:* my Chunking Strategy section — paragraph-based chunks at 500–800
  characters, because these articles are written one-thought-per-paragraph.
- *What it produced:* the `ingest.py` splitter implementing that strategy.
- *What I changed or overrode:* I set the chunk sizes and strategy myself (not the AI), inspected
  five sample chunks to confirm none were cut mid-venue, and rejected a plain fixed-character
  split because it would slice a venue's name away from its hours.

**Instance 2**

- *What I gave the AI:* my Retrieval Approach section and the requirement that the system answer
  only from retrieved context and cite sources.
- *What it produced:* the `rag.py` embedding/retrieval/generation code and the grounding prompt.
- *What I changed or overrode:* I required source attribution to be built **programmatically in
  Python** from the chunk metadata rather than asked of the LLM, so citations can't be
  hallucinated; and I verified the prompt actually enforces refusal on out-of-scope questions
  (confirmed by the parking test).

---

## Running the System

```bash
python -m venv .venv && .venv\Scripts\activate     # macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env          # then paste your free Groq key from console.groq.com
python ingest.py              # build chunks.json from documents/
python rag.py                 # embed + build the ChromaDB index (downloads the model once)
python eval.py                # run the 5 evaluation questions
python app.py                 # launch the Gradio UI at http://localhost:7860
```
