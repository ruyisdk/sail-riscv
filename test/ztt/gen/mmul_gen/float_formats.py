#!/usr/bin/env python3
#
# Copyright (c) Qualcomm Technologies, Inc. and/or its subsidiaries.
# SPDX-License-Identifier: BSD-3-Clause-Clear
#
"""Floating-point formats: their exact values, and their stored encodings.

The 2D matrix-product templates need the expected value of a power-of-two
product; the mixed-format templates need to know whether a value is exactly
representable in a format at all, which is the same question asked the other way
round.  Both live here so the format knowledge has one home.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from fractions import Fraction

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


#: ``amefflags.NX``: the result was rounded.
FFLAGS_NX = 0x01

#: The smallest most-significant byte of a stored element whose exponent field is
#: all ones, i.e. an infinity or a NaN.  The "finite number" check of the
#: approximate operations masks the sign bit off the top byte and compares it
#: against this value.
FINITE_LIMIT_BYTE = {
    "AME_FP16_DTYPE": 0x7C,
    "AME_BF16_DTYPE": 0x7F,
    "AME_FP32_DTYPE": 0x7F,
    "AME_FP64_DTYPE": 0x7F,
    "AME_OCP_E4M3_DTYPE": 0x7F,
    "AME_OCP_E5M2_DTYPE": 0x7C,
}

#: The canonical quiet NaN of each format, used to seed a destination square.
CANONICAL_NAN = {
    "AME_FP16_DTYPE": 0x7E00,
    "AME_BF16_DTYPE": 0x7FC0,
    "AME_FP32_DTYPE": 0x7FC00000,
    "AME_FP64_DTYPE": 0x7FF8000000000000,
    "AME_OCP_E4M3_DTYPE": 0x7F,
    "AME_OCP_E5M2_DTYPE": 0x7E,
}


@dataclass(frozen=True)
class FloatFormat:
    """One floating-point format, exactly enough to encode a value bit by bit."""

    exponent_bits: int
    significand_bits: int
    bias: int
    has_infinity: bool

    @property
    def bits(self) -> int:
        return 1 + self.exponent_bits + self.significand_bits

    @property
    def minimum_exponent(self) -> int:
        """Exponent of the smallest normal value."""

        return 1 - self.bias

    @property
    def maximum_exponent(self) -> int:
        """Exponent of the largest finite value."""

        reserved = 1 if self.has_infinity else 0
        return (1 << self.exponent_bits) - 1 - reserved - self.bias

    @property
    def subnormal_bit_weight(self) -> int:
        """Exponent of the least significant bit of a subnormal value."""

        return self.minimum_exponent - self.significand_bits


#: The six floating-point formats of §6.2.2.
FORMATS = {
    "AME_FP16_DTYPE": FloatFormat(5, 10, 15, True),
    "AME_BF16_DTYPE": FloatFormat(8, 7, 127, True),
    "AME_FP32_DTYPE": FloatFormat(8, 23, 127, True),
    "AME_FP64_DTYPE": FloatFormat(11, 52, 1023, True),
    "AME_OCP_E4M3_DTYPE": FloatFormat(4, 3, 7, False),
    "AME_OCP_E5M2_DTYPE": FloatFormat(5, 2, 15, True),
}


def floor_log2(value: Fraction) -> int:
    """The largest ``e`` with ``2**e <= value``, for a positive exact value."""

    if value <= 0:
        raise ValueError(f"{value}: not a positive value")
    exponent = value.numerator.bit_length() - value.denominator.bit_length()
    while Fraction(2) ** exponent > value:
        exponent -= 1
    while Fraction(2) ** (exponent + 1) <= value:
        exponent += 1
    return exponent


def encode_exact(value: Fraction, dtype_name: str) -> int | None:
    """The stored bit pattern of ``value`` in ``dtype_name``, or ``None``.

    ``None`` is the answer whenever the value would have to be rounded: it is
    not exactly representable in that format.  Callers use it to pick a
    stimulus whose expectation is the mathematical answer rather than a
    rounding of it.
    """

    fmt = FORMATS[dtype_name]
    if value == 0:
        return 0
    negative = value < 0
    magnitude = -value if negative else value
    sign = 1 << (fmt.bits - 1) if negative else 0
    exponent = floor_log2(magnitude)
    if exponent < fmt.minimum_exponent:
        scaled = magnitude / Fraction(2) ** fmt.subnormal_bit_weight
        if scaled.denominator != 1:
            return None
        significand = scaled.numerator
        if significand <= 0 or significand >= 1 << fmt.significand_bits:
            return None
        return sign | significand
    if exponent > fmt.maximum_exponent:
        return None
    scaled = magnitude / Fraction(2) ** (exponent - fmt.significand_bits)
    if scaled.denominator != 1:
        return None
    significand = scaled.numerator
    hidden = 1 << fmt.significand_bits
    if significand < hidden or significand >= 2 * hidden:
        return None
    exponent_field = exponent + fmt.bias
    return sign | (exponent_field << fmt.significand_bits) | (significand - hidden)


#: The four rounding directions the mfrint* family names.
ROUND_DOWN = "RDN"
ROUND_NEAREST = "RNE"
ROUND_UP = "RUP"
ROUND_ZERO = "RTZ"


def _grid_step(fmt: FloatFormat, magnitude: Fraction) -> Fraction:
    """The spacing of representable values around ``magnitude``."""

    if magnitude == 0:
        return Fraction(2) ** fmt.subnormal_bit_weight
    exponent = floor_log2(magnitude)
    if exponent < fmt.minimum_exponent:
        return Fraction(2) ** fmt.subnormal_bit_weight
    return Fraction(2) ** (max(exponent, fmt.minimum_exponent) - fmt.significand_bits)


def encode_rounded(
    value: Fraction, dtype_name: str, direction: str
) -> tuple[int, bool]:
    """Round ``value`` into ``dtype_name`` in ``direction``; return bits and inexact.

    This is the representation step of the mfrint* family: the rounded integral
    result still has to be *stored* in the destination format, and
    instructions.adoc:1516-1517 makes the instruction's own direction govern
    that step, so the expectation cannot come from the destination field.  The
    two grid neighbours bracket every answer, so the search is exhaustive.
    """

    if direction not in (ROUND_DOWN, ROUND_NEAREST, ROUND_UP, ROUND_ZERO):
        raise ValueError(f"{direction}: not a rounding direction of the family")
    fmt = FORMATS[dtype_name]
    if value == 0:
        return 0, False
    negative = value < 0
    magnitude = -value if negative else value
    sign = 1 << (fmt.bits - 1) if negative else 0
    step = _grid_step(fmt, magnitude)
    steps = magnitude / step
    below = Fraction(steps.numerator // steps.denominator) * step
    above = below + step
    if magnitude == below:
        chosen = below
    elif direction == ROUND_ZERO:
        chosen = below
    elif direction == ROUND_DOWN:
        chosen = above if negative else below
    elif direction == ROUND_UP:
        chosen = below if negative else above
    else:
        distance_below = magnitude - below
        distance_above = above - magnitude
        if distance_below < distance_above:
            chosen = below
        elif distance_above < distance_below:
            chosen = above
        else:
            # Ties to even: keep the neighbour whose least significant
            # significand bit is zero.
            chosen = below if int(below / step) % 2 == 0 else above
    encoded = encode_exact(-chosen if negative else chosen, dtype_name)
    if encoded is None:
        raise ValueError(
            f"rounded value {chosen} is not representable in {dtype_name}; "
            "the caller asked for an out-of-range representation"
        )
    return encoded, chosen != magnitude


def exact_root(value: Fraction) -> Fraction:
    """The exact square root of a perfect square."""

    root = Fraction(math.isqrt(value.numerator), math.isqrt(value.denominator))
    if root * root != value:
        raise ValueError(f"sqrt({value}) is not exactly representable")
    return root


__all__ = [
    "CANONICAL_NAN",
    "FINITE_LIMIT_BYTE",
    "FORMATS",
    "FloatFormat",
    "ROUND_DOWN",
    "ROUND_NEAREST",
    "ROUND_UP",
    "ROUND_ZERO",
    "encode_exact",
    "encode_rounded",
    "exact_root",
    "floor_log2",
    "softfloat_power_of_two",
    "softfloat_product_expected",
]
