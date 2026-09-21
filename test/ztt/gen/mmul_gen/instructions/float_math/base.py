#!/usr/bin/env python3
#
# Copyright (c) Qualcomm Technologies, Inc. and/or its subsidiaries.
# SPDX-License-Identifier: BSD-3-Clause-Clear
#
"""Shared declaration of the floating-point unary math family.

One floating-point unary math instruction and the two facts all ten share.
"""

from __future__ import annotations

from mmul_gen.instruction import Instruction


class FloatMathInstruction(Instruction, family_base=True):
    """One floating-point unary math instruction.

    The subject and the always-emitted ``.data`` footer are declared once here
    because all ten instructions name the same test purpose.  :class:`MathOperation`
    carries the nominal stimulus, the boundary scenarios, and -- for the
    transcendentals -- the host libm entry points; which operation an instruction
    implements is not a declaration on the class but the argument of its
    ``FloatMathCases`` entry.
    """

    always_emits_data = True
    subject = "floating-point semantic test cases."

__all__ = [
    "FloatMathInstruction",
]
