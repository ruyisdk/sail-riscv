// Integer fixed-point status is determined from exact intermediates before
// the destination element is narrowed. These tests use the first matrix
// element and execute the architectural instructions to cover the commit path.

function ztt_int_status_dtype(rounding : bits(2), saturating : bits(1))
  -> bits(32) =
  0b0 @ 0b1 @ saturating @ rounding @ zeros(18) @ 0b0 @ 0x08

function ztt_int_status_fill(value : bits(8)) -> bits(acclen) = {
  var square : bits(acclen) = zeros();
  foreach (element from 0 to (ame_nelem - 1)) {
    square = insert_elem_rm(square, 8, element,
      zero_extend(ame_max_dtype_size, value))
  };
  square
}

function ztt_int_status_fill16(value : bits(16)) -> bits(acclen) = {
  var square : bits(acclen) = zeros();
  foreach (element from 0 to (ame_nelem - 1)) {
    square = insert_elem_rm(square, 16, element,
      zero_extend(ame_max_dtype_size, value))
  };
  square
}

function ztt_int_status_fill32(value : bits(32)) -> bits(acclen) = {
  var square : bits(acclen) = zeros();
  foreach (element from 0 to (ame_nelem - 1)) {
    square = insert_elem_rm(square, 32, element,
      zero_extend(ame_max_dtype_size, value))
  };
  square
}

function ztt_int_status_first(reg : ameregidx) -> bits(8) =
  extract_elem_rm(read_m_square_rm(MD(Mdregidx(ameregidx_bits(reg))), reg),
                  8, 0)[7 .. 0]

$[test]
function test_ztt_integer_rounding_modes() -> unit = {
  let rnu = ztt_int_status_dtype(0b00, 0b0);
  let rne = ztt_int_status_dtype(0b01, 0b0);
  let rdn = ztt_int_status_dtype(0b10, 0b0);
  let rod = ztt_int_status_dtype(0b11, 0b0);

  ame_test_enable_context();
  amexsat = 0b0;

  // mmean: exact +2.5 distinguishes RNU/RNE from RDN/ROD.
  MD(Mdregidx(0b00000)) = rnu;
  MD(Mdregidx(0b00001)) = rnu;
  MD(Mdregidx(0b00010)) = rnu;
  write_m_square_rm(rnu, Ameregidx(0b00001), ztt_int_status_fill(0x02));
  write_m_square_rm(rnu, Ameregidx(0b00010), ztt_int_status_fill(0x03));
  let _ = execute(TEST_AME_MMEAN_EW(0b00000, 0b00001, 0b00010));
  assert(ztt_int_status_first(Ameregidx(0b00000)) == 0x03);

  MD(Mdregidx(0b00000)) = rne;
  MD(Mdregidx(0b00001)) = rne;
  MD(Mdregidx(0b00010)) = rne;
  write_m_square_rm(rne, Ameregidx(0b00001), ztt_int_status_fill(0x02));
  write_m_square_rm(rne, Ameregidx(0b00010), ztt_int_status_fill(0x03));
  let _ = execute(TEST_AME_MMEAN_EW(0b00000, 0b00001, 0b00010));
  assert(ztt_int_status_first(Ameregidx(0b00000)) == 0x02);

  MD(Mdregidx(0b00000)) = rdn;
  MD(Mdregidx(0b00001)) = rdn;
  MD(Mdregidx(0b00010)) = rdn;
  write_m_square_rm(rdn, Ameregidx(0b00001), ztt_int_status_fill(0x02));
  write_m_square_rm(rdn, Ameregidx(0b00010), ztt_int_status_fill(0x03));
  let _ = execute(TEST_AME_MMEAN_EW(0b00000, 0b00001, 0b00010));
  assert(ztt_int_status_first(Ameregidx(0b00000)) == 0x02);

  MD(Mdregidx(0b00000)) = rod;
  MD(Mdregidx(0b00001)) = rod;
  MD(Mdregidx(0b00010)) = rod;
  write_m_square_rm(rod, Ameregidx(0b00001), ztt_int_status_fill(0x02));
  write_m_square_rm(rod, Ameregidx(0b00010), ztt_int_status_fill(0x03));
  let _ = execute(TEST_AME_MMEAN_EW(0b00000, 0b00001, 0b00010));
  assert(ztt_int_status_first(Ameregidx(0b00000)) == 0x03);

  // mhdiff: exact -2.5 proves RDN is arithmetic rather than toward zero.
  MD(Mdregidx(0b00000)) = rdn;
  MD(Mdregidx(0b00001)) = rdn;
  MD(Mdregidx(0b00010)) = rdn;
  write_m_square_rm(rdn, Ameregidx(0b00001), ztt_int_status_fill(0x05));
  write_m_square_rm(rdn, Ameregidx(0b00010), ztt_int_status_fill(0x00));
  let _ = execute(TEST_AME_MHDIFF_EW(0b00000, 0b00001, 0b00010));
  assert(ztt_int_status_first(Ameregidx(0b00000)) == 0xfd);

  // Negative odd ties also distinguish RNU from RNE and ROD.
  MD(Mdregidx(0b00000)) = rnu;
  MD(Mdregidx(0b00001)) = rnu;
  MD(Mdregidx(0b00010)) = rnu;
  write_m_square_rm(rnu, Ameregidx(0b00001), ztt_int_status_fill(0x05));
  write_m_square_rm(rnu, Ameregidx(0b00010), ztt_int_status_fill(0x00));
  let _ = execute(TEST_AME_MHDIFF_EW(0b00000, 0b00001, 0b00010));
  assert(ztt_int_status_first(Ameregidx(0b00000)) == 0xfe);

  MD(Mdregidx(0b00000)) = rne;
  MD(Mdregidx(0b00001)) = rne;
  MD(Mdregidx(0b00010)) = rne;
  write_m_square_rm(rne, Ameregidx(0b00001), ztt_int_status_fill(0x05));
  write_m_square_rm(rne, Ameregidx(0b00010), ztt_int_status_fill(0x00));
  let _ = execute(TEST_AME_MHDIFF_EW(0b00000, 0b00001, 0b00010));
  assert(ztt_int_status_first(Ameregidx(0b00000)) == 0xfe);

  MD(Mdregidx(0b00000)) = rod;
  MD(Mdregidx(0b00001)) = rod;
  MD(Mdregidx(0b00010)) = rod;
  write_m_square_rm(rod, Ameregidx(0b00001), ztt_int_status_fill(0x05));
  write_m_square_rm(rod, Ameregidx(0b00010), ztt_int_status_fill(0x00));
  let _ = execute(TEST_AME_MHDIFF_EW(0b00000, 0b00001, 0b00010));
  assert(ztt_int_status_first(Ameregidx(0b00000)) == 0xfd);

  // Exact intermediates do not depend on the encoded rounding mode.
  write_m_square_rm(rne, Ameregidx(0b00001), ztt_int_status_fill(0x02));
  write_m_square_rm(rne, Ameregidx(0b00010), ztt_int_status_fill(0x04));
  MD(Mdregidx(0b00000)) = rne;
  MD(Mdregidx(0b00001)) = rne;
  MD(Mdregidx(0b00010)) = rne;
  let _ = execute(TEST_AME_MMEAN_EW(0b00000, 0b00001, 0b00010));
  assert(ztt_int_status_first(Ameregidx(0b00000)) == 0x03);
}

