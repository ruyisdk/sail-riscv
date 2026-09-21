# Ztt assembler macros for GNU GAS
# Auto-generated from manual-main/instructions.json - DO NOT EDIT BY HAND.
# Regenerate with generators/gen_ztt_macros.rb.

# Usage: .include "ame_macros.inc"

# ── AME CSR numbers ──────────────────────────────────────────────────────────
.equ amenlen,          0xCC0
.equ ameudsz,          0xCC1
.equ ame_scalar_dtype, 0xCC2
.equ ameown,           0xCC3
.equ amefflags,        0xCC4
.equ amexsat,          0xCC5
.equ amestatus,        0x800

# ── AME datatype constants ────────────────────────────────────────────────────
# Integer types (bit 30=sign, bit 29=sat, bit 8=0, bits 7:0=size)
.equ AME_UINT4_DTYPE,      0x00000004
.equ AME_INT4_DTYPE,       0x40000004
.equ AME_UINT8_DTYPE,      0x00000008
.equ AME_INT8_DTYPE,       0x40000008
.equ AME_UINT16_DTYPE,     0x00000010
.equ AME_INT16_DTYPE,      0x40000010
.equ AME_UINT32_DTYPE,     0x00000020
.equ AME_INT32_DTYPE,      0x40000020
.equ AME_UINT64_DTYPE,     0x00000040
.equ AME_INT64_DTYPE,      0x40000040
.equ AME_UINT128_DTYPE,    0x00000080
.equ AME_INT128_DTYPE,     0x40000080
# Saturating integer types (bit 29=1)
.equ AME_UINT4_SAT_DTYPE,  0x20000004
.equ AME_INT4_SAT_DTYPE,   0x60000004
.equ AME_UINT8_SAT_DTYPE,  0x20000008
.equ AME_INT8_SAT_DTYPE,   0x60000008
.equ AME_UINT16_SAT_DTYPE, 0x20000010
.equ AME_INT16_SAT_DTYPE,  0x60000010
.equ AME_UINT32_SAT_DTYPE, 0x20000020
.equ AME_INT32_SAT_DTYPE,  0x60000020
.equ AME_UINT64_SAT_DTYPE, 0x20000040
.equ AME_INT64_SAT_DTYPE,  0x60000040
.equ AME_UINT128_SAT_DTYPE,0x20000080
.equ AME_INT128_SAT_DTYPE, 0x60000080
# Floating-point types (bit 8=1; bits 25:22=rounding, default=RNE=0)
# To use a non-default rounding mode: AME_FP32_DTYPE | AME_RND_RTZ
.equ AME_FP16_DTYPE,       0x14300110
.equ AME_BF16_DTYPE,       0x20300110
.equ AME_FP32_DTYPE,       0x20300120
.equ AME_FP64_DTYPE,       0x2c300140
.equ AME_OCP_E4M3_DTYPE,   0x10100108
.equ AME_OCP_E5M2_DTYPE,   0x14300108
# Floating-point rounding modes (bits 25:22); OR into a float dtype constant
.equ AME_RND_RNE,          0x00000000
.equ AME_RND_RTZ,          0x00400000
.equ AME_RND_RDN,          0x00800000
.equ AME_RND_RUP,          0x00c00000
.equ AME_RND_RMM,          0x01000000
.equ AME_RND_RNO,          0x01400000

# ── M-register numbers (m0–m31) ──────────────────────────────────────────────
.equ m0,  0;  .equ m1,  1;  .equ m2,  2;  .equ m3,  3
.equ m4,  4;  .equ m5,  5;  .equ m6,  6;  .equ m7,  7
.equ m8,  8;  .equ m9,  9;  .equ m10,10;  .equ m11, 11
.equ m12,12;  .equ m13,13;  .equ m14,14;  .equ m15, 15
.equ m16,16;  .equ m17,17;  .equ m18,18;  .equ m19, 19
.equ m20,20;  .equ m21,21;  .equ m22,22;  .equ m23, 23
.equ m24,24;  .equ m25,25;  .equ m26,26;  .equ m27, 27
.equ m28,28;  .equ m29,29;  .equ m30,30;  .equ m31, 31

# ── Acc-register numbers (acc0–acc31) ────────────────────────────────────────
.equ acc0, 0;  .equ acc1, 1;  .equ acc2, 2;  .equ acc3, 3
.equ acc4, 4;  .equ acc5, 5;  .equ acc6, 6;  .equ acc7, 7
.equ acc8, 8;  .equ acc9, 9;  .equ acc10,10; .equ acc11,11
.equ acc12,12; .equ acc13,13; .equ acc14,14; .equ acc15,15
.equ acc16,16; .equ acc17,17; .equ acc18,18; .equ acc19,19
.equ acc20,20; .equ acc21,21; .equ acc22,22; .equ acc23,23
.equ acc24,24; .equ acc25,25; .equ acc26,26; .equ acc27,27
.equ acc28,28; .equ acc29,29; .equ acc30,30; .equ acc31,31

