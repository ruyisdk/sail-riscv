// =======================================================================================
// This Sail RISC-V architecture model, comprising all files and
// directories except where otherwise noted is subject the BSD
// two-clause license in the LICENSE file.
//
// SPDX-License-Identifier: BSD-2-Clause
// =======================================================================================
register m0 : amereglen
register m1 : amereglen
register m2 : amereglen
register m3 : amereglen
register m4 : amereglen
register m5 : amereglen
register m6 : amereglen
register m7 : amereglen
register m8 : amereglen
register m9 : amereglen
register m10 : amereglen
register m11 : amereglen
register m12 : amereglen
register m13 : amereglen
register m14 : amereglen
register m15 : amereglen
register m16 : amereglen
register m17 : amereglen
register m18 : amereglen
register m19 : amereglen
register m20 : amereglen
register m21 : amereglen
register m22 : amereglen
register m23 : amereglen
register m24 : amereglen
register m25 : amereglen
register m26 : amereglen
register m27 : amereglen
register m28 : amereglen
register m29 : amereglen
register m30 : amereglen
register m31 : amereglen

mapping amereg_name_raw : bits(5) <-> string = {
  0b00000 <-> "m0",
  0b00001 <-> "m1",
  0b00010 <-> "m2",
  0b00011 <-> "m3",
  0b00100 <-> "m4",
  0b00101 <-> "m5",
  0b00110 <-> "m6",
  0b00111 <-> "m7",
  0b01000 <-> "m8",
  0b01001 <-> "m9",
  0b01010 <-> "m10",
  0b01011 <-> "m11",
  0b01100 <-> "m12",
  0b01101 <-> "m13",
  0b01110 <-> "m14",
  0b01111 <-> "m15",
  0b10000 <-> "m16",
  0b10001 <-> "m17",
  0b10010 <-> "m18",
  0b10011 <-> "m19",
  0b10100 <-> "m20",
  0b10101 <-> "m21",
  0b10110 <-> "m22",
  0b10111 <-> "m23",
  0b11000 <-> "m24",
  0b11001 <-> "m25",
  0b11010 <-> "m26",
  0b11011 <-> "m27",
  0b11100 <-> "m28",
  0b11101 <-> "m29",
  0b11110 <-> "m30",
  0b11111 <-> "m31"
}

mapping amereg_name : ameregidx <-> string = { Ameregidx(i) <-> amereg_name_raw(i) }

// MS is the architectural enablement state for AME.  The current model does
// not implement H, so mstatus.MS is the sole applicable context field.  Keep
// this interface here so an H implementation can extend it with vsstatus.MS
// without changing Ztt instruction or CSR users.
function ame_context_enabled() -> bool =
  hartSupports(Ext_Ztt) & mstatus[MS] != extStatus_map(Off)

function ame_context_is_dirty() -> bool =
  extStatus_map(mstatus[MS]) == Dirty

function ame_update_mstatus_sd() -> unit = {
  let dirty = extStatus_map(mstatus[FS]) == Dirty |
              extStatus_map(mstatus[XS]) == Dirty |
              extStatus_map(mstatus[VS]) == Dirty |
              ame_context_is_dirty();
  mstatus[SD] = bool_to_bit(dirty);
  long_csr_write_callback("mstatus", "mstatush", mstatus.bits)
}

// Call this only after an AME architectural-state update has committed.
function ame_mark_context_dirty() -> unit = {
  if ame_context_enabled() & not(ame_context_is_dirty()) then {
    mstatus[MS] = extStatus_map(Dirty);
    ame_update_mstatus_sd()
  }
}

function rM(Ameregno(i) : ameregno) -> amereglen = {
  match i {
    0  => m0,
    1  => m1,
    2  => m2,
    3  => m3,
    4  => m4,
    5  => m5,
    6  => m6,
    7  => m7,
    8  => m8,
    9  => m9,
    10 => m10,
    11 => m11,
    12 => m12,
    13 => m13,
    14 => m14,
    15 => m15,
    16 => m16,
    17 => m17,
    18 => m18,
    19 => m19,
    20 => m20,
    21 => m21,
    22 => m22,
    23 => m23,
    24 => m24,
    25 => m25,
    26 => m26,
    27 => m27,
    28 => m28,
    29 => m29,
    30 => m30,
    31 => m31,
  }
}

