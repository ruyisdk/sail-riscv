// Elementwise arithmetic and log/exp instruction implementations.

/* Mixed integer operands are interpreted in their source datatypes. Numeric
   operations retain that exact value until destination rounding/writeback. */
function ame_int_binary_mixed_result(op : ame_int_binary_op,
                                     md_dtype : bits(32),
                                     lhs_dtype : bits(32),
                                     rhs_dtype : bits(32),
                                     ms1_val : bits(ame_max_dtype_size),
                                     ms2_val : bits(ame_max_dtype_size))
  -> (bool, bits(ame_max_dtype_size)) = {
  let lhs_int = ame_elem_int(lhs_dtype, ms1_val);
  let rhs_int = ame_elem_int(rhs_dtype, ms2_val);
  match op {
    AME_INT_ADD            => ame_int_result_with_saturation(md_dtype, lhs_int + rhs_int),
    AME_INT_SUB_LHS_RHS    => ame_int_result_with_saturation(md_dtype, lhs_int - rhs_int),
    AME_INT_SUB_RHS_LHS    => ame_int_result_with_saturation(md_dtype, rhs_int - lhs_int),
    AME_INT_AND            => (false, ame_int_result_from_int(md_dtype, lhs_int) & ame_int_result_from_int(md_dtype, rhs_int)),
    AME_INT_ANDNOT         => (false, ame_int_result_from_int(md_dtype, lhs_int) & ~(ame_int_result_from_int(md_dtype, rhs_int))),
    AME_INT_OR             => (false, ame_int_result_from_int(md_dtype, lhs_int) | ame_int_result_from_int(md_dtype, rhs_int)),
    AME_INT_ORNOT          => (false, ame_int_result_from_int(md_dtype, lhs_int) | ~(ame_int_result_from_int(md_dtype, rhs_int))),
    AME_INT_XOR            => (false, ame_int_result_from_int(md_dtype, lhs_int) ^ ame_int_result_from_int(md_dtype, rhs_int)),
    AME_INT_MAX            => ame_int_result_with_saturation(md_dtype, max(lhs_int, rhs_int)),
    AME_INT_MIN            => ame_int_result_with_saturation(md_dtype, min(lhs_int, rhs_int)),
    AME_INT_ABSDIFF        => ame_int_result_with_saturation(md_dtype, abs_int(lhs_int - rhs_int)),
    AME_INT_HDIFF_RHS_LHS  => ame_int_result_with_saturation(md_dtype, ame_int_round_right(md_dtype, rhs_int - lhs_int, 1)),
    AME_INT_HDIFF_LHS_RHS  => ame_int_result_with_saturation(md_dtype, ame_int_round_right(md_dtype, lhs_int - rhs_int, 1)),
    AME_INT_MEAN           => ame_int_result_with_saturation(md_dtype, ame_int_round_right(md_dtype, lhs_int + rhs_int, 1)),
    AME_INT_MUL            => ame_int_result_with_saturation(md_dtype, lhs_int * rhs_int),
    AME_INT_MULNEG         => ame_int_result_with_saturation(md_dtype, 0 - (lhs_int * rhs_int)),
    AME_INT_CMPGE          => (false, if lhs_int >= rhs_int then ones() else zeros()),
    AME_INT_CMPLT          => (false, if lhs_int < rhs_int then ones() else zeros())
  }
}

function ame_int_ternary_mixed_result(op : ame_int_ternary_op,
                                      md_dtype : bits(32),
                                      lhs_dtype : bits(32),
                                      rhs_dtype : bits(32),
                                      md_val : bits(ame_max_dtype_size),
                                      ms1_val : bits(ame_max_dtype_size),
                                      ms2_val : bits(ame_max_dtype_size))
  -> (bool, bits(ame_max_dtype_size)) = {
  let dest_int = ame_elem_int(md_dtype, md_val);
  let lhs_int = ame_elem_int(lhs_dtype, ms1_val);
  let rhs_int = ame_elem_int(rhs_dtype, ms2_val);
  match op {
    AME_INT_MULACC => ame_int_result_with_saturation(md_dtype,
      dest_int + lhs_int * rhs_int),
    AME_INT_MULNACC => ame_int_result_with_saturation(md_dtype,
      dest_int - lhs_int * rhs_int),
    AME_INT_MULADD => ame_int_result_with_saturation(md_dtype,
      lhs_int + rhs_int * dest_int),
    AME_INT_MULSUB => ame_int_result_with_saturation(md_dtype,
      lhs_int - rhs_int * dest_int)
  }
}

function ame_int_unary_result(op : ame_int_unary_op, dtype : bits(32),
                              ms1_val : bits(ame_max_dtype_size))
  -> (bool, bits(ame_max_dtype_size)) = {
  let value_int = ame_elem_int(dtype, ms1_val);
  match op {
    AME_INT_ABS => ame_int_result_with_saturation(dtype, if value_int < 0 then 0 - value_int else value_int)
  }
}

function ame_scalar_integer_data_value(md_dtype : bits(32), raw : xlenbits)
  -> option(bits(ame_max_dtype_size)) = {
  let scalar_dtype = amestype;
  if not(ame_datatype_supported(scalar_dtype) & ame_is_integer(scalar_dtype) &
         ame_valid_int_elementwise_dtype(md_dtype)) then None()
  else {
    let raw_element : bits(ame_max_dtype_size) = zero_extend(ame_max_dtype_size, raw);
    let scalar_value = ame_elem_int(scalar_dtype, raw_element);
    Some(ame_int_result_from_int(md_dtype, scalar_value))
  }
}

