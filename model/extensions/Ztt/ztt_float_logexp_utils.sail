// =====================================================================
// Float log/exp (mexp2 / mlog2 / mlog2sub / msublog2 / mldexp / mldexpacc /
// mrdexp / mrdexpacc) helper semantics.
//
// The transcendental members of the family (mexp2, mlog2, mlog2sub,
// msublog2) are implementation-defined approximations; this model evaluates
// them in FP32 with the host libm (<= 2 ulp, host glibc) exactly like the
// other Ztt float-math instructions, widening/narrowing the narrow storage
// formats around the FP32 evaluation.
//
// The scaled members (mldexp, mldexpacc, mrdexp, mrdexpacc) must round the
// exact mathematical value  a * 2^k  (and, for the accumulating forms,
// old + a * 2^k) exactly once to the destination format, including for FP64
// and for the narrow FP16 / BF16 / OCP-FP8 formats.  Those paths are
// implemented below with Sail's arbitrary-precision integers so no
// intermediate floating-point rounding can occur.
//
// Only amefflags is updated on these paths; the integer amexsat sticky bit is
// never touched by a floating-point logexp result.
// =====================================================================

enum ame_fp_class = {
  AME_FP_CLASS_ZERO,
  AME_FP_CLASS_SUBNORMAL,
  AME_FP_CLASS_NORMAL,
  AME_FP_CLASS_INF,
  AME_FP_CLASS_QNAN,
  AME_FP_CLASS_SNAN
}

struct ame_fp_layout = {
  mant_bits : nat,   // stored fraction bits
  bias      : nat,
  exp_bits  : nat,
  has_inf   : bool,
  max_ef    : nat,   // exponent field of the largest finite value
  max_frac  : nat    // fraction of the largest finite value
}

struct ame_fp_dec = {
  cls  : ame_fp_class,
  sign : bits(1),
  sig  : int,        // > 0 for finite non-zero; value = (-1)^sign * sig * 2^exp2
  exp2 : int
}

function ame_fp_layout_of(dtype : bits(32)) -> ame_fp_layout =
  match ame_dtype_without_rounding(dtype) {
    0x10100108 => struct { mant_bits = 3,  bias = 7,    exp_bits = 4,  has_inf = false, max_ef = 15,   max_frac = 6 },
    0x14300108 => struct { mant_bits = 2,  bias = 15,   exp_bits = 5,  has_inf = true,  max_ef = 30,   max_frac = 3 },
    0x14300110 => struct { mant_bits = 10, bias = 15,   exp_bits = 5,  has_inf = true,  max_ef = 30,   max_frac = 1023 },
    0x20300110 => struct { mant_bits = 7,  bias = 127,  exp_bits = 8,  has_inf = true,  max_ef = 254,  max_frac = 127 },
    0x20300120 => struct { mant_bits = 23, bias = 127,  exp_bits = 8,  has_inf = true,  max_ef = 254,  max_frac = 8388607 },
    0x2c300140 => struct { mant_bits = 52, bias = 1023, exp_bits = 11, has_inf = true,  max_ef = 2046, max_frac = 4503599627370495 },
    _          => internal_error(__FILE__, __LINE__, "unsupported AME float dtype")
  }

// AME_MAX_INT_DTYPE (Int128, descriptor 0x40000080).  The .ew.x exponent
// control is a signed 128-bit integer; on RV64 it is the zero-extended rs1
// value, whose sign bit is clear, so the exponent is always non-negative.
function ame_max_int_dtype_descriptor() -> bits(32) = 0x40000080

// --- raw field extraction -------------------------------------------------

function ame_fp_raw_fields(dtype : bits(32), value : bits(ame_max_dtype_size))
  -> (bits(1), int, int) =
  match ame_dtype_without_rounding(dtype) {
    0x10100108 => { let v : bits(8) = value[7 .. 0];
                    (v[7 .. 7], unsigned(v[6 .. 3]), unsigned(v[2 .. 0])) },
    0x14300108 => { let v : bits(8) = value[7 .. 0];
                    (v[7 .. 7], unsigned(v[6 .. 2]), unsigned(v[1 .. 0])) },
    0x14300110 => { let v : bits_H = value[15 .. 0];
                    (v[15 .. 15], unsigned(v[14 .. 10]), unsigned(v[9 .. 0])) },
    0x20300110 => { let v : bits_BF16 = value[15 .. 0];
                    (v[15 .. 15], unsigned(v[14 .. 7]), unsigned(v[6 .. 0])) },
    0x20300120 => { let v : bits_S = value[31 .. 0];
                    (v[31 .. 31], unsigned(v[30 .. 23]), unsigned(v[22 .. 0])) },
    0x2c300140 => { let v : bits_D = value[63 .. 0];
                    (v[63 .. 63], unsigned(v[62 .. 52]), unsigned(v[51 .. 0])) },
    _          => internal_error(__FILE__, __LINE__, "unsupported AME float dtype")
  }

