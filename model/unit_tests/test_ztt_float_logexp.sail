// Floating-point log/exp semantics: mexp2/mlog2 evaluate the transcendental
// through the documented approximation budget, while mldexp/mldexpacc must
// round the exact value a * 2^k a single time for every element format
// (including FP64 and the narrow FP16/BF16/OCP-FP8 formats).  These tests
// exercise the shared helpers directly so each width and flag combination is
// covered without depending on the instruction encodings.

$[test]
function test_ztt_float_logexp_ldexp_exact() -> unit = {
  let e4m3 : bits(32) = 0x10100108;
  let fp16 : bits(32) = 0x14300110;
  let fp32 : bits(32) = 0x20300120;
  let fp64 : bits(32) = 0x2c300140;
  let rne : bits_rm = 0b000;
  let rtz : bits_rm = 0b001;
  let rup : bits_rm = 0b011;

  // 1.0 * 2^3 = 8.0 is exact and raises no flag.
  let (lf0, r0) = ame_fp_ldexp_result(fp32, rne, false, false,
    zero_extend(ame_max_dtype_size, 0x3F800000), zeros(), 3);
  assert(lf0 == 0b00000 & r0[31 .. 0] == 0x41000000);

  // 1.0 * 2^-149 is exactly the minimum FP32 subnormal.
  let (lf1, r1) = ame_fp_ldexp_result(fp32, rne, false, false,
    zero_extend(ame_max_dtype_size, 0x3F800000), zeros(), 0 - 149);
  assert(lf1 == 0b00000 & r1[31 .. 0] == 0x00000001);

  // 1.0 * 2^-150 is a tie at half the minimum subnormal.  RNE keeps the even
  // zero, RUP delivers the minimum subnormal; both are tiny and inexact.
  let (lf2, r2) = ame_fp_ldexp_result(fp32, rne, false, false,
    zero_extend(ame_max_dtype_size, 0x3F800000), zeros(), 0 - 150);
  assert(lf2 == 0b00011 & r2[31 .. 0] == 0x00000000);
  let (lf3, r3) = ame_fp_ldexp_result(fp32, rup, false, false,
    zero_extend(ame_max_dtype_size, 0x3F800000), zeros(), 0 - 150);
  assert(lf3 == 0b00011 & r3[31 .. 0] == 0x00000001);

  // Overflow of the largest finite value raises OF+NX and selects infinity
  // under RNE but the largest finite value under RTZ.
  let (lf4, r4) = ame_fp_ldexp_result(fp32, rne, false, false,
    zero_extend(ame_max_dtype_size, 0x7F7FFFFF), zeros(), 1);
  assert(lf4 == 0b00101 & r4[31 .. 0] == 0x7F800000);
  let (lf5, r5) = ame_fp_ldexp_result(fp32, rtz, false, false,
    zero_extend(ame_max_dtype_size, 0x7F7FFFFF), zeros(), 1);
  assert(lf5 == 0b00101 & r5[31 .. 0] == 0x7F7FFFFF);

  // FP64 must also round a single time: 2^-1075 is a tie at half the minimum
  // FP64 subnormal, well below anything an FP32 intermediate could carry.
  let (lf6, r6) = ame_fp_ldexp_result(fp64, rne, false, false,
    zero_extend(ame_max_dtype_size, 0x3FF0000000000000), zeros(), 0 - 1075);
  assert(lf6 == 0b00011 & r6[63 .. 0] == 0x0000000000000000);
  let (lf7, r7) = ame_fp_ldexp_result(fp64, rup, false, false,
    zero_extend(ame_max_dtype_size, 0x3FF0000000000000), zeros(), 0 - 1075);
  assert(lf7 == 0b00011 & r7[63 .. 0] == 0x0000000000000001);

  // Narrow FP16 is single-rounded too: 2^-25 ties at half the minimum FP16
  // subnormal 2^-24.
  let (lf8, r8) = ame_fp_ldexp_result(fp16, rne, false, false,
    zero_extend(ame_max_dtype_size, 0x3C00), zeros(), 0 - 25);
  assert(lf8 == 0b00011 & r8[15 .. 0] == 0x0000);
  let (lf9, r9) = ame_fp_ldexp_result(fp16, rup, false, false,
    zero_extend(ame_max_dtype_size, 0x3C00), zeros(), 0 - 25);
  assert(lf9 == 0b00011 & r9[15 .. 0] == 0x0001);

  // 2^-1080 underflows any FP32/FP64 intermediate, but the correctly rounded
  // FP32 result under RUP is the minimum subnormal.  This forces the exact
  // arbitrary-precision path rather than a float intermediate.
  let (lf10, r10) = ame_fp_ldexp_result(fp32, rup, false, false,
    zero_extend(ame_max_dtype_size, 0x3F800000), zeros(), 0 - 1080);
  assert(lf10 == 0b00011 & r10[31 .. 0] == 0x00000001);

  // mrdexp negates the exponent: 1.0 * 2^-(-5) = 32.0.
  let (lf11, r11) = ame_fp_ldexp_result(fp32, rne, false, true,
    zero_extend(ame_max_dtype_size, 0x3F800000), zeros(), 0 - 5);
  assert(lf11 == 0b00000 & r11[31 .. 0] == 0x42000000);

  // Signalling NaN quiets and raises NV; quiet NaN propagates without NV.
  let (lf12, r12) = ame_fp_ldexp_result(fp32, rne, false, false,
    zero_extend(ame_max_dtype_size, 0x7F800001), zeros(), 7);
  assert(lf12 == 0b10000 & r12[31 .. 0] == 0x7FC00000);
  let (lf13, r13) = ame_fp_ldexp_result(fp32, rne, false, false,
    zero_extend(ame_max_dtype_size, 0x7FC00001), zeros(), 7);
  assert(lf13 == 0b00000 & r13[31 .. 0] == 0x7FC00000);

  // Zero and infinity are preserved with no flags, and the exponent is not
  // applied to them.
  let (lf14, r14) = ame_fp_ldexp_result(fp32, rne, false, false,
    zero_extend(ame_max_dtype_size, 0x80000000), zeros(), 7);
  assert(lf14 == 0b00000 & r14[31 .. 0] == 0x80000000);
  let (lf15, r15) = ame_fp_ldexp_result(fp32, rne, false, false,
    zero_extend(ame_max_dtype_size, 0xFF800000), zeros(), 7);
  assert(lf15 == 0b00000 & r15[31 .. 0] == 0xFF800000);

  // OCP E4M3 has no infinity, so an overflowing scale saturates to the signed
  // maximum finite magnitude with OF+NX.
  let (lf16, r16) = ame_fp_ldexp_result(e4m3, rne, false, false,
    zero_extend(ame_max_dtype_size, 0x40), zeros(), 10);
  assert(lf16 == 0b00101 & r16[7 .. 0] == 0x7E);

  // 2.0 * 2^-10 = 2^-9 is exactly the E4M3 minimum subnormal.
  let (lf17, r17) = ame_fp_ldexp_result(e4m3, rne, false, false,
    zero_extend(ame_max_dtype_size, 0x40), zeros(), 0 - 10);
  assert(lf17 == 0b00000 & r17[7 .. 0] == 0x01);
}

