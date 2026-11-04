// Integer shift instruction helpers.

function ame_int_shift_result(op : ame_int_shift_op, dtype : bits(32),
                              ms1_val : bits(ame_max_dtype_size), shift : nat)
  -> bits(ame_max_dtype_size) = {
  match ame_dtype_size(dtype) {
    4 => {
      let element : bits(4) = ms1_val[3..0];
      match op {
        AME_INT_SHIFT_LEFT => zero_extend(ame_max_dtype_size, element << shift),
        AME_INT_SHIFT_RIGHT_LOGICAL => zero_extend(ame_max_dtype_size, element >> shift),
        AME_INT_SHIFT_RIGHT_ARITH =>
          zero_extend(ame_max_dtype_size, (sign_extend(8, element) >> shift)[3..0])
      }
    },
    8 => {
      let element : bits(8) = ms1_val[7..0];
      match op {
        AME_INT_SHIFT_LEFT => zero_extend(ame_max_dtype_size, element << shift),
        AME_INT_SHIFT_RIGHT_LOGICAL => zero_extend(ame_max_dtype_size, element >> shift),
        AME_INT_SHIFT_RIGHT_ARITH =>
          zero_extend(ame_max_dtype_size, (sign_extend(16, element) >> shift)[7..0])
      }
    },
    16 => {
      let element : bits(16) = ms1_val[15..0];
      match op {
        AME_INT_SHIFT_LEFT => zero_extend(ame_max_dtype_size, element << shift),
        AME_INT_SHIFT_RIGHT_LOGICAL => zero_extend(ame_max_dtype_size, element >> shift),
        AME_INT_SHIFT_RIGHT_ARITH =>
          zero_extend(ame_max_dtype_size, (sign_extend(32, element) >> shift)[15..0])
      }
    },
    32 => {
      let element : bits(32) = ms1_val[31..0];
      match op {
        AME_INT_SHIFT_LEFT => zero_extend(ame_max_dtype_size, element << shift),
        AME_INT_SHIFT_RIGHT_LOGICAL => zero_extend(ame_max_dtype_size, element >> shift),
        AME_INT_SHIFT_RIGHT_ARITH =>
          zero_extend(ame_max_dtype_size, (sign_extend(64, element) >> shift)[31..0])
      }
    },
    64 => {
      let element : bits(64) = ms1_val[63..0];
      match op {
        AME_INT_SHIFT_LEFT => zero_extend(ame_max_dtype_size, element << shift),
        AME_INT_SHIFT_RIGHT_LOGICAL => zero_extend(ame_max_dtype_size, element >> shift),
        AME_INT_SHIFT_RIGHT_ARITH =>
          zero_extend(ame_max_dtype_size, (sign_extend(128, element) >> shift)[63..0])
      }
    },
    128 => {
      let element : bits(128) = ms1_val[127..0];
      match op {
        AME_INT_SHIFT_LEFT => zero_extend(ame_max_dtype_size, element << shift),
        AME_INT_SHIFT_RIGHT_LOGICAL => zero_extend(ame_max_dtype_size, element >> shift),
        AME_INT_SHIFT_RIGHT_ARITH =>
          zero_extend(ame_max_dtype_size, (sign_extend(256, element) >> shift)[127..0])
      }
    },
    _ => internal_error(__FILE__, __LINE__, "unsupported integer element size")
  }
}

function ame_ew_shift_m(md_dtype : bits(32), ms1_dtype : bits(32),
                        ms2_dtype : bits(32), md : ameregidx,
                        ms1 : ameregidx, ms2 : ameregidx,
                        op : ame_int_shift_op) -> bool = {
  let data_size = ame_dtype_size(ms1_dtype);
  let nsq = ame_nsq3(md_dtype, ms1_dtype, ms2_dtype);

  if not(ame_valid_int_ew_dtype(md_dtype) & ame_valid_int_ew_dtype(ms1_dtype) & ame_valid_int_ew_dtype(ms2_dtype)) then {
    ame_set_unsupported();
    true
  }
  else if md_dtype != ms1_dtype | (op == AME_INT_SHIFT_RIGHT_ARITH & not(ame_is_signed(ms1_dtype))) then {
    ame_set_unsupported();
    true
  }
  else if not(ame_check_formed_operand(md, md_dtype, nsq)) then false
  else if not(ame_check_formed_operand(ms1, ms1_dtype, nsq)) then false
  else if not(ame_check_formed_operand(ms2, ms2_dtype, nsq)) then false
  else {
    let snapshot = ame_snapshot_mregs();

    foreach (e from 0 to (nsq * ame_nelem - 1)) {
      let amount : nat = unsigned(ame_read_snapshot_elem(
        snapshot, ms2_dtype, ms2, e)) % max(1, data_size);
      write_m_elem(md_dtype, md, e,
        ame_int_shift_result(op, ms1_dtype,
          ame_read_snapshot_elem(snapshot, ms1_dtype, ms1, e), amount))
    };
    true
  }
}

function ame_ew_shift_x(md_dtype : bits(32), ms2_dtype : bits(32),
                        md : ameregidx, rs1_val : xlenbits,
                        ms2 : ameregidx, op : ame_int_shift_op) -> bool = {
  let data_size = ame_dtype_size(ms2_dtype);
  let nsq = ame_nsq2(md_dtype, ms2_dtype);

  if not(ame_valid_int_ew_dtype(md_dtype) & ame_valid_int_ew_dtype(ms2_dtype)) then {
    ame_set_unsupported();
    true
  }
  else if md_dtype != ms2_dtype | (op == AME_INT_SHIFT_RIGHT_ARITH & not(ame_is_signed(ms2_dtype))) then {
    ame_set_unsupported();
    true
  }
  else if not(ame_check_formed_operand(md, md_dtype, nsq)) then false
  else if not(ame_check_formed_operand(ms2, ms2_dtype, nsq)) then false
  else {
    let amount : nat = unsigned(rs1_val) % max(1, data_size);
    let snapshot = ame_snapshot_mregs();

    foreach (e from 0 to (nsq * ame_nelem - 1)) {
      write_m_elem(md_dtype, md, e,
        ame_int_shift_result(op, ms2_dtype,
          ame_read_snapshot_elem(snapshot, ms2_dtype, ms2, e), amount))
    };
    true
  }
}
