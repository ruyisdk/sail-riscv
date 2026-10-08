#!/usr/bin/env python3
#
# Copyright (c) Qualcomm Technologies, Inc. and/or its subsidiaries.
# SPDX-License-Identifier: BSD-3-Clause-Clear
#
"""Generator for ``mmulacc.2d``: ``C = C + A x B``.

``mmulacc.2d`` is the only matrix-multiply instruction whose accumulator is
written from a fresh product and read back with ``mmov.m.a`` alone, so it is
also the instruction that covers the packed accumulator span and the
independent multi-accumulator templates.
"""

from __future__ import annotations

from mmul_gen.instruction import PRODUCT_OPERANDS
from mmul_gen.instructions.mmul.base import MatrixMultiplyInstruction
from mmul_gen.reference import ProductFlags
from mmul_gen.templates.float_pair_sweep import (
    FloatPairSweep,
)
from mmul_gen.templates.mixed_signedness import (
    MixedSignednessMultipleSquare,
)
from mmul_gen.templates.multi_acc_independent import (
    MULTI_ACC_INDEPENDENT,
)
from mmul_gen.templates.ones_uniform import (
    ONES_UNIFORM,
    ONES_UNIFORM_128,
)
from mmul_gen.templates.packed_small import (
    PackedSmall,
)
from mmul_gen.templates.saturating_boundary import (
    SaturatingBoundary,
)


class MmulAcc2d(MatrixMultiplyInstruction):
    """C = C + A x B."""

    name = "mmulacc.2d"
    summary = "C = C + A x B"
    operands = PRODUCT_OPERANDS
    templates = (
        ONES_UNIFORM,
        ONES_UNIFORM_128,
        FloatPairSweep(ProductFlags()),
        PackedSmall(ProductFlags()),
        SaturatingBoundary(ProductFlags()),
        MULTI_ACC_INDEPENDENT,
        MixedSignednessMultipleSquare(ProductFlags()),
    )

    @property
    def title(self) -> str:
        return f"{self.name} 2D matrix multiply-accumulate test cases."


__all__ = ["MmulAcc2d"]
