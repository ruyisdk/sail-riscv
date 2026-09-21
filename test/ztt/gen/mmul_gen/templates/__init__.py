#!/usr/bin/env python3
#
# Copyright (c) Qualcomm Technologies, Inc. and/or its subsidiaries.
# SPDX-License-Identifier: BSD-3-Clause-Clear
#
"""Index of the template instances, one per template class.

Every instance is constructed by the module that defines its class, so a
template and its instance are read in one place and importing an instruction
does not drag in the whole package.  This module only re-exports them; the
aggregate tuples below are for the tests that check them.
"""

from __future__ import annotations

DOC_ZH = """\
模板实例索引，每个模板类一个实例。

每个实例都由定义其类的模块构造，因此模板与它的实例在同一处阅读，导入一条指令也不会牵入整个包。本模块只做再导出；下面的聚合元组供检查它们的测试使用。
"""

from mmul_gen.templates.acc_span_exceptions import (
    AccumulatorSpanExceptions,
)
from mmul_gen.templates.acc_span_routing import (
    AccumulatorSpanRouting,
)
from mmul_gen.templates.accumulator_acc_to_m import (
    ACCUMULATOR_ACC_TO_M,
)
from mmul_gen.templates.accumulator_m_to_acc import (
    ACCUMULATOR_M_TO_ACC,
)
from mmul_gen.templates.accumulator_zero_acc import (
    ACCUMULATOR_ZERO_ACC,
)
from mmul_gen.templates.accumulator_zero_m import (
    ACCUMULATOR_ZERO_M,
)
from mmul_gen.templates.axis_permute_column_broadcast import (
    COLUMN_BROADCAST,
)
from mmul_gen.templates.axis_permute_column_index import (
    COLUMN_INDEX,
)
from mmul_gen.templates.axis_permute_column_shift import (
    COLUMN_SHIFT,
)
from mmul_gen.templates.axis_permute_row_broadcast import (
    ROW_BROADCAST,
)
from mmul_gen.templates.axis_permute_row_index import (
    ROW_INDEX,
)
from mmul_gen.templates.axis_permute_row_shift import (
    ROW_SHIFT,
)
from mmul_gen.templates.backend_acquire_busy import (
    ACQUIRE_BUSY_STATE,
)
from mmul_gen.templates.backend_acquire_state import (
    ACQUIRE_RELEASE_STATE,
)
from mmul_gen.templates.backend_release_idle import (
    RELEASE_IDLE_STATE,
)
from mmul_gen.templates.backend_release_state import (
    RELEASE_STATE,
)
from mmul_gen.templates.broadcast_floating import (
    FLOATING_INGRESS,
)
from mmul_gen.templates.broadcast_int128_ingress import (
    INTEGER128_INGRESS,
)
from mmul_gen.templates.broadcast_packed_storage import (
    PACKED_STORAGE_INGRESS,
)
from mmul_gen.templates.broadcast_saturating_ingress import (
    SATURATING_INGRESS,
)
from mmul_gen.templates.broadcast_saturating_int128_ingress import (
    SATURATING_INTEGER128_INGRESS,
)
from mmul_gen.templates.broadcast_scalar_ingress import (
    SCALAR_INGRESS,
)
from mmul_gen.templates.broadcast_unsupported_probe import (
    UNSUPPORTED_DTYPE_PROBE,
)
from mmul_gen.templates.debug_move16 import (
    DEBUG_MOVE16,
)
from mmul_gen.templates.debug_move32 import (
    DEBUG_MOVE32,
)
from mmul_gen.templates.debug_move64 import (
    DEBUG_MOVE64,
)
from mmul_gen.templates.debug_move8 import (
    DEBUG_MOVE8,
)
from mmul_gen.templates.elementwise_templates import (
    ELEMENTWISE_TEMPLATE_CLASSES,
)
from mmul_gen.templates.float_math_cases import (
    FloatMathCases,
)
from mmul_gen.templates.float_pair_sweep import (
    FloatPairSweep,
)
from mmul_gen.templates.integer_shift_register import (
    ShiftRegisterSource,
)
from mmul_gen.templates.integer_shift_scalar import (
    ShiftScalarSource,
)
from mmul_gen.templates.logexp_nominal import (
    LogExpNominal,
)
from mmul_gen.templates.logexp_saturating_exp2 import (
    Exp2SaturatingBoundary,
)
from mmul_gen.templates.logexp_saturating_exp2_wide import (
    Exp2Saturating128,
)
from mmul_gen.templates.logexp_saturating_ldexpacc import (
    LdexpaccSaturatingBoundary,
)
from mmul_gen.templates.matrix_ops_gather_extra import (
    GATHER_EXTRA_INDEX,
)
from mmul_gen.templates.matrix_ops_gather_indexed import (
    GatherScatterIndexed,
)
from mmul_gen.templates.matrix_ops_reduce_ramp import (
    ReducePrefixRamp,
)
from mmul_gen.templates.matrix_ops_reduce_saturating import (
    REDUCE_SATURATING,
)
from mmul_gen.templates.matrix_ops_scatter_saturating import (
    SCATTER_SATURATING,
)
from mmul_gen.templates.matrix_ops_zip_dual import (
    ZipDualSource,
)
from mmul_gen.templates.matrix_ops_zip_extra import (
    ZipExtraSource,
)
from mmul_gen.templates.matrix_small import (
    MatrixSmall,
)
from mmul_gen.templates.mconv_roundtrip import (
    MCONV_ROUNDTRIP,
)
from mmul_gen.templates.memory_order_col_to_row import (
    MEMORY_ORDER_COL_TO_ROW,
)
from mmul_gen.templates.memory_order_row_to_col import (
    MEMORY_ORDER_ROW_TO_COL,
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
from mmul_gen.templates.pack_slots import (
    PACK_SLOTS,
)
from mmul_gen.templates.packed_small import (
    PackedSmall,
)
from mmul_gen.templates.raw_transfer import (
    RAW_TRANSFER,
)
from mmul_gen.templates.saturating_boundary import (
    SaturatingBoundary,
)
from mmul_gen.templates.strided_conversion_pairs import (
    StridedConversionPairs,
)
from mmul_gen.templates.strided_normal_square import (
    StridedNormalSquare,
)
from mmul_gen.templates.strided_packed_storage import (
    StridedPackedStorage,
)
from mmul_gen.templates.type_register_acc_roundtrip import (
    AccTypeRoundtrip,
)
from mmul_gen.templates.type_register_acc_unsupported_probe import (
    ACC_TYPE_UNSUPPORTED_PROBE,
)
from mmul_gen.templates.type_register_m_roundtrip import (
    MTypeRoundtrip,
)
from mmul_gen.templates.type_register_m_unsupported_probe import (
    M_TYPE_UNSUPPORTED_PROBE,
)
from mmul_gen.templates.unpack_slots import (
    UNPACK_SLOTS,
)


from mmul_gen.templates.base import (
    Case,
    CaseOutput,
    Template,
)


ALL_TEMPLATES = (
    ACCUMULATOR_ZERO_ACC,
    ACCUMULATOR_ZERO_M,
    ACCUMULATOR_ACC_TO_M,
    ACCUMULATOR_M_TO_ACC,
    MEMORY_ORDER_ROW_TO_COL,
    MEMORY_ORDER_COL_TO_ROW,
    DEBUG_MOVE8,
    DEBUG_MOVE16,
    DEBUG_MOVE32,
    DEBUG_MOVE64,
    RAW_TRANSFER,
    ACQUIRE_RELEASE_STATE,
    ACQUIRE_BUSY_STATE,
    RELEASE_STATE,
    RELEASE_IDLE_STATE,
    ONES_UNIFORM,
    ONES_UNIFORM_128,
    MULTI_ACC_INDEPENDENT,
    PACK_SLOTS,
    UNPACK_SLOTS,
    MCONV_ROUNDTRIP,
    M_TYPE_UNSUPPORTED_PROBE,
    ACC_TYPE_UNSUPPORTED_PROBE,
    SCALAR_INGRESS,
    INTEGER128_INGRESS,
    SATURATING_INGRESS,
    SATURATING_INTEGER128_INGRESS,
    PACKED_STORAGE_INGRESS,
    FLOATING_INGRESS,
    UNSUPPORTED_DTYPE_PROBE,
    COLUMN_BROADCAST,
    ROW_BROADCAST,
    COLUMN_INDEX,
    ROW_INDEX,
    COLUMN_SHIFT,
    ROW_SHIFT,
    REDUCE_SATURATING,
    GATHER_EXTRA_INDEX,
    SCATTER_SATURATING,
)
# The elementwise templates are not here: every elementwise instruction constructs
# the templates it runs with their own inputs, so the family's coverage is stated
# by the classes in ``ELEMENTWISE_TEMPLATE_CLASSES`` and by the per-instruction
# lists the tests check against them.

#: Templates that carry their own inputs.  An instruction constructs the
#: instances it runs, so the *class* is shared and the object is not; every other
#: template in :data:`ALL_TEMPLATES` is one shared instance.  The elementwise
#: templates come first, in the order their cases appear.
TEMPLATE_CLASSES = (
    *ELEMENTWISE_TEMPLATE_CLASSES,
    AccTypeRoundtrip,
    AccumulatorSpanExceptions,
    AccumulatorSpanRouting,
    Exp2Saturating128,
    Exp2SaturatingBoundary,
    FloatMathCases,
    FloatPairSweep,
    GatherScatterIndexed,
    LdexpaccSaturatingBoundary,
    LogExpNominal,
    MTypeRoundtrip,
    MatrixSmall,
    MixedSignednessMultipleSquare,
    PackedSmall,
    ReducePrefixRamp,
    SaturatingBoundary,
    ShiftRegisterSource,
    ShiftScalarSource,
    StridedConversionPairs,
    StridedNormalSquare,
    StridedPackedStorage,
    ZipDualSource,
    ZipExtraSource,
)


__all__ = [
    "ACCUMULATOR_ACC_TO_M",
    "ACCUMULATOR_M_TO_ACC",
    "ACCUMULATOR_ZERO_ACC",
    "ACCUMULATOR_ZERO_M",
    "ACC_TYPE_UNSUPPORTED_PROBE",
    "ACQUIRE_BUSY_STATE",
    "ACQUIRE_RELEASE_STATE",
    "ALL_TEMPLATES",
    "AccTypeRoundtrip",
    "AccumulatorSpanExceptions",
    "AccumulatorSpanRouting",
    "COLUMN_BROADCAST",
    "COLUMN_INDEX",
    "COLUMN_SHIFT",
    "Case",
    "CaseOutput",
    "DEBUG_MOVE16",
    "DEBUG_MOVE32",
    "DEBUG_MOVE64",
    "DEBUG_MOVE8",
    "ELEMENTWISE_TEMPLATE_CLASSES",
    "Exp2Saturating128",
    "Exp2SaturatingBoundary",
    "FLOATING_INGRESS",
    "FloatMathCases",
    "FloatPairSweep",
    "GATHER_EXTRA_INDEX",
    "GatherScatterIndexed",
    "INTEGER128_INGRESS",
    "LdexpaccSaturatingBoundary",
    "LogExpNominal",
    "MCONV_ROUNDTRIP",
    "MEMORY_ORDER_COL_TO_ROW",
    "MEMORY_ORDER_ROW_TO_COL",
    "MTypeRoundtrip",
    "MULTI_ACC_INDEPENDENT",
    "M_TYPE_UNSUPPORTED_PROBE",
    "MatrixSmall",
    "MixedSignednessMultipleSquare",
    "ONES_UNIFORM",
    "ONES_UNIFORM_128",
    "PACKED_STORAGE_INGRESS",
    "PACK_SLOTS",
    "PackedSmall",
    "RAW_TRANSFER",
    "REDUCE_SATURATING",
    "RELEASE_IDLE_STATE",
    "RELEASE_STATE",
    "ROW_BROADCAST",
    "ROW_INDEX",
    "ROW_SHIFT",
    "ReducePrefixRamp",
    "SATURATING_INGRESS",
    "SATURATING_INTEGER128_INGRESS",
    "SCALAR_INGRESS",
    "SCATTER_SATURATING",
    "SaturatingBoundary",
    "ShiftRegisterSource",
    "ShiftScalarSource",
    "StridedConversionPairs",
    "StridedNormalSquare",
    "StridedPackedStorage",
    "TEMPLATE_CLASSES",
    "Template",
    "UNPACK_SLOTS",
    "UNSUPPORTED_DTYPE_PROBE",
    "ZipDualSource",
    "ZipExtraSource",
]
