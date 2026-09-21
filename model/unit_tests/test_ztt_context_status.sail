// Verify the architectural Ztt context-state transitions independently of
// instruction execution.  MS is exposed through both mstatus and sstatus.

function ztt_write_mstatus_ms(status : ext_status) -> unit = {
  let value = [read_CSR(0x300) with 26 .. 25 = status];
  match write_CSR(0x300, value) {
    Ok(_) => (),
    Err(_) => assert(false),
  }
}

function ztt_write_sstatus_ms(status : ext_status) -> unit = {
  let value = [read_CSR(0x100) with 26 .. 25 = status];
  match write_CSR(0x100, value) {
    Ok(_) => (),
    Err(_) => assert(false),
  }
}

$[test]
function test_ztt_ms_context_status() -> unit = {
  let off : ext_status = extStatus_map(Off);
  let initial : ext_status = extStatus_map(Initial);
  let clean : ext_status = extStatus_map(Clean);
  let dirty : ext_status = extStatus_map(Dirty);
  let descriptor : xlenbits = zeros();
  let granted : xlenbits = zero_extend(0b1);
  let scalar_dtype : xlenbits = zero_extend(0x40000020);

  // Establish a state that is independent of the order in which unit tests run.
  mstatus = [mstatus with
    FS = off,
    XS = off,
    VS = off,
    MS = off,
    SD = 0b0,
  ];
  ameown = 0b0;

  assert(not(ame_context_enabled()));
  assert(not(check_CSR(0xCC0, Machine, CSRRead)));
  assert(not(check_CSR(0x810, Machine, CSRRead)));

  // Initial enables AME and is reflected in sstatus.  Capability CSRs are
  // readable, but context-local state remains inaccessible until ownership.
  ztt_write_mstatus_ms(initial);
  assert(mstatus[MS] == initial);
  assert(read_CSR(0x100)[26 .. 25] == initial);
  assert(ame_context_enabled());
  assert(check_CSR(0xCC0, Machine, CSRRead));
  assert(not(check_CSR(0xCC0, Machine, CSRWrite)));
  assert(not(check_CSR(0x810, Machine, CSRRead)));

  ameown = 0b1;
  assert(check_CSR(0x810, Machine, CSRRead));
  assert(check_CSR(0x810, Machine, CSRWrite));

  // An owning context must release AME before disabling MS through either
  // architectural status CSR.  Both rejected writes leave the shared state
  // unchanged.
  let mstatus_before = mstatus;
  let sstatus_before = read_CSR(0x100);
  match write_CSR(0x300, [read_CSR(0x300) with 26 .. 25 = off]) {
    Ok(_) => assert(false),
    Err(()) => (),
  };
  assert(mstatus == mstatus_before);
  match write_CSR(0x100, [sstatus_before with 26 .. 25 = off]) {
    Ok(_) => assert(false),
    Err(()) => (),
  };
  assert(mstatus == mstatus_before);

  // A context CSR modification makes MS Dirty and therefore sets SD.
  match write_CSR(0x810, scalar_dtype) {
    Ok(value) => assert(value == scalar_dtype),
    Err(_) => assert(false),
  };
  assert(mstatus[MS] == dirty);
  assert(read_CSR(0x100)[26 .. 25] == dirty);
  assert(mstatus[SD] == 0b1);

  // An sstatus write updates the shared MS state and recomputes SD.
  ztt_write_sstatus_ms(clean);
  assert(mstatus[MS] == clean);
  assert(read_CSR(0x100)[26 .. 25] == clean);
  assert(mstatus[SD] == 0b0);

  ame_mark_context_dirty();
  assert(mstatus[MS] == dirty);
  assert(read_CSR(0x100)[26 .. 25] == dirty);
  assert(mstatus[SD] == 0b1);

  ztt_write_mstatus_ms(clean);
  assert(mstatus[MS] == clean);
  assert(mstatus[SD] == 0b0);

  // Every architectural AME state bank uses a common commit hook.  Exercise
  // each bank from Clean to ensure no individual instruction family can skip
  // the required Initial/Clean-to-Dirty transition.
  M(Ameregidx(0b00000)) = zeros();
  assert(mstatus[MS] == dirty);
  assert(mstatus[SD] == 0b1);

  ztt_write_mstatus_ms(clean);
  assert(ame_context_enabled());
  assert(ameown == 0b1);
  ame_mark_context_dirty();
  assert(mstatus[MS] == dirty);
  ztt_write_mstatus_ms(clean);
  MD(Mdregidx(0b00000)) = zeros();
  assert(mstatus[MS] == dirty);

  ztt_write_mstatus_ms(clean);
  ACC(Ameaccregidx(0b00000)) = zeros();
  assert(mstatus[MS] == dirty);

  ztt_write_mstatus_ms(clean);
  AD(Ameadregidx(0b00000)) = zeros();
  assert(mstatus[MS] == dirty);

  // AME status flags are architectural context state as well.
  ztt_write_mstatus_ms(clean);
  amefflags = zeros();
  accrue_amefflags(0b00001);
  assert(mstatus[MS] == dirty);

  ztt_write_mstatus_ms(clean);
  amestatus = 0b0;
  ame_set_unsupported();
  assert(mstatus[MS] == dirty);

  // Backend ownership transitions initialise, rather than dirty, the AME
  // context.  Releasing ownership retains that Initial architectural state.
  ame_release_backend();
  assert(ameown == 0b0);
  assert(mstatus[MS] == initial);
  assert(mstatus[SD] == 0b0);

  assert(ame_acquire_backend(descriptor) == granted);
  assert(ameown == 0b1);
  assert(mstatus[MS] == initial);
  assert(mstatus[SD] == 0b0);

  ame_release_backend();
  assert(ameown == 0b0);
  assert(mstatus[MS] == initial);

  ztt_write_mstatus_ms(off);
  assert(not(ame_context_enabled()));
  assert(not(check_CSR(0xCC0, Machine, CSRRead)));
  assert(not(check_CSR(0x810, Machine, CSRRead)));

  // Instruction execution has the same effective-enable gate as the CSRs.
  // Ownership alone cannot bypass mstatus.MS = Off.
  ameown = 0b1;
  assert(execute(TEST_AME_MZERO_2D_M(0b00000)) == Illegal_Instruction());
}