function ame_scalar_float_data_value(md_dtype : bits(32), raw : xlenbits)
  -> option(bits(ame_max_dtype_size)) = {
  let scalar_dtype = amestype;
  if not(ame_datatype_supported(scalar_dtype) & ame_is_float(scalar_dtype) &
         ame_valid_softfloat_ew_dtype(md_dtype) &
         ame_dtype_without_rounding(scalar_dtype) == ame_dtype_without_rounding(md_dtype)) then None()
  else match ame_dtype_size(scalar_dtype) {
    8  => Some(zero_extend(ame_max_dtype_size, zero_extend(64, raw)[7 .. 0])),
    16 => Some(zero_extend(ame_max_dtype_size, zero_extend(64, raw)[15 .. 0])),
    32 => Some(zero_extend(ame_max_dtype_size, zero_extend(64, raw)[31 .. 0])),
    64 => Some(zero_extend(ame_max_dtype_size, zero_extend(64, raw)[63 .. 0])),
    _  => None()
  }
}

function ame_float_binary_supported(op : ame_int_binary_op) -> bool =
  match op {
    AME_INT_ADD           => true,
    AME_INT_SUB_LHS_RHS   => true,
    AME_INT_SUB_RHS_LHS   => true,
    AME_INT_MAX           => true,
    AME_INT_MIN           => true,
    AME_INT_ABSDIFF       => true,
    AME_INT_MUL           => true,
    AME_INT_MULNEG        => true,
    AME_INT_CMPGE         => true,
    AME_INT_CMPLT         => true,
    _                     => false
  }

function ame_float_ternary_supported(op : ame_int_ternary_op) -> bool =
  match op {
    AME_INT_MULACC  => true,
    AME_INT_MULNACC => true,
    AME_INT_MULADD  => true,
    AME_INT_MULSUB  => true
  }

function ame_fp32_unary_supported(op : ame_int_unary_op) -> bool =
  match op {
    AME_INT_ABS => true
  }

function ame_int_floor_log2_abs(value : int) -> int = {
  let magnitude = abs_int(value);
  var result : int = 0;
  foreach (bit from 0 to (ame_max_dtype_size - 1)) {
    if magnitude >= 2 ^ bit then result = bit
  };
  result
}

function ame_int_scale_pow2(value : int, exponent : int) -> int =
  if exponent >= 0 then
    value * (2 ^ exponent)
  else
    quot_round_zero(value, 2 ^ (0 - exponent))

function ame_int_logexp_exact_result(op : ame_int_logexp_op, dtype : bits(32),
                                     md_val : bits(ame_max_dtype_size),
                                     ms1_val : bits(ame_max_dtype_size),
                                     ms2_val : bits(ame_max_dtype_size))
  -> int = {
  let dest_int = ame_elem_int(dtype, md_val);
  let lhs_int = ame_elem_int(dtype, ms1_val);
  let rhs_int = ame_elem_int(dtype, ms2_val);
  let result : int = match op {
    AME_INT_EXP2     => if lhs_int < 0 then 0 else 2 ^ lhs_int,
    AME_INT_LOG2     => ame_int_floor_log2_abs(lhs_int),
    AME_INT_LDEXP    => ame_int_scale_pow2(lhs_int, rhs_int),
    AME_INT_LDEXPACC => dest_int + ame_int_scale_pow2(lhs_int, rhs_int),
    AME_INT_RDEXP    => ame_int_scale_pow2(lhs_int, 0 - rhs_int),
    AME_INT_RDEXPACC => dest_int + ame_int_scale_pow2(lhs_int, 0 - rhs_int),
    AME_INT_LOG2SUB  => ame_int_floor_log2_abs(lhs_int) - rhs_int,
    AME_INT_SUBLOG2  => rhs_int - ame_int_floor_log2_abs(lhs_int)
  };
  result
}

function ame_int_logexp_result(op : ame_int_logexp_op, dtype : bits(32),
                               md_val : bits(ame_max_dtype_size),
                               ms1_val : bits(ame_max_dtype_size),
                               ms2_val : bits(ame_max_dtype_size))
  -> (bool, bits(ame_max_dtype_size)) = {
  let result = ame_int_logexp_exact_result(op, dtype, md_val, ms1_val, ms2_val);
  ame_int_result_with_saturation(dtype, result)
}

function ame_binary_is_bitwise(op : ame_int_binary_op) -> bool =
  op == AME_INT_AND | op == AME_INT_ANDNOT | op == AME_INT_OR |
  op == AME_INT_ORNOT | op == AME_INT_XOR

function ame_binary_is_comparison(op : ame_int_binary_op) -> bool =
  op == AME_INT_CMPGE | op == AME_INT_CMPLT

function ame_binary_is_minmax(op : ame_int_binary_op) -> bool =
  op == AME_INT_MIN | op == AME_INT_MAX

function ame_integer_binary_m_tuple_supported(op : ame_int_binary_op,
                                               md_dtype : bits(32),
                                               ms1_dtype : bits(32),
                                               ms2_dtype : bits(32)) -> bool =
  if ame_binary_is_bitwise(op) | ame_binary_is_minmax(op) then
    md_dtype == ms1_dtype & md_dtype == ms2_dtype
  else true

function ame_integer_binary_x_tuple_supported(op : ame_int_binary_op,
                                               md_dtype : bits(32),
                                               ms2_dtype : bits(32)) -> bool =
  if ame_binary_is_bitwise(op) | ame_binary_is_minmax(op) then
    md_dtype == ms2_dtype & md_dtype == amestype
  else true

/* Comparisons are the one binary family whose result class differs from its
   source class.  Keep them out of the arithmetic dispatch so floating inputs
   can never be reinterpreted using an integer destination descriptor. */
