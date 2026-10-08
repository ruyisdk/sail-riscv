#!/usr/bin/env python3
#
# Copyright (c) Qualcomm Technologies, Inc. and/or its subsidiaries.
# SPDX-License-Identifier: BSD-3-Clause-Clear
#
"""The per-step saturated fold order of a reduce or prefix sum.

The manual requires each step of a reduction or prefix to round and saturate in
the destination domain *before* it feeds the next step.  A source whose first
three elements are ``127, 1, -128`` separates that rule from an exact
accumulation clamped once at the end:

* per-step:  ``127 -> sat_add(127, 1) = 127 -> sat_add(127, -128) = -1``
* exact then clamp: ``127 + 1 - 128 = 0``

So the reduced line ends at ``-1`` rather than ``0``, the running prefix reads
``127, 127, -1`` rather than ``127, 127, 0``, and both must raise ``amexsat``.
The all-maximum square the existing saturating template uses cannot tell the two
apart, which is why this recipe folds a saturating *sequence* instead.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import TYPE_CHECKING

from mmul_gen.asm import check_dst_element_lines
from mmul_gen.machine import SATURATING_INTEGER, MachineConfig, dtype_stem
from mmul_gen.registers import choose_m_group_base
from mmul_gen.templates.base import Case, CaseOutput, Template, domain_index
from mmul_gen.templates.matrix_ops_common import destination_lines, source_data_lines

if TYPE_CHECKING:
    from mmul_gen.instruction import Instruction
    from mmul_gen.instructions.matrix_ops.base import MatrixAxis
    from mmul_gen.machine import DType


#: The saturation order that separates per-step feedback from a final clamp.
FOLD_SEQUENCE = (127, 1, -128)
#: The one datatype this recipe is stated in.
FOLD_DTYPE_NAME = "AME_INT8_SAT_DTYPE"
#: Preferred destination base, clear of the source and of the ramp cases.
PREFERRED_DESTINATION_BASE = 8


def _saturated_add(left: int, right: int, lower: int, upper: int) -> int:
    """One fold step: add, then clamp into the destination domain."""

    return min(upper, max(lower, left + right))


def fold_values(machine: MachineConfig, axis: "MatrixAxis") -> list[int]:
    """A square whose first line (row or column) is the fold sequence."""

    n = machine.n
    values = [0] * (n * n)
    for row in range(n):
        for col in range(n):
            along = col if axis.by_row else row
            if along < len(FOLD_SEQUENCE):
                values[row * n + col] = FOLD_SEQUENCE[along]
    return values


def fold_expected(dtype: DType) -> tuple[list[int], int]:
    """The running prefix and the final reduced value under per-step feedback."""

    lower = -(1 << (dtype.bits - 1))
    upper = (1 << (dtype.bits - 1)) - 1
    prefix: list[int] = []
    running = 0
    for position, value in enumerate(FOLD_SEQUENCE):
        running = value if position == 0 else _saturated_add(running, value, lower, upper)
        prefix.append(running)
    return prefix, prefix[-1]


class ReducePrefixSaturatingFold(Template):
    """Fold a saturating sequence one step at a time and check the boundary."""

    name = "saturating_fold_feedback"
    dtypes = SATURATING_INTEGER

    def __init__(self, axis: "MatrixAxis", prefix: bool = False) -> None:
        """``axis`` is the line each case walks and ``prefix`` its checked shape."""

        self.axis = axis
        self.prefix = prefix

    def fits(
        self,
        machine: MachineConfig,
        instruction: Instruction,
        dtype: DType | None = None,
    ) -> bool:
        if dtype is None:
            raise ValueError("a fold case is always formed from a datatype")
        # Three elements are needed to reach the saturation boundary, and the
        # source and destination groups must both fit the register file.
        return (
            dtype.name == FOLD_DTYPE_NAME
            and machine.n >= len(FOLD_SEQUENCE)
            and 2 * machine.nregs(dtype.bits) <= machine.num_m_regs
        )

    def build(
        self, machine: MachineConfig, instruction: Instruction, dtype: DType | None
    ) -> Sequence[Case]:
        if dtype is None:
            raise ValueError("a fold case is always formed from a datatype")
        return [Case(number=0, dtype=dtype)]

    def render(
        self,
        machine: MachineConfig,
        instruction: Instruction,
        case: Case,
        out: CaseOutput,
    ) -> None:
        if case.dtype is None:
            raise ValueError("a fold case is always formed from a datatype")
        dtype = case.dtype
        index = domain_index(machine, dtype, self.dtypes)
        label = f"fold{index}_{dtype_stem(dtype.name)}_"
        source = f"{label}src_square"
        destination = f"{label}dst_square"
        destination_reg = choose_m_group_base(
            machine.num_m_regs, dtype.bits, machine.uds, PREFERRED_DESTINATION_BASE
        )
        prefix_values, reduced = fold_expected(dtype)

        out.text.extend(
            [
                f"    # case {index}: {instruction.name} {dtype.name} per-step "
                "saturated fold",
                f"    li      t0, {dtype.name}",
                "    msettyp m0, t0",
                f"    msettyp m{destination_reg}, t0",
                "    li      t6, 0",
                "    csrw    amexsat, t6",
                "",
                f"    la      t1, {source}",
                "    mls.rm     m0, t1",
                f"    {instruction.name} m{destination_reg}, m0",
                f"    la      t3, {destination}",
                f"    mss.rm     m{destination_reg}, t3",
                "    csrr    t5, amexsat",
                "    EXPECT  t5, 1",
            ]
        )
        for position, expected in self._checked_elements(machine, prefix_values, reduced):
            out.text.extend(
                check_dst_element_lines(expected, dtype.bits, position, destination)
            )
        out.data.extend(source_data_lines(source, fold_values(machine, self.axis), dtype.bits, machine))
        out.data.extend(destination_lines(destination, dtype.bits, machine))
        out.data.append("")

    def _checked_elements(
        self,
        machine: MachineConfig,
        prefix_values: list[int],
        reduced: int,
    ) -> list[tuple[int, int]]:
        """The positions and values this case asserts.

        A prefix checks its first line's first three elements, which are exactly
        where the two implementations diverge.  A reduce is replicated along its
        line, so its first and last elements both carry the folded value.
        """

        if self.prefix:
            if self.axis.by_row:
                positions = list(range(len(prefix_values)))
            else:
                positions = [row * machine.n for row in range(len(prefix_values))]
            return list(zip(positions, prefix_values))
        return [(0, reduced), (machine.nelem - 1, reduced)]


__all__ = ["FOLD_SEQUENCE", "ReducePrefixSaturatingFold", "fold_expected", "fold_values"]