function wM(Ameregno(i) : ameregno, v : amereglen) -> unit = {
  match i {
    0  => m0 = v,
    1  => m1 = v,
    2  => m2 = v,
    3  => m3 = v,
    4  => m4 = v,
    5  => m5 = v,
    6  => m6 = v,
    7  => m7 = v,
    8  => m8 = v,
    9  => m9 = v,
    10 => m10 = v,
    11 => m11 = v,
    12 => m12 = v,
    13 => m13 = v,
    14 => m14 = v,
    15 => m15 = v,
    16 => m16 = v,
    17 => m17 = v,
    18 => m18 = v,
    19 => m19 = v,
    20 => m20 = v,
    21 => m21 = v,
    22 => m22 = v,
    23 => m23 = v,
    24 => m24 = v,
    25 => m25 = v,
    26 => m26 = v,
    27 => m27 = v,
    28 => m28 = v,
    29 => m29 = v,
    30 => m30 = v,
    31 => m31 = v,
  };
  ame_mark_context_dirty()
}

function rM_bits(Ameregidx(i) : ameregidx) -> amereglen = rM(Ameregno(unsigned(i)))

function wM_bits(Ameregidx(i) : ameregidx, data : amereglen) -> unit = {
  wM(Ameregno(unsigned(i))) = data
}

overload M = {rM_bits, wM_bits, rM, wM}

register md0 : bits(32)
register md1 : bits(32)
register md2 : bits(32)
register md3 : bits(32)
register md4 : bits(32)
register md5 : bits(32)
register md6 : bits(32)
register md7 : bits(32)
register md8 : bits(32)
register md9 : bits(32)
register md10 : bits(32)
register md11 : bits(32)
register md12 : bits(32)
register md13 : bits(32)
register md14 : bits(32)
register md15 : bits(32)
register md16 : bits(32)
register md17 : bits(32)
register md18 : bits(32)
register md19 : bits(32)
register md20 : bits(32)
register md21 : bits(32)
register md22 : bits(32)
register md23 : bits(32)
register md24 : bits(32)
register md25 : bits(32)
register md26 : bits(32)
register md27 : bits(32)
register md28 : bits(32)
register md29 : bits(32)
register md30 : bits(32)
register md31 : bits(32)

mapping mdreg_name_raw : bits(5) <-> string = {
  0b00000 <-> "md0",
  0b00001 <-> "md1",
  0b00010 <-> "md2",
  0b00011 <-> "md3",
  0b00100 <-> "md4",
  0b00101 <-> "md5",
  0b00110 <-> "md6",
  0b00111 <-> "md7",
  0b01000 <-> "md8",
  0b01001 <-> "md9",
  0b01010 <-> "md10",
  0b01011 <-> "md11",
  0b01100 <-> "md12",
  0b01101 <-> "md13",
  0b01110 <-> "md14",
  0b01111 <-> "md15",
  0b10000 <-> "md16",
  0b10001 <-> "md17",
  0b10010 <-> "md18",
  0b10011 <-> "md19",
  0b10100 <-> "md20",
  0b10101 <-> "md21",
  0b10110 <-> "md22",
  0b10111 <-> "md23",
  0b11000 <-> "md24",
  0b11001 <-> "md25",
  0b11010 <-> "md26",
  0b11011 <-> "md27",
  0b11100 <-> "md28",
  0b11101 <-> "md29",
  0b11110 <-> "md30",
  0b11111 <-> "md31"
}

mapping mdreg_name : mdregidx <-> string = { Mdregidx(i) <-> mdreg_name_raw(i) }

function rMD(Mdregno(i) : mdregno) -> bits(32) = {
  match i {
    0  => md0,
    1  => md1,
    2  => md2,
    3  => md3,
    4  => md4,
    5  => md5,
    6  => md6,
    7  => md7,
    8  => md8,
    9  => md9,
    10 => md10,
    11 => md11,
    12 => md12,
    13 => md13,
    14 => md14,
    15 => md15,
    16 => md16,
    17 => md17,
    18 => md18,
    19 => md19,
    20 => md20,
    21 => md21,
    22 => md22,
    23 => md23,
    24 => md24,
    25 => md25,
    26 => md26,
    27 => md27,
    28 => md28,
    29 => md29,
    30 => md30,
    31 => md31,
  }
}

