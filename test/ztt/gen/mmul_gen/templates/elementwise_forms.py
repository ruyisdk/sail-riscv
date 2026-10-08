#!/usr/bin/env python3
#
# Copyright (c) Qualcomm Technologies, Inc. and/or its subsidiaries.
# SPDX-License-Identifier: BSD-3-Clause-Clear
#
"""Operand forms of the elementwise family.

An elementwise instruction is defined by its mnemonic, its operand form, and the
input cases it wants; the storage layout, the checks, and the expected values are
all derived from the form.  The form is therefore the family's only real axis of
variation, and it is enumerated here rather than spelled as bare strings.
"""

from __future__ import annotations

from enum import Enum


class ElementwiseForm(Enum):
    """How one elementwise instruction takes its operands."""

    #: Two M-register operands: ``op.md, ms1, ms2``.
    BINARY_M = "binary_m"
    #: One M-register operand and one XLEN scalar: ``op.ew.x md, ms1, x``.
    BINARY_X = "binary_x"
    #: Three M-register operands: ``op.md, ms1, ms2, ms3``.
    TERNARY_M = "ternary_m"
    #: Two M-register operands and one XLEN scalar.
    TERNARY_X = "ternary_x"
    #: A plain move between two M-register groups.
    MOVE_M = "move_m"
    #: Absolute value of one M-register operand.
    UNARY_ABS = "unary_abs"

    @property
    def is_binary(self) -> bool:
        return self in (ElementwiseForm.BINARY_M, ElementwiseForm.BINARY_X)

    @property
    def is_ternary(self) -> bool:
        return self in (ElementwiseForm.TERNARY_M, ElementwiseForm.TERNARY_X)

    @property
    def takes_scalar(self) -> bool:
        """Whether the narrow form carries its second operand in an X register."""

        return self in (ElementwiseForm.BINARY_X, ElementwiseForm.TERNARY_X)


__all__ = ["ElementwiseForm"]
