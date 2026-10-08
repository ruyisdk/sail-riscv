// Floating-point elementwise math instruction helpers.

// Default NaN encodings (IEEE-754 / softfloat defaults, matching the
// defaultNaN the other softfloat operations produce).
let defaultNaN32 : bits_S = 0x7fc00000

function ame_fp32_math_result(op : ame_float_math_op, rm : bits_rm, value : bits_S)
  -> (bits_fflags, bits_S) = {
  let one : bits_S = 0x3f800000;
  match op {
    AME_FLOAT_SQRT          => riscv_f32Sqrt(rm, value),
    AME_FLOAT_RECIPROCAL    => riscv_f32Div(rm, one, value),
    AME_FLOAT_RSQRT         => {
      let (sqrt_flags, sqrt_value) = riscv_f32Sqrt(rm, value);
      let (div_flags, result) = riscv_f32Div(rm, one, sqrt_value);
      (sqrt_flags | div_flags, result)
    },
    AME_FLOAT_ROUND_DOWN    => riscv_f32roundToInt(0b010, value, true),
    AME_FLOAT_ROUND_NEAREST => riscv_f32roundToInt(0b000, value, true),
    AME_FLOAT_ROUND_UP      => riscv_f32roundToInt(0b011, value, true),
    AME_FLOAT_ROUND_ZERO    => riscv_f32roundToInt(0b001, value, true),
    AME_FLOAT_COS => {
      // Spec: cos(+-0) = +1; an infinite input is invalid.  A signaling NaN
      // input raises NV and returns the default NaN; a quiet NaN propagates
      // without NV.  Numeric core: host libm (glibc, documented <= 2 ulp
      // budget).
      if (value[30 .. 23] == 0xff) & (value[22 .. 0] != zeros()) then
        (if value[22] == 0b0 then 0b10000 else zeros(), defaultNaN32)
      else if value[30 .. 23] == 0xff then (0b10000, defaultNaN32)
      else (zeros(), ame_ztt_f32cos(value))
    },
    AME_FLOAT_SIN => {
      if (value[30 .. 23] == 0xff) & (value[22 .. 0] != zeros()) then
        (if value[22] == 0b0 then 0b10000 else zeros(), defaultNaN32)
      else if value[30 .. 23] == 0xff then (0b10000, defaultNaN32)
      else (zeros(), ame_ztt_f32sin(value))
    },
    AME_FLOAT_TANH => {
      // tanh(+-inf) = +-1; the finite/NaN handling matches cos above.
      if (value[30 .. 23] == 0xff) & (value[22 .. 0] != zeros()) then
        (if value[22] == 0b0 then 0b10000 else zeros(), defaultNaN32)
      else (zeros(), ame_ztt_f32tanh(value))
    }
  }
}

function ame_bf16_math_result(op : ame_float_math_op, rm : bits_rm,
                              value : bits(ame_max_dtype_size))
  -> (bits_fflags, bits(ame_max_dtype_size)) = {
  let (input_flags, input32) = ame_bf16_to_f32(value);
  let (op_flags, result32) = ame_fp32_math_result(op, rm, input32);
  ame_bf16_round_result(rm, input_flags | op_flags, result32)
}

function ame_ocp_fp8_math_result(dtype : bits(32), op : ame_float_math_op,
                                 rm : bits_rm, value : bits(ame_max_dtype_size))
  -> (bits_fflags, bits(ame_max_dtype_size)) = {
  let (input_flags, input32) = ame_ocp_fp8_to_f32(dtype, value);
  let (op_flags, result32) = ame_fp32_math_result(op, rm, input32);
  ame_ocp_fp8_round_result(dtype, rm, input_flags | op_flags, result32)
}

