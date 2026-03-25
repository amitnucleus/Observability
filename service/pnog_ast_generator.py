#!/usr/bin/env python3
"""
PNOG Deep AST Generator v2
============================
Extracts EVERY AST node from Python and JavaScript files:
  - Module structure
  - All imports (from/import, aliases)
  - All function/class definitions with FULL bodies
  - All variable assignments with values
  - All function calls with arguments
  - All attributes/name accesses
  - All return statements
  - All control flow (if/for/while/try)
  - All decorators
  - All string/number constants
  - All binary/boolean operations

Place inside: service/ folder
Run:  python pnog_deep_ast.py

Output:
  - pnog_deep_ast.json          (full AST for every file)
  - pnog_deep_ast_summary.json  (human-readable summary)
  - pnog_deep_ast.dot           (Graphviz DOT for visualization)
  - pnog_deep_ast.html          (self-contained visual tree)
"""

import ast
import os
import re
import json
import sys
from pathlib import Path


# ============================================================
#  CONFIGURATION
# ============================================================

SCAN_DIRS = ["backend", "frontend"]

SKIP_DIRS = {
    "node_modules", "__pycache__", ".git", ".next",
    "dist", "build", ".venv", "venv", "env",
}

PYTHON_EXTS = {".py"}
JS_EXTS = {".js", ".jsx"}


# ============================================================
#  PYTHON DEEP AST PARSER
# ============================================================

def python_node_to_dict(node, depth=0, max_depth=20):
    """Recursively convert every AST node to a dictionary."""
    if depth > max_depth:
        return {"_type": "...", "_truncated": True}

    if node is None:
        return None

    if isinstance(node, list):
        return [python_node_to_dict(item, depth + 1, max_depth) for item in node]

    if not isinstance(node, ast.AST):
        # Primitive value (str, int, float, bool, None)
        return node

    result = {
        "_type": node.__class__.__name__,
    }

    # Add line/col info
    if hasattr(node, "lineno"):
        result["_line"] = node.lineno
    if hasattr(node, "col_offset"):
        result["_col"] = node.col_offset
    if hasattr(node, "end_lineno"):
        result["_end_line"] = node.end_lineno

    # Process all fields of the AST node
    for field_name, field_value in ast.iter_fields(node):
        if isinstance(field_value, ast.AST):
            result[field_name] = python_node_to_dict(field_value, depth + 1, max_depth)
        elif isinstance(field_value, list):
            items = []
            for item in field_value:
                if isinstance(item, ast.AST):
                    items.append(python_node_to_dict(item, depth + 1, max_depth))
                else:
                    items.append(item)
            result[field_name] = items
        else:
            result[field_name] = field_value

    return result


def parse_python_deep(filepath):
    """Parse Python file into complete AST dictionary."""
    try:
        with open(filepath, "r", encoding="utf-8", errors="replace") as f:
            source = f.read()
    except Exception as e:
        return {"error": str(e)}

    if not source.strip():
        return {"_type": "Module", "body": [], "_empty": True}

    try:
        tree = ast.parse(source, filename=filepath)
    except SyntaxError as e:
        return {"error": f"SyntaxError: {e}"}

    return python_node_to_dict(tree)


