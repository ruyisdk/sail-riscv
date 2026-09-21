#!/usr/bin/env python3
#
# Copyright (c) Qualcomm Technologies, Inc. and/or its subsidiaries.
# SPDX-License-Identifier: BSD-3-Clause-Clear
#
"""Generator for ``mmov.m.a``: the packed accumulator span recipe."""

from __future__ import annotations

from mmul_gen.instruction import ACCUMULATOR_OPERAND, FIRST_SOURCE_OPERAND, Instruction
from mmul_gen.templates.acc_span_routing import (
    AccumulatorSpanRouting,
)


class MmovMAAccSpan(Instruction):
    """Write a packed M square into a consecutive span of accumulators."""

    name = "mmov.m.a"
    summary = "write a packed M square into a consecutive accumulator span"
    summary_zh = "将打包的 M 方阵写入连续的累加器跨度"
    subject = "packed accumulator span test cases."
    operands = (ACCUMULATOR_OPERAND, FIRST_SOURCE_OPERAND)
    templates = (
        AccumulatorSpanRouting("span_low", "span_high", "overlapping_readback"),
    )
    # The recipe's source name carries the family: the accumulator family
    # separately generates the plain ``mmov.m.a`` file.
    file_name = "mmov_m_a_acc_span.S"


__all__ = ["MmovMAAccSpan"]
