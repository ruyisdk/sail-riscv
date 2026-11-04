// Permutation, gather/scatter, broadcast, and debug-move implementations.

// Debug move implementation helpers.

// Debug moves address a single physical M register through a normalized
// row-major view with the implementation's unsigned unit datatype.  The
// instruction width, rather than Md, determines the element interpretation.
function ame_debug_mmove_valid(reg : ameregidx, width : nat) -> bool =
  ameregidx_nat(reg) < ame_num_m_regs &
    width > 0 &
    width <= ame_nlen * ame_unit_dtype_size &
    mlen >= width

function ame_debug_mmove_position(pos : xlenbits, width : nat) -> nat =
  match width {
    8  => unsigned(pos) % max(1, mlen / 8),
    16 => unsigned(pos) % max(1, mlen / 16),
    32 => unsigned(pos) % max(1, mlen / 32),
    64 => unsigned(pos) % max(1, mlen / 64),
    _  => 0,
  }

function ame_debug_mmove_write(reg : ameregidx, pos : xlenbits,
                               value : bits(64), width : nat) -> bool = {
  if not(ame_debug_mmove_valid(reg, width)) then false
  else {
    let bit_low = ame_debug_mmove_position(pos, width) * width;
    assert(bit_low + width <= mlen, "debug move element extends beyond M register");
    match width {
      8  => M(reg) = [M(reg) with (bit_low + 7) .. bit_low = value[7..0]],
      16 => M(reg) = [M(reg) with (bit_low + 15) .. bit_low = value[15..0]],
      32 => M(reg) = [M(reg) with (bit_low + 31) .. bit_low = value[31..0]],
      64 => M(reg) = [M(reg) with (bit_low + 63) .. bit_low = value[63..0]],
      _  => return false,
    };
    true
  }
}

function ame_debug_mmove_read(reg : ameregidx, pos : xlenbits, width : nat)
  -> option(bits(64)) = {
  if not(ame_debug_mmove_valid(reg, width)) then None()
  else {
    let bit_low = ame_debug_mmove_position(pos, width) * width;
    assert(bit_low + width <= mlen, "debug move element extends beyond M register");
    match width {
      8  => Some(zero_extend(64, M(reg)[(bit_low + 7) .. bit_low])),
      16 => Some(zero_extend(64, M(reg)[(bit_low + 15) .. bit_low])),
      32 => Some(zero_extend(64, M(reg)[(bit_low + 31) .. bit_low])),
      64 => Some(M(reg)[(bit_low + 63) .. bit_low]),
      _  => None(),
    }
  }
}


function ame_valid_permute_dtype(dtype : bits(32)) -> bool = {
  let size = ame_dtype_size(dtype);
  size > 0 & not(ame_is_storage_only(dtype))
}

// The manual's rs1_val-shift instructions apply a signed low-32-bit offset
// along one matrix axis, zero-filling positions that leave the square.
function ame_shift_axis_ew(md_dtype : bits(32), ms1_dtype : bits(32),
                           md : ameregidx, ms1 : ameregidx,
                           shift : int, shift_rows : bool) -> bool = {
  let dest_size = ame_dtype_size(md_dtype);
  let src_size = ame_dtype_size(ms1_dtype);
  let dest_nregs = ame_nregs(dest_size);
  let src_nregs = ame_nregs(src_size);

  if not(ame_valid_permute_dtype(md_dtype) & ame_valid_permute_dtype(ms1_dtype)) then ame_unsupported_result()
  else if dest_size != src_size then ame_unsupported_result()
  else if not(ame_check_mreg_group(md, dest_nregs)) then false
  else if not(ame_check_mreg_group(ms1, src_nregs)) then false
  else {
    let src_data = read_m_square_rm(ms1_dtype, ms1);
    var dest_data : bits(acclen) = zeros();

    foreach (row from 0 to (ame_nlen - 1)) {
      foreach (col from 0 to (ame_nlen - 1)) {
        let destination_axis : int = if shift_rows then row else col;
        var element : bits(ame_max_dtype_size) = zeros();
        foreach (source_axis from 0 to (ame_nlen - 1)) {
          let source_axis_int : int = source_axis;
          if source_axis_int - destination_axis == shift then {
            let source_index = if shift_rows then source_axis * ame_nlen + col else row * ame_nlen + source_axis;
            element = extract_elem_rm(src_data, src_size, source_index)
          }
        };
        dest_data = insert_elem_rm(dest_data, dest_size, row * ame_nlen + col, element)
      }
    };

    write_m_square_rm(md_dtype, md, dest_data);
    true
  }
}

