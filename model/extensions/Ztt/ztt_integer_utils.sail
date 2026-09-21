// Integer value conversion and exact arithmetic helpers.

// =========================================================================
// Integer elementwise helpers
// =========================================================================

enum ame_int_binary_op = {
  AME_INT_ADD,
  AME_INT_SUB_LHS_RHS,
  AME_INT_SUB_RHS_LHS,
  AME_INT_AND,
  AME_INT_ANDNOT,
  AME_INT_OR,
  AME_INT_ORNOT,
  AME_INT_XOR,
  AME_INT_MAX,
  AME_INT_MIN,
  AME_INT_ABSDIFF,
  AME_INT_HDIFF_RHS_LHS,
  AME_INT_HDIFF_LHS_RHS,
  AME_INT_MEAN,
  AME_INT_MUL,
  AME_INT_MULNEG,
  AME_INT_CMPGE,
  AME_INT_CMPLT
}

enum ame_int_ternary_op = {
  AME_INT_MULACC,
  AME_INT_MULNACC,
  AME_INT_MULADD,
  AME_INT_MULSUB
}

enum ame_int_unary_op = { AME_INT_ABS }

enum ame_int_shift_op = {
  AME_INT_SHIFT_LEFT,
  AME_INT_SHIFT_RIGHT_LOGICAL,
  AME_INT_SHIFT_RIGHT_ARITH
}

enum ame_float_math_op = {
  AME_FLOAT_SQRT,
  AME_FLOAT_RECIPROCAL,
  AME_FLOAT_RSQRT,
  AME_FLOAT_ROUND_DOWN,
  AME_FLOAT_ROUND_NEAREST,
  AME_FLOAT_ROUND_UP,
  AME_FLOAT_ROUND_ZERO,
  AME_FLOAT_COS,
  AME_FLOAT_SIN,
  AME_FLOAT_TANH
}

enum ame_int_reduce_op = {
  AME_INT_REDUCE_ADD,
  AME_INT_REDUCE_MAX,
  AME_INT_REDUCE_MIN
}

enum ame_int_scatter_op = {
  AME_INT_SCATTER_ADD,
  AME_INT_SCATTER_MAX
}

enum ame_int_logexp_op = {
  AME_INT_EXP2,
  AME_INT_LOG2,
  AME_INT_LDEXP,
  AME_INT_LDEXPACC,
  AME_INT_RDEXP,
  AME_INT_RDEXPACC,
  AME_INT_LOG2SUB,
  AME_INT_SUBLOG2
}

function ame_valid_int_elementwise_dtype(dtype : bits(32)) -> bool = {
  let size = ame_dtype_size(dtype);
  size > 0 & ame_is_integer(dtype)
}

function ame_valid_int_ew_dtype(dtype : bits(32)) -> bool = {
  let size = ame_dtype_size(dtype);
  size > 0 & ame_is_integer(dtype) & not(ame_is_saturating(dtype))
}

function ame_elem_int(dtype : bits(32), ms1_val : bits(ame_max_dtype_size)) -> int = {
  let size = ame_dtype_size(dtype);
  if ame_is_signed(dtype) then {
    match size {
       4  => signed(ms1_val[ 3 .. 0]),
       8  => signed(ms1_val[ 7 .. 0]),
      16  => signed(ms1_val[15 .. 0]),
      32  => signed(ms1_val[31 .. 0]),
      64  => signed(ms1_val[63 .. 0]),
      128 => signed(ms1_val[127 .. 0]),
      _   => internal_error(__FILE__, __LINE__, "unsupported element size")
    }
  } else {
    match size {
       4  => unsigned(ms1_val[ 3 .. 0]),
       8  => unsigned(ms1_val[ 7 .. 0]),
      16  => unsigned(ms1_val[15 .. 0]),
      32  => unsigned(ms1_val[31 .. 0]),
      64  => unsigned(ms1_val[63 .. 0]),
      128 => unsigned(ms1_val[127 .. 0]),
      _   => internal_error(__FILE__, __LINE__, "unsupported element size")
    }
  }
}

function ame_int_min_value(dtype : bits(32)) -> int = {
  if not(ame_is_signed(dtype)) then 0
  else match ame_dtype_size(dtype) {
     4  => 0 - (2 ^ 3),
     8  => 0 - (2 ^ 7),
    16  => 0 - (2 ^ 15),
    32  => 0 - (2 ^ 31),
    64  => 0 - (2 ^ 63),
    128 => 0 - (2 ^ 127),
    _   => internal_error(__FILE__, __LINE__, "unsupported integer element size")
  }
}

function ame_int_max_value(dtype : bits(32)) -> int = {
  if ame_is_signed(dtype) then {
    match ame_dtype_size(dtype) {
       4  => (2 ^ 3) - 1,
       8  => (2 ^ 7) - 1,
      16  => (2 ^ 15) - 1,
      32  => (2 ^ 31) - 1,
      64  => (2 ^ 63) - 1,
      128 => (2 ^ 127) - 1,
      _   => internal_error(__FILE__, __LINE__, "unsupported integer element size")
    }
  } else {
    match ame_dtype_size(dtype) {
       4  => (2 ^ 4) - 1,
       8  => (2 ^ 8) - 1,
      16  => (2 ^ 16) - 1,
      32  => (2 ^ 32) - 1,
      64  => (2 ^ 64) - 1,
      128 => (2 ^ 128) - 1,
      _   => internal_error(__FILE__, __LINE__, "unsupported integer element size")
    }
  }
}