// Constructive power of two over the integers.  Expressing it as a loop makes
// the exponent's non-negativity a structural fact of this function rather than
// an obligation the backend has to discharge at every `2 ^ e` use site (the C
// backend cannot resolve such goals from branch conditions).
//
// Precondition: exp >= 0.  Every call site derives it from a non-negative
// quantity (a field width, a bit length, or a shift already known positive);
// the `while` loop defines the result as 1 for a negative exponent, which no
// reachable path can ask for.
function ame_int_pow2(exp : int) -> int = {
  var result : int = 1;
  var i : int = 0;
  while i < exp do {
    result = result * 2;
    i = i + 1
  };
  result
}

function ame_fp_class_of(layout : ame_fp_layout, ef : int, frac : int) -> ame_fp_class = {
  let exp_ones = (ame_int_pow2(layout.exp_bits)) - 1;
  if layout.has_inf then {
    if ef == exp_ones then
      (if frac == 0 then AME_FP_CLASS_INF
       else if 2 * frac >= ame_int_pow2(layout.mant_bits) then AME_FP_CLASS_QNAN
       else AME_FP_CLASS_SNAN)
    else if ef == 0 then
      (if frac == 0 then AME_FP_CLASS_ZERO else AME_FP_CLASS_SUBNORMAL)
    else AME_FP_CLASS_NORMAL
  } else {
    // OCP E4M3 has no infinity: only an all-ones significand at the top
    // exponent is the canonical NaN, everything else is finite.
    if ef == exp_ones & frac == ame_int_pow2(layout.mant_bits) - 1 then AME_FP_CLASS_QNAN
    else if ef == 0 then
      (if frac == 0 then AME_FP_CLASS_ZERO else AME_FP_CLASS_SUBNORMAL)
    else AME_FP_CLASS_NORMAL
  }
}

function ame_fp_decode(dtype : bits(32), value : bits(ame_max_dtype_size)) -> ame_fp_dec = {
  let layout = ame_fp_layout_of(dtype);
  let (sign, ef, frac) = ame_fp_raw_fields(dtype, value);
  let cls = ame_fp_class_of(layout, ef, frac);
  let (sig, exp2) : (int, int) = match cls {
    AME_FP_CLASS_NORMAL    => (ame_int_pow2(layout.mant_bits) + frac,
                               ef - layout.bias - layout.mant_bits),
    AME_FP_CLASS_SUBNORMAL => (frac, 1 - layout.bias - layout.mant_bits),
    _                      => (0, 0)
  };
  struct { cls = cls, sign = sign, sig = sig, exp2 = exp2 }
}

// --- encoding -------------------------------------------------------------

function ame_fp_encode(dtype : bits(32), sign : bits(1), ef : int, frac : int)
  -> bits(ame_max_dtype_size) =
  match ame_dtype_without_rounding(dtype) {
    0x10100108 => zero_extend(ame_max_dtype_size, sign @ to_bits_unsafe(4, ef) @ to_bits_unsafe(3, frac)),
    0x14300108 => zero_extend(ame_max_dtype_size, sign @ to_bits_unsafe(5, ef) @ to_bits_unsafe(2, frac)),
    0x14300110 => zero_extend(ame_max_dtype_size, sign @ to_bits_unsafe(5, ef) @ to_bits_unsafe(10, frac)),
    0x20300110 => zero_extend(ame_max_dtype_size, sign @ to_bits_unsafe(8, ef) @ to_bits_unsafe(7, frac)),
    0x20300120 => zero_extend(ame_max_dtype_size, sign @ to_bits_unsafe(8, ef) @ to_bits_unsafe(23, frac)),
    0x2c300140 => zero_extend(ame_max_dtype_size, sign @ to_bits_unsafe(11, ef) @ to_bits_unsafe(52, frac)),
    _          => internal_error(__FILE__, __LINE__, "unsupported AME float dtype")
  }

