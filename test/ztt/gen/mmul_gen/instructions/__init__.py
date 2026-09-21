#!/usr/bin/env python3
#
# Copyright (c) Qualcomm Technologies, Inc. and/or its subsidiaries.
# SPDX-License-Identifier: BSD-3-Clause-Clear
#
"""One module per instruction, one package per family.

Adding an instruction means adding a module under its family package and listing
its class in :mod:`mmul_gen.catalog`; no existing instruction file changes.
The order below follows the catalog's family order, so this list is a view of
that order rather than a second declaration of it.
"""

from mmul_gen.instructions.acc_span.acc_span_exceptions import AccSpanExceptions
from mmul_gen.instructions.acc_span.mmov_a_m_acc_span import MmovAMAccSpan
from mmul_gen.instructions.acc_span.mmov_m_a_acc_span import MmovMAAccSpan
from mmul_gen.instructions.accumulator.mmov_a_m import MmovAM
from mmul_gen.instructions.accumulator.mmov_m_a import MmovMA
from mmul_gen.instructions.accumulator.mzero_2d_acc import Mzero2dAcc
from mmul_gen.instructions.accumulator.mzero_2d_m import Mzero2dM
from mmul_gen.instructions.axis_permute.mcolbcast_ew_x import McolbcastEwX
from mmul_gen.instructions.axis_permute.mcolid_ew import McolidEw
from mmul_gen.instructions.axis_permute.mcolshift_ew_x import McolshiftEwX
from mmul_gen.instructions.axis_permute.mrowbcast_ew_x import MrowbcastEwX
from mmul_gen.instructions.axis_permute.mrowid_ew import MrowidEw
from mmul_gen.instructions.axis_permute.mrowshift_ew_x import MrowshiftEwX
from mmul_gen.instructions.backend.ame_acquire import AmeAcquire
from mmul_gen.instructions.backend.ame_release import AmeRelease
from mmul_gen.instructions.broadcast.mbcast_m_x import MbcastMX
from mmul_gen.instructions.debug_move.mmove16_m_x import Mmove16MX
from mmul_gen.instructions.debug_move.mmove16_x_m import Mmove16XM
from mmul_gen.instructions.debug_move.mmove32_m_x import Mmove32MX
from mmul_gen.instructions.debug_move.mmove32_x_m import Mmove32XM
from mmul_gen.instructions.debug_move.mmove64_m_x import Mmove64MX
from mmul_gen.instructions.debug_move.mmove64_x_m import Mmove64XM
from mmul_gen.instructions.debug_move.mmove8_m_x import Mmove8MX
from mmul_gen.instructions.debug_move.mmove8_x_m import Mmove8XM
from mmul_gen.instructions.elementwise.mabs_ew import MabsEw
from mmul_gen.instructions.elementwise.mabsdiff_ew import MabsdiffEw
from mmul_gen.instructions.elementwise.mabsdiff_ew_x import MabsdiffEwX
from mmul_gen.instructions.elementwise.madd_ew import MaddEw
from mmul_gen.instructions.elementwise.madd_ew_x import MaddEwX
from mmul_gen.instructions.elementwise.mand_ew import MandEw
from mmul_gen.instructions.elementwise.mand_ew_x import MandEwX
from mmul_gen.instructions.elementwise.mandnot_ew import MandnotEw
from mmul_gen.instructions.elementwise.mandnot_ew_x import MandnotEwX
from mmul_gen.instructions.elementwise.mcmovge_ew import McmovgeEw
from mmul_gen.instructions.elementwise.mcmovlt_ew import McmovltEw
from mmul_gen.instructions.elementwise.mcmpge_ew import McmpgeEw
from mmul_gen.instructions.elementwise.mcmpge_ew_x import McmpgeEwX
from mmul_gen.instructions.elementwise.mcmplt_ew import McmpltEw
from mmul_gen.instructions.elementwise.mcmplt_ew_x import McmpltEwX
from mmul_gen.instructions.elementwise.mhdiff_ew import MhdiffEw
from mmul_gen.instructions.elementwise.mhdiff_ew_x import MhdiffEwX
from mmul_gen.instructions.elementwise.mmax_ew import MmaxEw
from mmul_gen.instructions.elementwise.mmax_ew_x import MmaxEwX
from mmul_gen.instructions.elementwise.mmean_ew import MmeanEw
from mmul_gen.instructions.elementwise.mmean_ew_x import MmeanEwX
from mmul_gen.instructions.elementwise.mmin_ew import MminEw
from mmul_gen.instructions.elementwise.mmin_ew_x import MminEwX
from mmul_gen.instructions.elementwise.mmov_m_m import MmovMM
from mmul_gen.instructions.elementwise.mmul_ew import MmulEw
from mmul_gen.instructions.elementwise.mmul_ew_x import MmulEwX
from mmul_gen.instructions.elementwise.mmulacc_ew import MmulaccEw
from mmul_gen.instructions.elementwise.mmulacc_ew_x import MmulaccEwX
from mmul_gen.instructions.elementwise.mmulaccneg_ew import MmulaccnegEw
from mmul_gen.instructions.elementwise.mmulaccneg_ew_x import MmulaccnegEwX
from mmul_gen.instructions.elementwise.mmuladd_ew import MmuladdEw
from mmul_gen.instructions.elementwise.mmuladd_ew_x import MmuladdEwX
from mmul_gen.instructions.elementwise.mmulneg_ew import MmulnegEw
from mmul_gen.instructions.elementwise.mmulneg_ew_x import MmulnegEwX
from mmul_gen.instructions.elementwise.mmulsub_ew import MmulsubEw
from mmul_gen.instructions.elementwise.mmulsub_ew_x import MmulsubEwX
from mmul_gen.instructions.elementwise.mor_ew import MorEw
from mmul_gen.instructions.elementwise.mor_ew_x import MorEwX
from mmul_gen.instructions.elementwise.mornot_ew import MornotEw
from mmul_gen.instructions.elementwise.mornot_ew_x import MornotEwX
from mmul_gen.instructions.elementwise.mselge_ew import MselgeEw
from mmul_gen.instructions.elementwise.msellt_ew import MselltEw
from mmul_gen.instructions.elementwise.msub_ew import MsubEw
from mmul_gen.instructions.elementwise.msub_ew_x import MsubEwX
from mmul_gen.instructions.elementwise.mxor_ew import MxorEw
from mmul_gen.instructions.elementwise.mxor_ew_x import MxorEwX
from mmul_gen.instructions.float_math.mcos_ew import McosEw
from mmul_gen.instructions.float_math.mfrintm_ew import MfrintmEw
from mmul_gen.instructions.float_math.mfrintn_ew import MfrintnEw
from mmul_gen.instructions.float_math.mfrintp_ew import MfrintpEw
from mmul_gen.instructions.float_math.mfrintz_ew import MfrintzEw
from mmul_gen.instructions.float_math.mrec_ew import MrecEw
from mmul_gen.instructions.float_math.mrsqrt_ew import MrsqrtEw
from mmul_gen.instructions.float_math.msin_ew import MsinEw
from mmul_gen.instructions.float_math.msqrt_ew import MsqrtEw
from mmul_gen.instructions.float_math.mtanh_ew import MtanhEw
from mmul_gen.instructions.integer_shift.msll_ew import MsllEw
from mmul_gen.instructions.integer_shift.msll_ew_x import MsllEwX
from mmul_gen.instructions.integer_shift.msra_ew import MsraEw
from mmul_gen.instructions.integer_shift.msra_ew_x import MsraEwX
from mmul_gen.instructions.integer_shift.msrl_ew import MsrlEw
from mmul_gen.instructions.integer_shift.msrl_ew_x import MsrlEwX
from mmul_gen.instructions.load_store.mls_1r import Mls1r
from mmul_gen.instructions.load_store.mss_1r import Mss1r
from mmul_gen.instructions.logexp.mexp2_ew import Mexp2Ew
from mmul_gen.instructions.logexp.mldexp_ew import MldexpEw
from mmul_gen.instructions.logexp.mldexp_ew_x import MldexpEwX
from mmul_gen.instructions.logexp.mldexpacc_ew import MldexpaccEw
from mmul_gen.instructions.logexp.mldexpacc_ew_x import MldexpaccEwX
from mmul_gen.instructions.logexp.mlog2_ew import Mlog2Ew
from mmul_gen.instructions.logexp.mlog2sub_ew import Mlog2subEw
from mmul_gen.instructions.logexp.mlog2sub_ew_x import Mlog2subEwX
from mmul_gen.instructions.logexp.mrdexp_ew import MrdexpEw
from mmul_gen.instructions.logexp.mrdexpacc_ew import MrdexpaccEw
from mmul_gen.instructions.logexp.msublog2_ew import Msublog2Ew
from mmul_gen.instructions.logexp.msublog2_ew_x import Msublog2EwX
from mmul_gen.instructions.matrix_ops.mcolgather_ew import McolgatherEw
from mmul_gen.instructions.matrix_ops.mcolscatadd_ew import McolscataddEw
from mmul_gen.instructions.matrix_ops.mcolscatmax_ew import McolscatmaxEw
from mmul_gen.instructions.matrix_ops.mcolunzip_ew import McolunzipEw
from mmul_gen.instructions.matrix_ops.mcolzip_ew import McolzipEw
from mmul_gen.instructions.matrix_ops.mprefixadd_col import MprefixaddCol
from mmul_gen.instructions.matrix_ops.mprefixadd_row import MprefixaddRow
from mmul_gen.instructions.matrix_ops.mprefixmax_col import MprefixmaxCol
from mmul_gen.instructions.matrix_ops.mprefixmax_row import MprefixmaxRow
from mmul_gen.instructions.matrix_ops.mreduceadd_col import MreduceaddCol
from mmul_gen.instructions.matrix_ops.mreduceadd_row import MreduceaddRow
from mmul_gen.instructions.matrix_ops.mreducemax_col import MreducemaxCol
from mmul_gen.instructions.matrix_ops.mreducemax_row import MreducemaxRow
from mmul_gen.instructions.matrix_ops.mreducemin_col import MreduceminCol
from mmul_gen.instructions.matrix_ops.mreducemin_row import MreduceminRow
from mmul_gen.instructions.matrix_ops.mrowgather_ew import MrowgatherEw
from mmul_gen.instructions.matrix_ops.mrowscatadd_ew import MrowscataddEw
from mmul_gen.instructions.matrix_ops.mrowscatmax_ew import MrowscatmaxEw
from mmul_gen.instructions.matrix_ops.mrowunzip_ew import MrowunzipEw
from mmul_gen.instructions.matrix_ops.mrowzip_ew import MrowzipEw
from mmul_gen.instructions.mconv.mconv_ew import MconvEw
from mmul_gen.instructions.memory_order.mls_cm import MlsCm
from mmul_gen.instructions.memory_order.mls_rm import MlsRm
from mmul_gen.instructions.memory_order.mss_cm import MssCm
from mmul_gen.instructions.memory_order.mss_rm import MssRm
from mmul_gen.instructions.mmul.mmulacc_2d import MmulAcc2d
from mmul_gen.instructions.mmul.mmulaccneg_2d import MmulAccNeg2d
from mmul_gen.instructions.mmul.mmulatacc_2d import MmulAtAcc2d
from mmul_gen.instructions.mmul.mmulataccneg_2d import MmulAtAccNeg2d
from mmul_gen.instructions.mmul.mmulbtacc_2d import MmulBtAcc2d
from mmul_gen.instructions.mmul.mmulbtaccneg_2d import MmulBtAccNeg2d
from mmul_gen.instructions.pack.mpack_ew_x import MpackEwX
from mmul_gen.instructions.pack.munpack_ew_x import MunpackEwX
from mmul_gen.instructions.strided_memory.mls_st import MlsSt
from mmul_gen.instructions.strided_memory.mls_tst import MlsTst
from mmul_gen.instructions.strided_memory.mss_st import MssSt
from mmul_gen.instructions.strided_memory.mss_tst import MssTst
from mmul_gen.instructions.type_register.agettyp import Agettyp
from mmul_gen.instructions.type_register.asettyp import Asettyp
from mmul_gen.instructions.type_register.mgettyp import Mgettyp
from mmul_gen.instructions.type_register.msettyp import Msettyp


