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
