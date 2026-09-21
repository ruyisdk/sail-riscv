#!/usr/bin/env python3
#
# Copyright (c) Qualcomm Technologies, Inc. and/or its subsidiaries.
# SPDX-License-Identifier: BSD-3-Clause-Clear
#
"""Generator for the shared packed accumulator span exception recipe."""

from __future__ import annotations

from mmul_gen.instruction import Instruction
from mmul_gen.templates.acc_span_exceptions import (
    AccumulatorSpanExceptions,
)

class AccSpanExceptions(Instruction):
    """Test both rejection paths of a packed accumulator span in one source.

    The source is not one instruction: it is the shared recipe that the manual
    states for *every* packed span transfer, so it is declared once with the
    ``mmov`` stem and named after the recipe.
    """

    name = "mmov"
    summary = "reject an over-long or file-crossing packed accumulator span"
    summary_zh = "拒绝过长或跨越寄存器文件边界的打包累加器跨度"
    subject = "accumulator span exception test cases (amestatus.UN and illegal span)."
    operands = ()
    templates = (
        AccumulatorSpanExceptions("unsupported_span", "crossing_span"),
    )
    file_name = "acc_span_exceptions.S"

__all__ = ["AccSpanExceptions"]
