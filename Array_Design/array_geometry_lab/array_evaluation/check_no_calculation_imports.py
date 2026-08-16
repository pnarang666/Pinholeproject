"""
Mechanical enforcement of this layer's own contract (see README.md): array_evaluation/
must never import a generator or physics-propagation routine from array_calculation/.
Statically scans every .py file under array_evaluation/ (via the `ast` module, not a
naive text grep) for `import X` / `from X import ...` statements naming a module that
lives in array_calculation/ -- imports in this project are flat (sys.path-based, no
packages), so matching is by bare module name.

Exit code 0 = clean. Exit code 1 = at least one forbidden import found (printed with
file and line number).

Run:  python3 check_no_calculation_imports.py
"""
import ast
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))  # array_evaluation/
LAB_ROOT = os.path.dirname(HERE)  # array_geometry_lab/
CALC_ROOT = os.path.join(LAB_ROOT, "array_calculation")

# Every module name array_calculation/ exposes via a flat sys.path insert, gathered
# directly from its own subfolders (not hand-maintained separately from the real
# files, so this list can't silently drift out of date).
FORBIDDEN_MODULES = set()
for sub in ("generators", "engine", "margins"):
    subdir = os.path.join(CALC_ROOT, sub)
    if os.path.isdir(subdir):
        for fname in os.listdir(subdir):
            if fname.endswith(".py"):
                FORBIDDEN_MODULES.add(fname[:-3])
for fname in os.listdir(CALC_ROOT):
    if fname.endswith(".py") and os.path.isfile(os.path.join(CALC_ROOT, fname)):
        FORBIDDEN_MODULES.add(fname[:-3])


def find_violations(py_path):
    with open(py_path) as f:
        tree = ast.parse(f.read(), filename=py_path)
    violations = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                top = alias.name.split(".")[0]
                if top in FORBIDDEN_MODULES:
                    violations.append((node.lineno, f"import {alias.name}"))
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                top = node.module.split(".")[0]
                if top in FORBIDDEN_MODULES:
                    violations.append((node.lineno, f"from {node.module} import ..."))
    return violations


def main():
    all_violations = []
    for root, _dirs, files in os.walk(HERE):
        for fname in files:
            if not fname.endswith(".py"):
                continue
            path = os.path.join(root, fname)
            if os.path.abspath(path) == os.path.abspath(__file__):
                continue  # this checker itself references FORBIDDEN_MODULES by name,
                          # not by importing them -- not a violation
            for lineno, stmt in find_violations(path):
                all_violations.append((os.path.relpath(path, HERE), lineno, stmt))

    if all_violations:
        print(f"*** {len(all_violations)} forbidden array_calculation/ import(s) found in "
              f"array_evaluation/ -- layer 2 must never import a generator or propagation "
              f"routine from layer 1 (see README.md). ***")
        for path, lineno, stmt in all_violations:
            print(f"  {path}:{lineno}: {stmt}")
        sys.exit(1)
    print(f"OK: no array_calculation/ imports found under array_evaluation/ "
          f"({len(FORBIDDEN_MODULES)} forbidden module names checked).")


if __name__ == "__main__":
    main()
