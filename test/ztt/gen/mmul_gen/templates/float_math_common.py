#!/usr/bin/env python3
#
# Copyright (c) Qualcomm Technologies, Inc. and/or its subsidiaries.
# SPDX-License-Identifier: BSD-3-Clause-Clear
#
"""Semantics of one floating-point unary math instruction.

Every instruction of the family is *one* member of :class:`MathOperation`, and
the members carry the operation's own behaviour: which stimulus is nominal, which
boundary scenarios have an architecturally precise result and flag set, and -- for
the transcendentals -- which host libm function the simulators themselves call.

That keeps ten instructions on ten declarations and three templates, with no
`if mnemonic == ...` anywhere.

The expected values come from :mod:`mmul_gen.fp_semantics` (bit-exact tables
of the boundary encodings) and from the host libm for the
transcendental single-value cases: both simulators widen a narrow format to f32,
call the *host* `cosf`/`sinf`/`tanhf`, and round back, so the baked expectation
replicates that path exactly and cross-checks it against a 30-digit mpmath
reference inside the documented 2 ulp budget.
"""

from __future__ import annotations

DOC_ZH = """\
一条浮点一元数学指令的语义。

该家族的每条指令都是 :class:`MathOperation` 的一个成员，成员携带运算自身的行为：哪个激励是标称的、哪些边界场景有架构精确的结果与标志集合、以及（对超越函数）模拟器自己调用哪个主机 libm 函数。

这样十条指令就落在十份声明与三个模板上，任何地方都没有 ``if mnemonic == ...``。

期望值来自 :mod:`mmul_gen.fp_semantics`（从旧参考模块移植的位精确表）以及超越函数单值用例的主机 libm：两个模拟器都把窄格式扩展为 f32，调用*主机*的 ``cosf``/``sinf``/``tanhf``，再舍入回来，因此固化的期望精确复现该路径，并在文档化的 2 ulp 预算内与 30 位精度的 mpmath 参考交叉校验。
"""

import ctypes
import struct
from collections.abc import Sequence
from dataclasses import dataclass
from enum import StrEnum

import ml_dtypes
import mpmath as mp
import numpy as np

from fp_semantics import (
    FFLAGS_NX,
    FFLAGS_NV,
    FFLAGS_OF_NX,
    FLOAT_BOUNDARIES,
    ROUNDING_MODE_NAMES,
    SQRT_TWO_RESULTS,
    overflow_result,
    pole_result,
    signed,
)


#: Flags raised by an integer-valued rounding result on an inexact input.
ROUNDING_FLAGS = FFLAGS_NX
#: Flags raised by an infinite input to cos/sin (invalid operation).
INVALID_FLAGS = FFLAGS_NV
#: Flag budget the host libm stage is allowed to differ from the reference by.
LIBRARY_ULP_BUDGET = 2
#: mpmath precision used to cross-check the host libm.
REFERENCE_DECIMAL_PRECISION = 30
#: Datatype descriptors and the numpy/ml_dtypes types the libm path narrows to.
NUMERIC_DTYPES = {
    "AME_FP16_DTYPE": np.float16,
    "AME_BF16_DTYPE": ml_dtypes.bfloat16,
    "AME_FP32_DTYPE": np.float32,
    "AME_FP64_DTYPE": None,
    "AME_OCP_E4M3_DTYPE": ml_dtypes.float8_e4m3fn,
    "AME_OCP_E5M2_DTYPE": ml_dtypes.float8_e5m2,
}


@dataclass(frozen=True)
class BoundaryCase:
    """One datatype-specific boundary scenario with a precise outcome."""

    scenario: str
    source: int
    expected: int
    flags: int
    rounding_mode: str


