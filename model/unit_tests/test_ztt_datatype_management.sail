// Current-manual semantics for the first AME datatype-management tranche.
$[test]
function test_ztt_datatype_management_current_manual() -> unit = {
  let int8 : bits(32) = 0x40000008;
  let int16 : bits(32) = 0x40000010;
  let unsupported : bits(32) = 0x80000008;
  let int8_x : xlenbits = zero_extend(int8);
  let int16_x : xlenbits = zero_extend(int16);
  let zero_m : amereglen = zeros();
  let one_m : amereglen = ones();
  let zero_acc : ameaccreglen = zeros();
  let one_acc : ameaccreglen = ones();
  let mset_src : bits(5) = 0b00101;
  let aset_src : bits(5) = 0b00110;
  let result_xd : bits(5) = 0b00111;

  ame_test_enable_context();
  amestatus = 0b0;
  X(Regidx(trunc(mset_src))) = int16_x;
  M(Ameregidx(0b00000)) = one_m;
  M(Ameregidx(0b00001)) = one_m;
  let _ = execute(TEST_AME_MSETTYP(0b00000, mset_src));
  assert(MD(Mdregidx(0b00000)) == int16);
  assert(M(Ameregidx(0b00000)) == zero_m);
  assert(M(Ameregidx(0b00001)) == zero_m);

  M(Ameregidx(0b00000)) = one_m;
  X(Regidx(trunc(mset_src))) = zero_extend(unsupported);
  let _ = execute(TEST_AME_MSETTYP(0b00000, mset_src));
  assert(amestatus == 0b1);
  assert(MD(Mdregidx(0b00000)) == int16);
  assert(M(Ameregidx(0b00000)) == one_m);

  amestatus = 0b0;
  X(Regidx(trunc(aset_src))) = int8_x;
  ACC(Ameaccregidx(0b00000)) = one_acc;
  let _ = execute(TEST_AME_ASETTYP(0b00000, aset_src));
  assert(AD(Ameadregidx(0b00000)) == int8);
  assert(ACC(Ameaccregidx(0b00000)) == zero_acc);

  ACC(Ameaccregidx(0b00000)) = one_acc;
  X(Regidx(trunc(aset_src))) = zero_extend(unsupported);
  let _ = execute(TEST_AME_ASETTYP(0b00000, aset_src));
  assert(amestatus == 0b1);
  assert(AD(Ameadregidx(0b00000)) == int8);
  assert(ACC(Ameaccregidx(0b00000)) == one_acc);

  X(Regidx(trunc(result_xd))) = zeros();
  let _ = execute(TEST_AME_MGETTYP(result_xd, 0b00000));
  assert(X(Regidx(trunc(result_xd))) == int16_x);
  let _ = execute(TEST_AME_AGETTYP(result_xd, 0b00000));
  assert(X(Regidx(trunc(result_xd))) == int8_x);
}
