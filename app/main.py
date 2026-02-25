"""
FastAPI backend for the version tree viewer.

Endpoints:
  GET /versions          → paginated linearized tree
  GET /versions/{id}     → single node + its ancestry chain
  POST /versions/seed    → (dev) load sample data
  GET /                  → serve frontend HTML
"""
from __future__ import annotations
import json
from pathlib import Path
from typing import Optional
from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import HTMLResponse, Response
from fastapi.staticfiles import StaticFiles

from .models import Version, PageResponse
from .tree import TreeBuilder

# ── App setup ───────────────────────────────────────────────────────
app = FastAPI(
    title="Version Tree Viewer",
    description="Paginated, interactive version tree with ancestry highlighting.",
    version="1.0.0",
)

# Resolve static directory — works locally and on Vercel
def _find_static() -> Path:
    candidates = [
        Path(__file__).parent.parent / "static",   # local dev
        Path("/var/task/static"),                    # Vercel serverless
    ]
    for p in candidates:
        if p.exists():
            return p
    raise RuntimeError("Cannot find static directory")

static_dir = _find_static()

# Mount for local dev; on Vercel static files are served via explicit routes below
try:
    app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")
except Exception:
    pass  # Vercel may not support StaticFiles mount — fallback routes handle it

# ── In-memory store (swap for DB later) ─────────────────────────────
_versions: list[Version] = []
_builder: Optional[TreeBuilder] = None
_linearized = None   # cached full linearized list

PAGE_SIZE = 10


def _refresh_cache() -> None:
    global _builder, _linearized
    _builder = TreeBuilder(_versions)
    _linearized = _builder.linearize()


# ── Seed with sample data on startup ────────────────────────────────
def _load_sample_data() -> None:
    sample = [
        {"id": "v1",  "parent_id": None, "name": "Initial Release",   "description": "First stable trunk",           "type": "TRUNK",   "created_by": "alice", "created_at": "2024-01-01T10:00:00"},
        {"id": "v2",  "parent_id": "v1", "name": "Feature Branch A",  "description": "Auth system work",             "type": "BRANCH",  "created_by": "bob",   "created_at": "2024-01-05T09:00:00"},
        {"id": "v3",  "parent_id": "v1", "name": "Feature Branch B",  "description": "UI redesign track",            "type": "BRANCH",  "created_by": "carol", "created_at": "2024-01-06T11:00:00"},
        {"id": "v4",  "parent_id": "v2", "name": "Auth Module",        "description": "Core auth scaffolding",        "type": "TRUNK",   "created_by": "bob",   "created_at": "2024-01-10T08:00:00"},
        {"id": "v5",  "parent_id": "v2", "name": "Auth Hotfix",        "description": "Token expiry patch",           "type": "RELEASE", "created_by": "alice", "created_at": "2024-01-11T14:00:00"},
        {"id": "v6",  "parent_id": "v3", "name": "UI Overhaul",        "description": "Design system migration",      "type": "TRUNK",   "created_by": "carol", "created_at": "2024-01-12T10:00:00"},
        {"id": "v7",  "parent_id": "v4", "name": "OAuth Integration",  "description": "Google & GitHub OAuth",        "type": "TRUNK",   "created_by": "dave",  "created_at": "2024-01-15T09:30:00"},
        {"id": "v8",  "parent_id": "v4", "name": "2FA Support",        "description": "Two-factor auth flows",        "type": "BRANCH",  "created_by": "dave",  "created_at": "2024-01-16T11:00:00"},
        {"id": "v9",  "parent_id": "v5", "name": "Session Fix",        "description": "Resolve session race condition","type": "RELEASE", "created_by": "alice", "created_at": "2024-01-17T15:00:00"},
        {"id": "v10", "parent_id": "v6", "name": "Dark Mode",          "description": "System-wide dark theme",       "type": "BRANCH",  "created_by": "carol", "created_at": "2024-01-18T10:00:00"},
        {"id": "v11", "parent_id": "v6", "name": "Mobile Layout",      "description": "Responsive breakpoints",       "type": "BRANCH",  "created_by": "eve",   "created_at": "2024-01-19T08:00:00"},
        {"id": "v12", "parent_id": "v7", "name": "SSO Provider",       "description": "Enterprise SSO support",       "type": "RELEASE", "created_by": "dave",  "created_at": "2024-01-20T12:00:00"},
        {"id": "v13", "parent_id": "v8", "name": "TOTP Support",       "description": "Time-based OTP via RFC 6238",  "type": "TRUNK",   "created_by": "frank", "created_at": "2024-01-21T09:00:00"},
        {"id": "v14", "parent_id": "v11","name": "Tablet Breakpoints", "description": "768px–1024px layout fixes",    "type": "TRUNK",   "created_by": "eve",   "created_at": "2024-01-22T14:00:00"},
        {"id": "v15", "parent_id": "v12","name": "v2.0 Release",       "description": "GA release with SSO + 2FA",   "type": "RELEASE", "created_by": "alice", "created_at": "2024-01-25T10:00:00"},
    ]
    _versions.clear()
    _versions.extend([Version(**v) for v in sample])
    _refresh_cache()


