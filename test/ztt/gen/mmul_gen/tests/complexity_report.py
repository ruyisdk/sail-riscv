#!/usr/bin/env python3
#
# Copyright (c) Qualcomm Technologies, Inc. and/or its subsidiaries.
# SPDX-License-Identifier: BSD-3-Clause-Clear
#
"""Measure where the generator's complexity actually is.

This is a report, not a test: it prints the longest modules, the longest
functions, and the deepest real nesting so that each refactoring round starts
from evidence instead of a hunch.

Two measurement choices matter, because getting them wrong flatters the result:

* an ``elif`` chain is *not* nesting -- only a branch nested inside another
  branch is -- so a flattened ``if/elif/else`` dispatch reads as depth 1;
* comment-only and blank lines are excluded from the module length, because the
  framework's docstrings deliberately carry the design rationale.

Usage::

    python3 -m mmul_gen.tests.complexity_report [--top N] [--path DIR]
"""

from __future__ import annotations

import argparse
import ast
from pathlib import Path

BRANCHES = (ast.If, ast.For, ast.While, ast.Try, ast.Match, ast.With)

DEFAULT_ROOT = Path(__file__).resolve().parent.parent


def real_nesting(node: ast.AST, depth: int = 0) -> int:
    """The deepest branch actually nested inside ``node``, counting from 0.

    An ``If`` that is the sole statement of another ``If``'s ``else`` is an
    ``elif``: it continues the same dispatch and does not add depth.
    """

    deepest = depth
    for child in ast.iter_child_nodes(node):
        if isinstance(child, ast.If) and isinstance(node, ast.If) and child in node.orelse:
            extra = 0
        elif isinstance(child, BRANCHES):
            extra = 1
        else:
            extra = 0
        deepest = max(deepest, real_nesting(child, depth + extra))
    return deepest


def code_lines(path: Path) -> int:
    """Lines that carry code, ignoring blanks and comment-only lines."""

    return sum(
        1
        for line in path.read_text().splitlines()
        if line.strip() and not line.strip().startswith("#")
    )


def collect(root: Path) -> tuple[list[tuple[int, str]], list[tuple[int, int, str, str]]]:
    """The modules and the functions of ``root``, as (size, ...) tuples."""

    modules: list[tuple[int, str]] = []
    functions: list[tuple[int, int, str, str]] = []
    for path in sorted(root.rglob("*.py")):
        if "__pycache__" in str(path):
            continue
        modules.append((code_lines(path), str(path)))
        for node in ast.walk(ast.parse(path.read_text())):
            if isinstance(node, ast.FunctionDef):
                functions.append(
                    (
                        node.end_lineno - node.lineno + 1,
                        max(0, real_nesting(node) - 1),
                        node.name,
                        str(path),
                    )
                )
    return modules, functions


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--top", type=int, default=12, help="rows per table")
    parser.add_argument("--path", type=Path, default=DEFAULT_ROOT, help="tree to measure")
    args = parser.parse_args()

    modules, functions = collect(args.path)
    print(f"=== modules by code lines (top {args.top}) ===")
    for size, name in sorted(modules, reverse=True)[: args.top]:
        print(f"  {size:4d} code lines  {name}")
    print(f"  {len(modules)} modules, {sum(s for s, _ in modules)} code lines in total")

    production = [f for f in functions if "/tests/" not in f[3]]
    print(f"\n=== production functions by lines (top {args.top}) ===")
    for length, depth, name, path in sorted(production, reverse=True)[: args.top]:
        print(f"  {length:4d} lines, real nesting {depth}  {name}  ({path})")
    print(f"  {len(production)} production functions, "
          f"{len(functions) - len(production)} test functions")
    deep = [f for f in production if f[1] >= 3]
    print(f"  production functions with real nesting >= 3: {len(deep)}")
    for length, depth, name, path in sorted(deep, reverse=True)[:5]:
        print(f"      nesting {depth}, {length} lines  {name}  ({path})")


if __name__ == "__main__":
    main()
