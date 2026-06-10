# The Unofficial Guide — FIU Campus Dining (RAG)

A Retrieval-Augmented Generation system that answers plain-language questions about eating
at and around Florida International University, grounded in student-written documents.

## Domain and Document Sources

**Domain:** student knowledge about FIU campus and near-campus dining — quality, value,
dietary fit, hours, and which spots are worth it.

I chose this from personal experience. My first year I struggled just to figure out how to use
my meal plan and my bonus meals, and I didn't know how to spend most of my dining dollars for
months — until a friend told me you could use them through the GrubHub app. The official
information is so short and sometimes ambiguous that it's hard to actually understand or use it
unless you go and try things yourself. That candid, practical knowledge — whether the meal plan
is worth it, where to eat between classes, what works for a dietary restriction — lives in
student-newspaper opinion pieces and word of mouth, not the official ShopFIU dining page (which
lists hours but never tells you the dining hall is repetitive or that BBC runs out of food).

**Sources (10 documents, all PantherNOW — FIU student media):**

1. [Meal plans are not as beneficial as they seem (2017)](https://panthernow.com/2017/02/24/meal-plans-are-not-as-beneficial-as-they-seem/)
2. [Best places to eat near FIU's Modesto Maidique Campus (2023)](https://panthernow.com/2023/06/30/best-places-to-eat-near-fius-modesto-maidique-campus/)
3. [Ten Iconic Food Spots Around MMC and BBC (2021)](https://panthernow.com/2021/08/31/ten-iconic-food-spots-you-need-to-try-around-the-mmc-and-bbc-campuses/)
4. [FIU is in dire need of more diverse food options (2024)](https://panthernow.com/2024/03/17/from-options-like-the-salty-donut-or-chick-fil-a-it-can-be-difficult-for-students-to-stay-within-their-diet-or-avoid-allergens/)
5. [BBC needs more food options (2023)](https://panthernow.com/2023/04/21/bbc-needs-more-food-options/)
6. [New dining hall replaces 'Fresh' (2018)](https://panthernow.com/2018/09/18/new-dining-hall-replaces-fresh/)
7. [Taking a look into 8th Street Kitchen (2022)](https://panthernow.com/2022/08/31/taking-a-look-into-8th-street-kitchen/)
8. [On Campus Dining Options for Students this Summer (2022)](https://panthernow.com/2022/06/22/on-campus-dining-options-for-students-this-summer/)
9. [FIU's Food Pantry Increases in Usage (2024)](https://panthernow.com/2024/01/25/student-fiu-food-pantry-usage/)
10. [Healthy options available on campus — Letter to the Editor (2011)](https://panthernow.com/2011/10/21/letter-to-the-editor-healthy-options-available-on-campus/)

Raw text saved in `data/raw/` with a metadata header (source, URL, title, author, date).

## Chunking Strategy

Paragraph-based chunking targeting **500–800 characters** (`ingest.py`): small paragraphs are
merged, oversized ones split on sentence boundaries. Produces **44 chunks across 10 documents**
(observed sizes 253–796 chars). Each chunk carries metadata: source file, title, URL, date,
and chunk index.

These articles are organized by paragraph, and each paragraph is usually one self-contained
thought — one venue with its hours and prices, or one complaint. Fixed-character chunking
would cut a venue's name away from its hours; one-chunk-per-article would merge 10+ venues and
dilute retrieval.

A bad chunk here would be something like a lone fragment — `"2. specialTEA Lounge and Café"` —
with the hours and prices sliced off into the next chunk, so it can't answer anything on its
own; or a 600-character blob that mashes three unrelated venues together so no single query
matches it cleanly.

## Sample Chunks (5, labeled)

1. **`08_summer_dining_options_2022.txt` (552 chars)** — *good, self-contained:* intro + Almazar
   entry with location and hours. Answerable on its own.
   > "With the slowed down pace of the summer semester… Almazar — Graham Center (MMC),
   > Monday-Friday 11 a.m.-4 p.m. … offers classic Middle Eastern and Greek dishes."
2. **`01_meal_plans_not_beneficial_2017.txt` (625 chars)** — *good:* the candid "ripped off"
   judgment plus Fresh Food hours, one complete opinion.
   > "…the meat and fish has been overcooked and undercooked on many occasions and the food is
   > not always flavorful. While their food may not always be the most diverse, Fresh is open…"
3. **`04_diverse_food_options_needed_2024.txt` (650 chars)** — *good:* a full argument about
   allergen-friendly options being worth the investment.
4. **`03_ten_iconic_food_spots_2021.txt` (584 chars)** — *good:* the Night Owl late-night entry
   (hours + prices) plus the start of the BBC list.
   > "5. Night Owl (10534 SW 8th St): Open Sunday-Thursday until 2 a.m. … Cookie prices range
   > from $2.99 to $3.50."
5. **`05_bbc_needs_more_food_options_2023.txt` (605 chars)** — *good:* the "not much
   consideration for BBC students" judgment with the food-truck reasoning.

## Embedding Model

**all-MiniLM-L6-v2** (sentence-transformers), stored in **ChromaDB** with cosine distance.
Chosen because it runs locally with no API key and no rate limits, and is well-suited to short
review-style text.

**Production tradeoff reflection:** all-MiniLM-L6-v2 is great for this project — it's tiny
(384-dimensional), fast, and runs locally with no API key or rate limits, which fits short
review-style text. But for a real deployment I'd reconsider two things. First, language: FIU is
heavily bilingual and a lot of real student talk about food mixes English and Spanish, and this
model is English-only, so I'd look at a multilingual embedding model even though it's larger and
slower. Second, scale and freshness: a production version would index far more than 44 chunks
and need regular re-embedding as venues and prices change, so I'd weigh a hosted embedding API
(simpler to scale, but adds cost and latency) against running a bigger local model myself.

## Retrieval Test Results

Real results from `eval.py` (cosine distance — lower is closer). All top results are below
0.5, clearing the Milestone 4 checkpoint.

**Query 1 — "Is the meal plan worth it for students who live on campus?"**
- `[0.216]` 01_meal_plans_not_beneficial_2017.txt — "…but are they really worth it?"
- `[0.255]` 01_meal_plans_not_beneficial_2017.txt — "students could potentially save $1,899 to $2,099…"
- `[0.289]` 01_meal_plans_not_beneficial_2017.txt — "the Fresh Food Company is where most students…"
- `[0.362]` 10_healthy_options_letter_2011.txt — healthy-options letter
Relevant: the top 3 are the exact meal-plan opinion chunks, including the cost figure the
answer needs. Semantic search found them even though the query never says "mandatory" or "$".

**Query 2 — "What dining options does BBC have, and what is the main complaint?"**
- `[0.236]` 05_bbc_needs_more_food_options_2023.txt — "…constant food shortages, limited hours…"
- `[0.404]` 05_bbc_needs_more_food_options_2023.txt — "only four at BBC… Wolfe Center renovation"
Relevant: both BBC chunks surface at the top, carrying the four venues and the hours/shortage
complaint. (Two off-topic docs appear lower at 0.39–0.40 but don't drive the answer.)

**Query 5 — "How much does parking cost at FIU?" (out of scope)**
- `[0.618]` 03_ten_iconic_food_spots_2021.txt
- `[0.629]` 01_meal_plans_not_beneficial_2017.txt
Relevant *failure signal*: every distance is 0.6+, meaning nothing in the corpus actually
matches — correctly leading to a refusal (see below).

## How Grounded Generation Is Enforced

Two mechanisms (`rag.py`): (1) the **system prompt** instructs the model to answer *only* from
the provided documents and to reply "I don't have enough information on that in my documents"
when they don't cover the question; (2) **source attribution is appended programmatically** —
the sources list is built in Python from the retrieved chunks' metadata, not generated by the
LLM, so citations can't be hallucinated.

## Example Responses

**Grounded answer 1 — "Is the meal plan worth it?"**
> According to the documents, the meal plan may not be worth it for students who live on
> campus, as they could potentially save $1,899 to $2,099 if they weren't required to purchase
> them. The meal plan is mandatory for students living in certain dorms, but the food options
> at the Fresh Food Company, where most students go to use their meal plans, are limited and
> often the same. Additionally, students who can properly budget their money for meals or buy
> groceries to cook may not benefit from the meal plan.
>
> *Retrieved from:* Meal plans are not as beneficial as they seem — 01_meal_plans_not_beneficial_2017.txt;
> LETTER TO THE EDITOR: Healthy options available on campus — 10_healthy_options_letter_2011.txt

**Grounded answer 2 — "What dining options does BBC have, and the main complaint?"**
> The Biscayne Bay Campus (BBC) has four dining locations: Roary's Bay Cafe, Starbucks,
> Vicky's, and Chick-fil-a. The main complaint is that there are limited food options and
> operating hours, with Vicky's and Roary's Bay Cafe closing at 3:30 p.m., which affects
> students with late-afternoon classes.
>
> *Retrieved from:* BBC needs more food options — 05_bbc_needs_more_food_options_2023.txt

**Out-of-scope refusal — "How much does parking cost at FIU?"**
> I don't have enough information on that in my documents.

The refusal is the correct behavior: no collected document covers parking (all retrieval
distances were 0.6+), and the grounding prompt blocks the model from answering from general
knowledge.

## Query Interface

A **Gradio** web UI (`app.py`, `python app.py` → http://localhost:7860). Input: a free-text
question box. Outputs: an **Answer** field and a **Retrieved from** field listing the source
documents. A real transcript (from the Gradio UI):
> **Q:** Is the meal plan worth it for students who live on campus?
> **Answer:** According to the documents, the meal plan may not be worth it… they could
> potentially save $1,899 to $2,099 if they weren't required to purchase them…
> **Retrieved from:** Meal plans are not as beneficial as they seem — 01_meal_plans_not_beneficial_2017.txt;
> Healthy options available on campus — 10_healthy_options_letter_2011.txt

## Evaluation Report

Five test questions in `eval_questions.json`, run via `eval.py`. **[CONFIRM the judgments in
your own words — they're yours to defend in the video.]** My judgments based on the real run:

| # | Question | Expected (short) | System response (real) | Judgment |
|---|----------|------------------|------------------------|----------|
| 1 | Meal plan worth it? | Often not; ~$1,899–2,099 savings | Says not worth it, cites the $1,899–2,099 savings, repetitive Fresh Food, budget caveat | **Accurate** |
| 2 | BBC options + complaint | 4 options; hours/shortages/price | Names all 4 venues + the 3:30pm closing-hours complaint | **Accurate** |
| 3 | Gluten/kosher options | Limited; Miro's kosher, closed wknds | Limited gluten options, Miro's kosher closed weekends, Taco Bell detail | **Accurate** |
| 4 | Late-night spots | Night Owl, Rancho Mateo | Gives 107 Taste + Rancho Mateo, **misses Night Owl** | **Partially accurate** |
| 5 | Parking cost (out of scope) | Should refuse | "I don't have enough information on that in my documents." | **Accurate (correct refusal)** |

### Failure Case — Q4, late-night spots (real)

The system answered "107 Taste FIU (closes 10–10:30pm) and Rancho Mateo (open to 2am)" but
**missed Night Owl**, the strongest late-night answer (cookies, open to 2–3am). This is a
**retrieval failure, not a generation failure**: the Night Owl text lives in
`03_ten_iconic_food_spots_2021.txt`, but the chunk that retrieved from that document at k=4 was
the article's *intro* paragraph (distance 0.312), not the Night Owl chunk — and the top
retrieved chunk was actually from the BBC document (0.281), which has nothing to do with
late-night dining. The phrase "late-night" embedded closer to general "hours/limited options"
language than to the specific Night Owl entry, so the right chunk never entered the top-4 the
LLM saw. The LLM then answered faithfully from the chunks it *did* get — so the fault is
upstream in retrieval. **Fixes:** raise k to 5–6 so more of doc 03's chunks qualify, or chunk
the venue-guide articles so each venue (name + hours) is its own retrievable unit instead of
sharing a chunk with neighbors. ("The answer was wrong" isn't the explanation — the explanation
is that the relevant chunk lost the top-k ranking to an intro paragraph and an off-topic doc.)

## Spec Reflection

**How the spec helped:** writing the chunking strategy down in `planning.md` before coding kept
me from defaulting to a lazy "split every 500 characters." Because I'd committed on paper to
paragraph-based chunks that keep a venue's name with its hours, when the implementation came
together I had a clear target to check the output against — and I caught and rejected chunks
that didn't meet it instead of just accepting whatever the splitter produced.

**Where the implementation diverged:** my spec set retrieval at k=4, and I kept it there for the
final build. But the Q4 late-night failure showed that k=4 is genuinely too tight when the
answer is split across an article — the Night Owl chunk lost its top-4 spot to an intro
paragraph. So the spec was right as a *starting* point but the evaluation surfaced a real reason
to revisit it (raise k, or chunk each venue separately) — which is the whole point of building
the eval before trusting the number.

## AI Usage

Specific instances of what I directed the AI to do and what I changed or overrode:

1. **Chunking strategy — I made the call, not the AI.** I decided on paragraph-based chunks at
   500–800 characters because these articles are written one-thought-per-paragraph (one venue
   with its hours, or one complaint). The AI implemented the splitter from that spec, but the
   sizes and the strategy were mine. I then inspected five sample chunks and confirmed none were
   cut mid-venue or left as meaningless fragments before moving on — if they had been, I'd have
   tightened the rules. (I'd considered a plain fixed-character split first and rejected it for
   exactly the reason a bad chunk shows: it would slice a venue's name away from its hours.)
2. **Forced citations in code, not in the prompt.** When the AI wired up generation, I required
   that source attribution be built programmatically in Python from the retrieved chunks'
   metadata, rather than asking the LLM to cite its sources. That way citations are guaranteed
   and can't be hallucinated — the model never gets to invent a source.
3. **Grounding/refusal behavior.** I had the AI write the system prompt, but I checked that it
   actually enforced answering only from the retrieved documents and returned a clear refusal
   for out-of-scope questions — which the parking test confirmed.

## How to Run

```bash
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env        # then paste your free Groq key from console.groq.com
python ingest.py            # build chunks.json (already included)
python rag.py               # embed + build the ChromaDB index (downloads the model once)
python eval.py              # run the 5 eval questions
python app.py               # launch the Gradio UI at http://localhost:7860
```
