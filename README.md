
https://github.com/user-attachments/assets/9f7518e9-93c3-4d35-9a1c-28eb796ae01d
# Version Tree Table Explorer

A high-performance, zero-library implementation of a hierarchical version history table. [cite_start]This application translates a complex version tree into a linear, paginated tabular format similar to a Git commit history client[cite: 7, 12].

## 🚀 Live Demo
**https://version-tree-ruddy.vercel.app**

---

## 🛠 Features
** Live Video Example **
  ``` bash
   Uploading Screen Recording 2026-02-25 144126.mp4…


### 1. Visual Version Tree
* [cite_start]**Hierarchical Representation**: The first column uses custom-built connectors and indentation to show parent-child relationships[cite: 104, 105].
* [cite_start]**Node Indicators**: Distinguishes between `TRUNK`, `BRANCH`, and `RELEASE` types using unique visual indicators[cite: 13, 109].
* [cite_start]**Persistence**: Tree connectors (vertical lines) remain consistent even when scrolling or paginating, ensuring the mental model of the hierarchy is never lost[cite: 119, 122].

### 2. Smart Pagination
* [cite_start]**Page Size**: Fixed at 10 rows per page.
* [cite_start]**Integrity**: Versions are ordered using a pre-order Depth-First Search (DFS) to ensure no child ever appears before its parent[cite: 121, 122].

### 3. Interactive Selection
* [cite_start]**Ancestry Highlighting**: Clicking any row highlights the selected version and its entire ancestral path back to the root[cite: 124, 126].
* [cite_start]**Stateful**: Selection state is maintained during pagination[cite: 127].

---

## 🏗 Architecture & Logic

### Data Modeling
[cite_start]The application ingests a flat list of version objects and constructs an adjacency-list based tree[cite: 9, 11]. [cite_start]Each node tracks its depth and sibling status to determine which visual connectors to render[cite: 107, 108].

### The Linearization Algorithm
[cite_start]To solve the challenge of displaying a tree in a 10-row table without external libraries[cite: 129, 130]:
1. **DFS Traversal**: Flattens the tree while recording the "active branch" state for every node.
2. **Bitmask Rendering**: Each row knows which vertical lines (`│`) to draw based on whether its ancestors have "unvisited" siblings later in the list.
3. [cite_start]**Ancestry Path**: Pre-calculates parent IDs for $O(1)$ lookup during selection events[cite: 142].

---

## 💻 Tech Stack
* [cite_start]**Backend**: Python (FastAPI / Flask) for tree traversal and pagination logic[cite: 136, 142].
* [cite_start]**Frontend**: Vanilla JavaScript, HTML5, and CSS3 (No external table or graph libraries used).

---

## 📥 Setup Instructions

### Prerequisites
* Python 3.9+
* fastapi
* uvicorn
* pydantic


### Installation
1. **Clone the repository**:
   ```bash
   git clone [https://github.com/your-username/version-tree-table.git](https://github.com/your-username/version-tree-table.git)
   cd version-tree-table
2. ** Install requirements file **
   ```bash
   pip install -r requirements.txt
3.**Run on Local**
  ```bash
   python -m uvicorn app.main:app --reload
