/**
 * Version Tree Viewer — Frontend Logic
 *
 * Highlight state is owned by the backend:
 *   GET /versions?page=X&selected=Y  returns both the page nodes
 *   AND highlighted_ids (selected + all ancestors) in one response.
 *
 * This removes the second fetchAncestry() call entirely —
 * one request per interaction instead of two.
 *
 * URL params (?page=X&selected=Y) persist state across refresh/share.
 */

// ── State ────────────────────────────────────────────────────────────
const state = {
  page: 1,
  totalPages: 1,
  selected: null,        // currently selected version ID
  nodes: [],             // current page's LinearizedNode list
  highlightedIds: [],    // [selected, ...ancestors] — set directly from backend
};

// ── DOM refs ─────────────────────────────────────────────────────────
const tbody       = document.getElementById("table-body");
const btnPrev     = document.getElementById("btn-prev");
const btnNext     = document.getElementById("btn-next");
const pageIndicator = document.getElementById("page-indicator");
const metaEl      = document.getElementById("meta");

// ── Bootstrap ────────────────────────────────────────────────────────
(function init() {
  const params = new URLSearchParams(window.location.search);
  state.page     = parseInt(params.get("page") || "1", 10);
  state.selected = params.get("selected") || null;
  fetchPage(state.page);
})();

// ── Fetch & Render ────────────────────────────────────────────────────
async function fetchPage(page) {
  showLoading();
  try {
    const params = new URLSearchParams({ page });
    if (state.selected) params.set("selected", state.selected);

    const res = await fetch(`/versions?${params}`);
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const data = await res.json();

    state.page           = data.page;
    state.totalPages     = data.total_pages;
    state.nodes          = data.nodes;
    state.highlightedIds = data.highlighted_ids || []; // ← backend provides this

    metaEl.textContent = `${data.total_nodes} versions · page ${data.page} of ${data.total_pages}`;

    updateURL();
    renderRows();        // single render, no second fetch needed
    updatePagination();
  } catch (err) {
    showError(err.message);
  }
}

// ── Row Rendering ─────────────────────────────────────────────────────
function renderRows() {
  tbody.innerHTML = "";
  for (const node of state.nodes) {
    tbody.appendChild(buildRow(node));
  }
}

function buildRow(node) {
  const tr = document.createElement("tr");
  const id = node.version.id;

  // selected gets its own class; ancestors share "ancestor"
  // note: highlightedIds includes the selected id too, so check selected first
  if (id === state.selected) {
    tr.classList.add("selected");
  } else if (state.highlightedIds.includes(id)) {
    tr.classList.add("ancestor");
  }

  tr.addEventListener("click", () => onRowClick(id));

  // ── Col 1: Tree graph ──
  const tdTree = document.createElement("td");
  tdTree.className = "cell-tree";
  const connectors = node.connectors;
  for (let i = 0; i < connectors.length - 1; i++) {
    const span = document.createElement("span");
    span.className = "connector";
    span.textContent = connectors[i];
    tdTree.appendChild(span);
  }
  const dot = document.createElement("span");
  dot.className = "node-dot";
  dot.textContent = connectors[connectors.length - 1] ?? "•";
  tdTree.appendChild(dot);

  // ── Col 2: Version Name ──
  const tdName = document.createElement("td");
  tdName.className = "node-name";
  tdName.textContent = node.version.name;

  // ── Col 3: Description ──
  const tdDesc = document.createElement("td");
  tdDesc.className = "cell-author";   // reuse muted style
  tdDesc.textContent = node.version.description || "—";

  // ── Col 4: Type badge (TRUNK / BRANCH / RELEASE) ──
  const tdType = document.createElement("td");
  const badge = document.createElement("span");
  const t = (node.version.type || "TRUNK").toUpperCase();
  const badgeClass = { TRUNK: "trunk", BRANCH: "branch", RELEASE: "release" }[t] || "default";
  badge.className = `badge badge-${badgeClass}`;
  badge.textContent = t;
  tdType.appendChild(badge);

  // ── Col 5: Submitted By ──
  const tdAuthor = document.createElement("td");
  tdAuthor.className = "cell-author";
  tdAuthor.textContent = node.version.created_by;

  // ── Col 6: Created On ──
  const tdDate = document.createElement("td");
  tdDate.className = "cell-date";
  tdDate.textContent = formatDate(node.version.created_at);

  tr.append(tdTree, tdName, tdDesc, tdType, tdAuthor, tdDate);
  return tr;
}

// ── Row Click ─────────────────────────────────────────────────────────
async function onRowClick(id) {
  // Toggle: clicking the selected row deselects it
  state.selected = (state.selected === id) ? null : id;
  // Re-fetch current page — backend recalculates highlighted_ids
  await fetchPage(state.page);
}

// ── Pagination ────────────────────────────────────────────────────────
btnPrev.addEventListener("click", () => {
  if (state.page > 1) fetchPage(state.page - 1);
});
btnNext.addEventListener("click", () => {
  if (state.page < state.totalPages) fetchPage(state.page + 1);
});

function updatePagination() {
  btnPrev.disabled    = state.page <= 1;
  btnNext.disabled    = state.page >= state.totalPages;
  pageIndicator.textContent = `Page ${state.page} of ${state.totalPages}`;
}

// ── URL Sync ─────────────────────────────────────────────────────────
function updateURL() {
  const params = new URLSearchParams();
  params.set("page", state.page);
  if (state.selected) params.set("selected", state.selected);
  history.replaceState({}, "", `?${params}`);
}

// ── Helpers ───────────────────────────────────────────────────────────
function formatDate(iso) {
  try {
    return new Date(iso).toLocaleString("en-GB", {
      day: "2-digit", month: "short", year: "numeric",
      hour: "2-digit", minute: "2-digit",
    });
  } catch { return iso; }
}

function showLoading() {
  tbody.innerHTML = `<tr class="loading-row"><td colspan="6">Loading…</td></tr>`;
}

function showError(msg) {
  tbody.innerHTML = `<tr class="loading-row"><td colspan="6">Error: ${msg}</td></tr>`;
}