function ame_broadcast_axis_ew(md_dtype : bits(32), ms1_dtype : bits(32),
                               md : ameregidx, ms1 : ameregidx,
                               coordinate : xlenbits, broadcast_row : bool) -> bool = {
  let dest_size = ame_dtype_size(md_dtype);
  let src_size = ame_dtype_size(ms1_dtype);
  let dest_nregs = ame_nregs(dest_size);
  let src_nregs = ame_nregs(src_size);
  let source_axis = unsigned(coordinate);

  if not(ame_valid_permute_dtype(md_dtype) & ame_valid_permute_dtype(ms1_dtype)) then ame_unsupported_result()
  else if dest_size != src_size then ame_unsupported_result()
  else if source_axis >= ame_nlen then false
  else if not(ame_check_mreg_group(md, dest_nregs)) then false
  else if not(ame_check_mreg_group(ms1, src_nregs)) then false
  else {
    let src_data = read_m_square_rm(ms1_dtype, ms1);
    var dest_data : bits(acclen) = zeros();

    foreach (row from 0 to (ame_nlen - 1)) {
      foreach (col from 0 to (ame_nlen - 1)) {
        let source_index = if broadcast_row then source_axis * ame_nlen + col else row * ame_nlen + source_axis;
        let element = extract_elem_rm(src_data, src_size, source_index);
        dest_data = insert_elem_rm(dest_data, dest_size, row * ame_nlen + col, element)
      }
    };

    write_m_square_rm(md_dtype, md, dest_data);
    true
  }
}

function ame_coordinate_id_ew(dtype : bits(32), md : ameregidx,
                              row_coordinate : bool) -> bool = {
  let size = ame_dtype_size(dtype);
  let nregs = ame_nregs(size);

  if not(ame_valid_int_ew_dtype(dtype)) then ame_unsupported_result()
  else if (ame_nlen - 1) > ame_int_max_value(dtype) then ame_unsupported_result()
  else if not(ame_check_mreg_group(md, nregs)) then false
  else {
    var dest_data : bits(acclen) = zeros();
    foreach (row from 0 to (ame_nlen - 1)) {
      foreach (col from 0 to (ame_nlen - 1)) {
        let coordinate : int = if row_coordinate then row else col;
        dest_data = insert_elem_rm(dest_data, size, row * ame_nlen + col,
          ame_int_result_from_int(dtype, coordinate))
      }
    };
    write_m_square_rm(dtype, md, dest_data);
    true
  }
}

function ame_gather_ew(md_dtype : bits(32), ms1_dtype : bits(32),
                       ms2_dtype : bits(32), md : ameregidx,
                       ms1 : ameregidx, ms2 : ameregidx,
                       by_row : bool) -> bool = {
  let dest_size = ame_dtype_size(md_dtype);
  let src_size = ame_dtype_size(ms1_dtype);
  let index_size = ame_dtype_size(ms2_dtype);
  let dest_nregs = ame_nregs(dest_size);
  let src_nregs = ame_nregs(src_size);
  let index_nregs = ame_nregs(index_size);

  if not(ame_valid_permute_dtype(md_dtype) & ame_valid_permute_dtype(ms1_dtype) & ame_valid_int_ew_dtype(ms2_dtype)) then ame_unsupported_result()
  else if dest_size != src_size then ame_unsupported_result()
  else if not(ame_check_mreg_group(md, dest_nregs)) then false
  else if not(ame_check_mreg_group(ms1, src_nregs)) then false
  else if not(ame_check_mreg_group(ms2, index_nregs)) then false
  else {
    let src_data = read_m_square_rm(ms1_dtype, ms1);
    let index_data = read_m_square_rm(ms2_dtype, ms2);
    var dest_data : bits(acclen) = zeros();

    foreach (row from 0 to (ame_nlen - 1)) {
      foreach (col from 0 to (ame_nlen - 1)) {
        let index_bits = extract_elem_rm(index_data, index_size, row * ame_nlen + col);
        // N is a power of two, so modulo N selects exactly the architectural
        // low log2(N) bits and ignores every higher index bit.
        let index_value : nat = unsigned(index_bits) % ame_nlen;
        let src_idx = if by_row then index_value * ame_nlen + col else row * ame_nlen + index_value;
        let elem = extract_elem_rm(src_data, src_size, src_idx);
        dest_data = insert_elem_rm(dest_data, dest_size, row * ame_nlen + col, elem)
      }
    };

    write_m_square_rm(md_dtype, md, dest_data);
    true
  }
}