function ame_fp_nan(dtype : bits(32)) -> bits(ame_max_dtype_size) =
  match ame_dtype_without_rounding(dtype) {
    0x10100108 => zero_extend(ame_max_dtype_size, 0x7F),
    0x14300108 => zero_extend(ame_max_dtype_size, 0x7F),
    0x14300110 => zero_extend(ame_max_dtype_size, 0x7E00),
    0x20300110 => zero_extend(ame_max_dtype_size, 0x7FC0),
    0x20300120 => zero_extend(ame_max_dtype_size, 0x7FC00000),
    0x2c300140 => zero_extend(ame_max_dtype_size, 0x7FF8000000000000),
    _          => internal_error(__FILE__, __LINE__, "unsupported AME float dtype")
  }

function ame_fp_inf(dtype : bits(32), sign : bits(1)) -> bits(ame_max_dtype_size) = {
  let layout = ame_fp_layout_of(dtype);
  if layout.has_inf then ame_fp_encode(dtype, sign, (ame_int_pow2(layout.exp_bits)) - 1, 0)
  else ame_fp_encode(dtype, sign, layout.max_ef, layout.max_frac)
}

// --- integer rounding primitives -----------------------------------------

function ame_int_bit_length(value : int) -> int = {
  var bits : int = 0;
  var rest : int = value;
  while rest > 0 do {
    bits = bits + 1;
    rest = quot_round_zero(rest, 2)
  };
  bits
}


// Round the integer quotient of `value / 2^shift` where the exact magnitude
// is `value / 2^shift` plus an infinitesimal of sign delta (-1, 0 or +1).
function ame_fp_round_units_gen(sign : bits(1), rm : bits_rm,
                                q : int, r : int, shift : int, delta : int)
  -> (bool, int) = {
  if r == 0 & delta == 0 then (false, q)
  else if r == 0 then {
    // Magnitude is q + delta * epsilon.
    let q_odd = q - quot_round_zero(q, 2) * 2 == 1;
    let rounded : int = match rm {
      0b001 => if delta < 0 then q - 1 else q,                          // RTZ
      0b010 => if sign == 0b1 then (if delta < 0 then q else q + 1)     // RDN
               else (if delta < 0 then q - 1 else q),
      0b011 => if sign == 0b0 then (if delta < 0 then q else q + 1)     // RUP
               else (if delta < 0 then q - 1 else q),
      0b110 => if q_odd then q else (if delta < 0 then q - 1 else q + 1), // RNO
      _     => q                                                        // RNE / RMM
    };
    (true, rounded)
  }
  else {
    let halfway = ame_int_pow2(shift - 1);
    let q_odd = q - quot_round_zero(q, 2) * 2 == 1;
    let above = r > halfway | (r == halfway & delta > 0);
    let at    = r == halfway & delta == 0;
    let increment : bool = match rm {
      0b000 => above | (at & q_odd),  // RNE: ties to even
      0b001 => false,                 // RTZ
      0b010 => sign == 0b1,           // RDN
      0b011 => sign == 0b0,           // RUP
      0b100 => above | at,            // RMM: ties away
      0b110 => not(q_odd),            // RNO: round to odd
      _     => above | (at & q_odd)
    };
    (true, if increment then q + 1 else q)
  }
}

function ame_fp_round_units(sign : bits(1), rm : bits_rm,
                            value : int, shift : int, delta : int) -> (bool, int) = {
  if shift <= 0 then
    // The value already sits on the grid; a nonzero delta still makes the
    // exact result inexact and can flip a round-to-odd/directed decision.
    ame_fp_round_units_gen(sign, rm, value * (ame_int_pow2(0 - shift)), 0, 1, delta)
  else {
    let bits = ame_int_bit_length(value);
    if shift > bits then
      // value / 2^shift < 2^(bits - shift) <= 1/2; a coarser grid keeps the
      // exact fraction strictly below one half and preserves the decision.
      ame_fp_round_units_gen(sign, rm, 0, value, bits + 1, delta)
    else {
      let divisor = 2 ^ shift;
      let q = quot_round_zero(value, divisor);
      ame_fp_round_units_gen(sign, rm, q, value - q * divisor, shift, delta)
    }
  }
}

