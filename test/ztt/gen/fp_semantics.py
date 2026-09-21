#!/usr/bin/env python3
#
# Copyright (c) Qualcomm Technologies, Inc. and/or its subsidiaries.
# SPDX-License-Identifier: BSD-3-Clause-Clear
#
# Bit-exact AME floating-point boundary vectors shared by test formatters.
#
# These are deliberately independent of the Sail implementation.  A formatter
# may compose them into an operation, but expected results must come from this
# table and the IEEE/OCP rules encoded below.

from __future__ import annotations


ROUNDING_MODES = (
    ("RNE", "AME_RND_RNE"),
    ("RTZ", "AME_RND_RTZ"),
    ("RDN", "AME_RND_RDN"),
    ("RUP", "AME_RND_RUP"),
    ("RMM", "AME_RND_RMM"),
    ("RNO", "AME_RND_RNO"),
)
ROUNDING_MODE_NAMES = tuple(mode for mode, _dtype in ROUNDING_MODES)
ROUNDING_MODE_DTYPES = dict(ROUNDING_MODES)


# Elementwise instructions that expose destination-dtype rounding behavior.
ELEMENTWISE_FP_ROUNDING_INSTRUCTIONS = frozenset(
    {
        "madd.ew",
        "msub.ew",
        "mabsdiff.ew",
        "mmul.ew",
        "mmulneg.ew",
        "madd.ew.x",
        "msub.ew.x",
        "mabsdiff.ew.x",
        "mmul.ew.x",
        "mmulneg.ew.x",
        "mmulacc.ew",
        "mmulaccneg.ew",
        "mmuladd.ew",
        "mmulsub.ew",
        "mmulacc.ew.x",
        "mmulaccneg.ew.x",
        "mmuladd.ew.x",
        "mmulsub.ew.x",
    }
)
ELEMENTWISE_FP_UNDERFLOW_INSTRUCTIONS = frozenset(
    {
        "mmul.ew",
        "mmulneg.ew",
        "mmul.ew.x",
        "mmulneg.ew.x",
        "mmulacc.ew",
        "mmulaccneg.ew",
        "mmuladd.ew",
        "mmulsub.ew",
        "mmulacc.ew.x",
        "mmulaccneg.ew.x",
        "mmuladd.ew.x",
        "mmulsub.ew.x",
    }
)
ELEMENTWISE_FP_TIE_INSTRUCTIONS = frozenset({"madd.ew", "mmulacc.ew"})


