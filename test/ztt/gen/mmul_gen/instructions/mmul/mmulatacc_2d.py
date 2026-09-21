#!/usr/bin/env python3
#
# Copyright (c) Qualcomm Technologies, Inc. and/or its subsidiaries.
# SPDX-License-Identifier: BSD-3-Clause-Clear
#
"""Generator for ``mmulatacc.2d``: ``C = C + sum(transpose(A) x B)``."""

from __future__ import annotations

from mmul_gen.instruction import PRODUCT_OPERANDS
from mmul_gen.instructions.mmul.base import MatrixMultiplyInstruction
from mmul_gen.reference import ProductFlags
from mmul_gen.templates.float_pair_sweep import (
    FloatPairSweep,
)
from mmul_gen.templates.matrix_small import (
    MatrixSmall,
)
from mmul_gen.templates.mixed_signedness import (
    MixedSignednessMultipleSquare,
)
from mmul_gen.templates.packed_small import (
    PackedSmall,
)
from mmul_gen.templates.saturating_boundary import (
    SaturatingBoundary,
)


class MmulAtAcc2d(MatrixMultiplyInstruction):
    """C = C + sum(transpose(A) x B)."""

    name = "mmulatacc.2d"
    summary = "C = C + sum(transpose(A) x B)"
    summary_zh = "转置 A 的矩阵乘累加：C = C + Σ(transpose(A) × B)"
    manual_zh = "转置 A 的矩阵乘累加。将 `ms1` 的转置与 `ms2` 的矩阵乘积累加进 `acc`；`acc` 既是源又是目的：先读出它的当前值，加上转置 A 的矩阵乘积，再把结果写回。"
    operands = PRODUCT_OPERANDS
    templates = (
        MatrixSmall(ProductFlags(transpose_lhs=True)),
        FloatPairSweep(ProductFlags(transpose_lhs=True)),
        PackedSmall(ProductFlags(transpose_lhs=True)),
        SaturatingBoundary(ProductFlags(transpose_lhs=True)),
        MixedSignednessMultipleSquare(ProductFlags(transpose_lhs=True)),
    )


__all__ = ["MmulAtAcc2d"]
