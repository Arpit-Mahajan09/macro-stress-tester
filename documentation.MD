# Technical Documentation — Geopolitical Stress-Tester & Supply Chain Predictor

This document is a module-by-module technical reference. For a product-level overview, architecture diagram, and quick-start instructions, see `README.MD`. 

---

## 1. Data Flow

```
NewsScraper.runPipeline()
   -> list[{title, link, published, summary, full_text}]

NewsAnalysisPipeline.parseArticles(title, full_text)
   -> DisruptionEvent {isDisruption, mappedNode, mappedIntensity, impliedObsPeriod, reasoningSummary}

stimulateShock(G, mappedNode, mappedIntensity, impliedObsPeriod)
   -> dict[node_id -> risk_score in [0,1]]

recommend(node_id, risk_score)
   -> Recommendation {action, detail, has_alt_route, ...}

ReadableMessage.create_message(Recommendation)
   -> plain-language string (LLM narration, numbers untouched)

FinancialImpactEstimator.estimate_from_graph_node(node_id, risk_score)
   -> FinancialImpactReport (EPS / price sensitivity, via yfinance)
```

`main.py` drives this loop end-to-end on a 60-second cadence. `agent.py` exposes the same math engine (`stimulateShock`) and `recommend_action` through a conversational LangChain agent for ad hoc queries, bypassing the scraper/parser stage.

---

## 2. Module Reference

### `main.py`
Autonomous polling loop and Rich terminal dashboard.

- `displayDashB()` — clears the console and prints the header panel. No return value.
- `runCycle()` — one full pipeline pass:
  1. Scrapes articles via `NewsScraper.runPipeline()`.
  2. Parses each article with `NewsAnalysisPipeline.parseArticles()`, keeping only events where `isDisruption` and `mappedNode` are both truthy.
  3. If no active threats, prints a status line and returns early.
  4. Otherwise builds a threat table, picks the **single highest-intensity** threat (`max(..., key=lambda x: x[1].mappedIntensity or 0)`), and runs `stimulateShock` from that one origin.
  5. For the top 5 impacted nodes (by risk, descending), calls `recommend()` + `ReadableMessage.create_message()`, and — if the node is in `PROXY_MAP` — also calls `FinancialImpactEstimator.estimate_from_graph_node()`.
- Entry point requires `GROQ_API_KEY` in the environment (loaded via `.env` / `python-dotenv`); exits with status 1 if missing.

**Note:** only the *highest-intensity* detected threat is simulated per cycle — if two unrelated disruptions are detected in the same scrape, the lower-intensity one is silently dropped for that cycle (it may resurface next cycle if still in the feed).

### `agent.py`
Interactive conversational entry point (`python -m src.agent`).

- `stressTesterAgent()` — builds and returns a LangChain `AgentExecutor` wired to:
  - `ChatGroq(model="llama-3.3-70b-versatile", temperature=0)`
  - Tools: `stimulate_supply_chain_shock_tool` (from `simTools.py`)
  - `ConversationSummaryBufferMemory` (1000-token budget, key `chat_history`)
  - A system prompt that enforces zero-hallucination, explicit unit conversion (e.g. "completely blocked" → `intensity=1.0`), and a rule against summing/averaging risk from two independently-run shocks.
- The system prompt references calling `recommend_action` for any node with >30% risk, but **`recommend_action` is not included in the `tools` list** passed to `create_tool_calling_agent` — only `stimulate_supply_chain_shock_tool` is. As written, the agent cannot actually call `recommend_action` even though it's instructed to.
- REPL loop in `__main__`: reads from stdin until `exit`/`quit`, printing `response['output']` each turn.

### `graphEngine.py`
Builds the NetworkX graph from the JSON baseline.

- `supplyChainGraph(filepath) -> nx.DiGraph` — loads `data['nodes']` and `data['edges']`, adding each with all their JSON fields as node/edge attributes.
  - **Side effect:** this function calls `nx.draw(...)` and sets a plot title every time it's invoked, including when imported as a pure data-loading utility by `decisonEngine.py`, `eventParser.py`, `simTools.py`, etc. This doesn't render anything (no `plt.show()`), but it does populate matplotlib's current figure on every call, which is wasted work and a latent source of memory growth/plot-state bugs in a long-running process like `main.py`'s 60-second loop combined with `agent.py`'s conversational session.
- `visualizeGraph(G)` — separate function that actually calls `plt.show()`. Only invoked from the `graphEngine.py` `__main__` block, not from the rest of the pipeline.

