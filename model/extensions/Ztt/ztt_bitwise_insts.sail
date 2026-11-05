// Bitwise instruction families.
// Encodings follow manual-main/instructions.json; the encoding, execute
// and mnemonic coverage of this file is checked by test/ztt/gen/check_manual_sync.py.

// *****************************************************************
// Bit: R3(md, ms, ms) instruction family
mapping encdec_bit_r3funct7_md_ms_ms : bit_r3funct7_md_ms_ms <-> bits(7) = {
  AME_MAND_EW <-> 0b0011010,
  AME_MANDNOT_EW <-> 0b0011100,
  AME_MOR_EW <-> 0b0011110,
  AME_MORNOT_EW <-> 0b0100000,
  AME_MSLL_EW <-> 0b0100010,
  AME_MSRA_EW <-> 0b0100100,
  AME_MSRL_EW <-> 0b0100110,
  AME_MXOR_EW <-> 0b0101000
}

mapping bit_r3funct7_md_ms_ms_mnemonic : bit_r3funct7_md_ms_ms <-> string = {
  AME_MAND_EW <-> "mand.ew",
  AME_MANDNOT_EW <-> "mandnot.ew",
  AME_MOR_EW <-> "mor.ew",
  AME_MORNOT_EW <-> "mornot.ew",
  AME_MSLL_EW <-> "msll.ew",
  AME_MSRA_EW <-> "msra.ew",
  AME_MSRL_EW <-> "msrl.ew",
  AME_MXOR_EW <-> "mxor.ew"
}

mapping bit_r3funct7_md_ms_ms_assembly : (bit_r3funct7_md_ms_ms, bits(5), bits(5), bits(5)) <-> string = {
  (AME_MAND_EW, rd, rs1, rs2) <-> bit_r3funct7_md_ms_ms_mnemonic(AME_MAND_EW) ^ spc() ^ amereg_name_raw(rd) ^ sep() ^ amereg_name_raw(rs1) ^ sep() ^ amereg_name_raw(rs2),
  (AME_MANDNOT_EW, rd, rs1, rs2) <-> bit_r3funct7_md_ms_ms_mnemonic(AME_MANDNOT_EW) ^ spc() ^ amereg_name_raw(rd) ^ sep() ^ amereg_name_raw(rs1) ^ sep() ^ amereg_name_raw(rs2),
  (AME_MOR_EW, rd, rs1, rs2) <-> bit_r3funct7_md_ms_ms_mnemonic(AME_MOR_EW) ^ spc() ^ amereg_name_raw(rd) ^ sep() ^ amereg_name_raw(rs1) ^ sep() ^ amereg_name_raw(rs2),
  (AME_MORNOT_EW, rd, rs1, rs2) <-> bit_r3funct7_md_ms_ms_mnemonic(AME_MORNOT_EW) ^ spc() ^ amereg_name_raw(rd) ^ sep() ^ amereg_name_raw(rs1) ^ sep() ^ amereg_name_raw(rs2),
  (AME_MSLL_EW, rd, rs1, rs2) <-> bit_r3funct7_md_ms_ms_mnemonic(AME_MSLL_EW) ^ spc() ^ amereg_name_raw(rd) ^ sep() ^ amereg_name_raw(rs1) ^ sep() ^ amereg_name_raw(rs2),
  (AME_MSRA_EW, rd, rs1, rs2) <-> bit_r3funct7_md_ms_ms_mnemonic(AME_MSRA_EW) ^ spc() ^ amereg_name_raw(rd) ^ sep() ^ amereg_name_raw(rs1) ^ sep() ^ amereg_name_raw(rs2),
  (AME_MSRL_EW, rd, rs1, rs2) <-> bit_r3funct7_md_ms_ms_mnemonic(AME_MSRL_EW) ^ spc() ^ amereg_name_raw(rd) ^ sep() ^ amereg_name_raw(rs1) ^ sep() ^ amereg_name_raw(rs2),
  (AME_MXOR_EW, rd, rs1, rs2) <-> bit_r3funct7_md_ms_ms_mnemonic(AME_MXOR_EW) ^ spc() ^ amereg_name_raw(rd) ^ sep() ^ amereg_name_raw(rs1) ^ sep() ^ amereg_name_raw(rs2),
}

union clause instruction = BIT_R3_MD_MS_MS_TYPE : (bit_r3funct7_md_ms_ms, bits(5), bits(5), bits(5))

mapping clause encdec = BIT_R3_MD_MS_MS_TYPE(op, rd, rs1, rs2)
  <-> encdec_bit_r3funct7_md_ms_ms(op) @ rs2 : bits(5) @ rs1 : bits(5) @ 0b000 @ rd : bits(5) @ 0b0101011
  when currentlyEnabled(Ext_Ztt)

mapping clause assembly = BIT_R3_MD_MS_MS_TYPE(op, rd, rs1, rs2)
  <-> bit_r3funct7_md_ms_ms_assembly(op, rd, rs1, rs2)