# ── Integer register numbers ──────────────────────────────────────────────────
# Needed so ABI names resolve as numeric values inside .insn expressions.
# GAS register parsing still takes precedence in instruction operand contexts.
# Both ABI names (zero, ra, …) and xN names (x0, x1, …) are defined.
.equ zero, 0; .equ ra,  1;  .equ sp,  2;  .equ gp,  3;  .equ tp,  4
.equ t0,   5; .equ t1,  6;  .equ t2,  7;  .equ s0,  8;  .equ fp,  8;  .equ s1,  9
.equ a0,  10; .equ a1, 11;  .equ a2, 12;  .equ a3, 13
.equ a4,  14; .equ a5, 15;  .equ a6, 16;  .equ a7, 17
.equ s2,  18; .equ s3, 19;  .equ s4, 20;  .equ s5, 21
.equ s6,  22; .equ s7, 23;  .equ s8, 24;  .equ s9, 25
.equ s10, 26; .equ s11,27
.equ t3,  28; .equ t4, 29;  .equ t5, 30;  .equ t6, 31
.equ x0,   0; .equ x1,  1;  .equ x2,  2;  .equ x3,  3;  .equ x4,  4
.equ x5,   5; .equ x6,  6;  .equ x7,  7;  .equ x8,  8;  .equ x9,  9
.equ x10, 10; .equ x11,11;  .equ x12,12;  .equ x13,13;  .equ x14,14
.equ x15, 15; .equ x16,16;  .equ x17,17;  .equ x18,18;  .equ x19,19
.equ x20, 20; .equ x21,21;  .equ x22,22;  .equ x23,23;  .equ x24,24
.equ x25, 25; .equ x26,26;  .equ x27,27;  .equ x28,28;  .equ x29,29
.equ x30, 30; .equ x31,31

# ── Float register numbers ────────────────────────────────────────────────────
.equ ft0,  0; .equ ft1,  1; .equ ft2,  2; .equ ft3,  3
.equ ft4,  4; .equ ft5,  5; .equ ft6,  6; .equ ft7,  7
.equ fs0,  8; .equ fs1,  9
.equ fa0, 10; .equ fa1, 11; .equ fa2, 12; .equ fa3, 13
.equ fa4, 14; .equ fa5, 15; .equ fa6, 16; .equ fa7, 17
.equ fs2, 18; .equ fs3, 19; .equ fs4, 20; .equ fs5, 21
.equ fs6, 22; .equ fs7, 23; .equ fs8, 24; .equ fs9, 25
.equ fs10,26; .equ fs11,27
.equ ft8, 28; .equ ft9, 29; .equ ft10,30; .equ ft11,31

# ── Instruction macros ────────────────────────────────────────────────────────
# ame.acquire rd, rs1
.macro ame.acquire rd, rs1
    .insn 4, (0xa490002b | ((\rd) << 7) | ((\rs1) << 15))
.endm
# ame.release
.macro ame.release
    .insn 4, (0xa4a0002b)
.endm
# agettyp rd, ad
.macro agettyp rd, ad
    .insn 4, (0xa200002b | ((\rd) << 7) | ((\ad) << 15))
.endm
# asettyp ad, rs1
.macro asettyp ad, rs1
    .insn 4, (0xa210002b | ((\ad) << 7) | ((\rs1) << 15))
.endm
# mabs.ew md, ms1
.macro mabs.ew md, ms1
    .insn 4, (0xa240002b | ((\md) << 7) | ((\ms1) << 15))
.endm
# mabsdiff.ew md, ms1, ms2
.macro mabsdiff.ew md, ms1, ms2
    .insn 4, (0x0000002b | ((\md) << 7) | ((\ms1) << 15) | ((\ms2) << 20))
.endm
# mabsdiff.ew.x md, rs1, ms2
.macro mabsdiff.ew.x md, rs1, ms2
    .insn 4, (0x0200002b | ((\md) << 7) | ((\rs1) << 15) | ((\ms2) << 20))
.endm
# madd.ew md, ms1, ms2
.macro madd.ew md, ms1, ms2
    .insn 4, (0x0400002b | ((\md) << 7) | ((\ms1) << 15) | ((\ms2) << 20))
.endm
# madd.ew.x md, rs1, ms2
.macro madd.ew.x md, rs1, ms2
    .insn 4, (0x0600002b | ((\md) << 7) | ((\rs1) << 15) | ((\ms2) << 20))
