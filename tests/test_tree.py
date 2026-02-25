"""
Tests for the DFS linearization engine.
Run with: pytest tests/test_tree.py -v
"""
import pytest
from app.models import Version
from app.tree import TreeBuilder, VERTICAL, TEE, CORNER, SPACE, NODE_DOT


# ── Fixtures ─────────────────────────────────────────────────────────

def make_version(id_, parent_id=None, name=None):
    return Version(id=id_, parent_id=parent_id, name=name or id_, type="TRUNK")


# ── Test: Single root, no children ───────────────────────────────────

def test_single_root():
    builder = TreeBuilder([make_version("v1")])
    nodes = builder.linearize()
    assert len(nodes) == 1
    assert nodes[0].version.id == "v1"
    assert nodes[0].depth == 0
    assert nodes[0].connectors == [NODE_DOT]
    assert nodes[0].ancestors == []


# ── Test: Root with two children ─────────────────────────────────────

def test_root_with_two_children():
    versions = [
        make_version("root"),
        make_version("c1", "root"),
        make_version("c2", "root"),
    ]
    builder = TreeBuilder(versions)
    nodes = builder.linearize()
    ids = [n.version.id for n in nodes]
    assert ids == ["root", "c1", "c2"]

    # c1 is NOT the last child — should use TEE
    assert TEE in nodes[1].connectors
    # c2 IS the last child — should use CORNER
    assert CORNER in nodes[2].connectors


# ── Test: DFS order preserved through deep nesting ───────────────────

def test_dfs_order():
    #   root
    #   ├── A
    #   │   └── A1
    #   └── B
    versions = [
        make_version("root"),
        make_version("A",  "root"),
        make_version("A1", "A"),
        make_version("B",  "root"),
    ]
    builder = TreeBuilder(versions)
    nodes = builder.linearize()
    ids = [n.version.id for n in nodes]
    assert ids == ["root", "A", "A1", "B"]


# ── Test: Vertical lines persist across levels ────────────────────────

def test_vertical_line_persists():
    #   root
    #   ├── A
    #   │   └── A1
    #   └── B
    # A1's connectors should contain VERTICAL for level 0 (root still has B)
    versions = [
        make_version("root"),
        make_version("A",  "root"),
        make_version("A1", "A"),
        make_version("B",  "root"),
    ]
    builder = TreeBuilder(versions)
    nodes = builder.linearize()
    a1 = next(n for n in nodes if n.version.id == "A1")
    # At depth 2, connectors should be: [VERTICAL (root open), CORNER (last child), NODE_DOT]
    assert a1.connectors[0] == VERTICAL
    assert a1.connectors[1] == CORNER
    assert a1.connectors[2] == NODE_DOT


# ── Test: Ancestry is correct ─────────────────────────────────────────

def test_ancestry():
    versions = [
        make_version("root"),
        make_version("A",   "root"),
        make_version("A1",  "A"),
        make_version("A1a", "A1"),
    ]
    builder = TreeBuilder(versions)
    nodes = builder.linearize()
    a1a = next(n for n in nodes if n.version.id == "A1a")
    assert a1a.ancestors == ["root", "A", "A1"]


# ── Test: Space token when parent branch is closed ────────────────────

def test_space_when_branch_closed():
    #   root
    #   └── A
    #       └── A1    ← no siblings; root closed; A closed
    versions = [
        make_version("root"),
        make_version("A",  "root"),
        make_version("A1", "A"),
    ]
    builder = TreeBuilder(versions)
    nodes = builder.linearize()
    a1 = next(n for n in nodes if n.version.id == "A1")
    # root is closed (no more children after A), so SPACE at level 0
    assert a1.connectors[0] == SPACE


# ── Test: Pagination slicing ──────────────────────────────────────────

def test_pagination():
    versions = [make_version(f"v{i}") for i in range(25)]
    # All roots since no parent_ids
    builder = TreeBuilder(versions)
    linearized = builder.linearize()

    page1, total = builder.get_page(linearized, page=1, page_size=10)
    assert len(page1) == 10
    assert total == 3

    page3, _ = builder.get_page(linearized, page=3, page_size=10)
    assert len(page3) == 5  # 25 - 20 = 5 remaining


# ── Test: Orphan nodes become new roots ──────────────────────────────

def test_orphan_becomes_root():
    versions = [
        make_version("v1", parent_id="nonexistent"),
        make_version("v2"),
    ]
    builder = TreeBuilder(versions)
    nodes = builder.linearize()
    assert len(nodes) == 2
    # Both treated as roots since parents are absent
    for n in nodes:
        assert n.depth == 0