# Exactly representable nominal operands and expected results for elementwise
# tests.  Boundary vectors below are kept separate because they encode
# exception-specific values and flags.
FLOAT_OPERATION_VALUES = {
    "AME_OCP_E4M3_DTYPE": {
        "a": 0x3C,
        "b": 0x40,
        "scalar": 0x48,
        "dest": 0x30,
        "neg_abs": 0xBC,
        "add": 0x46,
        "sub": 0x30,
        "mul": 0x44,
        "mulneg": 0xC4,
        "x_add": 0x4C,
        "x_sub": 0xC0,        # B - c = 2.0 - 4.0 = -2.0
        "x_absdiff": 0x40,    # |c - B| = 2.0
        "x_mul": 0x50,
        "x_mulneg": 0xD0,
        "mulacc": 0x46,
        "mulaccneg": 0xC2,
        "muladd": 0x42,
        "mulsub": 0x30,
        "x_mulacc": 0x50,
        "x_mulaccneg": 0xCF,
        "x_muladd": 0x4A,
        "x_mulsub": 0x44,
    },
    "AME_OCP_E5M2_DTYPE": {
        "a": 0x3E,
        "b": 0x40,
        "scalar": 0x44,
        "dest": 0x38,
        "neg_abs": 0xBE,
        "add": 0x43,
        "sub": 0x38,
        "mul": 0x42,
        "mulneg": 0xC2,
        "x_add": 0x46,
        "x_sub": 0xC0,        # B - c = 2.0 - 4.0 = -2.0
        "x_absdiff": 0x40,    # |c - B| = 2.0
        "x_mul": 0x48,
        "x_mulneg": 0xC8,
        "mulacc": 0x43,
        "mulaccneg": 0xC1,
        "muladd": 0x41,
        "mulsub": 0x38,
        "x_mulacc": 0x48,
        "x_mulaccneg": 0xC8,
        "x_muladd": 0x45,
        "x_mulsub": 0x42,
    },
    "AME_FP16_DTYPE": {
        "a": 0x3E00,
        "b": 0x4000,
        "scalar": 0x4400,
        "dest": 0x3800,
        "neg_abs": 0xBE00,
        "add": 0x4300,
        "sub": 0x3800,
        "mul": 0x4200,
        "mulneg": 0xC200,
        "x_add": 0x4600,
        "x_sub": 0xC000,      # B - c = -2.0
        "x_absdiff": 0x4000,  # |c - B| = 2.0
        "x_mul": 0x4800,
        "x_mulneg": 0xC800,
        "mulacc": 0x4300,
        "mulaccneg": 0xC100,
        "muladd": 0x4100,
        "mulsub": 0x3800,
        "x_mulacc": 0x4840,
        "x_mulaccneg": 0xC780,
        "x_muladd": 0x4500,
        "x_mulsub": 0x4200,
    },
    "AME_BF16_DTYPE": {
        "a": 0x3FC0,
        "b": 0x4000,
        "scalar": 0x4080,
        "dest": 0x3F00,
        "neg_abs": 0xBFC0,
        "add": 0x4060,
        "sub": 0x3F00,
        "mul": 0x4040,
        "mulneg": 0xC040,
        "x_add": 0x40C0,
        "x_sub": 0xC000,      # B - c = -2.0
        "x_absdiff": 0x4000,  # |c - B| = 2.0
        "x_mul": 0x4100,
        "x_mulneg": 0xC100,
        "mulacc": 0x4060,
        "mulaccneg": 0xC020,
        "muladd": 0x4020,
        "mulsub": 0x3F00,
        "x_mulacc": 0x4108,
        "x_mulaccneg": 0xC0F0,
        "x_muladd": 0x40A0,
        "x_mulsub": 0x4040,
    },
    "AME_FP32_DTYPE": {
        "a": 0x3FC00000,
        "b": 0x40000000,
        "scalar": 0x40800000,
        "dest": 0x3F000000,
        "neg_abs": 0xBFC00000,
        "add": 0x40600000,
        "sub": 0x3F000000,
        "mul": 0x40400000,
        "mulneg": 0xC0400000,
        "x_add": 0x40C00000,
        "x_sub": 0xC0000000,      # B - c = -2.0
        "x_absdiff": 0x40000000,  # |c - B| = 2.0
        "x_mul": 0x41000000,
        "x_mulneg": 0xC1000000,
        "mulacc": 0x40600000,
        "mulaccneg": 0xC0200000,
        "muladd": 0x40200000,
        "mulsub": 0x3F000000,
        "x_mulacc": 0x41080000,
        "x_mulaccneg": 0xC0F00000,
        "x_muladd": 0x40A00000,
        "x_mulsub": 0x40400000,
    },
    "AME_FP64_DTYPE": {
        "a": 0x3FF8000000000000,
        "b": 0x4000000000000000,
        "scalar": 0x4010000000000000,
        "dest": 0x3FE0000000000000,
        "neg_abs": 0xBFF8000000000000,
        "add": 0x400C000000000000,
        "sub": 0x3FE0000000000000,
        "mul": 0x4008000000000000,
        "mulneg": 0xC008000000000000,
        "x_add": 0x4018000000000000,
        "x_sub": 0xC000000000000000,      # B - c = -2.0
        "x_absdiff": 0x4000000000000000,  # |c - B| = 2.0
        "x_mul": 0x4020000000000000,
        "x_mulneg": 0xC020000000000000,
        "mulacc": 0x400C000000000000,
        "mulaccneg": 0xC004000000000000,
        "muladd": 0x4004000000000000,
        "mulsub": 0x3FE0000000000000,
        "x_mulacc": 0x4021000000000000,
        "x_mulaccneg": 0xC01E000000000000,
        "x_muladd": 0x4014000000000000,
        "x_mulsub": 0x4008000000000000,
    },
}