function ame_int_saturates(dtype : bits(32), value : int) -> bool =
  ame_is_saturating(dtype) &
    (value < ame_int_min_value(dtype) | value > ame_int_max_value(dtype))

function ame_int_result_from_int(dtype : bits(32), value : int)
  -> bits(ame_max_dtype_size) = {
  let result =
    if ame_is_saturating(dtype) then
      min(max(value, ame_int_min_value(dtype)), ame_int_max_value(dtype))
    else
      value;
  to_bits_unsafe(ame_max_dtype_size, result)
}

// Return the architectural element value together with whether a saturating
// destination clamped the exact intermediate. Callers commit the accumulated
// flag only after their entire instruction result is ready.
function ame_int_result_with_saturation(dtype : bits(32), value : int)
  -> (bool, bits(ame_max_dtype_size)) =
  (ame_int_saturates(dtype, value), ame_int_result_from_int(dtype, value))

// Round a signed exact intermediate after discarding low fractional bits.
// The quotient is an arithmetic right shift, so RDN differs from truncation
// for negative values.
function ame_int_round_right(dtype : bits(32), value : int,
                             discarded_bits : nat) -> int = {
  if discarded_bits == 0 then value
  else {
    let divisor = 2 ^ discarded_bits;
    let magnitude = if value < 0 then 0 - value else value;
    let magnitude_quotient = quot_round_zero(magnitude, divisor);
    let magnitude_remainder = magnitude - magnitude_quotient * divisor;
    let quotient = if value < 0 then
      if magnitude_remainder == 0 then 0 - magnitude_quotient
      else 0 - magnitude_quotient - 1
    else magnitude_quotient;
    let remainder = value - quotient * divisor;
    let halfway = divisor / 2;
    let absolute_quotient = if quotient < 0 then 0 - quotient else quotient;
    let quotient_odd =
      absolute_quotient - quot_round_zero(absolute_quotient, 2) * 2 == 1;
    let rnu_increment = if remainder >= halfway then 1 else 0;
    let rne_increment = if remainder > halfway |
      (remainder == halfway & quotient_odd) then 1 else 0;
    match dtype[28 .. 27] {
      0b00 => quotient + rnu_increment, // RNU
      0b01 => quotient + rne_increment, // RNE
      0b10 => quotient, // RDN
      0b11 => (if remainder == 0 | quotient_odd then quotient else quotient + 1) // ROD
    }
  }
}

function ame_int_binary_result(op : ame_int_binary_op, dtype : bits(32),
                               ms1_val : bits(ame_max_dtype_size),
                               ms2_val : bits(ame_max_dtype_size))
  -> (bool, bits(ame_max_dtype_size)) = {
  let lhs_int = ame_elem_int(dtype, ms1_val);
  let rhs_int = ame_elem_int(dtype, ms2_val);
  match op {
    AME_INT_ADD            => ame_int_result_with_saturation(dtype, lhs_int + rhs_int),
    AME_INT_SUB_LHS_RHS    => ame_int_result_with_saturation(dtype, lhs_int - rhs_int),
    AME_INT_SUB_RHS_LHS    => ame_int_result_with_saturation(dtype, rhs_int - lhs_int),
    AME_INT_AND            => (false, ms1_val & ms2_val),
    AME_INT_ANDNOT         => (false, ms1_val & ~(ms2_val)),
    AME_INT_OR             => (false, ms1_val | ms2_val),
    AME_INT_ORNOT          => (false, ms1_val | ~(ms2_val)),
    AME_INT_XOR            => (false, ms1_val ^ ms2_val),
    AME_INT_MAX            => ame_int_result_with_saturation(dtype, max(lhs_int, rhs_int)),
    AME_INT_MIN            => ame_int_result_with_saturation(dtype, min(lhs_int, rhs_int)),
    AME_INT_ABSDIFF        => ame_int_result_with_saturation(dtype, abs_int(lhs_int - rhs_int)),
    AME_INT_HDIFF_RHS_LHS  => ame_int_result_with_saturation(dtype, ame_int_round_right(dtype, rhs_int - lhs_int, 1)),
    AME_INT_HDIFF_LHS_RHS  => ame_int_result_with_saturation(dtype, ame_int_round_right(dtype, lhs_int - rhs_int, 1)),
    AME_INT_MEAN           => ame_int_result_with_saturation(dtype, ame_int_round_right(dtype, lhs_int + rhs_int, 1)),
    AME_INT_MUL            => ame_int_result_with_saturation(dtype, lhs_int * rhs_int),
    AME_INT_MULNEG         => ame_int_result_with_saturation(dtype, 0 - (lhs_int * rhs_int)),
    AME_INT_CMPGE          => (false, if lhs_int >= rhs_int then ones() else zeros()),
    AME_INT_CMPLT          => (false, if lhs_int < rhs_int then ones() else zeros())
  }
}