class MathOperation(StrEnum):
    """One floating-point unary operation, with its own test semantics."""

    FLOOR = "floor"
    NEAREST = "nearest"
    CEIL = "ceil"
    TRUNC = "trunc"
    RECIPROCAL = "reciprocal"
    RECIPROCAL_SQRT = "reciprocal_sqrt"
    SQRT = "sqrt"
    COS = "cos"
    SIN = "sin"
    TANH = "tanh"

    @property
    def is_transcendental(self) -> bool:
        """Whether the operation is defined by the host libm, not a table."""

        return self in {MathOperation.COS, MathOperation.SIN, MathOperation.TANH}

    @property
    def rounds_to_integer(self) -> bool:
        """Whether the operation rounds to an integral value."""

        return self in {
            MathOperation.FLOOR,
            MathOperation.NEAREST,
            MathOperation.CEIL,
            MathOperation.TRUNC,
        }

    def nominal_values(
        self, boundaries: dict[str, int], element_count: int
    ) -> tuple[list[int], list[int]]:
        """The stimulus and expected square of one nominal case."""

        if self is MathOperation.SQRT:
            return [boundaries["four"]] * element_count, [boundaries["two"]] * element_count
        if self is MathOperation.RECIPROCAL:
            return [boundaries["two"]] * element_count, [boundaries["half"]] * element_count
        if self is MathOperation.RECIPROCAL_SQRT:
            return (
                [boundaries["four"]] * element_count,
                [boundaries["half"]] * element_count,
            )
        if not self.rounds_to_integer:
            raise ValueError(f"{self} has no table-driven nominal case")
        positive, negative = {
            MathOperation.FLOOR: ("one", "neg_two"),
            MathOperation.NEAREST: ("two", "neg_two"),
            MathOperation.CEIL: ("two", "neg_one"),
            MathOperation.TRUNC: ("one", "neg_one"),
        }[self]
        source = [
            boundaries["one_half"] if index % 2 == 0 else boundaries["neg_one_half"]
            for index in range(element_count)
        ]
        expected = [
            boundaries[positive] if index % 2 == 0 else boundaries[negative]
            for index in range(element_count)
        ]
        return source, expected

    def zero_pole_cases(
        self, dtype_name: str, element_bits: int, boundaries: dict[str, int]
    ) -> list[BoundaryCase]:
        """Both zero poles, where the result sign follows the sign of the zero."""

        cases: list[BoundaryCase] = []
        for negative in (False, True):
            expected, flags = pole_result(dtype_name, element_bits, negative)
            cases.extend(
                BoundaryCase(
                    scenario=f"{'negative' if negative else 'positive'}_zero_pole_{mode}",
                    source=signed(boundaries["zero"], element_bits, negative),
                    expected=expected,
                    flags=flags,
                    rounding_mode=mode,
                )
                for mode in ROUNDING_MODE_NAMES
            )
        return cases

    def negative_finite_invalid_cases(
        self, element_bits: int, boundaries: dict[str, int]
    ) -> list[BoundaryCase]:
        """A negative finite input to a function defined on non-negative values."""

        return [
            BoundaryCase(
                scenario=f"negative_finite_invalid_{mode}",
                source=signed(boundaries["one"], element_bits, True),
                expected=boundaries["qnan"],
                flags=FFLAGS_NV,
                rounding_mode=mode,
            )
            for mode in ROUNDING_MODE_NAMES
        ]

    def boundary_cases(
        self, dtype_name: str, element_bits: int, boundaries: dict[str, int]
    ) -> list[BoundaryCase]:
        """Every boundary scenario with an exact result and flag set.

        The scenarios are shaped rather than spelled out per operation: the zero
        poles and the negative-finite-invalid input are shared, and each
        operation adds what only it has.
        """

        if self is MathOperation.RECIPROCAL:
            cases = self.zero_pole_cases(dtype_name, element_bits, boundaries)
            for negative in (False, True):
                cases.extend(
                    BoundaryCase(
                        scenario=f"{'negative' if negative else 'positive'}_finite_overflow_{mode}",
                        source=signed(boundaries["min_subnormal"], element_bits, negative),
                        expected=overflow_result(dtype_name, element_bits, mode, negative),
                        flags=FFLAGS_OF_NX,
                        rounding_mode=mode,
                    )
                    for mode in ROUNDING_MODE_NAMES
                )
            return cases
        if self is MathOperation.RECIPROCAL_SQRT:
            return [
                *self.zero_pole_cases(dtype_name, element_bits, boundaries),
                *self.negative_finite_invalid_cases(element_bits, boundaries),
            ]
        if self is MathOperation.SQRT:
            return [
                *self.negative_finite_invalid_cases(element_bits, boundaries),
                *(
                    BoundaryCase(
                        scenario=f"sqrt_two_inexact_{mode}",
                        source=boundaries["two"],
                        expected=SQRT_TWO_RESULTS[dtype_name][mode],
                        flags=FFLAGS_NX,
                        rounding_mode=mode,
                    )
                    for mode in ROUNDING_MODE_NAMES
                ),
            ]
        if self.rounds_to_integer:
            fixed = {
                MathOperation.FLOOR: boundaries["one"],
                MathOperation.NEAREST: boundaries["two"],
                MathOperation.CEIL: boundaries["two"],
                MathOperation.TRUNC: boundaries["one"],
            }[self]
            return [
                BoundaryCase(
                    scenario=f"fixed_rounding_inexact_{mode}",
                    source=boundaries["one_half"],
                    expected=fixed,
                    flags=FFLAGS_NX,
                    rounding_mode=mode,
                )
                for mode in ROUNDING_MODE_NAMES
            ]
        raise ValueError(f"{self} has no boundary scenarios")

    @property
    def zero_expectations(self) -> tuple[str, str]:
        """Boundary keys an exact zero input maps to (``+0`` then ``-0``)."""

        return {
            MathOperation.COS: ("one", "one"),
            MathOperation.SIN: ("zero", "neg_zero"),
            MathOperation.TANH: ("zero", "neg_zero"),
        }[self]

    @property
    def library_names(self) -> tuple[str, str]:
        """Host libm function names for the f32 and f64 paths."""

        return {
            MathOperation.COS: ("cosf", "cos"),
            MathOperation.SIN: ("sinf", "sin"),
            MathOperation.TANH: ("tanhf", "tanh"),
        }[self]

    def infinite_expectation(
        self, boundaries: dict[str, int], negative: bool
    ) -> tuple[int, int]:
        """Result and flags of an infinite input (``(bits, flags)``)."""

        if self is MathOperation.TANH:
            # tanh saturates at +-1 and raises nothing.
            return boundaries["neg_one" if negative else "one"], 0
        # cos/sin of an infinity is an invalid operation: default NaN + NV.
        return boundaries["qnan"], INVALID_FLAGS


