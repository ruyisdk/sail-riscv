#!/usr/bin/env python3
#
# Copyright (c) Qualcomm Technologies, Inc. and/or its subsidiaries.
# SPDX-License-Identifier: BSD-3-Clause-Clear
#
"""Expected-value calculation for the integer matrix-multiply templates.

Every expectation is computed with exact Python integers and cross-checked
against a NumPy reference (see :mod:`numeric_reference`, which holds the
shared ISA arithmetic).  Ztt wrap or saturation is applied once, at writeback
to the destination dtype.
"""

from __future__ import annotations

from dataclasses import dataclass

from numeric_reference import IntegerDType, IntegerReferenceResult, integer_matmul

from mmul_gen.machine import dtype_is_signed_int
from mmul_gen.inputs import int_edge_value, small_matrix_inputs


# lhs * rhs * N stays inside the exact-integer range of every packed product
# dtype under test, so a mismatch is behaviour, not rounding.
PACKED_LHS_VALUE = 1
PACKED_RHS_VALUE = 2

# Seeds used by the independent-accumulator template, spaced so that a shared
# accumulator would be immediately visible in the stored result.
MULTI_ACC_SEED_STEP = 0x11


@dataclass(frozen=True)
class ProductFlags:
    """The per-instruction shape of a 2D matrix product."""

    subtract: bool = False
    transpose_lhs: bool = False
    transpose_rhs: bool = False


def integer_dtype(dtype_name: str, element_bits: int) -> IntegerDType:
    return IntegerDType(
        bits=element_bits,
        signed=dtype_is_signed_int(dtype_name),
        saturating="_SAT_" in dtype_name,
    )


def packed_compute_dtype(dtype_name: str, uds: int) -> str:
    """Whole-register destination dtype a packed source widens into."""

    stem = "INT" if dtype_is_signed_int(dtype_name) else "UINT"
    return f"AME_{stem}{uds}_DTYPE"


def _matmul(
    lhs,
    rhs,
    dtype: IntegerDType,
    *,
    n: int,
    flags: ProductFlags,
    accumulator=None,
) -> IntegerReferenceResult:
    return integer_matmul(
        lhs,
        rhs,
        n=n,
        lhs_dtype=dtype,
        rhs_dtype=dtype,
        dest_dtype=dtype,
        accumulator=accumulator,
        subtract_product=flags.subtract,
        transpose_lhs=flags.transpose_lhs,
        transpose_rhs=flags.transpose_rhs,
    )


def _uniform_result(result: IntegerReferenceResult, caller: str) -> int:
    expected = int(result.values[0, 0])
    if any(int(value) != expected for value in result.values.flat):
        raise AssertionError(f"{caller} produced non-uniform output")
    return expected


def uniform_ones_product(dtype_name: str, element_bits: int, n: int) -> int:
    """Expected value when both sources are all ones: the sum of N products."""

    nelem = n * n
    result = _matmul(
        [1] * nelem,
        [1] * nelem,
        integer_dtype(dtype_name, element_bits),
        n=n,
        flags=ProductFlags(),
    )
    return _uniform_result(result, f"{dtype_name} all-ones product")


def small_matrix_product(
    dtype_name: str,
    element_bits: int,
    n: int,
    flags: ProductFlags,
) -> list[int]:
    """Expected flat row-major result of the deterministic small-matrix stimulus."""

    a_values, b_values = small_matrix_inputs(n)
    dtype = integer_dtype(dtype_name, element_bits)
    result = _matmul(
        a_values,
        b_values,
        dtype,
        n=n,
        flags=flags,
        accumulator=[[0] * n for _ in range(n)],
    )
    return [int(value) for value in result.values.flat]


def packed_product(
    dtype_name: str,
    element_bits: int,
    uds: int,
    n: int,
    flags: ProductFlags,
) -> list[int]:
    """Expected flat result of one packed source square pair.

    The packed instruction folds every storage slot of a row into the single
    destination element, so the dot product spans ``(uds / element_bits) * N``
    products per element.
    """

    if element_bits >= uds:
        raise ValueError("packed matrix case requires a storage-only source")
    nelem = n * n
    pack_factor = uds // element_bits
    source_dtype = integer_dtype(dtype_name, element_bits)
    destination_dtype = integer_dtype(packed_compute_dtype(dtype_name, uds), uds)
    result = integer_matmul(
        [PACKED_LHS_VALUE] * (nelem * pack_factor),
        [PACKED_RHS_VALUE] * (nelem * pack_factor),
        n=n,
        lhs_dtype=source_dtype,
        rhs_dtype=source_dtype,
        dest_dtype=destination_dtype,
        accumulator=[[0] * n for _ in range(n)],
        subtract_product=flags.subtract,
        transpose_lhs=flags.transpose_lhs,
        transpose_rhs=flags.transpose_rhs,
    )
    return [int(value) for value in result.values.flat]


