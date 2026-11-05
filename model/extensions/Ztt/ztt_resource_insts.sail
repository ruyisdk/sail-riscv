// Resource Management instruction families.
// Encodings follow manual-main/instructions.json; the encoding, execute
// and mnemonic coverage of this file is checked by test/ztt/gen/check_manual_sync.py.

// *****************************************************************
// ame.acquire
union clause instruction = AME_AME_ACQUIRE : (bits(5), bits(5))

mapping clause encdec = AME_AME_ACQUIRE(rd, rs1)
  <-> 0b101001001001 @ rs1 : bits(5) @ 0b000 @ rd : bits(5) @ 0b0101011
  when currentlyEnabled(Ext_Ztt)

mapping clause assembly = AME_AME_ACQUIRE(rd, rs1)
  <-> "ame.acquire" ^ spc() ^ reg_name(encdec_reg(rd)) ^ sep() ^ reg_name(encdec_reg(rs1))

function clause execute AME_AME_ACQUIRE(rd, rs1) = {
  if not(ame_context_enabled())
  then return Illegal_Instruction();

  X(Regidx(trunc(rd))) = ame_acquire_backend(X(Regidx(trunc(rs1))));
  RETIRE_SUCCESS
}

// *****************************************************************
// ame.release
union clause instruction = AME_AME_RELEASE : unit

mapping clause encdec = AME_AME_RELEASE()
  <-> 0b10100100101000000000000000101011
  when currentlyEnabled(Ext_Ztt)

mapping clause assembly = AME_AME_RELEASE()
  <-> "ame.release"

function clause execute AME_AME_RELEASE() = {
  if not(ame_context_enabled()) then return Illegal_Instruction();
  ame_release_backend();
  RETIRE_SUCCESS
}
