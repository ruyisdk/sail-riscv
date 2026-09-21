#!/usr/bin/env python3
#
# Copyright (c) Qualcomm Technologies, Inc. and/or its subsidiaries.
# SPDX-License-Identifier: BSD-3-Clause-Clear
#
"""Generator for ``mmulbtacc.2d``: ``C = C + sum(A x transpose(B))``."""

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


class MmulBtAcc2d(MatrixMultiplyInstruction):
    """C = C + sum(A x transpose(B))."""

    name = "mmulbtacc.2d"
    summary = "C = C + sum(A x transpose(B))"
    summary_zh = "转置 B 的矩阵乘累加：C = C + Σ(A × transpose(B))"
    manual_zh = "转置 B 的矩阵乘累加。将 `ms1` 与 `ms2` 的转置的矩阵乘积累加进 `acc`；`acc` 既是源又是目的：先读出它的当前值，加上转置 B 的矩阵乘积，再把结果写回。"
    operands = PRODUCT_OPERANDS
    templates = (
        MatrixSmall(ProductFlags(transpose_rhs=True)),
        FloatPairSweep(ProductFlags(transpose_rhs=True)),
        PackedSmall(ProductFlags(transpose_rhs=True)),
        SaturatingBoundary(ProductFlags(transpose_rhs=True)),
        MixedSignednessMultipleSquare(ProductFlags(transpose_rhs=True)),
    )


__all__ = ["MmulBtAcc2d"]