.endm
# mand.ew md, ms1, ms2
.macro mand.ew md, ms1, ms2
    .insn 4, (0x3400002b | ((\md) << 7) | ((\ms1) << 15) | ((\ms2) << 20))
.endm
# mand.ew.x md, rs1, ms2
.macro mand.ew.x md, rs1, ms2
    .insn 4, (0x3600002b | ((\md) << 7) | ((\rs1) << 15) | ((\ms2) << 20))
.endm
# mandnot.ew md, ms1, ms2
.macro mandnot.ew md, ms1, ms2
    .insn 4, (0x3800002b | ((\md) << 7) | ((\ms1) << 15) | ((\ms2) << 20))
.endm
# mandnot.ew.x md, rs1, ms2
.macro mandnot.ew.x md, rs1, ms2
    .insn 4, (0x3a00002b | ((\md) << 7) | ((\rs1) << 15) | ((\ms2) << 20))
.endm
# mcmovge.ew md, ms1, ms2
.macro mcmovge.ew md, ms1, ms2
    .insn 4, (0x5400002b | ((\md) << 7) | ((\ms1) << 15) | ((\ms2) << 20))
.endm
# mcmovlt.ew md, ms1, ms2
.macro mcmovlt.ew md, ms1, ms2
    .insn 4, (0x5600002b | ((\md) << 7) | ((\ms1) << 15) | ((\ms2) << 20))
.endm
# mcmpge.ew md, ms1, ms2
.macro mcmpge.ew md, ms1, ms2
    .insn 4, (0x5800002b | ((\md) << 7) | ((\ms1) << 15) | ((\ms2) << 20))
.endm
# mcmpge.ew.x md, rs1, ms2
.macro mcmpge.ew.x md, rs1, ms2
    .insn 4, (0x5a00002b | ((\md) << 7) | ((\rs1) << 15) | ((\ms2) << 20))
.endm
# mcmplt.ew md, ms1, ms2
.macro mcmplt.ew md, ms1, ms2
    .insn 4, (0x5c00002b | ((\md) << 7) | ((\ms1) << 15) | ((\ms2) << 20))
.endm
# mcmplt.ew.x md, rs1, ms2
.macro mcmplt.ew.x md, rs1, ms2
    .insn 4, (0x5e00002b | ((\md) << 7) | ((\rs1) << 15) | ((\ms2) << 20))
.endm
# mcolbcast.ew.x md, rs1, ms2
.macro mcolbcast.ew.x md, rs1, ms2
    .insn 4, (0x6400002b | ((\md) << 7) | ((\rs1) << 15) | ((\ms2) << 20))
.endm
# mcolgather.ew md, ms1, ms2
.macro mcolgather.ew md, ms1, ms2
    .insn 4, (0x6600002b | ((\md) << 7) | ((\ms1) << 15) | ((\ms2) << 20))
.endm
# mcolid.ew md
.macro mcolid.ew md
    .insn 4, (0xa601002b | ((\md) << 7))
.endm
# mcolshift.ew.x md, rs1, ms2
.macro mcolshift.ew.x md, rs1, ms2
    .insn 4, (0x6800002b | ((\md) << 7) | ((\rs1) << 15) | ((\ms2) << 20))
.endm
# mcolunzip.ew ms1, ms2
.macro mcolunzip.ew ms1, ms2
    .insn 4, (0xc200002b | ((\ms1) << 15) | ((\ms2) << 20))
.endm
# mcolzip.ew ms1, ms2
.macro mcolzip.ew ms1, ms2
    .insn 4, (0xc400002b | ((\ms1) << 15) | ((\ms2) << 20))
.endm
# mconv.ew md, ms1
.macro mconv.ew md, ms1
    .insn 4, (0xa2d0002b | ((\md) << 7) | ((\ms1) << 15))
.endm
# mbcast.m.x md, rs1, rs2
.macro mbcast.m.x md, rs1, rs2
    .insn 4, (0xb000002b | ((\md) << 7) | ((\rs1) << 15) | ((\rs2) << 20))
.endm
# mcos.ew md, ms1
.macro mcos.ew md, ms1
    .insn 4, (0xa2e0002b | ((\md) << 7) | ((\ms1) << 15))
.endm
# mexp2.ew md, ms1
.macro mexp2.ew md, ms1
    .insn 4, (0xa2f0002b | ((\md) << 7) | ((\ms1) << 15))
.endm
# mfrintm.ew md, ms1
.macro mfrintm.ew md, ms1
    .insn 4, (0xa250002b | ((\md) << 7) | ((\ms1) << 15))