def extract_python_summary(filepath):
    """Extract human-readable summary with all details."""
    try:
        with open(filepath, "r", encoding="utf-8", errors="replace") as f:
            source = f.read()
    except Exception as e:
        return {"error": str(e), "nodes": []}

    if not source.strip():
        return {"nodes": []}

    try:
        tree = ast.parse(source, filename=filepath)
    except SyntaxError as e:
        return {"error": str(e), "nodes": []}

    nodes = []

    def walk_node(node, parent_context="module", depth=0):
        """Recursively walk all nodes extracting every construct."""

        # Import
        if isinstance(node, ast.Import):
            for alias in node.names:
                nodes.append({
                    "type": "Import",
                    "module": alias.name,
                    "alias": alias.asname,
                    "line": node.lineno,
                    "context": parent_context,
                    "depth": depth,
                })

        elif isinstance(node, ast.ImportFrom):
            for alias in node.names:
                nodes.append({
                    "type": "ImportFrom",
                    "module": node.module,
                    "name": alias.name,
                    "alias": alias.asname,
                    "line": node.lineno,
                    "context": parent_context,
                    "depth": depth,
                })

        # Function definition
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            is_async = isinstance(node, ast.AsyncFunctionDef)
            args_list = []
            for a in node.args.args:
                arg_info = {"name": a.arg}
                if a.annotation:
                    arg_info["annotation"] = ast.dump(a.annotation)
                args_list.append(arg_info)

            # Defaults
            defaults = []
            for d in node.args.defaults:
                defaults.append(ast.dump(d))

            # Decorators
            decorators = []
            for d in node.decorator_list:
                decorators.append(ast.dump(d))

            # Return annotation
            returns = ast.dump(node.returns) if node.returns else None

            fn_node = {
                "type": "AsyncFunctionDef" if is_async else "FunctionDef",
                "name": node.name,
                "args": args_list,
                "defaults": defaults,
                "decorators": decorators,
                "returns": returns,
                "line": node.lineno,
                "end_line": node.end_lineno,
                "context": parent_context,
                "depth": depth,
                "body_nodes": [],
            }
            nodes.append(fn_node)

            # Walk function body
            for child in ast.walk(node):
                if child is node:
                    continue

                if isinstance(child, ast.Return):
                    ret_val = ast.dump(child.value) if child.value else "None"
                    fn_node["body_nodes"].append({
                        "type": "Return",
                        "value": ret_val,
                        "line": child.lineno,
                    })

                elif isinstance(child, ast.Yield):
                    fn_node["body_nodes"].append({
                        "type": "Yield",
                        "line": getattr(child, "lineno", None),
                    })

                elif isinstance(child, ast.Call):
                    call_info = {"type": "Call", "line": getattr(child, "lineno", None)}
                    if hasattr(child.func, "id"):
                        call_info["func"] = child.func.id
                    elif hasattr(child.func, "attr"):
                        obj = ""
                        if hasattr(child.func.value, "id"):
                            obj = child.func.value.id + "."
                        call_info["func"] = obj + child.func.attr
                    call_info["args_count"] = len(child.args)
                    call_info["kwargs_count"] = len(child.keywords)
                    fn_node["body_nodes"].append(call_info)

                elif isinstance(child, ast.Assign):
                    targets = []
                    for t in child.targets:
                        if hasattr(t, "id"):
                            targets.append(t.id)
                        elif hasattr(t, "attr"):
                            targets.append(f".{t.attr}")
                    if targets:
                        fn_node["body_nodes"].append({
                            "type": "Assign",
                            "targets": targets,
                            "value_type": child.value.__class__.__name__,
                            "line": child.lineno,
                        })

                elif isinstance(child, (ast.If, ast.For, ast.While, ast.With, ast.Try)):
                    fn_node["body_nodes"].append({
                        "type": child.__class__.__name__,
                        "line": child.lineno,
                    })

                elif isinstance(child, ast.Raise):
                    fn_node["body_nodes"].append({
                        "type": "Raise",
                        "line": child.lineno,
                    })

            # Also recurse into nested functions/classes
            for child in node.body:
                if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                    walk_node(child, f"function:{node.name}", depth + 1)

            return  # Don't recurse further for this node

        # Class definition
        elif isinstance(node, ast.ClassDef):
            bases = []
            for b in node.bases:
                if hasattr(b, "id"):
                    bases.append(b.id)
                elif hasattr(b, "attr"):
                    bases.append(f"?.{b.attr}")
                else:
                    bases.append(ast.dump(b))

            decorators = [ast.dump(d) for d in node.decorator_list]

            cls_node = {
                "type": "ClassDef",
                "name": node.name,
                "bases": bases,
                "decorators": decorators,
                "line": node.lineno,
                "end_line": node.end_lineno,
                "context": parent_context,
                "depth": depth,
                "fields": [],
                "methods": [],
            }
            nodes.append(cls_node)

            for item in node.body:
                if isinstance(item, ast.Assign):
                    for t in item.targets:
                        if hasattr(t, "id"):
                            cls_node["fields"].append({
                                "name": t.id,
                                "value_type": item.value.__class__.__name__,
                                "line": item.lineno,
                            })
                elif isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    is_async = isinstance(item, ast.AsyncFunctionDef)
                    args = [a.arg for a in item.args.args]
                    decs = [ast.dump(d) for d in item.decorator_list]
                    cls_node["methods"].append({
                        "name": item.name,
                        "args": args,
                        "decorators": decs,
                        "is_async": is_async,
                        "line": item.lineno,
                        "end_line": item.end_lineno,
                    })
                    # Recurse into method body
                    walk_node(item, f"class:{node.name}", depth + 1)

            return

        # Global assignments
        elif isinstance(node, ast.Assign):
            for t in node.targets:
                name = None
                if hasattr(t, "id"):
                    name = t.id
                elif hasattr(t, "attr"):
                    name = f"self.{t.attr}" if hasattr(t, "value") and hasattr(t.value, "id") and t.value.id == "self" else f"?.{t.attr}"

                if name:
                    value_repr = ""
                    if isinstance(node.value, ast.Constant):
                        value_repr = repr(node.value.value)[:80]
                    elif isinstance(node.value, ast.Call):
                        if hasattr(node.value.func, "id"):
                            value_repr = f"{node.value.func.id}()"
                        elif hasattr(node.value.func, "attr"):
                            obj = getattr(node.value.func.value, "id", "?") if hasattr(node.value.func, "value") else "?"
                            value_repr = f"{obj}.{node.value.func.attr}()"
                    elif isinstance(node.value, ast.Name):
                        value_repr = node.value.id
                    elif isinstance(node.value, (ast.List, ast.Tuple, ast.Dict, ast.Set)):
                        value_repr = node.value.__class__.__name__

                    nodes.append({
                        "type": "Assign",
                        "name": name,
                        "value_type": node.value.__class__.__name__,
                        "value_repr": value_repr,
                        "line": node.lineno,
                        "context": parent_context,
                        "depth": depth,
                    })

        # AugAssign (+=, -=, etc.)
        elif isinstance(node, ast.AugAssign):
            target = getattr(node.target, "id", "?")
            nodes.append({
                "type": "AugAssign",
                "target": target,
                "op": node.op.__class__.__name__,
                "line": node.lineno,
                "context": parent_context,
                "depth": depth,
            })

        # Global/Nonlocal
        elif isinstance(node, (ast.Global, ast.Nonlocal)):
            nodes.append({
                "type": node.__class__.__name__,
                "names": node.names,
                "line": node.lineno,
                "context": parent_context,
                "depth": depth,
            })

        # Expression statements (standalone calls)
        elif isinstance(node, ast.Expr):
            if isinstance(node.value, ast.Call):
                call = node.value
                func_name = ""
                if hasattr(call.func, "id"):
                    func_name = call.func.id
                elif hasattr(call.func, "attr"):
                    obj = getattr(call.func.value, "id", "?") if hasattr(call.func, "value") else "?"
                    func_name = f"{obj}.{call.func.attr}"

                args_info = []
                for a in call.args[:5]:
                    if isinstance(a, ast.Constant):
                        args_info.append(repr(a.value)[:40])
                    elif isinstance(a, ast.Name):
                        args_info.append(a.id)
                    else:
                        args_info.append(a.__class__.__name__)

                nodes.append({
                    "type": "Call",
                    "func": func_name,
                    "args": args_info,
                    "kwargs": [kw.arg for kw in call.keywords if kw.arg],
                    "line": node.lineno,
                    "context": parent_context,
                    "depth": depth,
                })

        # Control flow at module level
        elif isinstance(node, (ast.If, ast.For, ast.While)):
            nodes.append({
                "type": node.__class__.__name__,
                "line": node.lineno,
                "context": parent_context,
                "depth": depth,
            })

        elif isinstance(node, ast.Try):
            handlers = []
            for h in node.handlers:
                handler_type = None
                if h.type and hasattr(h.type, "id"):
                    handler_type = h.type.id
                handlers.append({
                    "exception": handler_type,
                    "name": h.name,
                    "line": h.lineno,
                })
            nodes.append({
                "type": "Try",
                "handlers": handlers,
                "line": node.lineno,
                "context": parent_context,
                "depth": depth,
            })

    # Walk top-level nodes
    for node in ast.iter_child_nodes(tree):
        walk_node(node, "module", 0)

    return {"nodes": nodes}


