import networkx as nx


def stimulateShock(G: nx.DiGraph, source: str, intensity: float, obsPeriod: int) -> dict: 

    riskScore = {node: 0.0 for node in G.nodes}  
    arrivalTime = {node: float('inf') for node in G.nodes}
    arrivalTime[source] = 0
    if source not in G: 
        return riskScore
    
    riskScore[source]= min(1.0, intensity)

    queue = [source]
    visited = set()    

    while queue: 
        curNode = queue.pop(0)
        visited.add(curNode)
        curRisk = riskScore[curNode]

        for adjNode in G.successors(curNode): 
            edgeData = G.get_edge_data(curNode, adjNode)
            edgeTransit = edgeData.get('transit_time_days', 0)

            transportTime = arrivalTime[curNode] + edgeTransit
            arrivalTime[adjNode]=min(arrivalTime[adjNode], transportTime)
            nodeData = G.nodes[adjNode]

            volWeight = edgeData.get('volume_weight', 1.0)
            bufferDays= nodeData.get('buffer_days')

            if obsPeriod>0: 
                av = max(0.0, 1.0- ((bufferDays+transportTime)/obsPeriod))
            else: 
                av = 1.0             # If observation period is zero days, wrost impact is calculated

            propRisk = curRisk*volWeight*av
            riskScore[adjNode]= min(1.0, riskScore[adjNode]+propRisk)

            if adjNode not in visited and adjNode not in queue: 
                queue.append(adjNode)

    return riskScore

if __name__ == "__main__": 
    testGraph = nx.DiGraph()
    testGraph.add_node("Factory_A", buffer_days=5)          # buffer days represent the good we have in stock
    testGraph.add_node("Factory_B", buffer_days=7)
    testGraph.add_edge("Factory_A", "Factory_B", volume_weight =0.8, transit_time_days=10)

    results = stimulateShock(testGraph, "Factory_A", intensity=0.9, obsPeriod=15)
    print("Risk Factors for 15 days:", results)

    results = stimulateShock(testGraph, "Factory_A", intensity=0.9, obsPeriod=30)
    print("Risk Factors for 30 days:", results)

        

