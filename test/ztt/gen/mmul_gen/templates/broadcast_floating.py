#!/usr/bin/env python3
#
# Copyright (c) Qualcomm Technologies, Inc. and/or its subsidiaries.
# SPDX-License-Identifier: BSD-3-Clause-Clear
#
"""Broadcast one floating-point scalar into every element.

The scalar is a raw bit pattern, not a numeric literal, so no host floating
library decides the encoding: each width uses the pattern of a well-known
value (1.0 for 32/64-bit, 1.0 for the 16-bit pair).
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import TYPE_CHECKING

from mmul_gen.asm import check_dst_element_lines, hex_value
from mmul_gen.machine import SOFTFLOAT, MachineConfig
from mmul_gen.templates.base import Case, CaseOutput, Template
from mmul_gen.templates.broadcast_common import (
    DESTINATION_LABEL,
    FLOAT_ELEMENT_BITS,
    FLOAT_SCALARS,
    ingress_case,
    label_index,
)

if TYPE_CHECKING:
    from mmul_gen.instruction import Instruction
    from mmul_gen.machine import DType


class FloatingBroadcast(Template):
    """Broadcast a raw floating-point pattern into every element."""

    name = "floating_ingress"
    dtypes = SOFTFLOAT

    def build(
        self, machine: MachineConfig, instruction: Instruction, dtype: DType | None
    ) -> Sequence[Case]:
        return ingress_case(machine, dtype)

    def render(
        self,
        machine: MachineConfig,
        instruction: Instruction,
        case: Case,
        out: CaseOutput,
    ) -> None:
        if case.dtype is None:
            raise ValueError("a floating broadcast case needs a datatype")
        element_bits = case.dtype.bits
        if element_bits not in FLOAT_ELEMENT_BITS:
            raise ValueError(f"unsupported floating broadcast: {case.dtype.name}")
        index = label_index(machine, case.dtype, self.dtypes)
        scalar = FLOAT_SCALARS[element_bits]
        out.text.extend(
            [
                f"    # case {index}: {instruction.name} {case.dtype.name}",
                f"    li      t0, {case.dtype.name}",
                "    msettyp m0, t0",
                f"    li      t1, {hex_value(scalar, element_bits)}",
                f"    {instruction.name} m0, t1, t0",
                f"    la      t2, {DESTINATION_LABEL}",
                "    mss.rm     m0, t2",
                *check_dst_element_lines(scalar, element_bits, 0, DESTINATION_LABEL),
                *check_dst_element_lines(
                    scalar, element_bits, machine.nelem - 1, DESTINATION_LABEL
                ),
            ]
        )


__all__ = ["FloatingBroadcast"]


FLOATING_INGRESS = FloatingBroadcast()
