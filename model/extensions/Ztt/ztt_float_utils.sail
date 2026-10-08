// Floating-point format and SoftFloat helpers.

// Host-libm transcendentals for the Ztt float-math instructions.  The AME
// spec permits an implementation-defined approximation with a documented
// ulp budget; this model documents <= 2 ulp (host glibc).
val ame_ztt_f32cos = pure {cpp: "ame_ztt_f32cos"} : (bits_S) -> bits_S
val ame_ztt_f32sin = pure {cpp: "ame_ztt_f32sin"} : (bits_S) -> bits_S
val ame_ztt_f32tanh = pure {cpp: "ame_ztt_f32tanh"} : (bits_S) -> bits_S
val ame_ztt_f32exp2 = pure {cpp: "ame_ztt_f32exp2"} : (bits_S) -> bits_S
val ame_ztt_f32log2 = pure {cpp: "ame_ztt_f32log2"} : (bits_S) -> bits_S
val ame_ztt_f64cos = pure {cpp: "ame_ztt_f64cos"} : (bits_D) -> bits_D
val ame_ztt_f64sin = pure {cpp: "ame_ztt_f64sin"} : (bits_D) -> bits_D
val ame_ztt_f64tanh = pure {cpp: "ame_ztt_f64tanh"} : (bits_D) -> bits_D
val ame_ztt_f64exp2 = pure {cpp: "ame_ztt_f64exp2"} : (bits_D) -> bits_D
val ame_ztt_f64log2 = pure {cpp: "ame_ztt_f64log2"} : (bits_D) -> bits_D


function ame_dtype_without_rounding(dtype : bits(32)) -> bits(32) =
  [dtype with 25 .. 22 = 0b0000]

function ame_same_float_format2(ms1_dtype : bits(32), ms2_dtype : bits(32)) -> bool =
  ame_dtype_without_rounding(ms1_dtype) == ame_dtype_without_rounding(ms2_dtype)

function ame_same_float_format3(ms1_dtype : bits(32), ms2_dtype : bits(32),
                                dtype3 : bits(32)) -> bool =
  ame_same_float_format2(ms1_dtype, ms2_dtype) &
  ame_same_float_format2(ms1_dtype, dtype3)

function ame_is_bf16_dtype(dtype : bits(32)) -> bool =
  ame_dtype_without_rounding(dtype) == 0x20300110

function ame_is_ocp_e4m3_dtype(dtype : bits(32)) -> bool =
  ame_dtype_without_rounding(dtype) == 0x10100108

function ame_is_ocp_e5m2_dtype(dtype : bits(32)) -> bool =
  ame_dtype_without_rounding(dtype) == 0x14300108

function ame_is_ocp_fp8_dtype(dtype : bits(32)) -> bool =
  ame_is_ocp_e4m3_dtype(dtype) | ame_is_ocp_e5m2_dtype(dtype)

function ame_valid_softfloat_ew_dtype(dtype : bits(32)) -> bool = {
  match ame_dtype_without_rounding(dtype) {
    0x10100108 => true, // OCP_E4M3
    0x14300108 => true, // OCP_E5M2
    0x14300110 => true, // FP16
    0x20300110 => true, // BF16
    0x20300120 => true, // FP32
    0x2c300140 => true, // FP64
    _          => false
  }
}

function ame_fp_rounding_mode(dtype : bits(32)) -> option(bits_rm) = {
  match dtype[25 .. 22] {
    0b0000 => Some(0b000), // RNE
    0b0001 => Some(0b001), // RTZ
    0b0010 => Some(0b010), // RDN
    0b0011 => Some(0b011), // RUP
    0b0100 => Some(0b100), // RMM
    0b0101 => Some(0b110), // RNO (SoftFloat round-to-odd/jamming)
    _      => None()
  }
}

function ame_fp32_elem(value : bits(ame_max_dtype_size)) -> bits_S =
  value[31 .. 0]

function ame_fp32_result(value : bits_S) -> bits(ame_max_dtype_size) =
  zero_extend(ame_max_dtype_size, value)

function ame_fp32_abs(value : bits_S) -> bits_S =
  [value with 31 = 0b0]

function ame_fp32_negate(value : bits_S) -> bits_S =
  [value with 31 = not_bit(value[31])]

function ame_fp32_is_nan(value : bits_S) -> bool =
  value[30 .. 23] == ones() & value[22 .. 0] != zeros()

function ame_fp32_is_snan(value : bits_S) -> bool =
  ame_fp32_is_nan(value) & value[22] == 0b0

function ame_fp32_is_neg_zero(value : bits_S) -> bool =
  value[31] == 0b1 & value[30 .. 23] == zeros() & value[22 .. 0] == zeros()

function ame_fp32_is_pos_zero(value : bits_S) -> bool =
  value[31] == 0b0 & value[30 .. 23] == zeros() & value[22 .. 0] == zeros()

function ame_fp32_canonical_nan() -> bits_S =
  0x7FC00000

function ame_fp32_fmin(ms1_val : bits_S, ms2_val : bits_S) -> (bits_fflags, bits_S) = {
  if ame_fp32_is_nan(ms1_val) | ame_fp32_is_nan(ms2_val) then
    (if ame_fp32_is_snan(ms1_val) | ame_fp32_is_snan(ms2_val) then 0b10000 else zeros(),
     ame_fp32_canonical_nan())
  else {
    let (fflags, lhs_le_rhs) = riscv_f32Le_quiet(ms1_val, ms2_val);
    let result =
      if      ame_fp32_is_neg_zero(ms1_val) & ame_fp32_is_pos_zero(ms2_val) then ms1_val
      else if ame_fp32_is_neg_zero(ms2_val) & ame_fp32_is_pos_zero(ms1_val) then ms2_val
      else if lhs_le_rhs                                             then ms1_val
      else                                                                ms2_val;
    (fflags, result)
  }
}

function ame_fp32_fmax(ms1_val : bits_S, ms2_val : bits_S) -> (bits_fflags, bits_S) = {
  if ame_fp32_is_nan(ms1_val) | ame_fp32_is_nan(ms2_val) then
    (if ame_fp32_is_snan(ms1_val) | ame_fp32_is_snan(ms2_val) then 0b10000 else zeros(),
     ame_fp32_canonical_nan())
  else {
    let (fflags, rhs_le_lhs) = riscv_f32Le_quiet(ms2_val, ms1_val);
    let result =
      if      ame_fp32_is_neg_zero(ms1_val) & ame_fp32_is_pos_zero(ms2_val) then ms2_val
      else if ame_fp32_is_neg_zero(ms2_val) & ame_fp32_is_pos_zero(ms1_val) then ms1_val
      else if rhs_le_lhs                                             then ms1_val
      else                                                                ms2_val;
    (fflags, result)
  }
}

