// Common operand formation tests.  The default configuration has N=8 and an
// 8-bit unit, so Int4 contains two logical squares in one physical M register.
function ztt_nsq_fill(dtype : bits(32), value : bits(8), square : nat)
  -> bits(acclen) = {
  var data : bits(acclen) = zeros();
  foreach (e from 0 to (ame_nelem - 1)) {
    data = insert_elem_rm(data, ame_dtype_size(dtype), square * ame_nelem + e,
      zero_extend(ame_max_dtype_size, value))
  };
  data
}

function ztt_nsq_first(dtype : bits(32), reg : ameregidx, square : nat)
  -> bits(8) =
  read_m_elem(dtype, square * ame_nelem, reg)[7 .. 0]

$[test]
function test_ztt_common_nsq_packed_and_expanded() -> unit = {
  let int4 : bits(32) = 0x00000004;
  let int8 : bits(32) = 0x40000008;
  let int16 : bits(32) = 0x40000010;

  ame_test_enable_context();
  amestatus = 0b0;
  MD(Mdregidx(0b00000)) = int16;
  MD(Mdregidx(0b00010)) = int4;
  MD(Mdregidx(0b00110)) = int8;
  write_m_square_rm(int16, Ameregidx(0b00000), zeros());

  // A is packed: square 0 is 1 and square 1 is 3 in m2.
  var packed : bits(acclen) = ztt_nsq_fill(int4, 0x01, 0);
  let packed_nibble4 : bits(4) = 0b0011;
  let packed_nibble : bits(ame_max_dtype_size) = zero_extend(ame_max_dtype_size, packed_nibble4);
  foreach (e from 0 to (ame_nelem - 1)) {
    packed = insert_elem_rm(packed, 4, ame_nelem + e,
      packed_nibble)
  };
  foreach (e from 0 to (2 * ame_nelem - 1)) {
    write_m_elem(int4, Ameregidx(0b00010), e, extract_elem_rm(packed, 4, e))
  };

  // B and D are non-packed and therefore expand to two adjacent registers.
  write_m_square_rm(int8, Ameregidx(0b00110), ztt_nsq_fill(int8, 0x02, 0));
  write_m_square_rm(int8, Ameregidx(0b00111), ztt_nsq_fill(int8, 0x04, 0));
  // The packed source at m2 overlaps the second half of destination m0-m3.
  // Correct results therefore require a pre-writeback source snapshot.

  assert(execute(TEST_AME_MADD_EW(0b00000, 0b00010, 0b00110)) == RETIRE_SUCCESS);
  assert(amestatus == 0b0);
  assert(ztt_nsq_first(int16, Ameregidx(0b00000), 0) == 0x03);
  assert(ztt_nsq_first(int16, Ameregidx(0b00000), 1) == 0x07);

  // Complete formed spans, not merely the first square group, are checked.
  assert(ame_formed_span(int4, 2) == 1);
  assert(ame_formed_span(int8, 2) == 2);
  assert(ame_formed_span(int16, 2) == 4);
  assert(not(ame_check_formed_operand(Ameregidx(0b00001), int16, 2)));
  assert(not(ame_check_formed_operand(Ameregidx(0b11110), int16, 2)));
}

$[test]
function test_ztt_mmul_nsq_inner_dimension() -> unit = {
  let int4 : bits(32) = 0x00000004;
  let int8 : bits(32) = 0x40000008;
  let int16 : bits(32) = 0x40000010;

  ame_test_enable_context();
  MD(Mdregidx(0b00100)) = int4;
  MD(Mdregidx(0b00101)) = int4;
  AD(Ameadregidx(0b00000)) = int16;
  ACC(Ameaccregidx(0b00000)) = zeros();

  foreach (e from 0 to (2 * ame_nelem - 1)) {
    write_m_elem(int4, Ameregidx(0b00100), e,
      zero_extend(ame_max_dtype_size, 0x01));
    write_m_elem(int4, Ameregidx(0b00101), e,
      zero_extend(ame_max_dtype_size, 0x01))
  };

  assert(execute(TEST_AME_MMULACC_2D(0b00000, 0b00100, 0b00101)) == RETIRE_SUCCESS);
  assert(extract_elem_rm(ACC(Ameaccregidx(0b00000)), 16, 0)[15 .. 0] ==
         to_bits_unsafe(16, 2 * ame_nlen));

  // Mixed-width matmul uses source numeric values without first narrowing
  // either input to the accumulator datatype.
  MD(Mdregidx(0b00110)) = int8;
  write_m_square_rm(int8, Ameregidx(0b00110), ztt_nsq_fill(int8, 0x02, 0));
  write_m_square_rm(int8, Ameregidx(0b00111), ztt_nsq_fill(int8, 0x02, 0));
  ACC(Ameaccregidx(0b00000)) = zeros();
  assert(execute(TEST_AME_MMULACC_2D(0b00000, 0b00100, 0b00110)) == RETIRE_SUCCESS);
  assert(extract_elem_rm(ACC(Ameaccregidx(0b00000)), 16, 0)[15 .. 0] ==
         to_bits_unsafe(16, 4 * ame_nlen));
}

