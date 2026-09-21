#!/usr/bin/env python3
#
# Copyright (c) Qualcomm Technologies, Inc. and/or its subsidiaries.
# SPDX-License-Identifier: BSD-3-Clause-Clear
#
"""Generator for ``munpack.ew.x``: widen one packed storage slot into a square."""

from __future__ import annotations

from mmul_gen.instruction import (
    DESTINATION_OPERAND,
    PACK_SLOT_OPERAND,
    PACK_SOURCE_OPERAND,
)
from mmul_gen.instructions.pack.base import PackInstruction
from mmul_gen.templates.unpack_slots import (
    UNPACK_SLOTS,
)


class MunpackEwX(PackInstruction):
    name = "munpack.ew.x"
    summary = "widen one packed storage slot into a compute square"
    summary_zh = "将一个打包存储槽扩展为计算方阵"
    operands = (DESTINATION_OPERAND, PACK_SLOT_OPERAND, PACK_SOURCE_OPERAND)
    templates = (UNPACK_SLOTS,)


__all__ = ["MunpackEwX"]
