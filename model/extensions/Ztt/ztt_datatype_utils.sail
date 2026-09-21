// =======================================================================================
// This Sail RISC-V architecture model, comprising all files and
// directories except where otherwise noted is subject the BSD
// two-clause license in the LICENSE file.
//
// SPDX-License-Identifier: BSD-2-Clause
// =======================================================================================

/*
 * Ztt datatype helpers: descriptor decoding, packing, and element position
 * mapping. Register access and register-group validation live in
 * ztt_register_utils.sail.
 *
 * Covers all element types defined in Ztt-0.1:
 *   Integer:  Int4..Int128, Uint4..Uint128 (signed/unsigned)
 *   Saturated integer: Int4_Sat..Int128_Sat, Uint4_Sat..Uint128_Sat
 *   Float:    FP16, BF16, FP32, FP64, OCP_E4M3, OCP_E5M2
 *   Storage-only: any dtype where size < ame_unit_dtype_size
 */

/* AME square matrix is nlen × nlen elements (nelem = nlen² total).
   ame_nlen is a compile-time constant, so we can use it as a Sail vector size. */
type ame_row    = vector(ame_nlen, dec, bits(ame_max_dtype_size))
type ame_matrix = vector(ame_nlen, dec, ame_row)

// =========================================================================
// Datatype decoding helpers
//
// AME 32-bit dtype encoding (from spec sections 4.1 and 4.2):
//   bits[7:0]   : element size in bits
//   bit[8]      : 0 = integer, 1 = floating point
//   bit[30]     : signed (integer types)
//   bit[29]     : saturating (integer types)
//   others      : type-specific (exp_width, rounding_mode, inf, denorm for FP)
// =========================================================================

