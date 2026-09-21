#!/usr/bin/env ruby
# frozen_string_literal: true

# Generates a GAS macro include file for all Ztt instructions,
# derived from the current prose specification instruction snapshot.
#
# Usage:
#   ruby generators/gen_ztt_macros.rb > src/ame_macros.inc

require 'pathname'
require_relative 'manual_instruction_data'

MACHINE_READABLE_ROOT = Pathname.new(__FILE__).dirname.parent.expand_path

def match_to_value(match_str)
  match_str.tr('-', '0').to_i(2)
end

instructions = ManualInstructionData.load

puts <<~HEADER
  # Ztt assembler macros for GNU GAS
  # Auto-generated from manual-main/instructions.json - DO NOT EDIT BY HAND.
  # Regenerate with generators/gen_ztt_macros.rb.

  # Usage: .include "ame_macros.inc"

  # ── AME CSR numbers ──────────────────────────────────────────────────────────
  .equ amenlen,          0xCC0
  .equ ameudsz,          0xCC1
  .equ ame_scalar_dtype, 0xCC2
  .equ ameown,           0xCC3
  .equ amefflags,        0xCC4
  .equ amexsat,          0xCC5
  .equ amestatus,        0x800

  # ── AME datatype constants ────────────────────────────────────────────────────
  # Integer types (bit 30=sign, bit 29=sat, bit 8=0, bits 7:0=size)
  .equ AME_UINT4_DTYPE,      0x00000004
  .equ AME_INT4_DTYPE,       0x40000004
  .equ AME_UINT8_DTYPE,      0x00000008
  .equ AME_INT8_DTYPE,       0x40000008
  .equ AME_UINT16_DTYPE,     0x00000010
  .equ AME_INT16_DTYPE,      0x40000010
  .equ AME_UINT32_DTYPE,     0x00000020
  .equ AME_INT32_DTYPE,      0x40000020
  .equ AME_UINT64_DTYPE,     0x00000040
  .equ AME_INT64_DTYPE,      0x40000040
  .equ AME_UINT128_DTYPE,    0x00000080
  .equ AME_INT128_DTYPE,     0x40000080
  # Saturating integer types (bit 29=1)
  .equ AME_UINT4_SAT_DTYPE,  0x20000004
  .equ AME_INT4_SAT_DTYPE,   0x60000004
  .equ AME_UINT8_SAT_DTYPE,  0x20000008
  .equ AME_INT8_SAT_DTYPE,   0x60000008
  .equ AME_UINT16_SAT_DTYPE, 0x20000010
  .equ AME_INT16_SAT_DTYPE,  0x60000010
  .equ AME_UINT32_SAT_DTYPE, 0x20000020
  .equ AME_INT32_SAT_DTYPE,  0x60000020
  .equ AME_UINT64_SAT_DTYPE, 0x20000040
  .equ AME_INT64_SAT_DTYPE,  0x60000040
  .equ AME_UINT128_SAT_DTYPE,0x20000080
  .equ AME_INT128_SAT_DTYPE, 0x60000080
  # Floating-point types (bit 8=1; bits 25:22=rounding, default=RNE=0)
  # To use a non-default rounding mode: AME_FP32_DTYPE | AME_RND_RTZ
  .equ AME_FP16_DTYPE,       0x14300110
  .equ AME_BF16_DTYPE,       0x20300110
  .equ AME_FP32_DTYPE,       0x20300120
  .equ AME_FP64_DTYPE,       0x2c300140
  .equ AME_OCP_E4M3_DTYPE,   0x10100108
  .equ AME_OCP_E5M2_DTYPE,   0x14300108
  # Floating-point rounding modes (bits 25:22); OR into a float dtype constant
  .equ AME_RND_RNE,          0x00000000
  .equ AME_RND_RTZ,          0x00400000
  .equ AME_RND_RDN,          0x00800000
  .equ AME_RND_RUP,          0x00c00000
  .equ AME_RND_RMM,          0x01000000
  .equ AME_RND_RNO,          0x01400000

  # ── M-register numbers (m0–m31) ──────────────────────────────────────────────
  .equ m0,  0;  .equ m1,  1;  .equ m2,  2;  .equ m3,  3
  .equ m4,  4;  .equ m5,  5;  .equ m6,  6;  .equ m7,  7
  .equ m8,  8;  .equ m9,  9;  .equ m10,10;  .equ m11, 11
  .equ m12,12;  .equ m13,13;  .equ m14,14;  .equ m15, 15
  .equ m16,16;  .equ m17,17;  .equ m18,18;  .equ m19, 19
  .equ m20,20;  .equ m21,21;  .equ m22,22;  .equ m23, 23
  .equ m24,24;  .equ m25,25;  .equ m26,26;  .equ m27, 27
  .equ m28,28;  .equ m29,29;  .equ m30,30;  .equ m31, 31

  # ── Acc-register numbers (acc0–acc31) ────────────────────────────────────────
  .equ acc0, 0;  .equ acc1, 1;  .equ acc2, 2;  .equ acc3, 3
  .equ acc4, 4;  .equ acc5, 5;  .equ acc6, 6;  .equ acc7, 7
  .equ acc8, 8;  .equ acc9, 9;  .equ acc10,10; .equ acc11,11
  .equ acc12,12; .equ acc13,13; .equ acc14,14; .equ acc15,15
  .equ acc16,16; .equ acc17,17; .equ acc18,18; .equ acc19,19
  .equ acc20,20; .equ acc21,21; .equ acc22,22; .equ acc23,23
  .equ acc24,24; .equ acc25,25; .equ acc26,26; .equ acc27,27
  .equ acc28,28; .equ acc29,29; .equ acc30,30; .equ acc31,31

  # ── Integer register numbers ──────────────────────────────────────────────────
  # Needed so ABI names resolve as numeric values inside .insn expressions.
  # GAS register parsing still takes precedence in instruction operand contexts.
  # Both ABI names (zero, ra, …) and xN names (x0, x1, …) are defined.
  .equ zero, 0; .equ ra,  1;  .equ sp,  2;  .equ gp,  3;  .equ tp,  4
  .equ t0,   5; .equ t1,  6;  .equ t2,  7;  .equ s0,  8;  .equ fp,  8;  .equ s1,  9
  .equ a0,  10; .equ a1, 11;  .equ a2, 12;  .equ a3, 13
  .equ a4,  14; .equ a5, 15;  .equ a6, 16;  .equ a7, 17
  .equ s2,  18; .equ s3, 19;  .equ s4, 20;  .equ s5, 21
  .equ s6,  22; .equ s7, 23;  .equ s8, 24;  .equ s9, 25
  .equ s10, 26; .equ s11,27
  .equ t3,  28; .equ t4, 29;  .equ t5, 30;  .equ t6, 31
  .equ x0,   0; .equ x1,  1;  .equ x2,  2;  .equ x3,  3;  .equ x4,  4
  .equ x5,   5; .equ x6,  6;  .equ x7,  7;  .equ x8,  8;  .equ x9,  9
  .equ x10, 10; .equ x11,11;  .equ x12,12;  .equ x13,13;  .equ x14,14
  .equ x15, 15; .equ x16,16;  .equ x17,17;  .equ x18,18;  .equ x19,19
  .equ x20, 20; .equ x21,21;  .equ x22,22;  .equ x23,23;  .equ x24,24
  .equ x25, 25; .equ x26,26;  .equ x27,27;  .equ x28,28;  .equ x29,29
  .equ x30, 30; .equ x31,31

  # ── Float register numbers ────────────────────────────────────────────────────
  .equ ft0,  0; .equ ft1,  1; .equ ft2,  2; .equ ft3,  3
  .equ ft4,  4; .equ ft5,  5; .equ ft6,  6; .equ ft7,  7
  .equ fs0,  8; .equ fs1,  9
  .equ fa0, 10; .equ fa1, 11; .equ fa2, 12; .equ fa3, 13
  .equ fa4, 14; .equ fa5, 15; .equ fa6, 16; .equ fa7, 17
  .equ fs2, 18; .equ fs3, 19; .equ fs4, 20; .equ fs5, 21
  .equ fs6, 22; .equ fs7, 23; .equ fs8, 24; .equ fs9, 25
  .equ fs10,26; .equ fs11,27
  .equ ft8, 28; .equ ft9, 29; .equ ft10,30; .equ ft11,31

  # ── Instruction macros ────────────────────────────────────────────────────────
HEADER

instructions.each do |inst|
  name = inst[:name]
  match = inst[:match]
  variables = inst[:variables]
  assembly = inst[:assembly]

  match_val = match_to_value(match)

  var_lo = variables.each_with_object({}) do |v, h|
    h[v.name] = v.lsb
  end

  asm_args = assembly.split(',').map { |argument| argument.strip.delete('()') }.reject(&:empty?)

  parts = ["0x#{match_val.to_s(16).rjust(8, '0')}"]
  asm_args.each do |arg|
    lo = var_lo[arg]
    next if lo.nil?
    parts << "((\\#{arg}) << #{lo})"
  end

  header_comment = assembly.empty? ? name : "#{name} #{assembly}"
  puts "# #{header_comment}"
  puts asm_args.empty? ? ".macro #{name}" : ".macro #{name} #{asm_args.join(', ')}"
  puts "    .insn 4, (#{parts.join(' | ')})"
  puts ".endm"
end