_load_sample_data()


# ── Routes ───────────────────────────────────────────────────────────

@app.get("/", response_class=HTMLResponse, include_in_schema=False)
async def serve_frontend():
    html_path = static_dir / "index.html"
    return HTMLResponse(content=html_path.read_text(encoding="utf-8"))


@app.get("/static/css/styles.css", include_in_schema=False)
async def serve_css():
    content = (static_dir / "css" / "styles.css").read_text(encoding="utf-8")
    return Response(content=content, media_type="text/css")


@app.get("/static/js/app.js", include_in_schema=False)
async def serve_js():
    content = (static_dir / "js" / "app.js").read_text(encoding="utf-8")
    return Response(content=content, media_type="application/javascript")


@app.get("/versions", response_model=PageResponse, summary="Get paginated version tree")
async def get_versions(
    page: int = Query(default=1, ge=1, description="Page number (1-based)"),
    selected: Optional[str] = Query(default=None, description="Currently selected node ID"),
):
    """
    Returns a paginated slice of the linearized DFS version tree.
    Each node includes its connector tokens and ancestor IDs for
    client-side ancestry highlighting.
    """
    if _linearized is None:
        raise HTTPException(500, "Tree not initialised")

    page_nodes, total_pages = _builder.get_page(_linearized, page, PAGE_SIZE)

    return PageResponse(
        page=page,
        page_size=PAGE_SIZE,
        total_nodes=len(_linearized),
        total_pages=total_pages,
        nodes=page_nodes,
    )


@app.get("/versions/{version_id}", summary="Get a single version with ancestry")
async def get_version(version_id: str):
    """
    Returns a single node plus its full ancestry chain.
    Used by the frontend to highlight all ancestors on click.
    """
    if _linearized is None:
        raise HTTPException(500, "Tree not initialised")

    node = next((n for n in _linearized if n.version.id == version_id), None)
    if not node:
        raise HTTPException(404, f"Version '{version_id}' not found")

    ancestry_nodes = [
        n for n in _linearized if n.version.id in node.ancestors
    ]
    return {"node": node, "ancestry": ancestry_nodes}


@app.post("/versions/seed", summary="(Dev) Replace data with custom versions")
async def seed_versions(versions: list[Version]):
    """Load a custom list of versions, replacing existing data."""
    _versions.clear()
    _versions.extend(versions)
    _refresh_cache()
    return {"loaded": len(_versions), "total_nodes": len(_linearized)}


@app.get("/versions/debug/tree", summary="(Dev) Print ASCII tree to response")
async def debug_tree():
    """Returns the full tree as ASCII art for debugging."""
    if not _linearized:
        return {"tree": "(empty)"}
    lines = []
    for node in _linearized:
        prefix = "".join(node.connectors[:-1])   # all except the final •
        lines.append(f"{prefix} {node.version.name}  [{node.version.id}]")
    return {"tree": "\n".join(lines)}