#!/usr/bin/env python3
#
# Copyright (c) Qualcomm Technologies, Inc. and/or its subsidiaries.
# SPDX-License-Identifier: BSD-3-Clause-Clear
#
"""Generator for ``mpack.ew.x``: narrow a square into one packed storage slot."""

from __future__ import annotations

from mmul_gen.instruction import (
    DESTINATION_OPERAND,
    PACK_SLOT_OPERAND,
    PACK_SOURCE_OPERAND,
)
from mmul_gen.instructions.pack.base import PackInstruction
from mmul_gen.templates.pack_slots import (
    PACK_SLOTS,
)


class MpackEwX(PackInstruction):
    name = "mpack.ew.x"
    summary = "narrow a compute square into one packed storage slot"
    summary_zh = "将计算方阵收窄写入一个打包存储槽"
    operands = (DESTINATION_OPERAND, PACK_SLOT_OPERAND, PACK_SOURCE_OPERAND)
    templates = (PACK_SLOTS,)


__all__ = ["MpackEwX"]
