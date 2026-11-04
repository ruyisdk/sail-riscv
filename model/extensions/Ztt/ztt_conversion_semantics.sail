// Integer conversion instruction implementation.

function ame_convert_integer_elem(ms1_dtype : bits(32), ms1_val : bits(ame_max_dtype_size))
  -> bits(ame_max_dtype_size) =
  to_bits_unsafe(ame_max_dtype_size, ame_elem_int(ms1_dtype, ms1_val))

function ame_mconv_ew(md_dtype : bits(32), ms1_dtype : bits(32),
                      md : ameregidx, ms1 : ameregidx) -> bool = {
  let dest_size = ame_dtype_size(md_dtype);
  let src_size = ame_dtype_size(ms1_dtype);
  let nsq = ame_nsq2(md_dtype, ms1_dtype);

  if dest_size == 0 | src_size == 0 then ame_unsupported_result()
  else if not(ame_is_integer(md_dtype) & ame_is_integer(ms1_dtype)) then ame_unsupported_result()
  else if not(ame_check_formed_operand(md, md_dtype, nsq)) then false
  else if not(ame_check_formed_operand(ms1, ms1_dtype, nsq)) then false
  else {
    let snapshot = ame_snapshot_mregs();
    var saturated : bits(1) = 0b0;
    foreach (e from 0 to (nsq * ame_nelem - 1)) {
      let source = ame_read_snapshot_elem(snapshot, ms1_dtype, ms1, e);
      let exact = ame_elem_int(ms1_dtype, source);
      saturated = saturated | bool_to_bit(ame_int_saturates(md_dtype, exact));
      write_m_elem(md_dtype, md, e,
        ame_int_result_from_int(md_dtype, exact))
    };
    if saturated == 0b1 then ame_set_saturated();
    true
  }
}