function wMD(Mdregno(i) : mdregno, v : bits(32)) -> unit = {
  match i {
    0  => md0 = v,
    1  => md1 = v,
    2  => md2 = v,
    3  => md3 = v,
    4  => md4 = v,
    5  => md5 = v,
    6  => md6 = v,
    7  => md7 = v,
    8  => md8 = v,
    9  => md9 = v,
    10 => md10 = v,
    11 => md11 = v,
    12 => md12 = v,
    13 => md13 = v,
    14 => md14 = v,
    15 => md15 = v,
    16 => md16 = v,
    17 => md17 = v,
    18 => md18 = v,
    19 => md19 = v,
    20 => md20 = v,
    21 => md21 = v,
    22 => md22 = v,
    23 => md23 = v,
    24 => md24 = v,
    25 => md25 = v,
    26 => md26 = v,
    27 => md27 = v,
    28 => md28 = v,
    29 => md29 = v,
    30 => md30 = v,
    31 => md31 = v,
  };
  ame_mark_context_dirty()
}

function rMD_bits(Mdregidx(i) : mdregidx) -> bits(32) = rMD(Mdregno(unsigned(i)))

function wMD_bits(Mdregidx(i) : mdregidx, data : bits(32)) -> unit = {
  wMD(Mdregno(unsigned(i))) = data
}

overload MD = {rMD_bits, wMD_bits, rMD, wMD}

register acc0 : ameaccreglen
register acc1 : ameaccreglen
register acc2 : ameaccreglen
register acc3 : ameaccreglen
register acc4 : ameaccreglen
register acc5 : ameaccreglen
register acc6 : ameaccreglen
register acc7 : ameaccreglen
register acc8 : ameaccreglen
register acc9 : ameaccreglen
register acc10 : ameaccreglen
register acc11 : ameaccreglen
register acc12 : ameaccreglen
register acc13 : ameaccreglen
register acc14 : ameaccreglen
register acc15 : ameaccreglen

// Storage covers only the architectural maximum AME_NUM_ACC_REGS = 16.
// Encodings 16-31 are decodable (see ameaccreg_name_raw) but raise Illegal
// Instruction via ame_check_acc_reg_operand before any accessor runs.

mapping ameaccreg_name_raw : bits(5) <-> string = {
  0b00000 <-> "acc0",
  0b00001 <-> "acc1",
  0b00010 <-> "acc2",
  0b00011 <-> "acc3",
  0b00100 <-> "acc4",
  0b00101 <-> "acc5",
  0b00110 <-> "acc6",
  0b00111 <-> "acc7",
  0b01000 <-> "acc8",
  0b01001 <-> "acc9",
  0b01010 <-> "acc10",
  0b01011 <-> "acc11",
  0b01100 <-> "acc12",
  0b01101 <-> "acc13",
  0b01110 <-> "acc14",
  0b01111 <-> "acc15",
  0b10000 <-> "acc16",
  0b10001 <-> "acc17",
  0b10010 <-> "acc18",
  0b10011 <-> "acc19",
  0b10100 <-> "acc20",
  0b10101 <-> "acc21",
  0b10110 <-> "acc22",
  0b10111 <-> "acc23",
  0b11000 <-> "acc24",
  0b11001 <-> "acc25",
  0b11010 <-> "acc26",
  0b11011 <-> "acc27",
  0b11100 <-> "acc28",
  0b11101 <-> "acc29",
  0b11110 <-> "acc30",
  0b11111 <-> "acc31"
}

mapping ameaccreg_name : ameaccregidx <-> string = { Ameaccregidx(i) <-> ameaccreg_name_raw(i) }
mapping ameadreg_name : ameadregidx <-> string = { Ameadregidx(i) <-> ameaccreg_name_raw(i) }

function rACC(Ameaccregno(i) : ameaccregno) -> ameaccreglen = {
  match i {
    0 => acc0,
    1 => acc1,
    2 => acc2,
    3 => acc3,
    4 => acc4,
    5 => acc5,
    6 => acc6,
    7 => acc7,
    8 => acc8,
    9 => acc9,
    10 => acc10,
    11 => acc11,
    12 => acc12,
    13 => acc13,
    14 => acc14,
    15 => acc15,
    _  => internal_error(__FILE__, __LINE__, "acc index >= ame_num_acc_regs")
  }
}

function wACC(Ameaccregno(i) : ameaccregno, v : ameaccreglen) -> unit = {
  match i {
    0 => acc0 = v,
    1 => acc1 = v,
    2 => acc2 = v,
    3 => acc3 = v,
    4 => acc4 = v,
    5 => acc5 = v,
    6 => acc6 = v,
    7 => acc7 = v,
    8 => acc8 = v,
    9 => acc9 = v,
    10 => acc10 = v,
    11 => acc11 = v,
    12 => acc12 = v,
    13 => acc13 = v,
    14 => acc14 = v,
    15 => acc15 = v,
    _  => internal_error(__FILE__, __LINE__, "acc index >= ame_num_acc_regs")
  };
  ame_mark_context_dirty()
}

