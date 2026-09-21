#!/usr/bin/env python3
#
# Copyright (c) Qualcomm Technologies, Inc. and/or its subsidiaries.
# SPDX-License-Identifier: BSD-3-Clause-Clear
#
"""Shared declaration of the matrix gather/scatter/reduce/prefix/zip family.

One matrix operation and the ``.data`` footer every one of them carries.  The
axis, the aggregate, the accumulate mode and the shape are not declared here:
:class:`MatrixAxis`, :class:`Reduction` and :class:`ScatterAccess` carry that
arithmetic, and each instruction hands the values it uses to its templates.
"""

from __future__ import annotations

from collections.abc import Sequence
from enum import StrEnum

from mmul_gen.instruction import Instruction


def _square_index(row: int, col: int, n: int) -> int:
    """Row-major flat position inside an ``n x n`` square."""

    return row * n + col


class MatrixAxis(StrEnum):
    """Which axis a matrix operation walks.

    The axis decides both what an element's expected value aggregates over and
    where an indexed access lands, so the members carry that arithmetic and the
    templates never have to name an instruction.
    """

    ROW = "row"
    COLUMN = "column"

    @property
    def by_row(self) -> bool:
        """Whether the operation walks rows rather than columns."""

        return self is MatrixAxis.ROW

    def line_indices(self, n: int, row: int, col: int) -> list[int]:
        """Flat positions of the whole line this element belongs to."""

        if self is MatrixAxis.ROW:
            return [_square_index(row, index, n) for index in range(n)]
        return [_square_index(index, col, n) for index in range(n)]

    def prefix_indices(self, n: int, row: int, col: int) -> list[int]:
        """Flat positions from the start of the line through this element."""

        if self is MatrixAxis.ROW:
            return [_square_index(row, index, n) for index in range(col + 1)]
        return [_square_index(index, col, n) for index in range(row + 1)]

    def result_index(self, n: int, row: int, col: int, target: int) -> int:
        """Where an indexed access aimed at ``target`` is stored."""

        if self is MatrixAxis.ROW:
            return _square_index(target, col, n)
        return _square_index(row, target, n)

    def varying(self, row: int, col: int) -> int:
        """The coordinate this axis lets vary."""

        return col if self is MatrixAxis.COLUMN else row

    def reduce_check_indices(self, n: int) -> tuple[int, int, int]:
        """The three elements a whole-line reduce samples."""

        if self is MatrixAxis.ROW:
            return (0, n - 1, n * n - 1)
        return (0, n, n - 1)

    def prefix_check_indices(self, n: int) -> tuple[int, int, int]:
        """The three elements a prefix operation samples."""

        if self is MatrixAxis.ROW:
            return (0, 3, n + 2)
        return (0, n, 2 * n + 3)

    def source_index(self, n: int, index: int, row: int, col: int) -> int:
        """Which element an indexed access aimed at ``index`` reads."""

        if self is MatrixAxis.ROW:
            return _square_index(index, col, n)
        return _square_index(row, index, n)


class Reduction(StrEnum):
    """How a reduce or prefix operation combines a line of elements."""

    SUM = "sum"
    MAX = "max"
    MIN = "min"

    def aggregate(self, values: "Sequence[int]") -> int:
        """Combine one line of already-interpreted element values."""

        if self is Reduction.SUM:
            return sum(values)
        if self is Reduction.MAX:
            return max(values)
        if self is Reduction.MIN:
            return min(values)
        raise ValueError(f"unsupported reduction: {self}")


class ScatterAccess(StrEnum):
    """How an indexed operation combines a source element into its target."""

    GATHER = "gather"
    ADD = "add"
    MAX = "max"

    def combine(self, current: int, value: int) -> int:
        """Fold one source value into the destination accumulator."""

        if self is ScatterAccess.ADD:
            return current + value
        if self is ScatterAccess.MAX:
            return max(current, value)
        raise ValueError(f"{self} does not accumulate; it is a gather")

    @property
    def accumulates(self) -> bool:
        """Whether the operation writes a destination seeded beforehand."""

        return self is not ScatterAccess.GATHER

    @property
    def by_max(self) -> bool:
        """Whether an accumulating access keeps the larger of the two values."""

        return self is ScatterAccess.MAX


class MatrixOpsInstruction(Instruction, family_base=True):
    """One matrix operation: an axis, how it combines elements, and its shape.

    Which axis an instruction walks, how it combines elements, and whether it
    accumulates or splits a stream are not declared here: they are the arguments
    of its templates.
    """

    always_emits_data = True


__all__ = [
    "MatrixAxis",
    "MatrixOpsInstruction",
    "Reduction",
    "ScatterAccess",
]
