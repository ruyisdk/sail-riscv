#!/usr/bin/env python3
#
# Copyright (c) Qualcomm Technologies, Inc. and/or its subsidiaries.
# SPDX-License-Identifier: BSD-3-Clause-Clear
#
"""Generator for ``mmulaccneg.2d``: ``C = C - A x B``."""

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


class MmulAccNeg2d(MatrixMultiplyInstruction):
    """C = C - A x B."""

    name = "mmulaccneg.2d"
    summary = "C = C - A x B"
    summary_zh = "矩阵乘取负累加：C = C − A × B"
    manual_zh = "矩阵乘取负累加。从 `acc` 中减去 `ms1` 与 `ms2` 的矩阵乘积；`acc` 既是源又是目的：先读出它的当前值，减去矩阵乘积，再把结果写回。"
    operands = PRODUCT_OPERANDS
    templates = (
        MatrixSmall(ProductFlags(subtract=True)),
        FloatPairSweep(ProductFlags(subtract=True)),
        PackedSmall(ProductFlags(subtract=True)),
        SaturatingBoundary(ProductFlags(subtract=True)),
        MixedSignednessMultipleSquare(ProductFlags(subtract=True)),
    )


__all__ = ["MmulAccNeg2d"]
