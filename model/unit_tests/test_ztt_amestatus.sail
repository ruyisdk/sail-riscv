// Verify the AME unsupported-operation status contract from the current manual.
$[test]
function test_ztt_amestatus_un_w1c() -> unit = {
  let zero : xlenbits = zeros();
  let one : xlenbits = zero_extend(0b1);

  ame_test_enable_context();
  amestatus = 0b0;
  assert(read_CSR(0x800) == zero);

  ame_set_unsupported();
  assert(read_CSR(0x800) == one);

  match write_CSR(0x800, one) {
    Ok(value) => assert(value == one),
    Err(_) => assert(false),
  };
  assert(read_CSR(0x800) == one);

  match write_CSR(0x800, zero) {
    Ok(value) => assert(value == zero),
    Err(_) => assert(false),
  };
  assert(read_CSR(0x800) == zero);
}

$[test]
function test_ztt_current_csr_layout() -> unit = {
  let zero : xlenbits = zeros();
  let one : xlenbits = zero_extend(0b1);
  let scalar_dtype : xlenbits = zero_extend(0x40000020);
  let fflags : xlenbits = zero_extend(0b10101);

  ame_release_backend();
  ame_test_enable_context();
  amestype = zeros();
  amestatus = 0b0;
  amefflags = zeros();
  amexsat = 0b0;
  assert(read_CSR(0xCC0) == amenlen[xlen - 1 .. 0]);
  assert(read_CSR(0xCC1) == ameudsz[xlen - 1 .. 0]);
  assert(read_CSR(0x810) == zero);
  assert(read_CSR(0xCC3) == one);
  assert(read_CSR(0x811) == zero);
  assert(read_CSR(0x812) == zero);
  assert(check_CSR(0x810, Machine, CSRWrite));
  assert(check_CSR(0x811, Machine, CSRReadWrite));
  assert(check_CSR(0x812, Machine, CSRWrite));
  assert(not(check_CSR(0xCC0, Machine, CSRWrite)));

  match write_CSR(0x810, scalar_dtype) {
    Ok(value) => assert(value == scalar_dtype),
    Err(_) => assert(false),
  };
  match write_CSR(0x811, fflags) {
    Ok(value) => assert(value == fflags),
    Err(_) => assert(false),
  };
  match write_CSR(0x812, zero) {
    Ok(value) => assert(value == zero),
    Err(_) => assert(false),
  };
}

// Ztt must not claim the standard Zicntr time and instret CSR addresses.
$[test]
function test_ztt_zicntr_csr_integration() -> unit = {
  let expected_instret : bits(64) = 0xfedcba9876543210;

  assert(currentlyEnabled(Ext_Zicntr));
  assert(hartSupports(Ext_Ztt));
  assert(check_CSR(0xC01, Machine, CSRRead));
  assert(check_CSR(0xC02, Machine, CSRRead));

  // Keep the AME implementation-defined values distinct from their former
  // aliases so an overlapping read_CSR clause cannot make this test pass.
  amenlen = 0xffffffffffffffff;
  ameudsz = 0x0000000000000000;
  minstret = expected_instret;
  // `mtime` is platform-private; read it through the public accessor and
  // mirror the Zicntr clause so the comparison still detects an overlapping
  // AME clause at 0xC01.
  let expected_time : bits(64) = get_mtime() +
    (if inVirtualPrivilege() then htimedelta else zeros());
  assert(read_CSR(0xC01) == expected_time[xlen - 1 .. 0]);
  assert(read_CSR(0xC02) == expected_instret[xlen - 1 .. 0]);
}
