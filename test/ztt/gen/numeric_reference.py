#!/usr/bin/env python3
#
# Copyright (c) Qualcomm Technologies, Inc. and/or its subsidiaries.
# SPDX-License-Identifier: BSD-3-Clause-Clear
#
# Independent numeric reference calculations for generated Ztt tests.

from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

try:
    import numpy as np
except ModuleNotFoundError as exc:
    raise ModuleNotFoundError(
        "Ztt test generation requires NumPy; install test/ztt/gen/requirements.txt "
        "in the Python environment used by CMake"
    ) from exc


IntegerValues = (
    Sequence[int]
    | Sequence[Sequence[int]]
    | Sequence[Sequence[Sequence[int]]]
    | np.ndarray
)


@dataclass(frozen=True)
class IntegerDType:
    bits: int
    signed: bool
    saturating: bool = False

    def __post_init__(self) -> None:
        if self.bits <= 0:
            raise ValueError("integer element width must be positive")

    @property
    def bounds(self) -> tuple[int, int]:
        if self.signed:
            return (-(1 << (self.bits - 1)), (1 << (self.bits - 1)) - 1)
        return (0, (1 << self.bits) - 1)

    def decode(self, value: int) -> int:
        """Interpret a value using this datatype's architectural bit width."""
        modulus = 1 << self.bits
        encoded = int(value) % modulus
        if self.signed and encoded >= (1 << (self.bits - 1)):
            return encoded - modulus
        return encoded

    def convert_result(self, value: int) -> tuple[int, bool]:
        """Convert an exact intermediate and report whether it saturated."""
        exact = int(value)
        if self.saturating:
            minimum, maximum = self.bounds
            converted = min(max(exact, minimum), maximum)
            return converted, converted != exact
        return self.decode(exact), False


@dataclass(frozen=True)
class IntegerReferenceResult:
    values: np.ndarray
    saturated: bool


def _round_rnu_half(value: int) -> int:
    """Round an exact integer divided by two using round-to-nearest-up."""

    return value // 2 + (value % 2 != 0)


def integer_elementwise_binary(
    mnemonic: str,
    lhs: int,
    rhs: int,
    *,
    dtype: IntegerDType,
) -> int:
    """Evaluate one integer binary element using architectural decoding."""

    mask = (1 << dtype.bits) - 1
    lhs_raw = int(lhs) & mask
    rhs_raw = int(rhs) & mask
    lhs_value = dtype.decode(lhs)
    rhs_value = dtype.decode(rhs)

    if mnemonic in {"madd.ew", "madd.ew.x"}:
        exact = lhs_value + rhs_value
    elif mnemonic == "msub.ew" or mnemonic == "msub.ew.x":
        # Manual: both forms subtract the first operand from ms2, i.e.
        # msub.ew -> B[i] - A[i] and msub.ew.x -> B[i] - c.
        exact = rhs_value - lhs_value
    elif mnemonic in {"mand.ew", "mand.ew.x"}:
        exact = lhs_raw & rhs_raw
    elif mnemonic in {"mandnot.ew", "mandnot.ew.x"}:
        exact = lhs_raw & ~rhs_raw
    elif mnemonic in {"mor.ew", "mor.ew.x"}:
        exact = lhs_raw | rhs_raw
    elif mnemonic in {"mornot.ew", "mornot.ew.x"}:
        exact = lhs_raw | ~rhs_raw
    elif mnemonic in {"mxor.ew", "mxor.ew.x"}:
        exact = lhs_raw ^ rhs_raw
    elif mnemonic in {"mmax.ew", "mmax.ew.x"}:
        exact = max(lhs_value, rhs_value)
    elif mnemonic in {"mmin.ew", "mmin.ew.x"}:
        exact = min(lhs_value, rhs_value)
    elif mnemonic in {"mabsdiff.ew", "mabsdiff.ew.x"}:
        exact = abs(lhs_value - rhs_value)
    elif mnemonic == "mhdiff.ew" or mnemonic == "mhdiff.ew.x":
        # Manual: D[i] = (B[i] - A[i]) / 2 and D[i] = (B[i] - c) / 2.
        exact = _round_rnu_half(rhs_value - lhs_value)
    elif mnemonic in {"mmean.ew", "mmean.ew.x"}:
        exact = _round_rnu_half(lhs_value + rhs_value)
    elif mnemonic in {"mmul.ew", "mmul.ew.x"}:
        exact = lhs_value * rhs_value
    elif mnemonic in {"mmulneg.ew", "mmulneg.ew.x"}:
        exact = -(lhs_value * rhs_value)
    elif mnemonic in {"mcmpge.ew", "mcmpge.ew.x"}:
        exact = mask if lhs_value >= rhs_value else 0
    elif mnemonic in {"mcmplt.ew", "mcmplt.ew.x"}:
        exact = mask if lhs_value < rhs_value else 0
    elif mnemonic == "mselge.ew":
        # Manual: D[i] = (A[i] >= 0) ? B[i] : 0 (numeric compare, not MSB).
        exact = rhs_raw if lhs_value >= 0 else 0
    elif mnemonic == "msellt.ew":
        # Manual: D[i] = (A[i] < 0) ? B[i] : 0 (numeric compare, not MSB).
        exact = rhs_raw if lhs_value < 0 else 0
    else:
        raise ValueError(f"unsupported integer binary instruction: {mnemonic}")

    return dtype.convert_result(exact)[0]


