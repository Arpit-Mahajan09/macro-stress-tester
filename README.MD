# Macroeconomic Geopolitical Stress-Tester & Supply Chain Predictor

An autonomous, agentic framework built with LangChain and NetworkX that simulates the impact of geopolitical shocks on global supply chains, translates that impact into concrete operational recommendations, and estimates the resulting financial impact on real, tracked companies.

The system maps physical infrastructure networks as weighted directed graphs, models multi-stage risk propagation deterministically, then hands the result to two downstream layers: a rule-based recommendation engine and a market-data-grounded financial impact estimator.

## Key Features

* **Autonomous Data Gathering:** Continuously scrapes maritime and macroeconomic RSS feeds (CNBC, WSJ, SupplyChainBrain) using `BeautifulSoup` and `feedparser`.
* **Structured NLP Threat Parsing:** Uses **Llama 3.3 (via Groq)** and LangChain structured outputs to extract operational indicators (target node, disruption intensity, estimated duration) from unstructured news text, grounded against the actual node IDs in the live graph rather than a hand-maintained list.
* **Risk Simulation:** Models the global supply chain as a directed graph using **NetworkX**. Computes cumulative risk, transit delays, and inventory buffer attenuation using a topological-order traversal — this matters specifically because the graph contains nodes with multiple parents (e.g. a chokepoint fed by two different ports), and only topological ordering guarantees every parent's contribution is finalized before it's used downstream.
* **Actionable Recommendations:** A deterministic rule layer (`decisionEngine.py`) converts a raw risk score into one of four concrete actions — activate an alternate supplier, expedite buffer inventory, flag critical exposure for manual review, or monitor — then an LLM narrates it into plain language without altering any number.
* **Financial Impact Estimation:** `finImp.py` maps graph nodes to real public tickers and pulls live data via `yfinance` to estimate EPS and share-price sensitivity under the simulated shock — this is the layer that actually answers "what does this disruption mean in dollar terms," rather than stopping at a 0-1 risk score.
* **Terminal UI:** Command-line dashboard built with **Rich**, showing live threat tables and a combined risk / recommendation / financial-impact report per cycle.
* **Conversational Mode:** A separate LangChain `AgentExecutor` (`agent.py`) with conversational memory (`ConversationSummaryBufferMemory`) and two tools (simulation + recommendation), for ad hoc "what if" queries outside the autonomous monitoring loop.

## System Architecture Overview

The system decouples natural language understanding, deterministic graph traversal, and quantitative financial estimation to maximize reasoning fidelity and keep LLM involvement out of every step where a wrong number would matter.

```text
                                  +-----------------------------------+
                                  |      External Data Sources        |
                                  |  (RSS: CNBC, WSJ, SupplyChainBrain)|
                                  +-----------------+-----------------+
                                                    |
                                                    v
+---------------------------------------------------+---------------------------------------------------+
|                                   PHASE 1: INTELLIGENCE PIPELINE                                       |
|                                                                                                        |
|  +-----------------------------+                                   +-------------------------------+   |
|  |         NewsScraper         |      Raw Text (HTML parsed)       |    NewsAnalysisPipeline        |   |
|  |  (BeautifulSoup + RSS Feed) | --------------------------------> |  (Groq + Pydantic Schema,      |   |
|  |                             |                                   |   node list from live graph)   |   |
|  +-----------------------------+                                   +---------------+---------------+   |
+------------------------------------------------------------------------------------+-------------------+
                                                                                     |
                                            Extracts: {node, intensity, obsPeriod}   |
                                                                                     v
+------------------------------------------------------------------------------------+-------------------+
|                                  PHASE 2: DETERMINISTIC MATH ENGINE                                    |
|                                                                                                        |
|  +-----------------------------+                                   +-------------------------------+   |
|  |    LangChain Custom Tool    |     Passes Node + Intensity        |       NetworkX Simulator      |   |
|  |    (simTools.py wrapper)    | --------------------------------> |  (Topological-order cascade)  |   |
|  +-----------------------------+                                   +---------------+---------------+   |
+------------------------------------------------------------------------------------+-------------------+
                                                                                     |
                                                              Per-node risk score R_v |
                                                                                     v
+------------------------------------------------------------------------------------+-------------------+
|                                 PHASE 3: DECISION & FINANCIAL TRANSLATION                               |
|                                                                                                        |
|  +-----------------------------+                                   +-------------------------------+   |
|  |      decisionEngine.py      |    Recommendation (rule-based,     |          finImp.py            |   |
|  |  (recommend_action tool)    |    LLM narrates only, never        |  (yfinance - real EPS/price   |   |
|  |                             |    computes the numbers)           |   sensitivity for mapped nodes)|   |
|  +-----------------------------+                                   +-------------------------------+   |
+------------------------------------------------------------------------------------+-------------------+
                                                                                     |
                                                                                     v
+------------------------------------------------------------------------------------+-------------------+
|                                     PHASE 4: ORCHESTRATION & UI                                        |
|                                                                                                        |
|   main.py - autonomous 60s polling loop, Rich terminal dashboard, no user interaction needed            |
|   agent.py - separate interactive AgentExecutor + memory, for conversational "what if" queries          |
+---------------------------------------------------------------------------------------------------------+
```

## Repository Layout

