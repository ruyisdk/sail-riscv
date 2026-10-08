// Elementwise FP min/max has AME-specific NaN selection semantics.  Test the
// result helpers directly so every supported storage format follows the same
// canonical-NaN, signalling-NaN, and signed-zero contract.

$[test]
function test_ztt_fp_minmax_special_values() -> unit = {
  let fp16 : bits(32) = 0x14300110;
  let bf16 : bits(32) = 0x20300110;
  let fp32 : bits(32) = 0x20300120;
  let fp64 : bits(32) = 0x2c300140;
  let e4m3 : bits(32) = 0x10100108;
  let e5m2 : bits(32) = 0x14300108;
  let rm : bits_rm = 0b000;

  // qNaN returns the canonical quiet NaN without NV; sNaN returns the same
  // result and raises NV.  This is independent of which min/max operation is
  // selected or which operand contains the NaN.
  let (f16_qnan_flags, f16_qnan_result) =
    ame_float_binary_result(fp16, AME_INT_MIN, rm,
      zero_extend(ame_max_dtype_size, 0x7e01),
      zero_extend(ame_max_dtype_size, 0x3c00));
  assert(f16_qnan_flags == 0b00000);
  assert(f16_qnan_result[15 .. 0] == 0x7e00);
  let (f16_snan_flags, f16_snan_result) =
    ame_float_binary_result(fp16, AME_INT_MAX, rm,
      zero_extend(ame_max_dtype_size, 0x3c00),
      zero_extend(ame_max_dtype_size, 0x7c01));
  assert(f16_snan_flags == 0b10000);
  assert(f16_snan_result[15 .. 0] == 0x7e00);
  let (_, f16_min_zero) = ame_float_binary_result(fp16, AME_INT_MIN, rm,
    zero_extend(ame_max_dtype_size, 0x0000), zero_extend(ame_max_dtype_size, 0x8000));
  let (_, f16_max_zero) = ame_float_binary_result(fp16, AME_INT_MAX, rm,
    zero_extend(ame_max_dtype_size, 0x8000), zero_extend(ame_max_dtype_size, 0x0000));
  assert(f16_min_zero[15 .. 0] == 0x8000);
  assert(f16_max_zero[15 .. 0] == 0x0000);

  let (f32_qnan_flags, f32_qnan_result) =
    ame_float_binary_result(fp32, AME_INT_MAX, rm,
      zero_extend(ame_max_dtype_size, 0x7fc00001),
      zero_extend(ame_max_dtype_size, 0x3f800000));
  assert(f32_qnan_flags == 0b00000);
  assert(f32_qnan_result[31 .. 0] == 0x7fc00000);
  let (f32_snan_flags, f32_snan_result) =
    ame_float_binary_result(fp32, AME_INT_MIN, rm,
      zero_extend(ame_max_dtype_size, 0x7f800001),
      zero_extend(ame_max_dtype_size, 0x3f800000));
  assert(f32_snan_flags == 0b10000);
  assert(f32_snan_result[31 .. 0] == 0x7fc00000);
  let (_, f32_min_zero) = ame_float_binary_result(fp32, AME_INT_MIN, rm,
    zero_extend(ame_max_dtype_size, 0x00000000), zero_extend(ame_max_dtype_size, 0x80000000));
  let (_, f32_max_zero) = ame_float_binary_result(fp32, AME_INT_MAX, rm,
    zero_extend(ame_max_dtype_size, 0x80000000), zero_extend(ame_max_dtype_size, 0x00000000));
  assert(f32_min_zero[31 .. 0] == 0x80000000);
  assert(f32_max_zero[31 .. 0] == 0x00000000);

  let (f64_qnan_flags, f64_qnan_result) =
    ame_float_binary_result(fp64, AME_INT_MIN, rm,
      zero_extend(ame_max_dtype_size, 0x7ff8000000000001),
      zero_extend(ame_max_dtype_size, 0x3ff0000000000000));
  assert(f64_qnan_flags == 0b00000);
  assert(f64_qnan_result[63 .. 0] == 0x7ff8000000000000);
  let (f64_snan_flags, f64_snan_result) =
    ame_float_binary_result(fp64, AME_INT_MAX, rm,
      zero_extend(ame_max_dtype_size, 0x3ff0000000000000),
      zero_extend(ame_max_dtype_size, 0x7ff0000000000001));
  assert(f64_snan_flags == 0b10000);
  assert(f64_snan_result[63 .. 0] == 0x7ff8000000000000);
  let (_, f64_min_zero) = ame_float_binary_result(fp64, AME_INT_MIN, rm,
    zero_extend(ame_max_dtype_size, 0x0000000000000000), zero_extend(ame_max_dtype_size, 0x8000000000000000));
  let (_, f64_max_zero) = ame_float_binary_result(fp64, AME_INT_MAX, rm,
    zero_extend(ame_max_dtype_size, 0x8000000000000000), zero_extend(ame_max_dtype_size, 0x0000000000000000));
  assert(f64_min_zero[63 .. 0] == 0x8000000000000000);
  assert(f64_max_zero[63 .. 0] == 0x0000000000000000);

  // BF16 has an IEEE quiet bit; its canonical output is the BF16 qNaN.
  let (bf16_qnan_flags, bf16_qnan_result) =
    ame_float_binary_result(bf16, AME_INT_MIN, rm,
      zero_extend(ame_max_dtype_size, 0x7fc1), zero_extend(ame_max_dtype_size, 0x3f80));
  assert(bf16_qnan_flags == 0b00000);
  assert(bf16_qnan_result[15 .. 0] == 0x7fc0);
  let (bf16_snan_flags, bf16_snan_result) =
    ame_float_binary_result(bf16, AME_INT_MAX, rm,
      zero_extend(ame_max_dtype_size, 0x7f81), zero_extend(ame_max_dtype_size, 0x3f80));
  assert(bf16_snan_flags == 0b10000);
  assert(bf16_snan_result[15 .. 0] == 0x7fc0);

  // OCP E4M3 has no signalling/quiet distinction, so its sole positive NaN
  // propagates without NV.  OCP E5M2 uses frac[1] as the quiet bit.
  let (e4m3_nan_flags, e4m3_nan_result) =
    ame_float_binary_result(e4m3, AME_INT_MIN, rm,
      zero_extend(ame_max_dtype_size, 0x7f), zero_extend(ame_max_dtype_size, 0x38));
  assert(e4m3_nan_flags == 0b00000);
  assert(e4m3_nan_result[7 .. 0] == 0x7f);
  let (_, e4m3_min_zero) = ame_float_binary_result(e4m3, AME_INT_MIN, rm,
    zero_extend(ame_max_dtype_size, 0x00), zero_extend(ame_max_dtype_size, 0x80));
  let (_, e4m3_max_zero) = ame_float_binary_result(e4m3, AME_INT_MAX, rm,
    zero_extend(ame_max_dtype_size, 0x80), zero_extend(ame_max_dtype_size, 0x00));
  assert(e4m3_min_zero[7 .. 0] == 0x80);
  assert(e4m3_max_zero[7 .. 0] == 0x00);
  let (e5m2_qnan_flags, e5m2_qnan_result) =
    ame_float_binary_result(e5m2, AME_INT_MAX, rm,
      zero_extend(ame_max_dtype_size, 0x7f), zero_extend(ame_max_dtype_size, 0x3c));
  assert(e5m2_qnan_flags == 0b00000);
  assert(e5m2_qnan_result[7 .. 0] == 0x7f);
  let (e5m2_snan_flags, e5m2_snan_result) =
    ame_float_binary_result(e5m2, AME_INT_MIN, rm,
      zero_extend(ame_max_dtype_size, 0x7d), zero_extend(ame_max_dtype_size, 0x3c));
  assert(e5m2_snan_flags == 0b10000);
  assert(e5m2_snan_result[7 .. 0] == 0x7f);
  let (_, e5m2_min_zero) = ame_float_binary_result(e5m2, AME_INT_MIN, rm,
    zero_extend(ame_max_dtype_size, 0x00), zero_extend(ame_max_dtype_size, 0x80));
  let (_, e5m2_max_zero) = ame_float_binary_result(e5m2, AME_INT_MAX, rm,
    zero_extend(ame_max_dtype_size, 0x80), zero_extend(ame_max_dtype_size, 0x00));
  assert(e5m2_min_zero[7 .. 0] == 0x80);
  assert(e5m2_max_zero[7 .. 0] == 0x00);
}

