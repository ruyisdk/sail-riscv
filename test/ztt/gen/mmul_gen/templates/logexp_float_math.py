#!/usr/bin/env python3
#
# Copyright (c) Qualcomm Technologies, Inc. and/or its subsidiaries.
# SPDX-License-Identifier: BSD-3-Clause-Clear
#
"""The same-format floating-point cases of ``mexp2.ew`` and ``mlog2.ew``.

Spec:    instruction_semantics.adoc:213-214 (§6.2.3), instruction_semantics.adoc:243-245 (§6.2.3), instruction_semantics.adoc:248-250 (§6.2.3)
Quote:   "NX is set whenever the delivered finite result differs from the exact
         mathematical result because of rounding, including an implementation-defined
         approximation that is not exact."
Checks:  every IEEE format runs one exact and one inexact argument through the
         instruction, the exact case asserts the stored bits and a clear NX, the
         inexact case asserts the host-libm result and NX, and the special
         arguments (both zeros, both infinities, a negative finite value, a quiet
         and a signaling NaN) assert their own result and flags

This is the *same-format* half of the log/exp coverage.  ``float_mixed_format``
runs a tuple whose source and destination formats differ and deliberately picks
stimulus whose answer is exactly representable, so it can never exercise the
inexact path -- which is where §6.2.3's NX clause actually bites for these two
operations.  Here the source and destination share one format and half the
arguments are inexact on purpose.

The four IEEE interchange formats are covered.  The OCP 8-bit formats are left
to the mixed-format corpus: a same-format FP8 log/exp tuple raises flags that
none of the three simulators documents yet, and asserting them here would freeze
behaviour that has not been decided.
"""

from __future__ import annotations

import struct
from collections.abc import Sequence
from dataclasses import dataclass
from enum import StrEnum
from fractions import Fraction
from typing import TYPE_CHECKING

import ml_dtypes
import mpmath as mp
import numpy as np

from fp_semantics import FLOAT_BOUNDARIES
from mmul_gen.asm import check_dst_element_lines, square_lines
from mmul_gen.machine import FORMED_SOFTFLOAT, MachineConfig, dtype_stem
from mmul_gen.registers import choose_m_group_base
from mmul_gen.templates.base import Case, CaseOutput, Template, domain_index
from mmul_gen.templates.float_math_common import (
    FFLAGS_NX,
    FFLAGS_NV,
    LIBRARY_ULP_BUDGET,
    NUMERIC_DTYPES,
    REFERENCE_DECIMAL_PRECISION,
    library_float32,
    library_float64,
    ulp_distance_32,
    ulp_distance_64,
)

if TYPE_CHECKING:
    from mmul_gen.instruction import Instruction
    from mmul_gen.instructions.logexp.base import LogExpInstruction
    from mmul_gen.machine import DType


#: The four IEEE interchange formats this template covers.
IEEE_DTYPES = (
    "AME_FP16_DTYPE",
    "AME_BF16_DTYPE",
    "AME_FP32_DTYPE",
    "AME_FP64_DTYPE",
)
#: Preferred destination base: m16 for the float-math family.
PREFERRED_DESTINATION_BASE = 16
#: The divide-by-zero flag ``log2(+-0)`` raises.
FFLAGS_DZ = 0x08


class LogExpOperation(StrEnum):
    """One of the two same-format log/exp operations."""

    EXP2 = "exp2"
    LOG2 = "log2"

    @property
    def library_names(self) -> tuple[str, str]:
        """The single- and double-precision host entry points."""

        return ("exp2f", "exp2") if self is LogExpOperation.EXP2 else ("log2f", "log2")

    @property
    def exact_source(self) -> float:
        """An argument whose answer is exactly representable in every format."""

        return 3.0 if self is LogExpOperation.EXP2 else 8.0

    @property
    def exact_answer(self) -> Fraction:
        """The mathematical answer of :attr:`exact_source`."""

        return Fraction(8) if self is LogExpOperation.EXP2 else Fraction(3)

    @property
    def inexact_source(self) -> float:
        """An argument whose answer is not representable in any format."""

        return 1.5 if self is LogExpOperation.EXP2 else 3.0

    def reference(self, value: mp.mpf) -> mp.mpf:
        """The exact value mpmath says the host libm stage must reproduce."""

        if self is LogExpOperation.EXP2:
            return mp.power(2, value)
        return mp.log(value, 2)


