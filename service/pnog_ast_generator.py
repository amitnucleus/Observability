#!/usr/bin/env python3
"""
PNOG AST Syntax Tree Generator
================================
Place this file inside: service/ folder in VS Code

Run from VS Code terminal:
    cd service
    python pnog_ast_generator.py

Scans all Python and JavaScript files, generates AST, outputs draw.io diagram.
NO external dependencies - uses Python built-in ast module only.

Output:
  - pnog_full_ast.drawio   (open in https://app.diagrams.net)
  - pnog_full_ast.json     (structured AST data)
"""

import ast
import os
import re
import json
import html as html_mod
import sys
from pathlib import Path


# ============================================================
#  CONFIGURATION - runs from inside service/ folder
# ============================================================

SCAN_DIRS = [
    "backend",
    "frontend",
]

SKIP_DIRS = {
    "node_modules", "__pycache__", ".git", ".next",
    "dist", "build", ".venv", "venv", "env",
}

PYTHON_EXTS = {".py"}
JS_EXTS = {".js", ".jsx"}


# ============================================================
#  COLOR PALETTE (matching your draw.io reference screenshot)
# ============================================================

COLORS = {
    "root":    {"fill": "#E8E5FE", "stroke": "#9B93E0", "font": "#3C3489"},
    "dir_1":   {"fill": "#D4F5E9", "stroke": "#5DCAA5", "font": "#085041"},
    "dir_2":   {"fill": "#D6EEFB", "stroke": "#85B7EB", "font": "#0C447C"},
    "dir_3":   {"fill": "#FAECE7", "stroke": "#F0997B", "font": "#993C1D"},
    "dir_4":   {"fill": "#FBEAF0", "stroke": "#ED93B1", "font": "#72243E"},
    "dir_5":   {"fill": "#FAEEDA", "stroke": "#FAC775", "font": "#633806"},
    "dir_6":   {"fill": "#EAF3DE", "stroke": "#97C459", "font": "#27500A"},
    "dir_7":   {"fill": "#E6F1FB", "stroke": "#85B7EB", "font": "#0C447C"},
    "file":    {"fill": "#F5F3E8", "stroke": "#D3D1C7", "font": "#444441"},
    "import":  {"fill": "#FBEAF0", "stroke": "#ED93B1", "font": "#72243E"},
    "class":   {"fill": "#FAEEDA", "stroke": "#FAC775", "font": "#633806"},
    "func":    {"fill": "#E6F1FB", "stroke": "#85B7EB", "font": "#0C447C"},
    "var":     {"fill": "#F5F3E8", "stroke": "#D3D1C7", "font": "#444441"},
    "deco":    {"fill": "#EAF3DE", "stroke": "#97C459", "font": "#27500A"},
    "field":   {"fill": "#F5F3E8", "stroke": "#D3D1C7", "font": "#5F5E5A"},
}

DIR_COLOR_MAP = {
    "service":  "root",
    "backend":  "dir_1",
    "frontend": "dir_2",
    "app":      "dir_3",
    "models":   "dir_4",
    "routers":  "dir_5",
    "tasks":    "dir_6",
    "pages":    "dir_7",
}

DIR_COLOR_CYCLE = ["dir_1", "dir_2", "dir_3", "dir_4", "dir_5", "dir_6", "dir_7"]


# ============================================================
#  PYTHON AST PARSER
# ============================================================

