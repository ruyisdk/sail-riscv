#!/usr/bin/env python3
#
# Copyright (c) Qualcomm Technologies, Inc. and/or its subsidiaries.
# SPDX-License-Identifier: BSD-3-Clause-Clear

from __future__ import annotations

import unittest
from unittest import mock

import numpy as np

from numeric_reference import (
    IntegerDType,
    integer_elementwise_binary,
    integer_elementwise_ternary,
    integer_matmul,
)


class IntegerMatmulReferenceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.int8 = IntegerDType(bits=8, signed=True)
        self.uint8 = IntegerDType(bits=8, signed=False)
        self.int16 = IntegerDType(bits=16, signed=True)

    def assert_values(self, actual: np.ndarray, expected: list[list[int]]) -> None:
        self.assertEqual(actual.tolist(), expected)

    def test_basic_matrix_product(self) -> None:
        result = integer_matmul(
            [[1, 2], [3, 4]],
            [[5, 6], [7, 8]],
            n=2,
            lhs_dtype=self.int8,
            rhs_dtype=self.int8,
            dest_dtype=self.int16,
        )
        self.assert_values(result.values, [[19, 22], [43, 50]])
        self.assertFalse(result.saturated)

    def test_transpose_variants(self) -> None:
        lhs = [[1, 2], [3, 4]]
        rhs = [[5, 6], [7, 8]]
        lhs_transposed = integer_matmul(
            lhs,
            rhs,
            n=2,
            lhs_dtype=self.int8,
            rhs_dtype=self.int8,
            dest_dtype=self.int16,
            transpose_lhs=True,
        )
        rhs_transposed = integer_matmul(
            lhs,
            rhs,
            n=2,
            lhs_dtype=self.int8,
            rhs_dtype=self.int8,
            dest_dtype=self.int16,
            transpose_rhs=True,
        )
        self.assert_values(lhs_transposed.values, [[26, 30], [38, 44]])
        self.assert_values(rhs_transposed.values, [[17, 23], [39, 53]])

    def test_multiple_squares_are_accumulated_exactly(self) -> None:
        result = integer_matmul(
            [[[1, 0], [0, 1]], [[2, 0], [0, 2]]],
            [[[3, 0], [0, 3]], [[4, 0], [0, 4]]],
            n=2,
            lhs_dtype=self.int8,
            rhs_dtype=self.int8,
            dest_dtype=self.int16,
        )
        self.assert_values(result.values, [[11, 0], [0, 11]])

    def test_accumulator_and_subtracted_product(self) -> None:
        result = integer_matmul(
            [[2, 0], [0, 2]],
            [[3, 0], [0, 3]],
            n=2,
            lhs_dtype=self.int8,
            rhs_dtype=self.int8,
            dest_dtype=self.int16,
            accumulator=[[10, 1], [2, 10]],
            subtract_product=True,
        )
        self.assert_values(result.values, [[4, 1], [2, 4]])

    def test_mixed_signedness_uses_source_datatypes(self) -> None:
        result = integer_matmul(
            [[0xFF]],
            [[2]],
            n=1,
            lhs_dtype=self.int8,
            rhs_dtype=self.uint8,
            dest_dtype=self.int16,
        )
        self.assert_values(result.values, [[-2]])

    def test_non_saturating_destination_wraps(self) -> None:
        signed = integer_matmul(
            [[100]],
            [[2]],
            n=1,
            lhs_dtype=self.int8,
            rhs_dtype=self.int8,
            dest_dtype=self.int8,
        )
        unsigned_negative = integer_matmul(
            [[2]],
            [[3]],
            n=1,
            lhs_dtype=self.uint8,
            rhs_dtype=self.uint8,
            dest_dtype=self.uint8,
            subtract_product=True,
        )
        self.assert_values(signed.values, [[-56]])
        self.assert_values(unsigned_negative.values, [[250]])

    def test_saturating_destination_clamps_and_reports_flag(self) -> None:
        dtype = IntegerDType(bits=8, signed=True, saturating=True)
        result = integer_matmul(
            [[100]],
            [[2]],
            n=1,
            lhs_dtype=self.int8,
            rhs_dtype=self.int8,
            dest_dtype=dtype,
        )
        self.assert_values(result.values, [[127]])
        self.assertTrue(result.saturated)

    def test_rejects_mismatched_square_counts(self) -> None:
        with self.assertRaisesRegex(ValueError, "same number of squares"):
            integer_matmul(
                [1, 0, 0, 1, 1, 0, 0, 1],
                [1, 0, 0, 1],
                n=2,
                lhs_dtype=self.int8,
                rhs_dtype=self.int8,
                dest_dtype=self.int16,
            )

    def test_rejects_python_numpy_disagreement(self) -> None:
        with mock.patch(
            "numeric_reference._python_exact_matmul",
            return_value=np.asarray([[3]], dtype=object),
        ):
            with self.assertRaisesRegex(
                AssertionError, "NumPy/Python integer matrix reference mismatch"
            ):
                integer_matmul(
                    [[1]],
                    [[2]],
                    n=1,
                    lhs_dtype=self.int8,
                    rhs_dtype=self.int8,
                    dest_dtype=self.int16,
                )


class IntegerElementwiseReferenceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.int4 = IntegerDType(bits=4, signed=True)
        self.uint4 = IntegerDType(bits=4, signed=False)

    def test_signed_int4_scalar_is_decoded_before_arithmetic(self) -> None:
        self.assertEqual(
            integer_elementwise_binary(
                "mabsdiff.ew.x", 10, 5, dtype=self.int4
            ),
            -5,
        )
        self.assertEqual(
            integer_elementwise_binary("mmin.ew.x", 10, 5, dtype=self.int4),
            -6,
        )
        self.assertEqual(
            integer_elementwise_binary("mcmpge.ew.x", 10, 5, dtype=self.int4),
            0,
        )
        self.assertEqual(
            integer_elementwise_binary("mcmplt.ew.x", 10, 5, dtype=self.int4),
            -1,
        )

    def test_half_operations_use_default_rnu_rounding(self) -> None:
        self.assertEqual(
            integer_elementwise_binary("mhdiff.ew.x", 10, 5, dtype=self.int4),
            6,  # (B - c) / 2 = (5 - (-6)) / 2 = 5.5 -> RNU 6
        )
        self.assertEqual(
            integer_elementwise_binary("mmean.ew.x", 10, 5, dtype=self.int4),
            0,
        )
        self.assertEqual(
            integer_elementwise_binary("mmean.ew.x", 10, 5, dtype=self.uint4),
            8,
        )

    def test_subtract_forms_use_their_architectural_operand_order(self) -> None:
        self.assertEqual(
            integer_elementwise_binary("msub.ew", 3, 5, dtype=self.uint4),
            2,  # B - A
        )
        self.assertEqual(
            integer_elementwise_binary("msub.ew.x", 10, 5, dtype=self.uint4),
            0xb,  # B - c = 5 - (-6) = 11 mod 16 (UINT4)
        )
        self.assertEqual(
            integer_elementwise_binary("msub.ew.x", 10, 5, dtype=self.int4),
            -5,  # B - c = 5 - (-6) = 11 -> INT4 -5
        )

    def test_predicates_use_numeric_compare_not_msb(self) -> None:
        # UINT4 0xf decodes to 15 (>= 0).  The MSB rule would treat it as
        # negative; the manual numeric rule must select with ge and not with lt.
        self.assertEqual(
            integer_elementwise_binary("mselge.ew", 0xF, 5, dtype=self.uint4),
            5,
        )
        self.assertEqual(
            integer_elementwise_binary("msellt.ew", 0xF, 5, dtype=self.uint4),
            0,
        )
        # INT4 0xf decodes to -1 (< 0): select with lt, keep with ge.
        self.assertEqual(
            integer_elementwise_binary("msellt.ew", 0xF, 5, dtype=self.int4),
            5,
        )
        self.assertEqual(
            integer_elementwise_binary("mselge.ew", 0xF, 5, dtype=self.int4),
            0,
        )
        self.assertEqual(
            integer_elementwise_ternary("mcmovge.ew", 7, 0xF, 5, dtype=self.uint4),
            5,
        )
        self.assertEqual(
            integer_elementwise_ternary("mcmovlt.ew", 7, 0xF, 5, dtype=self.uint4),
            7,
        )

    def test_ternary_result_wraps_at_destination_width(self) -> None:
        self.assertEqual(
            integer_elementwise_ternary(
                "mmulacc.ew.x", 7, 10, 5, dtype=self.int4
            ),
            -7,
        )

if __name__ == "__main__":
    unittest.main()