def library_float32(function: str, value: float) -> float:
    """Host libm single-precision result; the function both simulators call."""

    libm = ctypes.CDLL("libm.so.6")
    call = getattr(libm, function)
    call.argtypes = [ctypes.c_float]
    call.restype = ctypes.c_float
    return float(call(ctypes.c_float(value)))


def library_float64(function: str, value: float) -> float:
    """Host libm double-precision result."""

    libm = ctypes.CDLL("libm.so.6")
    call = getattr(libm, function)
    call.argtypes = [ctypes.c_double]
    call.restype = ctypes.c_double
    return float(call(ctypes.c_double(value)))


def ulp_distance_32(first: float, second: float) -> int:
    """Bit distance of two same-sign finite single-precision floats."""

    (first_bits,) = struct.unpack("I", struct.pack("f", first))
    (second_bits,) = struct.unpack("I", struct.pack("f", second))
    return abs(first_bits - second_bits)


def ulp_distance_64(first: float, second: float) -> int:
    """Bit distance of two same-sign finite double-precision floats."""

    (first_bits,) = struct.unpack("Q", struct.pack("d", first))
    (second_bits,) = struct.unpack("Q", struct.pack("d", second))
    return abs(first_bits - second_bits)


def transcendental_numeric_case(
    operation: MathOperation, dtype_name: str, element_bits: int, boundaries: dict[str, int]
) -> tuple[int, int]:
    """Expected bits and flags of the ``1.0`` numeric case, or ``(0, -1)``.

    The simulators widen a narrow format to f32, call the host libm, and round
    the result back with RNE.  FP32 calls it natively (no narrowing, no NX);
    FP64 uses the double entry point.  The f32 stage is cross-checked against a
    30-digit mpmath reference so a host libm drift fails here, not in a test.
    """

    if dtype_name not in NUMERIC_DTYPES:
        return 0, -1
    single, double = operation.library_names
    float32_result = library_float32(single, 1.0)
    mp.mp.dps = REFERENCE_DECIMAL_PRECISION
    reference = float(
        {
            MathOperation.COS: mp.cos,
            MathOperation.SIN: mp.sin,
            MathOperation.TANH: mp.tanh,
        }[operation](mp.mpf(1.0))
    )
    ulp = ulp_distance_32(float32_result, reference)
    if ulp > LIBRARY_ULP_BUDGET:
        raise AssertionError(
            f"{operation} {dtype_name}: host libm differs from the mpmath "
            f"reference by more than the documented {LIBRARY_ULP_BUDGET} ulp ({ulp})"
        )
    if dtype_name == "AME_FP64_DTYPE":
        expected = library_float64(double, 1.0)
        ulp = ulp_distance_64(expected, reference)
        if ulp > LIBRARY_ULP_BUDGET:
            raise AssertionError(
                f"{operation} {dtype_name}: host libm f64 stage ulp {ulp} exceeds "
                f"the documented {LIBRARY_ULP_BUDGET}"
            )
        (expected_bits,) = struct.unpack("Q", struct.pack("d", expected))
        return expected_bits, 0
    if dtype_name == "AME_FP32_DTYPE":
        # f32 computes natively in libm: no narrowing stage, therefore no NX.
        (expected_bits,) = struct.unpack("I", struct.pack("f", float32_result))
        return expected_bits, 0
    narrowed = np.array([float32_result], dtype=np.float32).astype(NUMERIC_DTYPES[dtype_name])
    view = np.uint16 if element_bits == 16 else np.uint8
    # Narrowing an f32 to a narrow format is generally inexact and both
    # simulators raise NX for it.
    return int(narrowed.view(view)[0]), FFLAGS_NX


