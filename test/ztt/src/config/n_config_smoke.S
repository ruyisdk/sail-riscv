# Copyright (c) Qualcomm Technologies, Inc. and/or its subsidiaries.
# SPDX-License-Identifier: BSD-3-Clause-Clear
#
# Runtime-dynamic smoke for focused Ztt configuration coverage.  CMake compiles
# this source once and runs the same ELF with N=4/16/32 and UDS=8/16/32.

.include "test.inc"
.include "ame_macros.inc"

.text

    li      t0, 0
    ame.acquire t1, t0
    EXPECT t1, 1

    csrr    t0, amenlen
    csrr    t1, ameudsz

    # The focused matrix covers three square sizes and three UDS values.
    li      t2, 4
    beq     t0, t2, .Lvalid_n
    li      t2, 16
    beq     t0, t2, .Lvalid_n
    li      t2, 32
    bne     t0, t2, .Lfail
.Lvalid_n:
    li      t2, 8
    beq     t1, t2, .Lvalid_dims
    li      t2, 16
    beq     t1, t2, .Lvalid_dims
    li      t2, 32
    bne     t1, t2, .Lfail

.Lvalid_dims:
    # A UINT8 square uses UDS/8 packed slots.  The formed UINT16 operand has
    # that many logical squares and therefore occupies two physical M
    # registers for every tested UDS.
    mul     t5, t0, t0
    srli    t6, t1, 3
    mul     a2, t5, t6             # Bytes in one physical M register.
    slli    t5, a2, 1              # Bytes in the formed UINT16 operand.

    la      t3, input_u8
    li      t4, 0
.Lfill_u8:
    beq     t4, a2, .Lfill_u8_done
    add     t6, t3, t4
    li      a0, 1
    sb      a0, 0(t6)
    addi    t4, t4, 1
    j       .Lfill_u8
.Lfill_u8_done:
    la      t3, input_u16
    li      t4, 0
.Lfill_u16:
    beq     t4, t5, .Lfill_u16_done
    add     t6, t3, t4
    li      a0, 2                 # Each UINT16 element is 0x0202.
    sb      a0, 0(t6)
    addi    t4, t4, 1
    j       .Lfill_u16
.Lfill_u16_done:

    li      t0, AME_UINT8_DTYPE
    msettyp m0, t0
    li      t0, AME_UINT16_DTYPE
    msettyp m2, t0
    msettyp m4, t0
    li      t2, 8
    beq     t1, t2, .Ltypes_set
    msettyp m3, t0
    msettyp m5, t0
.Ltypes_set:

    la      t3, input_u8
    mls.rm  m0, t3
    la      t3, input_u16
    mls.rm  m2, t3
    li      t0, 8
    beq     t1, t0, .Linput_u16_loaded
    add     t3, t3, a2
    mls.rm  m3, t3
.Linput_u16_loaded:
    madd.ew m4, m0, m2

    la      t3, output_u16
    mss.rm  m4, t3
    li      t0, 8
    beq     t1, t0, .Loutput_u16_stored
    add     t3, t3, a2
    mss.rm  m5, t3
    la      t3, output_u16
.Loutput_u16_stored:

    li      t4, 0
.Lcheck_byte:
    beq     t4, t5, .Lcheck_strided
    add     t6, t3, t4
    lbu     a0, 0(t6)
    andi    a1, t4, 1
    bnez    a1, .Lexpect_high_byte
    li      a1, 3                 # 0x0202 + 0x0001 = 0x0203.
    j       .Lcompare_byte
.Lexpect_high_byte:
    li      a1, 2
.Lcompare_byte:
    bne     a0, a1, .Lfail
    addi    t4, t4, 1
    j       .Lcheck_byte

.Lcheck_strided:
    # UINT4 is packed by 2/4/8 for UDS=8/16/32.  A transposed strided
    # transfer has pack_factor*N segments.  Round-trip every active byte so
    # the UDS=32 case specifically reaches all 8*N segments.
    csrr    t0, amenlen
    csrr    t1, ameudsz
    srli    t5, t1, 2
    mul     t5, t5, t0             # Segment count.
    slli    a2, t5, 4              # 16-byte stride region size.
    la      t3, strided_u4_input
    la      t6, strided_u4_output
    li      t4, 0
.Lfill_strided:
    beq     t4, a2, .Lfill_strided_done
    add     a0, t3, t4
    sb      t4, 0(a0)
    add     a0, t6, t4
    li      a1, 0xa5
    sb      a1, 0(a0)
    addi    t4, t4, 1
    j       .Lfill_strided
.Lfill_strided_done:
    li      t2, AME_UINT4_DTYPE
    msettyp m8, t2
    li      t2, 16
    mls.tst m8, t3, t2
    mss.tst m8, t6, t2

    srli    a2, t0, 1              # Active bytes per segment.
    li      t4, 0
.Lcheck_segment:
    beq     t4, t5, .Lpass
    li      a0, 0
.Lcheck_segment_byte:
    beq     a0, a2, .Lnext_segment
    slli    a1, t4, 4
    add     a1, a1, a0
    add     t2, t3, a1
    lbu     t2, 0(t2)
    add     a1, t6, a1
    lbu     a1, 0(a1)
    bne     t2, a1, .Lfail
    addi    a0, a0, 1
    j       .Lcheck_segment_byte
.Lnext_segment:
    addi    t4, t4, 1
    j       .Lcheck_segment

.Lpass:
    RVMODEL_HALT_PASS

.Lfail:
    RVMODEL_HALT_FAIL

.bss
# N=32/UDS=32 requires 4 KiB per physical M register and 8 KiB for the
# complete formed UINT16 source or destination.  The 4 KiB alignment also
# satisfies the AME memory alignment rule for that case.
.balign 4096
input_u8:
    .space 4096
.balign 4096
input_u16:
    .space 8192
.balign 4096
output_u16:
    .space 8192
.balign 4096
strided_u4_input:
    .space 4096
.balign 4096
strided_u4_output:
    .space 4096