# Values are encoded directly in their destination datatype. They are derived
# from the IEEE/OCP format definitions, rather than from the Sail model.
FLOAT_BOUNDARIES = {
    "AME_OCP_E4M3_DTYPE": {
        "max": 0x7E,
        "finite": 0x7E,
        "inf": 0x7E,
        "neg_inf": 0xFE,
        "two": 0x40,
        "four": 0x48,
        "half": 0x30,
        "zero": 0x00,
        "neg_zero": 0x80,
        "one": 0x38,
        "one_ulp": 0x39,
        "one_3ulp": 0x3B,
        "one_half": 0x3C,
        "neg_one": 0xB8,
        "neg_one_half": 0xBC,
        "neg_two": 0xC0,
        "half_ulp": 0x18,
        "min_subnormal": 0x01,
        "qnan": 0x7F,
        "snan": None,
    },
    "AME_OCP_E5M2_DTYPE": {
        "max": 0x7B,
        "finite": 0x7B,
        "inf": 0x7C,
        "neg_inf": 0xFC,
        "two": 0x40,
        "four": 0x44,
        "half": 0x38,
        "zero": 0x00,
        "neg_zero": 0x80,
        "one": 0x3C,
        "one_ulp": 0x3D,
        "one_3ulp": 0x3F,
        "one_half": 0x3E,
        "neg_one": 0xBC,
        "neg_one_half": 0xBE,
        "neg_two": 0xC0,
        "half_ulp": 0x30,
        "min_subnormal": 0x01,
        "qnan": 0x7F,
        "snan": 0x7D,
    },
    "AME_FP16_DTYPE": {
        "max": 0x7BFF,
        "finite": 0x7BFF,
        "inf": 0x7C00,
        "neg_inf": 0xFC00,
        "two": 0x4000,
        "four": 0x4400,
        "half": 0x3800,
        "zero": 0x0000,
        "neg_zero": 0x8000,
        "one": 0x3C00,
        "one_ulp": 0x3C01,
        "one_3ulp": 0x3C03,
        "one_half": 0x3E00,
        "neg_one": 0xBC00,
        "neg_one_half": 0xBE00,
        "neg_two": 0xC000,
        "half_ulp": 0x1000,
        "min_subnormal": 0x0001,
        "qnan": 0x7E00,
        "snan": 0x7C01,
    },
    "AME_BF16_DTYPE": {
        "max": 0x7F7F,
        "finite": 0x7F7F,
        "inf": 0x7F80,
        "neg_inf": 0xFF80,
        "two": 0x4000,
        "four": 0x4080,
        "half": 0x3F00,
        "zero": 0x0000,
        "neg_zero": 0x8000,
        "one": 0x3F80,
        "one_ulp": 0x3F81,
        "one_3ulp": 0x3F83,
        "one_half": 0x3FC0,
        "neg_one": 0xBF80,
        "neg_one_half": 0xBFC0,
        "neg_two": 0xC000,
        "half_ulp": 0x3B80,
        "min_subnormal": 0x0001,
        "qnan": 0x7FC0,
        "snan": 0x7F81,
    },
    "AME_FP32_DTYPE": {
        "max": 0x7F7FFFFF,
        "finite": 0x7F7FFFFF,
        "inf": 0x7F800000,
        "neg_inf": 0xFF800000,
        "two": 0x40000000,
        "four": 0x40800000,
        "half": 0x3F000000,
        "zero": 0x00000000,
        "neg_zero": 0x80000000,
        "one": 0x3F800000,
        "one_ulp": 0x3F800001,
        "one_3ulp": 0x3F800003,
        "one_half": 0x3FC00000,
        "neg_one": 0xBF800000,
        "neg_one_half": 0xBFC00000,
        "neg_two": 0xC0000000,
        "half_ulp": 0x33800000,
        "min_subnormal": 0x00000001,
        "qnan": 0x7FC00000,
        "snan": 0x7F800001,
    },
    "AME_FP64_DTYPE": {
        "max": 0x7FEFFFFFFFFFFFFF,
        "finite": 0x7FEFFFFFFFFFFFFF,
        "inf": 0x7FF0000000000000,
        "neg_inf": 0xFFF0000000000000,
        "two": 0x4000000000000000,
        "four": 0x4010000000000000,
        "half": 0x3FE0000000000000,
        "zero": 0x0000000000000000,
        "neg_zero": 0x8000000000000000,
        "one": 0x3FF0000000000000,
        "one_ulp": 0x3FF0000000000001,
        "one_3ulp": 0x3FF0000000000003,
        "one_half": 0x3FF8000000000000,
        "neg_one": 0xBFF0000000000000,
        "neg_one_half": 0xBFF8000000000000,
        "neg_two": 0xC000000000000000,
        "half_ulp": 0x3CA0000000000000,
        "min_subnormal": 0x0000000000000001,
        "qnan": 0x7FF8000000000000,
        "snan": 0x7FF0000000000001,
    },
}


