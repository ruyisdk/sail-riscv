#!/usr/bin/env python3
#
# Copyright (c) Qualcomm Technologies, Inc. and/or its subsidiaries.
# SPDX-License-Identifier: BSD-3-Clause-Clear
#
"""The instruction inventory is explicit, ordered, and self-describing."""

from __future__ import annotations

import unittest

from mmul_gen.catalog import (
    ALL_INSTRUCTIONS,
    BACKEND_INSTRUCTIONS,
    MATRIX_MULTIPLY_INSTRUCTIONS,
    TYPE_REGISTER_INSTRUCTIONS,
    describe_instructions,
    find_instruction,
    generate_all,
    select_instructions,
)
from mmul_gen.instruction import Operand
from mmul_gen.instructions.mmul.base import MatrixMultiplyInstruction
from mmul_gen.tests.helpers import machine


EXPECTED_MNEMONICS = (
    "mmulacc.2d",
    "mmulaccneg.2d",
    "mmulatacc.2d",
    "mmulataccneg.2d",
    "mmulbtacc.2d",
    "mmulbtaccneg.2d",
)

EXPECTED_TYPE_REGISTER_MNEMONICS = ("msettyp", "mgettyp", "asettyp", "agettyp")

EXPECTED_BACKEND_MNEMONICS = ("ame.acquire", "ame.release")


class OperandDeclarationTests(unittest.TestCase):
    """Operand declarations are tuples, however many operands there are."""

    def test_every_instruction_declares_a_tuple_of_operands(self) -> None:
        for instruction in ALL_INSTRUCTIONS:
            with self.subTest(instruction=instruction.name):
                # A single operand written as ``(OPERAND)`` is the operand
                # itself, not a one-tuple, and every consumer that iterates the
                # declaration then fails on it.
                self.assertIsInstance(
                    instruction.operands,
                    tuple,
                    f"{instruction.name} must declare operands as a tuple; "
                    "a single operand needs a trailing comma",
                )
                for operand in instruction.operands:
                    self.assertIsInstance(operand, Operand)


class CatalogTests(unittest.TestCase):
    def test_inventory_is_the_six_architectural_2d_products_in_order(self) -> None:
        self.assertEqual(
            tuple(instruction.name for instruction in MATRIX_MULTIPLY_INSTRUCTIONS),
            EXPECTED_MNEMONICS,
        )

    def test_every_instruction_declares_name_summary_operands_and_templates(self) -> None:
        for instruction in MATRIX_MULTIPLY_INSTRUCTIONS:
            with self.subTest(instruction=instruction.name):
                self.assertTrue(instruction.summary)
                self.assertEqual(
                    [operand.role for operand in instruction.operands],
                    ["acc", "ms1", "ms2"],
                )
                self.assertTrue(instruction.templates)
                self.assertEqual(
                    len(instruction.template_names), len(set(instruction.template_names))
                )

    def test_file_names_normalise_dotted_mnemonics(self) -> None:
        for instruction in MATRIX_MULTIPLY_INSTRUCTIONS:
            with self.subTest(instruction=instruction.name):
                self.assertEqual(
                    instruction.file_name, instruction.name.replace(".", "_") + ".S"
                )

    def test_generation_order_matches_inventory_order(self) -> None:
        sources = generate_all(machine())
        self.assertEqual(
            [source.name for source in sources],
            [instruction.file_name for instruction in ALL_INSTRUCTIONS],
        )

    def test_backend_inventory_is_the_two_ownership_instructions(self) -> None:
        self.assertEqual(
            tuple(instruction.name for instruction in BACKEND_INSTRUCTIONS),
            EXPECTED_BACKEND_MNEMONICS,
        )
        # ``ame.release`` takes no operands, which is a declaration, not a gap.
        self.assertEqual(BACKEND_INSTRUCTIONS[1].operands, ())

    def test_every_family_is_reachable_and_ordered(self) -> None:
        self.assertEqual(
            tuple(instruction.name for instruction in TYPE_REGISTER_INSTRUCTIONS),
            EXPECTED_TYPE_REGISTER_MNEMONICS,
        )
        self.assertEqual(
            [instruction.name for instruction in select_instructions([])],
            [instruction.name for instruction in ALL_INSTRUCTIONS],
        )
        self.assertEqual(
            [instruction.name for instruction in select_instructions(["type_register"])],
            list(EXPECTED_TYPE_REGISTER_MNEMONICS),
        )
        with self.assertRaisesRegex(KeyError, "unknown instruction family"):
            select_instructions(["no_such_family"])

    def test_find_instruction_reports_the_known_mnemonics_on_a_typo(self) -> None:
        self.assertEqual(find_instruction("mmulacc.2d").name, "mmulacc.2d")
        with self.assertRaisesRegex(KeyError, "mmulacc.2d"):
            find_instruction("mmulacc.3d")

    def test_describe_instructions_carries_datatype_coverage(self) -> None:
        described = describe_instructions(machine(uds=8))
        self.assertEqual(
            [entry["name"] for entry in described],
            [instruction.name for instruction in ALL_INSTRUCTIONS],
        )
        for instruction, entry in zip(ALL_INSTRUCTIONS, described):
            with self.subTest(instruction=instruction.name):
                self.assertTrue(entry["templates"])
                # An instruction either covers datatypes or is dtype-free.
                self.assertEqual(
                    bool(entry["dtypes"]), bool(entry["datatype_domains"])
                )
                self.assertEqual(
                    entry["operands"],
                    [
                        f"{operand.role}:{operand.register_class}"
                        for operand in instruction.operands
                    ],
                )

    def test_describe_instructions_can_be_restricted_to_a_family(self) -> None:
        described = describe_instructions(machine(), TYPE_REGISTER_INSTRUCTIONS)
        self.assertEqual(
            [entry["name"] for entry in described],
            list(EXPECTED_TYPE_REGISTER_MNEMONICS),
        )

    def test_datatype_domains_are_derived_from_the_templates_in_order(self) -> None:
        for instruction in MATRIX_MULTIPLY_INSTRUCTIONS:
            with self.subTest(instruction=instruction.name):
                self.assertEqual(
                    list(instruction.datatype_domains),
                    list(dict.fromkeys(t.dtypes for t in instruction.templates)),
                )

    def test_only_mmulacc_2d_covers_the_accumulator_span_templates(self) -> None:
        accumulator_only = {"multi_acc_independent", "ones_uniform", "ones_uniform_128"}
        for instruction in MATRIX_MULTIPLY_INSTRUCTIONS:
            with self.subTest(instruction=instruction.name):
                covered = accumulator_only & set(instruction.template_names)
                if instruction.name == "mmulacc.2d":
                    self.assertEqual(covered, accumulator_only)
                else:
                    self.assertFalse(covered)
                self.assertEqual(
                    "integer128" in [domain.name for domain in instruction.datatype_domains],
                    instruction.name == "mmulacc.2d",
                )

    def test_a_subclass_without_metadata_fails_at_class_creation(self) -> None:
        with self.assertRaisesRegex(TypeError, "must declare 'name'"):

            class Incomplete(MatrixMultiplyInstruction):
                summary = "missing a name"


if __name__ == "__main__":
    unittest.main()