.endm
# mfrintn.ew md, ms1
.macro mfrintn.ew md, ms1
    .insn 4, (0xa260002b | ((\md) << 7) | ((\ms1) << 15))
.endm
# mfrintp.ew md, ms1
.macro mfrintp.ew md, ms1
    .insn 4, (0xa270002b | ((\md) << 7) | ((\ms1) << 15))
.endm
# mfrintz.ew md, ms1
.macro mfrintz.ew md, ms1
    .insn 4, (0xa280002b | ((\md) << 7) | ((\ms1) << 15))
.endm
# mgettyp rd, ms1
.macro mgettyp rd, ms1
    .insn 4, (0xa220002b | ((\rd) << 7) | ((\ms1) << 15))
.endm
# mhdiff.ew md, ms1, ms2
.macro mhdiff.ew md, ms1, ms2
    .insn 4, (0x0800002b | ((\md) << 7) | ((\ms1) << 15) | ((\ms2) << 20))
.endm
# mhdiff.ew.x md, rs1, ms2
.macro mhdiff.ew.x md, rs1, ms2
    .insn 4, (0x0a00002b | ((\md) << 7) | ((\rs1) << 15) | ((\ms2) << 20))
.endm
# mldexp.ew md, ms1, ms2
.macro mldexp.ew md, ms1, ms2
    .insn 4, (0x7e00002b | ((\md) << 7) | ((\ms1) << 15) | ((\ms2) << 20))
.endm
# mldexp.ew.x md, rs1, ms2
.macro mldexp.ew.x md, rs1, ms2
    .insn 4, (0x8000002b | ((\md) << 7) | ((\rs1) << 15) | ((\ms2) << 20))
.endm
# mldexpacc.ew md, ms1, ms2
.macro mldexpacc.ew md, ms1, ms2
    .insn 4, (0x8200002b | ((\md) << 7) | ((\ms1) << 15) | ((\ms2) << 20))
.endm
# mldexpacc.ew.x md, rs1, ms2
.macro mldexpacc.ew.x md, rs1, ms2
    .insn 4, (0x8400002b | ((\md) << 7) | ((\rs1) << 15) | ((\ms2) << 20))
.endm
# mlog2.ew md, ms1
.macro mlog2.ew md, ms1
    .insn 4, (0xa300002b | ((\md) << 7) | ((\ms1) << 15))
.endm
# mlog2sub.ew md, ms1, ms2
.macro mlog2sub.ew md, ms1, ms2
    .insn 4, (0x8600002b | ((\md) << 7) | ((\ms1) << 15) | ((\ms2) << 20))
.endm
# mlog2sub.ew.x md, rs1, ms2
.macro mlog2sub.ew.x md, rs1, ms2
    .insn 4, (0x8800002b | ((\md) << 7) | ((\rs1) << 15) | ((\ms2) << 20))
.endm
# mls.1r md, rs1
.macro mls.1r md, rs1
    .insn 4, (0xa360002b | ((\md) << 7) | ((\rs1) << 15))
.endm
# mls.cm md, rs1
.macro mls.cm md, rs1
    .insn 4, (0xa370002b | ((\md) << 7) | ((\rs1) << 15))
.endm
# mls.rm md, rs1
.macro mls.rm md, rs1
    .insn 4, (0xa380002b | ((\md) << 7) | ((\rs1) << 15))
.endm
# mls.st md, (rs1), rs2
.macro mls.st md, rs1, rs2
    .insn 4, (0xa800002b | ((\md) << 7) | ((\rs1) << 15) | ((\rs2) << 20))
.endm
# mls.tst md, (rs1), rs2
.macro mls.tst md, rs1, rs2
    .insn 4, (0xaa00002b | ((\md) << 7) | ((\rs1) << 15) | ((\rs2) << 20))
.endm
# mmax.ew md, ms1, ms2
.macro mmax.ew md, ms1, ms2
    .insn 4, (0x0c00002b | ((\md) << 7) | ((\ms1) << 15) | ((\ms2) << 20))
.endm
# mmax.ew.x md, rs1, ms2
.macro mmax.ew.x md, rs1, ms2
    .insn 4, (0x0e00002b | ((\md) << 7) | ((\rs1) << 15) | ((\ms2) << 20))
.endm
# mmean.ew md, ms1, ms2
.macro mmean.ew md, ms1, ms2
    .insn 4, (0x1000002b | ((\md) << 7) | ((\ms1) << 15) | ((\ms2) << 20))
.endm
# mmean.ew.x md, rs1, ms2
.macro mmean.ew.x md, rs1, ms2
    .insn 4, (0x1200002b | ((\md) << 7) | ((\rs1) << 15) | ((\ms2) << 20))