$[test]
function test_ztt_nsq_remaining_1d_paths() -> unit = {
  let int4 : bits(32) = 0x00000004;
  let int8 : bits(32) = 0x40000008;

  ame_test_enable_context();
  MD(Mdregidx(0b00000)) = int4;
  MD(Mdregidx(0b00001)) = int4;
  MD(Mdregidx(0b00010)) = int4;
  MD(Mdregidx(0b00011)) = int8;

  // Ternary and unary paths process both packed squares.
  foreach (e from 0 to (2 * ame_nelem - 1)) {
    write_m_elem(int4, Ameregidx(0b00001), e, zero_extend(ame_max_dtype_size, 0x01));
    write_m_elem(int4, Ameregidx(0b00010), e, zero_extend(ame_max_dtype_size, 0x02));
    write_m_elem(int4, Ameregidx(0b00000), e, zero_extend(ame_max_dtype_size, 0x00))
  };
  assert(execute(TEST_AME_MMULACC_EW(0b00000, 0b00001, 0b00010)) == RETIRE_SUCCESS);
  assert(read_m_elem(int4, ame_nelem, Ameregidx(0b00000))[7 .. 0] == 0x02);
  assert(execute(TEST_AME_MABS_EW(0b00000, 0b00000)) == RETIRE_SUCCESS);
  assert(read_m_elem(int4, ame_nelem, Ameregidx(0b00000))[7 .. 0] == 0x02);

  // mconv expands both packed source squares and compresses them back.
  assert(execute(TEST_AME_MCONV_EW(0b00011, 0b00001)) == RETIRE_SUCCESS);
  assert(read_m_elem(int8, 0, Ameregidx(0b00011))[7 .. 0] == 0x01);
  assert(read_m_elem(int8, 0, Ameregidx(0b00100))[7 .. 0] == 0x01);
  assert(ame_check_formed_operand(Ameregidx(0b00001), int4, 2));
  assert(ame_check_formed_operand(Ameregidx(0b00011), int8, 2));
  assert(execute(TEST_AME_MCONV_EW(0b00001, 0b00011)) == RETIRE_SUCCESS);
  assert(read_m_elem(int4, ame_nelem, Ameregidx(0b00001))[7 .. 0] == 0x01);

  // Predicate selection uses a packed predicate source and processes both
  // logical squares without treating the packed register as one square.
  foreach (e from 0 to (2 * ame_nelem - 1)) {
    write_m_elem(int4, Ameregidx(0b00001), e,
      if e % ame_nelem == 0 then zero_extend(ame_max_dtype_size, 0x08)
      else zero_extend(ame_max_dtype_size, 0x00));
    write_m_elem(int4, Ameregidx(0b00010), e, zero_extend(ame_max_dtype_size, 0x05));
    write_m_elem(int4, Ameregidx(0b00000), e, zero_extend(ame_max_dtype_size, 0x00))
  };
  assert(execute(TEST_AME_MSELGE_EW(0b00000, 0b00001, 0b00010)) == RETIRE_SUCCESS);
  assert(read_m_elem(int4, 0, Ameregidx(0b00000))[7 .. 0] == 0x00);
  assert(read_m_elem(int4, ame_nelem, Ameregidx(0b00000))[7 .. 0] == 0x00);
}