function ame_ew_compare_m(md_dtype : bits(32), ms1_dtype : bits(32),
                          ms2_dtype : bits(32), md : ameregidx,
                          ms1 : ameregidx, ms2 : ameregidx,
                          op : ame_int_binary_op) -> bool = {
  let nsq = ame_nsq3(md_dtype, ms1_dtype, ms2_dtype);
  if not(ame_valid_int_elementwise_dtype(md_dtype)) then ame_unsupported_result()
  else if ame_valid_int_elementwise_dtype(ms1_dtype) &
          ame_valid_int_elementwise_dtype(ms2_dtype) then {
    if not(ame_check_formed_operand(md, md_dtype, nsq)) then false
    else if not(ame_check_formed_operand(ms1, ms1_dtype, nsq)) then false
    else if not(ame_check_formed_operand(ms2, ms2_dtype, nsq)) then false
    else {
      let snapshot = ame_snapshot_mregs();
      foreach (e from 0 to (nsq * ame_nelem - 1)) {
        let (_, result) = ame_int_binary_mixed_result(op, md_dtype,
          ms1_dtype, ms2_dtype,
          ame_read_snapshot_elem(snapshot, ms1_dtype, ms1, e),
          ame_read_snapshot_elem(snapshot, ms2_dtype, ms2, e));
        write_m_elem(md_dtype, md, e, result)
      };
      true
    }
  }
  else if ame_valid_softfloat_ew_dtype(ms1_dtype) &
          ame_valid_softfloat_ew_dtype(ms2_dtype) &
          ame_same_float_format2(ms1_dtype, ms2_dtype) then {
    if not(ame_check_formed_operand(md, md_dtype, nsq)) then false
    else if not(ame_check_formed_operand(ms1, ms1_dtype, nsq)) then false
    else if not(ame_check_formed_operand(ms2, ms2_dtype, nsq)) then false
    else match ame_fp_rounding_mode(ms1_dtype) {
      None() => ame_unsupported_result(),
      Some(rm) => {
        let snapshot = ame_snapshot_mregs();
        var flags : bits_fflags = zeros();
        foreach (e from 0 to (nsq * ame_nelem - 1)) {
          let (element_flags, result) = ame_float_binary_result(ms1_dtype,
            op, rm,
            ame_read_snapshot_elem(snapshot, ms1_dtype, ms1, e),
            ame_read_snapshot_elem(snapshot, ms2_dtype, ms2, e));
          flags = flags | element_flags;
          write_m_elem(md_dtype, md, e, result)
        };
        accrue_amefflags(flags);
        true
      }
    }
  }
  else ame_unsupported_result()
}

function ame_ew_compare_x(md_dtype : bits(32), ms2_dtype : bits(32),
                          md : ameregidx, rs1_val : xlenbits,
                          ms2 : ameregidx, op : ame_int_binary_op) -> bool = {
  let nsq = ame_nsq2(md_dtype, ms2_dtype);
  if not(ame_valid_int_elementwise_dtype(md_dtype)) then ame_unsupported_result()
  else if ame_valid_int_elementwise_dtype(ms2_dtype) then {
    if not(ame_check_formed_operand(md, md_dtype, nsq)) then false
    else if not(ame_check_formed_operand(ms2, ms2_dtype, nsq)) then false
    else if not(ame_datatype_supported(amestype) &
                ame_is_integer(amestype)) then ame_unsupported_result()
    else {
      let raw_element : bits(ame_max_dtype_size) = zero_extend(ame_max_dtype_size, rs1_val);
      let ms1_val = ame_int_result_from_int(ms2_dtype,
        ame_elem_int(amestype, raw_element));
      let snapshot = ame_snapshot_mregs();
      foreach (e from 0 to (nsq * ame_nelem - 1)) {
        let (_, result) = ame_int_binary_result(op, ms2_dtype, ms1_val,
          ame_read_snapshot_elem(snapshot, ms2_dtype, ms2, e));
        write_m_elem(md_dtype, md, e, result)
      };
      true
    }
  }
  else if ame_valid_softfloat_ew_dtype(ms2_dtype) then {
    if not(ame_check_formed_operand(md, md_dtype, nsq)) then false
    else if not(ame_check_formed_operand(ms2, ms2_dtype, nsq)) then false
    else
    match (ame_scalar_float_data_value(ms2_dtype, rs1_val),
           ame_fp_rounding_mode(ms2_dtype)) {
      (Some(ms1_val), Some(rm)) => {
        let snapshot = ame_snapshot_mregs();
        var flags : bits_fflags = zeros();
        foreach (e from 0 to (nsq * ame_nelem - 1)) {
          let (element_flags, result) = ame_float_binary_result(ms2_dtype,
            op, rm, ms1_val,
            ame_read_snapshot_elem(snapshot, ms2_dtype, ms2, e));
          flags = flags | element_flags;
          write_m_elem(md_dtype, md, e, result)
        };
        accrue_amefflags(flags);
        true
      },
      _ => ame_unsupported_result()
    }
  }
  else ame_unsupported_result()
}