function ame_fp16_is_nan(value : bits_H) -> bool =
  value[14 .. 10] == ones() & value[9 .. 0] != zeros()

function ame_fp16_is_snan(value : bits_H) -> bool =
  ame_fp16_is_nan(value) & value[9] == 0b0

function ame_fp16_is_neg_zero(value : bits_H) -> bool =
  value == 0x8000

function ame_fp16_is_pos_zero(value : bits_H) -> bool =
  value == 0x0000

function ame_fp16_fmin(ms1_val : bits_H, ms2_val : bits_H) -> (bits_fflags, bits_H) = {
  if ame_fp16_is_nan(ms1_val) | ame_fp16_is_nan(ms2_val) then
    (if ame_fp16_is_snan(ms1_val) | ame_fp16_is_snan(ms2_val) then 0b10000 else zeros(), 0x7E00)
  else {
    let (fflags, lhs_le_rhs) = riscv_f16Le_quiet(ms1_val, ms2_val);
    let result =
      if      ame_fp16_is_neg_zero(ms1_val) & ame_fp16_is_pos_zero(ms2_val) then ms1_val
      else if ame_fp16_is_neg_zero(ms2_val) & ame_fp16_is_pos_zero(ms1_val) then ms2_val
      else if lhs_le_rhs                                             then ms1_val
      else                                                                ms2_val;
    (fflags, result)
  }
}

function ame_fp16_fmax(ms1_val : bits_H, ms2_val : bits_H) -> (bits_fflags, bits_H) = {
  if ame_fp16_is_nan(ms1_val) | ame_fp16_is_nan(ms2_val) then
    (if ame_fp16_is_snan(ms1_val) | ame_fp16_is_snan(ms2_val) then 0b10000 else zeros(), 0x7E00)
  else {
    let (fflags, rhs_le_lhs) = riscv_f16Le_quiet(ms2_val, ms1_val);
    let result =
      if      ame_fp16_is_neg_zero(ms1_val) & ame_fp16_is_pos_zero(ms2_val) then ms2_val
      else if ame_fp16_is_neg_zero(ms2_val) & ame_fp16_is_pos_zero(ms1_val) then ms1_val
      else if rhs_le_lhs                                             then ms1_val
      else                                                                ms2_val;
    (fflags, result)
  }
}

function ame_fp64_is_nan(value : bits_D) -> bool =
  value[62 .. 52] == ones() & value[51 .. 0] != zeros()

function ame_fp64_is_snan(value : bits_D) -> bool =
  ame_fp64_is_nan(value) & value[51] == 0b0

function ame_fp64_is_neg_zero(value : bits_D) -> bool =
  value == 0x8000000000000000

function ame_fp64_is_pos_zero(value : bits_D) -> bool =
  value == 0x0000000000000000

function ame_fp64_fmin(ms1_val : bits_D, ms2_val : bits_D) -> (bits_fflags, bits_D) = {
  if ame_fp64_is_nan(ms1_val) | ame_fp64_is_nan(ms2_val) then
    (if ame_fp64_is_snan(ms1_val) | ame_fp64_is_snan(ms2_val) then 0b10000 else zeros(), 0x7FF8000000000000)
  else {
    let (fflags, lhs_le_rhs) = riscv_f64Le_quiet(ms1_val, ms2_val);
    let result =
      if      ame_fp64_is_neg_zero(ms1_val) & ame_fp64_is_pos_zero(ms2_val) then ms1_val
      else if ame_fp64_is_neg_zero(ms2_val) & ame_fp64_is_pos_zero(ms1_val) then ms2_val
      else if lhs_le_rhs                                             then ms1_val
      else                                                                ms2_val;
    (fflags, result)
  }
}

function ame_fp64_fmax(ms1_val : bits_D, ms2_val : bits_D) -> (bits_fflags, bits_D) = {
  if ame_fp64_is_nan(ms1_val) | ame_fp64_is_nan(ms2_val) then
    (if ame_fp64_is_snan(ms1_val) | ame_fp64_is_snan(ms2_val) then 0b10000 else zeros(), 0x7FF8000000000000)
  else {
    let (fflags, rhs_le_lhs) = riscv_f64Le_quiet(ms2_val, ms1_val);
    let result =
      if      ame_fp64_is_neg_zero(ms1_val) & ame_fp64_is_pos_zero(ms2_val) then ms2_val
      else if ame_fp64_is_neg_zero(ms2_val) & ame_fp64_is_pos_zero(ms1_val) then ms1_val
      else if rhs_le_lhs                                             then ms1_val
      else                                                                ms2_val;
    (fflags, result)
  }
}

function ame_fp32_binary_result(op : ame_int_binary_op, rm : bits_rm,
                                ms1_val : bits(ame_max_dtype_size),
                                ms2_val : bits(ame_max_dtype_size))
  -> (bits_fflags, bits(ame_max_dtype_size)) = {
  let lhs32 = ame_fp32_elem(ms1_val);
  let rhs32 = ame_fp32_elem(ms2_val);
  let (fflags, result32) : (bits_fflags, bits_S) = match op {
    AME_INT_ADD         => riscv_f32Add(rm, lhs32, rhs32),
    AME_INT_SUB_LHS_RHS => riscv_f32Sub(rm, lhs32, rhs32),
    AME_INT_SUB_RHS_LHS => riscv_f32Sub(rm, rhs32, lhs32),
    AME_INT_MAX         => ame_fp32_fmax(lhs32, rhs32),
    AME_INT_MIN         => ame_fp32_fmin(lhs32, rhs32),
    AME_INT_ABSDIFF     => {
      let (sub_fflags, sub_result) = riscv_f32Sub(rm, lhs32, rhs32);
      (sub_fflags, ame_fp32_abs(sub_result))
    },
    AME_INT_MUL         => riscv_f32Mul(rm, lhs32, rhs32),
    AME_INT_MULNEG      => riscv_f32Mul(rm, ame_fp32_negate(lhs32), rhs32),
    AME_INT_CMPGE       => {
      let (cmp_fflags, cmp_result) = riscv_f32Le(rhs32, lhs32);
      (cmp_fflags, if cmp_result then (ones() : bits(32)) else (zeros() : bits(32)))
    },
    AME_INT_CMPLT       => {
      let (cmp_fflags, cmp_result) = riscv_f32Lt(lhs32, rhs32);
      (cmp_fflags, if cmp_result then (ones() : bits(32)) else (zeros() : bits(32)))
    },
    _ => internal_error(__FILE__, __LINE__, "unsupported FP32 AME binary op")
  };
  (fflags, ame_fp32_result(result32))
}

