#!/usr/bin/env python3
#
# Copyright (c) Qualcomm Technologies, Inc. and/or its subsidiaries.
# SPDX-License-Identifier: BSD-3-Clause-Clear
#
"""Floating-point expected values for the 2D matrix-product templates."""

from __future__ import annotations

from mmul_gen.inputs import SOFTFLOAT_LAYOUTS


def softfloat_power_of_two(dtype_name: str, exponent: int) -> int:
    """Encode ``2**exponent`` in one covered floating-point format."""

    bias, mantissa_bits, _total_bits = SOFTFLOAT_LAYOUTS[dtype_name]
    return (bias + exponent) << mantissa_bits


def softfloat_product_expected(dtype_name: str, n: int, *, negated: bool) -> int:
    """Expected element of the all-ones float product for the active N.

    Each entry of the product of two all-ones squares is N, but the 2D float
    variants accumulate one product at a time through the destination dtype.
    Integers up to ``2**(mantissa_bits + 1)`` are exact in every format; above
    that the representable spacing reaches 2 and the RNE tie at ``sum + 1``
    rounds back down, so the running sum sticks at ``2**(mantissa_bits + 1)``:
    E5M2 caps at 8 and E4M3 at 16, while the wider formats stay exact for the
    supported N values.
    """

    if n <= 0 or n & (n - 1):
        raise ValueError(f"softfloat 2D expectation requires a power-of-two N, got {n}")
    _, mantissa_bits, total_bits = SOFTFLOAT_LAYOUTS[dtype_name]
    magnitude = min(n, 1 << (mantissa_bits + 1))
    expected = softfloat_power_of_two(dtype_name, magnitude.bit_length() - 1)
    if negated:
        expected |= 1 << (total_bits - 1)
    return expected


__all__ = ["softfloat_power_of_two", "softfloat_product_expected"]