def integer_elementwise_ternary(
    mnemonic: str,
    dest: int,
    lhs: int,
    rhs: int,
    *,
    dtype: IntegerDType,
) -> int:
    """Evaluate one integer ternary element using architectural decoding."""

    mask = (1 << dtype.bits) - 1
    dest_value = dtype.decode(dest)
    lhs_value = dtype.decode(lhs)
    rhs_value = dtype.decode(rhs)
    # Manual cmov/sel predicate: numeric comparison of ms1 against zero,
    # not the raw sign bit.  Unsigned elements are never negative.
    lhs_negative = lhs_value < 0

    if mnemonic in {"mmulacc.ew", "mmulacc.ew.x"}:
        exact = dest_value + lhs_value * rhs_value
    elif mnemonic in {"mmulaccneg.ew", "mmulaccneg.ew.x"}:
        exact = dest_value - lhs_value * rhs_value
    elif mnemonic in {"mmuladd.ew", "mmuladd.ew.x"}:
        exact = lhs_value + rhs_value * dest_value
    elif mnemonic in {"mmulsub.ew", "mmulsub.ew.x"}:
        exact = lhs_value - rhs_value * dest_value
    elif mnemonic == "mcmovge.ew":
        exact = rhs_value if not lhs_negative else dest_value
    elif mnemonic == "mcmovlt.ew":
        exact = rhs_value if lhs_negative else dest_value
    else:
        raise ValueError(f"unsupported integer ternary instruction: {mnemonic}")

    return dtype.convert_result(exact)[0]


def _square_stack(
    values: IntegerValues,
    *,
    n: int,
    dtype: IntegerDType,
    name: str,
) -> np.ndarray:
    if n <= 0:
        raise ValueError("matrix dimension must be positive")

    array = np.asarray(values, dtype=object)
    if array.ndim == 1:
        square_elements = n * n
        if array.size == 0 or array.size % square_elements != 0:
            raise ValueError(f"{name} must contain one or more complete {n}x{n} squares")
        array = array.reshape((-1, n, n))
    elif array.ndim == 2:
        if array.shape != (n, n):
            raise ValueError(f"{name} must have shape ({n}, {n})")
        array = array.reshape((1, n, n))
    elif array.ndim == 3:
        if array.shape[0] == 0 or array.shape[1:] != (n, n):
            raise ValueError(f"{name} must have shape (N_sq, {n}, {n})")
    else:
        raise ValueError(f"{name} must be flat, 2D, or 3D")

    decode = np.frompyfunc(dtype.decode, 1, 1)
    return decode(array)


def _destination_square(
    values: IntegerValues,
    *,
    n: int,
    dtype: IntegerDType,
) -> np.ndarray:
    square = _square_stack(values, n=n, dtype=dtype, name="accumulator")
    if square.shape[0] != 1:
        raise ValueError("accumulator must contain exactly one square")
    return square[0]


