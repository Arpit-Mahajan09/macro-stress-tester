# Macroeconomic Geopolitical Stress-Tester & Supply Chain Predictor

An autonomous, agentic framework built with LangChain and NetworkX to simulate the impacts of geopolitical shocks on global supply chains and corporate financial margins. 

The system maps physical infrastructure networks as weighted directed graphs and models multi-stage risk propagation under uncertainty using a deterministic network flow and probabilistic state-space simulation.

## Key Features

* **Autonomous Data Gathering:** Continuously scrapes high-value maritime and macroeconomic RSS feeds (FreightWaves, WSJ, SupplyChainBrain) using `BeautifulSoup` and `feedparser`.
* **Structured NLP Threat Parsing:** Utilizes **Llama 3.3 (via Groq)** and LangChain structured outputs to extract precise operational indicators (target nodes, disruption intensity, and time period of imact) from unstructured news text.
* **Risk Simulation:** Models the global supply chain as a Directed Graph using **NetworkX**. Calculates cumulative risk, transit delays, and inventory buffer attenuation using a custom topological layer-by-layer traversal engine.
* **Terminal UI:** Features command-line interface built with **Rich**, providing live updates, threat tables, and execution reports.


## 🛠️ System Architecture Overview

The system decouples natural language understanding, discrete graph traversals, and quantitative simulations to maximize reasoning fidelity and eliminate large language model (LLM) hallucinations during mathematical computations.

    
                   +---------------------------------------+
                   |              User CLI                 |
                   +-------------------+-------------------+
                                       |
                                       v
                   +-------------------+-------------------+
                   |    LangChain Core Orchestrator        |
                   | (ReAct Loop + SummaryBufferMemory)    |
                   +-------------------+-------------------+
                                       |
               +-----------------------+-----------------------+
               |                                               |
               v                                               v
    +----------+------------+                       +----------+------------+
    |  Graph Traversal Tool |                       | Cascade Simulator Tool|
    |   (NetworkX Engine)   |                       |   (NumPy / Pandas)    |
    +----------+------------+                       +----------+------------+
               |                                               |
               v                                               v
    +----------+------------+                       +----------+------------+
    | Parses nodes, edges,  |                       | Computes cumulative   |
    | and structural routes |                       | distributions (CDF)   |
    | from graph state      |                       | & dynamic margins     |
    +-----------------------+                       +-----------------------+
## 🏗️ System Architecture

The project is heavily modularized to separate the AI reasoning loop from the underlying mathematical engine:

```text
macro-tress-tester/
│
├── data/
│   └── supply_chain.json       # Graph baseline (nodes, edges, transit times)
│
├── src/
│   ├── dataScrapper/
│   │   └── newsScraper.py          # RSS feed extraction & text cleaning
│   │   └── eventParesr.py           # LangChain + Groq Pydantic extraction
│   │
│   ├── tools/
│   │   └── simTools.py             # LangChain tool wrapper for the math engine
│   │   └── graphTools.py
│   │
│   ├── agent.py
│   ├── mainIngestion.py            
│   ├── graphEngine.py               # NetworkX logic: loads and maps the JSON data
│   └── simulator.py                 # Core mathematical state-space propagation
│
├── main.py                          # The core Watchdog loop and Terminal UI
├── .env                             # Environment variables (API keys)
└── requirements.txt                
``` 


## Installation Guide

### Prerequisites
* Python 3.10+
* Valid LLM API Key (configured in environment)

### Installation
1. Clone the repository and install the required libraries using:  
```bash 
python3 -m venv venv 
source venv/bin/activate
pip install -r requirements.txt 
```

2. Generate a .env file to store Groq API Key
`GROQ_API_KEY= "API KEY"  `

## The Mathematical Propagation Framework

To model how a localized shock cascades, the simulator should calculate a dynamic risk score $R_v \in [0, 1]$ for each downstream node $v$. The calculation accounts for incoming volume weights, transit delays, and inventory buffers.

It is assumed that the goods that have been moved for transportation from source node would not be affected. 

Let initial shock intensity applied to a source node be $S \in [0, 1]$. For any downstream node $v$, its risk is a function of its parent nodes $P(v)$ in the directed network:

$$R_v = \min\left(1, \sum_{u \in P(v)} R_u \cdot W_{uv} \cdot \alpha_v\right)$$

Where:
* $R_u$ is the propagated risk score of the upstream parent node.
* $W_{uv}$ is the `volume_weight` of the directional edge from $u$ to $v$ (the proportion of supply sourced from that link).
* $\alpha_v \in [0, 1]$ is the Buffer Attenuation Factor, which represents how effectively the node's internal inventory can cushion the shock over a given simulation horizon $T$:

$$\alpha_v = \max\left(0, 1 - \frac{B_v}{T}\right)$$

Here, $B_v$ represents the node's `inventory_buffer_days` + `total_transit_time`
* `inventory_buffer_days` = The days of stock left
* `total_transit_time` = The time that takes for goods to arrive on the destination



## Core Engineering Principles

### 1. Zero-Hallucination 
The LangChain agent functions strictly as an analytical orchestrator. It uses a structured ReAct loop to isolate variables from unstructured user prompts. It is then passed to Python tools for execution, and a quantitative result is synthesised for user.

### 2. Network Layout & Cascading Failures
Supply networks are parsed into a directed graph $G = (V, E)$ using NetworkX.The graph is then traverssed through BFS and the imact is calulated in an $O(V + E)$ runtime complexity.

### 3. Quantitative Risk Modeling
The simulator models shock waves across the structural layers using cumulative distribution functions (CDFs) to track inventory depletion over a period alongside state-space estimations of delayed margin compression over a multi-quarter window.


## Modification Guide 

1. The time period for imact calculations is considered if not mentioned in prompt. 

2. To modify LLM used change the Langchain agents used in `/src/agent.py`, then modify the .env file accordingly. 

3. To modify the supply chain graph change the `/data/mockData.json` 

4. News sources can be modified in `/src/dataScrapper/newsScrapper.py` 

## Lisence
This project is licensed under the MIT License - see the LICENSE file for details.