// Test-only constructors for the compact Ztt instruction families.
// Production decode uses operand-role-specific family constructors directly.

function TEST_AME_MZERO_2D_ACC(acc : bits(5)) -> instruction =
  AME_MZERO_2D_ACC(acc)

function TEST_AME_MZERO_2D_M(md : bits(5)) -> instruction =
  STATE_R1_MD_TYPE(AME_MZERO_2D_M, md)

function TEST_AME_MCOLID_EW(md : bits(5)) -> instruction =
  STATE_R1_MD_TYPE(AME_MCOLID_EW, md)

function TEST_AME_MROWID_EW(md : bits(5)) -> instruction =
  STATE_R1_MD_TYPE(AME_MROWID_EW, md)

function TEST_AME_AGETTYP(rd : bits(5), ad : bits(5)) -> instruction =
  AME_AGETTYP(rd, ad)

function TEST_AME_ASETTYP(ad : bits(5), rs1 : bits(5)) -> instruction =
  AME_ASETTYP(ad, rs1)

function TEST_AME_MGETTYP(rd : bits(5), ms1 : bits(5)) -> instruction =
  AME_MGETTYP(rd, ms1)

function TEST_AME_MSETTYP(md : bits(5), rs1 : bits(5)) -> instruction =
  AME_MSETTYP(md, rs1)

function TEST_AME_MABS_EW(md : bits(5), ms1 : bits(5)) -> instruction =
  AME_MABS_EW(md, ms1)

function TEST_AME_MCONV_EW(md : bits(5), ms1 : bits(5)) -> instruction =
  AME_MCONV_EW(md, ms1)

function TEST_AME_MEXP2_EW(md : bits(5), ms1 : bits(5)) -> instruction =
  FP_FR2_MD_MS_TYPE(AME_MEXP2_EW, md, ms1)

function TEST_AME_MLOG2_EW(md : bits(5), ms1 : bits(5)) -> instruction =
  FP_FR2_MD_MS_TYPE(AME_MLOG2_EW, md, ms1)

function TEST_AME_MSS_RM(ms1 : bits(5), rs1 : bits(5)) -> instruction =
  MEM_R2_MS_XS_TYPE(AME_MSS_RM, ms1, rs1)

function TEST_AME_MMOV_M_A(md : bits(5), acc : bits(5)) -> instruction =
  AME_MMOV_M_A(md, acc)

function TEST_AME_MMOV_A_M(acc : bits(5), ms : bits(5)) -> instruction =
  AME_MMOV_A_M(acc, ms)

function TEST_AME_MMOV_M_M(md : bits(5), ms : bits(5)) -> instruction =
  AME_MMOV_M_M(md, ms)

function TEST_AME_MADD_EW(md : bits(5), ms1 : bits(5), ms2 : bits(5)) -> instruction =
  ARITH_R3_MD_MS_MS_TYPE(AME_MADD_EW, md, ms1, ms2)

function TEST_AME_MADD_EW_X(md : bits(5), rs1 : bits(5), ms2 : bits(5)) -> instruction =
  ARITH_R3_MD_XS_MS_TYPE(AME_MADD_EW_X, md, rs1, ms2)

function TEST_AME_MAND_EW(md : bits(5), ms1 : bits(5), ms2 : bits(5)) -> instruction =
  BIT_R3_MD_MS_MS_TYPE(AME_MAND_EW, md, ms1, ms2)

function TEST_AME_MAND_EW_X(md : bits(5), rs1 : bits(5), ms2 : bits(5)) -> instruction =
  BIT_R3_MD_XS_MS_TYPE(AME_MAND_EW_X, md, rs1, ms2)

function TEST_AME_MCMPGE_EW(md : bits(5), ms1 : bits(5), ms2 : bits(5)) -> instruction =
  CMP_R3_MD_MS_MS_TYPE(AME_MCMPGE_EW, md, ms1, ms2)

function TEST_AME_MMIN_EW(md : bits(5), ms1 : bits(5), ms2 : bits(5)) -> instruction =
  ARITH_R3_MD_MS_MS_TYPE(AME_MMIN_EW, md, ms1, ms2)

function TEST_AME_MHDIFF_EW(md : bits(5), ms1 : bits(5), ms2 : bits(5)) -> instruction =
  ARITH_R3_MD_MS_MS_TYPE(AME_MHDIFF_EW, md, ms1, ms2)

function TEST_AME_MMEAN_EW(md : bits(5), ms1 : bits(5), ms2 : bits(5)) -> instruction =
  ARITH_R3_MD_MS_MS_TYPE(AME_MMEAN_EW, md, ms1, ms2)

function TEST_AME_MLDEXP_EW(md : bits(5), ms1 : bits(5), ms2 : bits(5)) -> instruction =
  MATH_R3_MD_MS_MS_TYPE(AME_MLDEXP_EW, md, ms1, ms2)

function TEST_AME_MMULACC_2D(acc : bits(5), ms1 : bits(5), ms2 : bits(5)) -> instruction =
  MMUL_R3_AD_MS_MS_TYPE(AME_MMULACC_2D, acc, ms1, ms2)

function TEST_AME_MMULACC_EW(md : bits(5), ms1 : bits(5), ms2 : bits(5)) -> instruction =
  ARITH_R3_MD_MS_MS_TYPE(AME_MMULACC_EW, md, ms1, ms2)

function TEST_AME_MMULACC_EW_X(md : bits(5), rs1 : bits(5), ms2 : bits(5)) -> instruction =
  ARITH_R3_MD_XS_MS_TYPE(AME_MMULACC_EW_X, md, rs1, ms2)

function TEST_AME_MCOLGATHER_EW(md : bits(5), ms1 : bits(5), ms2 : bits(5)) -> instruction =
  PERM_R3_MD_MS_MS_TYPE(AME_MCOLGATHER_EW, md, ms1, ms2)

function TEST_AME_MCOLSCATADD_EW(md : bits(5), ms1 : bits(5), ms2 : bits(5)) -> instruction =
  PERM_R3_MD_MS_MS_TYPE(AME_MCOLSCATADD_EW, md, ms1, ms2)

function TEST_AME_MSLL_EW(md : bits(5), ms1 : bits(5), ms2 : bits(5)) -> instruction =
  BIT_R3_MD_MS_MS_TYPE(AME_MSLL_EW, md, ms1, ms2)

function TEST_AME_MSLL_EW_X(md : bits(5), rs1 : bits(5), ms2 : bits(5)) -> instruction =
  BIT_R3_MD_XS_MS_TYPE(AME_MSLL_EW_X, md, rs1, ms2)

function TEST_AME_MSELGE_EW(md : bits(5), ms1 : bits(5), ms2 : bits(5)) -> instruction =
  CMP_R3_MD_MS_MS_TYPE(AME_MSELGE_EW, md, ms1, ms2)

function TEST_AME_MSELLT_EW(md : bits(5), ms1 : bits(5), ms2 : bits(5)) -> instruction =
  CMP_R3_MD_MS_MS_TYPE(AME_MSELLT_EW, md, ms1, ms2)

function TEST_AME_MCMOVGE_EW(md : bits(5), ms1 : bits(5), ms2 : bits(5)) -> instruction =
  CMP_R3_MD_MS_MS_TYPE(AME_MCMOVGE_EW, md, ms1, ms2)

function TEST_AME_MCMOVLT_EW(md : bits(5), ms1 : bits(5), ms2 : bits(5)) -> instruction =
  CMP_R3_MD_MS_MS_TYPE(AME_MCMOVLT_EW, md, ms1, ms2)
