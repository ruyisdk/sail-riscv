# Copyright (c) Qualcomm Technologies, Inc. and/or its subsidiaries.
# SPDX-License-Identifier: BSD-3-Clause-Clear
#
# AME assembly:
#   msettyp m0, t0
#   mgettyp t1, m0

.include "test.inc"
.include "ame_macros.inc"

.text

    li    t0, AME_INT8_DTYPE
    msettyp m0, t0
    mgettyp t1, m0

    EXPECT t1, AME_INT8_DTYPE

    RVMODEL_HALT_PASS