function ame_fp32_ternary_result(op : ame_int_ternary_op, rm : bits_rm,
                                 md_val : bits(ame_max_dtype_size),
                                 ms1_val : bits(ame_max_dtype_size),
                                 ms2_val : bits(ame_max_dtype_size))
  -> (bits_fflags, bits(ame_max_dtype_size)) = {
  let dest32 = ame_fp32_elem(md_val);
  let lhs32 = ame_fp32_elem(ms1_val);
  let rhs32 = ame_fp32_elem(ms2_val);
  let (fflags, result32) : (bits_fflags, bits_S) = match op {
    AME_INT_MULACC  => riscv_f32MulAdd(rm, lhs32, rhs32, dest32),
    AME_INT_MULNACC => riscv_f32MulAdd(rm, ame_fp32_negate(lhs32), rhs32, dest32),
    AME_INT_MULADD  => riscv_f32MulAdd(rm, rhs32, dest32, lhs32),
    AME_INT_MULSUB  => riscv_f32MulAdd(rm, ame_fp32_negate(rhs32), dest32, lhs32)
  };
  (fflags, ame_fp32_result(result32))
}

// ---------------------------------------------------------------------------
// BF16 fused ternary arithmetic.
//
// The manual converts the exact sum `dest + ms1 * ms2` to the destination
// format once.  SoftFloat exposes no bf16 fused primitive, so the exact sum is
// computed with Sail's arbitrary-precision `int` and rounded exactly once
// here.  A finite bf16 value is `significand * 2 ^ exponent` with an 8-bit
// significand and an exponent in [-133, 120]; a product of two of them keeps
// at most 16 significant bits, so the exact result is a dyadic rational that
// fits comfortably in an `int`.
// ---------------------------------------------------------------------------

// Round `value * 2 ^ (-shift)` to an integer under `rm`; `value` is
// non-negative and `sign` selects the directed-rounding direction.  A
// non-positive shift is an exact left shift, so callers can pass the full
// fractional size and only the required right shifts round.
function ame_round_scaled_int(sign : bits(1), rm : bits_rm, value : int,
                              shift : int) -> (bool, int) = {
  if shift <= 0 then (false, value * 2 ^ (0 - shift))
  else {
    let divisor = 2 ^ shift;
    let quotient = quot_round_zero(value, divisor);
    let remainder = value - quotient * divisor;
    let halfway = divisor / 2;
    let quotient_odd = quotient - quot_round_zero(quotient, 2) * 2 == 1;
    let increment : bool = match rm {
      0b000 => remainder > halfway | (remainder == halfway & quotient_odd), // RNE
      0b001 => false,                                                       // RTZ
      0b010 => sign == 0b1 & remainder != 0,                                // RDN
      0b011 => sign == 0b0 & remainder != 0,                                // RUP
      0b100 => remainder >= halfway,                                        // RMM
      0b110 => remainder != 0 & not(quotient_odd),                          // RNO
      _     => remainder > halfway | (remainder == halfway & quotient_odd)
    };
    (remainder != 0, if increment then quotient + 1 else quotient)
  }
}

// Position of the most significant set bit, i.e. floor(log2(value)) for
// value >= 1.  The exact bf16 sums reach a few hundred bits, past the fixed
// element widths, so this must not be bounded by the datatype size.
function ame_int_floor_log2(value : int) -> int = {
  var remaining : int = value;
  var result : int = 0;
  var running : bool = true;
  while running do {
    if remaining >= 2 then {
      remaining = quot_round_zero(remaining, 2);
      result = result + 1
    } else {
      running = false
    }
  };
  result
}

function ame_float_overflow_to_inf(sign : bits(1), rm : bits_rm) -> bool =
  rm == 0b000 | // RNE
  rm == 0b100 | // RMM
  (rm == 0b011 & sign == 0b0) | // RUP
  (rm == 0b010 & sign == 0b1)   // RDN

function ame_bf16_is_nan(value : bits_BF16) -> bool =
  value[14 .. 7] == ones() & value[6 .. 0] != zeros()

function ame_bf16_is_snan(value : bits_BF16) -> bool =
  ame_bf16_is_nan(value) & value[6] == 0b0

function ame_bf16_is_inf(value : bits_BF16) -> bool =
  value[14 .. 7] == ones() & value[6 .. 0] == zeros()

function ame_bf16_is_zero(value : bits_BF16) -> bool =
  value[14 .. 7] == zeros() & value[6 .. 0] == zeros()

// Decode a finite bf16 into `value = significand * 2 ^ exponent`.
function ame_bf16_significand_exponent(value : bits_BF16) -> (int, int) = {
  let exponent = unsigned(value[14 .. 7]);
  let fraction = unsigned(value[6 .. 0]);
  if exponent == 0 then (fraction, 0 - 133)
  else (128 + fraction, exponent - 134)
}

// Round the exact non-zero magnitude `magnitude * 2 ^ exponent` to bf16 with
// one rounding, applying tininess-after-rounding (UF only for a tiny delivered
// result) and overflow (OF+NX, saturating to Inf or the maximum finite value
// according to `rm`).
function ame_bf16_round_exact(sign : bits(1), rm : bits_rm, magnitude : int,
                              exponent : int) -> (bits_fflags, bits_BF16) = {
  let msb = ame_int_floor_log2(magnitude);
  let leading = exponent + msb;
  if leading >= 0 - 126 then {
    // Normal grid: the unit in the last place is 2 ^ (leading - 7).
    let (inexact, rounded) = ame_round_scaled_int(sign, rm, magnitude, msb - 7);
    let carry = rounded == 256;
    let significand : int = if carry then 128 else rounded;
    let result_exponent : int = leading + (if carry then 1 else 0);
    if result_exponent > 127 then {
      let result : bits_BF16 =
        if ame_float_overflow_to_inf(sign, rm) then sign @ ones(8) @ zeros(7)
        else sign @ to_bits_unsafe(8, 254) @ to_bits_unsafe(7, 127);
      (0b00101, result) // OF | NX
    } else {
      let result : bits_BF16 =
        sign @ to_bits_unsafe(8, result_exponent + 127) @
        to_bits_unsafe(7, significand - 128);
      ((if inexact then 0b00001 else 0b00000), result)
    }
  } else {
    // Subnormal grid: the unit in the last place is 2 ^ -133.
    let (inexact, rounded) = ame_round_scaled_int(sign, rm, magnitude,
      0 - (exponent + 133));
    if rounded >= 128 then
      // Rounded up to the minimum normal: not tiny after rounding.
      ((if inexact then 0b00001 else 0b00000),
       sign @ to_bits_unsafe(8, 1) @ zeros(7))
    else
      ((if inexact then 0b00011 else 0b00000), // UF | NX
       sign @ zeros(8) @ to_bits_unsafe(7, rounded))
  }
}

