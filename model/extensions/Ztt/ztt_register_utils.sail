// M/Acc register indexing, formation checks, and element access helpers.

// =========================================================================

type ame_m_snapshot = vector(32, dec, amereglen)

function ameregidx_bits(Ameregidx(b) : ameregidx) -> bits(5) = b
function ameregidx_nat(i : ameregidx) -> nat = unsigned(ameregidx_bits(i))
function nat_to_ameregidx(n : nat) -> ameregidx = Ameregidx(to_bits(5, n % 32))
function ameregidx_add(i : ameregidx, offset : nat) -> ameregidx =
  nat_to_ameregidx(ameregidx_nat(i) + offset)

function ame_check_formed_operand(base_reg : ameregidx, dtype : bits(32),
                                  nsq : nat) -> bool = {
  let size = ame_dtype_size(dtype);
  let per_square = ame_nregs(size);
  let span = ame_formed_span(dtype, nsq);
  size > 0 & span > 0 &
    ameregidx_nat(base_reg) < ame_num_m_regs &
    ameregidx_nat(base_reg) + span <= ame_num_m_regs &
    ameregidx_nat(base_reg) % max(1, per_square) == 0
}

function ameaccregidx_bits(Ameaccregidx(b) : ameaccregidx) -> bits(5) = b
function ameaccregidx_nat(i : ameaccregidx) -> nat = unsigned(ameaccregidx_bits(i))
function ameaccregidx_add(i : ameaccregidx, offset : nat) -> ameaccregidx =
  Ameaccregidx(to_bits(5, (ameaccregidx_nat(i) + offset) % 32))

function ame_check_mreg_group(base_reg : ameregidx, nregs : nat) -> bool = {
  let count = max(1, nregs);
  count <= ame_num_m_regs &
    ameregidx_nat(base_reg) < ame_num_m_regs &
    ameregidx_nat(base_reg) + count <= ame_num_m_regs &
    ameregidx_nat(base_reg) % count == 0
}

// The model selects the manual's precise-exception behavior for references to
// unimplemented accumulator registers.
function ame_check_acc_reg_operand(reg : bits(5)) -> bool =
  unsigned(reg) < ame_num_acc_regs

// =========================================================================

function read_m_elem(dtype : bits(32), element_index : nat,
                     base_reg : ameregidx) -> bits(ame_max_dtype_size) = {
  static_assert(ame_max_dtype_size >= 128);
  let size = ame_dtype_size(dtype);
  let (reg_in_grp, bit_low) = ame_element_position(element_index, dtype);
  let nregs = ame_nregs(size);

  assert(size > 0, "read_m_elem: dtype uninitialized");
  assert(ameregidx_nat(base_reg) % max(1, nregs) == 0,
    "read_m_elem: base register not aligned");

  let reg_idx = ameregidx_add(base_reg, reg_in_grp);
  let reg_data = M(reg_idx);

  assert(bit_low + size <= mlen, "element extends beyond register bounds");

  match size {
     4  => { let v : bits( 4) = reg_data[(bit_low +  3) .. bit_low]; zero_extend(ame_max_dtype_size, v) },
     8  => { let v : bits( 8) = reg_data[(bit_low +  7) .. bit_low]; zero_extend(ame_max_dtype_size, v) },
    16  => { let v : bits(16) = reg_data[(bit_low + 15) .. bit_low]; zero_extend(ame_max_dtype_size, v) },
    32  => { let v : bits(32) = reg_data[(bit_low + 31) .. bit_low]; zero_extend(ame_max_dtype_size, v) },
    64  => { let v : bits(64) = reg_data[(bit_low + 63) .. bit_low]; zero_extend(ame_max_dtype_size, v) },
    128 => { let v : bits(128) = reg_data[(bit_low + 127) .. bit_low]; zero_extend(ame_max_dtype_size, v) },
    _   => internal_error(__FILE__, __LINE__, "unsupported element size")
  }
}