function ame_fp_encode_overflow(dtype : bits(32), layout : ame_fp_layout,
                                sign : bits(1), rm : bits_rm)
  -> bits(ame_max_dtype_size) =
  if layout.has_inf & ame_float_overflow_to_inf(sign, rm) then
    ame_fp_encode(dtype, sign, (ame_int_pow2(layout.exp_bits)) - 1, 0)
  else
    ame_fp_encode(dtype, sign, layout.max_ef, layout.max_frac)

// Round (-1)^sign * sig * 2^exp2 to `dtype` with rounding mode rm.  `delta`
// folds an addend that is strictly below the rounding grid into a sticky bit.
function ame_fp_round_magnitude(dtype : bits(32), rm : bits_rm, sign : bits(1),
                                sig : int, exp2 : int, delta : int)
  -> (bits_fflags, bits(ame_max_dtype_size)) = {
  let layout = ame_fp_layout_of(dtype);
  let emin_normal = 1 - layout.bias;
  let emin_sub = 1 - layout.bias - layout.mant_bits;
  let bits = ame_int_bit_length(sig);
  let top = exp2 + bits - 1;
  if top >= emin_normal then {
    let shift = (top - layout.mant_bits) - exp2;
    let (inexact, rounded) : (bool, int) =
      ame_fp_round_units(sign, rm, sig, shift, delta);
    var q : int = rounded;
    var t : int = top;
    if q >= ame_int_pow2(layout.mant_bits + 1) then {
      // Rounding carried out of the significand; the right shift is exact.
      q = quot_round_zero(q, 2);
      t = t + 1
    }
    else if q < ame_int_pow2(layout.mant_bits) then {
      // A tiny subtractive addend can step below the bottom of the binade.
      // Renormalize onto the predecessor significand, or leave the value as
      // the largest subnormal when this was already the smallest normal
      // binade.
      if t > emin_normal then {
        q = (ame_int_pow2(layout.mant_bits + 1)) - 1;
        t = t - 1
      }
    };
    if q >= ame_int_pow2(layout.mant_bits) then {
      let ef = t + layout.bias;
      let frac = q - ame_int_pow2(layout.mant_bits);
      if ef > layout.max_ef | (ef == layout.max_ef & frac > layout.max_frac) then
        (0b00101, ame_fp_encode_overflow(dtype, layout, sign, rm))
      else
        ((if inexact then 0b00001 else 0b00000), ame_fp_encode(dtype, sign, ef, frac))
    }
    else
      (ame_ocp_subnormal_flags(inexact, false), ame_fp_encode(dtype, sign, 0, q))
  }
  else {
    let shift = emin_sub - exp2;
    let (inexact, rounded) : (bool, int) =
      ame_fp_round_units(sign, rm, sig, shift, delta);
    if rounded >= ame_int_pow2(layout.mant_bits) then
      // Rounded up to the minimum normal: tiny after rounding is false.
      ((if inexact then 0b00001 else 0b00000), ame_fp_encode(dtype, sign, 1, 0))
    else
      (ame_ocp_subnormal_flags(inexact, false),
       ame_fp_encode(dtype, sign, 0, rounded))
  }
}