$[test]
function test_ztt_float_logexp_ldexpacc_exact() -> unit = {
  let fp16 : bits(32) = 0x14300110;
  let fp32 : bits(32) = 0x20300120;
  let rne : bits_rm = 0b000;
  let rup : bits_rm = 0b011;

  // 1.0 + 1.5 * 2^0 = 2.5 is exact.
  let (lf0, r0) = ame_fp_ldexp_result(fp32, rne, true, false,
    zero_extend(ame_max_dtype_size, 0x3FC00000),
    zero_extend(ame_max_dtype_size, 0x3F800000), 0);
  assert(lf0 == 0b00000 & r0[31 .. 0] == 0x40200000);

  // fp32 maximum + (-fp32 maximum) * 2 = -fp32 maximum exactly.  Scaling the
  // product to infinity before the addition would wrongly deliver -inf.
  let (lf1, r1) = ame_fp_ldexp_result(fp32, rne, true, false,
    zero_extend(ame_max_dtype_size, 0xFF7FFFFF),
    zero_extend(ame_max_dtype_size, 0x7F7FFFFF), 1);
  assert(lf1 == 0b00000 & r1[31 .. 0] == 0xFF7FFFFF);

  // 2^24 + 1.0 is an exact tie: RNE keeps the even 2^24 and RUP rounds to
  // 2^24 + 2.  Both are inexact (NX).
  let (lf2, r2) = ame_fp_ldexp_result(fp32, rne, true, false,
    zero_extend(ame_max_dtype_size, 0x3F800000),
    zero_extend(ame_max_dtype_size, 0x4B800000), 0);
  assert(lf2 == 0b00001 & r2[31 .. 0] == 0x4B800000);
  let (lf3, r3) = ame_fp_ldexp_result(fp32, rup, true, false,
    zero_extend(ame_max_dtype_size, 0x3F800000),
    zero_extend(ame_max_dtype_size, 0x4B800000), 0);
  assert(lf3 == 0b00001 & r3[31 .. 0] == 0x4B800001);

  // The accumulator is the destination of a narrow format: FP16 1.0 plus
  // 1.0 * 2^-10 is exactly 1.0 + one FP16 ulp, i.e. 0x3C01.
  let (lf4, r4) = ame_fp_ldexp_result(fp16, rne, true, false,
    zero_extend(ame_max_dtype_size, 0x3C00),
    zero_extend(ame_max_dtype_size, 0x3C00), 0 - 10);
  assert(lf4 == 0b00000 & r4[15 .. 0] == 0x3C01);

  // old + 0 does not disturb the accumulator, and +0 + -0 picks the sign per
  // the rounding direction.
  let (lf5, r5) = ame_fp_ldexp_result(fp32, rne, true, false,
    zero_extend(ame_max_dtype_size, 0x00000000),
    zero_extend(ame_max_dtype_size, 0x40490FDB), 5);
  assert(lf5 == 0b00000 & r5[31 .. 0] == 0x40490FDB);
  let (lf6, r6) = ame_fp_ldexp_result(fp32, 0b010, true, false,
    zero_extend(ame_max_dtype_size, 0x80000000),
    zero_extend(ame_max_dtype_size, 0x00000000), 0);
  assert(lf6 == 0b00000 & r6[31 .. 0] == 0x80000000);

  // (+inf) + (-inf) is invalid, and a signalling NaN in either operand raises
  // NV while the result is the canonical quiet NaN.
  let (lf7, r7) = ame_fp_ldexp_result(fp32, rne, true, false,
    zero_extend(ame_max_dtype_size, 0xFF800000),
    zero_extend(ame_max_dtype_size, 0x7F800000), 0);
  assert(lf7 == 0b10000 & r7[31 .. 0] == 0x7FC00000);
  let (lf8, r8) = ame_fp_ldexp_result(fp32, rne, true, false,
    zero_extend(ame_max_dtype_size, 0x3F800000),
    zero_extend(ame_max_dtype_size, 0x7FA00000), 0);
  assert(lf8 == 0b10000 & r8[31 .. 0] == 0x7FC00000);
}

