# Copyright (c) Qualcomm Technologies, Inc. and/or its subsidiaries.
# SPDX-License-Identifier: BSD-3-Clause-Clear
#
# Bare-metal unit-datatype GEMM example.
#
# This test uses the manual square-format GEMM control flow and checks the
# first stored output element. The matrix shape is 128x128, but the AME square
# size is read from amenlen so the same code follows the active model config.
# With A and B filled with 1, one 128-wide dot product yields 128 for
# AME_UINT8_DTYPE; the first eight output bytes are therefore 0x80.
#
# AME assembly:
#   msettyp m0, a6
#   msettyp m1, a6
#   asettyp acc0, a6
#   mzero.2d.acc acc0
#   mls.rm m0, t4
#   mls.rm m1, t5
#   mmulacc.2d acc0, m0, m1
#   mmov.m.a m0, acc0
#   mss.rm m0, a6

.include "test.inc"
.include "ame_macros.inc"

.text

    li     t0, 0
    ame.acquire t1, t0
    EXPECT t1, 1

    la     a0, c_square
    li     a1, 128
    la     a2, a_square
    li     a3, 128
    la     a4, b_square
    li     a5, 128
    li     a6, AME_UINT8_DTYPE

    j      gemm_unit_dtype

.check_gemm_unit_dtype:
    ld     t0, 0(a0)
    EXPECT t0, 0x8080808080808080

    RVMODEL_HALT_PASS

# GEMM (square format, unit dtype): C[MxP] += A[MxK] * B[KxP]
# Unit-datatype square-format GEMM. This test requires AME_UNIT_DATATYPE_SIZE=8
# so AME_UINT8_DTYPE is a compute dtype and group_size=1.
#
# Arguments:   a0=*C  a1=M  a2=*A  a3=K  a4=*B  a5=P  a6=dtype
# Callee-saved: s2-s4 strides, s5-s7 loop-invariant ptrs/counter
# Scratch:      t0=N
#               t2=j  t4=A-square ptr  t5=B-square ptr
#               t6=k  ra=k-bound scratch
#               a6 reused as C-square ptr after dtype setup
#               a7 used as B-col-base ptr in j loop

gemm_unit_dtype:

    # step 1: discover N and verify this is the unit-datatype config
    csrr   t0, amenlen            # t0 = N = sqrt(AME_NELEM)
    csrr   t1, ameudsz            # t1 = AME_UNIT_DATATYPE_SIZE in bits
    li     t3, 8
    bne    t1, t3, .unsupported_config
    # group_size = 1 (dtype_bits = U = 8); elem_bytes = 1

    # step 2: configure datatypes
    # group_size = 1: A->m0, B->m1
    msettyp m0, a6
    msettyp m1, a6
    asettyp acc0, a6

    # step 3: compute loop-invariant square strides
    # elem_bytes = 1, so strides are pure element counts
    mul    s4, t0, t0             # s4 = sq_bytes  (= N^2)
    mul    s2, a3, t0             # s2 = K x N (A: one i-square down)
    mul    s3, a5, t0             # s3 = P x N (C/B: one square down)

    # step 4: initialize outer-loop state
    mv     s5, a0                 # s5 = C row-base ptr
    mv     s6, a2                 # s6 = A row-base ptr
    li     s7, 0                  # i  = 0 (rows consumed)

.i_loop:
    sub    t1, a1, s7
    blez   t1, .done

    mv     a6, s5                 # a6 = C square ptr
    mv     a7, a4                 # a7 = B col-base ptr
    li     t2, 0                  # j  = 0

.j_loop:
    sub    t3, a5, t2
    blez   t3, .j_done

    mzero.2d.acc acc0

    mv     t4, s6                 # t4 = A square ptr
    mv     t5, a7                 # t5 = B square ptr
    li     t6, 0                  # k  = 0

.k_loop:
    sub    ra, a3, t6
    blez   ra, .k_done

    mls.rm  m0, t4                # load A[i,k] square
    mls.rm  m1, t5                # load B[k,j] square
    mmulacc.2d  acc0, m0, m1      # acc0 += A_square x B_square

    add    t4, t4, s4             # A ptr: advance one k-square right
    add    t5, t5, s3             # B ptr: advance one k-square down
    add    t6, t6, t0             # k += N
    j      .k_loop

.k_done:
    mmov.m.a m0, acc0
    mss.rm  m0, a6                # store result square to C

    add    a6, a6, s4             # C ptr: advance one j-square right
    add    a7, a7, s4             # B col-base: advance one j-square right
    add    t2, t2, t0             # j += N
    j      .j_loop

.j_done:
    add    s5, s5, s3             # C row-base: advance one i-square down
    add    s6, s6, s2             # A row-base: advance one i-square down
    add    s7, s7, t0             # i += N
    j      .i_loop

.done:
    j      .check_gemm_unit_dtype

.unsupported_config:
    RVMODEL_HALT_FAIL

.data
.balign 16384
a_square:
    .rept 16384
    .byte 1
    .endr
.balign 16384
b_square:
    .rept 16384
    .byte 1
    .endr
.balign 16384
c_square:
    .rept 16384
    .byte 0xa5
    .endr