.endm
# mmin.ew md, ms1, ms2
.macro mmin.ew md, ms1, ms2
    .insn 4, (0x1400002b | ((\md) << 7) | ((\ms1) << 15) | ((\ms2) << 20))
.endm
# mmin.ew.x md, rs1, ms2
.macro mmin.ew.x md, rs1, ms2
    .insn 4, (0x1600002b | ((\md) << 7) | ((\rs1) << 15) | ((\ms2) << 20))
.endm
# mmov.m.a md, acc
.macro mmov.m.a md, acc
    .insn 4, (0xa3c0002b | ((\md) << 7) | ((\acc) << 15))
.endm
# mmov.a.m acc, ms
.macro mmov.a.m acc, ms
    .insn 4, (0xa3d0002b | ((\acc) << 7) | ((\ms) << 15))
.endm
# mmov.m.m md, ms
.macro mmov.m.m md, ms
    .insn 4, (0xa3e0002b | ((\md) << 7) | ((\ms) << 15))
.endm
# mmove8.m.x md, rs2, rs1
.macro mmove8.m.x md, rs2, rs1
    .insn 4, (0xb200002b | ((\md) << 7) | ((\rs2) << 15) | ((\rs1) << 20))
.endm
# mmove16.m.x md, rs2, rs1
.macro mmove16.m.x md, rs2, rs1
    .insn 4, (0xb400002b | ((\md) << 7) | ((\rs2) << 15) | ((\rs1) << 20))
.endm
# mmove32.m.x md, rs2, rs1
.macro mmove32.m.x md, rs2, rs1
    .insn 4, (0xb600002b | ((\md) << 7) | ((\rs2) << 15) | ((\rs1) << 20))
.endm
# mmove64.m.x md, rs2, rs1
.macro mmove64.m.x md, rs2, rs1
    .insn 4, (0xb800002b | ((\md) << 7) | ((\rs2) << 15) | ((\rs1) << 20))
.endm
# mmove8.x.m rd, ms2, rs1
.macro mmove8.x.m rd, ms2, rs1
    .insn 4, (0xba00002b | ((\rd) << 7) | ((\ms2) << 15) | ((\rs1) << 20))
.endm
# mmove16.x.m rd, ms2, rs1
.macro mmove16.x.m rd, ms2, rs1
    .insn 4, (0xbc00002b | ((\rd) << 7) | ((\ms2) << 15) | ((\rs1) << 20))
.endm
# mmove32.x.m rd, ms2, rs1
.macro mmove32.x.m rd, ms2, rs1
    .insn 4, (0xbe00002b | ((\rd) << 7) | ((\ms2) << 15) | ((\rs1) << 20))
.endm
# mmove64.x.m rd, ms2, rs1
.macro mmove64.x.m rd, ms2, rs1
    .insn 4, (0xc000002b | ((\rd) << 7) | ((\ms2) << 15) | ((\rs1) << 20))
.endm
# mmul.ew md, ms1, ms2
.macro mmul.ew md, ms1, ms2
    .insn 4, (0x1800002b | ((\md) << 7) | ((\ms1) << 15) | ((\ms2) << 20))
.endm
# mmul.ew.x md, rs1, ms2
.macro mmul.ew.x md, rs1, ms2
    .insn 4, (0x1a00002b | ((\md) << 7) | ((\rs1) << 15) | ((\ms2) << 20))
.endm
# mmulacc.2d acc, ms1, ms2
.macro mmulacc.2d acc, ms1, ms2
    .insn 4, (0x9400002b | ((\acc) << 7) | ((\ms1) << 15) | ((\ms2) << 20))
.endm
# mmulacc.ew md, ms1, ms2
.macro mmulacc.ew md, ms1, ms2
    .insn 4, (0x1c00002b | ((\md) << 7) | ((\ms1) << 15) | ((\ms2) << 20))
.endm
# mmulacc.ew.x md, rs1, ms2
.macro mmulacc.ew.x md, rs1, ms2
    .insn 4, (0x1e00002b | ((\md) << 7) | ((\rs1) << 15) | ((\ms2) << 20))
.endm
# mmulaccneg.2d acc, ms1, ms2
.macro mmulaccneg.2d acc, ms1, ms2
    .insn 4, (0x9600002b | ((\acc) << 7) | ((\ms1) << 15) | ((\ms2) << 20))
.endm
# mmulaccneg.ew md, ms1, ms2
.macro mmulaccneg.ew md, ms1, ms2
    .insn 4, (0x2000002b | ((\md) << 7) | ((\ms1) << 15) | ((\ms2) << 20))
.endm
# mmulaccneg.ew.x md, rs1, ms2
.macro mmulaccneg.ew.x md, rs1, ms2
    .insn 4, (0x2200002b | ((\md) << 7) | ((\rs1) << 15) | ((\ms2) << 20))