def _numpy_exact_matmul(
    lhs_squares: np.ndarray,
    rhs_squares: np.ndarray,
    accumulator: np.ndarray | None,
    *,
    subtract_product: bool,
    transpose_lhs: bool,
    transpose_rhs: bool,
) -> np.ndarray:
    if transpose_lhs:
        lhs_squares = lhs_squares.transpose((0, 2, 1))
    if transpose_rhs:
        rhs_squares = rhs_squares.transpose((0, 2, 1))

    products = np.matmul(lhs_squares, rhs_squares)
    exact = np.sum(products, axis=0, dtype=object)
    if subtract_product:
        exact = -exact
    if accumulator is not None:
        exact = accumulator + exact
    return exact


def _python_exact_matmul(
    lhs_squares: np.ndarray,
    rhs_squares: np.ndarray,
    accumulator: np.ndarray | None,
    *,
    subtract_product: bool,
    transpose_lhs: bool,
    transpose_rhs: bool,
) -> np.ndarray:
    lhs = lhs_squares.tolist()
    rhs = rhs_squares.tolist()
    initial = None if accumulator is None else accumulator.tolist()
    nsq, n, _ = lhs_squares.shape
    exact = [[0 for _ in range(n)] for _ in range(n)]

    for row in range(n):
        for col in range(n):
            total = 0 if initial is None else initial[row][col]
            for square in range(nsq):
                for inner in range(n):
                    lhs_value = (
                        lhs[square][inner][row]
                        if transpose_lhs
                        else lhs[square][row][inner]
                    )
                    rhs_value = (
                        rhs[square][col][inner]
                        if transpose_rhs
                        else rhs[square][inner][col]
                    )
                    product = lhs_value * rhs_value
                    total = total - product if subtract_product else total + product
            exact[row][col] = total

    return np.asarray(exact, dtype=object)


def integer_matmul(
    lhs: IntegerValues,
    rhs: IntegerValues,
    *,
    n: int,
    lhs_dtype: IntegerDType,
    rhs_dtype: IntegerDType,
    dest_dtype: IntegerDType,
    accumulator: IntegerValues | None = None,
    subtract_product: bool = False,
    transpose_lhs: bool = False,
    transpose_rhs: bool = False,
) -> IntegerReferenceResult:
    """Compute an integer Ztt 2D matrix operation with exact intermediates.

    Flat inputs may contain multiple consecutive squares. Products from each
    square pair are accumulated before the single destination conversion. The
    object arrays deliberately use Python integers so NumPy cannot overflow an
    intermediate before Ztt wrap or saturation semantics are applied. NumPy
    and ordinary Python-loop implementations must agree before a result is
    returned to the assembly generator.
    """
    lhs_squares = _square_stack(lhs, n=n, dtype=lhs_dtype, name="lhs")
    rhs_squares = _square_stack(rhs, n=n, dtype=rhs_dtype, name="rhs")
    if lhs_squares.shape[0] != rhs_squares.shape[0]:
        raise ValueError("lhs and rhs must contain the same number of squares")

    accumulator_square = (
        None
        if accumulator is None
        else _destination_square(accumulator, n=n, dtype=dest_dtype)
    )
    calculation_options = {
        "subtract_product": subtract_product,
        "transpose_lhs": transpose_lhs,
        "transpose_rhs": transpose_rhs,
    }
    numpy_exact = _numpy_exact_matmul(
        lhs_squares,
        rhs_squares,
        accumulator_square,
        **calculation_options,
    )
    python_exact = _python_exact_matmul(
        lhs_squares,
        rhs_squares,
        accumulator_square,
        **calculation_options,
    )
    if not np.array_equal(numpy_exact, python_exact):
        mismatch = np.argwhere(np.not_equal(numpy_exact, python_exact))[0]
        row, col = (int(index) for index in mismatch)
        raise AssertionError(
            "NumPy/Python integer matrix reference mismatch at "
            f"[{row}, {col}]: {numpy_exact[row, col]} != {python_exact[row, col]}"
        )

    converted = np.empty((n, n), dtype=object)
    saturated = False
    for index, value in np.ndenumerate(numpy_exact):
        converted[index], element_saturated = dest_dtype.convert_result(value)
        saturated = saturated or element_saturated

    return IntegerReferenceResult(values=converted, saturated=saturated)


__all__ = [
    "IntegerDType",
    "IntegerReferenceResult",
    "integer_elementwise_binary",
    "integer_elementwise_ternary",
    "integer_matmul",
]
