#!/usr/bin/env python3
#
# Copyright (c) Qualcomm Technologies, Inc. and/or its subsidiaries.
# SPDX-License-Identifier: BSD-3-Clause-Clear
#
"""The cases of one floating-point unary math instruction.

One template carries the whole family because the generated file interleaves the
cases *per datatype*: a datatype contributes its nominal case and then its
boundary scenarios before the next datatype starts.  A template per body shape
would group them the other way round (every nominal case, then every boundary
case), which is a different file.

The three bodies cover the three case shapes: the nominal case of a
table-driven operation, the boundary scenarios with their exact result and flag
set, and the exact-semantics scenarios of a transcendental.
"""

from __future__ import annotations

DOC_ZH = """\
一条浮点一元数学指令的用例。

一个模板承载整个家族，因为生成文件按*每个 datatype* 交错用例：一个 datatype 先贡献其标称用例，再贡献其边界场景，然后下一个 datatype 才开始。按主体形态分模板会把它们按另一种方式分组（先所有标称用例，再所有边界用例），那是另一个文件。

三个主体对应三种用例形态：查表运算的标称用例、带精确结果与标志集合的边界场景、以及超越函数的精确语义场景。
"""

from collections.abc import Sequence
from dataclasses import dataclass
from typing import TYPE_CHECKING

from mmul_gen.asm import check_dst_element_lines, square_lines
from fp_semantics import FLOAT_BOUNDARIES, ROUNDING_MODE_DTYPES
from mmul_gen.machine import FORMED_SOFTFLOAT, MachineConfig, dtype_stem
from mmul_gen.registers import choose_m_group_base
from mmul_gen.templates.base import Case, CaseOutput, Template, domain_index
from mmul_gen.templates.float_math_common import (
    ROUNDING_FLAGS,
    BoundaryCase,
    MathOperation,
    checked_indices,
    transcendental_cases,
)

if TYPE_CHECKING:
    from mmul_gen.instruction import Instruction
    from mmul_gen.instructions.float_math.base import FloatMathInstruction
    from mmul_gen.machine import DType


#: Preferred destination base: m16 for this family.
PREFERRED_DESTINATION_BASE = 16
#: The rounding-mode selector is folded into the case label.
BOUNDARY_LABEL_STRIDE = 100


@dataclass(frozen=True)
class BoundaryScenario:
    """One boundary scenario plus its position in the datatype's list.

    The position is part of the case label, so it has to survive the trip from
    :meth:`Template.build` to :meth:`Template.render`.
    """

    scenario_id: int
    case: BoundaryCase


@dataclass(frozen=True)
class TranscendentalCase:
    """One exact-semantics scenario of a transcendental operation."""

    scenario: str
    source: int
    expected: int
    flags: int


def _checks(values: Sequence[int], element_bits: int, label: str) -> list[str]:
    lines: list[str] = []
    for index in checked_indices(values):
        lines.extend(check_dst_element_lines(values[index], element_bits, index, label))
    return lines


def _acquire_lines() -> list[str]:
    """The per-case re-acquire every table-driven case performs."""

    return [
        "    ame.release",
        "    li      t0, 0",
        "    ame.acquire t1, t0",
        "    EXPECT  t1, 1",
    ]


