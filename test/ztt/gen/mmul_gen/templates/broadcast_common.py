#!/usr/bin/env python3
#
# Copyright (c) Qualcomm Technologies, Inc. and/or its subsidiaries.
# SPDX-License-Identifier: BSD-3-Clause-Clear
#
"""Shared shape of the scalar-ingress broadcast templates.

``mbcast.m.x`` is one instruction whose single output file walks through seven
groups of datatypes: plain integers, 128-bit integers, saturating integers,
saturating 128-bit integers, packed storage, floating point, and one
deliberately unsupported descriptor.  Every group is its own template because
each one owns its datatype domain, and the cases are numbered *within* a group
-- ``# case 0`` starts again for every group -- so the case number is the
position of the datatype inside its own template's domain rather than the
position of the case inside the file.

The scalar-ingress groups differ only in their domain, which is why they share
the body below; the packed-storage, floating-point, and unsupported-dtype groups
each emit something different and live in their own template files.

One departure from every other family: the file opens with its full input-case
inventory as a burst of ``# input:`` comments before the first case, and that
burst does not depend on the configuration.  It is therefore a dtype-free
template of its own, declared first, rather than a label hung on a case that
some configuration might not produce.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import TYPE_CHECKING

from mmul_gen.asm import check_dst_lines
from mmul_gen.machine import INTEGER, MachineConfig
from mmul_gen.templates.base import Case, CaseOutput, Template

if TYPE_CHECKING:
    from mmul_gen.instruction import Instruction
    from mmul_gen.machine import DType


#: The input cases the instruction covers, in the order the file reports them.
INPUT_CASES = (
    "integer",
    "integer_128",
    "saturating_integer",
    "saturating_integer_128",
    "packed_storage",
    "floating_point",
    "unsupported_dtype",
)
#: Square every group writes its broadcast into.
DESTINATION_LABEL = "dst_square"
#: Square the unsupported-dtype probe seeds and then must leave untouched.
UNSUPPORTED_SOURCE_LABEL = "mbcast_unsupported_src"
#: The scalar the integer groups broadcast into every element.
INGRESS_VALUE = 42
#: First packed-storage value; later cases step up so the bytes stay distinct.
STORAGE_VALUE_BASE = 0xA
#: Descriptor widths the floating-point group can broadcast.
FLOAT_ELEMENT_BITS = (8, 16, 32, 64)
#: Raw scalar the floating-point group broadcasts, per element width.
FLOAT_SCALARS = {
    8: 0x5A,
    16: 0x3C00,
    32: 0x3F800000,
    64: 0x3FF0000000000000,
}


def label_index(machine: MachineConfig, dtype: DType, domain: object) -> int:
    """The group-local case number of one datatype.

    The ``# case N`` numbering restarts for every datatype group, so the number
    is the datatype's position in its own template's domain rather than a counter
    shared by the whole file.
    """

    return domain(machine).index(dtype)


def unsupported_probe_values(nelem: int) -> list[int]:
    """The bytes the unsupported-dtype probe seeds its source square with."""

    return [((3 * index) + 5) & 0xFF for index in range(nelem)]


def unsupported_probe_data_lines(nelem: int) -> list[str]:
    """The probe's seeded source square."""

    from mmul_gen.asm import data_element_lines

    return [
        f".balign {nelem}",
        f"{UNSUPPORTED_SOURCE_LABEL}:",
        *data_element_lines(unsupported_probe_values(nelem), 8),
        "",
    ]


def packed_storage_bytes(value: int, element_bits: int, uds: int) -> list[int]:
    """One storage slot's bytes for a value repeated across the slot."""

    if element_bits == 4:
        element_bytes = [value | (value << 4)]
    else:
        element_bytes = [(value >> (8 * offset)) & 0xFF for offset in range(element_bits // 8)]
    return element_bytes * max(1, uds // max(8, element_bits))


def ingress_case(machine: MachineConfig, dtype: DType | None) -> list[Case]:
    """One case for one datatype; every group runs exactly one case per dtype."""

    return [Case(number=0, dtype=dtype)]


class ScalarIngressTemplate(Template, family_base=True):
    """Broadcast one scalar into every element of a whole-register descriptor."""

    dtypes = INTEGER

    def build(
        self,
        machine: MachineConfig,
        instruction: Instruction,
        dtype: DType | None,
    ) -> Sequence[Case]:
        return ingress_case(machine, dtype)

    def render(
        self,
        machine: MachineConfig,
        instruction: Instruction,
        case: Case,
        out: CaseOutput,
    ) -> None:
        if case.dtype is None:
            raise ValueError("a scalar-ingress broadcast case needs a datatype")
        index = label_index(machine, case.dtype, self.dtypes)
        out.text.extend(
            [
                f"    # case {index}: {instruction.name} {case.dtype.name}",
                f"    li      t0, {case.dtype.name}",
                "    msettyp m0, t0",
                "",
                f"    li      t4, {INGRESS_VALUE}",
                f"    {instruction.name} m0, t4, t0",
                f"    la      t3, {DESTINATION_LABEL}",
                "    mss.rm     m0, t3",
                *check_dst_lines(
                    INGRESS_VALUE, case.dtype.bits, machine=machine, label=DESTINATION_LABEL
                ),
            ]
        )


__all__ = [
    "DESTINATION_LABEL",
    "FLOAT_ELEMENT_BITS",
    "FLOAT_SCALARS",
    "INGRESS_VALUE",
    "INPUT_CASES",
    "STORAGE_VALUE_BASE",
    "UNSUPPORTED_SOURCE_LABEL",
    "ScalarIngressTemplate",
    "ingress_case",
    "label_index",
    "packed_storage_bytes",
    "unsupported_probe_data_lines",
    "unsupported_probe_values",
]
