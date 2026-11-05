// Matrix Multiply instruction families.
// Encodings follow manual-main/instructions.json; the encoding, execute
// and mnemonic coverage of this file is checked by test/ztt/gen/check_manual_sync.py.

// *****************************************************************
// Mmul: R3(ad, ms, ms) instruction family
mapping encdec_mmul_r3funct7_ad_ms_ms : mmul_r3funct7_ad_ms_ms <-> bits(7) = {
  AME_MMULACC_2D <-> 0b1001010,
  AME_MMULACCNEG_2D <-> 0b1001011,
  AME_MMULATACC_2D <-> 0b1001101,
  AME_MMULATACCNEG_2D <-> 0b1001110,
  AME_MMULBTACC_2D <-> 0b1001111,
  AME_MMULBTACCNEG_2D <-> 0b1010000
}

mapping mmul_r3funct7_ad_ms_ms_mnemonic : mmul_r3funct7_ad_ms_ms <-> string = {
  AME_MMULACC_2D <-> "mmulacc.2d",
  AME_MMULACCNEG_2D <-> "mmulaccneg.2d",
  AME_MMULATACC_2D <-> "mmulatacc.2d",
  AME_MMULATACCNEG_2D <-> "mmulataccneg.2d",
  AME_MMULBTACC_2D <-> "mmulbtacc.2d",
  AME_MMULBTACCNEG_2D <-> "mmulbtaccneg.2d"
}

mapping mmul_r3funct7_ad_ms_ms_assembly : (mmul_r3funct7_ad_ms_ms, bits(5), bits(5), bits(5)) <-> string = {
  (AME_MMULACC_2D, rd, rs1, rs2) <-> mmul_r3funct7_ad_ms_ms_mnemonic(AME_MMULACC_2D) ^ spc() ^ ameaccreg_name_raw(rd) ^ sep() ^ amereg_name_raw(rs1) ^ sep() ^ amereg_name_raw(rs2),
  (AME_MMULACCNEG_2D, rd, rs1, rs2) <-> mmul_r3funct7_ad_ms_ms_mnemonic(AME_MMULACCNEG_2D) ^ spc() ^ ameaccreg_name_raw(rd) ^ sep() ^ amereg_name_raw(rs1) ^ sep() ^ amereg_name_raw(rs2),
  (AME_MMULATACC_2D, rd, rs1, rs2) <-> mmul_r3funct7_ad_ms_ms_mnemonic(AME_MMULATACC_2D) ^ spc() ^ ameaccreg_name_raw(rd) ^ sep() ^ amereg_name_raw(rs1) ^ sep() ^ amereg_name_raw(rs2),
  (AME_MMULATACCNEG_2D, rd, rs1, rs2) <-> mmul_r3funct7_ad_ms_ms_mnemonic(AME_MMULATACCNEG_2D) ^ spc() ^ ameaccreg_name_raw(rd) ^ sep() ^ amereg_name_raw(rs1) ^ sep() ^ amereg_name_raw(rs2),
  (AME_MMULBTACC_2D, rd, rs1, rs2) <-> mmul_r3funct7_ad_ms_ms_mnemonic(AME_MMULBTACC_2D) ^ spc() ^ ameaccreg_name_raw(rd) ^ sep() ^ amereg_name_raw(rs1) ^ sep() ^ amereg_name_raw(rs2),
  (AME_MMULBTACCNEG_2D, rd, rs1, rs2) <-> mmul_r3funct7_ad_ms_ms_mnemonic(AME_MMULBTACCNEG_2D) ^ spc() ^ ameaccreg_name_raw(rd) ^ sep() ^ amereg_name_raw(rs1) ^ sep() ^ amereg_name_raw(rs2),
}

union clause instruction = MMUL_R3_AD_MS_MS_TYPE : (mmul_r3funct7_ad_ms_ms, bits(5), bits(5), bits(5))