.endm
# mmuladd.ew md, ms1, ms2
.macro mmuladd.ew md, ms1, ms2
    .insn 4, (0x2400002b | ((\md) << 7) | ((\ms1) << 15) | ((\ms2) << 20))
.endm
# mmuladd.ew.x md, rs1, ms2
.macro mmuladd.ew.x md, rs1, ms2
    .insn 4, (0x2600002b | ((\md) << 7) | ((\rs1) << 15) | ((\ms2) << 20))
.endm
# mmulatacc.2d acc, ms1, ms2
.macro mmulatacc.2d acc, ms1, ms2
    .insn 4, (0x9a00002b | ((\acc) << 7) | ((\ms1) << 15) | ((\ms2) << 20))
.endm
# mmulataccneg.2d acc, ms1, ms2
.macro mmulataccneg.2d acc, ms1, ms2
    .insn 4, (0x9c00002b | ((\acc) << 7) | ((\ms1) << 15) | ((\ms2) << 20))
.endm
# mmulbtacc.2d acc, ms1, ms2
.macro mmulbtacc.2d acc, ms1, ms2
    .insn 4, (0x9e00002b | ((\acc) << 7) | ((\ms1) << 15) | ((\ms2) << 20))
.endm
# mmulbtaccneg.2d acc, ms1, ms2
.macro mmulbtaccneg.2d acc, ms1, ms2
    .insn 4, (0xa000002b | ((\acc) << 7) | ((\ms1) << 15) | ((\ms2) << 20))
.endm
# mmulneg.ew md, ms1, ms2
.macro mmulneg.ew md, ms1, ms2
    .insn 4, (0x2800002b | ((\md) << 7) | ((\ms1) << 15) | ((\ms2) << 20))
.endm
# mmulneg.ew.x md, rs1, ms2
.macro mmulneg.ew.x md, rs1, ms2
    .insn 4, (0x2a00002b | ((\md) << 7) | ((\rs1) << 15) | ((\ms2) << 20))
.endm
# mmulsub.ew md, ms1, ms2
.macro mmulsub.ew md, ms1, ms2
    .insn 4, (0x2c00002b | ((\md) << 7) | ((\ms1) << 15) | ((\ms2) << 20))
.endm
# mmulsub.ew.x md, rs1, ms2
.macro mmulsub.ew.x md, rs1, ms2
    .insn 4, (0x2e00002b | ((\md) << 7) | ((\rs1) << 15) | ((\ms2) << 20))
.endm
# mor.ew md, ms1, ms2
.macro mor.ew md, ms1, ms2
    .insn 4, (0x3c00002b | ((\md) << 7) | ((\ms1) << 15) | ((\ms2) << 20))
.endm
# mor.ew.x md, rs1, ms2
.macro mor.ew.x md, rs1, ms2
    .insn 4, (0x3e00002b | ((\md) << 7) | ((\rs1) << 15) | ((\ms2) << 20))
.endm
# mornot.ew md, ms1, ms2
.macro mornot.ew md, ms1, ms2
    .insn 4, (0x4000002b | ((\md) << 7) | ((\ms1) << 15) | ((\ms2) << 20))
.endm
# mornot.ew.x md, rs1, ms2
.macro mornot.ew.x md, rs1, ms2
    .insn 4, (0x4200002b | ((\md) << 7) | ((\rs1) << 15) | ((\ms2) << 20))
.endm
# mpack.ew.x md, rs1, ms2
.macro mpack.ew.x md, rs1, ms2
    .insn 4, (0x7a00002b | ((\md) << 7) | ((\rs1) << 15) | ((\ms2) << 20))
.endm
# mprefixadd.col md, ms1
.macro mprefixadd.col md, ms1
    .insn 4, (0xa3f0002b | ((\md) << 7) | ((\ms1) << 15))
.endm
# mprefixadd.row md, ms1
.macro mprefixadd.row md, ms1
    .insn 4, (0xa400002b | ((\md) << 7) | ((\ms1) << 15))
.endm
# mprefixmax.col md, ms1
.macro mprefixmax.col md, ms1
    .insn 4, (0xa410002b | ((\md) << 7) | ((\ms1) << 15))
.endm
# mprefixmax.row md, ms1
.macro mprefixmax.row md, ms1
    .insn 4, (0xa420002b | ((\md) << 7) | ((\ms1) << 15))
.endm
# mrdexp.ew md, ms1, ms2
.macro mrdexp.ew md, ms1, ms2
    .insn 4, (0x8a00002b | ((\md) << 7) | ((\ms1) << 15) | ((\ms2) << 20))
