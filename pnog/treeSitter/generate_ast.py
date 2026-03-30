import argparse
import json
import os
from pathlib import Path
from typing import Optional


LANG_EXT_MAP = {
    ".py": "python",
    ".js": "javascript",
    ".jsx": "javascript",
    ".ts": "typescript",
    ".tsx": "tsx",
}


DEFAULT_EXTENSIONS = sorted(LANG_EXT_MAP.keys())


def safe_relpath_to_filename(rel_path: Path) -> str:
    # Convert "a/b/c.py" to "a__b__c.py"
    return rel_path.as_posix().replace("/", "__")


def node_to_dict(node, *, max_children: Optional[int] = None) -> dict:
    # Convert a tree-sitter Node to a JSON-friendly recursive structure.
    # Using named_children keeps the tree more semantic and avoids punctuation noise.
    d = {
        "type": node.type,
        "start_point": list(node.start_point),
        "end_point": list(node.end_point),
    }

    children = list(getattr(node, "named_children", []))
    if max_children is not None:
        children = children[:max_children]
    if children:
        d["children"] = [node_to_dict(c, max_children=max_children) for c in children]
    else:
        d["children"] = []
    return d


def load_language(lang_name: str):
    # tree_sitter_languages is imported lazily so this file can exist without deps.
    from tree_sitter_languages import get_language  # type: ignore

    return get_language(lang_name)


def build_parser_for_extension(ext: str):
    from tree_sitter import Parser  # type: ignore

    lang_name = LANG_EXT_MAP.get(ext)
    if not lang_name:
        return None

    parser = Parser()
    parser.set_language(load_language(lang_name))
    return parser


def should_skip(path: Path, source_root: Path, output_root: Path) -> bool:
    # Avoid parsing the output we are generating.
    try:
        rel = path.relative_to(source_root)
    except Exception:
        return True

    rel_posix = rel.as_posix()
    if rel_posix.startswith(".git/"):
        return True
    if "node_modules/" in rel_posix:
        return True
    if rel_posix.startswith("pnog/treeSitter/ast/"):
        return True
    if rel_posix.startswith(".venv/"):
        return True
    if rel_posix.startswith("__pycache__/"):
        return True
    if rel_posix.endswith(".lock"):
        return True
    return False


def iter_source_files(source_root: Path, extensions: list[str]):
    for path in source_root.rglob("*"):
        if not path.is_file():
            continue
        if should_skip(path, source_root, source_root / "pnog" / "treeSitter" / "ast"):
            continue
        if path.suffix.lower() not in extensions:
            continue
        yield path


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-root", default=".")
    parser.add_argument("--output-dir", default="pnog/treeSitter/ast")
    parser.add_argument("--per-file-subdir", default="by_file")
    parser.add_argument("--consolidated-filename", default="consolidated.json")
    parser.add_argument("--max-children", type=int, default=4000)
    args = parser.parse_args()

    source_root = Path(args.source_root).resolve()
    output_dir = Path(args.output_dir).resolve()
    per_file_dir = output_dir / args.per_file_subdir
    per_file_dir.mkdir(parents=True, exist_ok=True)
    output_dir.mkdir(parents=True, exist_ok=True)

    extensions = [e.lower() for e in DEFAULT_EXTENSIONS]
    ast_by_file = {}
    manifest = []

    files = sorted(iter_source_files(source_root, extensions), key=lambda p: str(p))
    for i, path in enumerate(files):
        rel_path = path.relative_to(source_root)
        ext = path.suffix.lower()
        lang = LANG_EXT_MAP.get(ext, None)

        out_name = safe_relpath_to_filename(rel_path) + ".json"
        out_path = per_file_dir / out_name

        try:
            parser_obj = build_parser_for_extension(ext)
            if parser_obj is None:
                manifest.append(
                    {
                        "path": rel_path.as_posix(),
                        "status": "skipped_no_parser",
                        "language": lang,
                    }
                )
                continue

            content = path.read_bytes()
            tree = parser_obj.parse(content)
            root_node = tree.root_node

            ast = node_to_dict(root_node, max_children=args.max_children)
            ast_record = {
                "path": rel_path.as_posix(),
                "language": lang,
                "ast_root": ast,
            }

            out_path.write_text(json.dumps(ast_record, indent=2), encoding="utf-8")
            ast_by_file[rel_path.as_posix()] = ast_record
            manifest.append(
                {
                    "path": rel_path.as_posix(),
                    "status": "ok",
                    "language": lang,
                    "ast_file": out_path.relative_to(output_dir).as_posix(),
                }
            )
        except Exception as e:
            manifest.append(
                {
                    "path": rel_path.as_posix(),
                    "status": "error",
                    "language": lang,
                    "error": str(e),
                }
            )

        if (i + 1) % 25 == 0:
            print(f"Parsed {i+1}/{len(files)} files...")

    manifest_path = output_dir / "manifest.json"
    manifest_path.write_text(json.dumps({"generated_from": source_root.as_posix(), "files": manifest}, indent=2), encoding="utf-8")

    consolidated_path = output_dir / args.consolidated_filename
    consolidated_path.write_text(json.dumps({"generated_from": source_root.as_posix(), "ast_by_file": ast_by_file}, indent=2), encoding="utf-8")

    print(f"AST generation complete. Output: {output_dir.as_posix()}")


if __name__ == "__main__":
    main()

