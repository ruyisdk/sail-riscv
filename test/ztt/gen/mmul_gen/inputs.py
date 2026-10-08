#!/usr/bin/env python3
#
# Copyright (c) Qualcomm Technologies, Inc. and/or its subsidiaries.
# SPDX-License-Identifier: BSD-3-Clause-Clear
#
"""The stimulus used by the matrix-multiply templates.

This module is the code-owned test-input inventory: deterministic integer
ramps, packed squares, floating-point boundary encodings.  Expected values are
*not* computed here; they live in :mod:`mmul_gen.reference` and
:mod:`mmul_gen.float_formats`.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from fp_semantics import (
    FFLAGS_OF_NX,
    FLOAT_BOUNDARIES,
    ROUNDING_MODE_DTYPES,
    ROUNDING_MODE_NAMES,
    overflow_result,
    signed,
)

from mmul_gen.machine import dtype_is_signed_int


def int_bounds(element_bits: int, signed_value: bool) -> tuple[int, int]:
    """Inclusive representable range for one integer datatype."""

    if signed_value:
        return (-(1 << (element_bits - 1)), (1 << (element_bits - 1)) - 1)
    return (0, (1 << element_bits) - 1)


def int_edge_value(dtype_name: str, element_bits: int, bound: str) -> int:
    """Corner value for one integer dtype.

    ``upper_bound``   -> representable maximum
    ``lower_bound``   -> representable minimum (0 for unsigned dtypes)
    ``abs_boundary``  -> the value whose absolute value is unrepresentable
                         (MIN for signed dtypes, MAX for unsigned dtypes)
    """

    low, high = int_bounds(element_bits, dtype_is_signed_int(dtype_name))
    if bound == "upper_bound":
        return high
    if bound == "lower_bound":
        return low
    if bound == "abs_boundary":
        return low if dtype_is_signed_int(dtype_name) else high
    raise ValueError(f"unknown integer edge bound: {bound}")


def sequence_values(nelem: int, start: int = 1) -> list[int]:
    """The linear ramp the reduce/zip sources are built from."""

    return list(range(start, start + nelem))


def gather_scatter_index_values(element_bits: int, n: int) -> list[int]:
    """Index table of a gather/scatter case: the row selector rides the sign bit.

    The hardware reads the index through the active datatype and reduces it
    modulo the active length, so the top bit marks "select along the other
    axis" without ever colliding with a valid index.
    """

    high_bit = 1 << (element_bits - 1)
    return [high_bit | ((2 * row + 2 * col) % n) for row in range(n) for col in range(n)]


def extra_permute_index_values(n: int) -> list[int]:
    """Byte index table of an extra-permute case, kept inside the active length."""

    return [(col + 1) % n for _row in range(n) for col in range(n)]


def small_matrix_inputs(n: int) -> tuple[list[int], list[int]]:
    """Row-major A/B squares for the small-matrix stimulus (values stay < 3)."""

    a_values = [(row + 2 * col + 1) % 3 for row in range(n) for col in range(n)]
    b_values = [(2 * row + col + 2) % 3 for row in range(n) for col in range(n)]
    return a_values, b_values


# ---------------------------------------------------------------------------
# Floating-point stimulus
# ---------------------------------------------------------------------------

# The exactly representable "1.0" encoding of each covered format.
SOFTFLOAT_ONE = {
    "AME_OCP_E4M3_DTYPE": 0x38,
    "AME_OCP_E5M2_DTYPE": 0x3C,
    "AME_FP16_DTYPE": 0x3C00,
    "AME_BF16_DTYPE": 0x3F80,
    "AME_FP32_DTYPE": 0x3F800000,
    "AME_FP64_DTYPE": 0x3FF0000000000000,
}

# Exponent bias, mantissa bits, and total width per covered format.  Used to
# encode the power-of-two matrix-product expectation for any N.
SOFTFLOAT_LAYOUTS = {
    "AME_OCP_E4M3_DTYPE": (7, 3, 8),
    "AME_OCP_E5M2_DTYPE": (15, 2, 8),
    "AME_FP16_DTYPE": (15, 10, 16),
    "AME_BF16_DTYPE": (127, 7, 16),
    "AME_FP32_DTYPE": (127, 23, 32),
    "AME_FP64_DTYPE": (1023, 52, 64),
}


def softfloat_max(dtype_name: str) -> int:
    """Largest finite encoding, the overflow stimulus."""

    return FLOAT_BOUNDARIES[dtype_name]["max"]


def softfloat_two(dtype_name: str) -> int:
    """Exactly representable 2.0, used as the overflow multiplier."""

    return FLOAT_BOUNDARIES[dtype_name]["two"]


@dataclass(frozen=True)
class FloatOverflowBoundary:
    """One overflow stimulus and the per-rounding-mode expected results."""

    output_negative: bool
    source_value: int
    per_mode: tuple[tuple[str, int], ...]


def float_overflow_boundaries(
    dtype_name: str,
    element_bits: int,
    *,
    negated_product: bool,
) -> tuple[FloatOverflowBoundary, ...]:
    """Precompute the sign x rounding-mode overflow sweep for one dtype.

    A negated variant inverts the product sign internally, so the source sign
    is selected to exercise both result signs through the same overflow path.
    """

    maximum = softfloat_max(dtype_name)
    boundaries = []
    for output_negative in (False, True):
        source_negative = output_negative ^ negated_product
        boundaries.append(
            FloatOverflowBoundary(
                output_negative=output_negative,
                source_value=signed(maximum, element_bits, source_negative),
                per_mode=tuple(
                    (
                        mode,
                        overflow_result(dtype_name, element_bits, mode, output_negative),
                    )
                    for mode in ROUNDING_MODE_NAMES
                ),
            )
        )
    return tuple(boundaries)


__all__ = [
    "FFLAGS_OF_NX",
    "ROUNDING_MODE_DTYPES",
    "ROUNDING_MODE_NAMES",
    "SOFTFLOAT_LAYOUTS",
    "SOFTFLOAT_ONE",
    "FloatOverflowBoundary",
    "float_overflow_boundaries",
    "int_bounds",
    "int_edge_value",
    "small_matrix_inputs",
    "softfloat_max",
    "softfloat_two",
]


# ---------------------------------------------------------------------------
# Integer elementwise stimulus ledger.
#
# The elementwise family's case inventory is declared here, in the module that
# also builds the operand values: this is the only declaration of that
# inventory.
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class IntegerInputCase:
    """One named, human-reviewable integer stimulus recipe.

    ``category`` is the data-provider key; ``description`` is part of the test
    specification and is emitted next to the instruction in the assembly.
    """

    name: str
    description: str
    category: str


SMALL_VALUES = IntegerInputCase(
    "small_values",
    "small signed/unsigned operands on the ordinary arithmetic path",
    "small_values",
)
BOUNDARIES = IntegerInputCase(
    "boundaries",
    "representable lower and upper bounds",
    "boundaries",
)
POWER_OF_TWO = IntegerInputCase(
    "power_of_two",
    "powers of two, including the element-width boundary",
    "power_of_two",
)
BIT_PATTERNS = IntegerInputCase(
    "bit_patterns",
    "alternating 0x55/0xaa bit pattern",
    "bit_patterns",
)
OVERFLOW_ADD = IntegerInputCase(
    "overflow_add",
    "maximum plus maximum: wrap or saturate",
    "overflow_add",
)
OVERFLOW_SUB = IntegerInputCase(
    "overflow_sub",
    "subtraction from the opposite extreme: wrap or saturate",
    "overflow_sub",
)
OVERFLOW_MUL = IntegerInputCase(
    "overflow_mul",
    "maximum times two: wrap or saturate",
    "overflow_mul",
)

#: The cases every integer instruction runs, before its overflow case.  The
#: elementwise base declares them, so an instruction with no overflow case of
#: its own still states the whole inventory it runs.
BASE_INTEGER_INPUT_CASES = (
    SMALL_VALUES,
    BOUNDARIES,
    POWER_OF_TWO,
    BIT_PATTERNS,
)


class IntegerInputKind(Enum):
    """Which operand pair drives the overflow case of one instruction."""

    ADD = "add"
    SUB_LTR = "sub_ltr"
    SUB_RTL = "sub_rtl"
    MUL = "mul"
    MULNEG = "mulneg"
    ABSDIFF = "absdiff"
    HDIFF_LTR = "hdiff_ltr"
    HDIFF_RTL = "hdiff_rtl"


@dataclass(frozen=True)
class IntegerOverflowCase(IntegerInputCase):
    """One instruction's overflow case: what it is called, and how it is built.

    ``kind`` selects the operand pair; ``downward`` says which bound ``dest``
    takes.  The pair does not determine the bound -- ``mmulsub`` multiplies yet
    lands on the floor -- so the instruction declares both, and the case name
    and description come from the emitted overflow case the kind belongs to.
    """

    kind: IntegerInputKind
    downward: bool


#: The overflow case each operand pair belongs to.
_OVERFLOW_CASE_BY_KIND: dict[IntegerInputKind, IntegerInputCase] = {
    IntegerInputKind.ADD: OVERFLOW_ADD,
    IntegerInputKind.SUB_LTR: OVERFLOW_SUB,
    IntegerInputKind.SUB_RTL: OVERFLOW_SUB,
    IntegerInputKind.MUL: OVERFLOW_MUL,
    IntegerInputKind.MULNEG: OVERFLOW_MUL,
    IntegerInputKind.ABSDIFF: OVERFLOW_SUB,
    IntegerInputKind.HDIFF_LTR: OVERFLOW_SUB,
    IntegerInputKind.HDIFF_RTL: OVERFLOW_SUB,
}

#: Which bound each operand pair puts first, and which it puts second.
_OVERFLOW_PAIRS: dict[IntegerInputKind, tuple[str, str]] = {
    IntegerInputKind.ADD: ("high", "high"),
    IntegerInputKind.SUB_LTR: ("low", "high"),
    IntegerInputKind.SUB_RTL: ("high", "low"),
    IntegerInputKind.MUL: ("high", "two"),
    IntegerInputKind.MULNEG: ("high", "two"),
    IntegerInputKind.ABSDIFF: ("high", "low"),
    IntegerInputKind.HDIFF_LTR: ("low", "high"),
    IntegerInputKind.HDIFF_RTL: ("high", "low"),
}


def overflow(kind: IntegerInputKind, *, downward: bool) -> IntegerOverflowCase:
    """The overflow case one instruction runs, under the name it is emitted as.

    Instructions compose their inventory from this and
    :data:`BASE_INTEGER_INPUT_CASES`, so an instruction file lists every input
    case it runs instead of selecting one out of a hidden shared set.
    """

    case = _OVERFLOW_CASE_BY_KIND[kind]
    return IntegerOverflowCase(
        case.name, case.description, case.category, kind, downward
    )


def _mask(element_bits: int) -> int:
    return (1 << element_bits) - 1


def _repeating(byte: int, element_bits: int) -> int:
    """An alternating byte pattern repeated to fill the element."""

    reps = max(1, element_bits // 8)
    return int(f"{byte & 0xFF:02x}" * reps, 16) & _mask(element_bits)


def _power_of_two_operands(signed: bool, element_bits: int) -> tuple[int, int]:
    """The largest representable power of two and the smallest one above 1."""

    if signed:
        top = 1 << max(0, element_bits - 2)
        low = 1 << max(0, (element_bits - 2) // 2)
    else:
        top = 1 << max(0, element_bits - 1)
        low = 2 if element_bits > 2 else 1
    if top == low:
        low = 1
    return top, low


def _overflow_pair(kind: IntegerInputKind, low: int, high: int) -> tuple[int, int]:
    """The operand pair that drives one overflow case past its bound."""

    bounds = {"low": low, "high": high, "two": 2}
    first, second = _OVERFLOW_PAIRS[kind]
    return bounds[first], bounds[second]


def int_operands_for_case(
    case: IntegerInputCase,
    dtype_name: str,
    element_bits: int,
) -> dict[str, int]:
    """The five operands (``a``/``b``/``scalar``/``dest``/``abs``) of one case.

    Every field comes from a named case; an unknown category, or an overflow
    case that is not an :class:`IntegerOverflowCase`, fails loudly instead of
    falling back to a generic operand set.
    """

    category = case.category
    signed = dtype_is_signed_int(dtype_name)
    low, high = int_bounds(element_bits, signed)

    if category == "small_values":
        a, b, scalar, dest, abs_input = 3, 5, 10, 7, (-3 if signed else 3)
    elif category == "boundaries":
        a, b, scalar, dest = high, low, high, low
        abs_input = low if signed else high
    elif category == "power_of_two":
        a, b = _power_of_two_operands(signed, element_bits)
        scalar, dest, abs_input = a, 1, a
    elif category == "bit_patterns":
        a = _repeating(0x55, element_bits)
        b = _repeating(0xAA, element_bits)
        scalar, dest, abs_input = a, b, a
    elif category.startswith("overflow"):
        if not isinstance(case, IntegerOverflowCase):
            raise ValueError(f"{case.name} is an overflow case without a pair")
        a, b = _overflow_pair(case.kind, low, high)
        scalar = a
        dest = low if case.downward else high
        abs_input = a
    else:
        raise ValueError(f"unknown integer value category: {category}")

    def decode(value: int) -> int:
        encoded = int(value) & _mask(element_bits)
        if signed and encoded >= (1 << (element_bits - 1)):
            return encoded - (1 << element_bits)
        return encoded

    return {
        "a": decode(a),
        "b": decode(b),
        "scalar": decode(scalar),
        "dest": decode(dest),
        "abs": decode(abs_input),
    }


def power_of_two_sequence(element_bits: int, slot_count: int) -> list[int]:
    """Encoded powers ``2^0 .. 2^(bits-1)``, capped at the square capacity.

    Includes the sign-bit position, so every element width sees the whole
    doubling chain -- including the value whose magnitude is not representable.
    """

    return [1 << shift for shift in range(min(element_bits, slot_count))]
