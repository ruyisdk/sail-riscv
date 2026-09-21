// Compare and predicate instruction helpers.

// Manual cmov/sel semantics: the predicate is the NUMERIC comparison of each
// ms1 element against zero, not the raw sign bit of the encoding.  Unsigned
// integers are never negative; signed integers are negative iff their decoded
// value is < 0; floating-point elements use the predicate datatype's order.
// Keep this separate from integer and floating arithmetic so predicate and
// selected-data descriptors may differ.
function ame_predicate_elem_negative(dtype : bits(32),
                                     ms1_val : bits(ame_max_dtype_size)) -> bool = {
  if ame_is_float(dtype) then {
    /* Compare the FP element against +0 using the datatype's own order;
       the comparison flags are dropped (predicated moves do not accrue
       amefflags, matching the architectural definition). */
    let (_, cmp) = ame_float_binary_result(dtype, AME_INT_CMPLT,
                                           0b000, ms1_val, zeros());
    cmp == ones()
  } else if ame_is_signed(dtype) then {
    ame_elem_int(dtype, ms1_val) < 0
  } else {
    false
  }
}

function ame_ew_predicate_m(md_dtype : bits(32), predicate_dtype : bits(32),
                            ms1_dtype : bits(32), md : ameregidx,
                            predicate_reg : ameregidx, ms1 : ameregidx,
                            select_when_sign_set : bool,
                            preserve_dest_when_false : bool) -> bool = {
  if not(ame_datatype_supported(md_dtype) & ame_datatype_supported(predicate_dtype) &
         ame_datatype_supported(ms1_dtype)) then ame_unsupported_result()
  else if md_dtype != ms1_dtype then ame_unsupported_result()
  else {
    let nsq = ame_nsq3(md_dtype, predicate_dtype, ms1_dtype);
    if not(ame_check_formed_operand(md, md_dtype, nsq)) then false
    else if not(ame_check_formed_operand(predicate_reg, predicate_dtype, nsq)) then false
    else if not(ame_check_formed_operand(ms1, ms1_dtype, nsq)) then false
    else {
    let snapshot = ame_snapshot_mregs();
    foreach (e from 0 to (nsq * ame_nelem - 1)) {
      let predicate = ame_predicate_elem_negative(predicate_dtype,
        ame_read_snapshot_elem(snapshot, predicate_dtype, predicate_reg, e));
      let selected = if select_when_sign_set then predicate else not(predicate);
      let result = if selected then ame_read_snapshot_elem(snapshot, ms1_dtype, ms1, e)
        else if preserve_dest_when_false then ame_read_snapshot_elem(snapshot, md_dtype, md, e)
        else zeros();
      write_m_elem(md_dtype, md, e, result)
    };
    true
    }
  }
}
