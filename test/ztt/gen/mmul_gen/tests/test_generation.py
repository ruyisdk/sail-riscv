#!/usr/bin/env python3
#
# Copyright (c) Qualcomm Technologies, Inc. and/or its subsidiaries.
# SPDX-License-Identifier: BSD-3-Clause-Clear
#
"""End-to-end rendering checks over the N/UDS/M/ACC configuration space."""

from __future__ import annotations

import re
import unittest

from mmul_gen.catalog import (
    ALL_INSTRUCTIONS,
    MATRIX_MULTIPLY_INSTRUCTIONS,
    TYPE_REGISTER_INSTRUCTIONS,
    generate_all,
)
from mmul_gen.tests.helpers import machine


CONFIGS = (
    (4, 8, 16, 1),
    (8, 8, 32, 4),
    (16, 16, 32, 16),
    (32, 32, 32, 4),
)


def sources_by_name(machine_config):
    return {source.name: source.text for source in generate_all(machine_config)}


EXPECTATION = re.compile(r"^(\s+EXPECT\s+t\d, ).*$", flags=re.MULTILINE)


def expected_values(text: str) -> list[int]:
    """Every ``EXPECT`` immediate in a generated source, in file order."""

    return [
        int(match.group(1), 0)
        for match in re.finditer(
            r"^\s+EXPECT\s+t\d, (0x[0-9a-fA-F]+|\d+)$", text, flags=re.MULTILINE
        )
    ]


def without_expected_values(text: str) -> list[str]:
    """The source with mnemonic and ``EXPECT`` immediates normalised away."""

    blanked = EXPECTATION.sub(r"\1", text)
    return re.sub(r"mmul\w*\.2d", "<mnemonic>", blanked).splitlines()


class GeneratedSourceTests(unittest.TestCase):
    """Assertions over generated sources that never echo the whole file."""

    def assert_contains(self, text: str, needle: str) -> None:
        self.assertTrue(needle in text, f"expected {needle!r} in the generated source")

    def assert_absent(self, text: str, needle: str) -> None:
        self.assertFalse(needle in text, f"unexpected {needle!r} in the generated source")


