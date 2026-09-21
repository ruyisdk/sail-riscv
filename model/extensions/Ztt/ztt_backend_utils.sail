// Single-hart backend ownership helpers.

function ame_reset_backend_context() -> unit = {
  foreach (mreg from 0 to (ame_num_m_regs - 1)) {
    let index = nat_to_ameregidx(mreg);
    M(index) = zeros();
    MD(Mdregidx(ameregidx_bits(index))) = zeros()
  };
  foreach (acc from 0 to (ame_num_acc_regs - 1)) {
    let index = ameaccregidx_add(Ameaccregidx(0b00000), acc);
    ACC(index) = zeros();
    AD(Ameadregidx(ameaccregidx_bits(index))) = zeros()
  };
  amestype = zeros();
  amefflags = zeros();
  amexsat = 0b0;
  amestatus = 0b0
}
// Single-hart bring-up model: ownership is local to this architectural state.
// It does not model contention, wait/timeout progress, cross-hart backend
// binding, or virtualized ownership.  A platform concurrency model can replace
// these helpers without changing the instruction-facing state contract.  OS
// software performs context save/restore through the architectural instructions
// and CSRs defined by the manual.
function ame_acquire_backend(descriptor : xlenbits) -> xlenbits = {
  let wait_mode = descriptor[1 .. 0];
  let timeout_class = descriptor[5 .. 2];
  let valid_wait = wait_mode == 0b00 |
    (wait_mode == 0b01 & (unsigned(timeout_class) <= 3 | timeout_class == 0b1111));
  let valid_descriptor = descriptor[xlen - 1 .. 6] == zeros() & valid_wait;
  if not(valid_descriptor) then zero_extend(xlen, 0x08) // BAD_DESC in STATUS[7:1]
  else if ameown == 0b1 then zero_extend(xlen, 0x01) // GRANTED, already owned
  else {
    ame_reset_backend_context();
    ameown = 0b1;
    ame_set_context_initial();
    zero_extend(xlen, 0x01) // GRANTED
  }
}

function ame_release_backend() -> unit = {
  if ameown == 0b1 then {
    ame_reset_backend_context();
    ameown = 0b0;
    ame_set_context_initial()
  }
}
