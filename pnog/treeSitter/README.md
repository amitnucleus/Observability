# treeSitter AST

This folder contains scripts and generated artifacts for building syntax trees (ASTs) using `tree-sitter`.

Generated output:
- Per-source AST JSON files under `ast/by_file/`
- A consolidated AST JSON under `ast/consolidated.json`
- A parse manifest under `ast/manifest.json`

## Generate ASTs

1. Ensure the `app` branch is checked out (or otherwise ensure the `app` branch source code is present).
2. Install dependencies in a local venv:

   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   pip install tree-sitter tree-sitter-languages
   ```

3. Run:

   ```bash
   python pnog/treeSitter/generate_ast.py --source-root . --output-dir pnog/treeSitter/ast
   ```

Notes:
- Only files with `.py`, `.js`, `.jsx`, `.ts`, `.tsx` are parsed.
- Some files may be skipped if the corresponding tree-sitter language grammar is unavailable.