@dataclass(frozen=True)
class LogExpCase:
    """One argument, its delivered result, and the flags it must raise."""

    scenario: str
    source: int
    expected: int
    flags: int


def encode(value: float, dtype_name: str, element_bits: int) -> int:
    """The stored bits of one exactly representable value."""

    if dtype_name == "AME_FP64_DTYPE":
        return struct.unpack("Q", struct.pack("d", value))[0]
    if dtype_name == "AME_FP32_DTYPE":
        return struct.unpack("I", struct.pack("f", value))[0]
    narrow = np.array([np.float32(value)], dtype=np.float32).astype(
        NUMERIC_DTYPES[dtype_name]
    )
    view = np.uint16 if element_bits == 16 else np.uint8
    return int(narrow.view(view)[0])


def inexact_case(
    operation: LogExpOperation, dtype_name: str, element_bits: int
) -> tuple[int, int]:
    """The stored bits the inexact argument delivers, and its flag.

    Both simulators widen or not to f32, call the host libm, and round back with
    RNE, so the case asserts the host's own answer.  The f32 stage is
    cross-checked against a 30-digit mpmath reference first, so a libm drift
    fails here rather than in a simulator.
    """

    source = operation.inexact_source
    single, double = operation.library_names
    float32_result = library_float32(single, source)
    mp.mp.dps = REFERENCE_DECIMAL_PRECISION
    reference = float(operation.reference(mp.mpf(source)))
    for name, candidate, distance in (
        ("f32", float32_result, ulp_distance_32),
        ("f64", library_float64(double, source), ulp_distance_64),
    ):
        ulp = distance(candidate, reference)
        if ulp > LIBRARY_ULP_BUDGET:
            raise AssertionError(
                f"{operation} {dtype_name}: host libm {name} stage differs from "
                f"the mpmath reference by {ulp} ulp, over the documented "
                f"{LIBRARY_ULP_BUDGET}"
            )
    if dtype_name == "AME_FP64_DTYPE":
        expected = library_float64(double, source)
    else:
        expected = float32_result
    return encode(expected, dtype_name, element_bits), FFLAGS_NX


def logexp_cases(
    operation: LogExpOperation, dtype_name: str, element_bits: int
) -> list[LogExpCase]:
    """Every case of one operation in one format."""

    boundaries = FLOAT_BOUNDARIES[dtype_name]
    cases = [
        LogExpCase(
            "exact",
            encode(operation.exact_source, dtype_name, element_bits),
            encode(float(operation.exact_answer), dtype_name, element_bits),
            0,
        ),
        LogExpCase(
            "inexact",
            encode(operation.inexact_source, dtype_name, element_bits),
            *inexact_case(operation, dtype_name, element_bits),
        ),
        LogExpCase("quiet_nan", boundaries["qnan"], boundaries["qnan"], 0),
        LogExpCase("signaling_nan", boundaries["snan"], boundaries["qnan"], FFLAGS_NV),
    ]
    if operation is LogExpOperation.EXP2:
        # 2**x is defined on the whole extended line: both zeros raise 2**0 = 1
        # with no flag, +inf overflows to +inf without OF (§6.2.3 counts a
        # required infinity as exact), and -inf underflows to +0 silently here
        # because the exact answer is not a rounded one.
        cases.extend(
            [
                LogExpCase("zero", boundaries["zero"], boundaries["one"], 0),
                LogExpCase("neg_zero", boundaries["neg_zero"], boundaries["one"], 0),
                LogExpCase("inf", boundaries["inf"], boundaries["inf"], 0),
                LogExpCase("neg_inf", boundaries["neg_inf"], boundaries["zero"], 0),
            ]
        )
    else:
        # log2 is defined only for positive arguments: +-0 is a pole (-inf and
        # DZ) and every other negative value is an invalid operation.
        cases.extend(
            [
                LogExpCase("zero", boundaries["zero"], boundaries["neg_inf"], FFLAGS_DZ),
                LogExpCase(
                    "neg_zero", boundaries["neg_zero"], boundaries["neg_inf"], FFLAGS_DZ
                ),
                LogExpCase("inf", boundaries["inf"], boundaries["inf"], 0),
                LogExpCase("neg_inf", boundaries["neg_inf"], boundaries["qnan"], FFLAGS_NV),
                LogExpCase(
                    "negative",
                    encode(-2.0, dtype_name, element_bits),
                    boundaries["qnan"],
                    FFLAGS_NV,
                ),
            ]
        )
    return cases