// Single-rounding bf16 fused multiply-add `(-1)^negate_product * a * b + c`,
// matching the reference `bf16_mulAdd` used by the C simulator: NaN operands
// collapse to the bf16 default NaN (raising NV only for signalling NaNs),
// zero times infinity is invalid, and an exact zero sum keeps the IEEE sign.
function ame_bf16_fma(rm : bits_rm, a : bits_BF16, b : bits_BF16, c : bits_BF16,
                      negate_product : bool) -> (bits_fflags, bits_BF16) = {
  let sign_c = c[15 .. 15];
  let sign_product_raw : bits(1) = if a[15 .. 15] == b[15 .. 15] then 0b0 else 0b1;
  let sign_product : bits(1) =
    if negate_product then not_bit(sign_product_raw) else sign_product_raw;

  if ame_bf16_is_nan(a) | ame_bf16_is_nan(b) | ame_bf16_is_nan(c) then {
    let invalid : bits_fflags =
      if ame_bf16_is_snan(a) | ame_bf16_is_snan(b) | ame_bf16_is_snan(c)
      then 0b10000 else 0b00000;
    (invalid, 0x7FC0)
  } else if (ame_bf16_is_zero(a) & ame_bf16_is_inf(b)) |
              (ame_bf16_is_inf(a) & ame_bf16_is_zero(b)) then
    (0b10000, 0x7FC0)
  else if ame_bf16_is_inf(a) | ame_bf16_is_inf(b) then {
    if ame_bf16_is_inf(c) & sign_c != sign_product then (0b10000, 0x7FC0)
    else (zeros(), sign_product @ ones(8) @ zeros(7))
  } else if ame_bf16_is_inf(c) then
    (zeros(), sign_c @ ones(8) @ zeros(7))
  else {
    let (sig_a, exp_a) = ame_bf16_significand_exponent(a);
    let (sig_b, exp_b) = ame_bf16_significand_exponent(b);
    let (sig_c, exp_c) = ame_bf16_significand_exponent(c);
    let product_exponent = exp_a + exp_b;
    // Both terms are aligned to the smaller exponent; the shifts stay exact.
    let common_exponent = min(product_exponent, exp_c);
    let product_term = sig_a * sig_b * 2 ^ (product_exponent - common_exponent);
    let addend_term = sig_c * 2 ^ (exp_c - common_exponent);
    let total =
      (if sign_product == 0b1 then 0 - product_term else product_term) +
      (if sign_c == 0b1 then 0 - addend_term else addend_term);
    if total == 0 then {
      let zero_sign : bits(1) =
        if sign_product == sign_c then sign_product
        else if rm == 0b010 then 0b1 else 0b0;
      (zeros(), zero_sign @ zeros(15))
    } else {
      let sign : bits(1) = if total < 0 then 0b1 else 0b0;
      let magnitude = if total < 0 then 0 - total else total;
      ame_bf16_round_exact(sign, rm, magnitude, common_exponent)
    }
  }
}

function ame_bf16_to_f32(value : bits(ame_max_dtype_size)) -> (bits_fflags, bits_S) = {
  let v : bits_BF16 = value[15 .. 0];
  let sign = v[15 .. 15];
  let exp = v[14 .. 7];
  let mant = v[6 .. 0];
  let is_nan = exp == ones() & mant != zeros();
  let is_inf = exp == ones() & mant == zeros();
  let fflags : bits_fflags = if is_nan & signed(mant) >= 0 then 0b10000 else 0b00000;
  let result : bits_S =
    if is_nan then 0x7FC00000
    else if is_inf then sign @ ones(8) @ zeros(23)
    else sign @ exp @ mant @ zeros(16);
  (fflags, result)
}

function ame_bf16_result(value : bits_BF16) -> bits(ame_max_dtype_size) =
  zero_extend(ame_max_dtype_size, value)

function ame_bf16_round_result(rm : bits_rm, input_fflags : bits_fflags,
                               value : bits_S) -> (bits_fflags, bits(ame_max_dtype_size)) = {
  let (round_fflags, result16) = riscv_f32ToBF16(rm, value);
  (input_fflags | round_fflags, ame_bf16_result(result16))
}

function ame_bf16_binary_result(op : ame_int_binary_op, rm : bits_rm,
                                ms1_val : bits(ame_max_dtype_size),
                                ms2_val : bits(ame_max_dtype_size))
  -> (bits_fflags, bits(ame_max_dtype_size)) = {
  let (lhs_fflags, lhs32) = ame_bf16_to_f32(ms1_val);
  let (rhs_fflags, rhs32) = ame_bf16_to_f32(ms2_val);
  let input_fflags = lhs_fflags | rhs_fflags;

  match op {
    AME_INT_ADD => {
      let (op_fflags, result32) = riscv_f32Add(rm, lhs32, rhs32);
      ame_bf16_round_result(rm, input_fflags | op_fflags, result32)
    },
    AME_INT_SUB_LHS_RHS => {
      let (op_fflags, result32) = riscv_f32Sub(rm, lhs32, rhs32);
      ame_bf16_round_result(rm, input_fflags | op_fflags, result32)
    },
    AME_INT_SUB_RHS_LHS => {
      let (op_fflags, result32) = riscv_f32Sub(rm, rhs32, lhs32);
      ame_bf16_round_result(rm, input_fflags | op_fflags, result32)
    },
    AME_INT_MAX => {
      if lhs_fflags != zeros() | rhs_fflags != zeros() then
        (input_fflags, ame_bf16_result(0x7FC0))
      else {
        let (op_fflags, result32) = ame_fp32_fmax(lhs32, rhs32);
        ame_bf16_round_result(rm, op_fflags, result32)
      }
    },
    AME_INT_MIN => {
      if lhs_fflags != zeros() | rhs_fflags != zeros() then
        (input_fflags, ame_bf16_result(0x7FC0))
      else {
        let (op_fflags, result32) = ame_fp32_fmin(lhs32, rhs32);
        ame_bf16_round_result(rm, op_fflags, result32)
      }
    },
    AME_INT_ABSDIFF => {
      let (op_fflags, sub32) = riscv_f32Sub(rm, lhs32, rhs32);
      ame_bf16_round_result(rm, input_fflags | op_fflags, ame_fp32_abs(sub32))
    },
    AME_INT_MUL => {
      let (op_fflags, result32) = riscv_f32Mul(rm, lhs32, rhs32);
      ame_bf16_round_result(rm, input_fflags | op_fflags, result32)
    },
    AME_INT_MULNEG => {
      let (op_fflags, result32) = riscv_f32Mul(rm, ame_fp32_negate(lhs32), rhs32);
      ame_bf16_round_result(rm, input_fflags | op_fflags, result32)
    },
    AME_INT_CMPGE => {
      let (op_fflags, result) = riscv_f32Le(rhs32, lhs32);
      (input_fflags | op_fflags, if result then ones() else zeros())
    },
    AME_INT_CMPLT => {
      let (op_fflags, result) = riscv_f32Lt(lhs32, rhs32);
      (input_fflags | op_fflags, if result then ones() else zeros())
    },
    _ => internal_error(__FILE__, __LINE__, "unsupported BF16 AME binary op")
  }
}