function rACC_bits(Ameaccregidx(i) : ameaccregidx) -> ameaccreglen = rACC(Ameaccregno(unsigned(i)))

function wACC_bits(Ameaccregidx(i) : ameaccregidx, data : ameaccreglen) -> unit = {
  wACC(Ameaccregno(unsigned(i))) = data
}

overload ACC = {rACC_bits, wACC_bits, rACC, wACC}

register ad0 : bits(32)
register ad1 : bits(32)
register ad2 : bits(32)
register ad3 : bits(32)
register ad4 : bits(32)
register ad5 : bits(32)
register ad6 : bits(32)
register ad7 : bits(32)
register ad8 : bits(32)
register ad9 : bits(32)
register ad10 : bits(32)
register ad11 : bits(32)
register ad12 : bits(32)
register ad13 : bits(32)
register ad14 : bits(32)
register ad15 : bits(32)

// Same limit as the Acc registers: AME_NUM_ACC_REGS is at most 16.

function rAD(Ameadregno(i) : ameadregno) -> bits(32) = {
  match i {
    0 => ad0,
    1 => ad1,
    2 => ad2,
    3 => ad3,
    4 => ad4,
    5 => ad5,
    6 => ad6,
    7 => ad7,
    8 => ad8,
    9 => ad9,
    10 => ad10,
    11 => ad11,
    12 => ad12,
    13 => ad13,
    14 => ad14,
    15 => ad15,
    _  => internal_error(__FILE__, __LINE__, "ad index >= ame_num_acc_regs")
  }
}

function wAD(Ameadregno(i) : ameadregno, v : bits(32)) -> unit = {
  match i {
    0 => ad0 = v,
    1 => ad1 = v,
    2 => ad2 = v,
    3 => ad3 = v,
    4 => ad4 = v,
    5 => ad5 = v,
    6 => ad6 = v,
    7 => ad7 = v,
    8 => ad8 = v,
    9 => ad9 = v,
    10 => ad10 = v,
    11 => ad11 = v,
    12 => ad12 = v,
    13 => ad13 = v,
    14 => ad14 = v,
    15 => ad15 = v,
    _  => internal_error(__FILE__, __LINE__, "ad index >= ame_num_acc_regs")
  };
  ame_mark_context_dirty()
}

function rAD_bits(Ameadregidx(i) : ameadregidx) -> bits(32) = rAD(Ameadregno(unsigned(i)))

function wAD_bits(Ameadregidx(i) : ameadregidx, data : bits(32)) -> unit = {
  wAD(Ameadregno(unsigned(i))) = data
}

overload AD = {rAD_bits, wAD_bits, rAD, wAD}

// Acquiring or releasing the current backend establishes initial AME state.
// Every M/Md/Acc/Ad write goes through a common architectural commit barrier,
// while acquire/release explicitly restore Initial afterwards.
function ame_set_context_initial() -> unit = {
  if hartSupports(Ext_Ztt) then {
    mstatus[MS] = extStatus_map(Initial);
    ame_update_mstatus_sd()
  }
}

function ame_capability_csr_accessible(access_type : CSRAccessType) -> bool =
  ame_context_enabled() & access_type == CSRRead

register amenlen : bits(64)
mapping clause csr_name_map = 0xCC0 <-> "amenlen"
function clause is_CSR_accessible(0xCC0, _, access_type) =
  ame_capability_csr_accessible(access_type)
function clause is_CSR_exception_virtual(0xCC0, _, _) = true
function clause read_CSR(0xCC0) = amenlen[xlen - 1 .. 0]
function clause write_CSR(0xCC0, _) = { Ok(amenlen[xlen - 1 .. 0]) }

register ameudsz : bits(64)
mapping clause csr_name_map = 0xCC1 <-> "ameudsz"
function clause is_CSR_accessible(0xCC1, _, access_type) =
  ame_capability_csr_accessible(access_type)
function clause is_CSR_exception_virtual(0xCC1, _, _) = true
function clause read_CSR(0xCC1) = ameudsz[xlen - 1 .. 0]
function clause write_CSR(0xCC1, _) = { Ok(ameudsz[xlen - 1 .. 0]) }

