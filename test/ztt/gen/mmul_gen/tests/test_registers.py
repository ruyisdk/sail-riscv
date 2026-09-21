#!/usr/bin/env python3
#
# Copyright (c) Qualcomm Technologies, Inc. and/or its subsidiaries.
# SPDX-License-Identifier: BSD-3-Clause-Clear
#
"""M/ACC register layouts are resolved, deduplicated, and strictly validated."""

from __future__ import annotations

import unittest

from mmul_gen.registers import (
    AccumulatorOperand,
    MRegisterGroup,
    MRegisterLayout,
    MRegisterRole,
    accumulator_operands,
    m_register_layouts,
    paired_layouts,
    representative_accumulator_operands,
)


SINGLE = (MRegisterRole("ms1", 1), MRegisterRole("ms2", 1), MRegisterRole("md", 1, reuse_of="ms1"))
WIDE = (MRegisterRole("ms1", 4), MRegisterRole("ms2", 4), MRegisterRole("md", 4, reuse_of="ms1"))


class LayoutTests(unittest.TestCase):
    def test_layouts_cover_low_high_and_edge_placements(self) -> None:
        layouts = m_register_layouts(32, SINGLE)
        self.assertEqual([layout.name for layout in layouts], ["low", "high", "boundary"])
        self.assertEqual([layout.base("ms1") for layout in layouts], [0, 30, 0])
        self.assertEqual([layout.base("ms2") for layout in layouts], [1, 31, 31])
        for layout in layouts:
            self.assertEqual(layout.base("md"), layout.base("ms1"))

    def test_layouts_that_do_not_fit_are_absent_rather_than_moved(self) -> None:
        self.assertEqual(m_register_layouts(16, WIDE)[0].base("ms1"), 0)
        self.assertEqual(
            [layout.name for layout in m_register_layouts(16, WIDE)],
            ["low", "high", "boundary"],
        )
        # A 4-register triple needs 8 registers, so both edge placements
        # collapse onto the low one and an 8-register span still fits.
        self.assertEqual([layout.name for layout in m_register_layouts(8, WIDE)], ["low"])
        self.assertEqual(m_register_layouts(4, WIDE), ())
        self.assertEqual(m_register_layouts(8, (MRegisterRole("ms1", 16),)), ())

    def test_duplicate_placements_are_deduplicated(self) -> None:
        layouts = m_register_layouts(4, SINGLE)
        self.assertEqual(len(layouts), len({tuple((g.role, g.base) for g in item.groups) for item in layouts}))

    def test_declared_layout_rejects_overlap_without_an_alias(self) -> None:
        with self.assertRaisesRegex(ValueError, "overlap"):
            MRegisterLayout(
                "bad",
                "overlapping",
                (
                    MRegisterGroup("ms1", 0, 2),
                    MRegisterGroup("ms2", 0, 2),
                ),
            )

    def test_declared_layout_rejects_a_partial_alias(self) -> None:
        with self.assertRaisesRegex(ValueError, "exactly reuse"):
            MRegisterLayout(
                "bad",
                "partial alias",
                (
                    MRegisterGroup("ms1", 0, 4),
                    MRegisterGroup("md", 0, 2, reuse_of="ms1"),
                ),
            )

    def test_declared_layout_rejects_unaligned_groups(self) -> None:
        with self.assertRaisesRegex(ValueError, "not aligned"):
            MRegisterGroup("ms1", 2, 4)

    def test_accumulator_operands_cover_every_legal_span(self) -> None:
        self.assertEqual(
            [(operand.base, operand.span) for operand in accumulator_operands(4)],
            [(0, 1), (1, 1), (2, 1), (3, 1)],
        )
        self.assertEqual(
            [(operand.name, operand.base) for operand in representative_accumulator_operands(16)],
            [("acc0", 0), ("acc7", 7), ("acc8", 8), ("acc15", 15)],
        )
        self.assertEqual(
            [operand.base for operand in representative_accumulator_operands(2)], [0, 1]
        )

    def test_paired_layouts_cycle_instead_of_cross_producting(self) -> None:
        layouts = paired_layouts(32, 4, SINGLE)
        self.assertEqual(len(layouts), 4)
        self.assertEqual([layout.acc.base for layout in layouts], [0, 1, 2, 3])
        self.assertEqual([layout.m.name for layout in layouts], ["low", "high", "boundary", "low"])

    def test_packed_span_comment_names_the_whole_span(self) -> None:
        operand = AccumulatorOperand("all_accumulators", "every accumulator", base=0, span=16)
        self.assertEqual(operand.register_text, "acc0..acc15")
        self.assertEqual(
            operand.comment(), "ACC layout [all_accumulators, legal]: acc0..acc15"
        )

    def test_layout_comment_reports_the_temporal_alias(self) -> None:
        layout = m_register_layouts(32, SINGLE)[0]
        self.assertEqual(
            layout.comment(),
            "M layout [low]: ms1=m0, ms2=m1, md=m0 (reuses ms1)",
        )


if __name__ == "__main__":
    unittest.main()