function ame_ew_binary_m(md_dtype : bits(32), ms1_dtype : bits(32),
                         ms2_dtype : bits(32), md : ameregidx,
                         ms1 : ameregidx, ms2 : ameregidx,
                         op : ame_int_binary_op) -> bool = {
  let nsq = ame_nsq3(md_dtype, ms1_dtype, ms2_dtype);

  if ame_binary_is_comparison(op) then
    ame_ew_compare_m(md_dtype, ms1_dtype, ms2_dtype, md,
      ms1, ms2, op)
  else if ame_valid_int_elementwise_dtype(md_dtype) & ame_valid_int_elementwise_dtype(ms1_dtype) & ame_valid_int_elementwise_dtype(ms2_dtype) then {
    if not(ame_integer_binary_m_tuple_supported(op, md_dtype, ms1_dtype, ms2_dtype)) then
      ame_unsupported_result()
    else if not(ame_check_formed_operand(md, md_dtype, nsq)) then false
    else if not(ame_check_formed_operand(ms1, ms1_dtype, nsq)) then false
    else if not(ame_check_formed_operand(ms2, ms2_dtype, nsq)) then false
    else {
      let snapshot = ame_snapshot_mregs();
      var saturated : bits(1) = 0b0;

      foreach (e from 0 to (nsq * ame_nelem - 1)) {
        let ms1_val = ame_read_snapshot_elem(snapshot, ms1_dtype, ms1, e);
        let ms2_val = ame_read_snapshot_elem(snapshot, ms2_dtype, ms2, e);
        let (element_saturated, result) =
          ame_int_binary_mixed_result(op, md_dtype, ms1_dtype, ms2_dtype, ms1_val, ms2_val);
        saturated = saturated | bool_to_bit(element_saturated);
        write_m_elem(md_dtype, md, e, result)
      };
      if saturated == 0b1 then ame_set_saturated();
      true
    }
  }
  else if ame_valid_softfloat_ew_dtype(md_dtype) & ame_valid_softfloat_ew_dtype(ms1_dtype) & ame_valid_softfloat_ew_dtype(ms2_dtype) & ame_float_binary_supported(op) then {
    if not(ame_same_float_format3(md_dtype, ms1_dtype, ms2_dtype)) then
      ame_unsupported_result()
    else if not(ame_check_formed_operand(md, md_dtype, nsq)) then false
    else if not(ame_check_formed_operand(ms1, ms1_dtype, nsq)) then false
    else if not(ame_check_formed_operand(ms2, ms2_dtype, nsq)) then false
    else match ame_fp_rounding_mode(md_dtype) {
      None() => ame_unsupported_result(),
      Some(rm) => {
        let snapshot = ame_snapshot_mregs();
        var flags : bits_fflags = zeros();

        foreach (e from 0 to (nsq * ame_nelem - 1)) {
          let ms1_val = ame_read_snapshot_elem(snapshot, ms1_dtype, ms1, e);
          let ms2_val = ame_read_snapshot_elem(snapshot, ms2_dtype, ms2, e);
          let (fflags, result) = ame_float_binary_result(md_dtype, op, rm, ms1_val, ms2_val);
          flags = flags | fflags;
          write_m_elem(md_dtype, md, e, result)
        };
        accrue_amefflags(flags);
        true
      }
    }
  }
  else ame_unsupported_result()
}

function ame_ew_binary_x(md_dtype : bits(32), ms2_dtype : bits(32),
                         md : ameregidx, rs1_val : xlenbits,
                         ms2 : ameregidx, op : ame_int_binary_op) -> bool = {
  let nsq = ame_nsq2(md_dtype, ms2_dtype);

  if ame_binary_is_comparison(op) then
    ame_ew_compare_x(md_dtype, ms2_dtype, md, rs1_val, ms2, op)
  else if ame_valid_int_elementwise_dtype(md_dtype) & ame_valid_int_elementwise_dtype(ms2_dtype) then {
    if not(ame_integer_binary_x_tuple_supported(op, md_dtype, ms2_dtype)) then
      ame_unsupported_result()
    else if not(ame_datatype_supported(amestype) &
                ame_is_integer(amestype)) then ame_unsupported_result()
    else {
      let raw_element : bits(ame_max_dtype_size) = zero_extend(ame_max_dtype_size, rs1_val);
      let ms1_val = ame_int_result_from_int(ms2_dtype,
        ame_elem_int(amestype, raw_element));
        if not(ame_check_formed_operand(md, md_dtype, nsq)) then false
        else if not(ame_check_formed_operand(ms2, ms2_dtype, nsq)) then false
        else {
          let snapshot = ame_snapshot_mregs();
          var saturated : bits(1) = 0b0;

          foreach (e from 0 to (nsq * ame_nelem - 1)) {
            let ms2_val = ame_read_snapshot_elem(snapshot, ms2_dtype, ms2, e);
            let (element_saturated, result) = ame_int_binary_mixed_result(
              op, md_dtype, ms2_dtype, ms2_dtype, ms1_val, ms2_val);
            saturated = saturated | bool_to_bit(element_saturated);
            write_m_elem(md_dtype, md, e, result)
          };

          if saturated == 0b1 then ame_set_saturated();
          true
        }
    }
  }
  else if ame_valid_softfloat_ew_dtype(md_dtype) & ame_valid_softfloat_ew_dtype(ms2_dtype) & ame_float_binary_supported(op) then {
    if not(ame_same_float_format2(md_dtype, ms2_dtype)) then
      ame_unsupported_result()
    else match ame_scalar_float_data_value(md_dtype, rs1_val) {
      None() => { ame_set_unsupported(); true },
      Some(ms1_val) => {
        if not(ame_check_formed_operand(md, md_dtype, nsq)) then false
        else if not(ame_check_formed_operand(ms2, ms2_dtype, nsq)) then false
        else match ame_fp_rounding_mode(md_dtype) {
          None() => { ame_set_unsupported(); true },
          Some(rm) => {
            let snapshot = ame_snapshot_mregs();
            var flags : bits_fflags = zeros();

            foreach (e from 0 to (nsq * ame_nelem - 1)) {
              let ms2_val = ame_read_snapshot_elem(snapshot, ms2_dtype, ms2, e);
              let (fflags, result) = ame_float_binary_result(md_dtype, op, rm, ms1_val, ms2_val);
              flags = flags | fflags;
              write_m_elem(md_dtype, md, e, result)
            };

            accrue_amefflags(flags);
            true
          }
        }
      }
    }
  }
  else ame_unsupported_result()
}