# ============================================================
#  JAVASCRIPT DEEP PARSER (regex-based)
# ============================================================

def parse_javascript_deep(filepath):
    """Deep parse JavaScript file extracting all constructs."""
    try:
        with open(filepath, "r", encoding="utf-8", errors="replace") as f:
            source = f.read()
    except Exception as e:
        return {"error": str(e), "nodes": []}

    nodes = []
    lines = source.split("\n")
    in_function = None
    brace_depth = 0

    for i, line in enumerate(lines, 1):
        s = line.strip()
        if not s or s.startswith("//"):
            continue

        # Track brace depth for context
        brace_depth += s.count("{") - s.count("}")

        # Imports
        m = re.match(r'import\s+\{([^}]+)\}\s+from\s+[\'"](.+?)[\'"]', s)
        if m:
            names = [n.strip() for n in m.group(1).split(",")]
            for name in names:
                parts = name.split(" as ")
                nodes.append({
                    "type": "ImportSpecifier",
                    "name": parts[0].strip(),
                    "alias": parts[1].strip() if len(parts) > 1 else None,
                    "source": m.group(2),
                    "line": i,
                })
            continue

        m = re.match(r'import\s+(\w+)\s+from\s+[\'"](.+?)[\'"]', s)
        if m:
            nodes.append({
                "type": "ImportDefault",
                "name": m.group(1),
                "source": m.group(2),
                "line": i,
            })
            continue

        m = re.match(r'const\s+\{([^}]+)\}\s*=\s*require\([\'"](.+?)[\'"]\)', s)
        if m:
            names = [n.strip() for n in m.group(1).split(",")]
            for name in names:
                nodes.append({
                    "type": "Require",
                    "name": name.strip(),
                    "source": m.group(2),
                    "line": i,
                })
            continue

        # Export default function
        m = re.match(r'export\s+default\s+function\s+(\w+)\s*\(([^)]*)\)', s)
        if m:
            args = [a.strip() for a in m.group(2).split(",") if a.strip()]
            nodes.append({
                "type": "ExportDefaultFunction",
                "name": m.group(1),
                "args": args,
                "line": i,
            })
            in_function = m.group(1)
            continue

        # Named function
        m = re.match(r'(?:async\s+)?function\s+(\w+)\s*\(([^)]*)\)', s)
        if m:
            args = [a.strip() for a in m.group(2).split(",") if a.strip()]
            is_async = s.strip().startswith("async")
            nodes.append({
                "type": "FunctionDeclaration",
                "name": m.group(1),
                "args": args,
                "is_async": is_async,
                "line": i,
            })
            in_function = m.group(1)
            continue

        # Arrow functions
        m = re.match(r'(const|let|var)\s+(\w+)\s*=\s*(async\s+)?\(([^)]*)\)\s*=>', s)
        if m:
            args = [a.strip() for a in m.group(4).split(",") if a.strip()]
            nodes.append({
                "type": "ArrowFunction",
                "name": m.group(2),
                "args": args,
                "is_async": bool(m.group(3)),
                "line": i,
            })
            in_function = m.group(2)
            continue

        # React hooks
        m = re.match(r'const\s+\[(\w+),\s*(\w+)\]\s*=\s*use(\w+)\((.*)?\)', s)
        if m:
            nodes.append({
                "type": "ReactHook",
                "hook": f"use{m.group(3)}",
                "state": m.group(1),
                "setter": m.group(2),
                "initial": m.group(4).strip() if m.group(4) else None,
                "line": i,
            })
            continue

        m = re.match(r'use(\w+)\s*\(', s)
        if m and m.group(1) in ("Effect", "Memo", "Callback", "Ref", "Context", "Reducer"):
            nodes.append({
                "type": "ReactHook",
                "hook": f"use{m.group(1)}",
                "line": i,
            })
            continue

        # Variable declarations with object
        m = re.match(r'(const|let|var)\s+(\w+)\s*=\s*\{', s)
        if m:
            nodes.append({
                "type": "VariableDeclaration",
                "kind": m.group(1),
                "name": m.group(2),
                "value_type": "ObjectExpression",
                "line": i,
            })
            continue

        # Variable declarations with array
        m = re.match(r'(const|let|var)\s+(\w+)\s*=\s*\[', s)
        if m:
            nodes.append({
                "type": "VariableDeclaration",
                "kind": m.group(1),
                "name": m.group(2),
                "value_type": "ArrayExpression",
                "line": i,
            })
            continue

        # Variable declarations with value
        m = re.match(r'(const|let|var)\s+(\w+)\s*=\s*(.+)', s)
        if m:
            val = m.group(3).rstrip(";").strip()
            val_type = "unknown"
            if val.startswith("'") or val.startswith('"') or val.startswith("`"):
                val_type = "StringLiteral"
            elif val.replace(".", "").replace("-", "").isdigit():
                val_type = "NumericLiteral"
            elif val in ("true", "false"):
                val_type = "BooleanLiteral"
            elif val == "null" or val == "undefined":
                val_type = "NullLiteral"
            elif "(" in val:
                val_type = "CallExpression"
            elif "." in val:
                val_type = "MemberExpression"
            nodes.append({
                "type": "VariableDeclaration",
                "kind": m.group(1),
                "name": m.group(2),
                "value_type": val_type,
                "value_preview": val[:60],
                "line": i,
            })
            continue

        # Return statements
        m = re.match(r'return\s+(.*)', s)
        if m:
            nodes.append({
                "type": "ReturnStatement",
                "value_preview": m.group(1)[:60].rstrip(";"),
                "line": i,
                "context": in_function or "module",
            })
            continue

        # Method calls: obj.method(...)
        m = re.match(r'(\w+)\.(\w+)\(', s)
        if m and not s.startswith("//"):
            nodes.append({
                "type": "CallExpression",
                "object": m.group(1),
                "method": m.group(2),
                "line": i,
            })
            continue

        # Standalone function calls
        m = re.match(r'(\w+)\(', s)
        if m and not s.startswith("//") and m.group(1) not in ("if", "for", "while", "switch", "catch"):
            nodes.append({
                "type": "CallExpression",
                "func": m.group(1),
                "line": i,
            })
            continue

        # Module exports
        m = re.match(r'module\.exports\s*=', s)
        if m:
            nodes.append({
                "type": "ModuleExports",
                "line": i,
            })
            continue

        # JSX return
        if s.startswith("return (") or s.startswith("return <"):
            nodes.append({
                "type": "JSXReturn",
                "line": i,
                "context": in_function or "module",
            })
            continue

    return {"nodes": nodes}