$[test]
function test_ztt_backend_management_boundaries() -> unit = {
  let initial : ext_status = extStatus_map(Initial);
  let descriptor : xlenbits = zeros();
  let invalid_descriptor : xlenbits = zero_extend(0x40);
  let granted : xlenbits = zero_extend(0b1);
  let bad_desc : xlenbits = zero_extend(0x08);
  let value : amereglen = ones();

  ame_release_backend();
  ameown = 0b0;
  mstatus[MS] = initial;

  // Reserved descriptor bits report BAD_DESC without changing ownership or
  // the enabled-state status.
  assert(ame_acquire_backend(invalid_descriptor) == bad_desc);
  assert(ameown == 0b0);
  assert(mstatus[MS] == initial);

  assert(ame_acquire_backend(descriptor) == granted);
  M(Ameregidx(0b00000)) = value;
  assert(mstatus[MS] == extStatus_map(Dirty));

  // A request from the current owner is granted without rebinding or
  // reinitialising the backend state.
  assert(ame_acquire_backend(descriptor) == granted);
  assert(M(Ameregidx(0b00000)) == value);
  assert(mstatus[MS] == extStatus_map(Dirty));

  ame_release_backend();
  assert(ameown == 0b0);
  assert(mstatus[MS] == initial);

  // A non-owner release is a no-op and does not alter MS.
  ame_release_backend();
  assert(ameown == 0b0);
  assert(mstatus[MS] == initial)
}
