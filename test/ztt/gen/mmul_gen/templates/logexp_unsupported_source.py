#!/usr/bin/env python3
#
# Copyright (c) Qualcomm Technologies, Inc. and/or its subsidiaries.
# SPDX-License-Identifier: BSD-3-Clause-Clear
#
"""The unsupported-integer-source case of the nonlinear log/exp family.

v0.6 §6.2.2: "Among standard datatypes, mexp2.ew, mlog2.ew, mcos.ew, msin.ew,
mtanh.ew, mrec.ew, mrsqrt.ew, msqrt.ew, and the mfrint*.ew family require
floating-point source and destination datatypes.  For the mlog2sub.ew and
msublog2.ew families, including their .ew.x forms, the operand of log2, and the
destination, are standard floating-point datatypes".  A standard integer tuple
of those instructions is therefore unsupported, and §6.1.3 fixes what that
means: `amestatus.UN` is set and every destination register keeps its previous
contents.

The case is the integer-datatype half of the family's coverage: it loads the
same operands the nominal case would, so operand formation still runs, and then
requires both halves of the unsupported-tuple contract -- the status bit set and
the seeded destination square byte for byte intact.  That one sentence covers
two instruction families -- the integer log/exp instructions and the
floating-point unary math group -- and the rejection is identical for both, so
this template serves both instead of restating the assertion.  The scaled family
(mldexp/mldexpacc/mrdexp/mrdexpacc) is not in the §6.2.2 list and keeps its
integer semantics, which is why this is a separate template rather than a change
to the nominal one.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import TYPE_CHECKING

from mmul_gen.asm import check_dst_lines, repeated_square_lines
from mmul_gen.machine import INTEGER, MachineConfig
from mmul_gen.templates.base import Case, CaseOutput, Template, domain_index
from mmul_gen.templates.logexp_common import (
    DATA_VALUES,
    DESTINATION_LABEL,
    DESTINATION_REGISTER,
    DESTINATION_SEED_LABEL,
    LogExpForm,
    case_prefix,
    source_registers,
)

if TYPE_CHECKING:
    from mmul_gen.instruction import Instruction
    from mmul_gen.machine import DType, DTypeDomain


class LogExpUnsupportedSource(Template):
    """An integer source and destination make the nonlinear log/exp op unsupported."""

    name = "logexp_unsupported_source"
    #: Every integer datatype domain is rejected by the same body; the
    #: constructor's ``domain`` argument replaces this declaration so one
    #: template can cover the plain, saturating, and 128-bit integer domains.
    dtypes = INTEGER

    def __init__(
        self,
        src1_label: str,
        form: LogExpForm,
        domain: DTypeDomain,
        src2_label: str | None = None,
        scalar: int | None = None,
        scalar_dtype_csr: bool = False,
    ) -> None:
        """``domain`` is the integer datatype domain this case must reject.

        ``src1_label``/``src2_label`` name the squares the nominal case reads,
        so the rejected instruction sees the same integer operands it would
        otherwise consume.  ``scalar`` and ``scalar_dtype_csr`` describe the
        ``binary_x`` form's scalar operand exactly as the nominal case does.
        """

        self.src1_label = src1_label
        self.form = form
        self.dtypes = domain
        self.src2_label = src2_label
        self.scalar = scalar
        self.scalar_dtype_csr = scalar_dtype_csr

    @property
    def register_groups(self) -> int:
        """M register groups the case needs: destination and sources."""

        return 3 if self.form.reads_second_source else 2

    def fits(
        self,
        machine: MachineConfig,
        instruction: Instruction,
        dtype: DType | None = None,
    ) -> bool:
        if dtype is None:
            raise ValueError("a log/exp case is always formed from a datatype")
        return self.register_groups * machine.nregs(dtype.bits) <= machine.num_m_regs

    def build(
        self, machine: MachineConfig, instruction: Instruction, dtype: DType | None
    ) -> Sequence[Case]:
        if dtype is None:
            raise ValueError("a log/exp case is always formed from a datatype")
        return [Case(number=0, dtype=dtype)]

    def operand_lines(self, instruction: Instruction, src1_reg: int, src2_reg: int) -> list[str]:
        """The rejected operation itself, in the instruction's operand shape."""

        if self.form is LogExpForm.UNARY:
            return [f"    {instruction.name} m{DESTINATION_REGISTER}, m{src1_reg}"]
        if self.form.reads_second_source:
            return [
                f"    {instruction.name} m{DESTINATION_REGISTER}, m{src1_reg}, m{src2_reg}"
            ]
        if self.form is LogExpForm.BINARY_X:
            if self.scalar is None:
                raise ValueError(f"{instruction.name}: the scalar form needs a scalar operand")
            return [
                f"    li      t4, {self.scalar}",
                f"    {instruction.name} m{DESTINATION_REGISTER}, t4, m{src1_reg}",
            ]
        raise ValueError(f"{instruction.name}: unsupported log/exp form {self.form}")

    def render(
        self,
        machine: MachineConfig,
        instruction: Instruction,
        case: Case,
        out: CaseOutput,
    ) -> None:
        if case.dtype is None:
            raise ValueError("a log/exp case is always formed from a datatype")
        dtype = case.dtype
        index = domain_index(machine, dtype, self.dtypes)
        src1_reg, src2_reg = source_registers(machine, dtype.bits)
        prefix = case_prefix("case", index, dtype)
        seed = DATA_VALUES[DESTINATION_SEED_LABEL]
        out.text.extend(
            [
                f"    # case {index}: {instruction.name} {dtype.name} "
                "(integer source: unsupported tuple)",
                f"    li      t0, {dtype.name}",
                f"    msettyp m{DESTINATION_REGISTER}, t0",
                f"    msettyp m{src1_reg}, t0",
            ]
        )
        if self.form.reads_second_source:
            out.text.append(f"    msettyp m{src2_reg}, t0")
        if self.scalar_dtype_csr:
            out.text.append("    csrw    amestype, t0")
        out.text.extend(
            [
                "",
                f"    la      t1, {prefix}{DESTINATION_SEED_LABEL}",
                f"    mls.rm     m{DESTINATION_REGISTER}, t1",
                f"    la      t1, {prefix}{self.src1_label}",
                f"    mls.rm     m{src1_reg}, t1",
            ]
        )
        if self.src2_label is not None:
            out.text.extend(
                [
                    f"    la      t2, {prefix}{self.src2_label}",
                    f"    mls.rm     m{src2_reg}, t2",
                ]
            )
        out.text.extend(
            [
                "    csrwi   amestatus, 0",
                *self.operand_lines(instruction, src1_reg, src2_reg),
                "    csrr    t5, amestatus",
                "    andi    t5, t5, 1",
                "    EXPECT  t5, 1",
                f"    la      t3, {prefix}{DESTINATION_LABEL}",
                f"    mss.rm     m{DESTINATION_REGISTER}, t3",
                *check_dst_lines(
                    seed, dtype.bits, machine=machine, label=f"{prefix}{DESTINATION_LABEL}"
                ),
            ]
        )
        # The store target is this case's own square: the family's data footer
        # is not emitted for every instruction that runs this template, so the
        # case cannot rely on a shared ``dst_square`` scratch label.
        labels = {self.src1_label, DESTINATION_SEED_LABEL}
        if self.src2_label is not None:
            labels.add(self.src2_label)
        for label in sorted(labels):
            out.data.extend(
                repeated_square_lines(
                    f"{prefix}{label}", DATA_VALUES[label], dtype.bits, machine
                )
            )
        out.data.extend(
            repeated_square_lines(
                f"{prefix}{DESTINATION_LABEL}", seed, dtype.bits, machine
            )
        )
        out.data.append("")


__all__ = ["LogExpUnsupportedSource"]