def transcendental_cases(
    operation: MathOperation, dtype_name: str, element_bits: int
) -> list[tuple[str, int, int, int]]:
    """The exact-semantics scenarios of a transcendental instruction."""

    boundaries = FLOAT_BOUNDARIES[dtype_name]
    positive_zero, negative_zero = operation.zero_expectations
    cases: list[tuple[str, int, int, int]] = [
        ("zero", boundaries["zero"], boundaries[positive_zero], 0),
        ("neg_zero", boundaries["neg_zero"], boundaries[negative_zero], 0),
        ("qnan", boundaries["qnan"], boundaries["qnan"], 0),
    ]
    if boundaries["inf"] != boundaries["finite"]:
        for name, negative in (("inf", False), ("neg_inf", True)):
            expected, flags = operation.infinite_expectation(boundaries, negative)
            cases.append((name, boundaries["neg_inf" if negative else "inf"], expected, flags))
    expected, flags = transcendental_numeric_case(operation, dtype_name, element_bits, boundaries)
    if flags >= 0:
        cases.append(("one", boundaries["one"], expected, flags))
    return cases


def checked_indices(values: Sequence[int]) -> list[int]:
    """The sampled element positions of one float-math square."""

    return sorted({0, 1, 2, len(values) - 1})


__all__ = [
    "INVALID_FLAGS",
    "LIBRARY_ULP_BUDGET",
    "NUMERIC_DTYPES",
    "REFERENCE_DECIMAL_PRECISION",
    "ROUNDING_FLAGS",
    "BoundaryCase",
    "MathOperation",
    "checked_indices",
    "library_float32",
    "library_float64",
    "transcendental_cases",
    "transcendental_numeric_case",
    "ulp_distance_32",
    "ulp_distance_64",
]
