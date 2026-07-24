import os
from langchain.tools import tool
from pydantic import BaseModel, Field


from ..graphEngine import supplyChainGraph
from ..stimulator import stimulateShock

cur = os.path.dirname(os.path.abspath(__file__))
jsonPath = os.path.join(cur, "..","..","data", "supply_chain.json")
G = supplyChainGraph(jsonPath)


#Pydamic Input Schema
class stressTestInput(BaseModel): 
    source: str = Field(
        ...,
        description = "The exact ID of the node experiencing the shock (e.g., 'Suez_Canal', 'Taiwan_Semi_Fab'). Must exactly match graph nodes."
    )  
    intensity: float = Field(
        ..., 
        description= "A float between 0.0 and 1.0 representing shock severity. 1.0 means total capacity destruction."
    ) 
    obsPeriod: int = Field(
        ..., 
        description="The evaluation time window in days. Essential for calculating if inventory buffers hold up."
    )

@tool("stimulate_supply_chain_shock", args_schema=stressTestInput)
def stimulate_supply_chain_shock_tool(source: str, intensity: float, obsPeriod: int) -> str:
    """
    Calculates the mathematical risk propagation of a geopolitical shock through the global supply chain.
    Use this tool WHENEVER the user asks about the impact of a disruption, strike, tariff, or disaster.
    DO NOT guess the impact yourself. Always pass the exact variables to this tool.
    """
    if source not in G:
        available = ", ".join(sorted(G.nodes)[:8]) + ("..." if len(G.nodes) > 8 else "")
        return (
            f"Error: node '{source}' not found in the supply chain graph. "
            f"Some known node IDs include: {available}"
        )

    try: 
        riskSource = stimulateShock(G, source, intensity, obsPeriod)
    except ValueError as e:
        return f"Error executing stimulations: {str(e)}" 
    
    impactedNode= {node: risk for node, risk in riskSource.items() if risk>0.0}
    if not impactedNode:
        return f"Observation: No downstream supply chain impact detected for a shock at a {source} over a period of {obsPeriod} days"

    report = f"----Test Stimulation Results----\n"
    report+= f"origin: {source}, (Intensity: {intensity: .0%})\n"
    report+= f"Observation Period: {obsPeriod} day\n"
    report += "Affected Nodes & Risk of Supply Failure:\n"

    sortedImpact = sorted(impactedNode.items(), key=lambda x:x[1], reverse=True)
    for node, risk in sortedImpact: 
        report+= f"- {node}: {risk:.1%}\n"
        
    return report 