// Exact single rounding of the sum of two finite non-zero binary values.
function ame_fp_add_round(dtype : bits(32), rm : bits_rm,
                          sign_a : bits(1), sig_a : int, exp_a : int,
                          sign_b : bits(1), sig_b : int, exp_b : int)
  -> (bits_fflags, bits(ame_max_dtype_size)) = {
  let layout = ame_fp_layout_of(dtype);
  let emin_normal = 1 - layout.bias;
  let emin_sub = 1 - layout.bias - layout.mant_bits;
  let bits_a = ame_int_bit_length(sig_a);
  let bits_b = ame_int_bit_length(sig_b);
  let top_a = exp_a + bits_a - 1;
  let top_b = exp_b + bits_b - 1;
  // Keep the larger-magnitude operand in the "a" slots.
  let (sa, Ma, ea, ta, sb, Mb, eb, tb)
    : (bits(1), int, int, int, bits(1), int, int, int) =
    if top_a >= top_b then (sign_a, sig_a, exp_a, top_a, sign_b, sig_b, exp_b, top_b)
    else (sign_b, sig_b, exp_b, top_b, sign_a, sig_a, exp_a, top_a);
  let lsb = if ta >= emin_normal then ta - layout.mant_bits else emin_sub;
  // The smaller operand is negligible as a tie breaker when it is strictly
  // below both the relevant rounding threshold and the granularity of the
  // larger operand.  Subtracting from a value that is exactly a power of two
  // halves the distance to the predecessor, so directed/nearest decisions
  // there need the quarter-ulp threshold rather than the half-ulp one.
  let threshold = if sa == sb then lsb - 1 else lsb - 2;
  let negligible_below = if threshold <= ea then threshold else ea;
  if tb < negligible_below then
    ame_fp_round_magnitude(dtype, rm, sa, Ma, ea, if sb == sa then 1 else -1)
  else {
    // Exact alignment; the exponent difference is bounded by the rounding
    // window because the smaller operand reaches into the guard bits.
    let w = if ea <= eb then ea else eb;
    let ia = Ma * (ame_int_pow2(ea - w));
    let ib = Mb * (ame_int_pow2(eb - w));
    let signed_a = if sa == 0b0 then ia else 0 - ia;
    let signed_b = if sb == 0b0 then ib else 0 - ib;
    let total = signed_a + signed_b;
    if total == 0 then
      // Exact cancellation: +0, except -0 under round-toward-negative.
      (zeros(), ame_fp_encode(dtype, if rm == 0b010 then 0b1 else 0b0, 0, 0))
    else
      ame_fp_round_magnitude(dtype, rm,
        (if total >= 0 then 0b0 else 0b1), abs_int(total), w, 0)
  }
}

// --- mldexp / mldexpacc / mrdexp / mrdexpacc ------------------------------

function ame_fp_ldexp_result(dtype : bits(32), rm : bits_rm,
                             accumulate : bool, negate_exp : bool,
                             data_val : bits(ame_max_dtype_size),
                             md_val : bits(ame_max_dtype_size),
                             exp_value : int)
  -> (bits_fflags, bits(ame_max_dtype_size)) = {
  let k = if negate_exp then 0 - exp_value else exp_value;
  let d = ame_fp_decode(dtype, data_val);
  let o = ame_fp_decode(dtype, md_val);
  let nan_flags : bits_fflags =
    (if d.cls == AME_FP_CLASS_SNAN then 0b10000 else 0b00000) |
    (if accumulate & o.cls == AME_FP_CLASS_SNAN then 0b10000 else 0b00000);
  if d.cls == AME_FP_CLASS_QNAN | d.cls == AME_FP_CLASS_SNAN then
    (nan_flags, ame_fp_nan(dtype))
  else if accumulate & (o.cls == AME_FP_CLASS_QNAN | o.cls == AME_FP_CLASS_SNAN) then
    (nan_flags, ame_fp_nan(dtype))
  else if accumulate & o.cls == AME_FP_CLASS_INF then {
    if d.cls == AME_FP_CLASS_INF & d.sign != o.sign then (0b10000, ame_fp_nan(dtype))
    else (zeros(), ame_fp_inf(dtype, o.sign))
  }
  else if d.cls == AME_FP_CLASS_INF then (zeros(), ame_fp_inf(dtype, d.sign))
  else if d.cls == AME_FP_CLASS_ZERO then {
    if not(accumulate) then (zeros(), ame_fp_encode(dtype, d.sign, 0, 0))
    else if o.cls == AME_FP_CLASS_ZERO then {
      let zero_sign = if o.sign == d.sign then o.sign
                      else (if rm == 0b010 then 0b1 else 0b0);
      (zeros(), ame_fp_encode(dtype, zero_sign, 0, 0))
    }
    else (zeros(), md_val)
  }
  else if accumulate & o.cls == AME_FP_CLASS_ZERO then
    ame_fp_round_magnitude(dtype, rm, d.sign, d.sig, d.exp2 + k, 0)
  else if not(accumulate) then
    ame_fp_round_magnitude(dtype, rm, d.sign, d.sig, d.exp2 + k, 0)
  else
    ame_fp_add_round(dtype, rm, o.sign, o.sig, o.exp2, d.sign, d.sig, d.exp2 + k)
}

// --- mexp2 / mlog2 (FP32 core) -------------------------------------------

