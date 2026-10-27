#!/usr/bin/env python3
#
# Copyright (c) Qualcomm Technologies, Inc. and/or its subsidiaries.
# SPDX-License-Identifier: BSD-3-Clause-Clear
#
"""The mixed-datatype tuples of the biased base-2 logarithm family.

v0.6 §6.2.2 (instruction_semantics.adoc:182-188): "For the mlog2sub.ew and
msublog2.ew families, including their .ew.x forms, the operand of log2, and the
destination, are standard floating-point datatypes; the bias is governed by the
exact tuple's conversion and subtraction capabilities."

That sentence names exactly two operands that must be floating-point, so the
family's edge cases are the three tuples where one of the three operands is a
standard integer:

* the log2 operand is integer -- unsupported: §6.1.3 then sets `amestatus.UN`
  and leaves every destination element as it was;
* the destination is integer -- unsupported for the same reason;
* the bias is integer -- *supported*: the bias has a standard conversion into
  the destination format and the tuple can subtract, so the instruction runs.

The third tuple is why this template exists: it is the only case of the family
that must produce a value instead of a rejection.  The log2 operand is 8.0 and
the bias is 2, both exact, so the tuple's whole conversion-and-subtraction
chain is exact and the expected result is 1.0 (log2 minus bias) or -1.0
(bias minus log2) with no accrued flag.

The 128-bit integer bias is deliberately not covered: a standard integer has no
single conversion to a floating-point datatype at that width, so the tuple has
no conversion capability to rely on and the model rejects it.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import TYPE_CHECKING

from mmul_gen.asm import check_dst_lines, repeated_square_lines
from mmul_gen.machine import MachineConfig
from mmul_gen.templates.base import Case, CaseOutput, Template
from mmul_gen.templates.logexp_common import (
    DATA_VALUES,
    DESTINATION_LABEL,
    DESTINATION_REGISTER,
    DESTINATION_SEED_LABEL,
    LogExpForm,
)

if TYPE_CHECKING:
    from mmul_gen.instruction import Instruction
    from mmul_gen.machine import DType


#: The destination and log2 operand the family requires: FP32 is the one format
#: with a standard integer-to-float conversion that both models evaluate
#: natively for this instruction.
FLOAT_DTYPE = "AME_FP32_DTYPE"
#: The integer operand every case of this template swaps in, in one of the
#: three roles.
INTEGER_DTYPE = "AME_UINT32_DTYPE"
#: 8.0f: log2(8.0) is exactly 3, so the logarithm term contributes no rounding.
LOG2_SOURCE_BITS = 0x41000000
#: An integer bias that is exactly representable in FP32.
BIAS_VALUE = 2
#: 3 - 2 (or 2 - 3) is exact in FP32.
RESULT_BITS_LOG_MINUS_BIAS = 0x3F800000
RESULT_BITS_BIAS_MINUS_LOG = 0xBF800000
#: The three tuples, in emission order.
INTEGER_LOG2 = "int_log2"
INTEGER_DESTINATION = "int_dest"
INTEGER_BIAS = "int_bias"
#: Element width every case of this template uses.
ELEMENT_BITS = 32


class Log2BiasTuple(Template):
    """Emit the integer-log2, integer-destination, and integer-bias tuples."""

    name = "log2bias_tuple"
    dtypes = None

    def __init__(self, log_minus_bias: bool, form: LogExpForm) -> None:
        """``log_minus_bias`` picks log2-bias over bias-log2; ``form`` the shape."""

        self.log_minus_bias = log_minus_bias
        self.form = form

    def fits(
        self,
        machine: MachineConfig,
        instruction: Instruction,
        dtype: DType | None = None,
    ) -> bool:
        squares = 3 if self.form is LogExpForm.BINARY_M else 2
        return squares * machine.nregs(ELEMENT_BITS) <= machine.num_m_regs

    def build(
        self, machine: MachineConfig, instruction: Instruction, dtype: DType | None
    ) -> Sequence[Case]:
        return [
            Case(number=0, dtype=None, payload=INTEGER_LOG2),
            Case(number=0, dtype=None, payload=INTEGER_DESTINATION),
            Case(number=0, dtype=None, payload=INTEGER_BIAS),
        ]

    def render(
        self,
        machine: MachineConfig,
        instruction: Instruction,
        case: Case,
        out: CaseOutput,
    ) -> None:
        kind = str(case.payload)
        if kind not in (INTEGER_LOG2, INTEGER_DESTINATION, INTEGER_BIAS):
            raise ValueError(f"{instruction.name}: unknown log2bias tuple {kind!r}")
        dest, log2_operand, scalar = self._roles(kind)
        step = machine.nregs(ELEMENT_BITS)
        destination = DESTINATION_REGISTER
        log2_reg = destination + step
        prefix = f"{kind}_"
        log2_label = f"{prefix}log2"
        out.text.append(f"    # {instruction.name} {self._description(kind)}")
        out.text.extend(
            [
                f"    li      t0, {dest}",
                f"    msettyp m{destination}, t0",
                f"    li      t0, {log2_operand}",
                f"    msettyp m{log2_reg}, t0",
            ]
        )
        if self.form is LogExpForm.BINARY_M:
            bias_reg = destination + 2 * step
            out.text.extend(
                [
                    f"    li      t0, {scalar}",
                    f"    msettyp m{bias_reg}, t0",
                ]
            )
            bias_label = f"{prefix}bias"
            operand_lines = [
                f"    {instruction.name} m{destination}, m{log2_reg}, m{bias_reg}"
            ]
        else:
            out.text.extend(
                [
                    f"    li      t0, {scalar}",
                    "    csrw    amestype, t0",
                    f"    li      t4, {BIAS_VALUE if kind == INTEGER_BIAS else 0}",
                ]
            )
            bias_label = None
            operand_lines = [
                f"    {instruction.name} m{destination}, t4, m{log2_reg}"
            ]
        out.text.append("")
        if kind != INTEGER_BIAS:
            out.text.extend(
                [
                    f"    la      t1, {prefix}{DESTINATION_SEED_LABEL}",
                    f"    mls.rm     m{destination}, t1",
                ]
            )
        out.text.extend(
            [
                f"    la      t1, {log2_label}",
                f"    mls.rm     m{log2_reg}, t1",
            ]
        )
        if bias_label is not None:
            out.text.extend(
                [f"    la      t2, {bias_label}", f"    mls.rm     m{bias_reg}, t2"]
            )
        out.text.append("    csrwi   amestatus, 0")
        if kind == INTEGER_BIAS:
            out.text.append("    csrw    amefflags, x0")
        out.text.extend(operand_lines)
        out.text.extend(self._checks(kind, machine))
        out.data.extend(
            repeated_square_lines(log2_label, LOG2_SOURCE_BITS, ELEMENT_BITS, machine)
        )
        if bias_label is not None:
            out.data.extend(
                repeated_square_lines(bias_label, BIAS_VALUE, ELEMENT_BITS, machine)
            )
        if kind != INTEGER_BIAS:
            # The seed is 32-bit 7 in every element, so the same square serves an
            # integer destination (7) and a floating-point one (bit pattern 7).
            out.data.extend(
                repeated_square_lines(
                    f"{prefix}{DESTINATION_SEED_LABEL}",
                    DATA_VALUES[DESTINATION_SEED_LABEL],
                    ELEMENT_BITS,
                    machine,
                )
            )
        out.data.append("")

    def _roles(self, kind: str) -> tuple[str, str, str]:
        """``(destination, log2 operand, bias)`` descriptor names for one tuple."""

        if kind == INTEGER_DESTINATION:
            return INTEGER_DTYPE, FLOAT_DTYPE, FLOAT_DTYPE
        if kind == INTEGER_LOG2:
            return FLOAT_DTYPE, INTEGER_DTYPE, FLOAT_DTYPE
        return FLOAT_DTYPE, FLOAT_DTYPE, INTEGER_DTYPE

    def _description(self, kind: str) -> str:
        """The one-line tuple summary in the case comment."""

        return {
            INTEGER_LOG2: "integer log2 operand: unsupported tuple",
            INTEGER_DESTINATION: "integer destination: unsupported tuple",
            INTEGER_BIAS: "integer bias: converted, exact result",
        }[kind]

    def _checks(self, kind: str, machine: MachineConfig) -> list[str]:
        """The status, flag, and destination assertions of one tuple."""

        if kind == INTEGER_BIAS:
            expected = (
                RESULT_BITS_LOG_MINUS_BIAS
                if self.log_minus_bias
                else RESULT_BITS_BIAS_MINUS_LOG
            )
            status, flags = 0, 0
        else:
            expected = DATA_VALUES[DESTINATION_SEED_LABEL]
            status, flags = 1, None
        lines = [
            "    csrr    t5, amestatus",
            "    andi    t5, t5, 1",
            f"    EXPECT  t5, {status}",
        ]
        if flags is not None:
            lines.extend(["    csrr    t5, amefflags", f"    EXPECT  t5, {flags}"])
        lines.extend(
            [
                f"    la      t3, {DESTINATION_LABEL}",
                f"    mss.rm     m{DESTINATION_REGISTER}, t3",
                *check_dst_lines(expected, ELEMENT_BITS, machine=machine),
            ]
        )
        return lines


__all__ = ["Log2BiasTuple"]