```text
Scale/
|
|-- data/
|   `-- supply_chain.json        # Graph baseline: 18 nodes, 21 edges, real chokepoints
|                                 #   (Strait of Malacca, Suez, Panama), real transit times
|
|-- src/
|   |-- config.py                # Single source of truth for the data file path
|   |-- graphEngine.py           # Builds the NetworkX graph from JSON (pure - no plotting side effects)
|   |-- stimulator.py            # Core risk-propagation math (topological-order traversal)
|   |-- decisionEngine.py        # Risk score -> recommendation, plus LLM narration
|   |-- finImp.py                # Recommendation/risk -> real financial impact (yfinance)
|   |-- mainIngestion.py         # Batch ingestion entry point
|   |-- agent.py                 # Interactive LangChain agent (memory + 2 tools)
|   |
|   |-- dataScrapper/
|   |   |-- newsScrapper.py      # RSS feed extraction & text cleaning
|   |   `-- eventParser.py       # Groq + Pydantic structured extraction
|   |
|   `-- tools/
|       `-- simTools.py          # LangChain tool wrapper around the math engine
|
|-- tests/
|   `-- test_stimulator.py       # Unit tests for the risk-propagation engine
|
|-- main.py                      # Autonomous watchdog loop + Rich terminal UI
|-- .env                         # GROQ_API_KEY (not committed)
`-- requirements.txt
```

> Note: file locations above reflect the current, cleaned-up layout. If your local tree differs slightly (e.g. a file sitting directly in `src/` vs. `src/tools/`), the important thing is that every cross-module import uses the `src.`-qualified form (`from src.graphEngine import ...`), not a bare one - see Known Issues below for why that matters.

## Installation Guide

### Prerequisites
* Python 3.10+
* A Groq API key

### Installation
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

Create a `.env` file in the repo root:
```
GROQ_API_KEY=gsk_your_actual_key_here
```
No quotes, no spaces around `=` - both can cause the key not to load correctly depending on your `python-dotenv` version.

### Running it
```bash
python main.py            # autonomous monitoring dashboard
python -m src.agent        # interactive chat mode (run as a module, from the repo root)
```

## The Mathematical Propagation Framework

To model how a localized shock cascades, the simulator calculates a risk score R_v in [0, 1] for each downstream node v, accounting for incoming volume weights, transit delays, and inventory buffers.

Goods already in transit from a source node at the moment of the shock are assumed unaffected.

Let the initial shock intensity applied to a source node be S in [0, 1]. For any downstream node v, its risk is a function of its parent nodes P(v) in the directed network:

R_v = min( 1, sum over u in P(v) of [ R_u * W_uv * alpha_v ] )

Where:
* R_u is the propagated risk score of the upstream parent node.
* W_uv is the `volume_weight` of the directional edge from u to v (the proportion of supply sourced from that link).
* alpha_v in [0, 1] is the Buffer Attenuation Factor:

alpha_v = max( 0, 1 - (B_v / T) )

Here B_v is `buffer_days` + cumulative transit time to reach v, and T is the observation window in days.

**Why topological order, not BFS:** any node with more than one parent (e.g. `Strait_of_Malacca`, fed by both `Port_of_Kaohsiung` and `Port_of_Singapore`) needs *all* of its parents' contributions finalized before its own risk is used to compute its children's risk. A naive breadth-first traversal doesn't guarantee this ordering and can silently understate downstream risk. This was caught and fixed via a unit test that reproduces the exact failure with a minimal 4-node diamond graph - see `tests/test_stimulator.py`.

## Core Engineering Principles

#### 1. Zero-Hallucination
The LLM never computes a number. `eventParser.py` extracts structured facts (grounded against the live graph's actual node list, not a hardcoded one). `stimulator.py` runs the deterministic math. `decisionEngine.py`'s recommendation logic is pure Python rules; the LLM only rephrases the resulting sentence into natural language, and is explicitly instructed not to alter any figure - with a fallback to the raw deterministic text if the LLM step fails for any reason.

#### 2. Network Layout & Cascading Failures
Supply networks are parsed into a directed graph G = (V, E) using NetworkX, then traversed in topological order in O(V + E), with an explicit check that the graph is acyclic before propagation begins (a cyclic input raises rather than silently producing an incomplete result).

#### 3. From Risk Score to Financial Decision
A risk score alone isn't a financial decision. `decisionEngine.py` closes that gap with concrete, rule-based actions (activate alternate sourcing, expedite buffer inventory, escalate for manual review, or monitor), and `finImp.py` closes it further by translating risk into an estimated EPS and share-price sensitivity for real, tracked tickers - using live `yfinance` data rather than assumed figures.

## Example Output

```
----Stress Test Results----
Origin: Strait_of_Malacca (Intensity: 80%)
Observation Period: 21 day(s)

Suez_Canal - 34.2% risk
  Suez_Canal is at elevated risk (34%). Recommend expediting inventory
  to cover the 9-day exposure window.

Global_Tech_Corp - 12.1% risk
--- Financial Impact: TSM (proxy for Global_Tech_Corp) ---
Simulated exposure (R_v):        0.12
Assumed margin compression:      150 bps (full-shock basis)
EPS: 6.10 -> 5.98  (-2.0%)
Implied price impact (P/E flat): -2.0%
Note: Directional sensitivity only - not investment advice.
```
*(Illustrative format based on the actual report structure - figures will vary run to run with live news and live market data.)*

## License
This project is licensed under the MIT License - see the LICENSE file for details.