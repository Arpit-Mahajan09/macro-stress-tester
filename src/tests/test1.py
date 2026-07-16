from stimulator import stimulateShock
import networkx as nx
import pytest

def make_graph(edges, buffer_days):
    G = nx.DiGraph()
    for node, buf in buffer_days.items():
        G.add_node(node, buffer_days=buf)
    for src, tgt, w, t in edges:
        G.add_edge(src, tgt, volume_weight=w, transit_time_days=t)
    return G


def test_unknown_source(): #returns all 0
    G = make_graph(
        edges=[("Factory_A", "Factory_B", 0.8, 10)],
        buffer_days={"Factory_A": 5, "Factory_B": 7},
    )

    result = stimulateShock(G, "Factory_Z", intensity=0.9, obsPeriod=15)
    assert all(v == 0.0 for v in result.values())

def test_zero_shock_produces_zero_risk():
    G = make_graph(
        edges= [("Factory_A", "Factory_B", 0.8, 1.0)],
        buffer_days={"Factory_A": 5, "Factory_B": 7}
    )

    result = stimulateShock(G, "Factory_A", intensity=0.0, obsPeriod=15)
    assert result["Factory_A"] == 0.0
    assert result["Factory_B"] == 0.0


 
def test_single_hop_matches_hand_calculation():
    # A --(w=0.8, transit=10)--> B, buffer_days(B)=7, intensity=0.9, obsPeriod=30
    # av = max(0, 1 - (7+10)/30) = 13/30
    # expected B = 0.9 * 0.8 * (13/30) = 0.312
    G = make_graph(
        edges=[("Factory_A", "Factory_B", 0.8, 10)],
        buffer_days={"Factory_A": 5, "Factory_B": 7},
    )
    result = stimulateShock(G, "Factory_A", intensity=0.9, obsPeriod=30)
    assert result["Factory_A"] == pytest.approx(0.9)
    assert result["Factory_B"] == pytest.approx(0.312, abs=1e-6)
    

def test_full_buffer_absorbs_shock():
    # bufferDays+transportTime=obsperod
    G = make_graph(
        edges=[("Factory_A", "Factory_B", 0.8, 5)],
        buffer_days={"Factory_A": 0, "Factory_B": 20},
    )
    result = stimulateShock(G, "Factory_A", intensity=0.9, obsPeriod=15)
    assert result["Factory_A"] == pytest.approx(0.9)  
    assert result["Factory_B"] == 0.0                   

def test_risk_score_bounded_0_to_1():
    # even with an adversarial high-weight cascade, Rv never exceeds 1
    G = make_graph(
        edges=[
            ("A", "B", 1.0, 0),
            ("B", "C", 1.0, 0),
            ("A", "C", 1.0, 0),
        ],
        buffer_days={"A": 0, "B": 0, "C": 0},
    )
    result = stimulateShock(G, "A", intensity=1.0, obsPeriod=1)
    assert all(0.0 <= v <= 1.0 for v in result.values())

def test_cyclic_graph_raises_or_handles_gracefully():
    G = make_graph(
        edges=[
            ("A", "B", 0.8, 1),
            ("B", "C", 0.5, 1),
            ("C", "A", 0.2, 1),  
        ],
        buffer_days={"A": 5, "B": 5, "C": 5},
    )

    with pytest.raises(ValueError):
        stimulateShock(G, "A", intensity=0.5, obsPeriod=15)