$[test]
function test_ztt_nsq_logexp_paths() -> unit = {
  let int4 : bits(32) = 0x00000004;

  ame_test_enable_context();
  MD(Mdregidx(0b00000)) = int4;
  MD(Mdregidx(0b00001)) = int4;
  MD(Mdregidx(0b00010)) = int4;

  // Packed Int4 has two logical squares in one physical register.  Unary
  // log/exp must transform both squares, not just the first one.
  foreach (e from 0 to (ame_nelem - 1)) {
    write_m_elem(int4, Ameregidx(0b00001), e,
      zero_extend(ame_max_dtype_size, 0x01));
    write_m_elem(int4, Ameregidx(0b00001), ame_nelem + e,
      zero_extend(ame_max_dtype_size, 0x02));
  };
  assert(execute(TEST_AME_MEXP2_EW(0b00000, 0b00001)) == RETIRE_SUCCESS);
  assert(read_m_elem(int4, 0, Ameregidx(0b00000))[7 .. 0] == 0x02);
  assert(read_m_elem(int4, ame_nelem, Ameregidx(0b00000))[7 .. 0] == 0x04);
  assert(execute(TEST_AME_MLOG2_EW(0b00000, 0b00000)) == RETIRE_SUCCESS);
  assert(read_m_elem(int4, 0, Ameregidx(0b00000))[7 .. 0] == 0x01);
  assert(read_m_elem(int4, ame_nelem, Ameregidx(0b00000))[7 .. 0] == 0x02);

  // mldexp.ew uses two formed packed operands; the second square has a
  // distinct exponent and catches implementations that process only N*N.
  foreach (e from 0 to (ame_nelem - 1)) {
    write_m_elem(int4, Ameregidx(0b00001), e,
      zero_extend(ame_max_dtype_size, 0x01));
    write_m_elem(int4, Ameregidx(0b00001), ame_nelem + e,
      zero_extend(ame_max_dtype_size, 0x03));
    write_m_elem(int4, Ameregidx(0b00010), e,
      zero_extend(ame_max_dtype_size, 0x01));
    write_m_elem(int4, Ameregidx(0b00010), ame_nelem + e,
      zero_extend(ame_max_dtype_size, 0x02));
  };
  assert(execute(TEST_AME_MLDEXP_EW(0b00000, 0b00001, 0b00010)) == RETIRE_SUCCESS);
  assert(read_m_elem(int4, 0, Ameregidx(0b00000))[7 .. 0] == 0x02);
  assert(read_m_elem(int4, ame_nelem, Ameregidx(0b00000))[7 .. 0] == 0x0c);
}