function clause execute BIT_R3_MD_MS_MS_TYPE(op, rd, rs1, rs2) = {
  if not(ame_context_owned()) |
     not(ame_check_mreg_operand(rd)) |
     not(ame_check_mreg_operand(rs1)) |
     not(ame_check_mreg_operand(rs2))
  then return Illegal_Instruction();

  match op {
    AME_MAND_EW => ame_retire_if(ame_ew_binary_m(MD(Mdregidx(rd)), MD(Mdregidx(rs1)), MD(Mdregidx(rs2)), Ameregidx(rd), Ameregidx(rs1), Ameregidx(rs2), AME_INT_AND)),
    AME_MANDNOT_EW => ame_retire_if(ame_ew_binary_m(MD(Mdregidx(rd)), MD(Mdregidx(rs1)), MD(Mdregidx(rs2)), Ameregidx(rd), Ameregidx(rs1), Ameregidx(rs2), AME_INT_ANDNOT)),
    AME_MOR_EW => ame_retire_if(ame_ew_binary_m(MD(Mdregidx(rd)), MD(Mdregidx(rs1)), MD(Mdregidx(rs2)), Ameregidx(rd), Ameregidx(rs1), Ameregidx(rs2), AME_INT_OR)),
    AME_MORNOT_EW => ame_retire_if(ame_ew_binary_m(MD(Mdregidx(rd)), MD(Mdregidx(rs1)), MD(Mdregidx(rs2)), Ameregidx(rd), Ameregidx(rs1), Ameregidx(rs2), AME_INT_ORNOT)),
    AME_MSLL_EW => ame_retire_if(ame_ew_shift_m(MD(Mdregidx(rd)), MD(Mdregidx(rs1)), MD(Mdregidx(rs2)), Ameregidx(rd), Ameregidx(rs1), Ameregidx(rs2), AME_INT_SHIFT_LEFT)),
    AME_MSRA_EW => ame_retire_if(ame_ew_shift_m(MD(Mdregidx(rd)), MD(Mdregidx(rs1)), MD(Mdregidx(rs2)), Ameregidx(rd), Ameregidx(rs1), Ameregidx(rs2), AME_INT_SHIFT_RIGHT_ARITH)),
    AME_MSRL_EW => ame_retire_if(ame_ew_shift_m(MD(Mdregidx(rd)), MD(Mdregidx(rs1)), MD(Mdregidx(rs2)), Ameregidx(rd), Ameregidx(rs1), Ameregidx(rs2), AME_INT_SHIFT_RIGHT_LOGICAL)),
    AME_MXOR_EW => ame_retire_if(ame_ew_binary_m(MD(Mdregidx(rd)), MD(Mdregidx(rs1)), MD(Mdregidx(rs2)), Ameregidx(rd), Ameregidx(rs1), Ameregidx(rs2), AME_INT_XOR)),
  }
}

// *****************************************************************
// Bit: R3(md, xs, ms) instruction family
mapping encdec_bit_r3funct7_md_xs_ms : bit_r3funct7_md_xs_ms <-> bits(7) = {
  AME_MAND_EW_X <-> 0b0011011,
  AME_MANDNOT_EW_X <-> 0b0011101,
  AME_MOR_EW_X <-> 0b0011111,
  AME_MORNOT_EW_X <-> 0b0100001,
  AME_MSLL_EW_X <-> 0b0100011,
  AME_MSRA_EW_X <-> 0b0100101,
  AME_MSRL_EW_X <-> 0b0100111,
  AME_MXOR_EW_X <-> 0b0101001
}

mapping bit_r3funct7_md_xs_ms_mnemonic : bit_r3funct7_md_xs_ms <-> string = {
  AME_MAND_EW_X <-> "mand.ew.x",
  AME_MANDNOT_EW_X <-> "mandnot.ew.x",
  AME_MOR_EW_X <-> "mor.ew.x",
  AME_MORNOT_EW_X <-> "mornot.ew.x",
  AME_MSLL_EW_X <-> "msll.ew.x",
  AME_MSRA_EW_X <-> "msra.ew.x",
  AME_MSRL_EW_X <-> "msrl.ew.x",
  AME_MXOR_EW_X <-> "mxor.ew.x"
}

