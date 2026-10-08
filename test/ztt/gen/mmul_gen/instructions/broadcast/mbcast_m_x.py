#!/usr/bin/env python3
#
# Copyright (c) Qualcomm Technologies, Inc. and/or its subsidiaries.
# SPDX-License-Identifier: BSD-3-Clause-Clear
#
"""Generator for ``mbcast.m.x``: scalar-ingress broadcast.

The instruction reads a scalar from a general register and fills every element
of the descriptor named by the third operand, so its two trailing operands are
both ``t`` registers: first the value, then the type register.  The seven input
case groups it covers are declared by its templates, in the order the output
file reports them.
"""

from __future__ import annotations

from mmul_gen.asm import dst_square_lines
from mmul_gen.instruction import (
    DESTINATION_OPERAND,
    SCALAR_SOURCE_OPERAND,
    Instruction,
)
from mmul_gen.machine import MachineConfig
from mmul_gen.templates.broadcast_floating import (
    FLOATING_INGRESS,
)
from mmul_gen.templates.broadcast_int128_ingress import (
    INTEGER128_INGRESS,
)
from mmul_gen.templates.broadcast_packed_storage import (
    PACKED_STORAGE_INGRESS,
)
from mmul_gen.templates.broadcast_saturating_ingress import (
    SATURATING_INGRESS,
)
from mmul_gen.templates.broadcast_saturating_int128_ingress import (
    SATURATING_INTEGER128_INGRESS,
)
from mmul_gen.templates.broadcast_scalar_ingress import (
    SCALAR_INGRESS,
)
from mmul_gen.templates.broadcast_unsupported_probe import (
    UNSUPPORTED_DTYPE_PROBE,
)

class MbcastMX(Instruction):
    """Broadcast one scalar into every element of a formed descriptor."""

    name = "mbcast.m.x"
    summary = "broadcast one scalar into every element of a formed descriptor"
    subject = "scalar-ingress and packed-storage broadcast test cases."
    operands = (DESTINATION_OPERAND, SCALAR_SOURCE_OPERAND, SCALAR_SOURCE_OPERAND)
    templates = (
        SCALAR_INGRESS,
        INTEGER128_INGRESS,
        SATURATING_INGRESS,
        SATURATING_INTEGER128_INGRESS,
        PACKED_STORAGE_INGRESS,
        FLOATING_INGRESS,
        UNSUPPORTED_DTYPE_PROBE,
    )

    def data_footer(self, machine: MachineConfig) -> list[str]:
        return dst_square_lines(machine)

__all__ = ["MbcastMX"]
