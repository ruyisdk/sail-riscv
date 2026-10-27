#!/usr/bin/env python3
#
# Copyright (c) Qualcomm Technologies, Inc. and/or its subsidiaries.
# SPDX-License-Identifier: BSD-3-Clause-Clear
#
"""Zeroing an accumulator and copying it out must leave an all-zero square.

Spec:    programming_model.adoc:72-75 (§2.2)
Quote:   "A single `M` register may hold multiple, one, or part of a square, depending on implementation-defined
         parameters and programmed datatype.  In contrast, an `Acc` register always holds exactly one square."
Checks:  zeroing an accumulator with mzero.2d.acc and copying it out must store an all-zero square rather than a stale
         payload.

The copy is what makes the check meaningful: it reads the accumulator back
through ``mmov.m.a``, so a zeroed descriptor with a stale payload still fails.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from mmul_gen.registers import RegisterLayout
from mmul_gen.templates.accumulator_common import (
    AccumulatorUtilityTemplate,
    require_accumulator,
    zero_acc_then_copy_out,
)
from mmul_gen.templates.base import register

if TYPE_CHECKING:
    from mmul_gen.instruction import Instruction


class AccumulatorZeroAcc(AccumulatorUtilityTemplate):
    """Zeroing an accumulator and copying it out must leave an all-zero square."""

    name = "zero_acc"
    uses_accumulator = True

    def operation_lines(
        self, instruction: Instruction, layout: RegisterLayout, destination_label: str
    ) -> list[str]:
        return zero_acc_then_copy_out(
            register("md", layout), require_accumulator(layout), destination_label
        )


__all__ = ["AccumulatorZeroAcc"]


ACCUMULATOR_ZERO_ACC = AccumulatorZeroAcc()