mapping bit_r3funct7_md_xs_ms_assembly : (bit_r3funct7_md_xs_ms, bits(5), bits(5), bits(5)) <-> string = {
  (AME_MAND_EW_X, rd, rs1, rs2) <-> bit_r3funct7_md_xs_ms_mnemonic(AME_MAND_EW_X) ^ spc() ^ amereg_name_raw(rd) ^ sep() ^ reg_name(encdec_reg(rs1)) ^ sep() ^ amereg_name_raw(rs2),
  (AME_MANDNOT_EW_X, rd, rs1, rs2) <-> bit_r3funct7_md_xs_ms_mnemonic(AME_MANDNOT_EW_X) ^ spc() ^ amereg_name_raw(rd) ^ sep() ^ reg_name(encdec_reg(rs1)) ^ sep() ^ amereg_name_raw(rs2),
  (AME_MOR_EW_X, rd, rs1, rs2) <-> bit_r3funct7_md_xs_ms_mnemonic(AME_MOR_EW_X) ^ spc() ^ amereg_name_raw(rd) ^ sep() ^ reg_name(encdec_reg(rs1)) ^ sep() ^ amereg_name_raw(rs2),
  (AME_MORNOT_EW_X, rd, rs1, rs2) <-> bit_r3funct7_md_xs_ms_mnemonic(AME_MORNOT_EW_X) ^ spc() ^ amereg_name_raw(rd) ^ sep() ^ reg_name(encdec_reg(rs1)) ^ sep() ^ amereg_name_raw(rs2),
  (AME_MSLL_EW_X, rd, rs1, rs2) <-> bit_r3funct7_md_xs_ms_mnemonic(AME_MSLL_EW_X) ^ spc() ^ amereg_name_raw(rd) ^ sep() ^ reg_name(encdec_reg(rs1)) ^ sep() ^ amereg_name_raw(rs2),
  (AME_MSRA_EW_X, rd, rs1, rs2) <-> bit_r3funct7_md_xs_ms_mnemonic(AME_MSRA_EW_X) ^ spc() ^ amereg_name_raw(rd) ^ sep() ^ reg_name(encdec_reg(rs1)) ^ sep() ^ amereg_name_raw(rs2),
  (AME_MSRL_EW_X, rd, rs1, rs2) <-> bit_r3funct7_md_xs_ms_mnemonic(AME_MSRL_EW_X) ^ spc() ^ amereg_name_raw(rd) ^ sep() ^ reg_name(encdec_reg(rs1)) ^ sep() ^ amereg_name_raw(rs2),
  (AME_MXOR_EW_X, rd, rs1, rs2) <-> bit_r3funct7_md_xs_ms_mnemonic(AME_MXOR_EW_X) ^ spc() ^ amereg_name_raw(rd) ^ sep() ^ reg_name(encdec_reg(rs1)) ^ sep() ^ amereg_name_raw(rs2),
}

union clause instruction = BIT_R3_MD_XS_MS_TYPE : (bit_r3funct7_md_xs_ms, bits(5), bits(5), bits(5))

mapping clause encdec = BIT_R3_MD_XS_MS_TYPE(op, rd, rs1, rs2)
  <-> encdec_bit_r3funct7_md_xs_ms(op) @ rs2 : bits(5) @ rs1 : bits(5) @ 0b000 @ rd : bits(5) @ 0b0101011
  when currentlyEnabled(Ext_Ztt)

mapping clause assembly = BIT_R3_MD_XS_MS_TYPE(op, rd, rs1, rs2)
  <-> bit_r3funct7_md_xs_ms_assembly(op, rd, rs1, rs2)

function clause execute BIT_R3_MD_XS_MS_TYPE(op, rd, rs1, rs2) = {
  if not(ame_context_owned()) |
     not(ame_check_mreg_operand(rd)) |
     not(ame_check_mreg_operand(rs2))
  then return Illegal_Instruction();

  match op {
    AME_MAND_EW_X => ame_retire_if(ame_ew_binary_x(MD(Mdregidx(rd)), MD(Mdregidx(rs2)), Ameregidx(rd), X(Regidx(trunc(rs1))), Ameregidx(rs2), AME_INT_AND)),
    AME_MANDNOT_EW_X => ame_retire_if(ame_ew_binary_x(MD(Mdregidx(rd)), MD(Mdregidx(rs2)), Ameregidx(rd), X(Regidx(trunc(rs1))), Ameregidx(rs2), AME_INT_ANDNOT)),
    AME_MOR_EW_X => ame_retire_if(ame_ew_binary_x(MD(Mdregidx(rd)), MD(Mdregidx(rs2)), Ameregidx(rd), X(Regidx(trunc(rs1))), Ameregidx(rs2), AME_INT_OR)),
    AME_MORNOT_EW_X => ame_retire_if(ame_ew_binary_x(MD(Mdregidx(rd)), MD(Mdregidx(rs2)), Ameregidx(rd), X(Regidx(trunc(rs1))), Ameregidx(rs2), AME_INT_ORNOT)),
    AME_MSLL_EW_X => ame_retire_if(ame_ew_shift_x(MD(Mdregidx(rd)), MD(Mdregidx(rs2)), Ameregidx(rd), X(Regidx(trunc(rs1))), Ameregidx(rs2), AME_INT_SHIFT_LEFT)),
    AME_MSRA_EW_X => ame_retire_if(ame_ew_shift_x(MD(Mdregidx(rd)), MD(Mdregidx(rs2)), Ameregidx(rd), X(Regidx(trunc(rs1))), Ameregidx(rs2), AME_INT_SHIFT_RIGHT_ARITH)),
    AME_MSRL_EW_X => ame_retire_if(ame_ew_shift_x(MD(Mdregidx(rd)), MD(Mdregidx(rs2)), Ameregidx(rd), X(Regidx(trunc(rs1))), Ameregidx(rs2), AME_INT_SHIFT_RIGHT_LOGICAL)),
    AME_MXOR_EW_X => ame_retire_if(ame_ew_binary_x(MD(Mdregidx(rd)), MD(Mdregidx(rs2)), Ameregidx(rd), X(Regidx(trunc(rs1))), Ameregidx(rs2), AME_INT_XOR)),
  }
}