function ame_scatter_result(op : ame_int_scatter_op, dtype : bits(32),
                            md_val : bits(ame_max_dtype_size),
                            ms1_val : bits(ame_max_dtype_size))
  -> bits(ame_max_dtype_size) = {
  match op {
    AME_INT_SCATTER_ADD => { let (_, result) = ame_int_binary_result(AME_INT_ADD, dtype, md_val, ms1_val); result },
    AME_INT_SCATTER_MAX => { let (_, result) = ame_int_binary_result(AME_INT_MAX, dtype, md_val, ms1_val); result }
  }
}

function ame_scatter_saturates(op : ame_int_scatter_op, dtype : bits(32),
                               md_val : bits(ame_max_dtype_size),
                               ms1_val : bits(ame_max_dtype_size)) -> bool = {
  let current_int = ame_elem_int(dtype, md_val);
  let incoming_int = ame_elem_int(dtype, ms1_val);
  match op {
    AME_INT_SCATTER_ADD => ame_int_saturates(dtype, current_int + incoming_int),
    AME_INT_SCATTER_MAX => ame_int_saturates(dtype, max(current_int, incoming_int))
  }
}

function ame_scatter_ew(md_dtype : bits(32), ms1_dtype : bits(32),
                        ms2_dtype : bits(32), md : ameregidx,
                        ms1 : ameregidx, ms2 : ameregidx,
                        op : ame_int_scatter_op, target_row : bool) -> bool = {
  let dest_size = ame_dtype_size(md_dtype);
  let src_size = ame_dtype_size(ms1_dtype);
  let index_size = ame_dtype_size(ms2_dtype);
  let dest_nregs = ame_nregs(dest_size);
  let src_nregs = ame_nregs(src_size);
  let index_nregs = ame_nregs(index_size);

  if not(ame_valid_int_elementwise_dtype(md_dtype) & ame_valid_int_elementwise_dtype(ms1_dtype) & ame_valid_int_ew_dtype(ms2_dtype)) then ame_unsupported_result()
  else if dest_size != src_size | ame_is_signed(md_dtype) != ame_is_signed(ms1_dtype) then ame_unsupported_result()
  else if not(ame_check_mreg_group(md, dest_nregs)) then false
  else if not(ame_check_mreg_group(ms1, src_nregs)) then false
  else if not(ame_check_mreg_group(ms2, index_nregs)) then false
  else {
    let src_data = read_m_square_rm(ms1_dtype, ms1);
    let index_data = read_m_square_rm(ms2_dtype, ms2);
    var dest_data = read_m_square_rm(md_dtype, md);
    var saturated : bits(1) = 0b0;

    foreach (row from 0 to (ame_nlen - 1)) {
      foreach (col from 0 to (ame_nlen - 1)) {
        let index_bits = extract_elem_rm(index_data, index_size, row * ame_nlen + col);
        let index_value : nat = unsigned(index_bits) % ame_nlen;
        let incoming = extract_elem_rm(src_data, src_size, row * ame_nlen + col);
        let dest_idx = if target_row then index_value * ame_nlen + col else row * ame_nlen + index_value;
        let current = extract_elem_rm(dest_data, dest_size, dest_idx);
        saturated = saturated | bool_to_bit(ame_scatter_saturates(op, md_dtype, current, incoming));
        dest_data = insert_elem_rm(dest_data, dest_size, dest_idx,
          ame_scatter_result(op, md_dtype, current, incoming))
      }
    };

    write_m_square_rm(md_dtype, md, dest_data);
    if saturated == 0b1 then ame_set_saturated();
    true
  }
}

// The current AME specification defines the zip and unzip operations as
// in-place two-square permutations.  Both encoded operands are read before
// either result is committed, so aliasing is rejected before touching state.
enum ame_pair_permutation = {
  AME_PAIR_COL_UNZIP,
  AME_PAIR_COL_ZIP,
  AME_PAIR_ROW_UNZIP,
  AME_PAIR_ROW_ZIP
}