function ame_bf16_ternary_result(op : ame_int_ternary_op, rm : bits_rm,
                                 md_val : bits(ame_max_dtype_size),
                                 ms1_val : bits(ame_max_dtype_size),
                                 ms2_val : bits(ame_max_dtype_size))
  -> (bits_fflags, bits(ame_max_dtype_size)) = {
  let dest : bits_BF16 = md_val[15 .. 0];
  let lhs : bits_BF16 = ms1_val[15 .. 0];
  let rhs : bits_BF16 = ms2_val[15 .. 0];
  // The four ternary instructions differ only in operand order and in whether
  // the product is negated (manual 6.x):
  //   MULACC  : lhs * rhs + dest
  //   MULNACC : -(lhs * rhs) + dest
  //   MULADD  : rhs * dest + lhs
  //   MULSUB  : -(rhs * dest) + lhs
  let (a, b, c, negate_product) : (bits_BF16, bits_BF16, bits_BF16, bool) =
    match op {
      AME_INT_MULACC  => (lhs, rhs, dest, false),
      AME_INT_MULNACC => (lhs, rhs, dest, true),
      AME_INT_MULADD  => (rhs, dest, lhs, false),
      AME_INT_MULSUB  => (rhs, dest, lhs, true)
    };
  let (fflags, result) = ame_bf16_fma(rm, a, b, c, negate_product);
  (fflags, ame_bf16_result(result))
}

function ame_bf16_unary_result(op : ame_int_unary_op,
                               value : bits(ame_max_dtype_size))
  -> (bits_fflags, bits(ame_max_dtype_size)) = {
  let result : bits_BF16 = match op {
    AME_INT_ABS => [value[15 .. 0] with 15 = 0b0]
  };
  (zeros(), ame_bf16_result(result))
}

function ame_ocp_fp8_result(value : bits(8)) -> bits(ame_max_dtype_size) =
  zero_extend(ame_max_dtype_size, value)

function ame_ocp_round_right(sign : bits(1), rm : bits_rm, value : int, shift : nat)
  -> (bool, int) =
  ame_round_scaled_int(sign, rm, value, shift)

// Tininess is detected after rounding.  An inexact subnormal/zero raises
// UF+NX, while a tiny exact value and an inexact value rounded up to the
// minimum normal do not raise UF.
function ame_ocp_subnormal_flags(inexact : bool,
                                 rounded_to_normal : bool) -> bits_fflags =
  if not(inexact) then 0b00000
  else if rounded_to_normal then 0b00001
  else 0b00011

function ame_e4m3_subnormal_to_f32(sign : bits(1), frac : bits(3)) -> bits_S = {
  let mag : bits(31) = match frac {
    0b001 => to_bits(8, 118) @ to_bits(23, 0),
    0b010 => to_bits(8, 119) @ to_bits(23, 0),
    0b011 => to_bits(8, 119) @ to_bits(23, 4194304),
    0b100 => to_bits(8, 120) @ to_bits(23, 0),
    0b101 => to_bits(8, 120) @ to_bits(23, 2097152),
    0b110 => to_bits(8, 120) @ to_bits(23, 4194304),
    0b111 => to_bits(8, 120) @ to_bits(23, 6291456),
    _     => zeros()
  };
  sign @ mag
}

function ame_e5m2_subnormal_to_f32(sign : bits(1), frac : bits(2)) -> bits_S = {
  let mag : bits(31) = match frac {
    0b01 => to_bits(8, 111) @ to_bits(23, 0),
    0b10 => to_bits(8, 112) @ to_bits(23, 0),
    0b11 => to_bits(8, 112) @ to_bits(23, 4194304),
    _    => zeros()
  };
  sign @ mag
}

function ame_e4m3_to_f32(value : bits(ame_max_dtype_size)) -> (bits_fflags, bits_S) = {
  let v : bits(8) = value[7 .. 0];
  let sign = v[7 .. 7];
  let exp : bits(4) = v[6 .. 3];
  let frac : bits(3) = v[2 .. 0];
  if exp == 0b0000 then {
    if frac == 0b000 then (zeros(), sign @ zeros(8) @ zeros(23))
    else (zeros(), ame_e4m3_subnormal_to_f32(sign, frac))
  } else if exp == 0b1111 & frac == 0b111 then {
    // OCP E4M3 has one NaN encoding per sign and no signalling NaN.
    (zeros(), 0x7FC00000)
  } else {
    let exp32 = unsigned(exp) - 7 + 127;
    (zeros(), sign @ to_bits_unsafe(8, exp32) @ frac @ zeros(20))
  }
}

function ame_e5m2_to_f32(value : bits(ame_max_dtype_size)) -> (bits_fflags, bits_S) = {
  let v : bits(8) = value[7 .. 0];
  let sign = v[7 .. 7];
  let exp : bits(5) = v[6 .. 2];
  let frac : bits(2) = v[1 .. 0];
  if exp == 0b00000 then {
    if frac == 0b00 then (zeros(), sign @ zeros(8) @ zeros(23))
    else (zeros(), ame_e5m2_subnormal_to_f32(sign, frac))
  } else if exp == 0b11111 then {
    if frac == 0b00 then (zeros(), sign @ ones(8) @ zeros(23))
    // OCP E5M2 follows the IEEE quiet-bit convention: frac[1] clear is sNaN.
    else ((if frac[1] == 0b0 then 0b10000 else zeros()), 0x7FC00000)
  } else {
    let exp32 = unsigned(exp) - 15 + 127;
    (zeros(), sign @ to_bits_unsafe(8, exp32) @ frac @ zeros(21))
  }
}

function ame_ocp_fp8_to_f32(dtype : bits(32), value : bits(ame_max_dtype_size))
  -> (bits_fflags, bits_S) =
  if ame_is_ocp_e4m3_dtype(dtype) then ame_e4m3_to_f32(value)
  else ame_e5m2_to_f32(value)