### `stimulator.py`
The deterministic math core. See `README.MD` §"Mathematical Propagation Framework" for the formula derivation.

- `stimulateShock(G, source, intensity, obsPeriod) -> dict[node_id, float]`
  - Returns all-zero dict immediately if `source` isn't in `G`.
  - Raises `ValueError` if `G` is not a DAG.
  - Performs a **BFS-style traversal** using a FIFO queue (`queue.pop(0)`), *not* a strict topological sort via `nx.topological_sort`. Because a node is only re-added to the queue if it's neither visited nor already queued, and its risk score accumulates additively (`riskScore[adjNode] = min(1.0, riskScore[adjNode] + propRisk)`) each time a parent processes it, multi-parent nodes are still handled correctly in practice as long as all parents are enqueued before the node is dequeued and marked visited — but this relies on the specific queue/visited bookkeeping rather than an explicit topological ordering pass. The README's description of "topological-order traversal" should be read as describing the *intent/guarantee*, not the literal implementation (there's no `nx.topological_sort` call in this file).
  - `arrivalTime` tracks the *minimum* cumulative transit time to reach a node, used to compute the buffer attenuation factor `av`.
  - `buffer_days` is read from node attributes with no default (`nodeData.get('buffer_days')`) — if a node in `supply_chain.json` omits `buffer_days`, this evaluates to `None` and `bufferDays + transportTime` will raise `TypeError` at runtime.

### `decisonEngine.py`
*(filename is misspelled — "decison" not "decision" — matches the actual file on disk; imports elsewhere use `src.decisonEngine`.)*

- `AltRoute` — dataclass: `name`, `cost`, `buffer_reduction_days`.
- `get_alt_route(node_id) -> Optional[AltRoute]` — calls `supplyChainGraph.get_node(node_id)`. **This is a bug**: `supplyChainGraph` is the graph-building function from `graphEngine.py`, not a class instance, and it has no `get_node` method — this call will raise `AttributeError` any time a node actually has `has_alternate_source` data to look up (i.e., the intended "activate alt route" code path is currently broken).
- `Recommendation` (Pydantic `BaseModel`) — `node_id`, `risk_score`, `action`, `detail`, `has_alt_route`.
- `recommend(node_id, risk) -> Recommendation`:
  - `risk >= 0.6` and no alt route → `action="critical_exposure"`.
  - `risk >= 0.6` and alt route exists → `action="active_alt_route"`, but the `detail` text is copy-pasted verbatim from the critical-exposure branch ("...with no alternate route available. Recommend manual contingency review.") rather than describing the alternate route, and `has_alt_route` is hardcoded to `False` in both branches — so this field never actually reflects `alt`'s truthiness.
  - `0.3 < risk < 0.6` → `action="expedite_buffer"`, references `alt.name`/`alt.cost` in the message even though `alt` may be `None` at this risk level (only checked for existence in the `>= 0.6` branches) — this will raise `AttributeError` if triggered with no alternate route configured for that node.
  - `risk <= 0.3` → `action="monitor"`.
- `ReadableMessage` — wraps a Groq LLM call that rephrases `Recommendation.detail` into prose without changing any figures.
  - **Bug:** `__init__` builds `chain = self.prompt | self.llm | StrOutputParser()` as a *local* variable, never assigning it to `self.chain`. `create_message()` references `self.chain`, which doesn't exist — every call falls through to the `except Exception: return recommendation.detail` fallback, silently degrading to the raw deterministic text instead of the intended LLM narration. Functionally harmless (there's a fallback) but the narration feature does not currently work.
  - **Also:** `ChatPromptTemplate.from_messages([...])`'s first entry is a bare string, not a `("system", "...")` tuple like the second entry — this is inconsistent with the expected message-tuple format and is likely the root cause behind wanting to catch the exception above.
- `recommend_action` — `@tool`-decorated wrapper exposing `recommend()` + narration to LangChain agents (see `agent.py` note above about it not being registered as a usable tool there).

### `finImp.py`
Financial translation layer, real market data via `yfinance`.