$[test]
function test_ztt_float_logexp_transcendental_special() -> unit = {
  let e5m2 : bits(32) = 0x14300108;
  let fp16 : bits(32) = 0x14300110;
  let rne : bits_rm = 0b000;

  // exp2(+0) = 1, exp2(+inf) = +inf, exp2(-inf) = +0.
  let (lf0, r0) = ame_fp32_logexp_result(AME_INT_EXP2, 0x00000000);
  assert(lf0 == 0b00000 & r0 == 0x3F800000);
  let (lf1, r1) = ame_fp32_logexp_result(AME_INT_EXP2, 0x7F800000);
  assert(lf1 == 0b00000 & r1 == 0x7F800000);
  let (lf2, r2) = ame_fp32_logexp_result(AME_INT_EXP2, 0xFF800000);
  assert(lf2 == 0b00000 & r2 == 0x00000000);

  // log2(+/-0) = -inf with DZ, log2(negative) is invalid, log2(+inf) = +inf.
  let (lf3, r3) = ame_fp32_logexp_result(AME_INT_LOG2, 0x00000000);
  assert(lf3 == 0b01000 & r3 == 0xFF800000);
  let (lf4, r4) = ame_fp32_logexp_result(AME_INT_LOG2, 0x80000000);
  assert(lf4 == 0b01000 & r4 == 0xFF800000);
  let (lf5, r5) = ame_fp32_logexp_result(AME_INT_LOG2, 0xBF800000);
  assert(lf5 == 0b10000 & r5 == 0x7FC00000);
  let (lf6, r6) = ame_fp32_logexp_result(AME_INT_LOG2, 0xFF800000);
  assert(lf6 == 0b10000 & r6 == 0x7FC00000);
  let (lf7, r7) = ame_fp32_logexp_result(AME_INT_LOG2, 0x7F800000);
  assert(lf7 == 0b00000 & r7 == 0x7F800000);
  let (lf8, r8) = ame_fp32_logexp_result(AME_INT_LOG2, 0x3F800000);
  assert(lf8 == 0b00000 & r8 == 0x00000000);

  // Signalling NaN raises NV, quiet NaN propagates without it.
  let (lf9, r9) = ame_fp32_logexp_result(AME_INT_EXP2, 0x7F800001);
  assert(lf9 == 0b10000 & r9 == 0x7FC00000);
  let (lf10, r10) = ame_fp32_logexp_result(AME_INT_LOG2, 0x7FC00001);
  assert(lf10 == 0b00000 & r10 == 0x7FC00000);

  // Narrow storage widens to FP32: E5M2 log2(+0) still raises DZ and narrows
  // to the E5M2 -inf encoding, FP16 exp2(-inf) narrows to +0.
  let (lf11, r11) = ame_float_logexp_unary_result(e5m2, AME_INT_LOG2, rne,
    zero_extend(ame_max_dtype_size, 0x00));
  assert(lf11 == 0b01000 & r11[7 .. 0] == 0xFC);
  let (lf12, r12) = ame_float_logexp_unary_result(fp16, AME_INT_EXP2, rne,
    zero_extend(ame_max_dtype_size, 0xFC00));
  assert(lf12 == 0b00000 & r12[15 .. 0] == 0x0000);
}

