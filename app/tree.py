"""
Tree construction and DFS linearization engine.

Key ideas:
- Build an adjacency list (parent_id → [children]) for O(1) child lookup.
- DFS visits each node, tracking a "branch_open" stack of booleans.
  Each boolean at index i means "level i still has more siblings coming".
  This lets vertical │ lines persist correctly across page boundaries.
- Pre-calculate ancestry for O(1) highlight lookups on click.
"""
from __future__ import annotations
from collections import defaultdict
from typing import Optional
from .models import Version, LinearizedNode

# ── Connector tokens ────────────────────────────────────────────────
VERTICAL   = "│"   # level has more siblings below
TEE        = "├──" # standard child connector
CORNER     = "└──" # final child connector
SPACE      = "   " # level is closed; just padding
NODE_DOT   = "•"   # node indicator appended after connector


class TreeBuilder:
    """
    Builds and linearises a version tree.

    Usage:
        builder = TreeBuilder(versions)
        nodes   = builder.linearize()   # full ordered list
        page    = builder.get_page(nodes, page=2, page_size=10)
    """

    def __init__(self, versions: list[Version]) -> None:
        self._versions: dict[str, Version] = {v.id: v for v in versions}
        self._children: dict[Optional[str], list[str]] = defaultdict(list)
        self._roots: list[str] = []

        for v in versions:
            self._children[v.parent_id].append(v.id)

        # Roots are nodes whose parent_id is None (or whose parent doesn't exist)
        for v in versions:
            if v.parent_id is None or v.parent_id not in self._versions:
                self._roots.append(v.id)

    # ── Public API ───────────────────────────────────────────────────

    def linearize(self) -> list[LinearizedNode]:
        """Return every node in DFS pre-order with display metadata."""
        result: list[LinearizedNode] = []
        for root_id in self._roots:
            self._dfs(
                node_id=root_id,
                ancestors=[],
                branch_open=[],   # stack of booleans: True = level still has siblings
                result=result,
            )
        return result

    def get_page(
        self,
        linearized: list[LinearizedNode],
        page: int,
        page_size: int = 10,
    ) -> tuple[list[LinearizedNode], int]:
        """
        Slice the linearized list for pagination.
        Returns (page_nodes, total_pages).
        """
        total = len(linearized)
        total_pages = max(1, -(-total // page_size))  # ceiling division
        page = max(1, min(page, total_pages))
        start = (page - 1) * page_size
        return linearized[start : start + page_size], total_pages

    def lookup(self, node_id: str) -> Optional[LinearizedNode]:
        """Return a single LinearizedNode by version id (after linearize())."""
        # Re-linearize is cheap for small trees; cache if needed.
        for node in self.linearize():
            if node.version.id == node_id:
                return node
        return None

    # ── Private DFS ─────────────────────────────────────────────────

    def _dfs(
        self,
        node_id: str,
        ancestors: list[str],
        branch_open: list[bool],
        result: list[LinearizedNode],
    ) -> None:
        version = self._versions[node_id]
        children = self._children.get(node_id, [])
        depth = len(ancestors)
        is_last = self._is_last_child(node_id)

        connectors = self._build_connectors(branch_open, depth, is_last)

        result.append(
            LinearizedNode(
                version=version,
                depth=depth,
                connectors=connectors,
                ancestors=list(ancestors),
                is_last_child=is_last,
            )
        )

        # Recurse into children
        for idx, child_id in enumerate(children):
            child_is_last = idx == len(children) - 1
            # Push: at this depth, are there more siblings after this child?
            self._dfs(
                node_id=child_id,
                ancestors=ancestors + [node_id],
                branch_open=branch_open + [not child_is_last],
                result=result,
            )

    def _is_last_child(self, node_id: str) -> bool:
        version = self._versions[node_id]
        siblings = self._children.get(version.parent_id, [])
        return not siblings or siblings[-1] == node_id

    # ── Connector generation ─────────────────────────────────────────

    @staticmethod
    def _build_connectors(
        branch_open: list[bool],
        depth: int,
        is_last_child: bool,
    ) -> list[str]:
        """
        Build the list of connector tokens for a node.

        Example for depth=2, branch_open=[True, False]:
            ["│", "└──", "•"]
        """
        if depth == 0:
            return [NODE_DOT]

        tokens: list[str] = []

        # All ancestor levels: vertical line if that level's branch is still open
        for open_flag in branch_open[:-1]:
            tokens.append(VERTICAL if open_flag else SPACE)

        # Immediate parent connector
        tokens.append(CORNER if is_last_child else TEE)

        # Node indicator
        tokens.append(NODE_DOT)
        return tokens