function ame_pair_permute_ew(ms1_dtype : bits(32), ms2_dtype : bits(32),
                             reg1 : ameregidx, reg2 : ameregidx,
                             op : ame_pair_permutation) -> bool = {
  let size1 = ame_dtype_size(ms1_dtype);
  let size2 = ame_dtype_size(ms2_dtype);
  let nregs1 = ame_nregs(size1);
  let nregs2 = ame_nregs(size2);

  if ameregidx_bits(reg1) == ameregidx_bits(reg2) then false
  else if not(ame_valid_permute_dtype(ms1_dtype) & ame_valid_permute_dtype(ms2_dtype)) then ame_unsupported_result()
  else if size1 != size2 then ame_unsupported_result()
  else if not(ame_check_mreg_group(reg1, nregs1)) then false
  else if not(ame_check_mreg_group(reg2, nregs2)) then false
  else {
    let src1 = read_m_square_rm(ms1_dtype, reg1);
    let src2 = read_m_square_rm(ms2_dtype, reg2);
    let half_nlen = ame_nlen / 2;
    var dest1 : bits(acclen) = zeros();
    var dest2 : bits(acclen) = zeros();

    foreach (row from 0 to (ame_nlen - 1)) {
      foreach (col from 0 to (ame_nlen - 1)) {
        let idx = row * ame_nlen + col;
        match op {
          AME_PAIR_COL_UNZIP => {
            if col < half_nlen then {
              dest1 = insert_elem_rm(dest1, size1, idx,
                                     extract_elem_rm(src1, size1, row * ame_nlen + 2 * col));
              dest2 = insert_elem_rm(dest2, size1, idx,
                                     extract_elem_rm(src1, size1, row * ame_nlen + 2 * col + 1))
            } else {
              let source_col = col - half_nlen;
              dest1 = insert_elem_rm(dest1, size1, idx,
                                     extract_elem_rm(src2, size1, row * ame_nlen + 2 * source_col));
              dest2 = insert_elem_rm(dest2, size1, idx,
                                     extract_elem_rm(src2, size1, row * ame_nlen + 2 * source_col + 1))
            }
          },
          AME_PAIR_COL_ZIP => {
            let source_col = col / 2;
            let source = if (col % 2) == 0 then src1 else src2;
            dest1 = insert_elem_rm(dest1, size1, idx,
                                   extract_elem_rm(source, size1, row * ame_nlen + source_col));
            dest2 = insert_elem_rm(dest2, size1, idx,
                                   extract_elem_rm(source, size1, row * ame_nlen + half_nlen + source_col))
          },
          AME_PAIR_ROW_UNZIP => {
            if row < half_nlen then {
              dest1 = insert_elem_rm(dest1, size1, idx,
                                     extract_elem_rm(src1, size1, (2 * row) * ame_nlen + col));
              dest2 = insert_elem_rm(dest2, size1, idx,
                                     extract_elem_rm(src1, size1, (2 * row + 1) * ame_nlen + col))
            } else {
              let source_row = row - half_nlen;
              dest1 = insert_elem_rm(dest1, size1, idx,
                                     extract_elem_rm(src2, size1, (2 * source_row) * ame_nlen + col));
              dest2 = insert_elem_rm(dest2, size1, idx,
                                     extract_elem_rm(src2, size1, (2 * source_row + 1) * ame_nlen + col))
            }
          },
          AME_PAIR_ROW_ZIP => {
            let source_row = row / 2;
            let source = if (row % 2) == 0 then src1 else src2;
            dest1 = insert_elem_rm(dest1, size1, idx,
                                   extract_elem_rm(source, size1, source_row * ame_nlen + col));
            dest2 = insert_elem_rm(dest2, size1, idx,
                                   extract_elem_rm(source, size1, (half_nlen + source_row) * ame_nlen + col))
          }
        }
      }
    };

    write_m_square_rm(ms1_dtype, reg1, dest1);
    write_m_square_rm(ms1_dtype, reg2, dest2);
    true
  }
}

