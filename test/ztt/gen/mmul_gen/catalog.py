#!/usr/bin/env python3
#
# Copyright (c) Qualcomm Technologies, Inc. and/or its subsidiaries.
# SPDX-License-Identifier: BSD-3-Clause-Clear
#
"""The generator entry point: the whole instruction inventory.

This module holds an ordered sequence of instruction *families* and one loop
that renders them.  It contains no instruction-specific data, so reviewing an
instruction never means reading a shared dispatch function, and adding one
means listing a class here.

Family order and instruction order inside a family are part of the
generated-suite contract: the catalog fixes both orders, and the frozen
source hashes in the tests depend on them.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from mmul_gen.instruction import (
    GeneratedSource,
    Instruction,
)
from mmul_gen.instructions.mmul.base import MatrixMultiplyInstruction
from mmul_gen.instructions import (
    AccSpanExceptions,
    Agettyp,
    AmeAcquire,
    AmeRelease,
    Asettyp,
    MabsEw,
    MabsdiffEw,
    MabsdiffEwX,
    MaddEw,
    MaddEwX,
    MandEw,
    MandEwX,
    MandnotEw,
    MandnotEwX,
    MbcastMX,
    McmovgeEw,
    McmovltEw,
    McmpgeEw,
    McmpgeEwX,
    McmpltEw,
    McmpltEwX,
    McolbcastEwX,
    McolgatherEw,
    McolidEw,
    McolscataddEw,
    McolscatmaxEw,
    McolshiftEwX,
    McolunzipEw,
    McolzipEw,
    MconvEw,
    McosEw,
    Mexp2Ew,
    MfrintmEw,
    MfrintnEw,
    MfrintpEw,
    MfrintzEw,
    Mgettyp,
    MhdiffEw,
    MhdiffEwX,
    MldexpEw,
    MldexpEwX,
    MldexpaccEw,
    MldexpaccEwX,
    Mlog2Ew,
    Mlog2subEw,
    Mlog2subEwX,
    Mls1r,
    MlsCm,
    MlsRm,
    MlsSt,
    MlsTst,
    MmaxEw,
    MmaxEwX,
    MmeanEw,
    MmeanEwX,
    MminEw,
    MminEwX,
    MmovAM,
    MmovAMAccSpan,
    MmovMA,
    MmovMAAccSpan,
    MmovMM,
    Mmove16MX,
    Mmove16XM,
    Mmove32MX,
    Mmove32XM,
    Mmove64MX,
    Mmove64XM,
    Mmove8MX,
    Mmove8XM,
    MmulAcc2d,
    MmulAccNeg2d,
    MmulAtAcc2d,
    MmulAtAccNeg2d,
    MmulBtAcc2d,
    MmulBtAccNeg2d,
    MmulEw,
    MmulEwX,
    MmulaccEw,
    MmulaccEwX,
    MmulaccnegEw,
    MmulaccnegEwX,
    MmuladdEw,
    MmuladdEwX,
    MmulnegEw,
    MmulnegEwX,
    MmulsubEw,
    MmulsubEwX,
    MorEw,
    MorEwX,
    MornotEw,
    MornotEwX,
    MpackEwX,
    MprefixaddCol,
    MprefixaddRow,
    MprefixmaxCol,
    MprefixmaxRow,
    MrdexpEw,
    MrdexpaccEw,
    MrecEw,
    MreduceaddCol,
    MreduceaddRow,
    MreducemaxCol,
    MreducemaxRow,
    MreduceminCol,
    MreduceminRow,
    MrowbcastEwX,
    MrowgatherEw,
    MrowidEw,
    MrowscataddEw,
    MrowscatmaxEw,
    MrowshiftEwX,
    MrowunzipEw,
    MrowzipEw,
    MrsqrtEw,
    MselgeEw,
    MselltEw,
    Msettyp,
    MsinEw,
    MsllEw,
    MsllEwX,
    MsqrtEw,
    MsraEw,
    MsraEwX,
    MsrlEw,
    MsrlEwX,
    Mss1r,
    MssCm,
    MssRm,
    MssSt,
    MssTst,
    MsubEw,
    MsubEwX,
    Msublog2Ew,
    Msublog2EwX,
    MtanhEw,
    MunpackEwX,
    MxorEw,
    MxorEwX,
    Mzero2dAcc,
    Mzero2dM,
)
from mmul_gen.machine import MachineConfig


@dataclass(frozen=True)
class Family:
    """One instruction family: its name and its members."""

    name: str
    instructions: tuple[Instruction, ...]


ACC_SPAN_INSTRUCTIONS: tuple[Instruction, ...] = (
    MmovMAAccSpan(),
    MmovAMAccSpan(),
    AccSpanExceptions(),
)

AXIS_PERMUTE_INSTRUCTIONS: tuple[Instruction, ...] = (
    McolbcastEwX(),
    MrowbcastEwX(),
    McolidEw(),
    MrowidEw(),
    McolshiftEwX(),
    MrowshiftEwX(),
)

BACKEND_INSTRUCTIONS: tuple[Instruction, ...] = (
    AmeAcquire(),
    AmeRelease(),
)

ELEMENTWISE_INSTRUCTIONS: tuple[Instruction, ...] = (
    MaddEw(),
    MsubEw(),
    MandEw(),
    MandnotEw(),
    MorEw(),
    MornotEw(),
    MxorEw(),
    MmaxEw(),
    MminEw(),
    MabsdiffEw(),
    MhdiffEw(),
    MmeanEw(),
    MmulEw(),
    MmulnegEw(),
    McmpgeEw(),
    McmpltEw(),
    MselgeEw(),
    MselltEw(),
    MaddEwX(),
    MsubEwX(),
    MandEwX(),
    MandnotEwX(),
    MorEwX(),
    MornotEwX(),
    MxorEwX(),
    MmaxEwX(),
    MminEwX(),
    MabsdiffEwX(),
    MhdiffEwX(),
    MmeanEwX(),
    MmulEwX(),
    MmulnegEwX(),
    McmpgeEwX(),
    McmpltEwX(),
    MmulaccEw(),
    MmulaccnegEw(),
    MmuladdEw(),
    MmulsubEw(),
    McmovgeEw(),
    McmovltEw(),
    MmulaccEwX(),
    MmulaccnegEwX(),
    MmuladdEwX(),
    MmulsubEwX(),
    MmovMM(),
    MabsEw(),
)

FLOAT_MATH_INSTRUCTIONS: tuple[Instruction, ...] = (
    MfrintmEw(),
    MfrintnEw(),
    MfrintpEw(),
    MfrintzEw(),
    MrecEw(),
    MrsqrtEw(),
    MsqrtEw(),
    McosEw(),
    MsinEw(),
    MtanhEw(),
)

INTEGER_SHIFT_INSTRUCTIONS: tuple[Instruction, ...] = (
    MsllEw(),
    MsllEwX(),
    MsraEw(),
    MsraEwX(),
    MsrlEw(),
    MsrlEwX(),
)

LOAD_STORE_INSTRUCTIONS: tuple[Instruction, ...] = (
    Mls1r(),
    Mss1r(),
)

LOGEXP_INSTRUCTIONS: tuple[Instruction, ...] = (
    Mexp2Ew(),
    Mlog2Ew(),
    MldexpEw(),
    MrdexpEw(),
    MldexpaccEw(),
    MrdexpaccEw(),
    MldexpEwX(),
    MldexpaccEwX(),
    Mlog2subEw(),
    Msublog2Ew(),
    Mlog2subEwX(),
    Msublog2EwX(),
)

MATRIX_OPS_INSTRUCTIONS: tuple[Instruction, ...] = (
    McolgatherEw(),
    McolscataddEw(),
    McolscatmaxEw(),
    McolunzipEw(),
    McolzipEw(),
    MprefixaddCol(),
    MprefixaddRow(),
    MprefixmaxCol(),
    MprefixmaxRow(),
    MreduceaddCol(),
    MreduceaddRow(),
    MreducemaxCol(),
    MreducemaxRow(),
    MreduceminCol(),
    MreduceminRow(),
    MrowgatherEw(),
    MrowscataddEw(),
    MrowscatmaxEw(),
    MrowunzipEw(),
    MrowzipEw(),
)

MCONV_INSTRUCTIONS: tuple[Instruction, ...] = (MconvEw(),)

MATRIX_MULTIPLY_INSTRUCTIONS: tuple[MatrixMultiplyInstruction, ...] = (
    MmulAcc2d(),
    MmulAccNeg2d(),
    MmulAtAcc2d(),
    MmulAtAccNeg2d(),
    MmulBtAcc2d(),
    MmulBtAccNeg2d(),
)

STRIDED_MEMORY_INSTRUCTIONS: tuple[Instruction, ...] = (
    MlsSt(),
    MlsTst(),
    MssSt(),
    MssTst(),
)

PACK_INSTRUCTIONS: tuple[Instruction, ...] = (
    MpackEwX(),
    MunpackEwX(),
)

ACCUMULATOR_INSTRUCTIONS: tuple[Instruction, ...] = (
    Mzero2dAcc(),
    Mzero2dM(),
    MmovMA(),
    MmovAM(),
)

BROADCAST_INSTRUCTIONS: tuple[Instruction, ...] = (MbcastMX(),)

DEBUG_MOVE_INSTRUCTIONS: tuple[Instruction, ...] = (
    Mmove8MX(),
    Mmove16MX(),
    Mmove32MX(),
    Mmove64MX(),
    Mmove8XM(),
    Mmove16XM(),
    Mmove32XM(),
    Mmove64XM(),
)

MEMORY_ORDER_INSTRUCTIONS: tuple[Instruction, ...] = (
    MlsRm(),
    MssCm(),
    MlsCm(),
    MssRm(),
)

TYPE_REGISTER_INSTRUCTIONS: tuple[Instruction, ...] = (
    Msettyp(),
    Mgettyp(),
    Asettyp(),
    Agettyp(),
)


#: Generation order is part of the generated-suite contract.
INSTRUCTION_FAMILIES: tuple[Family, ...] = (
    Family("accumulator", ACCUMULATOR_INSTRUCTIONS),
    Family("acc_span", ACC_SPAN_INSTRUCTIONS),
    Family("axis_permute", AXIS_PERMUTE_INSTRUCTIONS),
    Family("backend", BACKEND_INSTRUCTIONS),
    Family("broadcast", BROADCAST_INSTRUCTIONS),
    Family("debug_move", DEBUG_MOVE_INSTRUCTIONS),
    Family("elementwise", ELEMENTWISE_INSTRUCTIONS),
    Family("float_math", FLOAT_MATH_INSTRUCTIONS),
    Family("integer_shift", INTEGER_SHIFT_INSTRUCTIONS),
    Family("load_store", LOAD_STORE_INSTRUCTIONS),
    Family("logexp", LOGEXP_INSTRUCTIONS),
    Family("matrix_ops", MATRIX_OPS_INSTRUCTIONS),
    Family("mconv", MCONV_INSTRUCTIONS),
    Family("memory_order", MEMORY_ORDER_INSTRUCTIONS),
    Family("mmul", MATRIX_MULTIPLY_INSTRUCTIONS),
    Family("pack", PACK_INSTRUCTIONS),
    Family("strided_memory", STRIDED_MEMORY_INSTRUCTIONS),
    Family("type_register", TYPE_REGISTER_INSTRUCTIONS),
)

#: Every instruction, in generated-suite order.
ALL_INSTRUCTIONS: tuple[Instruction, ...] = tuple(
    instruction
    for family in INSTRUCTION_FAMILIES
    for instruction in family.instructions
)


def generate_all(machine: MachineConfig) -> list[GeneratedSource]:
    """Render every test source for one configuration."""

    return [
        source
        for instruction in ALL_INSTRUCTIONS
        if (source := instruction.gen(machine)) is not None
    ]


def find_instruction(mnemonic: str) -> Instruction:
    """Look up one instruction by mnemonic, failing loudly on a typo."""

    for instruction in ALL_INSTRUCTIONS:
        if instruction.name == mnemonic:
            return instruction
    known = ", ".join(instruction.name for instruction in ALL_INSTRUCTIONS)
    raise KeyError(f"unknown instruction {mnemonic!r}; known: {known}")


def select_instructions(families: Sequence[str]) -> tuple[Instruction, ...]:
    """Every instruction of the named families, in generated-suite order.

    No family name means the whole inventory; an unknown name fails loudly.
    """

    if not families:
        return ALL_INSTRUCTIONS
    wanted = set(families)
    known = {family.name for family in INSTRUCTION_FAMILIES}
    unknown = wanted - known
    if unknown:
        raise KeyError(
            f"unknown instruction family {sorted(unknown)}; known: {sorted(known)}"
        )
    return tuple(
        instruction
        for family in INSTRUCTION_FAMILIES
        if family.name in wanted
        for instruction in family.instructions
    )


def describe_instructions(
    machine: MachineConfig,
    instructions: Sequence[Instruction] = ALL_INSTRUCTIONS,
) -> Sequence[dict[str, object]]:
    """Structured, human-readable inventory of the configured generators.

    ``input_cases`` names every stimulus the instruction covers, in the order a
    source emits them, read from the templates the instruction constructed; a
    family that narrows its inventory per datatype (the 128-bit template of a
    scalar form, say) still reports the whole declaration here, because that is
    what the templates state.
    """

    return [
        {
            "name": instruction.name,
            "summary": instruction.summary,
            "operands": [
                f"{operand.role}:{operand.register_class}"
                for operand in instruction.operands
            ],
            "input_cases": list(instruction.input_case_names),
            "templates": [
                {"name": template.name, "summary": template.summary}
                for template in instruction.template_set(machine)
            ],
            "datatype_domains": [
                domain.name for domain in instruction.datatype_domains
            ],
            "dtypes": [dtype.name for dtype in instruction.supported_dtypes(machine)],
            "file": instruction.file_name,
        }
        for instruction in instructions
    ]


__all__ = [
    "ACC_SPAN_INSTRUCTIONS",
    "ELEMENTWISE_INSTRUCTIONS",
    "FLOAT_MATH_INSTRUCTIONS",
    "MATRIX_OPS_INSTRUCTIONS",
    "LOGEXP_INSTRUCTIONS",
    "AXIS_PERMUTE_INSTRUCTIONS",
    "BROADCAST_INSTRUCTIONS",
    "INTEGER_SHIFT_INSTRUCTIONS",
    "ACCUMULATOR_INSTRUCTIONS",
    "ALL_INSTRUCTIONS",
    "BACKEND_INSTRUCTIONS",
    "LOAD_STORE_INSTRUCTIONS",
    "Family",
    "INSTRUCTION_FAMILIES",
    "MATRIX_MULTIPLY_INSTRUCTIONS",
    "MCONV_INSTRUCTIONS",
    "MEMORY_ORDER_INSTRUCTIONS",
    "PACK_INSTRUCTIONS",
    "STRIDED_MEMORY_INSTRUCTIONS",
    "TYPE_REGISTER_INSTRUCTIONS",
    "describe_instructions",
    "find_instruction",
    "generate_all",
    "select_instructions",
]
