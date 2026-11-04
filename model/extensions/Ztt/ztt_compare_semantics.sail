// Compare and predicate instruction helpers.

// Manual cmov/sel semantics: the predicate is the NUMERIC comparison of each
// ms1 element against zero, not the raw sign bit of the encoding.  The
// comparison is the predicate datatype's ordered comparison, so a NaN element
// makes the predicate false and a negative zero compares equal to +0.
// Unsigned integers are never negative; signed integers are compared by their
// decoded value.  Keep this separate from integer and floating arithmetic so
// predicate and selected-data descriptors may differ.
// Decode the boolean produced by `AME_INT_CMPLT`/`AME_INT_CMPGE` on a floating
// datatype, which encodes true as an all-ones *element*.  The element occupies
// the low bits of the container: the 32-bit path zero-extends a 32-bit
// all-ones value (`ame_fp32_result`) while the 16/64-bit and BF16/OCP-FP8
// paths return a container-wide all-ones value, so testing against a
// container-wide `ones()` would only match the latter.  Testing against zero
// decodes the element value regardless of its width.
function ame_float_cmp_is_true(cmp : bits(ame_max_dtype_size)) -> bool =
  cmp != zeros()

function ame_predicate_elem_negative(dtype : bits(32),
                                     ms1_val : bits(ame_max_dtype_size)) -> bool = {
  if ame_is_float(dtype) then {
    /* Compare the FP element against +0 using the datatype's own order;
       the comparison flags are dropped (predicated moves do not accrue
       amefflags, matching the architectural definition). */
    let (_, cmp) = ame_float_binary_result(dtype, AME_INT_CMPLT,
                                           0b000, ms1_val, zeros());
    ame_float_cmp_is_true(cmp)
  } else if ame_is_signed(dtype) then {
    ame_elem_int(dtype, ms1_val) < 0
  } else {
    false
  }
}

// Ordered `ms1_val >= +0`.  This is a separate helper rather than
// `not(ame_predicate_elem_negative(...))` because `not(a < 0)` and `a >= 0`
// disagree for floating-point NaN operands: the manual defines the predicate as
// an ordered comparison, so a NaN element must make the non-negative predicate
// false.  For integer datatypes the two formulations are equivalent.
function ame_predicate_elem_nonnegative(dtype : bits(32),
                                        ms1_val : bits(ame_max_dtype_size)) -> bool = {
  if ame_is_float(dtype) then {
    /* `AME_INT_CMPGE` computes `ms1_val >= +0` with the datatype's own order;
       the comparison flags are dropped for the same reason as above. */
    let (_, cmp) = ame_float_binary_result(dtype, AME_INT_CMPGE,
                                           0b000, ms1_val, zeros());
    ame_float_cmp_is_true(cmp)
  } else if ame_is_signed(dtype) then {
    ame_elem_int(dtype, ms1_val) >= 0
  } else {
    true
  }
}

function ame_ew_predicate_m(md_dtype : bits(32), predicate_dtype : bits(32),
                            ms1_dtype : bits(32), md : ameregidx,
                            predicate_reg : ameregidx, ms1 : ameregidx,
                            select_when_negative : bool,
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
      let predicate_elem = ame_read_snapshot_elem(snapshot, predicate_dtype, predicate_reg, e);
      let selected = if select_when_negative
        then ame_predicate_elem_negative(predicate_dtype, predicate_elem)
        else ame_predicate_elem_nonnegative(predicate_dtype, predicate_elem);
      let result = if selected then ame_read_snapshot_elem(snapshot, ms1_dtype, ms1, e)
        else if preserve_dest_when_false then ame_read_snapshot_elem(snapshot, md_dtype, md, e)
        else zeros();
      write_m_elem(md_dtype, md, e, result)
    };
    true
    }
  }
}
