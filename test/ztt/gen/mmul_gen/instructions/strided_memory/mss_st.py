#!/usr/bin/env python3
#
# Copyright (c) Qualcomm Technologies, Inc. and/or its subsidiaries.
# SPDX-License-Identifier: BSD-3-Clause-Clear
#
"""mss_st.py: store one square with a stride, one element per segment."""

from __future__ import annotations

from mmul_gen.instructions.strided_memory.base import (
    StridedMemoryInstruction,
)
from mmul_gen.templates.strided_normal_square import (
    StridedNormalSquare,
)
from mmul_gen.templates.strided_packed_storage import (
    StridedPackedStorage,
)
from mmul_gen.templates.strided_conversion_pairs import (
    StridedConversionPairs,
)
from mmul_gen.templates.strided_memory_common import StridedTransfer

class MssSt(StridedMemoryInstruction):
    """Store one square with a stride, one element per segment."""

    name = "mss.st"
    summary = "store one square with a stride, one element per segment"
    summary_zh = "按步长存储一个方阵，每段一个元素"
    subject = "strided-memory semantic test cases."
    operands = ()
    templates = (
        StridedNormalSquare(StridedTransfer(is_load=False, transposed=False)),
        StridedPackedStorage(StridedTransfer(is_load=False, transposed=False)),
        StridedConversionPairs(StridedTransfer(is_load=False, transposed=False)),
    )

__all__ = ["MssSt"]