$[test]
function test_ztt_nsq_destination_scalar_and_shift_paths() -> unit = {
  let uint4 : bits(32) = 0x00000004;
  let uint8 : bits(32) = 0x00000008;
  let scalar_reg : regidx = t0;

  ame_test_enable_context();
  amestatus = 0b0;
  amestype = uint8;
  X(scalar_reg) = zero_extend(0x02);

  // The packed destination alone raises N_sq to two.  Both non-packed
  // sources must expand to two registers even though neither source is packed.
  MD(Mdregidx(0b00000)) = uint4;
  MD(Mdregidx(0b00010)) = uint8;
  MD(Mdregidx(0b00100)) = uint8;
  write_m_square_rm(uint8, Ameregidx(0b00010), ztt_nsq_fill(uint8, 0x01, 0));
  write_m_square_rm(uint8, Ameregidx(0b00011), ztt_nsq_fill(uint8, 0x03, 0));
  write_m_square_rm(uint8, Ameregidx(0b00100), ztt_nsq_fill(uint8, 0x02, 0));
  write_m_square_rm(uint8, Ameregidx(0b00101), ztt_nsq_fill(uint8, 0x04, 0));
  assert(execute(TEST_AME_MADD_EW(0b00000, 0b00010, 0b00100)) == RETIRE_SUCCESS);
  assert(ztt_nsq_first(uint4, Ameregidx(0b00000), 0) == 0x03);
  assert(ztt_nsq_first(uint4, Ameregidx(0b00000), 1) == 0x07);

  // Scalar binary and ternary helpers use the same formed tensor span.
  assert(execute(TEST_AME_MADD_EW_X(0b00000, 0b00101, 0b00100)) == RETIRE_SUCCESS);
  assert(ztt_nsq_first(uint4, Ameregidx(0b00000), 0) == 0x04);
  assert(ztt_nsq_first(uint4, Ameregidx(0b00000), 1) == 0x06);
  assert(execute(TEST_AME_MMULACC_EW_X(0b00000, 0b00101, 0b00100)) == RETIRE_SUCCESS);
  assert(ztt_nsq_first(uint4, Ameregidx(0b00000), 0) == 0x08);
  assert(ztt_nsq_first(uint4, Ameregidx(0b00000), 1) == 0x0e);

  // Packed shift data and per-element amounts exercise both logical squares.
  MD(Mdregidx(0b00001)) = uint4;
  MD(Mdregidx(0b00010)) = uint4;
  foreach (e from 0 to (ame_nelem - 1)) {
    write_m_elem(uint4, Ameregidx(0b00001), e, zero_extend(ame_max_dtype_size, 0x01));
    write_m_elem(uint4, Ameregidx(0b00001), ame_nelem + e, zero_extend(ame_max_dtype_size, 0x02));
    write_m_elem(uint4, Ameregidx(0b00010), e, zero_extend(ame_max_dtype_size, 0x01));
    write_m_elem(uint4, Ameregidx(0b00010), ame_nelem + e, zero_extend(ame_max_dtype_size, 0x02))
  };
  assert(execute(TEST_AME_MSLL_EW(0b00000, 0b00001, 0b00010)) == RETIRE_SUCCESS);
  assert(ztt_nsq_first(uint4, Ameregidx(0b00000), 0) == 0x02);
  assert(ztt_nsq_first(uint4, Ameregidx(0b00000), 1) == 0x08);
  assert(execute(TEST_AME_MSLL_EW_X(0b00000, 0b00101, 0b00001)) == RETIRE_SUCCESS);
  assert(ztt_nsq_first(uint4, Ameregidx(0b00000), 0) == 0x04);
  assert(ztt_nsq_first(uint4, Ameregidx(0b00000), 1) == 0x08);
}

$[test]
function test_ztt_gather_scatter_truncate_indices() -> unit = {
  let uint8 : bits(32) = 0x00000008;
  ame_test_enable_context();
  amestatus = 0b0;
  MD(Mdregidx(0b00000)) = uint8;
  MD(Mdregidx(0b00001)) = uint8;
  MD(Mdregidx(0b00010)) = uint8;
  MD(Mdregidx(0b00011)) = uint8;

  var source : bits(acclen) = zeros();
  var indices : bits(acclen) = zeros();
  foreach (row from 0 to (ame_nlen - 1)) {
    foreach (col from 0 to (ame_nlen - 1)) {
      source = insert_elem_rm(source, 8, row * ame_nlen + col,
        zero_extend(ame_max_dtype_size, to_bits_unsafe(8, col + 1)));
      // For N=8, 0x89 and 0x01 have the same architectural index.
      indices = insert_elem_rm(indices, 8, row * ame_nlen + col,
        zero_extend(ame_max_dtype_size, 0x89))
    }
  };
  write_m_square_rm(uint8, Ameregidx(0b00001), source);
  write_m_square_rm(uint8, Ameregidx(0b00010), indices);

  assert(execute(TEST_AME_MCOLGATHER_EW(0b00000, 0b00001, 0b00010)) == RETIRE_SUCCESS);
  assert(extract_elem_rm(read_m_square_rm(uint8, Ameregidx(0b00000)), 8, 0)[7 .. 0] == 0x02);

  write_m_square_rm(uint8, Ameregidx(0b00011), zeros());
  write_m_square_rm(uint8, Ameregidx(0b00001), ztt_nsq_fill(uint8, 0x01, 0));
  assert(execute(TEST_AME_MCOLSCATADD_EW(0b00011, 0b00001, 0b00010)) == RETIRE_SUCCESS);
  assert(extract_elem_rm(read_m_square_rm(uint8, Ameregidx(0b00011)), 8, 1)[7 .. 0] ==
         to_bits_unsafe(8, ame_nlen));
  assert(amestatus == 0b0);
}
