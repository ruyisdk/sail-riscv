# Minimal case: 128-bit `mhdiff.ew.x` rounding direction (n8/uds16/m32).
#
# This file pins the generated case (case 51: INT128 small values,
# scalar=10, B=5) with no other stimulus, so the rounding direction of
# 128-bit `mhdiff.ew.x` is checked deterministically on both simulators.
#
# Manual semantics: D[i] = (B[i] - c) / 2 with RNU rounding.
#   (5 - 10) / 2 = -2.5  ->  RNU  ->  -2  ->  0xFF..FE per element.

.include "test.inc"
.include "ame_macros.inc"

.text

    li      t0, 0
    ame.acquire t1, t0
    EXPECT  t1, 1

    li      t0, AME_INT128_DTYPE
    msettyp m0, t0
    msettyp m16, t0
    csrw    amestype, t0

    li      t4, 10
    la      t2, b_square
    mls.rm  m0, t2
    mhdiff.ew.x m16, t4, m0
    la      t3, dst_square
    mss.rm  m16, t3

    # Element 0 (bytes 0-15): 0xFE 0xFF*15
    la      t3, dst_square
    lbu     t4, 0(t3)
    EXPECT  t4, 0xFE
    lbu     t4, 1(t3)
    EXPECT  t4, 0xFF
    lbu     t4, 15(t3)
    EXPECT  t4, 0xFF
    # Element 63 (bytes 1008-1023)
    lbu     t4, 1008(t3)
    EXPECT  t4, 0xFE
    lbu     t4, 1009(t3)
    EXPECT  t4, 0xFF
    lbu     t4, 1023(t3)
    EXPECT  t4, 0xFF

    RVMODEL_HALT_PASS

.data
.balign 4096
# 64 INT128 elements, each equal to 5.
b_square:
    .rept 64
    .byte 0x05, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0
    .endr
.balign 4096
dst_square:
    .rept 64
    .byte 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0
    .endr