# ============================================================
#  HTML TREE VISUALIZATION
# ============================================================

def generate_html_tree(all_data):
    """Generate self-contained HTML visualization."""

    html_parts = []
    html_parts.append("""<!DOCTYPE html>
<html><head><meta charset="UTF-8"><title>PNOG Deep AST</title>
<style>
*{box-sizing:border-box;margin:0;padding:0}
body{background:#0a0a14;color:#c0c0d0;font-family:'Courier New',monospace;font-size:12px;padding:20px}
h1{font-family:Arial,sans-serif;font-size:20px;color:#7eb8f7;margin-bottom:4px}
h2{font-family:Arial,sans-serif;font-size:11px;color:#555;margin-bottom:20px;font-weight:normal}
.file-block{margin:0 0 8px;border:1px solid #1a1a2e;border-radius:8px;overflow:hidden}
.file-hdr{background:#12122a;padding:10px 14px;cursor:pointer;display:flex;align-items:center;gap:10px}
.file-hdr:hover{background:#1a1a3a}
.file-name{color:#4a90e2;font-weight:bold;font-size:13px}
.file-lang{font-size:9px;padding:2px 8px;border-radius:4px;font-weight:bold}
.lang-py{background:#1a2a4a;color:#7eb8f7}
.lang-js{background:#2a2a1a;color:#f0a500}
.file-count{margin-left:auto;color:#444;font-size:10px}
.arrow{color:#444;font-size:10px;transition:transform .2s}
.arrow.open{transform:rotate(90deg)}
.file-body{display:none;padding:8px 14px 14px;border-top:1px solid #1a1a2e}
.file-body.open{display:block}
.node{display:flex;gap:8px;padding:3px 0;align-items:flex-start}
.node-indent{color:#222;user-select:none;flex-shrink:0}
.node-type{font-size:10px;padding:1px 6px;border-radius:3px;font-weight:bold;flex-shrink:0;min-width:70px;text-align:center}
.t-Module{background:#1a1a3a;color:#7eb8f7}
.t-Import,.t-ImportFrom,.t-ImportDefault,.t-ImportSpecifier,.t-Require{background:#2a2000;color:#f0a500}
.t-FunctionDef,.t-AsyncFunctionDef,.t-FunctionDeclaration,.t-ArrowFunction,.t-ExportDefaultFunction{background:#1a0a2a;color:#b07ef7}
.t-ClassDef{background:#2a0a0a;color:#f76e6e}
.t-Assign,.t-VariableDeclaration,.t-AugAssign{background:#0a2a0a;color:#3ecf6e}
.t-Return,.t-ReturnStatement,.t-Yield{background:#2a0a2a;color:#e0a0e0}
.t-Call,.t-CallExpression{background:#0a2a2a;color:#4ecde4}
.t-If,.t-For,.t-While,.t-Try,.t-With{background:#2a2a0a;color:#c0c060}
.t-Raise{background:#2a1a0a;color:#f0a500}
.t-ReactHook{background:#0a2a1a;color:#3ecf6e}
.t-JSXReturn{background:#1a0a2a;color:#b07ef7}
.t-ModuleExports{background:#2a2a0a;color:#c0c060}
.t-Global,.t-Nonlocal{background:#1a1a2a;color:#a0a0c0}
.node-info{color:#888;word-break:break-all}
.node-info .name{color:#e0e0f0}
.node-info .val{color:#6a6}
.node-info .line{color:#444}
.node-info .decorator{color:#f0a500}
.node-info .arg{color:#80c0a0}
.body-nodes{padding-left:20px;border-left:1px solid #1a1a2e;margin:2px 0 2px 35px}
.stats{display:flex;gap:16px;margin:16px 0;flex-wrap:wrap}
.stat{background:#12122a;border:1px solid #1a1a2e;border-radius:8px;padding:10px 16px;min-width:100px}
.stat-n{font-size:20px;font-weight:bold;color:#7eb8f7}
.stat-l{font-size:10px;color:#555;margin-top:2px}
.legend{display:flex;gap:12px;flex-wrap:wrap;margin:12px 0 20px}
.legend-item{display:flex;align-items:center;gap:4px;font-size:10px;color:#666}
.legend-dot{width:10px;height:10px;border-radius:2px}
</style></head><body>
<h1>PNOG Deep AST Syntax Tree</h1>
<h2>Complete abstract syntax tree for all Python and JavaScript files</h2>
""")

    # Stats
    total_files = len(all_data)
    total_nodes = sum(len(d.get("summary", {}).get("nodes", [])) for d in all_data.values())
    type_counts = {}
    for d in all_data.values():
        for n in d.get("summary", {}).get("nodes", []):
            t = n.get("type", "?")
            type_counts[t] = type_counts.get(t, 0) + 1

    html_parts.append(f'<div class="stats">')
    html_parts.append(f'<div class="stat"><div class="stat-n">{total_files}</div><div class="stat-l">files</div></div>')
    html_parts.append(f'<div class="stat"><div class="stat-n">{total_nodes}</div><div class="stat-l">total nodes</div></div>')
    for t in ["ImportFrom", "FunctionDef", "ClassDef", "Assign", "Call"]:
        if t in type_counts:
            html_parts.append(f'<div class="stat"><div class="stat-n">{type_counts[t]}</div><div class="stat-l">{t}</div></div>')
    html_parts.append('</div>')

    # Legend
    html_parts.append('<div class="legend">')
    for label, cls in [("Import", "t-Import"), ("Function", "t-FunctionDef"), ("Class", "t-ClassDef"),
                       ("Variable", "t-Assign"), ("Call", "t-Call"), ("Return", "t-Return"),
                       ("Control", "t-If"), ("Hook", "t-ReactHook")]:
        html_parts.append(f'<div class="legend-item"><div class="legend-dot {cls}"></div>{label}</div>')
    html_parts.append('</div>')

    # File blocks
    idx = 0
    for filepath, data in sorted(all_data.items()):
        lang = data.get("language", "python")
        summary_nodes = data.get("summary", {}).get("nodes", [])
        lang_cls = "lang-py" if lang == "python" else "lang-js"
        lang_tag = "PY" if lang == "python" else "JS"
        fname = filepath.split("/")[-1]

        html_parts.append(f'<div class="file-block">')
        html_parts.append(f'<div class="file-hdr" onclick="toggle({idx})">')
        html_parts.append(f'<span class="arrow" id="arrow{idx}">&#9654;</span>')
        html_parts.append(f'<span class="file-lang {lang_cls}">{lang_tag}</span>')
        html_parts.append(f'<span class="file-name">{filepath}</span>')
        html_parts.append(f'<span class="file-count">{len(summary_nodes)} nodes</span>')
        html_parts.append(f'</div>')
        html_parts.append(f'<div class="file-body" id="body{idx}">')

        if not summary_nodes:
            html_parts.append('<div style="color:#444;padding:4px">empty module</div>')
        else:
            for n in summary_nodes:
                ntype = n.get("type", "?")
                depth = n.get("depth", 0)
                indent = "&nbsp;&nbsp;" * depth
                type_cls = f"t-{ntype}"

                info_parts = []

                # Name
                name = n.get("name", "")
                if name:
                    info_parts.append(f'<span class="name">{name}</span>')

                # Module (for imports)
                module = n.get("module", "")
                if module:
                    info_parts.append(f'from <span class="val">{module}</span>')

                # Alias
                alias = n.get("alias")
                if alias:
                    info_parts.append(f'as <span class="val">{alias}</span>')

                # Args
                args = n.get("args", [])
                if args and isinstance(args[0], dict):
                    arg_names = [a.get("name", "?") for a in args]
                    info_parts.append(f'(<span class="arg">{", ".join(arg_names)}</span>)')
                elif args and isinstance(args[0], str):
                    info_parts.append(f'(<span class="arg">{", ".join(str(a) for a in args[:5])}</span>)')

                # Bases (for classes)
                bases = n.get("bases", [])
                if bases:
                    info_parts.append(f'({", ".join(bases)})')

                # Decorators
                decs = n.get("decorators", [])
                for d in decs[:3]:
                    info_parts.append(f'<span class="decorator">{d[:50]}</span>')

                # Value
                vr = n.get("value_repr", "")
                if vr:
                    info_parts.append(f'= <span class="val">{vr[:60]}</span>')

                vp = n.get("value_preview", "")
                if vp:
                    info_parts.append(f'= <span class="val">{vp[:60]}</span>')

                # Func (for calls)
                func = n.get("func", "")
                if func and ntype in ("Call", "CallExpression"):
                    obj = n.get("object", "")
                    method = n.get("method", "")
                    if obj and method:
                        info_parts.append(f'<span class="name">{obj}.{method}</span>()')
                    else:
                        info_parts.append(f'<span class="name">{func}</span>()')

                # Source (JS imports)
                source = n.get("source", "")
                if source:
                    info_parts.append(f'from <span class="val">{source}</span>')

                # Hook info
                state = n.get("state", "")
                setter = n.get("setter", "")
                hook = n.get("hook", "")
                if hook:
                    info_parts.append(f'<span class="name">{hook}</span>')
                if state:
                    info_parts.append(f'[<span class="arg">{state}, {setter}</span>]')

                # Returns
                returns = n.get("returns")
                if returns:
                    info_parts.append(f'-> <span class="val">{returns[:40]}</span>')

                # Line
                line = n.get("line")
                if line:
                    info_parts.append(f'<span class="line">L{line}</span>')

                info_html = " ".join(info_parts)

                html_parts.append(f'<div class="node">')
                html_parts.append(f'<span class="node-indent">{indent}{"├─" if depth > 0 else "•"}</span>')
                html_parts.append(f'<span class="node-type {type_cls}">{ntype}</span>')
                html_parts.append(f'<span class="node-info">{info_html}</span>')
                html_parts.append(f'</div>')

                # Body nodes (for functions)
                body_nodes = n.get("body_nodes", [])
                if body_nodes:
                    html_parts.append(f'<div class="body-nodes">')
                    for bn in body_nodes[:20]:
                        bn_type = bn.get("type", "?")
                        bn_cls = f"t-{bn_type}"
                        bn_info = ""
                        if bn.get("func"):
                            bn_info = f'<span class="name">{bn["func"]}</span>()'
                        elif bn.get("targets"):
                            bn_info = f'<span class="name">{", ".join(bn["targets"])}</span> = {bn.get("value_type", "")}'
                        elif bn.get("value"):
                            bn_info = f'<span class="val">{str(bn["value"])[:50]}</span>'
                        bn_line = f' <span class="line">L{bn["line"]}</span>' if bn.get("line") else ""
                        html_parts.append(f'<div class="node"><span class="node-indent">&nbsp;&nbsp;·</span>')
                        html_parts.append(f'<span class="node-type {bn_cls}">{bn_type}</span>')
                        html_parts.append(f'<span class="node-info">{bn_info}{bn_line}</span></div>')
                    if len(body_nodes) > 20:
                        html_parts.append(f'<div class="node" style="color:#444">&nbsp;&nbsp;... +{len(body_nodes)-20} more</div>')
                    html_parts.append(f'</div>')

                # Fields and methods (for classes)
                fields = n.get("fields", [])
                methods = n.get("methods", [])
                if fields or methods:
                    html_parts.append(f'<div class="body-nodes">')
                    for field in fields:
                        html_parts.append(f'<div class="node"><span class="node-indent">&nbsp;&nbsp;·</span>')
                        html_parts.append(f'<span class="node-type t-Assign">Field</span>')
                        html_parts.append(f'<span class="node-info"><span class="name">{field["name"]}</span> = {field.get("value_type","")} <span class="line">L{field["line"]}</span></span></div>')
                    for method in methods:
                        prefix = "async " if method.get("is_async") else ""
                        args = ", ".join(method.get("args", [])[:4])
                        html_parts.append(f'<div class="node"><span class="node-indent">&nbsp;&nbsp;·</span>')
                        html_parts.append(f'<span class="node-type t-FunctionDef">Method</span>')
                        html_parts.append(f'<span class="node-info"><span class="name">{prefix}{method["name"]}</span>(<span class="arg">{args}</span>) <span class="line">L{method["line"]}</span></span></div>')
                    html_parts.append(f'</div>')

        html_parts.append(f'</div></div>')
        idx += 1

    html_parts.append("""
<script>
function toggle(i){
  var b=document.getElementById('body'+i);
  var a=document.getElementById('arrow'+i);
  if(b.classList.contains('open')){b.classList.remove('open');a.classList.remove('open')}
  else{b.classList.add('open');a.classList.add('open')}
}
// Open first file by default
if(document.getElementById('body0'))toggle(0);
</script>
</body></html>""")

    return "\n".join(html_parts)