- `PROXY_MAP` — hardcoded `{graph_node_id: ticker}`, currently only 2 entries (`Global_Tech_Corp` → `TSM`, `Global_Auto_Corp` → `TM`). Any other node has no financial estimate available (`main.py` handles this by only calling the estimator `if node in PROXY_MAP`).
- `FinancialImpactReport` — dataclass holding both raw figures and a `__str__` that renders the Rich-friendly report block shown in the README's example output.
- `FinancialImpactEstimator.estimate(ticker, risk_score, proxy_for=None)`:
  - Pulls `totalRevenue`, `sharesOutstanding`, `trailingEps`, `currentPrice`/`regularMarketPrice`, `trailingPE` from `yfinance.Ticker(ticker).info`.
  - Raises `ValueError` listing any of the first four fields that are `None` — `yfinance` field availability is not guaranteed per-ticker/market, so callers should expect and handle this.
  - Margin compression is scaled linearly by `risk_score` (clamped to `[0,1]`) against `margin_compression_bps` (default 150 bps at full shock).
  - Produces both a "P/E flat" price-impact estimate and a "P/E also compresses" estimate (the latter derates the multiple itself by `pe_compression_at_full_shock`, also scaled by risk).
- `estimate_from_graph_node(node_name, risk_score)` — looks up `PROXY_MAP`, raises `KeyError` if unmapped.
- `estimate_financial_impact` — `@tool`-decorated wrapper for agent use; catches `KeyError`/`ValueError` and returns a string rather than raising, so an agent conversation degrades gracefully.

### `eventParser.py`
LLM-driven structured extraction from raw article text.

- `DisruptionEvent` (Pydantic model) — `isDisruption`, `mappedNode`, `mappedIntensity` (0.0–1.0), `impliedObsPeriod` (days, defaults conceptually to 30 per the field description, but this default is only encoded in the prompt text, not enforced in code — a `None` will pass through if the LLM omits it, and `main.py`/`mainIngestion.py` handle that with `highestThreat.impliedObsPeriod or 30`).
- `NewsAnalysisPipeline.parseArticles(title, full_text) -> DisruptionEvent | None`:
  - Builds a structured-output chain against `ChatGroq(model="llama-3.3-70b-versatile")`.
  - System prompt explicitly instructs the model to leave `mappedNode` unset rather than guess or fabricate a plausible-but-wrong node ID — this is the mechanism behind the README's "grounded against the live graph's actual node list" claim, though note the node list itself (`{node_list}` in the prompt) is never actually formatted into the prompt — the `ChatPromptTemplate` declares the `{node_list}` placeholder but `chain.invoke()` is only called with `{"title": ..., "text": ...}`, so this variable is never supplied. This will raise a `KeyError`/template-variable error on every call rather than silently omitting the list.
  - Truncates `full_text` to 4000 characters before sending (`full_text[:4000]`), separate from the `TEXT_TRUNCATE_CHARS = 6000` class attribute, which is declared but unused.
  - On any exception, prints a truncated error and returns `None` — callers (`main.py`, `mainIngestion.py`) must handle `None` events, and `main.py`'s `runCycle()` does (`if event and event.isDisruption ...`).

### `newsScrapper.py`
*(filename matches actual spelling on disk: "Scrapper", not "Scraper" — module name only; the class inside is `NewsScraper`.)*

- `NewsScraper.fetchFeedData() -> list[dict]` — parses 6 hardcoded RSS feeds (CNBC ×2, SupplyChainBrain ×3, WSJ), takes the first 5 entries per feed, extracts `title`/`link`/`published`/`summary`.
- `NewsScraper.extractFullText(url) -> str` — fetches the article page directly, strips out short paragraphs (<20 chars) and a known WSJ copyright boilerplate line, joins remaining `<p>` text. Returns an error string (not an exception) on failure, which downstream code will pass into the LLM parser as if it were article text.
- `NewsScraper.runPipeline() -> list[dict]` — combines both steps; note this makes one blocking HTTP request per article (up to 30 articles per cycle), with no concurrency and only a 10-second timeout per request — a single slow site can noticeably lengthen a 60-second polling cycle.

### `simTools.py`
LangChain tool wrapper around `stimulateShock`, used by `agent.py`.

- `stressTestInput` — Pydantic arg schema (`source`, `intensity`, `obsPeriod`) shown to the LLM as tool-call parameters.
- `stimulate_supply_chain_shock_tool(source, intensity, obsPeriod) -> str` — validates `source in G` up front with a helpful error listing sample known node IDs; catches `ValueError` from `stimulateShock` (e.g. cyclic graph) and returns it as a string rather than raising, so the agent can relay it conversationally.
- Uses relative imports (`from ..graphEngine import ...`), consistent with living under `src/tools/`.