.endm
# mrdexpacc.ew md, ms1, ms2
.macro mrdexpacc.ew md, ms1, ms2
    .insn 4, (0x8c00002b | ((\md) << 7) | ((\ms1) << 15) | ((\ms2) << 20))
.endm
# mrec.ew md, ms1
.macro mrec.ew md, ms1
    .insn 4, (0xa310002b | ((\md) << 7) | ((\ms1) << 15))
.endm
# mreduceadd.col md, ms1
.macro mreduceadd.col md, ms1
    .insn 4, (0xa430002b | ((\md) << 7) | ((\ms1) << 15))
.endm
# mreduceadd.row md, ms1
.macro mreduceadd.row md, ms1
    .insn 4, (0xa440002b | ((\md) << 7) | ((\ms1) << 15))
.endm
# mreducemax.col md, ms1
.macro mreducemax.col md, ms1
    .insn 4, (0xa450002b | ((\md) << 7) | ((\ms1) << 15))
.endm
# mreducemax.row md, ms1
.macro mreducemax.row md, ms1
    .insn 4, (0xa460002b | ((\md) << 7) | ((\ms1) << 15))
.endm
# mreducemin.col md, ms1
.macro mreducemin.col md, ms1
    .insn 4, (0xa470002b | ((\md) << 7) | ((\ms1) << 15))
.endm
# mreducemin.row md, ms1
.macro mreducemin.row md, ms1
    .insn 4, (0xa480002b | ((\md) << 7) | ((\ms1) << 15))
.endm
# mrowbcast.ew.x md, rs1, ms2
.macro mrowbcast.ew.x md, rs1, ms2
    .insn 4, (0x6a00002b | ((\md) << 7) | ((\rs1) << 15) | ((\ms2) << 20))
.endm
# mrowgather.ew md, ms1, ms2
.macro mrowgather.ew md, ms1, ms2
    .insn 4, (0x6c00002b | ((\md) << 7) | ((\ms1) << 15) | ((\ms2) << 20))
.endm
# mrowid.ew md
.macro mrowid.ew md
    .insn 4, (0xa601802b | ((\md) << 7))
.endm
# mrowshift.ew.x md, rs1, ms2
.macro mrowshift.ew.x md, rs1, ms2
    .insn 4, (0x6e00002b | ((\md) << 7) | ((\rs1) << 15) | ((\ms2) << 20))
.endm
# mrowunzip.ew ms1, ms2
.macro mrowunzip.ew ms1, ms2
    .insn 4, (0xc600002b | ((\ms1) << 15) | ((\ms2) << 20))
.endm
# mrowzip.ew ms1, ms2
.macro mrowzip.ew ms1, ms2
    .insn 4, (0x7000002b | ((\ms1) << 15) | ((\ms2) << 20))
.endm
# mrsqrt.ew md, ms1
.macro mrsqrt.ew md, ms1
    .insn 4, (0xa320002b | ((\md) << 7) | ((\ms1) << 15))
.endm
# mrowscatadd.ew md, ms1, ms2
.macro mrowscatadd.ew md, ms1, ms2
    .insn 4, (0x7200002b | ((\md) << 7) | ((\ms1) << 15) | ((\ms2) << 20))
.endm
# mcolscatadd.ew md, ms1, ms2
.macro mcolscatadd.ew md, ms1, ms2
    .insn 4, (0x7400002b | ((\md) << 7) | ((\ms1) << 15) | ((\ms2) << 20))
.endm
# mrowscatmax.ew md, ms1, ms2
.macro mrowscatmax.ew md, ms1, ms2
    .insn 4, (0x7600002b | ((\md) << 7) | ((\ms1) << 15) | ((\ms2) << 20))
.endm
# mcolscatmax.ew md, ms1, ms2
.macro mcolscatmax.ew md, ms1, ms2
    .insn 4, (0x7800002b | ((\md) << 7) | ((\ms1) << 15) | ((\ms2) << 20))
.endm
# mselge.ew md, ms1, ms2
.macro mselge.ew md, ms1, ms2
    .insn 4, (0x6000002b | ((\md) << 7) | ((\ms1) << 15) | ((\ms2) << 20))
.endm
# msellt.ew md, ms1, ms2
.macro msellt.ew md, ms1, ms2
    .insn 4, (0x6200002b | ((\md) << 7) | ((\ms1) << 15) | ((\ms2) << 20))
.endm
# msettyp md, rs1
.macro msettyp md, rs1
    .insn 4, (0xa230002b | ((\md) << 7) | ((\rs1) << 15))
.endm
# msin.ew md, ms1
.macro msin.ew md, ms1
    .insn 4, (0xa330002b | ((\md) << 7) | ((\ms1) << 15))