mapping clause encdec = MMUL_R3_AD_MS_MS_TYPE(op, rd, rs1, rs2)
  <-> encdec_mmul_r3funct7_ad_ms_ms(op) @ rs2 : bits(5) @ rs1 : bits(5) @ 0b000 @ rd : bits(5) @ 0b0101011
  when currentlyEnabled(Ext_Ztt)

mapping clause assembly = MMUL_R3_AD_MS_MS_TYPE(op, rd, rs1, rs2)
  <-> mmul_r3funct7_ad_ms_ms_assembly(op, rd, rs1, rs2)

function clause execute MMUL_R3_AD_MS_MS_TYPE(op, rd, rs1, rs2) = {
  if not(ame_context_owned()) |
     not(ame_check_acc_reg_operand(rd)) |
     not(ame_check_mreg_operand(rs1)) |
     not(ame_check_mreg_operand(rs2))
  then return Illegal_Instruction();

  match op {
    AME_MMULACC_2D => {
      let md_dtype : bits(32) = AD(Ameadregidx(rd));
      let ms1_dtype : bits(32) = MD(Mdregidx(rs1));
      let ms2_dtype : bits(32) = MD(Mdregidx(rs2));
      ame_retire_if(ame_mmulacc_2d(md_dtype, ms1_dtype, ms2_dtype, Ameaccregidx(rd), Ameregidx(rs1), Ameregidx(rs2)))
    },
    AME_MMULACCNEG_2D => {
      let md_dtype : bits(32) = AD(Ameadregidx(rd));
      let ms1_dtype : bits(32) = MD(Mdregidx(rs1));
      let ms2_dtype : bits(32) = MD(Mdregidx(rs2));
      ame_retire_if(ame_mmul_2d(md_dtype, ms1_dtype, ms2_dtype, Ameaccregidx(rd), Ameregidx(rs1), Ameregidx(rs2), true, true, false, false))
    },
    AME_MMULATACC_2D => {
      let md_dtype : bits(32) = AD(Ameadregidx(rd));
      let ms1_dtype : bits(32) = MD(Mdregidx(rs1));
      let ms2_dtype : bits(32) = MD(Mdregidx(rs2));
      ame_retire_if(ame_mmul_2d(md_dtype, ms1_dtype, ms2_dtype, Ameaccregidx(rd), Ameregidx(rs1), Ameregidx(rs2), true, false, true, false))
    },
    AME_MMULATACCNEG_2D => {
      let md_dtype : bits(32) = AD(Ameadregidx(rd));
      let ms1_dtype : bits(32) = MD(Mdregidx(rs1));
      let ms2_dtype : bits(32) = MD(Mdregidx(rs2));
      ame_retire_if(ame_mmul_2d(md_dtype, ms1_dtype, ms2_dtype, Ameaccregidx(rd), Ameregidx(rs1), Ameregidx(rs2), true, true, true, false))
    },
    AME_MMULBTACC_2D => {
      let md_dtype : bits(32) = AD(Ameadregidx(rd));
      let ms1_dtype : bits(32) = MD(Mdregidx(rs1));
      let ms2_dtype : bits(32) = MD(Mdregidx(rs2));
      ame_retire_if(ame_mmul_2d(md_dtype, ms1_dtype, ms2_dtype, Ameaccregidx(rd), Ameregidx(rs1), Ameregidx(rs2), true, false, false, true))
    },
    AME_MMULBTACCNEG_2D => {
      let md_dtype : bits(32) = AD(Ameadregidx(rd));
      let ms1_dtype : bits(32) = MD(Mdregidx(rs1));
      let ms2_dtype : bits(32) = MD(Mdregidx(rs2));
      ame_retire_if(ame_mmul_2d(md_dtype, ms1_dtype, ms2_dtype, Ameaccregidx(rd), Ameregidx(rs1), Ameregidx(rs2), true, true, false, true))
    },
  }
}
