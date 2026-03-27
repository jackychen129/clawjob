from __future__ import annotations

from typing import Dict, List, Set, Tuple


def validate_workflow_dag(nodes: List[int], edges: List[dict]) -> Tuple[bool, str, List[int]]:
    node_set: Set[int] = set(int(n) for n in nodes)
    indeg: Dict[int, int] = {n: 0 for n in node_set}
    g: Dict[int, List[int]] = {n: [] for n in node_set}
    for e in edges:
        src = int(e.get("from"))
        dst = int(e.get("to"))
        if src not in node_set or dst not in node_set:
            return False, "edge contains unknown node", []
        if src == dst:
            return False, "self loop is not allowed", []
        g[src].append(dst)
        indeg[dst] += 1

    q = [n for n in node_set if indeg[n] == 0]
    topo: List[int] = []
    while q:
        cur = q.pop(0)
        topo.append(cur)
        for nx in g[cur]:
            indeg[nx] -= 1
            if indeg[nx] == 0:
                q.append(nx)
    if len(topo) != len(node_set):
        return False, "cycle detected", []
    return True, "ok", topo


def predecessors(task_id: int, edges: List[dict]) -> List[int]:
    out: List[int] = []
    for e in edges:
        if int(e.get("to")) == int(task_id):
            out.append(int(e.get("from")))
    return out