function ame_float_math_result(dtype : bits(32), op : ame_float_math_op,
                               rm : bits_rm, value : bits(ame_max_dtype_size))
  -> (bits_fflags, bits(ame_max_dtype_size)) = {
  if ame_is_ocp_fp8_dtype(dtype) then ame_ocp_fp8_math_result(dtype, op, rm, value)
  else if ame_is_bf16_dtype(dtype) then ame_bf16_math_result(op, rm, value)
  else match ame_dtype_size(dtype) {
    16 => {
      let input : bits_H = value[15 .. 0];
      let one : bits_H = 0x3c00;
      if op == AME_FLOAT_COS | op == AME_FLOAT_SIN | op == AME_FLOAT_TANH then {
        // Transcendentals compute in f32 (exact widening, host libm, then a
        // rounded narrowing back to f16), matching the narrow-format path
        // of the other AME float instructions.
        let (conv_flags, input32) = riscv_f16ToF32(rm, input);
        let (op_flags, result32) = ame_fp32_math_result(op, rm, input32);
        let (round_flags, result) = riscv_f32ToF16(rm, result32);
        (conv_flags | op_flags | round_flags, zero_extend(ame_max_dtype_size, result))
      } else {
        let (flags, result) : (bits_fflags, bits_H) = match op {
          AME_FLOAT_SQRT          => riscv_f16Sqrt(rm, input),
          AME_FLOAT_RECIPROCAL    => riscv_f16Div(rm, one, input),
          AME_FLOAT_RSQRT         => {
            let (sqrt_flags, sqrt_value) = riscv_f16Sqrt(rm, input);
            let (div_flags, quotient) = riscv_f16Div(rm, one, sqrt_value);
            (sqrt_flags | div_flags, quotient)
          },
          AME_FLOAT_ROUND_DOWN    => riscv_f16roundToInt(0b010, input, true),
          AME_FLOAT_ROUND_NEAREST => riscv_f16roundToInt(0b000, input, true),
          AME_FLOAT_ROUND_UP      => riscv_f16roundToInt(0b011, input, true),
          AME_FLOAT_ROUND_ZERO    => riscv_f16roundToInt(0b001, input, true)
        };
        (flags, zero_extend(ame_max_dtype_size, result))
      }
    },
    32 => {
      let (flags, result) = ame_fp32_math_result(op, rm, value[31 .. 0]);
      (flags, zero_extend(ame_max_dtype_size, result))
    },
    64 => {
      let input : bits_D = value[63 .. 0];
      let one : bits_D = 0x3ff0000000000000;
      let (flags, result) : (bits_fflags, bits_D) = match op {
        AME_FLOAT_SQRT          => riscv_f64Sqrt(rm, input),
        AME_FLOAT_RECIPROCAL    => riscv_f64Div(rm, one, input),
        AME_FLOAT_RSQRT         => {
          let (sqrt_flags, sqrt_value) = riscv_f64Sqrt(rm, input);
          let (div_flags, quotient) = riscv_f64Div(rm, one, sqrt_value);
          (sqrt_flags | div_flags, quotient)
        },
        AME_FLOAT_ROUND_DOWN    => riscv_f64roundToInt(0b010, input, true),
        AME_FLOAT_ROUND_NEAREST => riscv_f64roundToInt(0b000, input, true),
        AME_FLOAT_ROUND_UP      => riscv_f64roundToInt(0b011, input, true),
        AME_FLOAT_ROUND_ZERO    => riscv_f64roundToInt(0b001, input, true),
        AME_FLOAT_COS => {
          if ((value[63 .. 52] & 0x7ff) == 0x7ff) & (value[51 .. 0] != zeros()) then
            (if value[51] == 0b0 then 0b10000 else zeros(), 0x7ff8000000000000)
          else if (value[63 .. 52] & 0x7ff) == 0x7ff then (0b10000, 0x7ff8000000000000)
          else (zeros(), ame_ztt_f64cos(input))
        },
        AME_FLOAT_SIN => {
          if ((value[63 .. 52] & 0x7ff) == 0x7ff) & (value[51 .. 0] != zeros()) then
            (if value[51] == 0b0 then 0b10000 else zeros(), 0x7ff8000000000000)
          else if (value[63 .. 52] & 0x7ff) == 0x7ff then (0b10000, 0x7ff8000000000000)
          else (zeros(), ame_ztt_f64sin(input))
        },
        AME_FLOAT_TANH => {
          if ((value[63 .. 52] & 0x7ff) == 0x7ff) & (value[51 .. 0] != zeros()) then
            (if value[51] == 0b0 then 0b10000 else zeros(), 0x7ff8000000000000)
          else (zeros(), ame_ztt_f64tanh(input))
        }
      };
      (flags, zero_extend(ame_max_dtype_size, result))
    },
    _ => internal_error(__FILE__, __LINE__, "unsupported AME float element size")
  }
}

function ame_ew_float_math(md_dtype : bits(32), ms1_dtype : bits(32),
                           md : ameregidx, ms1 : ameregidx,
                           op : ame_float_math_op) -> bool = {
  let nsq = ame_nsq2(md_dtype, ms1_dtype);

  if not(ame_valid_softfloat_ew_dtype(md_dtype) & ame_valid_softfloat_ew_dtype(ms1_dtype)) then {
    ame_set_unsupported();
    true
  }
  else if not(ame_same_float_format2(md_dtype, ms1_dtype)) then {
    ame_set_unsupported();
    true
  }
  else if not(ame_check_formed_operand(md, md_dtype, nsq)) then false
  else if not(ame_check_formed_operand(ms1, ms1_dtype, nsq)) then false
  else match ame_fp_rounding_mode(md_dtype) {
    None() => {
      ame_set_unsupported();
      true
    },
    Some(rm) => {
      let snapshot = ame_snapshot_mregs();
      var flags : bits_fflags = zeros();
      foreach (e from 0 to (nsq * ame_nelem - 1)) {
        let (fflags, result) = ame_float_math_result(
          md_dtype, op, rm,
          ame_read_snapshot_elem(snapshot, ms1_dtype, ms1, e));
        flags = flags | fflags;
        write_m_elem(md_dtype, md, e, result)
      };
      accrue_amefflags(flags);
      true
    }
  }
}