function ame_ew_ternary_m(md_dtype : bits(32), ms1_dtype : bits(32),
                          ms2_dtype : bits(32), md : ameregidx,
                          ms1 : ameregidx, ms2 : ameregidx,
                          op : ame_int_ternary_op) -> bool = {
  let nsq = ame_nsq3(md_dtype, ms1_dtype, ms2_dtype);

  if ame_valid_int_elementwise_dtype(md_dtype) & ame_valid_int_elementwise_dtype(ms1_dtype) & ame_valid_int_elementwise_dtype(ms2_dtype) then {
    if not(ame_check_formed_operand(md, md_dtype, nsq)) then false
    else if not(ame_check_formed_operand(ms1, ms1_dtype, nsq)) then false
    else if not(ame_check_formed_operand(ms2, ms2_dtype, nsq)) then false
    else {
      let snapshot = ame_snapshot_mregs();
      var saturated : bits(1) = 0b0;

      foreach (e from 0 to (nsq * ame_nelem - 1)) {
        let md_val = ame_read_snapshot_elem(snapshot, md_dtype, md, e);
        let ms1_val = ame_read_snapshot_elem(snapshot, ms1_dtype, ms1, e);
        let ms2_val = ame_read_snapshot_elem(snapshot, ms2_dtype, ms2, e);
        let (element_saturated, result) = ame_int_ternary_mixed_result(
          op, md_dtype, ms1_dtype, ms2_dtype, md_val, ms1_val, ms2_val);
        saturated = saturated | bool_to_bit(element_saturated);
        write_m_elem(md_dtype, md, e, result)
      };
      if saturated == 0b1 then ame_set_saturated();
      true
    }
  }
  else if ame_valid_softfloat_ew_dtype(md_dtype) & ame_valid_softfloat_ew_dtype(ms1_dtype) & ame_valid_softfloat_ew_dtype(ms2_dtype) & ame_float_ternary_supported(op) then {
    if not(ame_same_float_format3(md_dtype, ms1_dtype, ms2_dtype)) then
      ame_unsupported_result()
    else if not(ame_check_formed_operand(md, md_dtype, nsq)) then false
    else if not(ame_check_formed_operand(ms1, ms1_dtype, nsq)) then false
    else if not(ame_check_formed_operand(ms2, ms2_dtype, nsq)) then false
    else match ame_fp_rounding_mode(md_dtype) {
      None() => ame_unsupported_result(),
      Some(rm) => {
        let snapshot = ame_snapshot_mregs();
        var flags : bits_fflags = zeros();

        foreach (e from 0 to (nsq * ame_nelem - 1)) {
          let md_val = ame_read_snapshot_elem(snapshot, md_dtype, md, e);
          let ms1_val = ame_read_snapshot_elem(snapshot, ms1_dtype, ms1, e);
          let ms2_val = ame_read_snapshot_elem(snapshot, ms2_dtype, ms2, e);
          let (fflags, result) = ame_float_ternary_result(md_dtype, op, rm, md_val, ms1_val, ms2_val);
          flags = flags | fflags;
          write_m_elem(md_dtype, md, e, result)
        };
        accrue_amefflags(flags);
        true
      }
    }
  }
  else ame_unsupported_result()
}

function ame_ew_ternary_x(md_dtype : bits(32), ms2_dtype : bits(32),
                          md : ameregidx, rs1_val : xlenbits,
                          ms2 : ameregidx, op : ame_int_ternary_op) -> bool = {
  let nsq = ame_nsq2(md_dtype, ms2_dtype);

  if ame_valid_int_elementwise_dtype(md_dtype) & ame_valid_int_elementwise_dtype(ms2_dtype) then {
    if not(ame_datatype_supported(amestype) &
           ame_is_integer(amestype)) then ame_unsupported_result()
    else {
      let raw_element : bits(ame_max_dtype_size) = zero_extend(ame_max_dtype_size, rs1_val);
      let ms1_val = ame_int_result_from_int(ms2_dtype,
        ame_elem_int(amestype, raw_element));
        if not(ame_check_formed_operand(md, md_dtype, nsq)) then false
        else if not(ame_check_formed_operand(ms2, ms2_dtype, nsq)) then false
        else {
          let snapshot = ame_snapshot_mregs();
          var saturated : bits(1) = 0b0;

          foreach (e from 0 to (nsq * ame_nelem - 1)) {
            let md_val = ame_read_snapshot_elem(snapshot, md_dtype, md, e);
            let ms2_val = ame_read_snapshot_elem(snapshot, ms2_dtype, ms2, e);
            let (element_saturated, result) = ame_int_ternary_mixed_result(
              op, md_dtype, ms2_dtype, ms2_dtype, md_val, ms1_val, ms2_val);
            saturated = saturated | bool_to_bit(element_saturated);
            write_m_elem(md_dtype, md, e, result)
          };

          if saturated == 0b1 then ame_set_saturated();
          true
        }
    }
  }
  else if ame_valid_softfloat_ew_dtype(md_dtype) & ame_valid_softfloat_ew_dtype(ms2_dtype) & ame_float_ternary_supported(op) then {
    if not(ame_same_float_format2(md_dtype, ms2_dtype)) then
      ame_unsupported_result()
    else match (ame_scalar_float_data_value(md_dtype, rs1_val), ame_fp_rounding_mode(md_dtype)) {
      (None(), _) => { ame_set_unsupported(); true },
      (_, None()) => { ame_set_unsupported(); true },
      (Some(ms1_val), Some(rm)) => {
        if not(ame_check_formed_operand(md, md_dtype, nsq)) then false
        else if not(ame_check_formed_operand(ms2, ms2_dtype, nsq)) then false
        else {
          let snapshot = ame_snapshot_mregs();
          var flags : bits_fflags = zeros();

          foreach (e from 0 to (nsq * ame_nelem - 1)) {
            let md_val = ame_read_snapshot_elem(snapshot, md_dtype, md, e);
            let ms2_val = ame_read_snapshot_elem(snapshot, ms2_dtype, ms2, e);
            let (fflags, result) = ame_float_ternary_result(md_dtype, op, rm, md_val, ms1_val, ms2_val);
            flags = flags | fflags;
            write_m_elem(md_dtype, md, e, result)
          };

          accrue_amefflags(flags);
          true
        }
      }
    }
  }
  else ame_unsupported_result()
}