# ============================================================
#  MAIN
# ============================================================

def main():
    print("=" * 62)
    print("  PNOG Deep AST Generator v2")
    print("  Extracts ALL AST nodes from Python & JavaScript files")
    print("=" * 62)

    cwd = os.getcwd()
    print(f"\n  Working directory: {cwd}")

    found = [d for d in SCAN_DIRS if os.path.isdir(d)]
    if not found:
        print(f"\n  ERROR: Cannot find backend/ or frontend/ folders!")
        print(f"  Run from inside the service/ folder:")
        print(f"    cd service")
        print(f"    python pnog_deep_ast.py")
        sys.exit(1)

    all_data = {}
    total_ast_nodes = 0

    for scan_dir in SCAN_DIRS:
        if not os.path.isdir(scan_dir):
            continue
        for root, dirs, files in os.walk(scan_dir):
            dirs[:] = sorted([d for d in dirs if d not in SKIP_DIRS])
            for fname in sorted(files):
                ext = Path(fname).suffix.lower()
                if ext not in PYTHON_EXTS and ext not in JS_EXTS:
                    continue

                filepath = os.path.join(root, fname).replace("\\", "/")
                lang = "python" if ext in PYTHON_EXTS else "javascript"

                # Deep AST
                if lang == "python":
                    deep = parse_python_deep(filepath)
                    summary = extract_python_summary(filepath)
                else:
                    deep = None
                    summary = parse_javascript_deep(filepath)

                n_nodes = len(summary.get("nodes", []))
                total_ast_nodes += n_nodes
                print(f"    {filepath:<50} {n_nodes:>3} nodes")

                all_data[filepath] = {
                    "language": lang,
                    "full_ast": deep,
                    "summary": summary,
                }

    # Save full deep AST JSON
    deep_json = "pnog_deep_ast.json"
    deep_out = {}
    for fp, data in all_data.items():
        deep_out[fp] = {
            "language": data["language"],
            "full_ast": data["full_ast"],
        }
    with open(deep_json, "w", encoding="utf-8") as f:
        json.dump(deep_out, f, indent=2, default=str)
    print(f"\n  Full AST JSON: {deep_json}")

    # Save summary JSON
    summary_json = "pnog_deep_ast_summary.json"
    summary_out = {}
    for fp, data in all_data.items():
        summary_out[fp] = {
            "language": data["language"],
            "nodes": data["summary"].get("nodes", []),
        }
    with open(summary_json, "w", encoding="utf-8") as f:
        json.dump(summary_out, f, indent=2, default=str)
    print(f"  Summary JSON:  {summary_json}")

    # Generate HTML visualization
    html_file = "pnog_deep_ast.html"
    html_content = generate_html_tree(all_data)
    with open(html_file, "w", encoding="utf-8") as f:
        f.write(html_content)
    print(f"  HTML visual:   {html_file}")

    # Stats
    type_counts = {}
    for d in all_data.values():
        for n in d.get("summary", {}).get("nodes", []):
            t = n.get("type", "?")
            type_counts[t] = type_counts.get(t, 0) + 1

    print(f"\n{'='*62}")
    print(f"  COMPLETE!")
    print(f"{'='*62}")
    print(f"  Files:          {len(all_data)}")
    print(f"  Total nodes:    {total_ast_nodes}")
    print(f"  Node types:")
    for t, c in sorted(type_counts.items(), key=lambda x: -x[1]):
        print(f"    {t:<30} {c:>4}")
    print(f"{'='*62}")
    print(f"  How to view:")
    print(f"    Open {html_file} in browser (double-click)")
    print(f"    Or open {deep_json} for full raw AST data")
    print(f"{'='*62}\n")


if __name__ == "__main__":
    main()