.endm
# msll.ew md, ms1, ms2
.macro msll.ew md, ms1, ms2
    .insn 4, (0x4400002b | ((\md) << 7) | ((\ms1) << 15) | ((\ms2) << 20))
.endm
# msll.ew.x md, rs1, ms2
.macro msll.ew.x md, rs1, ms2
    .insn 4, (0x4600002b | ((\md) << 7) | ((\rs1) << 15) | ((\ms2) << 20))
.endm
# msqrt.ew md, ms1
.macro msqrt.ew md, ms1
    .insn 4, (0xa340002b | ((\md) << 7) | ((\ms1) << 15))
.endm
# msra.ew md, ms1, ms2
.macro msra.ew md, ms1, ms2
    .insn 4, (0x4800002b | ((\md) << 7) | ((\ms1) << 15) | ((\ms2) << 20))
.endm
# msra.ew.x md, rs1, ms2
.macro msra.ew.x md, rs1, ms2
    .insn 4, (0x4a00002b | ((\md) << 7) | ((\rs1) << 15) | ((\ms2) << 20))
.endm
# msrl.ew md, ms1, ms2
.macro msrl.ew md, ms1, ms2
    .insn 4, (0x4c00002b | ((\md) << 7) | ((\ms1) << 15) | ((\ms2) << 20))
.endm
# msrl.ew.x md, rs1, ms2
.macro msrl.ew.x md, rs1, ms2
    .insn 4, (0x4e00002b | ((\md) << 7) | ((\rs1) << 15) | ((\ms2) << 20))
.endm
# mss.1r ms1, rs1
.macro mss.1r ms1, rs1
    .insn 4, (0xa390002b | ((\ms1) << 7) | ((\rs1) << 15))
.endm
# mss.cm ms1, rs1
.macro mss.cm ms1, rs1
    .insn 4, (0xa3a0002b | ((\ms1) << 7) | ((\rs1) << 15))
.endm
# mss.rm ms1, rs1
.macro mss.rm ms1, rs1
    .insn 4, (0xa3b0002b | ((\ms1) << 7) | ((\rs1) << 15))
.endm
# mss.st ms1, (rs1), rs2
.macro mss.st ms1, rs1, rs2
    .insn 4, (0xac00002b | ((\ms1) << 7) | ((\rs1) << 15) | ((\rs2) << 20))
.endm
# mss.tst ms1, (rs1), rs2
.macro mss.tst ms1, rs1, rs2
    .insn 4, (0xae00002b | ((\ms1) << 7) | ((\rs1) << 15) | ((\rs2) << 20))
.endm
# msub.ew md, ms1, ms2
.macro msub.ew md, ms1, ms2
    .insn 4, (0x3000002b | ((\md) << 7) | ((\ms1) << 15) | ((\ms2) << 20))
.endm
# msub.ew.x md, rs1, ms2
.macro msub.ew.x md, rs1, ms2
    .insn 4, (0x3200002b | ((\md) << 7) | ((\rs1) << 15) | ((\ms2) << 20))
.endm
# msublog2.ew md, ms1, ms2
.macro msublog2.ew md, ms1, ms2
    .insn 4, (0x8e00002b | ((\md) << 7) | ((\ms1) << 15) | ((\ms2) << 20))
.endm
# msublog2.ew.x md, rs1, ms2
.macro msublog2.ew.x md, rs1, ms2
    .insn 4, (0x9000002b | ((\md) << 7) | ((\rs1) << 15) | ((\ms2) << 20))
.endm
# mtanh.ew md, ms1
.macro mtanh.ew md, ms1
    .insn 4, (0xa350002b | ((\md) << 7) | ((\ms1) << 15))
.endm
# munpack.ew.x md, rs1, ms2
.macro munpack.ew.x md, rs1, ms2
    .insn 4, (0x7c00002b | ((\md) << 7) | ((\rs1) << 15) | ((\ms2) << 20))
.endm
# mxor.ew md, ms1, ms2
.macro mxor.ew md, ms1, ms2
    .insn 4, (0x5000002b | ((\md) << 7) | ((\ms1) << 15) | ((\ms2) << 20))
.endm
# mxor.ew.x md, rs1, ms2
.macro mxor.ew.x md, rs1, ms2
    .insn 4, (0x5200002b | ((\md) << 7) | ((\rs1) << 15) | ((\ms2) << 20))
.endm
# mzero.2d.acc acc
.macro mzero.2d.acc acc
    .insn 4, (0xa600002b | ((\acc) << 7))
.endm
# mzero.2d.m md
.macro mzero.2d.m md
    .insn 4, (0xa600802b | ((\md) << 7))
.endm