// Typed X-register ingress currently advertises identity conversion tuples for
// every supported AME datatype. Other source/destination pairs are reported
// unsupported rather than silently interpreting xs1 using the destination type.
function ame_broadcast_typed_x(md_dtype : bits(32), ms1_dtype : bits(32),
                               md : ameregidx, rs1_val : xlenbits) -> bool = {
  let dest_size = ame_dtype_size(md_dtype);
  let dest_nregs = ame_nregs(dest_size);

  if not(ame_datatype_supported(md_dtype) & ame_datatype_supported(ms1_dtype)) then ame_unsupported_result()
  else if md_dtype != ms1_dtype then ame_unsupported_result()
  else if not(ame_check_mreg_group(md, dest_nregs)) then false
  else {
    let value : bits(ame_max_dtype_size) = zero_extend(ame_max_dtype_size, rs1_val);
    foreach (e from 0 to (ame_total_elements(md_dtype) - 1)) {
      write_m_elem(md_dtype, md, e, value)
    };
    true
  }
}

// The supported single-square conversion tuples mirror ame_mconv_ew: packed
// 4-bit integer storage and non-packed 8-bit integer compute elements.
function ame_pack_square_ew(md_dtype : bits(32), ms1_dtype : bits(32),
                            md : ameregidx, ms1 : ameregidx,
                            slot_selector : xlenbits) -> bool = {
  let dest_size = ame_dtype_size(md_dtype);
  let src_size = ame_dtype_size(ms1_dtype);
  let pack_factor = ame_pack_factor(dest_size);

  if not(ame_datatype_supported(md_dtype) & ame_datatype_supported(ms1_dtype)) then ame_unsupported_result()
  else if not(ame_is_integer(md_dtype) & ame_is_integer(ms1_dtype)) then ame_unsupported_result()
  else if not(ame_is_storage_only(md_dtype)) | ame_is_storage_only(ms1_dtype) then ame_unsupported_result()
  else if src_size != ame_unit_dtype_size | dest_size * 2 != ame_unit_dtype_size then ame_unsupported_result()
  else if pack_factor != 2 then ame_unsupported_result()
  else if not(ame_check_mreg_group(md, 1)) then false
  else if not(ame_check_mreg_group(ms1, ame_nregs(src_size))) then false
  else {
    let slot : nat = unsigned(slot_selector) % pack_factor;
    let src_data = read_m_square_rm(ms1_dtype, ms1);
    var dest_data = read_m_square_rm(md_dtype, md);

    foreach (e from 0 to (ame_nelem - 1)) {
      let src_elem = extract_elem_rm(src_data, src_size, e);
      dest_data = insert_elem_rm(dest_data, dest_size, slot * ame_nelem + e,
        ame_convert_integer_elem(ms1_dtype, src_elem))
    };
    write_m_square_rm(md_dtype, md, dest_data);
    true
  }
}

function ame_unpack_square_ew(md_dtype : bits(32), ms1_dtype : bits(32),
                              md : ameregidx, ms1 : ameregidx,
                              slot_selector : xlenbits) -> bool = {
  let dest_size = ame_dtype_size(md_dtype);
  let src_size = ame_dtype_size(ms1_dtype);
  let pack_factor = ame_pack_factor(src_size);

  if not(ame_datatype_supported(md_dtype) & ame_datatype_supported(ms1_dtype)) then ame_unsupported_result()
  else if not(ame_is_integer(md_dtype) & ame_is_integer(ms1_dtype)) then ame_unsupported_result()
  else if ame_is_storage_only(md_dtype) | not(ame_is_storage_only(ms1_dtype)) then ame_unsupported_result()
  else if dest_size != ame_unit_dtype_size | src_size * 2 != ame_unit_dtype_size then ame_unsupported_result()
  else if pack_factor != 2 then ame_unsupported_result()
  else if not(ame_check_mreg_group(md, ame_nregs(dest_size))) then false
  else if not(ame_check_mreg_group(ms1, 1)) then false
  else {
    let slot : nat = unsigned(slot_selector) % pack_factor;
    let src_data = read_m_square_rm(ms1_dtype, ms1);
    var dest_data : bits(acclen) = zeros();

    foreach (e from 0 to (ame_nelem - 1)) {
      let src_elem = extract_elem_rm(src_data, src_size, slot * ame_nelem + e);
      dest_data = insert_elem_rm(dest_data, dest_size, e,
        ame_convert_integer_elem(ms1_dtype, src_elem))
    };
    write_m_square_rm(md_dtype, md, dest_data);
    true
  }
}