function ztt_fp_fill16(value : bits(16)) -> bits(acclen) = {
  var square : bits(acclen) = zeros();
  foreach (element from 0 to (ame_nelem - 1)) {
    square = insert_elem_rm(square, 16, element,
      zero_extend(ame_max_dtype_size, value))
  };
  square
}

function ztt_fp_fill8(value : bits(8)) -> bits(acclen) = {
  var square : bits(acclen) = zeros();
  foreach (element from 0 to (ame_nelem - 1)) {
    square = insert_elem_rm(square, 8, element,
      zero_extend(ame_max_dtype_size, value))
  };
  square
}

$[test]
function test_ztt_fp8_subnormal_writeback_rounding() -> unit = {
  // Exact E4M3/E5M2 subnormals must survive f32 writeback without UF/NX.
  let (e4_exact_flags, e4_exact) = ame_f32_to_e4m3(0b000, 0x3b000000); // 2^-9
  let (e4_max_flags, e4_max) = ame_f32_to_e4m3(0b000, 0x3c600000);     // 7 * 2^-9
  let (e5_exact_flags, e5_exact) = ame_f32_to_e5m2(0b000, 0x37800000); // 2^-16
  let (e5_max_flags, e5_max) = ame_f32_to_e5m2(0b000, 0x38400000);     // 3 * 2^-16
  assert(e4_exact_flags == 0b00000 & e4_exact == 0x01);
  assert(e4_max_flags == 0b00000 & e4_max == 0x07);
  assert(e5_exact_flags == 0b00000 & e5_exact == 0x01);
  assert(e5_max_flags == 0b00000 & e5_max == 0x03);

  // Half of the minimum subnormal distinguishes directed/nearest/jamming
  // behavior.  Every delivered zero/subnormal is tiny and inexact: UF+NX.
  let (e4_rne_f, e4_rne) = ame_f32_to_e4m3(0b000, 0x3a800000);
  let (e4_rtz_f, e4_rtz) = ame_f32_to_e4m3(0b001, 0x3a800000);
  let (e4_rdn_f, e4_rdn) = ame_f32_to_e4m3(0b010, 0x3a800000);
  let (e4_rup_f, e4_rup) = ame_f32_to_e4m3(0b011, 0x3a800000);
  let (e4_rmm_f, e4_rmm) = ame_f32_to_e4m3(0b100, 0x3a800000);
  let (e4_rno_f, e4_rno) = ame_f32_to_e4m3(0b110, 0x3a800000);
  assert(e4_rne_f == 0b00011 & e4_rne == 0x00);
  assert(e4_rtz_f == 0b00011 & e4_rtz == 0x00);
  assert(e4_rdn_f == 0b00011 & e4_rdn == 0x00);
  assert(e4_rup_f == 0b00011 & e4_rup == 0x01);
  assert(e4_rmm_f == 0b00011 & e4_rmm == 0x01);
  assert(e4_rno_f == 0b00011 & e4_rno == 0x01);

  let (e5_rne_f, e5_rne) = ame_f32_to_e5m2(0b000, 0x37000000);
  let (e5_rtz_f, e5_rtz) = ame_f32_to_e5m2(0b001, 0x37000000);
  let (e5_rdn_f, e5_rdn) = ame_f32_to_e5m2(0b010, 0x37000000);
  let (e5_rup_f, e5_rup) = ame_f32_to_e5m2(0b011, 0x37000000);
  let (e5_rmm_f, e5_rmm) = ame_f32_to_e5m2(0b100, 0x37000000);
  let (e5_rno_f, e5_rno) = ame_f32_to_e5m2(0b110, 0x37000000);
  assert(e5_rne_f == 0b00011 & e5_rne == 0x00);
  assert(e5_rtz_f == 0b00011 & e5_rtz == 0x00);
  assert(e5_rdn_f == 0b00011 & e5_rdn == 0x00);
  assert(e5_rup_f == 0b00011 & e5_rup == 0x01);
  assert(e5_rmm_f == 0b00011 & e5_rmm == 0x01);
  assert(e5_rno_f == 0b00011 & e5_rno == 0x01);

  // Rounding a tiny result up to the minimum normal is inexact but no longer
  // tiny after rounding, so only NX is raised.
  let (e4_boundary_flags, e4_boundary) = ame_f32_to_e4m3(0b000, 0x3c700000);
  let (e5_boundary_flags, e5_boundary) = ame_f32_to_e5m2(0b000, 0x38600000);
  assert(e4_boundary_flags == 0b00001 & e4_boundary == 0x08);
  assert(e5_boundary_flags == 0b00001 & e5_boundary == 0x04);

  // Directed negative rounding uses the sign when choosing zero/subnormal.
  let (e4_neg_down_flags, e4_neg_down) = ame_f32_to_e4m3(0b010, 0xba800000);
  let (e4_neg_up_flags, e4_neg_up) = ame_f32_to_e4m3(0b011, 0xba800000);
  assert(e4_neg_down_flags == 0b00011 & e4_neg_down == 0x81);
  assert(e4_neg_up_flags == 0b00011 & e4_neg_up == 0x80);
}