$[test]
function test_ztt_float_logexp_log2bias() -> unit = {
  let e5m2 : bits(32) = 0x14300108;
  let fp16 : bits(32) = 0x14300110;
  let fp32 : bits(32) = 0x20300120;
  let rne : bits_rm = 0b000;

  // log2sub(8, 1) = 3 - 1 = 2 and msublog2(8, 1) = 1 - 3 = -2.
  let (lf0, r0) = ame_fp32_log2bias_result(AME_INT_LOG2SUB, rne, 0x41000000, 0x3F800000);
  assert(lf0 == 0b00000 & r0 == 0x40000000);
  let (lf1, r1) = ame_fp32_log2bias_result(AME_INT_SUBLOG2, rne, 0x41000000, 0x3F800000);
  assert(lf1 == 0b00000 & r1 == 0xC0000000);

  // The logarithm operand is |a|, so a negative finite value is valid.
  let (lf2, r2) = ame_fp32_log2bias_result(AME_INT_LOG2SUB, rne, 0xC1000000, 0x3F800000);
  assert(lf2 == 0b00000 & r2 == 0x40000000);

  // log2(+/-0) raises DZ and the subtraction then sees -inf.
  let (lf3, r3) = ame_fp32_log2bias_result(AME_INT_LOG2SUB, rne, 0x00000000, 0x3F800000);
  assert(lf3 == 0b01000 & r3 == 0xFF800000);

  // NaN divides through the subtraction: sNaN raises NV.
  let (lf4, r4) = ame_fp32_log2bias_result(AME_INT_SUBLOG2, rne, 0x7F800001, 0x3F800000);
  assert(lf4 == 0b10000 & r4 == 0x7FC00000);

  // Narrow formats evaluate through FP32: FP16 log2sub(4, 1) = 1 exactly.
  let (lf5, r5) = ame_float_log2bias_result(fp16, AME_INT_LOG2SUB, rne,
    zero_extend(ame_max_dtype_size, 0x4400),
    zero_extend(ame_max_dtype_size, 0x3C00));
  assert(lf5 == 0b00000 & r5[15 .. 0] == 0x3C00);

  // E5M2 log2sub(4, 1) narrows back to the E5M2 1.0 encoding.
  let (lf6, r6) = ame_float_log2bias_result(e5m2, AME_INT_LOG2SUB, rne,
    zero_extend(ame_max_dtype_size, 0x44),
    zero_extend(ame_max_dtype_size, 0x3C));
  assert(lf6 == 0b00000 & r6[7 .. 0] == 0x3C);

  let (lf7, r7) = ame_fp64_log2bias_result(AME_INT_SUBLOG2, rne,
    0x4020000000000000, 0x3FF0000000000000);
  assert(lf7 == 0b00000 & r7[63 .. 0] == 0xC000000000000000);
}

