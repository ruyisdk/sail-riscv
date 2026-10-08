#!/usr/bin/env python3
#
# Copyright (c) Qualcomm Technologies, Inc. and/or its subsidiaries.
# SPDX-License-Identifier: BSD-3-Clause-Clear

"""The shared configuration validators accept exactly the manual's values."""

from __future__ import annotations

import argparse
import unittest

from matrix_geometry import (
    comma_separated,
    matrix_n,
    num_acc_regs,
    num_m_regs,
    unit_dtype_size,
)


class GeometryValueTests(unittest.TestCase):
    def test_values_the_manual_allows(self) -> None:
        # N is a power of two with no upper bound; 128 is the rv64-ztt-16k-8
        # configuration (AME_NELEM = 16384).
        self.assertEqual(matrix_n("128"), 128)
        self.assertEqual(unit_dtype_size("32"), 32)
        self.assertEqual(num_m_regs("16"), 16)
        self.assertEqual(num_acc_regs("16"), 16)

    def test_values_the_manual_forbids(self) -> None:
        for text in ("7", "0", "3"):
            with self.assertRaises(argparse.ArgumentTypeError):
                matrix_n(text)
        with self.assertRaises(argparse.ArgumentTypeError):
            unit_dtype_size("12")
        with self.assertRaises(argparse.ArgumentTypeError):
            num_m_regs("64")
        with self.assertRaises(argparse.ArgumentTypeError):
            num_acc_regs("3")

    def test_the_driver_sweep_takes_a_comma_separated_list_in_written_order(self) -> None:
        sweep = comma_separated(matrix_n)
        self.assertEqual(sweep("4,8,16"), [4, 8, 16])
        self.assertEqual(sweep("8, 4"), [8, 4])
        self.assertEqual(sweep("8,8,16"), [8, 16])

    def test_the_driver_sweep_rejects_empty_and_illegal_entries(self) -> None:
        sweep = comma_separated(num_acc_regs)
        for text in ("", " , ", ","):
            with self.assertRaises(argparse.ArgumentTypeError):
                sweep(text)
        with self.assertRaises(argparse.ArgumentTypeError):
            sweep("1,3")


if __name__ == "__main__":
    unittest.main()