function ame_ew_unary_m(md_dtype : bits(32), ms1_dtype : bits(32),
                        md : ameregidx, ms1 : ameregidx,
                        op : ame_int_unary_op) -> bool = {
  let dest_size = ame_dtype_size(md_dtype);
  let src_size = ame_dtype_size(ms1_dtype);
  let nsq = ame_nsq2(md_dtype, ms1_dtype);

  if ame_valid_int_elementwise_dtype(md_dtype) & ame_valid_int_elementwise_dtype(ms1_dtype) then {
    if dest_size != src_size | ame_is_signed(md_dtype) != ame_is_signed(ms1_dtype) then
      ame_unsupported_result()
    else if not(ame_check_formed_operand(md, md_dtype, nsq)) then false
    else if not(ame_check_formed_operand(ms1, ms1_dtype, nsq)) then false
    else {
      let snapshot = ame_snapshot_mregs();
      var saturated : bits(1) = 0b0;

      foreach (e from 0 to (nsq * ame_nelem - 1)) {
        let value = ame_read_snapshot_elem(snapshot, ms1_dtype, ms1, e);
        let (element_saturated, result) = ame_int_unary_result(op, md_dtype, value);
        saturated = saturated | bool_to_bit(element_saturated);
        write_m_elem(md_dtype, md, e, result)
      };
      if saturated == 0b1 then ame_set_saturated();
      true
    }
  }
  else if ame_valid_softfloat_ew_dtype(md_dtype) & ame_valid_softfloat_ew_dtype(ms1_dtype) & ame_fp32_unary_supported(op) then {
    if not(ame_same_float_format2(md_dtype, ms1_dtype)) then
      ame_unsupported_result()
    else if not(ame_check_formed_operand(md, md_dtype, nsq)) then false
    else if not(ame_check_formed_operand(ms1, ms1_dtype, nsq)) then false
    else {
      let snapshot = ame_snapshot_mregs();
      var flags : bits_fflags = zeros();

      foreach (e from 0 to (nsq * ame_nelem - 1)) {
        let value = ame_read_snapshot_elem(snapshot, ms1_dtype, ms1, e);
        let (fflags, result) = ame_float_unary_result(md_dtype, op, value);
        flags = flags | fflags;
        write_m_elem(md_dtype, md, e, result)
      };
      accrue_amefflags(flags);
      true
    }
  }
  else ame_unsupported_result()
}

function ame_logexp_unary_m(md_dtype : bits(32), ms1_dtype : bits(32),
                            md : ameregidx, ms1 : ameregidx,
                            op : ame_int_logexp_op) -> bool = {
  let dest_size = ame_dtype_size(md_dtype);
  let src_size = ame_dtype_size(ms1_dtype);
  let nsq = ame_nsq2(md_dtype, ms1_dtype);

  if ame_valid_softfloat_ew_dtype(md_dtype) & ame_valid_softfloat_ew_dtype(ms1_dtype) &
     (op == AME_INT_EXP2 | op == AME_INT_LOG2) then {
    // mexp2/mlog2 with floating-point data: the transcendental is evaluated
    // with the destination datatype rounding mode and only amefflags is
    // accrued (never the integer amexsat sticky bit).
    if not(ame_same_float_format2(md_dtype, ms1_dtype)) then
      ame_unsupported_result()
    else if not(ame_check_formed_operand(md, md_dtype, nsq)) then false
    else if not(ame_check_formed_operand(ms1, ms1_dtype, nsq)) then false
    else match ame_fp_rounding_mode(md_dtype) {
      None() => ame_unsupported_result(),
      Some(rm) => {
        let snapshot = ame_snapshot_mregs();
        var flags : bits_fflags = zeros();

        foreach (e from 0 to (nsq * ame_nelem - 1)) {
          let value = ame_read_snapshot_elem(snapshot, ms1_dtype, ms1, e);
          let (fflags, result) = ame_float_logexp_unary_result(md_dtype, op, rm, value);
          flags = flags | fflags;
          write_m_elem(md_dtype, md, e, result)
        };

        accrue_amefflags(flags);
        true
      }
    }
  }
  else if not(ame_valid_int_elementwise_dtype(md_dtype) & ame_valid_int_elementwise_dtype(ms1_dtype)) then
    ame_unsupported_result()
  else if dest_size != src_size | ame_is_signed(md_dtype) != ame_is_signed(ms1_dtype) then
    ame_unsupported_result()
  else if not(ame_check_formed_operand(md, md_dtype, nsq)) then false
  else if not(ame_check_formed_operand(ms1, ms1_dtype, nsq)) then false
  else {
    let snapshot = ame_snapshot_mregs();
    var saturated : bits(1) = 0b0;

    foreach (e from 0 to (nsq * ame_nelem - 1)) {
      let value = ame_read_snapshot_elem(snapshot, ms1_dtype, ms1, e);
      let (element_saturated, result) =
        ame_int_logexp_result(op, md_dtype, zeros(), value, value);
      saturated = saturated | bool_to_bit(element_saturated);
      write_m_elem(md_dtype, md, e, result)
    };

    if saturated == 0b1 then ame_set_saturated();
    true
  }
}