### `mainIngestion.py`
Standalone batch entry point — runs scrape + parse only (no simulation, decision, or financial layers). Useful for inspecting what the scraper/parser combination currently detects without triggering the rest of the pipeline. `dataGatherer()` prints each detected disruption's node/intensity/reasoning and returns the list of `DisruptionEvent`s.

### `test1.py`
Unit tests for `stimulateShock` (pytest). Despite the README describing this file as living at `tests/test_stimulator.py`, the uploaded copy is named `test1.py` and imports with a **bare** `from stimulator import stimulateShock` rather than `from src.stimulator import stimulateShock` — per the README's own "Known Issues" guidance, bare imports break when run from the repo root; this file will only work if run from inside `src/`, or if `src/` is separately added to `PYTHONPATH`/`sys.path`.

Covers: unknown source (all-zero output), zero-intensity shock (all-zero output), a hand-verified single-hop calculation, full-buffer absorption (shock fully absorbed by buffer, downstream risk = 0), risk-score upper bound of 1.0 under an adversarial multi-path cascade, and that a cyclic graph raises `ValueError`.

---

## 3. Expected `supply_chain.json` Schema

Inferred from `graphEngine.py` and `stimulator.py` usage (the file itself was not included in this upload):

```jsonc
{
  "nodes": [
    {
      "id": "Strait_of_Malacca",       // required, used as graph node key
      "buffer_days": 5,                 // required by stimulateShock (no default — see stimulator.py note)
      "has_alternate_source": true,     // optional, read by decisonEngine.get_alt_route
      "alt_route_name": "...",          // optional
      "alt_route_cost": 0.15,           // optional, fraction (multiplied by 100 for a % cost)
      "buffer_reduction_days": 3        // optional
      // any other fields become node attributes automatically
    }
  ],
  "edges": [
    {
      "source": "Port_of_Singapore",    // required
      "target": "Strait_of_Malacca",    // required
      "volume_weight": 0.6,             // required by stimulateShock (defaults to 1.0 if absent)
      "transit_time_days": 2            // required by stimulateShock (defaults to 0 if absent)
      // any other fields become edge attributes automatically
    }
  ]
}
```

---

## 4. Configuration

| Variable | Required by | Notes |
|---|---|---|
| `GROQ_API_KEY` | `decisonEngine.py`, `eventParser.py`, `agent.py` (via `ChatGroq`) | Checked explicitly at startup only in `main.py`; other entry points (`agent.py`, `mainIngestion.py`) will fail later, inside the first LLM call, if missing. |

Loaded via `python-dotenv`'s `load_dotenv()`, called independently in `main.py`, `agent.py`, and `decisonEngine.py`.

---

## 5. Running

```bash
python main.py              # autonomous 60s polling loop + Rich dashboard
python -m src.agent          # interactive conversational mode
python -m src.mainIngestion  # scrape + parse only, no simulation
pytest test1.py              # unit tests (run from src/, or adjust the import — see note above)
```

---

## 6. Summary of Known Issues Found in This Review

These are noted here as an engineering reference, not fixed in this pass:

1. `decisonEngine.ReadableMessage` never sets `self.chain` — LLM narration silently no-ops to the raw deterministic message every time (masked by the `except` fallback).
2. `decisonEngine.get_alt_route` calls a nonexistent `supplyChainGraph.get_node` — the "activate alternate route" path raises `AttributeError` when it would otherwise trigger.
3. `decisonEngine.recommend`'s `0.3 < risk < 0.6` branch dereferences `alt.name`/`alt.cost` without checking `alt is not None` first.
4. `decisonEngine.recommend`'s `risk >= 0.6` "has alt route" branch has a copy-pasted `detail` string identical to the no-alt-route branch, and `has_alt_route` is hardcoded `False` in both branches.
5. `eventParser.NewsAnalysisPipeline.parseArticles` declares a `{node_list}` prompt placeholder but never supplies it in `chain.invoke()`.
6. `agent.py`'s system prompt instructs the agent to call `recommend_action` for high-risk nodes, but that tool is not included in the `tools` list passed to the agent.
7. `graphEngine.supplyChainGraph` performs an `nx.draw()` side effect on every call, even when used purely for data loading (called repeatedly across the polling loop and by multiple modules).
8. `stimulator.stimulateShock` reads `buffer_days` with no default; a node missing this field in the source JSON will raise `TypeError` at simulation time rather than failing at load time.
9. `test1.py` uses a bare `from stimulator import stimulateShock`, which only resolves if run from inside `src/`.