$[test]
function test_ztt_operand_class_validation() -> unit = {
  let int8 : bits(32) = 0x40000008;
  let uint8 : bits(32) = 0x00000008;
  let fp16 : bits(32) = 0x14300110;
  let fp16_rtz : bits(32) = 0x14700110;
  let bf16 : bits(32) = 0x20300110;
  let scalar_reg : regidx = t0;

  ame_test_enable_context();
  X(scalar_reg) = zero_extend(0x01);
  MD(Mdregidx(0b00000)) = int8;
  MD(Mdregidx(0b00001)) = int8;
  MD(Mdregidx(0b00010)) = uint8;
  write_m_square_rm(int8, Ameregidx(0b00000), ztt_fp_fill8(0x5a));
  write_m_square_rm(int8, Ameregidx(0b00001), ztt_fp_fill8(0x03));
  write_m_square_rm(uint8, Ameregidx(0b00010), ztt_fp_fill8(0x01));

  // Bitwise and min/max require one common integer/ordered dtype.  Unsupported
  // mixed tuples retire with UN and preserve every destination bit.
  amestatus = 0b0;
  assert(execute(TEST_AME_MAND_EW(0b00000, 0b00001, 0b00010)) == RETIRE_SUCCESS);
  assert(amestatus == 0b1);
  assert(extract_elem_rm(read_m_square_rm(int8, Ameregidx(0b00000)), 8, 0)[7 .. 0] == 0x5a);
  amestatus = 0b0;
  assert(execute(TEST_AME_MMIN_EW(0b00000, 0b00001, 0b00010)) == RETIRE_SUCCESS);
  assert(amestatus == 0b1);
  assert(extract_elem_rm(read_m_square_rm(int8, Ameregidx(0b00000)), 8, 0)[7 .. 0] == 0x5a);
  amestatus = 0b0;
  amestype = uint8;
  assert(execute(TEST_AME_MAND_EW_X(0b00000, 0b00101, 0b00001)) == RETIRE_SUCCESS);
  assert(amestatus == 0b1);
  assert(extract_elem_rm(read_m_square_rm(int8, Ameregidx(0b00000)), 8, 0)[7 .. 0] == 0x5a);

  // Comparison accepts ordered floating sources with an integer destination.
  amestatus = 0b0;
  MD(Mdregidx(0b00000)) = uint8;
  MD(Mdregidx(0b00010)) = fp16;
  MD(Mdregidx(0b00100)) = fp16_rtz;
  write_m_square_rm(fp16, Ameregidx(0b00010), ztt_fp_fill16(0x4000)); // 2.0
  write_m_square_rm(fp16_rtz, Ameregidx(0b00100), ztt_fp_fill16(0x3c00)); // 1.0
  assert(execute(TEST_AME_MCMPGE_EW(0b00000, 0b00010, 0b00100)) == RETIRE_SUCCESS);
  assert(amestatus == 0b0);
  assert(extract_elem_rm(read_m_square_rm(uint8, Ameregidx(0b00000)), 8, 0)[7 .. 0] == 0xff);

  // A floating comparison destination and a cross-class source pair are both
  // unsupported rather than being reinterpreted through the destination.
  MD(Mdregidx(0b00000)) = fp16;
  write_m_square_rm(fp16, Ameregidx(0b00000), ztt_fp_fill16(0x3555));
  amestatus = 0b0;
  assert(execute(TEST_AME_MCMPGE_EW(0b00000, 0b00010, 0b00100)) == RETIRE_SUCCESS);
  assert(amestatus == 0b1);
  assert(extract_elem_rm(read_m_square_rm(fp16, Ameregidx(0b00000)), 16, 0)[15 .. 0] == 0x3555);
  MD(Mdregidx(0b00000)) = uint8;
  MD(Mdregidx(0b00010)) = int8;
  write_m_square_rm(uint8, Ameregidx(0b00000), ztt_fp_fill8(0x5a));
  amestatus = 0b0;
  assert(execute(TEST_AME_MCMPGE_EW(0b00000, 0b00010, 0b00100)) == RETIRE_SUCCESS);
  assert(amestatus == 0b1);
  assert(extract_elem_rm(read_m_square_rm(uint8, Ameregidx(0b00000)), 8, 0)[7 .. 0] == 0x5a);

  // Same base float formats may differ only in rounding.  Cross-format
  // FP16/BF16 tuples instead set UN and leave the destination unchanged.
  MD(Mdregidx(0b00000)) = fp16;
  MD(Mdregidx(0b00010)) = fp16_rtz;
  MD(Mdregidx(0b00100)) = fp16_rtz;
  write_m_square_rm(fp16_rtz, Ameregidx(0b00010), ztt_fp_fill16(0x3c00));
  write_m_square_rm(fp16_rtz, Ameregidx(0b00100), ztt_fp_fill16(0x4000));
  amestatus = 0b0;
  assert(execute(TEST_AME_MADD_EW(0b00000, 0b00010, 0b00100)) == RETIRE_SUCCESS);
  assert(amestatus == 0b0);
  assert(extract_elem_rm(read_m_square_rm(fp16, Ameregidx(0b00000)), 16, 0)[15 .. 0] == 0x4200);
  MD(Mdregidx(0b00010)) = bf16;
  write_m_square_rm(fp16, Ameregidx(0b00000), ztt_fp_fill16(0x3555));
  write_m_square_rm(bf16, Ameregidx(0b00010), ztt_fp_fill16(0x3f80));
  amestatus = 0b0;
  assert(execute(TEST_AME_MADD_EW(0b00000, 0b00010, 0b00100)) == RETIRE_SUCCESS);
  assert(amestatus == 0b1);
  assert(extract_elem_rm(read_m_square_rm(fp16, Ameregidx(0b00000)), 16, 0)[15 .. 0] == 0x3555);
}