type ame_dtype_bitsize = {0, 4, 8, 16, 32, 64, 128}
type is_ame_dtype_bitsize('n) -> Bool = 'n in {0, 4, 8, 16, 32, 64, 128}

/* Extract the element size in bits from the dtype register.
   Returns 0 if the dtype is uninitialized or invalid. */
function ame_dtype_size(dtype : bits(32)) -> ame_dtype_bitsize = {
  let s = unsigned(dtype[7 .. 0]);
  match s {
     4 => 4,
     8 => 8,
    16 => 16,
    32 => 32,
    64 => 64,
   128 => 128,
     _ => 0
  }
}

/* The model implements every standard AME v1.0 datatype, and no custom
   datatype.  Datatype setters use this predicate to implement the manual's
   discovery contract: an unsupported descriptor sets amestatus.UN without
   changing the selected descriptor or raw register storage. */
function ame_is_standard_integer_dtype(dtype : bits(32)) -> bool =
  dtype[31] == 0b0 & dtype[8] == 0b0 & dtype[26..9] == zeros() &
    ame_dtype_size(dtype) != 0

function ame_is_standard_float_dtype(dtype : bits(32)) -> bool = {
  let exp_width = dtype[30..26];
  dtype[31] == 0b0 & dtype[8] == 0b1 & dtype[19..9] == zeros() &
    unsigned(dtype[25..22]) <= 5 &
    (
      (dtype[7..0] == 0b00010000 & dtype[21..20] == 0b11 &
        (exp_width == 0b00101 | exp_width == 0b01000)) |
      (dtype[7..0] == 0b00100000 & dtype[21..20] == 0b11 &
        exp_width == 0b01000) |
      (dtype[7..0] == 0b01000000 & dtype[21..20] == 0b11 &
        exp_width == 0b01011) |
      (dtype[7..0] == 0b00001000 &
        ((dtype[21..20] == 0b01 & exp_width == 0b00100) |
         (dtype[21..20] == 0b11 & exp_width == 0b00101)))
    )
}

function ame_datatype_supported(dtype : bits(32)) -> bool =
  ame_is_standard_integer_dtype(dtype) | ame_is_standard_float_dtype(dtype)

// Operation tuples that the implementation does not provide are observable
// capabilities, not synchronous decode failures.  Helpers return true after
// recording UN so their execute clauses retire without modifying a target.
function ame_unsupported_result() -> bool = {
  ame_set_unsupported();
  true
}

/* Check if the dtype is a storage-only type.
   Storage-only: element size < ame_unit_dtype_size. */
function ame_is_storage_only(dtype : bits(32)) -> bool = {
  ame_dtype_size(dtype) < ame_unit_dtype_size
}

/* Check if the dtype is an integer type (bit[8] == 0). */
function ame_is_integer(dtype : bits(32)) -> bool =
  dtype[8] == 0b0

/* Check if the dtype is a floating-point type (bit[8] == 1). */
function ame_is_float(dtype : bits(32)) -> bool =
  dtype[8] == 0b1

/* Check if an integer dtype is signed (bit[30] == 1). */
function ame_is_signed(dtype : bits(32)) -> bool =
  dtype[30] == 0b1

/* Check if an integer dtype uses saturation arithmetic (bit[29] == 1). */
function ame_is_saturating(dtype : bits(32)) -> bool =
  dtype[29] == 0b1

// =========================================================================
// Register group layout computation
// =========================================================================

/* Number of M registers needed for a square of the given element size. */
function ame_nregs(element_size : nat) -> nat = {
  if element_size <= ame_unit_dtype_size then 1
  else element_size / ame_unit_dtype_size
}

/* Packing factor for storage-only types. */
function ame_pack_factor(element_size : nat) -> nat = {
  if element_size == 0 | element_size >= ame_unit_dtype_size then 1
  else ame_unit_dtype_size / element_size
}

/* Common operand formation for ordinary multi-operand instructions.
   N_sq is the largest packing factor in the instruction.  A packed operand
   stores several logical squares in each physical register; unit/wide
   operands therefore span one physical square group per logical square. */
function ame_nsq2(ms1_dtype : bits(32), ms2_dtype : bits(32)) -> nat =
  max(ame_pack_factor(ame_dtype_size(ms1_dtype)),
      ame_pack_factor(ame_dtype_size(ms2_dtype)))

function ame_nsq3(ms1_dtype : bits(32), ms2_dtype : bits(32),
                  dtype3 : bits(32)) -> nat =
  max(ame_pack_factor(ame_dtype_size(ms1_dtype)),
      max(ame_pack_factor(ame_dtype_size(ms2_dtype)),
          ame_pack_factor(ame_dtype_size(dtype3))))

/* Physical register span for an operand formed with nsq logical squares. */
function ame_formed_span(dtype : bits(32), nsq : nat) -> nat = {
  let size = ame_dtype_size(dtype);
  let pack = ame_pack_factor(size);
  if pack > 1 then (nsq + pack - 1) / pack
  else nsq * ame_nregs(size)
}

/* Total number of elements accessible through a register group. */
function ame_total_elements(dtype : bits(32)) -> nat = {
  let size = ame_dtype_size(dtype);
  if size == 0 then 0
  else if ame_is_storage_only(dtype) then
    ame_pack_factor(size) * ame_nelem
  else
    ame_nelem
}

// =========================================================================
// Element position mapping
// =========================================================================

function ame_element_position(element_index : nat, dtype : bits(32))
  -> (nat /* reg_in_group */, nat /* bit_low */) = {
  let size = ame_dtype_size(dtype);
  if ame_is_storage_only(dtype) then {
    let pack = ame_pack_factor(size);
    let square = element_index / ame_nelem;
    let in_square = element_index % ame_nelem;
    let reg_in_group = square / max(1, pack);
    let slot = square % max(1, pack);
    (reg_in_group, slot * ame_nelem * size + in_square * size)
  } else {
    // A formed non-packed operand contains one complete square per
    // `nregs`-register group.  The square number must select the group
    // before locating the element within that square; otherwise the second
    // logical square would alias the tail of the first register.
    let square = element_index / ame_nelem;
    let in_square = element_index % ame_nelem;
    let bit_offset = in_square * size;
    (square * ame_nregs(size) + bit_offset / mlen, bit_offset % mlen)
  }
}