class GenerationTests(GeneratedSourceTests):
    def test_no_local_label_is_defined_twice(self) -> None:
        configs = [
            machine(n=n, uds=uds, num_m_regs=m_regs, num_acc_regs=acc_regs)
            for n, uds, m_regs, acc_regs in CONFIGS
        ]
        for config in configs:
            for source in generate_all(config):
                labels = re.findall(r"^(\.L[\w.]+):", source.text, flags=re.MULTILINE)
                duplicates = sorted({label for label in labels if labels.count(label) > 1})
                with self.subTest(source=source.name, uds=config.uds, n=config.n):
                    self.assertEqual(duplicates, [])

    def test_generation_is_deterministic(self) -> None:
        config = machine()
        self.assertEqual(
            [source.text for source in generate_all(config)],
            [source.text for source in generate_all(config)],
        )

    def test_every_source_is_a_complete_self_checking_test(self) -> None:
        for uds in (8, 16, 32):
            sources = sources_by_name(machine(uds=uds))
            for instruction in MATRIX_MULTIPLY_INSTRUCTIONS:
                with self.subTest(instruction=instruction.name, uds=uds):
                    text = sources[instruction.file_name]
                    self.assertTrue(text.startswith("# Copyright"))
                    self.assert_contains(text, '.include "test.inc"')
                    self.assert_contains(text, "    ame.acquire t1, t0")
                    self.assert_contains(text, "    RVMODEL_HALT_PASS")
                    self.assert_contains(text, "\n.data\n")
                    self.assert_contains(text, "\ndst_square:")
                    self.assert_absent(text, "None")

    def test_every_declared_datatype_appears_in_the_generated_source(self) -> None:
        for uds in (8, 16, 32):
            config = machine(uds=uds)
            sources = sources_by_name(config)
            for instruction in MATRIX_MULTIPLY_INSTRUCTIONS:
                text = sources[instruction.file_name]
                for dtype in instruction.supported_dtypes(config):
                    with self.subTest(instruction=instruction.name, uds=uds, dtype=dtype.name):
                        self.assert_contains(text, dtype.name)

    def test_layout_comments_match_the_cases_that_describe_one(self) -> None:
        # The comment block is derived from ``Case.layout``, so the source must
        # carry exactly one comment line per layout-bearing case and no more.
        # A family whose cases describe no layout (raw transfers, backend
        # state) therefore has to render none.
        for n, uds, m_regs, acc_regs in CONFIGS:
            config = machine(n=n, uds=uds, num_m_regs=m_regs, num_acc_regs=acc_regs)
            for instruction in ALL_INSTRUCTIONS:
                cases = list(instruction.cases(config))
                source = instruction.gen(config)
                if not cases:
                    self.assertIsNone(source)
                    continue
                described = sum(
                    len(case.layout.comment_lines())
                    for _, case in cases
                    if case.layout is not None
                )
                with self.subTest(
                    source=source.name, n=n, uds=uds, m=m_regs, acc=acc_regs
                ):
                    self.assertEqual(
                        len(re.findall(r"^\s+# (?:M|ACC) layout \[", source.text, re.MULTILINE)),
                        described,
                    )

    def test_product_cases_pair_an_m_layout_with_an_accumulator(self) -> None:
        # A matrix product addresses both register files, so every case that
        # names one must name the other.
        for n, uds, m_regs, acc_regs in CONFIGS:
            config = machine(n=n, uds=uds, num_m_regs=m_regs, num_acc_regs=acc_regs)
            for instruction in MATRIX_MULTIPLY_INSTRUCTIONS:
                source = instruction.gen(config)
                with self.subTest(source=source.name, n=n, uds=uds, m=m_regs, acc=acc_regs):
                    self.assertEqual(source.text.count("# M layout"), source.text.count("# ACC layout"))
                    self.assertGreater(source.text.count("# M layout"), 0)

    def test_type_register_cases_carry_exactly_one_register_layout_comment(self) -> None:
        # A descriptor roundtrip addresses one register file, so each case has
        # exactly one layout comment rather than a pair.
        for n, uds, m_regs, acc_regs in CONFIGS:
            config = machine(n=n, uds=uds, num_m_regs=m_regs, num_acc_regs=acc_regs)
            for instruction in TYPE_REGISTER_INSTRUCTIONS:
                source = instruction.gen(config)
                with self.subTest(source=source.name, n=n, uds=uds, m=m_regs, acc=acc_regs):
                    self.assertEqual(
                        source.text.count("# case "),
                        source.text.count("# M layout") + source.text.count("# ACC layout"),
                    )
                    self.assertGreater(source.text.count("# case "), 0)

    def test_no_case_names_an_illegal_m_register(self) -> None:
        for n, uds, m_regs, acc_regs in CONFIGS:
            if m_regs >= 32:
                continue
            config = machine(n=n, uds=uds, num_m_regs=m_regs, num_acc_regs=acc_regs)
            for source in generate_all(config):
                with self.subTest(source=source.name, m=m_regs):
                    forbidden = "|".join(str(index) for index in range(m_regs, 32))
                    self.assertIsNone(re.search(rf"(?<![0-9])m(?:{forbidden})\b", source.text))

    def test_only_a_declared_illegal_span_names_an_out_of_file_accumulator(self) -> None:
        """An out-of-file accumulator name has to come from a declared span.

        The packed-span exception recipe exists precisely to name a span that
        crosses the end of the accumulator file, so the guard is not "never name
        one" but "never name one that the case did not declare illegal": every
        such name must sit inside the ``expected illegal`` span of its case.
        """

        for n, uds, m_regs, acc_regs in CONFIGS:
            config = machine(n=n, uds=uds, num_m_regs=m_regs, num_acc_regs=acc_regs)
            for source in generate_all(config):
                declared: tuple[int, int] | None = None
                pending: tuple[int, int] | None = None
                for line in source.text.splitlines():
                    if "# ACC layout" in line:
                        span = re.search(r"acc(\d+)\.\.acc(\d+)", line)
                        pending = (
                            (int(span.group(1)), int(span.group(2)))
                            if span and "expected illegal" in line
                            else None
                        )
                        continue
                    if line.startswith("    # case "):
                        # The driver emits a case's layout comment directly
                        # above it, so this is where the declaration takes over.
                        declared, pending = pending, None
                    for match in re.finditer(r"acc(\d+)", line):
                        index = int(match.group(1))
                        if index < acc_regs:
                            continue
                        with self.subTest(
                            source=source.name, acc=acc_regs, name=match.group(0)
                        ):
                            self.assertIsNotNone(
                                declared,
                                f"{source.name} names acc{index} outside a declared illegal span",
                            )
                            assert declared is not None
                            self.assertLessEqual(declared[0], index)
                            self.assertLessEqual(index, declared[1])

    def test_the_multi_accumulator_template_only_runs_where_it_is_declared(self) -> None:
        for acc_regs, expected in ((1, False), (4, True)):
            sources = sources_by_name(machine(num_acc_regs=acc_regs))
            for instruction in MATRIX_MULTIPLY_INSTRUCTIONS:
                text = sources[instruction.file_name]
                present = "multi_acc_independent" in text
                with self.subTest(instruction=instruction.name, acc=acc_regs):
                    self.assertEqual(
                        present, expected and instruction.name == "mmulacc.2d"
                    )

    def test_transposed_variants_change_only_the_expected_values(self) -> None:
        # ``transposes_lhs``/``transposes_rhs`` reach the generated test only as a
        # different ``reference.py`` product, so the stimulus, the register
        # layouts, and the code must be identical while the expectations differ.
        # ``mmulatacc`` and ``mmulbtacc`` declare the same templates and datatypes,
        # so they differ in nothing else.
        sources = sources_by_name(machine())
        for transposed_lhs, transposed_rhs in (
            ("mmulatacc_2d.S", "mmulbtacc_2d.S"),
            ("mmulataccneg_2d.S", "mmulbtaccneg_2d.S"),
        ):
            with self.subTest(lhs=transposed_lhs, rhs=transposed_rhs):
                self.assertEqual(
                    without_expected_values(sources[transposed_lhs]),
                    without_expected_values(sources[transposed_rhs]),
                )
                lhs_values = expected_values(sources[transposed_lhs])
                rhs_values = expected_values(sources[transposed_rhs])
                self.assertTrue(lhs_values)
                self.assertEqual(len(lhs_values), len(rhs_values))
                self.assertNotEqual(lhs_values, rhs_values)

    def test_negated_variants_change_the_expected_values(self) -> None:
        # ``negates_product`` also selects the negative float-overflow boundary as
        # the stimulus, so unlike transposition it may change the data section too;
        # what must never happen is the two variants agreeing on every expectation.
        sources = sources_by_name(machine())
        for plain, negated in (
            ("mmulatacc_2d.S", "mmulataccneg_2d.S"),
            ("mmulbtacc_2d.S", "mmulbtaccneg_2d.S"),
        ):
            with self.subTest(plain=plain, negated=negated):
                plain_values = expected_values(sources[plain])
                negated_values = expected_values(sources[negated])
                self.assertTrue(plain_values)
                self.assertEqual(len(plain_values), len(negated_values))
                self.assertNotEqual(plain_values, negated_values)


if __name__ == "__main__":
    unittest.main()
