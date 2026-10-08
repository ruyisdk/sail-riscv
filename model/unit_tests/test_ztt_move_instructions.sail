// Current-manual semantics for AME M/accumulator moves, including packed tiles.
$[test]
function test_ztt_move_instructions_current_manual() -> unit = {
  let int4 : bits(32) = 0x40000004;
  let uint8 : bits(32) = 0x00000008;
  let int8 : bits(32) = 0x40000008;
  let int16 : bits(32) = 0x40000010;
  let zero_m : amereglen = zeros();
  let one_m : amereglen = ones();
  let zero_acc : ameaccreglen = zeros();
  let one_acc : ameaccreglen = ones();
  let packed_m : amereglen = zero_extend(mlen, ones(mlen / 2));
  let one_int8 : bits(ame_max_dtype_size) = zero_extend(0xff);
  let one_int4 : bits(ame_max_dtype_size) = zero_extend(0b1111);

  ame_test_enable_context();
  amestatus = 0b0;
  MD(Mdregidx(0b00000)) = int8;
  AD(Ameadregidx(0b00000)) = int8;
  ACC(Ameaccregidx(0b00000)) = one_acc;
  M(Ameregidx(0b00000)) = zero_m;
  let _ = execute(TEST_AME_MMOV_M_A(0b00000, 0b00000));
  assert(M(Ameregidx(0b00000)) == one_m);

  M(Ameregidx(0b00000)) = one_m;
  ACC(Ameaccregidx(0b00000)) = zero_acc;
  let _ = execute(TEST_AME_MMOV_A_M(0b00000, 0b00000));
  var int8_acc : ameaccreglen = zeros();
  foreach (e from 0 to (ame_nelem - 1)) {
    int8_acc = insert_elem_rm(int8_acc, 8, e, one_int8);
  };
  assert(ACC(Ameaccregidx(0b00000)) == int8_acc);

  // The default configuration has an 8-bit unit dtype, so int4 packs two
  // N-by-N accumulator tiles into one M register.
  MD(Mdregidx(0b00000)) = int4;
  AD(Ameadregidx(0b00000)) = int4;
  ACC(Ameaccregidx(0b00000)) = one_acc;
  ACC(Ameaccregidx(0b00001)) = zero_acc;
  M(Ameregidx(0b00000)) = zero_m;
  let _ = execute(TEST_AME_MMOV_M_A(0b00000, 0b00000));
  assert(M(Ameregidx(0b00000)) == packed_m);

  var packed_acc : ameaccreglen = zeros();
  foreach (e from 0 to (ame_nelem - 1)) {
    packed_acc = insert_elem_rm(packed_acc, 4, e, one_int4);
  };
  ACC(Ameaccregidx(0b00000)) = zero_acc;
  ACC(Ameaccregidx(0b00001)) = one_acc;
  let _ = execute(TEST_AME_MMOV_A_M(0b00000, 0b00000));
  assert(ACC(Ameaccregidx(0b00000)) == packed_acc);
  assert(ACC(Ameaccregidx(0b00001)) == zero_acc);

  amestatus = 0b0;
  MD(Mdregidx(0b00000)) = int8;
  AD(Ameadregidx(0b00000)) = int16;
  M(Ameregidx(0b00000)) = zero_m;
  ACC(Ameaccregidx(0b00000)) = one_acc;
  let _ = execute(TEST_AME_MMOV_M_A(0b00000, 0b00000));
  assert(amestatus == 0b1);
  assert(M(Ameregidx(0b00000)) == zero_m);

  // mmov.m.m requires identical descriptors, not merely equal element
  // widths.  A mismatch is an unsupported operation and preserves md.
  amestatus = 0b0;
  MD(Mdregidx(0b00000)) = int8;
  MD(Mdregidx(0b00001)) = uint8;
  M(Ameregidx(0b00000)) = zero_m;
  M(Ameregidx(0b00001)) = one_m;
  assert(execute(TEST_AME_MMOV_M_M(0b00000, 0b00001)) == RETIRE_SUCCESS);
  assert(amestatus == 0b1);
  assert(M(Ameregidx(0b00000)) == zero_m);

  // Exactly matching descriptors copy the complete source image.
  amestatus = 0b0;
  MD(Mdregidx(0b00001)) = int8;
  assert(execute(TEST_AME_MMOV_M_M(0b00000, 0b00001)) == RETIRE_SUCCESS);
  assert(amestatus == 0b0);
  assert(M(Ameregidx(0b00000)) == one_m);
}
