// Reduction and prefix instruction implementations.

function ame_int_reduce_result(op : ame_int_reduce_op, dtype : bits(32),
                               acc_val : bits(ame_max_dtype_size),
                               ms1_val : bits(ame_max_dtype_size))
  -> bits(ame_max_dtype_size) = {
  let lhs_int = ame_elem_int(dtype, acc_val);
  let rhs_int = ame_elem_int(dtype, ms1_val);
  match op {
    AME_INT_REDUCE_ADD => ame_int_result_from_int(dtype, lhs_int + rhs_int),
    AME_INT_REDUCE_MAX => ame_int_result_from_int(dtype, max(lhs_int, rhs_int)),
    AME_INT_REDUCE_MIN => ame_int_result_from_int(dtype, min(lhs_int, rhs_int))
  }
}

function ame_int_reduce_saturates(op : ame_int_reduce_op, dtype : bits(32),
                                  acc_val : bits(ame_max_dtype_size),
                                  ms1_val : bits(ame_max_dtype_size)) -> bool = {
  let lhs_int = ame_elem_int(dtype, acc_val);
  let rhs_int = ame_elem_int(dtype, ms1_val);
  match op {
    AME_INT_REDUCE_ADD => ame_int_saturates(dtype, lhs_int + rhs_int),
    AME_INT_REDUCE_MAX => ame_int_saturates(dtype, max(lhs_int, rhs_int)),
    AME_INT_REDUCE_MIN => ame_int_saturates(dtype, min(lhs_int, rhs_int))
  }
}

function ame_reduce_ew(md_dtype : bits(32), ms1_dtype : bits(32),
                       md : ameregidx, ms1 : ameregidx,
                       op : ame_int_reduce_op, by_row : bool) -> bool = {
  let dest_size = ame_dtype_size(md_dtype);
  let src_size = ame_dtype_size(ms1_dtype);
  let nsq = ame_nsq2(md_dtype, ms1_dtype);

  if not(ame_valid_int_elementwise_dtype(md_dtype) & ame_valid_int_elementwise_dtype(ms1_dtype)) then
    ame_unsupported_result()
  else if dest_size != src_size | ame_is_signed(md_dtype) != ame_is_signed(ms1_dtype) then
    ame_unsupported_result()
  else if not(ame_check_formed_operand(md, md_dtype, nsq)) then false
  else if not(ame_check_formed_operand(ms1, ms1_dtype, nsq)) then false
  else {
    let snapshot = ame_snapshot_mregs();
    var saturated : bits(1) = 0b0;

    foreach (sq from 0 to (nsq - 1)) {
    foreach (outer from 0 to (ame_nlen - 1)) {
      var running : bits(ame_max_dtype_size) = zeros();
      foreach (inner from 0 to (ame_nlen - 1)) {
        let local_idx = if by_row then outer * ame_nlen + inner else inner * ame_nlen + outer;
        let value = ame_read_snapshot_elem(snapshot, ms1_dtype, ms1,
                                           sq * ame_nelem + local_idx);
        if inner == 0 then
          running = value
        else {
          saturated = saturated | bool_to_bit(ame_int_reduce_saturates(op, md_dtype, running, value));
          running = ame_int_reduce_result(op, md_dtype, running, value)
        }
      };
      foreach (inner from 0 to (ame_nlen - 1)) {
        let local_idx = if by_row then outer * ame_nlen + inner else inner * ame_nlen + outer;
        write_m_elem(md_dtype, md, sq * ame_nelem + local_idx, running)
      }
    };
    };
    if saturated == 0b1 then ame_set_saturated();
    true
  }
}

function ame_prefix_ew(md_dtype : bits(32), ms1_dtype : bits(32),
                       md : ameregidx, ms1 : ameregidx,
                       op : ame_int_reduce_op, by_row : bool) -> bool = {
  let dest_size = ame_dtype_size(md_dtype);
  let src_size = ame_dtype_size(ms1_dtype);
  let nsq = ame_nsq2(md_dtype, ms1_dtype);

  if not(ame_valid_int_elementwise_dtype(md_dtype) & ame_valid_int_elementwise_dtype(ms1_dtype)) then
    ame_unsupported_result()
  else if dest_size != src_size | ame_is_signed(md_dtype) != ame_is_signed(ms1_dtype) then
    ame_unsupported_result()
  else if not(ame_check_formed_operand(md, md_dtype, nsq)) then false
  else if not(ame_check_formed_operand(ms1, ms1_dtype, nsq)) then false
  else {
    let snapshot = ame_snapshot_mregs();
    var saturated : bits(1) = 0b0;

    foreach (sq from 0 to (nsq - 1)) {
    foreach (outer from 0 to (ame_nlen - 1)) {
      var running : bits(ame_max_dtype_size) = zeros();
      foreach (inner from 0 to (ame_nlen - 1)) {
        let local_idx = if by_row then outer * ame_nlen + inner else inner * ame_nlen + outer;
        let idx = sq * ame_nelem + local_idx;
        let value = ame_read_snapshot_elem(snapshot, ms1_dtype, ms1, idx);
        if inner == 0 then
          running = value
        else {
          saturated = saturated | bool_to_bit(ame_int_reduce_saturates(op, md_dtype, running, value));
          running = ame_int_reduce_result(op, md_dtype, running, value)
        };
        write_m_elem(md_dtype, md, idx, running)
      }
    };
    };
    if saturated == 0b1 then ame_set_saturated();
    true
  }
}
