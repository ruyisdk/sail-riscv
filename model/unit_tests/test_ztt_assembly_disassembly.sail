// Verify Ztt encoding and canonical disassembly without executing instructions.

function test_ztt_assembly_disassembly_case(expected_encoding : bits(32),
                                             expected_assembly : string) -> unit = {
  // Decode, disassemble, and re-encode without entering an execute clause.
  let decoded : instruction = encdec(expected_encoding);
  let actual_assembly : string = assembly(decoded);
  assert(actual_assembly == expected_assembly,
         "unexpected Ztt disassembly: expected " ^ expected_assembly ^ ", got " ^ actual_assembly);
  assert(encdec(decoded) == expected_encoding,
         "Ztt re-encoding mismatch: " ^ expected_assembly);
}

$[test]
function test_ztt_assembly_disassembly() -> unit = {
  // One non-zero operand instance for every v0.6 instruction encoding.
  test_ztt_assembly_disassembly_case(0xa49686ab, "ame.acquire x13, x13");
  test_ztt_assembly_disassembly_case(0xa4a0002b, "ame.release");
  test_ztt_assembly_disassembly_case(0xa20106ab, "agettyp x13, acc2");
  test_ztt_assembly_disassembly_case(0xa216812b, "asettyp acc2, x13");
  test_ztt_assembly_disassembly_case(0xa24888ab, "mabs.ew m17, m17");
  test_ztt_assembly_disassembly_case(0x01d888ab, "mabsdiff.ew m17, m17, m29");
  test_ztt_assembly_disassembly_case(0x03d688ab, "mabsdiff.ew.x m17, x13, m29");
  test_ztt_assembly_disassembly_case(0x05d888ab, "madd.ew m17, m17, m29");
  test_ztt_assembly_disassembly_case(0x07d688ab, "madd.ew.x m17, x13, m29");
  test_ztt_assembly_disassembly_case(0x35d888ab, "mand.ew m17, m17, m29");
  test_ztt_assembly_disassembly_case(0x37d688ab, "mand.ew.x m17, x13, m29");
  test_ztt_assembly_disassembly_case(0x39d888ab, "mandnot.ew m17, m17, m29");
  test_ztt_assembly_disassembly_case(0x3bd688ab, "mandnot.ew.x m17, x13, m29");
  test_ztt_assembly_disassembly_case(0x55d888ab, "mcmovge.ew m17, m17, m29");
  test_ztt_assembly_disassembly_case(0x57d888ab, "mcmovlt.ew m17, m17, m29");
  test_ztt_assembly_disassembly_case(0x59d888ab, "mcmpge.ew m17, m17, m29");
  test_ztt_assembly_disassembly_case(0x5bd688ab, "mcmpge.ew.x m17, x13, m29");
  test_ztt_assembly_disassembly_case(0x5dd888ab, "mcmplt.ew m17, m17, m29");
  test_ztt_assembly_disassembly_case(0x5fd688ab, "mcmplt.ew.x m17, x13, m29");
  test_ztt_assembly_disassembly_case(0x65d688ab, "mcolbcast.ew.x m17, x13, m29");
  test_ztt_assembly_disassembly_case(0x67d888ab, "mcolgather.ew m17, m17, m29");
  test_ztt_assembly_disassembly_case(0xa60108ab, "mcolid.ew m17");
  test_ztt_assembly_disassembly_case(0x69d688ab, "mcolshift.ew.x m17, x13, m29");
  test_ztt_assembly_disassembly_case(0xc3d8802b, "mcolunzip.ew m17, m29");
  test_ztt_assembly_disassembly_case(0xc5d8802b, "mcolzip.ew m17, m29");
  test_ztt_assembly_disassembly_case(0xa2d888ab, "mconv.ew m17, m17");
  test_ztt_assembly_disassembly_case(0xb1d688ab, "mbcast.m.x m17, x13, x29");
  test_ztt_assembly_disassembly_case(0xa2e888ab, "mcos.ew m17, m17");
  test_ztt_assembly_disassembly_case(0xa2f888ab, "mexp2.ew m17, m17");
  test_ztt_assembly_disassembly_case(0xa25888ab, "mfrintm.ew m17, m17");
  test_ztt_assembly_disassembly_case(0xa26888ab, "mfrintn.ew m17, m17");
  test_ztt_assembly_disassembly_case(0xa27888ab, "mfrintp.ew m17, m17");
  test_ztt_assembly_disassembly_case(0xa28888ab, "mfrintz.ew m17, m17");
  test_ztt_assembly_disassembly_case(0xa22886ab, "mgettyp x13, m17");
  test_ztt_assembly_disassembly_case(0x09d888ab, "mhdiff.ew m17, m17, m29");
  test_ztt_assembly_disassembly_case(0x0bd688ab, "mhdiff.ew.x m17, x13, m29");
  test_ztt_assembly_disassembly_case(0x7fd888ab, "mldexp.ew m17, m17, m29");
  test_ztt_assembly_disassembly_case(0x81d688ab, "mldexp.ew.x m17, x13, m29");
  test_ztt_assembly_disassembly_case(0x83d888ab, "mldexpacc.ew m17, m17, m29");
  test_ztt_assembly_disassembly_case(0x85d688ab, "mldexpacc.ew.x m17, x13, m29");
  test_ztt_assembly_disassembly_case(0xa30888ab, "mlog2.ew m17, m17");
  test_ztt_assembly_disassembly_case(0x87d888ab, "mlog2sub.ew m17, m17, m29");
  test_ztt_assembly_disassembly_case(0x89d688ab, "mlog2sub.ew.x m17, x13, m29");
  test_ztt_assembly_disassembly_case(0xa36688ab, "mls.1r m17, x13");
  test_ztt_assembly_disassembly_case(0xa37688ab, "mls.cm m17, x13");
  test_ztt_assembly_disassembly_case(0xa38688ab, "mls.rm m17, x13");
  test_ztt_assembly_disassembly_case(0xa9d688ab, "mls.st m17, x13, x29");
  test_ztt_assembly_disassembly_case(0xabd688ab, "mls.tst m17, x13, x29");
  test_ztt_assembly_disassembly_case(0x0dd888ab, "mmax.ew m17, m17, m29");
  test_ztt_assembly_disassembly_case(0x0fd688ab, "mmax.ew.x m17, x13, m29");
  test_ztt_assembly_disassembly_case(0x11d888ab, "mmean.ew m17, m17, m29");
  test_ztt_assembly_disassembly_case(0x13d688ab, "mmean.ew.x m17, x13, m29");
  test_ztt_assembly_disassembly_case(0x15d888ab, "mmin.ew m17, m17, m29");
  test_ztt_assembly_disassembly_case(0x17d688ab, "mmin.ew.x m17, x13, m29");
  test_ztt_assembly_disassembly_case(0xa3c108ab, "mmov.m.a m17, acc2");
  test_ztt_assembly_disassembly_case(0xa3d8812b, "mmov.a.m acc2, m17");
  test_ztt_assembly_disassembly_case(0xa3e888ab, "mmov.m.m m17, m17");
  test_ztt_assembly_disassembly_case(0xb2de88ab, "mmove8.m.x m17, x29, x13");
  test_ztt_assembly_disassembly_case(0xb4de88ab, "mmove16.m.x m17, x29, x13");
  test_ztt_assembly_disassembly_case(0xb6de88ab, "mmove32.m.x m17, x29, x13");
  test_ztt_assembly_disassembly_case(0xb8de88ab, "mmove64.m.x m17, x29, x13");
  test_ztt_assembly_disassembly_case(0xbade86ab, "mmove8.x.m x13, m29, x13");
  test_ztt_assembly_disassembly_case(0xbcde86ab, "mmove16.x.m x13, m29, x13");
  test_ztt_assembly_disassembly_case(0xbede86ab, "mmove32.x.m x13, m29, x13");
  test_ztt_assembly_disassembly_case(0xc0de86ab, "mmove64.x.m x13, m29, x13");
  test_ztt_assembly_disassembly_case(0x19d888ab, "mmul.ew m17, m17, m29");
  test_ztt_assembly_disassembly_case(0x1bd688ab, "mmul.ew.x m17, x13, m29");
  test_ztt_assembly_disassembly_case(0x95d8812b, "mmulacc.2d acc2, m17, m29");
  test_ztt_assembly_disassembly_case(0x1dd888ab, "mmulacc.ew m17, m17, m29");
  test_ztt_assembly_disassembly_case(0x1fd688ab, "mmulacc.ew.x m17, x13, m29");
  test_ztt_assembly_disassembly_case(0x97d8812b, "mmulaccneg.2d acc2, m17, m29");
  test_ztt_assembly_disassembly_case(0x21d888ab, "mmulaccneg.ew m17, m17, m29");
  test_ztt_assembly_disassembly_case(0x23d688ab, "mmulaccneg.ew.x m17, x13, m29");
  test_ztt_assembly_disassembly_case(0x25d888ab, "mmuladd.ew m17, m17, m29");
  test_ztt_assembly_disassembly_case(0x27d688ab, "mmuladd.ew.x m17, x13, m29");
  test_ztt_assembly_disassembly_case(0x9bd8812b, "mmulatacc.2d acc2, m17, m29");
  test_ztt_assembly_disassembly_case(0x9dd8812b, "mmulataccneg.2d acc2, m17, m29");
  test_ztt_assembly_disassembly_case(0x9fd8812b, "mmulbtacc.2d acc2, m17, m29");
  test_ztt_assembly_disassembly_case(0xa1d8812b, "mmulbtaccneg.2d acc2, m17, m29");
  test_ztt_assembly_disassembly_case(0x29d888ab, "mmulneg.ew m17, m17, m29");
  test_ztt_assembly_disassembly_case(0x2bd688ab, "mmulneg.ew.x m17, x13, m29");
  test_ztt_assembly_disassembly_case(0x2dd888ab, "mmulsub.ew m17, m17, m29");
  test_ztt_assembly_disassembly_case(0x2fd688ab, "mmulsub.ew.x m17, x13, m29");
  test_ztt_assembly_disassembly_case(0x3dd888ab, "mor.ew m17, m17, m29");
  test_ztt_assembly_disassembly_case(0x3fd688ab, "mor.ew.x m17, x13, m29");
  test_ztt_assembly_disassembly_case(0x41d888ab, "mornot.ew m17, m17, m29");
  test_ztt_assembly_disassembly_case(0x43d688ab, "mornot.ew.x m17, x13, m29");
  test_ztt_assembly_disassembly_case(0x7bd688ab, "mpack.ew.x m17, x13, m29");
  test_ztt_assembly_disassembly_case(0xa3f888ab, "mprefixadd.col m17, m17");
  test_ztt_assembly_disassembly_case(0xa40888ab, "mprefixadd.row m17, m17");
  test_ztt_assembly_disassembly_case(0xa41888ab, "mprefixmax.col m17, m17");
  test_ztt_assembly_disassembly_case(0xa42888ab, "mprefixmax.row m17, m17");
  test_ztt_assembly_disassembly_case(0x8bd888ab, "mrdexp.ew m17, m17, m29");
  test_ztt_assembly_disassembly_case(0x8dd888ab, "mrdexpacc.ew m17, m17, m29");
  test_ztt_assembly_disassembly_case(0xa31888ab, "mrec.ew m17, m17");
  test_ztt_assembly_disassembly_case(0xa43888ab, "mreduceadd.col m17, m17");
  test_ztt_assembly_disassembly_case(0xa44888ab, "mreduceadd.row m17, m17");
  test_ztt_assembly_disassembly_case(0xa45888ab, "mreducemax.col m17, m17");
  test_ztt_assembly_disassembly_case(0xa46888ab, "mreducemax.row m17, m17");
  test_ztt_assembly_disassembly_case(0xa47888ab, "mreducemin.col m17, m17");
  test_ztt_assembly_disassembly_case(0xa48888ab, "mreducemin.row m17, m17");
  test_ztt_assembly_disassembly_case(0x6bd688ab, "mrowbcast.ew.x m17, x13, m29");
  test_ztt_assembly_disassembly_case(0x6dd888ab, "mrowgather.ew m17, m17, m29");
  test_ztt_assembly_disassembly_case(0xa60188ab, "mrowid.ew m17");
  test_ztt_assembly_disassembly_case(0x6fd688ab, "mrowshift.ew.x m17, x13, m29");
  test_ztt_assembly_disassembly_case(0xc7d8802b, "mrowunzip.ew m17, m29");
  test_ztt_assembly_disassembly_case(0x71d8802b, "mrowzip.ew m17, m29");
  test_ztt_assembly_disassembly_case(0xa32888ab, "mrsqrt.ew m17, m17");
  test_ztt_assembly_disassembly_case(0x73d888ab, "mrowscatadd.ew m17, m17, m29");
  test_ztt_assembly_disassembly_case(0x75d888ab, "mcolscatadd.ew m17, m17, m29");
  test_ztt_assembly_disassembly_case(0x77d888ab, "mrowscatmax.ew m17, m17, m29");
  test_ztt_assembly_disassembly_case(0x79d888ab, "mcolscatmax.ew m17, m17, m29");
  test_ztt_assembly_disassembly_case(0x61d888ab, "mselge.ew m17, m17, m29");
  test_ztt_assembly_disassembly_case(0x63d888ab, "msellt.ew m17, m17, m29");
  test_ztt_assembly_disassembly_case(0xa23688ab, "msettyp m17, x13");
  test_ztt_assembly_disassembly_case(0xa33888ab, "msin.ew m17, m17");
  test_ztt_assembly_disassembly_case(0x45d888ab, "msll.ew m17, m17, m29");
  test_ztt_assembly_disassembly_case(0x47d688ab, "msll.ew.x m17, x13, m29");
  test_ztt_assembly_disassembly_case(0xa34888ab, "msqrt.ew m17, m17");
  test_ztt_assembly_disassembly_case(0x49d888ab, "msra.ew m17, m17, m29");
  test_ztt_assembly_disassembly_case(0x4bd688ab, "msra.ew.x m17, x13, m29");
  test_ztt_assembly_disassembly_case(0x4dd888ab, "msrl.ew m17, m17, m29");
  test_ztt_assembly_disassembly_case(0x4fd688ab, "msrl.ew.x m17, x13, m29");
  test_ztt_assembly_disassembly_case(0xa39688ab, "mss.1r m17, x13");
  test_ztt_assembly_disassembly_case(0xa3a688ab, "mss.cm m17, x13");
  test_ztt_assembly_disassembly_case(0xa3b688ab, "mss.rm m17, x13");
  test_ztt_assembly_disassembly_case(0xadd688ab, "mss.st m17, x13, x29");
  test_ztt_assembly_disassembly_case(0xafd688ab, "mss.tst m17, x13, x29");
  test_ztt_assembly_disassembly_case(0x31d888ab, "msub.ew m17, m17, m29");
  test_ztt_assembly_disassembly_case(0x33d688ab, "msub.ew.x m17, x13, m29");
  test_ztt_assembly_disassembly_case(0x8fd888ab, "msublog2.ew m17, m17, m29");
  test_ztt_assembly_disassembly_case(0x91d688ab, "msublog2.ew.x m17, x13, m29");
  test_ztt_assembly_disassembly_case(0xa35888ab, "mtanh.ew m17, m17");
  test_ztt_assembly_disassembly_case(0x7dd688ab, "munpack.ew.x m17, x13, m29");
  test_ztt_assembly_disassembly_case(0x51d888ab, "mxor.ew m17, m17, m29");
  test_ztt_assembly_disassembly_case(0x53d688ab, "mxor.ew.x m17, x13, m29");
  test_ztt_assembly_disassembly_case(0xa600012b, "mzero.2d.acc acc2");
  test_ztt_assembly_disassembly_case(0xa60088ab, "mzero.2d.m m17");

  // The Acc/Ad operand is a complete five-bit field in v0.6.  These operands
  // exercise both source field positions and the high bits of the encoding.
  test_ztt_assembly_disassembly_case(0xa20406ab, "agettyp x13, acc8");
  test_ztt_assembly_disassembly_case(0xa21687ab, "asettyp acc15, x13");
  test_ztt_assembly_disassembly_case(0xa3c788ab, "mmov.m.a m17, acc15");
  test_ztt_assembly_disassembly_case(0xa3d887ab, "mmov.a.m acc15, m17");
  test_ztt_assembly_disassembly_case(0x95d887ab, "mmulacc.2d acc15, m17, m29");
  test_ztt_assembly_disassembly_case(0xa60007ab, "mzero.2d.acc acc15");

  // acc16 is decodable but exceeds the maximum v0.6 implementation count.
  // Execution tests below cover rejection by a smaller implementation.
  test_ztt_assembly_disassembly_case(0xa600082b, "mzero.2d.acc acc16");
}
