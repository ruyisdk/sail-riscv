// Predicate instructions use the raw predicate sign bit, independently of
// the selected-data descriptor.  A positive-sign NaN is deliberately used so
// this cannot accidentally pass through a floating numeric comparison.

function ztt_predicate_fill(value : bits(8)) -> bits(acclen) = {
  var square : bits(acclen) = zeros();
  foreach (element from 0 to (ame_nelem - 1)) {
    square = insert_elem_rm(square, 8, element,
      zero_extend(ame_max_dtype_size, value))
  };
  square
}

function ztt_predicate_fill_fp32(value : bits(32)) -> bits(acclen) = {
  var square : bits(acclen) = zeros();
  foreach (element from 0 to (ame_nelem - 1)) {
    square = insert_elem_rm(square, 32, element,
      zero_extend(ame_max_dtype_size, value))
  };
  square
}

$[test]
function test_ztt_predicate_raw_sign_and_dtype() -> unit = {
  let int8 : bits(32) = 0x40000008;
  let fp32 : bits(32) = 0x20300120;
  let destination = Ameregidx(0b00000);
  let predicate = Ameregidx(0b00100);
  let source = Ameregidx(0b01000);

  ame_test_enable_context();
  amestatus = 0b0;
  MD(Mdregidx(ameregidx_bits(destination))) = int8;
  MD(Mdregidx(ameregidx_bits(predicate))) = fp32;
  MD(Mdregidx(ameregidx_bits(source))) = int8;
  write_m_square_rm(int8, source, ztt_predicate_fill(0x5a));

  // Positive qNaN has a clear raw sign bit: mselge selects integer source
  // data even though a numeric FP comparison would be unordered.
  write_m_square_rm(fp32, predicate, ztt_predicate_fill_fp32(0x7fc00000));
  let select_ge = execute(TEST_AME_MSELGE_EW(0b00000, 0b00100, 0b01000));
  assert(select_ge == RETIRE_SUCCESS);
  assert(extract_elem_rm(read_m_square_rm(int8, destination), 8, 0)[7 .. 0] == 0x5a);

  // A negative zero has its raw sign bit set: ge writes semantic zero, while
  // lt selects the same data value.
  write_m_square_rm(fp32, predicate, ztt_predicate_fill_fp32(0x80000000));
  let select_ge_false = execute(TEST_AME_MSELGE_EW(0b00000, 0b00100, 0b01000));
  assert(select_ge_false == RETIRE_SUCCESS);
  assert(extract_elem_rm(read_m_square_rm(int8, destination), 8, 0)[7 .. 0] == 0x00);
  let select_lt = execute(TEST_AME_MSELLT_EW(0b00000, 0b00100, 0b01000));
  assert(select_lt == RETIRE_SUCCESS);
  assert(extract_elem_rm(read_m_square_rm(int8, destination), 8, 0)[7 .. 0] == 0x5a);

  // Conditional move preserves the old destination when its raw-sign test
  // fails, unlike select which writes a semantic zero.
  write_m_square_rm(int8, destination, ztt_predicate_fill(0x33));
  write_m_square_rm(fp32, predicate, ztt_predicate_fill_fp32(0x00000000));
  let cmov_lt_false = execute(TEST_AME_MCMOVLT_EW(0b00000, 0b00100, 0b01000));
  assert(cmov_lt_false == RETIRE_SUCCESS);
  assert(extract_elem_rm(read_m_square_rm(int8, destination), 8, 0)[7 .. 0] == 0x33);
}
