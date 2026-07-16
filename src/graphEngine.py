import networkx as nx
import os 
import matplotlib.pyplot as plt
import json 

def supplyChainGraph(filepath: str) ->nx.DiGraph:
    with open(filepath, "r", encoding="utf-8") as file:
        data = json.load(file)

    G = nx.DiGraph()

    for node in data['nodes']: 
        G.add_node(node['id'], **node)

    for edge in data['edges']: 
        G.add_edge(edge['source'], edge['target'], **edge)

    nx.draw(G, with_labels=True, node_color='lightblue', font_weight='bold')
    plt.title("Supply Chain Network Topology")
    return G


 
def visualizeGraph(G: nx.DiGraph) -> None:
    import matplotlib.pyplot as plt  
    nx.draw(G, with_labels=True, node_color='lightblue', font_weight='bold')
    plt.title("Supply Chain Network Topology")
    plt.show()

if __name__=="__main__":
    current = os.path.dirname(os.path.abspath(__file__))
    json_path = os.path.join(current, "..", "data", "mockData.json")
    supplyChainGraph(json_path)
    plt.show()