function ame_f32_to_e4m3(rm : bits_rm, value : bits_S) -> (bits_fflags, bits(8)) = {
  let sign = value[31 .. 31];
  let exp = unsigned(value[30 .. 23]);
  let frac = unsigned(value[22 .. 0]);

  if exp == 0 & frac == 0 then (zeros(), sign @ 0b0000 @ 0b000)
  else if exp == 255 then {
    if frac == 0 then (0b00101, sign @ 0b1111 @ 0b110)
    else (zeros(), 0x7F)
  } else {
    let target_exp = exp - 127 + 7;
    if target_exp <= 0 then {
      let sig = if exp == 0 then frac else (2 ^ 23) + frac;
      // E4M3 subnormal bit 0 has value 2^-9.  A normal f32 significand
      // therefore shifts by 141-exp; an f32 subnormal shifts by 140.
      let shift = if exp == 0 then 140 else 141 - exp;
      let (inexact, rounded) = ame_ocp_round_right(sign, rm, sig, shift);
      let rounded_to_normal = rounded >= 8;
      let result = if rounded_to_normal then sign @ 0b0001 @ 0b000
        else sign @ 0b0000 @ to_bits_unsafe(3, rounded);
      (ame_ocp_subnormal_flags(inexact, rounded_to_normal), result)
    }
    else {
      let sig = (2 ^ 23) + frac;
      let (inexact, rounded) = ame_ocp_round_right(sign, rm, sig, 20);
      var exp_out : int = target_exp;
      var sig_out : int = rounded;
      if sig_out == 16 then {
        exp_out = exp_out + 1;
        sig_out = 8
      };
      let frac_out = sig_out - 8;
      if exp_out > 15 | (exp_out == 15 & frac_out >= 7) then
        (0b00101, sign @ 0b1111 @ 0b110)
      else
        ((if inexact then 0b00001 else 0b00000), sign @ to_bits_unsafe(4, exp_out) @ to_bits_unsafe(3, frac_out))
    }
  }
}

function ame_f32_to_e5m2(rm : bits_rm, value : bits_S) -> (bits_fflags, bits(8)) = {
  let sign = value[31 .. 31];
  let exp = unsigned(value[30 .. 23]);
  let frac = unsigned(value[22 .. 0]);

  if exp == 0 & frac == 0 then (zeros(), sign @ 0b00000 @ 0b00)
  else if exp == 255 then {
    if frac == 0 then (zeros(), sign @ 0b11111 @ 0b00)
    else (zeros(), 0x7F)
  } else {
    let target_exp = exp - 127 + 15;
    if target_exp <= 0 then {
      let sig = if exp == 0 then frac else (2 ^ 23) + frac;
      // E5M2 subnormal bit 0 has value 2^-16.
      let shift = if exp == 0 then 133 else 134 - exp;
      let (inexact, rounded) = ame_ocp_round_right(sign, rm, sig, shift);
      let rounded_to_normal = rounded >= 4;
      let result = if rounded_to_normal then sign @ 0b00001 @ 0b00
        else sign @ 0b00000 @ to_bits_unsafe(2, rounded);
      (ame_ocp_subnormal_flags(inexact, rounded_to_normal), result)
    }
    else {
      let sig = (2 ^ 23) + frac;
      let (inexact, rounded) = ame_ocp_round_right(sign, rm, sig, 21);
      var exp_out : int = target_exp;
      var sig_out : int = rounded;
      if sig_out == 8 then {
        exp_out = exp_out + 1;
        sig_out = 4
      };
      if exp_out >= 31 then {
        let result = if ame_float_overflow_to_inf(sign, rm)
          then sign @ 0b11111 @ 0b00
          else sign @ 0b11110 @ 0b11;
        (0b00101, result)
      }
      else
        ((if inexact then 0b00001 else 0b00000), sign @ to_bits_unsafe(5, exp_out) @ to_bits_unsafe(2, sig_out - 4))
    }
  }
}

function ame_ocp_fp8_round_result(dtype : bits(32), rm : bits_rm,
                                  input_fflags : bits_fflags, value : bits_S)
  -> (bits_fflags, bits(ame_max_dtype_size)) = {
  let (round_fflags, result8) =
    if ame_is_ocp_e4m3_dtype(dtype) then ame_f32_to_e4m3(rm, value)
    else ame_f32_to_e5m2(rm, value);
  (input_fflags | round_fflags, ame_ocp_fp8_result(result8))
}

function ame_ocp_fp8_binary_result(dtype : bits(32), op : ame_int_binary_op,
                                   rm : bits_rm,
                                   ms1_val : bits(ame_max_dtype_size),
                                   ms2_val : bits(ame_max_dtype_size))
  -> (bits_fflags, bits(ame_max_dtype_size)) = {
  let (lhs_fflags, lhs32) = ame_ocp_fp8_to_f32(dtype, ms1_val);
  let (rhs_fflags, rhs32) = ame_ocp_fp8_to_f32(dtype, ms2_val);
  let input_fflags = lhs_fflags | rhs_fflags;

  match op {
    AME_INT_ADD => {
      let (op_fflags, result32) = riscv_f32Add(rm, lhs32, rhs32);
      ame_ocp_fp8_round_result(dtype, rm, input_fflags | op_fflags, result32)
    },
    AME_INT_SUB_LHS_RHS => {
      let (op_fflags, result32) = riscv_f32Sub(rm, lhs32, rhs32);
      ame_ocp_fp8_round_result(dtype, rm, input_fflags | op_fflags, result32)
    },
    AME_INT_SUB_RHS_LHS => {
      let (op_fflags, result32) = riscv_f32Sub(rm, rhs32, lhs32);
      ame_ocp_fp8_round_result(dtype, rm, input_fflags | op_fflags, result32)
    },
    AME_INT_MAX => {
      if lhs_fflags != zeros() | rhs_fflags != zeros() then
        (input_fflags, ame_ocp_fp8_result(0x7F))
      else {
        let (op_fflags, result32) = ame_fp32_fmax(lhs32, rhs32);
        ame_ocp_fp8_round_result(dtype, rm, op_fflags, result32)
      }
    },
    AME_INT_MIN => {
      if lhs_fflags != zeros() | rhs_fflags != zeros() then
        (input_fflags, ame_ocp_fp8_result(0x7F))
      else {
        let (op_fflags, result32) = ame_fp32_fmin(lhs32, rhs32);
        ame_ocp_fp8_round_result(dtype, rm, op_fflags, result32)
      }
    },
    AME_INT_ABSDIFF => {
      let (op_fflags, sub32) = riscv_f32Sub(rm, lhs32, rhs32);
      ame_ocp_fp8_round_result(dtype, rm, input_fflags | op_fflags, ame_fp32_abs(sub32))
    },
    AME_INT_MUL => {
      let (op_fflags, result32) = riscv_f32Mul(rm, lhs32, rhs32);
      ame_ocp_fp8_round_result(dtype, rm, input_fflags | op_fflags, result32)
    },
    AME_INT_MULNEG => {
      let (op_fflags, result32) = riscv_f32Mul(rm, ame_fp32_negate(lhs32), rhs32);
      ame_ocp_fp8_round_result(dtype, rm, input_fflags | op_fflags, result32)
    },
    AME_INT_CMPGE => {
      let (op_fflags, result) = riscv_f32Le(rhs32, lhs32);
      (input_fflags | op_fflags, if result then ones() else zeros())
    },
    AME_INT_CMPLT => {
      let (op_fflags, result) = riscv_f32Lt(lhs32, rhs32);
      (input_fflags | op_fflags, if result then ones() else zeros())
    },
    _ => internal_error(__FILE__, __LINE__, "unsupported OCP FP8 AME binary op")
  }
}

