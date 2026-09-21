// Current-manual semantics for the split AME zero instructions.
$[test]
function test_ztt_zero_instructions_current_manual() -> unit = {
  let int4 : bits(32) = 0x00000004;
  let int8 : bits(32) = 0x40000008;
  let int16 : bits(32) = 0x40000010;
  let unsupported : bits(32) = 0x80000008;
  let zero_m : amereglen = zeros();
  let one_m : amereglen = ones();
  let zero_acc : ameaccreglen = zeros();
  let one_acc : ameaccreglen = ones();

  ame_test_enable_context();
  amestatus = 0b0;
  AD(Ameadregidx(0b00000)) = int8;
  ACC(Ameaccregidx(0b00000)) = one_acc;
  let _ = execute(TEST_AME_MZERO_2D_ACC(0b00000));
  assert(ACC(Ameaccregidx(0b00000)) == zero_acc);
  assert(amestatus == 0b0);

  AD(Ameadregidx(0b00000)) = unsupported;
  ACC(Ameaccregidx(0b00000)) = one_acc;
  let _ = execute(TEST_AME_MZERO_2D_ACC(0b00000));
  assert(amestatus == 0b1);
  assert(ACC(Ameaccregidx(0b00000)) == one_acc);

  // The instruction encoding names 32 Acc slots, while the default model
  // implements four.  A validly decoded but unavailable register is illegal.
  ACC(Ameaccregidx(0b00100)) = one_acc;
  assert(execute(TEST_AME_MZERO_2D_ACC(0b00100)) == Illegal_Instruction());
  assert(ACC(Ameaccregidx(0b00100)) == one_acc);
  assert(amestatus == 0b1);

  amestatus = 0b0;
  MD(Mdregidx(0b00000)) = int16;
  M(Ameregidx(0b00000)) = one_m;
  M(Ameregidx(0b00001)) = one_m;
  let _ = execute(TEST_AME_MZERO_2D_M(0b00000));
  assert(M(Ameregidx(0b00000)) == zero_m);
  assert(M(Ameregidx(0b00001)) == zero_m);
  assert(amestatus == 0b0);

  MD(Mdregidx(0b00000)) = int4;
  M(Ameregidx(0b00000)) = one_m;
  let _ = execute(TEST_AME_MZERO_2D_M(0b00000));
  assert(M(Ameregidx(0b00000)) == zero_m);

  MD(Mdregidx(0b00000)) = unsupported;
  M(Ameregidx(0b00000)) = one_m;
  let _ = execute(TEST_AME_MZERO_2D_M(0b00000));
  assert(amestatus == 0b1);
  assert(M(Ameregidx(0b00000)) == one_m);
}
