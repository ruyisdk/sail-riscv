#!/usr/bin/env python3
#
# Copyright (c) Qualcomm Technologies, Inc. and/or its subsidiaries.
# SPDX-License-Identifier: BSD-3-Clause-Clear
#
"""Generator for ``mmov.a.m``: the packed accumulator span recipe."""

from __future__ import annotations

from mmul_gen.instruction import ACCUMULATOR_OPERAND, FIRST_SOURCE_OPERAND, Instruction
from mmul_gen.templates.acc_span_routing import (
    AccumulatorSpanRouting,
)


class MmovAMAccSpan(Instruction):
    """Read a consecutive span of accumulators back into a packed M square."""

    name = "mmov.a.m"
    summary = "read a consecutive accumulator span back into a packed M square"
    summary_zh = "将连续的累加器跨度读回打包的 M 方阵"
    subject = "packed accumulator span test cases."
    operands = (ACCUMULATOR_OPERAND, FIRST_SOURCE_OPERAND)
    templates = (
        AccumulatorSpanRouting("span_low", "span_high", "overlapping_readback"),
    )
    file_name = "mmov_a_m_acc_span.S"


__all__ = ["MmovAMAccSpan"]
