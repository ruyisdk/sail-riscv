// Predicate instructions use the numeric comparison of each `ms1` element with
// zero, independently of the selected-data descriptor.  The comparison is the
// predicate datatype's ordered comparison: a NaN operand compares false and a
// negative zero compares equal to +0.

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
function test_ztt_predicate_numeric_compare_and_dtype() -> unit = {
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

  // A qNaN compares false against zero under the ordered comparison the manual
  // requires (see `mcmpge.ew`: "a NaN operand makes it false"), so `mselge`
  // writes the destination datatype's semantic zero.
  write_m_square_rm(fp32, predicate, ztt_predicate_fill_fp32(0x7fc00000));
  let select_ge = execute(TEST_AME_MSELGE_EW(0b00000, 0b00100, 0b01000));
  assert(select_ge == RETIRE_SUCCESS);
  assert(extract_elem_rm(read_m_square_rm(int8, destination), 8, 0)[7 .. 0] == 0x00);

  // A negative zero compares equal to +0 under the ordered numeric comparison
  // the manual defines, so ge selects the source data while lt writes the
  // destination datatype's semantic zero.
  write_m_square_rm(fp32, predicate, ztt_predicate_fill_fp32(0x80000000));
  let select_ge_neg_zero = execute(TEST_AME_MSELGE_EW(0b00000, 0b00100, 0b01000));
  assert(select_ge_neg_zero == RETIRE_SUCCESS);
  assert(extract_elem_rm(read_m_square_rm(int8, destination), 8, 0)[7 .. 0] == 0x5a);
  let select_lt = execute(TEST_AME_MSELLT_EW(0b00000, 0b00100, 0b01000));
  assert(select_lt == RETIRE_SUCCESS);
  assert(extract_elem_rm(read_m_square_rm(int8, destination), 8, 0)[7 .. 0] == 0x00);

  // Conditional move preserves the old destination when the comparison is
  // false, unlike select which writes a semantic zero.
  write_m_square_rm(int8, destination, ztt_predicate_fill(0x33));
  write_m_square_rm(fp32, predicate, ztt_predicate_fill_fp32(0x00000000));
  let cmov_lt_false = execute(TEST_AME_MCMOVLT_EW(0b00000, 0b00100, 0b01000));
  assert(cmov_lt_false == RETIRE_SUCCESS);
  assert(extract_elem_rm(read_m_square_rm(int8, destination), 8, 0)[7 .. 0] == 0x33);

  // A NaN operand also makes the non-negative comparison false, so `mcmovge`
  // preserves the old destination just like the false `mcmovlt` case above.
  write_m_square_rm(fp32, predicate, ztt_predicate_fill_fp32(0x7fc00000));
  let cmov_ge_nan = execute(TEST_AME_MCMOVGE_EW(0b00000, 0b00100, 0b01000));
  assert(cmov_ge_nan == RETIRE_SUCCESS);
  assert(extract_elem_rm(read_m_square_rm(int8, destination), 8, 0)[7 .. 0] == 0x33);
}
