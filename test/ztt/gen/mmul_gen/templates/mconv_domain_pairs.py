#!/usr/bin/env python3
#
# Copyright (c) Qualcomm Technologies, Inc. and/or its subsidiaries.
# SPDX-License-Identifier: BSD-3-Clause-Clear
#
"""``mconv.ew`` integer conversion across mismatched value domains.

The conversion must keep the source's *mathematical* value while it re-scales
into the destination domain.  A 128-bit source whose value is ``2**127`` cannot
be held by a signed intermediate, so an implementation that routes it through a
signed accumulator loses the domain and clamps to the wrong bound (or reports no
saturation at all).  Each pair below is chosen so that the correct result is the
destination's positive limit:

* ``UINT128 2**127 -> INT8_SAT``   -> ``0x7F``
* ``UINT128 2**127 -> UINT32_SAT`` -> ``0xFFFFFFFF``
* ``UINT128 2**127 -> INT128_SAT`` -> ``0x7FFF...F``

The unsigned-to-signed crossings exercise the domain change; the last pair,
``INT128 -1 -> UINT8_SAT``, exercises the other direction: a negative value into
an unsigned domain saturates to ``0``.  Every pair must also raise ``amexsat``.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from typing import TYPE_CHECKING

from mmul_gen.asm import check_dst_element_lines, repeated_square_lines
from mmul_gen.machine import INTEGER128, MachineConfig, dtype_stem
from mmul_gen.templates.base import Case, CaseOutput, Template, case_payload, domain_index

if TYPE_CHECKING:
    from mmul_gen.instruction import Instruction
    from mmul_gen.machine import DType

#: The upload unit the conversion pairs are stated in: at UDS 8 every operand
#: forms one square, so a pair is a plain element-by-element conversion.
CONVERSION_UDS = 8
#: Physical register count of a 128-bit formed operand at that UDS.
SOURCE_BITS = 128


@dataclass(frozen=True)
class ConversionPair:
    """One source datatype, one destination datatype, and the expected result."""

    source_dtype: str
    source_value: int
    destination_dtype: str
    destination_bits: int
    expected: int


def _pairs_for(source_dtype: str) -> tuple[ConversionPair, ...]:
    """The conversion pairs each 128-bit source is checked through."""

    if source_dtype == "AME_UINT128_DTYPE":
        unsigned_high_bit = 1 << 127
        return (
            ConversionPair(
                source_dtype, unsigned_high_bit, "AME_INT8_SAT_DTYPE", 8, 0x7F
            ),
            ConversionPair(
                source_dtype, unsigned_high_bit, "AME_UINT32_SAT_DTYPE", 32, 0xFFFFFFFF
            ),
            ConversionPair(
                source_dtype,
                unsigned_high_bit,
                "AME_INT128_SAT_DTYPE",
                128,
                (1 << 127) - 1,
            ),
        )
    if source_dtype == "AME_INT128_DTYPE":
        return (
            ConversionPair(source_dtype, -1, "AME_UINT8_SAT_DTYPE", 8, 0x00),
        )
    raise ValueError(f"no integer conversion pairs declared for {source_dtype}")


class MconvDomainPairs(Template):
    """Convert a 128-bit source into narrower saturating destination domains."""

    name = "integer_conversion_domain_pairs"
    dtypes = INTEGER128

    def fits(
        self,
        machine: MachineConfig,
        instruction: Instruction,
        dtype: DType | None = None,
    ) -> bool:
        if dtype is None:
            raise ValueError("a conversion pair is always formed from a datatype")
        if machine.uds != CONVERSION_UDS or dtype.bits != SOURCE_BITS:
            return False
        return any(
            machine.nregs(SOURCE_BITS) + machine.nregs(pair.destination_bits)
            <= machine.num_m_regs
            for pair in _pairs_for(dtype.name)
        )

    def build(
        self, machine: MachineConfig, instruction: Instruction, dtype: DType | None
    ) -> Sequence[Case]:
        if dtype is None:
            raise ValueError("a conversion pair is always formed from a datatype")
        available = {declared.name for declared in machine.dtypes}
        return [
            Case(number=0, dtype=dtype, payload=pair)
            for pair in _pairs_for(dtype.name)
            if pair.destination_dtype in available
            and machine.nregs(SOURCE_BITS) + machine.nregs(pair.destination_bits)
            <= machine.num_m_regs
        ]

    def render(
        self,
        machine: MachineConfig,
        instruction: Instruction,
        case: Case,
        out: CaseOutput,
    ) -> None:
        pair = case_payload(ConversionPair, case)
        if case.dtype is None:
            raise ValueError("a conversion pair is always formed from a datatype")
        source_index = domain_index(machine, case.dtype, self.dtypes)
        number = case.number
        stem = (
            f"conv{source_index}_{dtype_stem(pair.source_dtype)}"
            f"_to_{dtype_stem(pair.destination_dtype)}"
        )
        source_label = f"{stem}_src_square"
        destination_label = f"{stem}_dst_square"
        destination_reg = machine.nregs(SOURCE_BITS)
        source_elements = machine.storage_elements(SOURCE_BITS)

        out.text.extend(
            [
                f"    # case {number}: {instruction.name} {pair.source_dtype} -> "
                f"{pair.destination_dtype} integer conversion domain",
                f"    li      t0, {pair.source_dtype}",
                "    msettyp m0, t0",
                f"    li      t0, {pair.destination_dtype}",
                f"    msettyp m{destination_reg}, t0",
                "    li      t6, 0",
                "    csrw    amexsat, t6",
                "",
                f"    la      t1, {source_label}",
                "    mls.rm     m0, t1",
                f"    {instruction.name} m{destination_reg}, m0",
                f"    la      t3, {destination_label}",
                f"    mss.rm     m{destination_reg}, t3",
                "    csrr    t5, amexsat",
                "    EXPECT  t5, 1",
            ]
        )
        for element_index in (0, source_elements - 1):
            out.text.extend(
                check_dst_element_lines(
                    pair.expected,
                    pair.destination_bits,
                    element_index,
                    destination_label,
                )
            )
        out.data.extend(
            repeated_square_lines(
                source_label, pair.source_value, SOURCE_BITS, machine
            )
        )
        out.data.extend(
            self._destination_lines(
                destination_label, pair.destination_bits, machine
            )
        )
        out.data.append("")

    @staticmethod
    def _destination_lines(
        label: str, destination_bits: int, machine: MachineConfig
    ) -> list[str]:
        """A destination square pre-filled so a partial write cannot pass."""

        square_bytes = machine.square_bytes(destination_bits)
        return [
            f".balign {square_bytes}",
            f"{label}:",
            f"    .rept {square_bytes}",
            "    .byte 0xa5",
            "    .endr",
        ]


__all__ = ["CONVERSION_UDS", "ConversionPair", "MconvDomainPairs"]


MCONV_DOMAIN_PAIRS = MconvDomainPairs()