FFLAGS_NX = 0x01
FFLAGS_UF_NX = 0x03
FFLAGS_OF_NX = 0x05
FFLAGS_DZ = 0x08
FFLAGS_NV = 0x10


def sign_mask(element_bits: int) -> int:
    return 1 << (element_bits - 1)


def signed(value: int, element_bits: int, negative: bool) -> int:
    return value | sign_mask(element_bits) if negative else value


def overflow_result(dtype_name: str, element_bits: int, mode: str, negative: bool) -> int:
    values = FLOAT_BOUNDARIES[dtype_name]
    to_infinity = mode in {"RNE", "RMM"} or (mode == "RUP" and not negative) or (
        mode == "RDN" and negative
    )
    return signed(values["inf"] if to_infinity else values["finite"], element_bits, negative)


def underflow_result(dtype_name: str, element_bits: int, mode: str, negative: bool) -> int:
    # Every supported format, including OCP FP8, preserves subnormals.  The
    # test operand is exactly half the minimum subnormal, so directed, ties-
    # away, and round-to-odd modes can select the minimum subnormal.
    rounds_to_min_subnormal = mode in {"RMM", "RNO"} or (mode == "RUP" and not negative) or (
        mode == "RDN" and negative
    )
    value = FLOAT_BOUNDARIES[dtype_name]["min_subnormal"] if rounds_to_min_subnormal else 0
    return signed(value, element_bits, negative)


def pole_result(dtype_name: str, element_bits: int, negative: bool) -> tuple[int, int]:
    values = FLOAT_BOUNDARIES[dtype_name]
    result = signed(values["inf"], element_bits, negative)
    # E4M3 has no infinity encoding. Its conversion saturates and raises OF|NX
    # in addition to the division-by-zero flag.
    flags = FFLAGS_DZ | FFLAGS_OF_NX if dtype_name == "AME_OCP_E4M3_DTYPE" else FFLAGS_DZ
    return result, flags


def tie_result(lower: int, mode: str) -> int:
    """Return the correctly rounded result for an exact positive halfway value."""

    upper = lower + 1
    odd_lower = lower & 1 == 1
    if mode in {"RTZ", "RDN"}:
        return lower
    if mode in {"RUP", "RMM"}:
        return upper
    if mode == "RNO":
        return lower if odd_lower else upper
    return upper if odd_lower else lower


SQRT_TWO_RESULTS = {
    "AME_OCP_E4M3_DTYPE": {
        "RNE": 0x3B,
        "RTZ": 0x3B,
        "RDN": 0x3B,
        "RUP": 0x3C,
        "RMM": 0x3B,
        "RNO": 0x3B,
    },
    "AME_OCP_E5M2_DTYPE": {
        "RNE": 0x3E,
        "RTZ": 0x3D,
        "RDN": 0x3D,
        "RUP": 0x3E,
        "RMM": 0x3E,
        "RNO": 0x3D,
    },
    "AME_FP16_DTYPE": {
        "RNE": 0x3DA8,
        "RTZ": 0x3DA8,
        "RDN": 0x3DA8,
        "RUP": 0x3DA9,
        "RMM": 0x3DA8,
        "RNO": 0x3DA9,
    },
    "AME_BF16_DTYPE": {
        "RNE": 0x3FB5,
        "RTZ": 0x3FB5,
        "RDN": 0x3FB5,
        "RUP": 0x3FB6,
        "RMM": 0x3FB5,
        "RNO": 0x3FB5,
    },
    "AME_FP32_DTYPE": {
        "RNE": 0x3FB504F3,
        "RTZ": 0x3FB504F3,
        "RDN": 0x3FB504F3,
        "RUP": 0x3FB504F4,
        "RMM": 0x3FB504F3,
        "RNO": 0x3FB504F3,
    },
    "AME_FP64_DTYPE": {
        "RNE": 0x3FF6A09E667F3BCD,
        "RTZ": 0x3FF6A09E667F3BCC,
        "RDN": 0x3FF6A09E667F3BCC,
        "RUP": 0x3FF6A09E667F3BCD,
        "RMM": 0x3FF6A09E667F3BCD,
        "RNO": 0x3FF6A09E667F3BCD,
    },
}