function ame_ocp_fp8_ternary_result(dtype : bits(32), op : ame_int_ternary_op,
                                    rm : bits_rm,
                                    md_val : bits(ame_max_dtype_size),
                                    ms1_val : bits(ame_max_dtype_size),
                                    ms2_val : bits(ame_max_dtype_size))
  -> (bits_fflags, bits(ame_max_dtype_size)) = {
  let (dest_fflags, dest32) = ame_ocp_fp8_to_f32(dtype, md_val);
  let (lhs_fflags, lhs32) = ame_ocp_fp8_to_f32(dtype, ms1_val);
  let (rhs_fflags, rhs32) = ame_ocp_fp8_to_f32(dtype, ms2_val);
  let input_fflags = dest_fflags | lhs_fflags | rhs_fflags;

  match op {
    AME_INT_MULACC => {
      let (op_fflags, result32) = riscv_f32MulAdd(rm, lhs32, rhs32, dest32);
      ame_ocp_fp8_round_result(dtype, rm, input_fflags | op_fflags, result32)
    },
    AME_INT_MULNACC => {
      let (op_fflags, result32) = riscv_f32MulAdd(rm, ame_fp32_negate(lhs32), rhs32, dest32);
      ame_ocp_fp8_round_result(dtype, rm, input_fflags | op_fflags, result32)
    },
    AME_INT_MULADD => {
      let (op_fflags, result32) = riscv_f32MulAdd(rm, rhs32, dest32, lhs32);
      ame_ocp_fp8_round_result(dtype, rm, input_fflags | op_fflags, result32)
    },
    AME_INT_MULSUB => {
      let (op_fflags, result32) = riscv_f32MulAdd(rm, ame_fp32_negate(rhs32), dest32, lhs32);
      ame_ocp_fp8_round_result(dtype, rm, input_fflags | op_fflags, result32)
    }
  }
}

function ame_ocp_fp8_unary_result(op : ame_int_unary_op,
                                  value : bits(ame_max_dtype_size))
  -> (bits_fflags, bits(ame_max_dtype_size)) = {
  let result : bits(8) = match op {
    AME_INT_ABS => [value[7 .. 0] with 7 = 0b0]
  };
  (zeros(), ame_ocp_fp8_result(result))
}

function ame_float_abs_result(dtype : bits(32), value : bits(ame_max_dtype_size))
  -> bits(ame_max_dtype_size) = {
  match ame_dtype_size(dtype) {
    16 => { let v : bits_H = [value[15 .. 0] with 15 = 0b0]; zero_extend(ame_max_dtype_size, v) },
    32 => { let v : bits_S = [value[31 .. 0] with 31 = 0b0]; zero_extend(ame_max_dtype_size, v) },
    64 => { let v : bits_D = [value[63 .. 0] with 63 = 0b0]; zero_extend(ame_max_dtype_size, v) },
    _  => internal_error(__FILE__, __LINE__, "unsupported AME float element size")
  }
}

function ame_float_negate_result(dtype : bits(32), value : bits(ame_max_dtype_size))
  -> bits(ame_max_dtype_size) = {
  match ame_dtype_size(dtype) {
    16 => { let v : bits_H = [value[15 .. 0] with 15 = not_bit(value[15])]; zero_extend(ame_max_dtype_size, v) },
    32 => { let v : bits_S = [value[31 .. 0] with 31 = not_bit(value[31])]; zero_extend(ame_max_dtype_size, v) },
    64 => { let v : bits_D = [value[63 .. 0] with 63 = not_bit(value[63])]; zero_extend(ame_max_dtype_size, v) },
    _  => internal_error(__FILE__, __LINE__, "unsupported AME float element size")
  }
}

