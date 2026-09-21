// Pure row-major bit-vector helpers shared by Ztt instruction families.

// =========================================================================
// Row-major element extraction / insertion
//
// These operate on bits(acclen) bit-vectors (i.e. the result of
// read_m_square_rm or the input to write_m_square_rm) rather than on
// the register file directly.  This enables the efficient instruction
// pattern: read square → loop over elements in bit-vector → write square,
// minimising individual register read-modify-write operations.
// =========================================================================

/* Extract a single element from a row-major square bit-vector.
   In row-major layout element e of size s occupies bits [(e+1)*s-1 : e*s].
   Returns the element zero-extended to bits(ame_max_dtype_size). */
function extract_elem_rm(rm_data : bits(acclen), element_size : nat,
                         elem_idx : nat) -> bits(ame_max_dtype_size) = {
  static_assert(ame_max_dtype_size >= 128);
  let bit_low = elem_idx * element_size;
  assert(bit_low + element_size <= acclen, "element extends beyond square bounds");
  match element_size {
     4  => { let v : bits( 4) = rm_data[(bit_low +  3) .. bit_low]; zero_extend(ame_max_dtype_size, v) },
     8  => { let v : bits( 8) = rm_data[(bit_low +  7) .. bit_low]; zero_extend(ame_max_dtype_size, v) },
    16  => { let v : bits(16) = rm_data[(bit_low + 15) .. bit_low]; zero_extend(ame_max_dtype_size, v) },
    32  => { let v : bits(32) = rm_data[(bit_low + 31) .. bit_low]; zero_extend(ame_max_dtype_size, v) },
    64  => { let v : bits(64) = rm_data[(bit_low + 63) .. bit_low]; zero_extend(ame_max_dtype_size, v) },
    128 => { let v : bits(128) = rm_data[(bit_low + 127) .. bit_low]; zero_extend(ame_max_dtype_size, v) },
    _   => internal_error(__FILE__, __LINE__, "unsupported element size")
  }
}
/* Insert a single element into a row-major square bit-vector.
   Only the low element_size bits of value are written; the function
   returns the updated bit-vector (pure functional update). */
function insert_elem_rm(rm_data : bits(acclen), element_size : nat,
                        elem_idx : nat,
                        ms1_val : bits(ame_max_dtype_size)) -> bits(acclen) = {
  let bit_low = elem_idx * element_size;
  assert(bit_low + element_size <= acclen, "element extends beyond square bounds");
  match element_size {
     4  => [rm_data with (bit_low +  3) .. bit_low = ms1_val[ 3 .. 0]],
     8  => [rm_data with (bit_low +  7) .. bit_low = ms1_val[ 7 .. 0]],
    16  => [rm_data with (bit_low + 15) .. bit_low = ms1_val[15 .. 0]],
    32  => [rm_data with (bit_low + 31) .. bit_low = ms1_val[31 .. 0]],
    64  => [rm_data with (bit_low + 63) .. bit_low = ms1_val[63 .. 0]],
    128 => [rm_data with (bit_low + 127) .. bit_low = ms1_val[127 .. 0]],
    _   => internal_error(__FILE__, __LINE__, "unsupported element size")
  }
}