def _checks(values: Sequence[int], element_bits: int, label: str) -> list[str]:
    lines: list[str] = []
    for index in range(len(values)):
        lines.extend(check_dst_element_lines(values[index], element_bits, index, label))
    return lines


class LogExpFloatMath(Template):
    """Emit one format's exact, inexact, and special-argument log/exp cases."""

    name = "logexp_float_math"
    dtypes = FORMED_SOFTFLOAT

    def __init__(self, operation: LogExpOperation) -> None:
        """``operation`` is the function this instruction applies."""

        self.operation = operation

    def fits(
        self,
        machine: MachineConfig,
        instruction: "Instruction",
        dtype: DType | None = None,
    ) -> bool:
        """Cover the four IEEE formats; OCP 8-bit stays with the mixed corpus."""

        return dtype is not None and dtype.name in IEEE_DTYPES

    def build(
        self, machine: MachineConfig, instruction: "Instruction", dtype: DType | None
    ) -> Sequence[Case]:
        if dtype is None:
            raise ValueError("a log/exp float case is always formed from a datatype")
        element_bits = dtype.bits
        cases = logexp_cases(self.operation, dtype.name, element_bits)
        return [
            Case(number=number, dtype=dtype, payload=payload)
            for number, payload in enumerate(cases)
        ]

    def render(
        self,
        machine: MachineConfig,
        instruction: "LogExpInstruction",
        case: Case,
        out: CaseOutput,
    ) -> None:
        if case.dtype is None:
            raise ValueError("a log/exp float case is always formed from a datatype")
        dtype = case.dtype
        payload = case.payload
        if not isinstance(payload, LogExpCase):
            raise ValueError(f"unknown log/exp case payload: {payload!r}")
        index = domain_index(machine, dtype, self.dtypes)
        destination = choose_m_group_base(
            machine.num_m_regs, dtype.bits, machine.uds, PREFERRED_DESTINATION_BASE
        )
        element_count = machine.storage_elements(dtype.bits)
        prefix = f"case{index}_{dtype_stem(dtype.name)}_{payload.scenario}_"
        source_label = f"{prefix}source"
        destination_label = f"{prefix}destination"
        out.text.extend(
            [
                f"    # {instruction.name} {dtype.name}: {payload.scenario}",
                f"    li      t0, {dtype.name}",
                "    msettyp m0, t0",
                f"    msettyp m{destination}, t0",
                f"    la      t1, {source_label}",
                "    mls.rm     m0, t1",
                "    csrw    amefflags, x0",
                f"    {instruction.name} m{destination}, m0",
                "    csrr    t4, amefflags",
                f"    EXPECT  t4, {payload.flags}",
                f"    la      t2, {destination_label}",
                f"    mss.rm     m{destination}, t2",
                *_checks([payload.expected] * element_count, dtype.bits, destination_label),
            ]
        )
        out.data.extend(
            square_lines(
                source_label, [payload.source] * element_count, dtype.bits, machine
            )
        )
        out.data.extend(
            square_lines(
                destination_label,
                [payload.expected] * element_count,
                dtype.bits,
                machine,
            )
        )
        out.data.append("")


__all__ = [
    "IEEE_DTYPES",
    "LogExpCase",
    "LogExpFloatMath",
    "LogExpOperation",
    "logexp_cases",
]