function ame_fp32_logexp_result(op : ame_int_logexp_op, value : bits_S)
  -> (bits_fflags, bits_S) = {
  let exp_field = value[30 .. 23];
  let frac = value[22 .. 0];
  if exp_field == 0xFF & frac != zeros() then
    (if value[22] == 0b0 then 0b10000 else 0b00000, 0x7FC00000)
  else if op == AME_INT_EXP2 then {
    if exp_field == 0xFF then
      (zeros(), if value[31] == 0b0 then 0x7F800000 else 0x00000000)
    else if exp_field == 0x00 & frac == zeros() then (zeros(), 0x3F800000)
    else (zeros(), ame_ztt_f32exp2(value))
  } else {
    if exp_field == 0x00 & frac == zeros() then (0b01000, 0xFF800000)
    else if value[31] == 0b1 then (0b10000, 0x7FC00000)
    else if exp_field == 0xFF then (zeros(), 0x7F800000)
    else (zeros(), ame_ztt_f32log2(value))
  }
}

// log2(|a|) - b  (LOG2SUB) or  b - log2(|a|)  (SUBLOG2).
function ame_fp32_log2bias_result(op : ame_int_logexp_op, rm : bits_rm,
                                  a : bits_S, b : bits_S) -> (bits_fflags, bits_S) = {
  let exp_field = a[30 .. 23];
  let frac = a[22 .. 0];
  let (log_flags, l) =
    if exp_field == 0xFF & frac != zeros() then
      (if a[22] == 0b0 then 0b10000 else 0b00000, 0x7FC00000)
    else if exp_field == 0x00 & frac == zeros() then (0b01000, 0xFF800000)
    else (zeros(), ame_ztt_f32log2(ame_fp32_abs(a)));
  let (sub_flags, r) =
    if op == AME_INT_SUBLOG2 then riscv_f32Sub(rm, b, l)
    else riscv_f32Sub(rm, l, b);
  (log_flags | sub_flags, r)
}

// --- mexp2 / mlog2 (FP64 core) -------------------------------------------

function ame_fp64_logexp_result(op : ame_int_logexp_op, value : bits_D)
  -> (bits_fflags, bits(ame_max_dtype_size)) = {
  let exp_field = value[62 .. 52];
  let frac = value[51 .. 0];
  if exp_field == 0b11111111111 & frac != zeros() then
    (if value[51] == 0b0 then 0b10000 else 0b00000,
     zero_extend(ame_max_dtype_size, 0x7FF8000000000000))
  else if op == AME_INT_EXP2 then {
    if exp_field == 0b11111111111 then
      (zeros(), zero_extend(ame_max_dtype_size,
        if value[63] == 0b0 then 0x7FF0000000000000 else 0x0000000000000000))
    else if exp_field == zeros() & frac == zeros() then
      (zeros(), zero_extend(ame_max_dtype_size, 0x3FF0000000000000))
    else (zeros(), zero_extend(ame_max_dtype_size, ame_ztt_f64exp2(value)))
  } else {
    if exp_field == zeros() & frac == zeros() then
      (0b01000, zero_extend(ame_max_dtype_size, 0xFFF0000000000000))
    else if value[63] == 0b1 then
      (0b10000, zero_extend(ame_max_dtype_size, 0x7FF8000000000000))
    else if exp_field == 0b11111111111 then
      (zeros(), zero_extend(ame_max_dtype_size, 0x7FF0000000000000))
    else (zeros(), zero_extend(ame_max_dtype_size, ame_ztt_f64log2(value)))
  }
}

function ame_fp64_log2bias_result(op : ame_int_logexp_op, rm : bits_rm,
                                  a : bits_D, b : bits_D)
  -> (bits_fflags, bits(ame_max_dtype_size)) = {
  let exp_field = a[62 .. 52];
  let frac = a[51 .. 0];
  let (log_flags, l) : (bits_fflags, bits_D) =
    if exp_field == 0b11111111111 & frac != zeros() then
      (if a[51] == 0b0 then 0b10000 else 0b00000, 0x7FF8000000000000)
    else if exp_field == zeros() & frac == zeros() then (0b01000, 0xFFF0000000000000)
    else (zeros(), ame_ztt_f64log2([a with 63 .. 63 = 0b0]));
  let (sub_flags, r) =
    if op == AME_INT_SUBLOG2 then riscv_f64Sub(rm, b, l)
    else riscv_f64Sub(rm, l, b);
  (log_flags | sub_flags, zero_extend(ame_max_dtype_size, r))
}