def parse_python_file(filepath):
    try:
        with open(filepath, "r", encoding="utf-8", errors="replace") as f:
            source = f.read()
    except Exception as e:
        return {"error": str(e), "nodes": []}

    if not source.strip():
        return {"error": None, "nodes": []}

    try:
        tree = ast.parse(source, filename=filepath)
    except SyntaxError as e:
        return {"error": f"SyntaxError: {e}", "nodes": []}

    nodes = []

    for node in ast.iter_child_nodes(tree):
        if isinstance(node, ast.ImportFrom):
            names = [a.name for a in node.names]
            label = f"from {node.module} import {', '.join(names[:3])}"
            if len(names) > 3:
                label += f" (+{len(names)-3})"
            nodes.append({"type": "import", "label": label, "line": node.lineno, "kind": "import"})

        elif isinstance(node, ast.Import):
            names = [a.name for a in node.names]
            nodes.append({"type": "import", "label": f"import {', '.join(names)}", "line": node.lineno, "kind": "import"})

        elif isinstance(node, ast.ClassDef):
            bases = [getattr(b, "id", "?") for b in node.bases]
            base_str = f"({', '.join(bases)})" if bases else ""
            cls_node = {
                "type": "class", "label": f"class {node.name}{base_str}",
                "line": node.lineno, "kind": "class", "children": [],
            }
            for item in node.body:
                if isinstance(item, ast.Assign):
                    for t in item.targets:
                        if hasattr(t, "id"):
                            cls_node["children"].append({"type": "field", "label": t.id, "line": item.lineno, "kind": "field"})
                elif isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    prefix = "async " if isinstance(item, ast.AsyncFunctionDef) else ""
                    args = [a.arg for a in item.args.args if a.arg != "self"]
                    cls_node["children"].append({
                        "type": "method", "label": f"{prefix}def {item.name}({', '.join(args[:3])})",
                        "line": item.lineno, "kind": "func",
                    })
            nodes.append(cls_node)

        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            prefix = "async " if isinstance(node, ast.AsyncFunctionDef) else ""
            args = [a.arg for a in node.args.args]
            decorators = []
            for d in node.decorator_list:
                if hasattr(d, "func") and hasattr(d.func, "attr"):
                    obj = getattr(d.func.value, "id", "?") if hasattr(d.func, "value") else "?"
                    dec_label = f"@{obj}.{d.func.attr}"
                    if d.args and hasattr(d.args[0], "value"):
                        dec_label += f'("{d.args[0].value}")'
                    decorators.append(dec_label)
                elif hasattr(d, "id"):
                    decorators.append(f"@{d.id}")
            nodes.append({
                "type": "function", "label": f"{prefix}def {node.name}({', '.join(args[:4])})",
                "line": node.lineno, "kind": "func", "decorators": decorators,
            })

        elif isinstance(node, ast.Assign):
            for t in node.targets:
                if hasattr(t, "id"):
                    val = ""
                    if isinstance(node.value, ast.Call):
                        if hasattr(node.value.func, "id"):
                            val = f" = {node.value.func.id}()"
                        elif hasattr(node.value.func, "attr"):
                            val = f" = .{node.value.func.attr}()"
                    nodes.append({"type": "variable", "label": f"{t.id}{val}", "line": node.lineno, "kind": "var"})

    return {"error": None, "nodes": nodes}


# ============================================================
#  JAVASCRIPT PARSER (regex-based, no dependencies)
# ============================================================

def parse_javascript_file(filepath):
    try:
        with open(filepath, "r", encoding="utf-8", errors="replace") as f:
            source = f.read()
    except Exception as e:
        return {"error": str(e), "nodes": []}

    nodes = []
    lines = source.split("\n")

    for i, line in enumerate(lines, 1):
        s = line.strip()
        if not s or s.startswith("//") or s.startswith("/*"):
            continue

        m = re.match(r'import\s+(.+?)\s+from\s+[\'"](.+?)[\'"]', s)
        if m:
            nodes.append({"type": "import", "label": f"import {m.group(1)[:35]} from '{m.group(2)}'", "line": i, "kind": "import"})
            continue

        m = re.match(r'const\s+\{(.+?)\}\s*=\s*require\([\'"](.+?)[\'"]\)', s)
        if m:
            nodes.append({"type": "import", "label": f"require('{m.group(2)}')", "line": i, "kind": "import"})
            continue

        m = re.match(r'export\s+default\s+function\s+(\w+)\s*\(([^)]*)\)', s)
        if m:
            nodes.append({"type": "function", "label": f"export default function {m.group(1)}({m.group(2)[:25]})", "line": i, "kind": "func", "decorators": []})
            continue

        m = re.match(r'(?:async\s+)?function\s+(\w+)\s*\(([^)]*)\)', s)
        if m:
            nodes.append({"type": "function", "label": f"function {m.group(1)}({m.group(2)[:25]})", "line": i, "kind": "func", "decorators": []})
            continue

        m = re.match(r'(const|let|var)\s+(\w+)\s*=\s*(?:async\s+)?\(', s)
        if m:
            nodes.append({"type": "arrow_fn", "label": f"const {m.group(2)} = () =>", "line": i, "kind": "func", "decorators": []})
            continue

        m = re.match(r'const\s+\[(\w+),\s*(\w+)\]\s*=\s*useState', s)
        if m:
            nodes.append({"type": "hook", "label": f"useState: [{m.group(1)}, {m.group(2)}]", "line": i, "kind": "var"})
            continue

        m = re.match(r'useEffect\s*\(', s)
        if m:
            nodes.append({"type": "hook", "label": "useEffect(() => ...)", "line": i, "kind": "func"})
            continue

        m = re.match(r'module\.exports\s*=', s)
        if m:
            nodes.append({"type": "export", "label": "module.exports = {...}", "line": i, "kind": "var"})
            continue

        m = re.match(r'(const|let|var)\s+(\w+)\s*=\s*\{', s)
        if m:
            nodes.append({"type": "variable", "label": f"{m.group(1)} {m.group(2)} = {{...}}", "line": i, "kind": "var"})
            continue

    return {"error": None, "nodes": nodes}


# ============================================================
#  PROJECT SCANNER
# ============================================================