class FloatMathCases(Template):
    """Emit one datatype's nominal (or transcendental) case and its boundaries."""

    summary_zh = "发射一个 datatype 的标称（或超越函数）用例及其边界。"
    name = "float_math_cases"
    dtypes = FORMED_SOFTFLOAT

    def __init__(self, operation: MathOperation) -> None:
        """``operation`` is the arithmetic this instruction applies."""

        self.operation = operation

    def build(
        self, machine: MachineConfig, instruction: Instruction, dtype: DType | None
    ) -> Sequence[Case]:
        if dtype is None:
            raise ValueError("a float-math case is always formed from a datatype")
        operation = self.operation
        if operation.is_transcendental:
            payloads: list[object] = [
                TranscendentalCase(*fields)
                for fields in transcendental_cases(operation, dtype.name, dtype.bits)
            ]
        else:
            payloads = [
                None,
                *(
                    BoundaryScenario(scenario_id, boundary)
                    for scenario_id, boundary in enumerate(
                        operation.boundary_cases(
                            dtype.name, dtype.bits, FLOAT_BOUNDARIES[dtype.name]
                        )
                    )
                ),
            ]
        return [Case(number=0, dtype=dtype, payload=payload) for payload in payloads]

    def render(
        self,
        machine: MachineConfig,
        instruction: FloatMathInstruction,
        case: Case,
        out: CaseOutput,
    ) -> None:
        if case.dtype is None:
            raise ValueError("a float-math case is always formed from a datatype")
        dtype = case.dtype
        index = domain_index(machine, dtype, self.dtypes)
        destination = choose_m_group_base(
            machine.num_m_regs, dtype.bits, machine.uds, PREFERRED_DESTINATION_BASE
        )
        if case.payload is None:
            self._render_nominal(machine, instruction, dtype, index, destination, out)
        elif isinstance(case.payload, BoundaryScenario):
            self._render_boundary(
                machine, instruction, dtype, index, destination, case.payload, out
            )
        elif isinstance(case.payload, TranscendentalCase):
            self._render_transcendental(
                machine, instruction, dtype, index, destination, case.payload, out
            )
        else:
            raise ValueError(f"unknown float-math case payload: {case.payload!r}")

    def _render_nominal(
        self,
        machine: MachineConfig,
        instruction: FloatMathInstruction,
        dtype: DType,
        index: int,
        destination: int,
        out: CaseOutput,
    ) -> None:
        operation = self.operation
        boundaries = FLOAT_BOUNDARIES[dtype.name]
        element_count = machine.storage_elements(dtype.bits)
        source, expected = operation.nominal_values(boundaries, element_count)
        prefix = f"case{index}_{dtype_stem(dtype.name)}_"
        source_label = f"{prefix}source"
        destination_label = f"{prefix}destination"
        flags = ROUNDING_FLAGS if operation.rounds_to_integer else 0
        out.text.extend(
            [
                f"    # {instruction.name} {dtype.name}",
                *_acquire_lines(),
                f"    li      t0, {dtype.name}",
                "    msettyp m0, t0",
                f"    msettyp m{destination}, t0",
                f"    la      t1, {source_label}",
                "    mls.rm     m0, t1",
                f"    {instruction.name} m{destination}, m0",
                "    csrr    t5, amefflags",
                f"    EXPECT  t5, {flags}",
                f"    la      t2, {destination_label}",
                f"    mss.rm     m{destination}, t2",
                *_checks(expected, dtype.bits, destination_label),
            ]
        )
        out.data.extend(square_lines(source_label, source, dtype.bits, machine))
        out.data.extend(square_lines(destination_label, expected, dtype.bits, machine))
        out.data.append("")

    def _render_boundary(
        self,
        machine: MachineConfig,
        instruction: FloatMathInstruction,
        dtype: DType,
        index: int,
        destination: int,
        scenario: BoundaryScenario,
        out: CaseOutput,
    ) -> None:
        case = scenario.case
        element_count = machine.storage_elements(dtype.bits)
        label_id = index * BOUNDARY_LABEL_STRIDE + scenario.scenario_id
        prefix = f"boundary{label_id}_{dtype_stem(dtype.name)}_{case.scenario}_"
        source_label = f"{prefix}source"
        destination_label = f"{prefix}destination"
        mode_dtype = ROUNDING_MODE_DTYPES[case.rounding_mode]
        out.text.extend(
            [
                f"    # {instruction.name} {dtype.name}: {case.scenario}",
                *_acquire_lines(),
                f"    li      t0, {dtype.name} | {mode_dtype}",
                "    msettyp m0, t0",
                f"    msettyp m{destination}, t0",
                f"    la      t1, {source_label}",
                "    mls.rm     m0, t1",
                f"    {instruction.name} m{destination}, m0",
                "    csrr    t5, amefflags",
                f"    EXPECT  t5, {case.flags}",
                f"    la      t2, {destination_label}",
                f"    mss.rm     m{destination}, t2",
                *_checks([case.expected] * element_count, dtype.bits, destination_label),
            ]
        )
        out.data.extend(
            square_lines(source_label, [case.source] * element_count, dtype.bits, machine)
        )
        out.data.extend(
            square_lines(
                destination_label, [case.expected] * element_count, dtype.bits, machine
            )
        )
        out.data.append("")

    def _render_transcendental(
        self,
        machine: MachineConfig,
        instruction: FloatMathInstruction,
        dtype: DType,
        index: int,
        destination: int,
        case: TranscendentalCase,
        out: CaseOutput,
    ) -> None:
        element_count = machine.storage_elements(dtype.bits)
        prefix = f"case{index}_{dtype_stem(dtype.name)}_{case.scenario}_"
        source_label = f"{prefix}source"
        destination_label = f"{prefix}destination"
        out.text.extend(
            [
                f"    # {instruction.name} {dtype.name}: {case.scenario}",
                f"    li      t0, {dtype.name}",
                "    msettyp m0, t0",
                f"    msettyp m{destination}, t0",
                f"    la      t1, {source_label}",
                "    mls.rm     m0, t1",
                f"    la      t1, {destination_label}",
                f"    mls.rm     m{destination}, t1",
                "    csrw    amefflags, x0",
                f"    {instruction.name} m{destination}, m0",
                "    csrr    t4, amefflags",
                f"    EXPECT  t4, {case.flags}",
                f"    la      t2, {destination_label}",
                f"    mss.rm     m{destination}, t2",
                *_checks([case.expected] * element_count, dtype.bits, destination_label),
            ]
        )
        out.data.extend(
            square_lines(source_label, [case.source] * element_count, dtype.bits, machine)
        )
        out.data.extend(
            square_lines(
                destination_label, [case.expected] * element_count, dtype.bits, machine
            )
        )
        out.data.append("")


__all__ = [
    "BoundaryScenario",
    "FloatMathCases",
    "PREFERRED_DESTINATION_BASE",
    "TranscendentalCase",
]