// --- format dispatch ------------------------------------------------------

// Storage formats narrower than FP32 evaluate the transcendental in FP32 and
// narrow once, matching the documented approximation budget of the other Ztt
// float-math instructions.
function ame_float_logexp_unary_result(dtype : bits(32), op : ame_int_logexp_op,
                                       rm : bits_rm, value : bits(ame_max_dtype_size))
  -> (bits_fflags, bits(ame_max_dtype_size)) = {
  if ame_is_ocp_fp8_dtype(dtype) then {
    let (input_flags, input32) = ame_ocp_fp8_to_f32(dtype, value);
    let (op_flags, result32) = ame_fp32_logexp_result(op, input32);
    ame_ocp_fp8_round_result(dtype, rm, input_flags | op_flags, result32)
  } else if ame_is_bf16_dtype(dtype) then {
    let (input_flags, input32) = ame_bf16_to_f32(value);
    let (op_flags, result32) = ame_fp32_logexp_result(op, input32);
    ame_bf16_round_result(rm, input_flags | op_flags, result32)
  } else match ame_dtype_size(dtype) {
    16 => {
      let (input_flags, input32) = riscv_f16ToF32(rm, value[15 .. 0]);
      let (op_flags, result32) = ame_fp32_logexp_result(op, input32);
      let (round_flags, result16) = riscv_f32ToF16(rm, result32);
      (input_flags | op_flags | round_flags,
       zero_extend(ame_max_dtype_size, result16))
    },
    32 => {
      let (op_flags, result32) = ame_fp32_logexp_result(op, value[31 .. 0]);
      (op_flags, zero_extend(ame_max_dtype_size, result32))
    },
    64 => ame_fp64_logexp_result(op, value[63 .. 0]),
    _  => internal_error(__FILE__, __LINE__, "unsupported AME float logexp dtype")
  }
}

function ame_float_log2bias_result(dtype : bits(32), op : ame_int_logexp_op,
                                   rm : bits_rm,
                                   lhs_val : bits(ame_max_dtype_size),
                                   rhs_val : bits(ame_max_dtype_size))
  -> (bits_fflags, bits(ame_max_dtype_size)) = {
  if ame_is_ocp_fp8_dtype(dtype) then {
    let (lhs_flags, lhs32) = ame_ocp_fp8_to_f32(dtype, lhs_val);
    let (rhs_flags, rhs32) = ame_ocp_fp8_to_f32(dtype, rhs_val);
    let (op_flags, result32) = ame_fp32_log2bias_result(op, rm, lhs32, rhs32);
    ame_ocp_fp8_round_result(dtype, rm, lhs_flags | rhs_flags | op_flags, result32)
  } else if ame_is_bf16_dtype(dtype) then {
    let (lhs_flags, lhs32) = ame_bf16_to_f32(lhs_val);
    let (rhs_flags, rhs32) = ame_bf16_to_f32(rhs_val);
    let (op_flags, result32) = ame_fp32_log2bias_result(op, rm, lhs32, rhs32);
    ame_bf16_round_result(rm, lhs_flags | rhs_flags | op_flags, result32)
  } else match ame_dtype_size(dtype) {
    16 => {
      let (lhs_flags, lhs32) = riscv_f16ToF32(rm, lhs_val[15 .. 0]);
      let (rhs_flags, rhs32) = riscv_f16ToF32(rm, rhs_val[15 .. 0]);
      let (op_flags, result32) = ame_fp32_log2bias_result(op, rm, lhs32, rhs32);
      let (round_flags, result16) = riscv_f32ToF16(rm, result32);
      (lhs_flags | rhs_flags | op_flags | round_flags,
       zero_extend(ame_max_dtype_size, result16))
    },
    32 => {
      let (op_flags, result32) =
        ame_fp32_log2bias_result(op, rm, lhs_val[31 .. 0], rhs_val[31 .. 0]);
      (op_flags, zero_extend(ame_max_dtype_size, result32))
    },
    64 => ame_fp64_log2bias_result(op, rm, lhs_val[63 .. 0], rhs_val[63 .. 0]),
    _  => internal_error(__FILE__, __LINE__, "unsupported AME float logexp dtype")
  }
}