$[test]
function test_ztt_amexsat_integer_commit() -> unit = {
  let int8_sat = ztt_int_status_dtype(0b00, 0b1);
  let int8_wrap = ztt_int_status_dtype(0b00, 0b0);
  let zero : xlenbits = zeros();
  let one : xlenbits = zero_extend(0b1);

  ame_test_enable_context();
  amexsat = 0b0;
  MD(Mdregidx(0b00000)) = int8_sat;
  MD(Mdregidx(0b00001)) = int8_sat;
  MD(Mdregidx(0b00010)) = int8_sat;
  write_m_square_rm(int8_sat, Ameregidx(0b00001), ztt_int_status_fill(0x7f));
  write_m_square_rm(int8_sat, Ameregidx(0b00010), ztt_int_status_fill(0x01));
  let _ = execute(TEST_AME_MADD_EW(0b00000, 0b00001, 0b00010));
  assert(ztt_int_status_first(Ameregidx(0b00000)) == 0x7f);
  assert(read_CSR(0x812) == one);

  // A later non-saturating instruction cannot clear the sticky flag.
  MD(Mdregidx(0b00000)) = int8_wrap;
  MD(Mdregidx(0b00001)) = int8_wrap;
  MD(Mdregidx(0b00010)) = int8_wrap;
  write_m_square_rm(int8_wrap, Ameregidx(0b00001), ztt_int_status_fill(0x01));
  write_m_square_rm(int8_wrap, Ameregidx(0b00010), ztt_int_status_fill(0x02));
  let _ = execute(TEST_AME_MADD_EW(0b00000, 0b00001, 0b00010));
  assert(read_CSR(0x812) == one);

  match write_CSR(0x812, zero) {
    Ok(value) => assert(value == zero),
    Err(_) => assert(false),
  };
  assert(read_CSR(0x812) == zero);
}

$[test]
function test_ztt_amexsat_logexp_commit() -> unit = {
  let int8_sat = ztt_int_status_dtype(0b00, 0b1);
  let one : xlenbits = zero_extend(0b1);

  ame_test_enable_context();
  amexsat = 0b0;
  MD(Mdregidx(0b00000)) = int8_sat;
  MD(Mdregidx(0b00001)) = int8_sat;
  write_m_square_rm(int8_sat, Ameregidx(0b00001), ztt_int_status_fill(0x07));

  // 2^7 is one above the signed INT8 maximum, so this saturates at 127.
  let _ = execute(TEST_AME_MEXP2_EW(0b00000, 0b00001));
  assert(ztt_int_status_first(Ameregidx(0b00000)) == 0x7f);
  assert(read_CSR(0x812) == one);
}

