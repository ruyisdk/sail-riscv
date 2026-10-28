#!/usr/bin/env python3
#
# Copyright (c) Qualcomm Technologies, Inc. and/or its subsidiaries.
# SPDX-License-Identifier: BSD-3-Clause-Clear
#
"""The same-format log/exp cases: which arguments run, and what they assert.

The generated sources are frozen by the golden test; these are the properties a
reader of the recipe should be able to check without hashing assembly: the four
IEEE formats are covered and the OCP 8-bit formats are not, every format runs an
exact and an inexact argument, the exact one asserts the stored value and a clear
NX while the inexact one asserts NX, and each operation's special arguments
carry the flags §6.2.3 gives them.
"""

from __future__ import annotations

import unittest

from mmul_gen.catalog import ALL_INSTRUCTIONS
from mmul_gen.templates.logexp_float_math import (
    IEEE_DTYPES,
    LogExpFloatMath,
    LogExpOperation,
    logexp_cases,
)
from mmul_gen.tests.helpers import dtypes, machine

#: The mnemonic each operation is attached to.
INSTRUCTIONS = {LogExpOperation.EXP2: "mexp2.ew", LogExpOperation.LOG2: "mlog2.ew"}
#: Element width of each covered descriptor.
WIDTHS = {"AME_FP16_DTYPE": 16, "AME_BF16_DTYPE": 16, "AME_FP32_DTYPE": 32,
          "AME_FP64_DTYPE": 64}


def instruction(name: str):
    for candidate in ALL_INSTRUCTIONS:
        if candidate.name == name:
            return candidate
    raise AssertionError(f"no instruction named {name}")


def scenarios(operation: LogExpOperation, dtype_name: str) -> dict[str, object]:
    cases = logexp_cases(operation, dtype_name, WIDTHS[dtype_name])
    return {case.scenario: case for case in cases}


class CoverageTest(unittest.TestCase):
    def test_the_four_ieee_formats_are_covered(self) -> None:
        template = LogExpFloatMath(LogExpOperation.EXP2)
        config = machine()
        covered = {
            dtype.name
            for dtype in dtypes()
            if template.fits(config, instruction("mexp2.ew"), dtype)
        }
        self.assertEqual(covered, set(IEEE_DTYPES))

    def test_the_ocp_formats_are_left_to_the_mixed_corpus(self) -> None:
        template = LogExpFloatMath(LogExpOperation.EXP2)
        config = machine()
        for dtype in dtypes():
            if dtype.name in IEEE_DTYPES:
                continue
            with self.subTest(dtype=dtype.name):
                self.assertFalse(template.fits(config, instruction("mexp2.ew"), dtype))

    def test_both_instructions_run_it(self) -> None:
        for operation, mnemonic in INSTRUCTIONS.items():
            with self.subTest(mnemonic=mnemonic):
                bound = [
                    template
                    for template in instruction(mnemonic).templates
                    if isinstance(template, LogExpFloatMath)
                ]
                self.assertEqual([template.operation for template in bound], [operation])


class CaseTableTest(unittest.TestCase):
    def test_every_format_has_an_exact_and_an_inexact_argument(self) -> None:
        for operation in INSTRUCTIONS:
            for dtype_name in IEEE_DTYPES:
                with self.subTest(operation=operation, dtype=dtype_name):
                    cases = scenarios(operation, dtype_name)
                    self.assertEqual(cases["exact"].flags, 0)
                    self.assertEqual(cases["inexact"].flags, 0x01)
                    self.assertNotEqual(
                        cases["exact"].expected, cases["inexact"].expected
                    )

    def test_the_exact_argument_is_the_round_trip_of_the_exact_answer(self) -> None:
        # 2**3 = 8 and log2(8) = 3, both exactly representable in all four
        # formats, so the same answer bits appear in every one of them only for
        # the same value -- the case is written from the answer, not the format.
        for dtype_name in IEEE_DTYPES:
            with self.subTest(dtype=dtype_name):
                exp2 = scenarios(LogExpOperation.EXP2, dtype_name)["exact"]
                log2 = scenarios(LogExpOperation.LOG2, dtype_name)["exact"]
                self.assertEqual(
                    exp2.source, log2.expected
                )  # 3 -> 8 and 8 -> 3

    def test_exp2_covers_the_whole_extended_line(self) -> None:
        for dtype_name in IEEE_DTYPES:
            with self.subTest(dtype=dtype_name):
                cases = scenarios(LogExpOperation.EXP2, dtype_name)
                # Both zeros raise 2**0 = 1; +inf stays +inf and -inf becomes +0,
                # none of which raises a flag.
                for scenario in ("zero", "neg_zero", "inf", "neg_inf"):
                    self.assertEqual(cases[scenario].flags, 0)
                self.assertEqual(cases["zero"].expected, cases["neg_zero"].expected)
                self.assertEqual(cases["neg_inf"].expected, 0)

    def test_log2_specialises_zero_and_negative_arguments(self) -> None:
        for dtype_name in IEEE_DTYPES:
            with self.subTest(dtype=dtype_name):
                cases = scenarios(LogExpOperation.LOG2, dtype_name)
                # log2(+-0) is the pole at zero: -inf with DZ.
                for scenario in ("zero", "neg_zero"):
                    self.assertEqual(cases[scenario].flags, 0x08)
                # Every other negative argument, -inf included, is invalid.
                for scenario in ("neg_inf", "negative"):
                    self.assertEqual(cases[scenario].flags, 0x10)

    def test_the_nan_arguments_differ_only_in_their_flag(self) -> None:
        for operation in INSTRUCTIONS:
            for dtype_name in IEEE_DTYPES:
                with self.subTest(operation=operation, dtype=dtype_name):
                    cases = scenarios(operation, dtype_name)
                    self.assertEqual(cases["quiet_nan"].flags, 0)
                    self.assertEqual(cases["signaling_nan"].flags, 0x10)
                    self.assertEqual(
                        cases["quiet_nan"].expected, cases["signaling_nan"].expected
                    )


class EmissionTest(unittest.TestCase):
    def text(self, operation: LogExpOperation, config) -> str:
        mnemonic = INSTRUCTIONS[operation]
        return instruction(mnemonic).gen(config).text

    def test_every_case_clears_the_flags_before_the_operation(self) -> None:
        text = self.text(LogExpOperation.EXP2, machine())
        self.assertIn("csrw    amefflags, x0", text)
        self.assertIn("csrr    t4, amefflags", text)
        self.assertLess(
            text.index("csrw    amefflags, x0"), text.index("csrr    t4, amefflags")
        )

    def test_the_scenarios_appear_in_their_table_order(self) -> None:
        text = self.text(LogExpOperation.LOG2, machine())
        positions = [
            text.index(f"mlog2.ew AME_FP32_DTYPE: {scenario}")
            for scenario in (
                "exact",
                "inexact",
                "quiet_nan",
                "signaling_nan",
                "zero",
                "neg_zero",
                "inf",
                "neg_inf",
                "negative",
            )
        ]
        self.assertEqual(positions, sorted(positions))


if __name__ == "__main__":
    unittest.main()
