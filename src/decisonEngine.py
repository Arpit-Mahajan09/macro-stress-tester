import os
from dataclasses import dataclass
from typing import Optional
from dotenv import load_dotenv

load_dotenv()

from src.graphEngine import supplyChainGraph
from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.tools import tool
from pydantic import BaseModel

cur = os.path.dirname(os.path.abspath(__file__))
jsonPath = os.path.join(cur, "..", "data", "supply_chain.json")
G = supplyChainGraph(jsonPath)  

@dataclass
class AltRoute:
    """Alternate sourcing option for a node, pulled from the graph — not
    passed in ad hoc, so the caller can't get the field order wrong."""
    name: str
    cost: float
    buffer_reduction_days: int
 
 
class Recommendation(BaseModel):
    node_id: str
    risk_score: float
    action: str          # "critical_exposure" | "activate_alt_route" | "expedite_buffer" | "monitor"
    detail: str         
    has_alt_route: bool
 
def get_alt_route(node_id: str) -> Optional[AltRoute]:
    node = supplyChainGraph.get_node(node_id)  
    if not node or not node.get("has_alternate_source"):
        return None
    return AltRoute(
        name=node.get("alt_route_name", "unspecified alternate route"),
        cost=node.get("alt_route_cost", 0.0) * 100,
        buffer_reduction_days=node.get("buffer_reduction_days", 0),
    )



def recommend(node_id:str, risk:float) -> Recommendation: 
    alt = get_alt_route(node_id); 

    if risk>=0.6 and not alt:
        return Recommendation(
            node_id=node_id,
            risk_score=risk,
            action = "critical_exposure",
            detail =(
                f"{node_id} is at critical risk ({risk:.0%}) with no alternate "
                f"route available. Recommend manual contingency review."
            ),
            has_alt_route= False,
        )
    elif risk>=0.6 and alt:
        return Recommendation(
            node_id=node_id,
            risk_score=risk,
            action = "active_alt_route",
            detail =(
                f"{node_id} is at critical risk ({risk:.0%}) with no alternate "
                f"route available. Recommend manual contingency review."
            ),
            has_alt_route= False,
        )
    elif risk>0.3:
        return Recommendation(
            node_id=node_id,
            risk_score=risk,
            action = "expedite_buffer",
            detail = (
                f"{node_id} is at critical risk ({risk:.0%}). Recommend activating "
                f"alternate sourcing via {alt.name}, at a cost of "
                f"+{alt.cost:.1f}%."
            ),
            has_alt_route= False
        )
    else: 
        return Recommendation(
            node_id=node_id,
            risk_score=risk,
            action = "monitor", 
            detail = f"{node_id} risk is low ({risk:.0%}). No action needed — continue monitoring.",
            has_alt_route= False,
        )
    

class ReadableMessage: 
    def __init__(self): 
        self.llm=ChatGroq(model="llama-3.3-70b-versatile", temperature=0)
        self.prompt = ChatPromptTemplate.from_messages([
            ("You are a numbers-to-text converter. Rephrase the given "
             "recommendation into a natural, readable message for a finance "
             "user, without changing a single number. Every number in the "
             "input must appear, unchanged, in your output."),
            ("user", "Recommendation:\n{message}"),
        ])
        chain = self.prompt | self.llm | StrOutputParser()

    def create_message(self, recommendation: Recommendation) -> str:
        try:
            return self.chain.invoke({"message": recommendation.detail})
        except Exception:
            return recommendation.detail


_narrator = ReadableMessage()

@tool
def recommend_action(node_id: str, risk_score: float) -> str:
    """Given a node id and its simulated risk score (0.0-1.0) from
    stimulate_supply_chain_shock, return a plain-language financial
    recommendation: activate an alternate supplier, expedite buffer
    inventory, flag critical exposure, or recommend monitoring only.
    Call this after stimulate_supply_chain_shock to turn a raw risk
    percentage into an actionable decision."""
    rec = recommend(node_id, risk_score)
    return _narrator.create_message(rec)
 