function ame_float_binary_result(dtype : bits(32), op : ame_int_binary_op,
                                 rm : bits_rm,
                                 ms1_val : bits(ame_max_dtype_size),
                                 ms2_val : bits(ame_max_dtype_size))
  -> (bits_fflags, bits(ame_max_dtype_size)) = {
  if ame_is_ocp_fp8_dtype(dtype) then ame_ocp_fp8_binary_result(dtype, op, rm, ms1_val, ms2_val)
  else if ame_is_bf16_dtype(dtype) then ame_bf16_binary_result(op, rm, ms1_val, ms2_val)
  else match ame_dtype_size(dtype) {
    16 => {
      let lhs16 : bits_H = ms1_val[15 .. 0];
      let rhs16 : bits_H = ms2_val[15 .. 0];
      match op {
        AME_INT_ADD         => { let (f, r) = riscv_f16Add(rm, lhs16, rhs16); (f, zero_extend(ame_max_dtype_size, r)) },
        AME_INT_SUB_LHS_RHS => { let (f, r) = riscv_f16Sub(rm, lhs16, rhs16); (f, zero_extend(ame_max_dtype_size, r)) },
        AME_INT_SUB_RHS_LHS => { let (f, r) = riscv_f16Sub(rm, rhs16, lhs16); (f, zero_extend(ame_max_dtype_size, r)) },
        AME_INT_MAX         => { let (f, r) = ame_fp16_fmax(lhs16, rhs16); (f, zero_extend(ame_max_dtype_size, r)) },
        AME_INT_MIN         => { let (f, r) = ame_fp16_fmin(lhs16, rhs16); (f, zero_extend(ame_max_dtype_size, r)) },
        AME_INT_ABSDIFF     => { let (f, r) = riscv_f16Sub(rm, lhs16, rhs16); (f, ame_float_abs_result(dtype, zero_extend(ame_max_dtype_size, r))) },
        AME_INT_MUL         => { let (f, r) = riscv_f16Mul(rm, lhs16, rhs16); (f, zero_extend(ame_max_dtype_size, r)) },
        AME_INT_MULNEG      => { let neg_lhs = ame_float_negate_result(dtype, ms1_val); let (f, r) = riscv_f16Mul(rm, neg_lhs[15 .. 0], rhs16); (f, zero_extend(ame_max_dtype_size, r)) },
        AME_INT_CMPGE       => { let (f, r) = riscv_f16Le(rhs16, lhs16); (f, if r then ones() else zeros()) },
        AME_INT_CMPLT       => { let (f, r) = riscv_f16Lt(lhs16, rhs16); (f, if r then ones() else zeros()) },
        _ => internal_error(__FILE__, __LINE__, "unsupported AME float binary op")
      }
    },
    32 => ame_fp32_binary_result(op, rm, ms1_val, ms2_val),
    64 => {
      let lhs64 : bits_D = ms1_val[63 .. 0];
      let rhs64 : bits_D = ms2_val[63 .. 0];
      match op {
        AME_INT_ADD         => { let (f, r) = riscv_f64Add(rm, lhs64, rhs64); (f, zero_extend(ame_max_dtype_size, r)) },
        AME_INT_SUB_LHS_RHS => { let (f, r) = riscv_f64Sub(rm, lhs64, rhs64); (f, zero_extend(ame_max_dtype_size, r)) },
        AME_INT_SUB_RHS_LHS => { let (f, r) = riscv_f64Sub(rm, rhs64, lhs64); (f, zero_extend(ame_max_dtype_size, r)) },
        AME_INT_MAX         => { let (f, r) = ame_fp64_fmax(lhs64, rhs64); (f, zero_extend(ame_max_dtype_size, r)) },
        AME_INT_MIN         => { let (f, r) = ame_fp64_fmin(lhs64, rhs64); (f, zero_extend(ame_max_dtype_size, r)) },
        AME_INT_ABSDIFF     => { let (f, r) = riscv_f64Sub(rm, lhs64, rhs64); (f, ame_float_abs_result(dtype, zero_extend(ame_max_dtype_size, r))) },
        AME_INT_MUL         => { let (f, r) = riscv_f64Mul(rm, lhs64, rhs64); (f, zero_extend(ame_max_dtype_size, r)) },
        AME_INT_MULNEG      => { let neg_lhs = ame_float_negate_result(dtype, ms1_val); let (f, r) = riscv_f64Mul(rm, neg_lhs[63 .. 0], rhs64); (f, zero_extend(ame_max_dtype_size, r)) },
        AME_INT_CMPGE       => { let (f, r) = riscv_f64Le(rhs64, lhs64); (f, if r then ones() else zeros()) },
        AME_INT_CMPLT       => { let (f, r) = riscv_f64Lt(lhs64, rhs64); (f, if r then ones() else zeros()) },
        _ => internal_error(__FILE__, __LINE__, "unsupported AME float binary op")
      }
    },
    _ => internal_error(__FILE__, __LINE__, "unsupported AME float element size")
  }
}

function ame_float_ternary_result(dtype : bits(32), op : ame_int_ternary_op,
                                  rm : bits_rm,
                                  md_val : bits(ame_max_dtype_size),
                                  ms1_val : bits(ame_max_dtype_size),
                                  ms2_val : bits(ame_max_dtype_size))
  -> (bits_fflags, bits(ame_max_dtype_size)) = {
  if ame_is_ocp_fp8_dtype(dtype) then ame_ocp_fp8_ternary_result(dtype, op, rm, md_val, ms1_val, ms2_val)
  else if ame_is_bf16_dtype(dtype) then ame_bf16_ternary_result(op, rm, md_val, ms1_val, ms2_val)
  else match ame_dtype_size(dtype) {
    16 => {
      let dest16 : bits_H = md_val[15 .. 0];
      let lhs16 : bits_H = ms1_val[15 .. 0];
      let rhs16 : bits_H = ms2_val[15 .. 0];
      match op {
        AME_INT_MULACC  => { let (f, r) = riscv_f16MulAdd(rm, lhs16, rhs16, dest16); (f, zero_extend(ame_max_dtype_size, r)) },
        AME_INT_MULNACC => { let neg_lhs = ame_float_negate_result(dtype, ms1_val); let (f, r) = riscv_f16MulAdd(rm, neg_lhs[15 .. 0], rhs16, dest16); (f, zero_extend(ame_max_dtype_size, r)) },
        AME_INT_MULADD  => { let (f, r) = riscv_f16MulAdd(rm, rhs16, dest16, lhs16); (f, zero_extend(ame_max_dtype_size, r)) },
        AME_INT_MULSUB  => { let neg_rhs = ame_float_negate_result(dtype, ms2_val); let (f, r) = riscv_f16MulAdd(rm, neg_rhs[15 .. 0], dest16, lhs16); (f, zero_extend(ame_max_dtype_size, r)) }
      }
    },
    32 => ame_fp32_ternary_result(op, rm, md_val, ms1_val, ms2_val),
    64 => {
      let dest64 : bits_D = md_val[63 .. 0];
      let lhs64 : bits_D = ms1_val[63 .. 0];
      let rhs64 : bits_D = ms2_val[63 .. 0];
      match op {
        AME_INT_MULACC  => { let (f, r) = riscv_f64MulAdd(rm, lhs64, rhs64, dest64); (f, zero_extend(ame_max_dtype_size, r)) },
        AME_INT_MULNACC => { let neg_lhs = ame_float_negate_result(dtype, ms1_val); let (f, r) = riscv_f64MulAdd(rm, neg_lhs[63 .. 0], rhs64, dest64); (f, zero_extend(ame_max_dtype_size, r)) },
        AME_INT_MULADD  => { let (f, r) = riscv_f64MulAdd(rm, rhs64, dest64, lhs64); (f, zero_extend(ame_max_dtype_size, r)) },
        AME_INT_MULSUB  => { let neg_rhs = ame_float_negate_result(dtype, ms2_val); let (f, r) = riscv_f64MulAdd(rm, neg_rhs[63 .. 0], dest64, lhs64); (f, zero_extend(ame_max_dtype_size, r)) }
      }
    },
    _ => internal_error(__FILE__, __LINE__, "unsupported AME float element size")
  }
}

function ame_float_unary_result(dtype : bits(32), op : ame_int_unary_op,
                                value : bits(ame_max_dtype_size))
  -> (bits_fflags, bits(ame_max_dtype_size)) = {
  if ame_is_ocp_fp8_dtype(dtype) then ame_ocp_fp8_unary_result(op, value)
  else if ame_is_bf16_dtype(dtype) then ame_bf16_unary_result(op, value)
  else {
    let result : bits(ame_max_dtype_size) = match op {
      AME_INT_ABS => ame_float_abs_result(dtype, value)
    };
    (zeros(), result)
  }
}