@dataclass(frozen=True)
class MixedSignednessProduct:
    """Two physically packed squares of different signedness and value."""

    lhs_dtype: str
    rhs_dtype: str
    dest_dtype: str
    lhs: tuple[int, ...]
    rhs: tuple[int, ...]
    expected: int


def mixed_signedness_product(uds: int, n: int, flags: ProductFlags) -> MixedSignednessProduct:
    """Build the mixed-sign/multiple-square stimulus and its expectation.

    The first square contributes ``(-1) * 2`` and the second ``2 * 3``, so a
    one-square implementation produces a different result from the expected
    ``4 * N`` and the physical second square becomes observable.
    """

    storage_bits = uds // 2
    lhs_dtype = f"AME_INT{storage_bits}_DTYPE"
    rhs_dtype = f"AME_UINT{storage_bits}_DTYPE"
    dest_dtype = f"AME_INT{uds}_DTYPE"
    nelem = n * n
    lhs = tuple([-1] * nelem + [2] * nelem)
    rhs = tuple([2] * nelem + [3] * nelem)
    result = integer_matmul(
        list(lhs),
        list(rhs),
        n=n,
        lhs_dtype=integer_dtype(lhs_dtype, storage_bits),
        rhs_dtype=integer_dtype(rhs_dtype, storage_bits),
        dest_dtype=integer_dtype(dest_dtype, uds),
        accumulator=[[0] * n for _ in range(n)],
        subtract_product=flags.subtract,
        transpose_lhs=flags.transpose_lhs,
        transpose_rhs=flags.transpose_rhs,
    )
    values = [int(value) for value in result.values.flat]
    if not values or any(value != values[0] for value in values):
        raise AssertionError("mixed multiple-square stimulus must be uniform")
    return MixedSignednessProduct(
        lhs_dtype=lhs_dtype,
        rhs_dtype=rhs_dtype,
        dest_dtype=dest_dtype,
        lhs=lhs,
        rhs=rhs,
        expected=values[0],
    )


def saturating_edge_product(
    dtype_name: str,
    element_bits: int,
    n: int,
    flags: ProductFlags,
) -> tuple[int, int]:
    """Expected saturated result and the stimulus edge value that produced it."""

    edge = int_edge_value(dtype_name, element_bits, "upper_bound")
    nelem = n * n
    result = _matmul(
        [1] * nelem,
        [edge] * nelem,
        integer_dtype(dtype_name, element_bits),
        n=n,
        flags=flags,
        accumulator=[[0] * n for _ in range(n)],
    )
    if not result.saturated:
        raise AssertionError(f"{dtype_name} saturating stimulus did not saturate")
    return _uniform_result(result, f"{dtype_name} saturating product"), edge


def seeded_ones_product(seed: int, dtype_name: str, element_bits: int, n: int) -> int:
    """Expected value of accumulating an all-ones product into a seeded square."""

    nelem = n * n
    result = _matmul(
        [1] * nelem,
        [1] * nelem,
        integer_dtype(dtype_name, element_bits),
        n=n,
        flags=ProductFlags(),
        accumulator=[[seed] * n for _ in range(n)],
    )
    return _uniform_result(result, f"{dtype_name} seeded product")


__all__ = [
    "MULTI_ACC_SEED_STEP",
    "PACKED_LHS_VALUE",
    "PACKED_RHS_VALUE",
    "IntegerDType",
    "IntegerReferenceResult",
    "MixedSignednessProduct",
    "ProductFlags",
    "integer_dtype",
    "mixed_signedness_product",
    "packed_compute_dtype",
    "packed_product",
    "saturating_edge_product",
    "seeded_ones_product",
    "small_matrix_product",
    "uniform_ones_product",
]