__all__ = [
    "AccSpanExceptions",
    "Agettyp",
    "AmeAcquire",
    "AmeRelease",
    "Asettyp",
    "MabsEw",
    "MabsdiffEw",
    "MabsdiffEwX",
    "MaddEw",
    "MaddEwX",
    "MandEw",
    "MandEwX",
    "MandnotEw",
    "MandnotEwX",
    "MbcastMX",
    "McmovgeEw",
    "McmovltEw",
    "McmpgeEw",
    "McmpgeEwX",
    "McmpltEw",
    "McmpltEwX",
    "McolbcastEwX",
    "McolgatherEw",
    "McolidEw",
    "McolscataddEw",
    "McolscatmaxEw",
    "McolshiftEwX",
    "McolunzipEw",
    "McolzipEw",
    "MconvEw",
    "McosEw",
    "Mexp2Ew",
    "MfrintmEw",
    "MfrintnEw",
    "MfrintpEw",
    "MfrintzEw",
    "Mgettyp",
    "MhdiffEw",
    "MhdiffEwX",
    "MldexpEw",
    "MldexpEwX",
    "MldexpaccEw",
    "MldexpaccEwX",
    "Mlog2Ew",
    "Mlog2subEw",
    "Mlog2subEwX",
    "Mls1r",
    "MlsCm",
    "MlsRm",
    "MlsSt",
    "MlsTst",
    "MmaxEw",
    "MmaxEwX",
    "MmeanEw",
    "MmeanEwX",
    "MminEw",
    "MminEwX",
    "MmovAM",
    "MmovAMAccSpan",
    "MmovMA",
    "MmovMAAccSpan",
    "MmovMM",
    "Mmove16MX",
    "Mmove16XM",
    "Mmove32MX",
    "Mmove32XM",
    "Mmove64MX",
    "Mmove64XM",
    "Mmove8MX",
    "Mmove8XM",
    "MmulAcc2d",
    "MmulAccNeg2d",
    "MmulAtAcc2d",
    "MmulAtAccNeg2d",
    "MmulBtAcc2d",
    "MmulBtAccNeg2d",
    "MmulEw",
    "MmulEwX",
    "MmulaccEw",
    "MmulaccEwX",
    "MmulaccnegEw",
    "MmulaccnegEwX",
    "MmuladdEw",
    "MmuladdEwX",
    "MmulnegEw",
    "MmulnegEwX",
    "MmulsubEw",
    "MmulsubEwX",
    "MorEw",
    "MorEwX",
    "MornotEw",
    "MornotEwX",
    "MpackEwX",
    "MprefixaddCol",
    "MprefixaddRow",
    "MprefixmaxCol",
    "MprefixmaxRow",
    "MrdexpEw",
    "MrdexpaccEw",
    "MrecEw",
    "MreduceaddCol",
    "MreduceaddRow",
    "MreducemaxCol",
    "MreducemaxRow",
    "MreduceminCol",
    "MreduceminRow",
    "MrowbcastEwX",
    "MrowgatherEw",
    "MrowidEw",
    "MrowscataddEw",
    "MrowscatmaxEw",
    "MrowshiftEwX",
    "MrowunzipEw",
    "MrowzipEw",
    "MrsqrtEw",
    "MselgeEw",
    "MselltEw",
    "Msettyp",
    "MsinEw",
    "MsllEw",
    "MsllEwX",
    "MsqrtEw",
    "MsraEw",
    "MsraEwX",
    "MsrlEw",
    "MsrlEwX",
    "Mss1r",
    "MssCm",
    "MssRm",
    "MssSt",
    "MssTst",
    "MsubEw",
    "MsubEwX",
    "Msublog2Ew",
    "Msublog2EwX",
    "MtanhEw",
    "MunpackEwX",
    "MxorEw",
    "MxorEwX",
    "Mzero2dAcc",
    "Mzero2dM",
]
