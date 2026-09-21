#!/usr/bin/env python3
#
# Copyright (c) Qualcomm Technologies, Inc. and/or its subsidiaries.
# SPDX-License-Identifier: BSD-3-Clause-Clear
#
"""What one elementwise instruction sees when it evaluates a single element.

The form decides how the operands reach the instruction (``integer_elements``);
the instruction declares what it computes with them (``Instruction.evaluate``).
Keeping the two apart is what lets an instruction state its own formula without
knowing how its operands are loaded.
"""

from __future__ import annotations

DOC_ZH = """\
一条 elementwise 指令在求值单个元素时看到的内容。

形态决定操作数如何到达指令（``integer_elements``）；指令声明它用这些操作数算什么（``Instruction.evaluate``）。把两者分开，指令才能在不了解操作数如何加载的情况下陈述自己的算式。
"""

from dataclasses import dataclass

from mmul_gen.reference import IntegerDType
from mmul_gen.templates.elementwise_forms import ElementwiseForm


@dataclass(frozen=True)
class IntegerElements:
    """One element of each operand, in both of its architectural readings.

    ``lhs``/``rhs``/``dest`` are the architectural values, read at the element
    width; ``lhs_raw``/``rhs_raw`` are the same bits read as unsigned, which is
    what the bitwise instructions operate on.  ``dtype`` carries the width the
    declared result is re-encoded at.
    """

    dtype: IntegerDType
    lhs: int
    rhs: int
    dest: int
    lhs_raw: int
    rhs_raw: int

    @property
    def mask(self) -> int:
        """All ones at the element width: the ``true`` a comparison produces."""

        return (1 << self.dtype.bits) - 1


def round_to_nearest_up(value: int) -> int:
    """Halve an exact integer, rounding ties toward positive infinity."""

    return value // 2 + (value % 2 != 0)


#: Which operand of the case each form presents as ``lhs``/``rhs``/``dest``.  The
#: ternary M form shares one register group for ``D`` and ``A``, so it presents
#: the same square as both.
FORM_OPERANDS: dict[ElementwiseForm, tuple[str, str, str]] = {
    ElementwiseForm.BINARY_M: ("a", "b", "dest"),
    ElementwiseForm.BINARY_X: ("scalar", "b", "dest"),
    ElementwiseForm.TERNARY_M: ("a", "b", "a"),
    ElementwiseForm.TERNARY_X: ("scalar", "b", "dest"),
    ElementwiseForm.MOVE_M: ("b", "b", "dest"),
    ElementwiseForm.UNARY_ABS: ("abs", "abs", "dest"),
}


def integer_elements(
    form: ElementwiseForm, dtype: IntegerDType, values: dict[str, int]
) -> IntegerElements:
    """The operands one case of ``form`` presents to its instruction."""

    operands = FORM_OPERANDS.get(form)
    if operands is None:
        raise ValueError(f"{form} has no elementwise evaluation")
    lhs_role, rhs_role, dest_role = operands
    mask = (1 << dtype.bits) - 1
    lhs_raw = values[lhs_role] & mask
    rhs_raw = values[rhs_role] & mask
    return IntegerElements(
        dtype=dtype,
        lhs=dtype.decode(lhs_raw),
        rhs=dtype.decode(rhs_raw),
        dest=dtype.decode(values[dest_role]),
        lhs_raw=lhs_raw,
        rhs_raw=rhs_raw,
    )


__all__ = ["FORM_OPERANDS", "IntegerElements", "integer_elements", "round_to_nearest_up"]