def scan_project():
    print("\n  Scanning from:", os.getcwd())
    print()

    tree = {}
    counts = {"py": 0, "js": 0}

    for scan_dir in SCAN_DIRS:
        if not os.path.isdir(scan_dir):
            print(f"    SKIP: {scan_dir}/ not found")
            continue

        for root, dirs, files in os.walk(scan_dir):
            dirs[:] = sorted([d for d in dirs if d not in SKIP_DIRS])
            for fname in sorted(files):
                ext = Path(fname).suffix.lower()
                if ext not in PYTHON_EXTS and ext not in JS_EXTS:
                    continue

                filepath = os.path.join(root, fname).replace("\\", "/")
                lang = "python" if ext in PYTHON_EXTS else "javascript"

                if lang == "python":
                    parsed = parse_python_file(filepath)
                    counts["py"] += 1
                else:
                    parsed = parse_javascript_file(filepath)
                    counts["js"] += 1

                n = len(parsed.get("nodes", []))
                err = parsed.get("error")
                tag = f"({n} nodes)" if not err else f"[ERROR]"
                print(f"    {filepath:<50} {tag}")

                tree[filepath] = {"language": lang, "parsed": parsed}

    print(f"\n  Total: {counts['py']} Python + {counts['js']} JavaScript = {counts['py']+counts['js']} files")
    return tree


# ============================================================
#  DRAW.IO DIAGRAM GENERATOR
# ============================================================

class Drawio:
    def __init__(self):
        self.cells = []
        self.edges = []
        self._id = 100

    def _nid(self):
        self._id += 1
        return f"n{self._id}"

    def _style(self, kind, bold=False, big=False):
        c = COLORS.get(kind, COLORS["file"])
        b = "fontStyle=1;" if bold else ""
        s = "fontSize=14;" if big else "fontSize=12;"
        return (f"rounded=1;whiteSpace=wrap;html=1;{b}{s}"
                f"fillColor={c['fill']};strokeColor={c['stroke']};"
                f"fontColor={c['font']};fontFamily=Helvetica;arcSize=30;")

    def node(self, label, x, y, w, h, kind="file", bold=False, big=False):
        nid = self._nid()
        self.cells.append(
            f'<mxCell id="{nid}" value="{html_mod.escape(label)}" '
            f'style="{self._style(kind, bold, big)}" vertex="1" parent="1">'
            f'<mxGeometry x="{x}" y="{y}" width="{w}" height="{h}" as="geometry"/></mxCell>')
        return nid

    def edge(self, src, tgt):
        eid = self._nid()
        self.edges.append(
            f'<mxCell id="{eid}" edge="1" parent="1" source="{src}" target="{tgt}" '
            f'style="edgeStyle=orthogonalEdgeStyle;rounded=1;orthogonalLoop=1;'
            f'jettySize=auto;html=1;strokeColor=#888888;strokeWidth=1;curved=1;">'
            f'<mxGeometry relative="1" as="geometry"/></mxCell>')

    def xml(self):
        body = "\n        ".join(self.cells + self.edges)
        return (
            '<?xml version="1.0" encoding="UTF-8"?>\n'
            '<mxfile host="app.diagrams.net">\n'
            '  <diagram name="PNOG AST Syntax Tree">\n'
            '    <mxGraphModel dx="1800" dy="3000" grid="1" gridSize="10">\n'
            '      <root>\n'
            '        <mxCell id="0"/>\n'
            '        <mxCell id="1" parent="0"/>\n'
            f'        {body}\n'
            '      </root>\n'
            '    </mxGraphModel>\n'
            '  </diagram>\n'
            '</mxfile>')


