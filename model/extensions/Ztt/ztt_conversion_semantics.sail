// Integer conversion instruction implementation.

function ame_convert_integer_elem(ms1_dtype : bits(32), ms1_val : bits(ame_max_dtype_size))
  -> bits(ame_max_dtype_size) =
  to_bits_unsafe(ame_max_dtype_size, ame_elem_int(ms1_dtype, ms1_val))

// mconv.ew converts between integer squares; a zero-sized or non-integer
// datatype on either side is not a tuple this instruction covers.
function ame_mconv_accepts(md_dtype : bits(32), ms1_dtype : bits(32)) -> bool =
  ame_dtype_size(md_dtype) != 0 &
  ame_dtype_size(ms1_dtype) != 0 &
  ame_is_integer(md_dtype) &
  ame_is_integer(ms1_dtype)

function ame_mconv_ew(md_dtype : bits(32), ms1_dtype : bits(32),
                      md : ameregidx, ms1 : ameregidx) -> bool = {
  let nsq = ame_nsq2(md_dtype, ms1_dtype);

  if not(ame_mconv_accepts(md_dtype, ms1_dtype)) then
    return ame_unsupported_result();

  if not(ame_unary_formed(nsq, md, md_dtype, ms1, ms1_dtype)) then false
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