function ame_logexp_binary_m(md_dtype : bits(32), ms1_dtype : bits(32),
                             ms2_dtype : bits(32), md : ameregidx,
                             ms1 : ameregidx, ms2 : ameregidx,
                             op : ame_int_logexp_op) -> bool = {
  let dest_size = ame_dtype_size(md_dtype);
  let src1_size = ame_dtype_size(ms1_dtype);
  let src2_size = ame_dtype_size(ms2_dtype);
  let nsq = max(ame_pack_factor(dest_size),
                max(ame_pack_factor(src1_size), ame_pack_factor(src2_size)));

  let ldexp_float =
    (op == AME_INT_LDEXP | op == AME_INT_LDEXPACC |
     op == AME_INT_RDEXP | op == AME_INT_RDEXPACC) &
    ame_valid_softfloat_ew_dtype(md_dtype) & ame_valid_softfloat_ew_dtype(ms1_dtype) &
    ame_valid_int_elementwise_dtype(ms2_dtype) & ame_same_float_format2(md_dtype, ms1_dtype);
  let log2bias_float =
    ame_valid_softfloat_ew_dtype(md_dtype) & ame_valid_softfloat_ew_dtype(ms1_dtype) &
    ame_valid_softfloat_ew_dtype(ms2_dtype) & ame_same_float_format3(md_dtype, ms1_dtype, ms2_dtype);

  if ldexp_float then {
    // mldexp/mldexpacc/mrdexp/mrdexpacc with floating-point data and an
    // integer exponent operand.  The exact product is rounded a single time
    // to the destination datatype; only amefflags is accrued.
    if not(ame_check_formed_operand(md, md_dtype, nsq)) then false
    else if not(ame_check_formed_operand(ms1, ms1_dtype, nsq)) then false
    else if not(ame_check_formed_operand(ms2, ms2_dtype, nsq)) then false
    else match ame_fp_rounding_mode(md_dtype) {
      None() => ame_unsupported_result(),
      Some(rm) => {
        let snapshot = ame_snapshot_mregs();
        var flags : bits_fflags = zeros();

        foreach (e from 0 to (nsq * ame_nelem - 1)) {
          let md_val = ame_read_snapshot_elem(snapshot, md_dtype, md, e);
          let ms1_val = ame_read_snapshot_elem(snapshot, ms1_dtype, ms1, e);
          let ms2_val = ame_read_snapshot_elem(snapshot, ms2_dtype, ms2, e);
          let exp_value = ame_elem_int(ms2_dtype, ms2_val);
          let (fflags, result) = ame_fp_ldexp_result(md_dtype, rm,
            op == AME_INT_LDEXPACC | op == AME_INT_RDEXPACC,
            op == AME_INT_RDEXP | op == AME_INT_RDEXPACC,
            ms1_val, md_val, exp_value);
          flags = flags | fflags;
          write_m_elem(md_dtype, md, e, result)
        };

        accrue_amefflags(flags);
        true
      }
    }
  }
  else if log2bias_float then {
    // mlog2sub/msublog2 with floating-point data: approximated in FP32.
    if not(op == AME_INT_LOG2SUB | op == AME_INT_SUBLOG2) then
      ame_unsupported_result()
    else if not(ame_check_formed_operand(md, md_dtype, nsq)) then false
    else if not(ame_check_formed_operand(ms1, ms1_dtype, nsq)) then false
    else if not(ame_check_formed_operand(ms2, ms2_dtype, nsq)) then false
    else match ame_fp_rounding_mode(md_dtype) {
      None() => ame_unsupported_result(),
      Some(rm) => {
        let snapshot = ame_snapshot_mregs();
        var flags : bits_fflags = zeros();

        foreach (e from 0 to (nsq * ame_nelem - 1)) {
          let ms1_val = ame_read_snapshot_elem(snapshot, ms1_dtype, ms1, e);
          let ms2_val = ame_read_snapshot_elem(snapshot, ms2_dtype, ms2, e);
          let (fflags, result) = ame_float_log2bias_result(md_dtype, op, rm, ms1_val, ms2_val);
          flags = flags | fflags;
          write_m_elem(md_dtype, md, e, result)
        };

        accrue_amefflags(flags);
        true
      }
    }
  }
  else if not(ame_valid_int_elementwise_dtype(md_dtype) & ame_valid_int_elementwise_dtype(ms1_dtype) & ame_valid_int_elementwise_dtype(ms2_dtype)) then
    ame_unsupported_result()
  else if dest_size != src1_size | dest_size != src2_size |
          ame_is_signed(md_dtype) != ame_is_signed(ms1_dtype) |
          ame_is_signed(md_dtype) != ame_is_signed(ms2_dtype) then
    ame_unsupported_result()
  else if not(ame_check_formed_operand(md, md_dtype, nsq)) then false
  else if not(ame_check_formed_operand(ms1, ms1_dtype, nsq)) then false
  else if not(ame_check_formed_operand(ms2, ms2_dtype, nsq)) then false
  else {
    let snapshot = ame_snapshot_mregs();
    var saturated : bits(1) = 0b0;

    foreach (e from 0 to (nsq * ame_nelem - 1)) {
      let md_val = ame_read_snapshot_elem(snapshot, md_dtype, md, e);
      let ms1_val = ame_read_snapshot_elem(snapshot, ms1_dtype, ms1, e);
      let ms2_val = ame_read_snapshot_elem(snapshot, ms2_dtype, ms2, e);
      let (element_saturated, result) =
        ame_int_logexp_result(op, md_dtype, md_val, ms1_val, ms2_val);
      saturated = saturated | bool_to_bit(element_saturated);
      write_m_elem(md_dtype, md, e, result)
    };

    if saturated == 0b1 then ame_set_saturated();
    true
  }
}

