#!/usr/bin/env python3
#
# Copyright (c) Qualcomm Technologies, Inc. and/or its subsidiaries.
# SPDX-License-Identifier: BSD-3-Clause-Clear
#
"""mls_tst.py: load one square with a transposed stride."""

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

class MlsTst(StridedMemoryInstruction):
    """Load one square with a transposed stride, one element per segment."""

    name = "mls.tst"
    summary = "load one square with a transposed stride"
    subject = "strided-memory semantic test cases."
    operands = ()
    templates = (
        StridedNormalSquare(StridedTransfer(is_load=True, transposed=True)),
        StridedPackedStorage(StridedTransfer(is_load=True, transposed=True)),
        StridedConversionPairs(StridedTransfer(is_load=True, transposed=True)),
    )

__all__ = ["MlsTst"]