def generate_diagram(project_tree):
    d = Drawio()

    X_DIR = 60
    X_FILE = 350
    X_AST = 620
    X_CHILD = 940

    y = 40
    dir_color_idx = 0

    # Root: service/
    root_id = d.node("service/", X_DIR, y, 150, 44, "root", bold=True, big=True)
    y += 70

    # Group files by directory
    dir_groups = {}
    for fp in sorted(project_tree.keys()):
        parts = fp.split("/")
        dir_path = "/".join(parts[:-1])
        if dir_path not in dir_groups:
            dir_groups[dir_path] = []
        dir_groups[dir_path].append((fp, parts[-1]))

    drawn_dirs = {"": root_id}

    for dir_path in sorted(dir_groups.keys()):
        parts = dir_path.split("/")

        # Draw directory chain
        current_path = ""
        for i, part in enumerate(parts):
            current_path = f"{current_path}/{part}" if current_path else part

            if current_path not in drawn_dirs:
                parent_path = "/".join(parts[:i]) if i > 0 else ""
                parent_id = drawn_dirs.get(parent_path, root_id)

                color_key = DIR_COLOR_MAP.get(part, DIR_COLOR_CYCLE[dir_color_idx % len(DIR_COLOR_CYCLE)])
                dir_color_idx += 1

                depth = len(current_path.split("/"))
                x_off = X_DIR + (depth - 1) * 40

                dir_id = d.node(part + "/", x_off, y, 140, 40, color_key, bold=True, big=True)
                d.edge(parent_id, dir_id)
                drawn_dirs[current_path] = dir_id
                y += 54

        # Draw files + AST nodes
        dir_id = drawn_dirs[dir_path]

        for filepath, filename in dir_groups[dir_path]:
            file_data = project_tree[filepath]
            lang = file_data["language"]
            parsed = file_data["parsed"]

            badge = " [py]" if lang == "python" else " [js]"
            file_id = d.node(filename + badge, X_FILE, y, 220, 34, "file", bold=True)
            d.edge(dir_id, file_id)
            y += 40

            for ast_node in parsed.get("nodes", []):
                kind = ast_node.get("kind", "var")
                label = ast_node["label"]
                ln = ast_node.get("line", "")

                if len(label) > 48:
                    label = label[:45] + "..."
                display = f"L{ln}: {label}" if ln else label

                for dec in ast_node.get("decorators", []):
                    if len(dec) > 45:
                        dec = dec[:42] + "..."
                    dec_id = d.node(dec, X_AST, y, 280, 28, "deco")
                    d.edge(file_id, dec_id)
                    y += 34

                ast_id = d.node(display, X_AST, y, 280, 28, kind)
                d.edge(file_id, ast_id)
                y += 34

                for child in ast_node.get("children", []):
                    cl = child["label"]
                    ck = child.get("kind", "field")
                    cln = child.get("line", "")
                    cd = f"L{cln}: {cl}" if cln else cl
                    if len(cd) > 40:
                        cd = cd[:37] + "..."
                    cid = d.node(cd, X_CHILD, y, 220, 24, ck)
                    d.edge(ast_id, cid)
                    y += 30

            y += 16

        y += 24

    return d


# ============================================================
#  MAIN
# ============================================================

def main():
    print("=" * 62)
    print("  PNOG AST Syntax Tree Generator")
    print("  Run from inside: service/ folder")
    print("=" * 62)

    cwd = os.getcwd()
    print(f"\n  Working directory: {cwd}")

    found = [d for d in SCAN_DIRS if os.path.isdir(d)]

    if not found:
        print(f"\n  ERROR: Cannot find backend/ or frontend/ folders!")
        print(f"\n  You must run this from inside the service/ folder:")
        print(f"    cd service")
        print(f"    python pnog_ast_generator.py")
        sys.exit(1)

    project_tree = scan_project()

    if not project_tree:
        print("\n  ERROR: No Python or JavaScript files found!")
        sys.exit(1)

    # Save JSON
    json_out = "pnog_full_ast.json"
    json_data = {}
    for fp, data in project_tree.items():
        json_data[fp] = {
            "language": data["language"],
            "error": data["parsed"]["error"],
            "nodes": data["parsed"]["nodes"],
        }
    with open(json_out, "w", encoding="utf-8") as f:
        json.dump(json_data, f, indent=2, default=str)

    # Generate draw.io
    print("\n  Generating draw.io AST diagram...")
    diagram = generate_diagram(project_tree)

    drawio_out = "pnog_full_ast.drawio"
    with open(drawio_out, "w", encoding="utf-8") as f:
        f.write(diagram.xml())

    # Stats
    total = len(project_tree)
    funcs = sum(sum(1 for n in d["parsed"]["nodes"] if n.get("kind") == "func") for d in project_tree.values())
    classes = sum(sum(1 for n in d["parsed"]["nodes"] if n.get("kind") == "class") for d in project_tree.values())
    imports = sum(sum(1 for n in d["parsed"]["nodes"] if n.get("kind") == "import") for d in project_tree.values())
    variables = sum(sum(1 for n in d["parsed"]["nodes"] if n.get("kind") == "var") for d in project_tree.values())

    print(f"\n{'='*62}")
    print(f"  COMPLETE!")
    print(f"{'='*62}")
    print(f"  Files parsed:     {total}")
    print(f"  Imports:          {imports}")
    print(f"  Functions:        {funcs}")
    print(f"  Classes:          {classes}")
    print(f"  Variables:        {variables}")
    print(f"{'='*62}")
    print(f"  Output files (inside service/ folder):")
    print(f"    {drawio_out}")
    print(f"    {json_out}")
    print(f"{'='*62}")
    print(f"  How to view the diagram:")
    print(f"    1. Go to https://app.diagrams.net")
    print(f"    2. File > Open from > Device")
    print(f"    3. Select {drawio_out}")
    print(f"{'='*62}\n")


if __name__ == "__main__":
    main()
