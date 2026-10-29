#!/usr/bin/env python3
#
# Copyright (c) Qualcomm Technologies, Inc. and/or its subsidiaries.
# SPDX-License-Identifier: BSD-3-Clause-Clear
#
"""An AME floating-point instruction must not disturb the scalar ``fflags``.

Spec:    instruction_semantics.adoc:215-216 (§6.2.3)
Quote:   "accrue IEEE exception flags in `amefflags` and do not modify `fflags`"
Checks:  an AME square root of an inexact argument raises `NX` in `amefflags`, and the
         exact scalar `fadd.s` that follows it leaves `fcsr.fflags` clear

`amefflags` and `fflags` are separate registers, so "does not modify `fflags`"
has a second reading beyond "the AME instruction never writes the CSR": the
instruction must also leave no residue in the state the next scalar
floating-point instruction reports from.  Both simulators accumulate IEEE flags
in a process-global variable that a scalar instruction drains into `fflags` when
it retires; an AME instruction that leaves its own accrual in that variable makes
the *next* scalar instruction report flags it never raised.

The case therefore pairs the two: `msqrt.ew(2.0)` is inexact in every IEEE
format, so `amefflags` must read `NX`, and the exact `fadd.s 1.0 + 2.0` that
follows must leave `fflags` at zero.  Only `msqrt.ew` carries the case: the
stimulus needs a format-independent inexact answer, which square root of two
supplies and no other instruction of the family does.
"""

from __future__ import annotations

import struct
from collections.abc import Sequence
from typing import TYPE_CHECKING

import ml_dtypes
import numpy as np

from mmul_gen.asm import square_lines
from mmul_gen.machine import FORMED_SOFTFLOAT, MachineConfig, dtype_stem
from mmul_gen.registers import choose_m_group_base
from mmul_gen.templates.base import Case, CaseOutput, Template, domain_index

if TYPE_CHECKING:  # pragma: no cover - typing only
    from mmul_gen.instruction import Instruction
    from mmul_gen.machine import DType


#: The four IEEE interchange formats: an 8-bit format has no `fadd.s` companion
#: and its AME flag behaviour has not been settled by all three implementations.
IEEE_DTYPES = (
    "AME_FP16_DTYPE",
    "AME_BF16_DTYPE",
    "AME_FP32_DTYPE",
    "AME_FP64_DTYPE",
)
#: Preferred destination base: m16 for the float-math family.
PREFERRED_DESTINATION_BASE = 16
#: `sqrt(2)` is inexact in every format, so the AME instruction must raise `NX`.
FFLAGS_NX = 0x01
#: The exact scalar operands of the companion `fadd.s`: 1.0 + 2.0 = 3.0.
SCALAR_ADDENDS = (0x3F800000, 0x40000000)


def _encode(value: float, dtype_name: str, element_bits: int) -> int:
    """The stored bits of one value in a formed datatype."""

    if dtype_name == "AME_FP64_DTYPE":
        return struct.unpack("Q", struct.pack("d", value))[0]
    if dtype_name == "AME_FP32_DTYPE":
        return struct.unpack("I", struct.pack("f", value))[0]
    narrow = np.array([np.float32(value)], dtype=np.float32).astype(
        ml_dtypes.bfloat16 if dtype_name == "AME_BF16_DTYPE" else np.float16
    )
    return int(narrow.view(np.uint16)[0])


class FloatFlagIsolation(Template):
    """An AME instruction leaves the next scalar floating-point ``fflags`` clean."""

    name = "float_flag_isolation"
    dtypes = FORMED_SOFTFLOAT

    def fits(
        self,
        machine: MachineConfig,
        instruction: "Instruction",
        dtype: DType | None = None,
    ) -> bool:
        """Cover the IEEE formats; the OCP 8-bit flags are not settled."""

        return dtype is not None and dtype.name in IEEE_DTYPES

    def build(
        self, machine: MachineConfig, instruction: "Instruction", dtype: DType | None
    ) -> Sequence[Case]:
        if dtype is None:
            raise ValueError("a flag-isolation case is always formed from a datatype")
        return (Case(number=0, dtype=dtype, description="scalar fflags isolation"),)

    def render(
        self,
        machine: MachineConfig,
        instruction: "Instruction",
        case: Case,
        out: CaseOutput,
    ) -> None:
        if case.dtype is None:
            raise ValueError("a flag-isolation case is always formed from a datatype")
        dtype = case.dtype
        index = domain_index(machine, dtype, self.dtypes)
        destination = choose_m_group_base(
            machine.num_m_regs, dtype.bits, machine.uds, PREFERRED_DESTINATION_BASE
        )
        element_count = machine.storage_elements(dtype.bits)
        prefix = f"case{index}_{dtype_stem(dtype.name)}_flag_isolation_"
        source_label = f"{prefix}source"
        destination_label = f"{prefix}destination"
        low, high = SCALAR_ADDENDS
        out.text.extend(
            [
                f"    # {instruction.name} {dtype.name}: scalar fflags isolation",
                "    li      t0, 0x6000",  # mstatus.FS = 3: the scalar unit is on
                "    csrs    mstatus, t0",
                f"    li      t0, {dtype.name}",
                "    msettyp m0, t0",
                f"    msettyp m{destination}, t0",
                f"    la      t1, {source_label}",
                "    mls.rm     m0, t1",
                "    csrw    amefflags, x0",
                f"    {instruction.name} m{destination}, m0",
                "    csrr    t4, amefflags",
                f"    EXPECT  t4, {FFLAGS_NX}",
                # The scalar instruction must report only its own exceptions.
                "    csrw    fflags, x0",
                f"    li      t3, {low:#x}",
                f"    li      t2, {high:#x}",
                "    fmv.w.x f0, t3",
                "    fmv.w.x f1, t2",
                "    fadd.s  f2, f0, f1",
                "    csrr    t5, fflags",
                "    EXPECT  t5, 0",
            ]
        )
        out.data.extend(
            square_lines(
                source_label,
                [_encode(2.0, dtype.name, dtype.bits)] * element_count,
                dtype.bits,
                machine,
            )
        )
        out.data.extend(
            square_lines(
                destination_label, [0] * element_count, dtype.bits, machine
            )
        )
        out.data.append("")


__all__ = ["FloatFlagIsolation", "IEEE_DTYPES"]


FLOAT_FLAG_ISOLATION = FloatFlagIsolation()