// BF16 fused multiply-add must round the exact sum once, not first to f32 and
// then to bf16.  Every vector below fixes a value that the old two-step path
// got wrong (or that pins the one-rounding contract against a wider format).
$[test]
function test_ztt_bf16_fused_single_rounding() -> unit = {
  let bf16 : bits(32) = 0x20300110;
  let rne : bits_rm = 0b000;

  // dest + ms1 * ms2 with the exact sum a quarter of an f32 ulp above the
  // 0x3fc0/0x3fc1 midpoint: two-step rounds down to 0x3fc0, one rounding up.
  let (forward_flags, forward) = ame_float_ternary_result(bf16, AME_INT_MULACC, rne,
    zero_extend(ame_max_dtype_size, 0x3300), // 2^-25
    zero_extend(ame_max_dtype_size, 0x3fa0), // 1.25
    zero_extend(ame_max_dtype_size, 0x3f9a)); // 1.203125
  assert(forward_flags == 0b00001);
  assert(forward[15 .. 0] == 0x3fc1);

  // The same product with the smallest BF16 addend (2^-133).  Borrowing f64
  // would swallow the addend and land on the midpoint, so this pins the exact
  // computation.
  let (min_sub_flags, min_sub) = ame_float_ternary_result(bf16, AME_INT_MULACC, rne,
    zero_extend(ame_max_dtype_size, 0x0001), // 2^-133
    zero_extend(ame_max_dtype_size, 0x3fa0),
    zero_extend(ame_max_dtype_size, 0x3f9a));
  assert(min_sub_flags == 0b00001);
  assert(min_sub[15 .. 0] == 0x3fc1);

  // MULACCNEG negates the product: -(1.25 * 1.203125) - 2^-25.
  let (nacc_flags, nacc) = ame_float_ternary_result(bf16, AME_INT_MULNACC, rne,
    zero_extend(ame_max_dtype_size, 0xb300), // -2^-25
    zero_extend(ame_max_dtype_size, 0x3fa0),
    zero_extend(ame_max_dtype_size, 0x3f9a));
  assert(nacc_flags == 0b00001);
  assert(nacc[15 .. 0] == 0xbfc1);

  // MULADD is ms2 * dest + ms1, so the product operands move to ms2/dest.
  let (add_flags, add) = ame_float_ternary_result(bf16, AME_INT_MULADD, rne,
    zero_extend(ame_max_dtype_size, 0x3fa0),
    zero_extend(ame_max_dtype_size, 0x3300),
    zero_extend(ame_max_dtype_size, 0x3f9a));
  assert(add_flags == 0b00001);
  assert(add[15 .. 0] == 0x3fc1);

  // MULSUB is ms1 - ms2 * dest.
  let (sub_flags, sub) = ame_float_ternary_result(bf16, AME_INT_MULSUB, rne,
    zero_extend(ame_max_dtype_size, 0x3fa0),
    zero_extend(ame_max_dtype_size, 0xb300), // -2^-25
    zero_extend(ame_max_dtype_size, 0x3f9a));
  assert(sub_flags == 0b00001);
  assert(sub[15 .. 0] == 0xbfc1);

  // Opposite direction: the exact sum is 2^-28 below a midpoint whose lower
  // neighbour is odd, so two-step ties up to 0x3e42 while one rounding goes
  // down to 0x3e41.
  let (below_flags, below) = ame_float_ternary_result(bf16, AME_INT_MULACC, rne,
    zero_extend(ame_max_dtype_size, 0xb180), // -2^-28
    zero_extend(ame_max_dtype_size, 0x3f81), // 1.0078125
    zero_extend(ame_max_dtype_size, 0x3e40)); // 0.1875
  assert(below_flags == 0b00001);
  assert(below[15 .. 0] == 0x3e41);

  // NaN operands collapse to the BF16 default NaN without propagating a
  // payload; only a signalling NaN raises NV.
  let (qnan_flags, qnan) = ame_float_ternary_result(bf16, AME_INT_MULACC, rne,
    zero_extend(ame_max_dtype_size, 0x7fc1),
    zero_extend(ame_max_dtype_size, 0x3f80),
    zero_extend(ame_max_dtype_size, 0x3f80));
  assert(qnan_flags == 0b00000);
  assert(qnan[15 .. 0] == 0x7fc0);
  let (snan_flags, snan) = ame_float_ternary_result(bf16, AME_INT_MULACC, rne,
    zero_extend(ame_max_dtype_size, 0x7f81),
    zero_extend(ame_max_dtype_size, 0x3f80),
    zero_extend(ame_max_dtype_size, 0x3f80));
  assert(snan_flags == 0b10000);
  assert(snan[15 .. 0] == 0x7fc0);

  // Invalid operations and the infinity result still follow the fused rules.
  let (zero_inf_flags, zero_inf) = ame_float_ternary_result(bf16, AME_INT_MULACC, rne,
    zero_extend(ame_max_dtype_size, 0x3f80),
    zero_extend(ame_max_dtype_size, 0x0000),
    zero_extend(ame_max_dtype_size, 0x7f80));
  assert(zero_inf_flags == 0b10000);
  assert(zero_inf[15 .. 0] == 0x7fc0);
  let (inf_inf_flags, inf_inf) = ame_float_ternary_result(bf16, AME_INT_MULACC, rne,
    zero_extend(ame_max_dtype_size, 0xff80),
    zero_extend(ame_max_dtype_size, 0x7f80),
    zero_extend(ame_max_dtype_size, 0x3f80));
  assert(inf_inf_flags == 0b10000);
  assert(inf_inf[15 .. 0] == 0x7fc0);
  let (finite_inf_flags, finite_inf) = ame_float_ternary_result(bf16, AME_INT_MULACC, rne,
    zero_extend(ame_max_dtype_size, 0x3f80),
    zero_extend(ame_max_dtype_size, 0x7f80),
    zero_extend(ame_max_dtype_size, 0x3f80));
  assert(finite_inf_flags == 0b00000);
  assert(finite_inf[15 .. 0] == 0x7f80);

  // An exactly representable subnormal raises nothing, while a product of the
  // two smallest subnormals underflows to signed zero with UF+NX.
  let (exact_flags, exact) = ame_float_ternary_result(bf16, AME_INT_MULACC, rne,
    zero_extend(ame_max_dtype_size, 0x0000),
    zero_extend(ame_max_dtype_size, 0x0001),
    zero_extend(ame_max_dtype_size, 0x3f80));
  assert(exact_flags == 0b00000);
  assert(exact[15 .. 0] == 0x0001);
  let (tiny_flags, tiny) = ame_float_ternary_result(bf16, AME_INT_MULACC, rne,
    zero_extend(ame_max_dtype_size, 0x0000),
    zero_extend(ame_max_dtype_size, 0x0001),
    zero_extend(ame_max_dtype_size, 0x0001));
  assert(tiny_flags == 0b00011);
  assert(tiny[15 .. 0] == 0x0000);

  // Overflow saturates with OF+NX: infinity under RNE, maximum finite under a
  // directed mode.
  let (ovf_flags, ovf) = ame_float_ternary_result(bf16, AME_INT_MULACC, rne,
    zero_extend(ame_max_dtype_size, 0x0000),
    zero_extend(ame_max_dtype_size, 0x7f7f),
    zero_extend(ame_max_dtype_size, 0x7f7f));
  assert(ovf_flags == 0b00101);
  assert(ovf[15 .. 0] == 0x7f80);
  let (ovf_rtz_flags, ovf_rtz) = ame_float_ternary_result(bf16, AME_INT_MULACC, 0b001,
    zero_extend(ame_max_dtype_size, 0x0000),
    zero_extend(ame_max_dtype_size, 0x7f7f),
    zero_extend(ame_max_dtype_size, 0x7f7f));
  assert(ovf_rtz_flags == 0b00101);
  assert(ovf_rtz[15 .. 0] == 0x7f7f);

  // An exact midpoint tie depends only on the destination rounding mode.
  let (tie_flags, tie) = ame_float_ternary_result(bf16, AME_INT_MULACC, rne,
    zero_extend(ame_max_dtype_size, 0x0000),
    zero_extend(ame_max_dtype_size, 0x3fa0),
    zero_extend(ame_max_dtype_size, 0x3f9a));
  assert(tie_flags == 0b00001);
  assert(tie[15 .. 0] == 0x3fc0);
  let (tie_away_flags, tie_away) = ame_float_ternary_result(bf16, AME_INT_MULACC, 0b100,
    zero_extend(ame_max_dtype_size, 0x0000),
    zero_extend(ame_max_dtype_size, 0x3fa0),
    zero_extend(ame_max_dtype_size, 0x3f9a));
  assert(tie_away_flags == 0b00001);
  assert(tie_away[15 .. 0] == 0x3fc1);

  // Tininess after rounding: this product is 2^-140 below the minimum normal,
  // so the single rounding promotes it to 2^-126 with NX but no UF.
  let (promote_flags, promote) = ame_float_ternary_result(bf16, AME_INT_MULACC, rne,
    zero_extend(ame_max_dtype_size, 0x0000),
    zero_extend(ame_max_dtype_size, 0x007f), // 127 * 2^-133
    zero_extend(ame_max_dtype_size, 0x3f81)); // 129 * 2^-7
  assert(promote_flags == 0b00001);
  assert(promote[15 .. 0] == 0x0080);
}