$[test]
function test_ztt_float_logexp_instruction_paths() -> unit = {
  // FP16 spans two physical registers per logical square and Int8 one, so the
  // aligned base registers 0 / 2 / 4 never overlap and every operand is a
  // legal formed operand (FP32 would need a base multiple of four, which
  // leaves no room for three distinct operands in eight M registers).
  let fp16 : bits(32) = 0x14300110;
  let int8 : bits(32) = 0x40000008;
  let fp32 : bits(32) = 0x20300120;
  let int32 : bits(32) = 0x40000020;

  ame_test_enable_context();

  // mlog2.ew on floating-point data must take the float path: log2(+0) is
  // -inf with DZ in amefflags, while amexsat (integer-only sticky saturation)
  // stays clear and amestatus does not report an unsupported operand.
  amefflags = zeros();
  amexsat = 0b0;
  amestatus = 0b0;
  MD(Mdregidx(0b00000)) = fp16;
  MD(Mdregidx(0b00010)) = fp16;
  foreach (e from 0 to (ame_nelem - 1)) {
    write_m_elem(fp16, Ameregidx(0b00010), e,
      zero_extend(ame_max_dtype_size, 0x0000))
  };
  assert(execute(TEST_AME_MLOG2_EW(0b00000, 0b00010)) == RETIRE_SUCCESS);
  assert(amestatus == 0b0);
  assert(read_m_elem(fp16, 0, Ameregidx(0b00000))[15 .. 0] == 0xFC00);
  assert(amefflags == 0b01000);
  assert(amexsat == 0b0);

  // mldexp.ew float data with an Int8 exponent: 1.0 * 2^3 = 8.0, exact.
  amefflags = zeros();
  amexsat = 0b0;
  amestatus = 0b0;
  MD(Mdregidx(0b00000)) = fp16;
  MD(Mdregidx(0b00010)) = fp16;
  MD(Mdregidx(0b00100)) = int8;
  foreach (e from 0 to (ame_nelem - 1)) {
    write_m_elem(fp16, Ameregidx(0b00010), e,
      zero_extend(ame_max_dtype_size, 0x3C00));
    write_m_elem(int8, Ameregidx(0b00100), e,
      zero_extend(ame_max_dtype_size, 0x03))
  };
  assert(execute(TEST_AME_MLDEXP_EW(0b00000, 0b00010, 0b00100)) == RETIRE_SUCCESS);
  assert(amestatus == 0b0);
  assert(read_m_elem(fp16, 0, Ameregidx(0b00000))[15 .. 0] == 0x4800);
  assert(amefflags == 0b00000);
  assert(amexsat == 0b0);

  // mldexp.ew.x takes the exponent from the integer control register:
  // 2.0 * 2^2 = 8.0.
  amefflags = zeros();
  amestatus = 0b0;
  let rs1 : bits(5) = 0b00010;
  X(Regidx(trunc(rs1))) = zero_extend(0b10);
  MD(Mdregidx(0b00000)) = fp16;
  MD(Mdregidx(0b00010)) = fp16;
  foreach (e from 0 to (ame_nelem - 1)) {
    write_m_elem(fp16, Ameregidx(0b00010), e,
      zero_extend(ame_max_dtype_size, 0x4000))
  };
  assert(execute(MATH_R3_MD_XS_MS_TYPE(AME_MLDEXP_EW_X, 0b00000, rs1, 0b00010)) == RETIRE_SUCCESS);
  assert(amestatus == 0b0);
  assert(read_m_elem(fp16, 0, Ameregidx(0b00000))[15 .. 0] == 0x4800);
  assert(amefflags == 0b00000);

  // A floating-point destination with an integer source is still unsupported.
  amestatus = 0b0;
  MD(Mdregidx(0b00000)) = fp32;
  MD(Mdregidx(0b00100)) = int32;
  assert(execute(TEST_AME_MLOG2_EW(0b00000, 0b00100)) == RETIRE_SUCCESS);
  assert(amestatus == 0b1);
}
