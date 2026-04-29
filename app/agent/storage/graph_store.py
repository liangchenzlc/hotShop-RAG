from __future__ import annotations

import os
import pickle
from typing import Any

from langchain_community.graphs.networkx_graph import NetworkxEntityGraph

from ..utils import logger


class GraphStore:

    def __init__(self, namespace: str, working_dir: str):
        self.namespace = namespace
        self.file_path = os.path.join(working_dir, f"{namespace}.graph")
        self.working_dir = working_dir
        self._graph: NetworkxEntityGraph | None = None

    async def initialize(self) -> None:
        import networkx as nx

        os.makedirs(self.working_dir, exist_ok=True)
        if os.path.exists(self.file_path):
            with open(self.file_path, "rb") as f:
                data = pickle.load(f)
                self._graph = NetworkxEntityGraph(graph=data)
            logger.debug(f"Graph loaded: {self.file_path}")
        else:
            self._graph = NetworkxEntityGraph(graph=nx.DiGraph())

    async def finalize(self) -> None:
        if self._graph is None:
            return
        os.makedirs(self.working_dir, exist_ok=True)
        with open(self.file_path, "wb") as f:
            pickle.dump(self._graph._graph, f)

    async def drop(self) -> None:
        self._graph = None
        if os.path.exists(self.file_path):
            os.remove(self.file_path)

    def _require(self):
        if self._graph is None:
            raise RuntimeError("GraphStore not initialized")

    async def has_node(self, name: str) -> bool:
        self._require()
        return self._graph._graph.has_node(name)

    async def has_edge(self, src: str, tgt: str) -> bool:
        self._require()
        return self._graph._graph.has_edge(src, tgt)

    async def get_node(self, name: str) -> dict[str, Any] | None:
        self._require()
        if not self._graph._graph.has_node(name):
            return None
        return dict(self._graph._graph.nodes[name])

    async def get_edge(self, src: str, tgt: str) -> dict[str, Any] | None:
        self._require()
        if not self._graph._graph.has_edge(src, tgt):
            return None
        return dict(self._graph._graph.edges[(src, tgt)])

    async def upsert_node(self, name: str, data: dict[str, Any]) -> None:
        self._require()
        g = self._graph._graph
        if g.has_node(name):
            g.nodes[name].update(data)
        else:
            g.add_node(name, **data)

    async def upsert_edge(self, src: str, tgt: str, data: dict[str, Any]) -> None:
        self._require()
        g = self._graph._graph
        if g.has_edge(src, tgt):
            g.edges[(src, tgt)].update(data)
        else:
            g.add_edge(src, tgt, **data)

    async def delete_node(self, name: str) -> None:
        self._require()
        if self._graph._graph.has_node(name):
            self._graph._graph.remove_node(name)

    async def get_all_nodes(self) -> list[dict[str, Any]]:
        self._require()
        return [
            {"entity_name": n, **dict(d)}
            for n, d in self._graph._graph.nodes(data=True)
        ]

    async def get_all_edges(self) -> list[dict[str, Any]]:
        self._require()
        return [
            {"src": u, "tgt": v, **dict(d)}
            for u, v, d in self._graph._graph.edges(data=True)
        ]

    async def get_nodes_batch(self, names: list[str]) -> dict[str, dict[str, Any] | None]:
        self._require()
        g = self._graph._graph
        return {n: dict(g.nodes[n]) if g.has_node(n) else None for n in names}

    async def get_edges_batch(self, pairs: list[dict]) -> dict[tuple, dict[str, Any] | None]:
        self._require()
        g = self._graph._graph
        result = {}
        for p in pairs:
            src, tgt = p["src"], p["tgt"]
            key = (src, tgt)
            if g.has_edge(src, tgt):
                result[key] = dict(g.edges[(src, tgt)])
            else:
                result[key] = None
        return result

    async def get_node_degree(self, name: str) -> int:
        self._require()
        g = self._graph._graph
        return int(g.degree(name)) if g.has_node(name) else 0