$[test]
function test_ztt_integer_data_scalar_conversion() -> unit = {
  let int8 : bits(32) = 0x40000008;
  let int16 : bits(32) = 0x40000010;
  let unsupported : bits(32) = 0x80000008;

  ame_test_enable_context();
  amestatus = 0b0;
  MD(Mdregidx(0b00000)) = int16;
  MD(Mdregidx(0b00010)) = int16;
  amestype = int8;
  let scalar_reg : regidx = t0;
  X(scalar_reg) = to_bits_unsafe(xlen, unsigned(0x11223344556677ff));
  write_m_square_rm(int16, Ameregidx(0b00010), ztt_int_status_fill16(0x0002));

  // The low INT8 scalar is -1; higher X-register bits must not participate.
  let _ = execute(TEST_AME_MADD_EW_X(0b00000, zero_extend(0b00101), 0b00010));
  assert(extract_elem_rm(read_m_square_rm(int16, Ameregidx(0b00000)), 16, 0)[15 .. 0] == 0x0001);

  // An unsupported scalar conversion retires, reports UN, and preserves Md.
  amestatus = 0b0;
  amestype = unsupported;
  write_m_square_rm(int16, Ameregidx(0b00000), ztt_int_status_fill16(0x5a5a));
  let _ = execute(TEST_AME_MADD_EW_X(0b00000, zero_extend(0b00101), 0b00010));
  assert(amestatus == 0b1);
  assert(extract_elem_rm(read_m_square_rm(int16, Ameregidx(0b00000)), 16, 0)[15 .. 0] == 0x5a5a);
}

$[test]
function test_ztt_float_data_scalar_width() -> unit = {
  let fp16 : bits(32) = 0x14300110;
  let fp32 : bits(32) = 0x20300120;
  let scalar_reg : regidx = t0;

  ame_test_enable_context();
  amestatus = 0b0;
  MD(Mdregidx(0b00000)) = fp16;
  MD(Mdregidx(0b00010)) = fp16;
  amestype = fp16;
  X(scalar_reg) = to_bits_unsafe(xlen, unsigned(0x1122334455663c00));
  write_m_square_rm(fp16, Ameregidx(0b00010),
    ztt_int_status_fill16(0x4000)); // 2.0

  // Exact FP16 scalar use takes only X[15:0], so 1.0 + 2.0 is 3.0.
  let _ = execute(TEST_AME_MADD_EW_X(0b00000, zero_extend(0b00101), 0b00010));
  assert(extract_elem_rm(read_m_square_rm(fp16, Ameregidx(0b00000)), 16, 0)[15 .. 0] == 0x4200);

  // Cross-format scalar conversion remains deliberately unsupported and must
  // not reinterpret an FP16 bit pattern as FP32 input.
  amestatus = 0b0;
  amestype = fp16;
  MD(Mdregidx(0b00000)) = fp32;
  MD(Mdregidx(0b00100)) = fp32;
  write_m_square_rm(fp32, Ameregidx(0b00000),
    ztt_int_status_fill32(0x5a5a5a5a));
  assert(ame_context_owned());
  assert(ame_valid_softfloat_ew_dtype(fp32));
  match ame_scalar_float_data_value(fp32, X(scalar_reg)) {
    None() => (),
    Some(_) => assert(false),
  };
  let _ = execute(TEST_AME_MADD_EW_X(0b00000, zero_extend(0b00101), 0b00100));
  assert(amestatus == 0b1);
  assert(extract_elem_rm(read_m_square_rm(fp32, Ameregidx(0b00000)), 32, 0)[31 .. 0] == 0x5a5a5a5a);
}

$[test]
function test_ztt_unsupported_tuple_and_illegal_group() -> unit = {
  let signed_int8 : bits(32) = 0x40000008;
  let unsigned_int8 : bits(32) = 0x00000008;
  let int32 : bits(32) = 0x40000020;
  let sentinel : bits(8) = 0x5a;

  ame_test_enable_context();
  amestatus = 0b0;

  // Same-width mixed signedness is interpreted in each source datatype and
  // converted only when writing the destination.
  MD(Mdregidx(0b00000)) = signed_int8;
  MD(Mdregidx(0b00001)) = signed_int8;
  MD(Mdregidx(0b00010)) = unsigned_int8;
  write_m_square_rm(signed_int8, Ameregidx(0b00000), ztt_int_status_fill(sentinel));
  write_m_square_rm(signed_int8, Ameregidx(0b00001), ztt_int_status_fill(0x01));
  write_m_square_rm(unsigned_int8, Ameregidx(0b00010), ztt_int_status_fill(0x02));
  let _ = execute(TEST_AME_MADD_EW(0b00000, 0b00001, 0b00010));
  assert(amestatus == 0b0);
  assert(ztt_int_status_first(Ameregidx(0b00000)) == 0x03);

  // A valid encoded M register can still be an illegal four-register group.
  // This remains a synchronous Illegal Instruction and cannot be masked by UN.
  amestatus = 0b0;
  MD(Mdregidx(0b00000)) = int32;
  MD(Mdregidx(0b00010)) = int32;
  let illegal_group = execute(TEST_AME_MADD_EW(0b00000, 0b00010, 0b00010));
  assert(illegal_group == Illegal_Instruction());
  assert(amestatus == 0b0);
}