function ame_logexp_binary_x(md_dtype : bits(32), ms2_dtype : bits(32),
                             md : ameregidx, rs1_val : xlenbits,
                             ms2 : ameregidx, op : ame_int_logexp_op) -> bool = {
  let dest_size = ame_dtype_size(md_dtype);
  let src2_size = ame_dtype_size(ms2_dtype);
  let nsq = ame_nsq2(md_dtype, ms2_dtype);

  if ame_valid_softfloat_ew_dtype(md_dtype) & ame_valid_softfloat_ew_dtype(ms2_dtype) &
     ame_same_float_format2(md_dtype, ms2_dtype) then {
    if not(ame_check_formed_operand(md, md_dtype, nsq)) then false
    else if not(ame_check_formed_operand(ms2, ms2_dtype, nsq)) then false
    else match ame_fp_rounding_mode(md_dtype) {
      None() => ame_unsupported_result(),
      Some(rm) =>
        if op == AME_INT_LOG2SUB | op == AME_INT_SUBLOG2 then
          match ame_scalar_float_data_value(md_dtype, rs1_val) {
            None() => { ame_set_unsupported(); true },
            Some(scalar_elem) => {
              let snapshot = ame_snapshot_mregs();
              var flags : bits_fflags = zeros();

              foreach (e from 0 to (nsq * ame_nelem - 1)) {
                let ms2_val = ame_read_snapshot_elem(snapshot, ms2_dtype, ms2, e);
                let (fflags, result) =
                  ame_float_log2bias_result(md_dtype, op, rm, ms2_val, scalar_elem);
                flags = flags | fflags;
                write_m_elem(md_dtype, md, e, result)
              };

              accrue_amefflags(flags);
              true
            }
          }
        else {
          // mldexp*.ew.x and mrdexp*.ew.x use the instruction-defined
          // exponent control rs1_val (a signed 128-bit integer, which on
          // RV64 is the zero-extended 64-bit rs1 value), not amestype.
          let exp_value = ame_elem_int(ame_max_int_dtype_descriptor(),
                                       zero_extend(ame_max_dtype_size, rs1_val));
          let snapshot = ame_snapshot_mregs();
          var flags : bits_fflags = zeros();

          foreach (e from 0 to (nsq * ame_nelem - 1)) {
            let md_val = ame_read_snapshot_elem(snapshot, md_dtype, md, e);
            let ms2_val = ame_read_snapshot_elem(snapshot, ms2_dtype, ms2, e);
            let (fflags, result) = ame_fp_ldexp_result(md_dtype, rm,
              op == AME_INT_LDEXPACC, false, ms2_val, md_val, exp_value);
            flags = flags | fflags;
            write_m_elem(md_dtype, md, e, result)
          };

          accrue_amefflags(flags);
          true
        }
    }
  }
  else if not(ame_valid_int_elementwise_dtype(md_dtype) & ame_valid_int_elementwise_dtype(ms2_dtype)) then
    ame_unsupported_result()
  else if dest_size != src2_size | ame_is_signed(md_dtype) != ame_is_signed(ms2_dtype) then
    ame_unsupported_result()
  else if not(ame_check_formed_operand(md, md_dtype, nsq)) then false
  else if not(ame_check_formed_operand(ms2, ms2_dtype, nsq)) then false
  else if op == AME_INT_LOG2SUB | op == AME_INT_SUBLOG2 then
    match ame_scalar_integer_data_value(ms2_dtype, rs1_val) {
      None() => { ame_set_unsupported(); true },
      Some(scalar_elem) => {
        let snapshot = ame_snapshot_mregs();
        var saturated : bits(1) = 0b0;

        foreach (e from 0 to (nsq * ame_nelem - 1)) {
          let md_val = ame_read_snapshot_elem(snapshot, md_dtype, md, e);
          let ms2_val = ame_read_snapshot_elem(snapshot, ms2_dtype, ms2, e);
          let (element_saturated, result) =
            ame_int_logexp_result(op, md_dtype, md_val, ms2_val, scalar_elem);
          saturated = saturated | bool_to_bit(element_saturated);
          write_m_elem(md_dtype, md, e, result)
        };

        if saturated == 0b1 then ame_set_saturated();
        true
      }
    }
  else {
    // mldexp*.ew.x and mrdexp*.ew.x use the instruction-defined exponent
    // control rs1_val, not amestype.
    let scalar_elem : bits(ame_max_dtype_size) = zero_extend(ame_max_dtype_size, rs1_val);
    let snapshot = ame_snapshot_mregs();
    var saturated : bits(1) = 0b0;

    foreach (e from 0 to (nsq * ame_nelem - 1)) {
      let md_val = ame_read_snapshot_elem(snapshot, md_dtype, md, e);
      let ms2_val = ame_read_snapshot_elem(snapshot, ms2_dtype, ms2, e);
      let (element_saturated, result) =
        ame_int_logexp_result(op, md_dtype, md_val, ms2_val, scalar_elem);
      saturated = saturated | bool_to_bit(element_saturated);
      write_m_elem(md_dtype, md, e, result)
    };

    if saturated == 0b1 then ame_set_saturated();
    true
  }
}