register ameown : bits(1)

function ame_context_csr_accessible() -> bool =
  ame_context_enabled() & ameown == 0b1

function ame_context_owned() -> bool = ame_context_csr_accessible()

// An owning context must explicitly release AME before disabling it.  The
// common mstatus hook sees legalised mstatus/sstatus writes, so this covers
// both architectural CSR views without making core code depend on Ztt.
function clause is_mstatus_write_legal(updated) =
  not(hartSupports(Ext_Ztt) & ameown == 0b1 &
      extStatus_map(Mk_Mstatus(updated)[MS]) == Off)

// Unit tests that exercise AME instructions require both a live context and
// an acquired backend.  Keep that setup explicit and independent of test
// execution order.
function ame_test_enable_context() -> unit = {
  ameown = 0b1;
  ame_set_context_initial()
}

register amestype : bits(32)
mapping clause csr_name_map = 0x810 <-> "amestype"
function clause is_CSR_writable(0x810) = true
function clause is_CSR_accessible(0x810, _, _) = ame_context_csr_accessible()
function clause is_CSR_exception_virtual(0x810, _, _) = true
function clause read_CSR(0x810) = zero_extend(amestype)
function clause write_CSR(0x810, value) = {
  let old_value = amestype;
  amestype = value[31 .. 0];
  if amestype != old_value then ame_mark_context_dirty();
  Ok(zero_extend(amestype))
}

mapping clause csr_name_map = 0xCC3 <-> "ameown"
function clause is_CSR_accessible(0xCC3, _, access_type) =
  ame_capability_csr_accessible(access_type)
function clause is_CSR_exception_virtual(0xCC3, _, _) = true
function clause read_CSR(0xCC3) = zero_extend(ameown)
function clause write_CSR(0xCC3, _) = { Ok(zero_extend(ameown)) }

register amefflags : bits(5)
mapping clause csr_name_map = 0x811 <-> "amefflags"
function clause is_CSR_writable(0x811) = true
function clause is_CSR_accessible(0x811, _, _) = ame_context_csr_accessible()
function clause is_CSR_exception_virtual(0x811, _, _) = true
function clause read_CSR(0x811) = zero_extend(amefflags)
function clause write_CSR(0x811, value) = {
  let old_value = amefflags;
  amefflags = value[4 .. 0];
  if amefflags != old_value then ame_mark_context_dirty();
  Ok(zero_extend(amefflags))
}

// AME floating-point exceptions accrue independently of the F extension's fflags CSR.
function accrue_amefflags(flags : bits_fflags) -> unit = {
  let updated = amefflags | flags;
  if amefflags != updated then {
    amefflags = updated;
    csr_write_callback("amefflags", zero_extend(amefflags));
    ame_mark_context_dirty()
  }
}

register amexsat : bits(1)

function ame_set_saturated() -> unit = {
  if amexsat == 0b0 then {
    amexsat = 0b1;
    ame_mark_context_dirty()
  }
}

mapping clause csr_name_map = 0x812 <-> "amexsat"
function clause is_CSR_writable(0x812) = true
function clause is_CSR_accessible(0x812, _, _) = ame_context_csr_accessible()
function clause is_CSR_exception_virtual(0x812, _, _) = true
function clause read_CSR(0x812) = zero_extend(amexsat)
function clause write_CSR(0x812, value) = {
  let old_value = amexsat;
  amexsat = value[0 .. 0];
  if amexsat != old_value then ame_mark_context_dirty();
  Ok(zero_extend(amexsat))
}

// The current AME manual defines amestatus.UN as a sticky unsupported-operation
// report. It is not a synchronous exception and software clears it with zero.
register amestatus : bits(1)

function ame_set_unsupported() -> unit = {
  if amestatus == 0b0 then {
    amestatus = 0b1;
    ame_mark_context_dirty()
  }
}

function write_amestatus(value : xlenbits) -> unit = {
  if value[0] == 0b0 then amestatus = 0b0
}

mapping clause csr_name_map = 0x800 <-> "amestatus"
function clause is_CSR_accessible(0x800, _, _) = ame_context_csr_accessible()
function clause is_CSR_exception_virtual(0x800, _, _) = true
function clause read_CSR(0x800) = zero_extend(amestatus)
function clause write_CSR(0x800, value) = {
  let old_value = amestatus;
  write_amestatus(value);
  if amestatus != old_value then ame_mark_context_dirty();
  Ok(zero_extend(amestatus))
}
