#!/usr/bin/env python3
#
# Copyright (c) Qualcomm Technologies, Inc. and/or its subsidiaries.
# SPDX-License-Identifier: BSD-3-Clause-Clear
#
"""Generator for ``mgettyp``: read the datatype descriptor of an M register."""

from __future__ import annotations

from mmul_gen.instruction import (
    M_TYPE_OPERAND,
    SCALAR_DESTINATION_OPERAND,
    Instruction,
)
from mmul_gen.templates.type_register_m_roundtrip import (
    MTypeRoundtrip,
)


class Mgettyp(Instruction):
    """Read the datatype descriptor of an M register."""

    name = "mgettyp"
    summary = "read the datatype descriptor of an M register"
    summary_zh = "读取 M 寄存器的 datatype 描述符"
    subject = "type-register roundtrip test cases."
    operands = (SCALAR_DESTINATION_OPERAND, M_TYPE_OPERAND,)
    templates = (MTypeRoundtrip("mgettyp reads a descriptor seeded by msettyp"),)


__all__ = ["Mgettyp"]
