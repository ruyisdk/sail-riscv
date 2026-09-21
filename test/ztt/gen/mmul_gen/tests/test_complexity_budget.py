#!/usr/bin/env python3
#
# Copyright (c) Qualcomm Technologies, Inc. and/or its subsidiaries.
# SPDX-License-Identifier: BSD-3-Clause-Clear
#
"""Keep the generator's complexity budget from drifting back up.

The budget is the measurable half of "one file, one thing": a module states one
behaviour, a function stays readable, control flow stays flat, and a shared
module never branches on a particular instruction's name.  Each limit sits just
above what the framework needs today, so passing it means someone added a
responsibility rather than a case.

Run ``python3 -m mmul_gen.tests.complexity_report`` to see where the current
numbers are before raising a limit.
"""

from __future__ import annotations

import ast
import unittest
from pathlib import Path

from mmul_gen.tests.complexity_report import collect, real_nesting

#: Longest module the framework may carry, in code lines.
MODULE_CODE_LINES = 520
#: Longest production function, in lines.  Data tables may sit near this.
FUNCTION_LINES = 140
#: Deepest real nesting a production function may have.  An ``elif`` chain is a
#: flat dispatch, not nesting.
FUNCTION_NESTING = 3

ROOT = Path(__file__).resolve().parent.parent


class ComplexityBudgetTest(unittest.TestCase):
    """The framework's module, function and nesting budgets."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.modules, cls.functions = collect(ROOT)
        cls.production = [f for f in cls.functions if "/tests/" not in f[3]]

    def test_no_module_exceeds_the_code_line_budget(self) -> None:
        over = [(size, name) for size, name in self.modules if size > MODULE_CODE_LINES]
        self.assertEqual(
            [],
            over,
            f"modules over {MODULE_CODE_LINES} code lines: "
            f"{[(name, size) for size, name in over]}",
        )

    def test_no_production_function_exceeds_the_length_budget(self) -> None:
        over = [f for f in self.production if f[0] > FUNCTION_LINES]
        self.assertEqual(
            [],
            over,
            f"production functions over {FUNCTION_LINES} lines: "
            f"{[(name, length, path) for length, _, name, path in over]}",
        )

    def test_no_production_function_nests_deeper_than_the_budget(self) -> None:
        over = [f for f in self.production if f[1] > FUNCTION_NESTING]
        self.assertEqual(
            [],
            over,
            f"production functions nested deeper than {FUNCTION_NESTING}: "
            f"{[(name, depth, path) for _, depth, name, path in over]}",
        )

    def test_shared_modules_do_not_branch_on_an_instruction_name(self) -> None:
        """A template that matches a mnemonic has an undeclared contract.

        An instruction states what it is in its own module; a shared template
        reads those declarations.  Comparing ``instruction.name`` against a
        string, or prefix-matching it, means some behaviour never got declared --
        see ``mcmpge``'s special-value comparison, which declares
        ``FloatSpecialRole.COMPARE_TRUE`` rather than being recognised by its
        mnemonic prefix.
        """

        offenders = []
        for path in sorted((ROOT / "templates").rglob("*.py")):
            if "__pycache__" in str(path):
                continue
            for node in ast.walk(ast.parse(path.read_text())):
                operand_names = []
                if isinstance(node, ast.Compare):
                    operand_names = [node.left, *node.comparators]
                elif (
                    isinstance(node, ast.Call)
                    and isinstance(node.func, ast.Attribute)
                    and node.func.attr in ("startswith", "endswith", "find")
                ):
                    operand_names = [node.func.value]
                for operand in operand_names:
                    if self._is_instruction_name(operand):
                        offenders.append((str(path), node.lineno, ast.unparse(node)))
        self.assertEqual([], offenders, f"templates matching a mnemonic: {offenders}")

    @staticmethod
    def _is_instruction_name(node: ast.AST) -> bool:
        """Whether ``node`` reads the name of the instruction being generated."""

        if isinstance(node, ast.Name):
            return node.id in ("mnemonic", "instruction_name")
        if isinstance(node, ast.Attribute):
            return node.attr == "name" and isinstance(node.value, ast.Name) and (
                node.value.id in ("instruction", "self")
            )
        return False

    def test_the_report_and_the_budget_agree_on_nesting(self) -> None:
        """Guard the measurement itself: an ``elif`` chain is one flat dispatch."""

        source = (
            "def f(x):\n"
            "    if x:\n"
            "        return 1\n"
            "    elif x == 2:\n"
            "        return 2\n"
            "    return 0\n"
        )
        function = ast.parse(source).body[0]
        # ``real_nesting`` counts the function body itself, so a single flat
        # dispatch reads as depth 1 and a nested branch would read as 2.
        self.assertEqual(1, real_nesting(function))

        nested = ast.parse(
            "def g(x):\n"
            "    if x:\n"
            "        for y in x:\n"
            "            return y\n"
            "    return 0\n"
        ).body[0]
        self.assertEqual(2, real_nesting(nested))


if __name__ == "__main__":
    unittest.main()
