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
    operands = PRODUCT_OPERANDS
    templates = (
        MatrixSmall(ProductFlags(subtract=True)),
        FloatPairSweep(ProductFlags(subtract=True)),
        PackedSmall(ProductFlags(subtract=True)),
        SaturatingBoundary(ProductFlags(subtract=True)),
        MixedSignednessMultipleSquare(ProductFlags(subtract=True)),
    )


__all__ = ["MmulAccNeg2d"]
