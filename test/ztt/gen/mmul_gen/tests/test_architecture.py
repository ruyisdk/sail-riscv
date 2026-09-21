#!/usr/bin/env python3
#
# Copyright (c) Qualcomm Technologies, Inc. and/or its subsidiaries.
# SPDX-License-Identifier: BSD-3-Clause-Clear
#
"""The architecture every instruction follows, checked mechanically.

Two rules, both of them consequences of "the class holds identity and formulas,
the template call holds the parameters":

* no template reads a family declaration back off the instruction it renders -- a
  template may use the framework identity (``name``, ``subject``, ...) and the
  elementwise family's own ``form``, and nothing else;
* an instruction class declares no member that exists to be read back: identity,
  the framework vocabulary, its formulas, and the ``templates`` tuple.

Both rules are about *what a name is for*, so both are checked structurally
rather than by eyeballing: the first over the syntax tree of every template
module, the second over the class dictionaries of the whole catalog.
"""

from __future__ import annotations

import ast
import unittest
from pathlib import Path

from mmul_gen.catalog import ALL_INSTRUCTIONS
from mmul_gen.tests.helpers import GEN_ROOT

#: What a template may read off the instruction it is rendering.
FRAMEWORK_ATTRIBUTES = frozenset(
    {
        "acquires_backend",
        "always_emits_data",
        "banner",
        "data_footer",
        "datatype_domains",
        "file_name",
        "name",
        "operands",
        "subject",
        "summary",
        "supported_dtypes",
        "template_names",
        "templates",
        "title",
    }
)

#: The elementwise family states its operand shape as a class member and its
#: templates read it, exactly as the reference instruction ``madd_ew.py`` does.
FAMILY_ATTRIBUTES = {"elementwise": frozenset({"form"})}

#: What an instruction class may declare: the framework vocabulary plus the
#: formulas it owns plus the family vocabulary its own templates read.  Everything
#: else -- a product shape, a stimulus, an operand shape -- is an argument of its
#: templates.  ``summary_zh`` and ``manual_zh`` are the design document's prose
#: fields: templates never read them, so they are not part of
#: :data:`FRAMEWORK_ATTRIBUTES`.
FRAMEWORK_MEMBERS = (
    FRAMEWORK_ATTRIBUTES
    | {"evaluate", "evaluate_float", "manual_zh", "summary_zh"}
    | set().union(*FAMILY_ATTRIBUTES.values())
)


def template_modules() -> tuple[Path, ...]:
    """Every template module except the shared base and the package index."""

    return tuple(
        path
        for path in sorted((GEN_ROOT / "mmul_gen" / "templates").glob("*.py"))
        if path.name not in {"base.py", "__init__.py"}
    )


def family_of(module: Path) -> str:
    """The family a template module belongs to, from its own name."""

    return module.stem.split("_", 1)[0]


def instruction_reads(module: Path) -> set[str]:
    """Every attribute a module reads off a parameter named ``instruction``.

    A ``getattr(instruction, "x")`` counts too: it is the same read with the name
    hidden from a reader, which is exactly what this test is here to prevent.
    """

    reads: set[str] = set()
    for node in ast.walk(ast.parse(module.read_text())):
        if (
            isinstance(node, ast.Attribute)
            and isinstance(node.value, ast.Name)
            and node.value.id == "instruction"
        ):
            reads.add(node.attr)
        if (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Name)
            and node.func.id == "getattr"
            and node.args
            and isinstance(node.args[0], ast.Name)
            and node.args[0].id == "instruction"
        ):
            for argument in node.args[1:]:
                if isinstance(argument, ast.Constant) and isinstance(argument.value, str):
                    reads.add(argument.value)
    return reads


class TemplateReadsNoFamilyDeclarationTest(unittest.TestCase):
    def test_every_read_off_the_instruction_is_framework_identity(self) -> None:
        for module in template_modules():
            allowed = FRAMEWORK_ATTRIBUTES | FAMILY_ATTRIBUTES.get(family_of(module), frozenset())
            with self.subTest(module=module.name):
                self.assertEqual(instruction_reads(module) - allowed, set())

    def test_no_template_hides_a_read_behind_getattr(self) -> None:
        for module in template_modules():
            source = module.read_text()
            with self.subTest(module=module.name):
                self.assertNotIn("getattr(instruction", source)


class InstructionClassShapeTest(unittest.TestCase):
    #: Class members that are Python's own record-keeping rather than the class's.
    PYTHON_MEMBERS = frozenset(
        {"__dict__", "__doc__", "__module__", "__orig_bases__", "__parameters__", "__qualname__", "__weakref__"}
    )

    def test_an_instruction_class_declares_identity_formulas_and_templates(self) -> None:
        for instruction in ALL_INSTRUCTIONS:
            declared = {
                name
                for name, value in vars(type(instruction)).items()
                if name not in self.PYTHON_MEMBERS
                and name not in FRAMEWORK_MEMBERS
                and not callable(value)
                and not isinstance(value, property)
            }
            with self.subTest(instruction=instruction.name):
                self.assertEqual(declared, set())

    def test_a_constructed_template_is_not_shared_between_instructions(self) -> None:
        """The class is shared; the object carries one instruction's inputs."""

        from mmul_gen.templates import TEMPLATE_CLASSES

        holders: dict[int, set[str]] = {}
        for instruction in ALL_INSTRUCTIONS:
            for template in instruction.templates:
                if type(template) in TEMPLATE_CLASSES:
                    holders.setdefault(id(template), set()).add(instruction.name)
        shared = {name for names in holders.values() if len(names) > 1 for name in names}
        self.assertEqual(shared, set())


if __name__ == "__main__":
    unittest.main()