function write_m_elem(dtype : bits(32), base_reg : ameregidx,
                      element_index : nat,
                      ms1_val : bits(ame_max_dtype_size)) -> unit = {
  let size = ame_dtype_size(dtype);
  let (reg_in_grp, bit_low) = ame_element_position(element_index, dtype);
  let nregs = ame_nregs(size);

  assert(size > 0, "write_m_elem: dtype uninitialized");
  assert(ameregidx_nat(base_reg) % max(1, nregs) == 0,
    "write_m_elem: base register not aligned");

  let reg_idx = ameregidx_add(base_reg, reg_in_grp);

  assert(bit_low + size <= mlen, "element extends beyond register bounds");

  match size {
     4  => M(reg_idx) = [M(reg_idx) with (bit_low +  3) .. bit_low = ms1_val[ 3 .. 0]],
     8  => M(reg_idx) = [M(reg_idx) with (bit_low +  7) .. bit_low = ms1_val[ 7 .. 0]],
    16  => M(reg_idx) = [M(reg_idx) with (bit_low + 15) .. bit_low = ms1_val[15 .. 0]],
    32  => M(reg_idx) = [M(reg_idx) with (bit_low + 31) .. bit_low = ms1_val[31 .. 0]],
    64  => M(reg_idx) = [M(reg_idx) with (bit_low + 63) .. bit_low = ms1_val[63 .. 0]],
    128 => M(reg_idx) = [M(reg_idx) with (bit_low + 127) .. bit_low = ms1_val[127 .. 0]],
    _   => internal_error(__FILE__, __LINE__, "unsupported element size")
  }
}

function ame_snapshot_mregs() -> ame_m_snapshot = {
  var snapshot : ame_m_snapshot = vector_init(zeros());
  foreach (reg from 0 to (ame_num_m_regs - 1)) {
    snapshot[reg] = M(nat_to_ameregidx(reg))
  };
  snapshot
}

function ame_read_snapshot_elem(snapshot : ame_m_snapshot, dtype : bits(32),
                                base_reg : ameregidx, logical_index : nat)
  -> bits(ame_max_dtype_size) = {
  let size = ame_dtype_size(dtype);
  let (reg_in_group, bit_low) = ame_element_position(logical_index, dtype);
  let reg_index = (ameregidx_nat(base_reg) + reg_in_group) % 32;
  let reg_data = snapshot[reg_index];
  let shifted : bits(mlen) = reg_data >> bit_low;
  match size {
     4  => to_bits_unsafe(ame_max_dtype_size, unsigned(shifted) % (2 ^   4)),
     8  => to_bits_unsafe(ame_max_dtype_size, unsigned(shifted) % (2 ^   8)),
    16  => to_bits_unsafe(ame_max_dtype_size, unsigned(shifted) % (2 ^  16)),
    32  => to_bits_unsafe(ame_max_dtype_size, unsigned(shifted) % (2 ^  32)),
    64  => to_bits_unsafe(ame_max_dtype_size, unsigned(shifted) % (2 ^  64)),
   128  => to_bits_unsafe(ame_max_dtype_size, unsigned(shifted) % (2 ^ 128)),
    _   => internal_error(__FILE__, __LINE__, "unsupported element size")
  }
}

// =========================================================================
// Row-major square access
// =========================================================================

function read_m_square_rm(dtype : bits(32), base_reg : ameregidx) -> bits(acclen) = {
  let size = ame_dtype_size(dtype);
  let nregs = ame_nregs(size);
  let max_regs = acclen / mlen;

  assert(size > 0, "read_m_square_rm: dtype uninitialized");
  assert(ameregidx_nat(base_reg) % max(1, nregs) == 0,
    "read_m_square_rm: base register not aligned");

  var result : bits(acclen) = zeros();
  foreach (r from 0 to (max_regs - 1)) {
    if r < nregs then {
      let offset = r * mlen;
      result = [result with (offset + mlen - 1) .. offset = M(ameregidx_add(base_reg, r))];
    };
  };
  result
}

function write_m_square_rm(dtype : bits(32), base_reg : ameregidx,
                           rm_data : bits(acclen)) -> unit = {
  let size = ame_dtype_size(dtype);
  let nregs = ame_nregs(size);
  let max_regs = acclen / mlen;

  assert(size > 0, "write_m_square_rm: dtype uninitialized");
  assert(ameregidx_nat(base_reg) % max(1, nregs) == 0,
    "write_m_square_rm: base register not aligned");

  foreach (r from 0 to (max_regs - 1)) {
    if r < nregs then {
      let offset = r * mlen;
      M(ameregidx_add(base_reg, r)) = rm_data[(offset + mlen - 1) .. offset];
    };
  };
}
