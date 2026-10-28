#!/usr/bin/env python3
#
# Copyright (c) Qualcomm Technologies, Inc. and/or its subsidiaries.
# SPDX-License-Identifier: BSD-3-Clause-Clear
#
"""How a formed square image is laid out in M registers and in memory.

A formed operand is a stack of *images*: one ``mls.rm`` or ``mss.rm`` moves
exactly one image, and an image spans ``nregs(bits)`` M registers.  A format
narrower than the storage descriptor packs ``uds/size`` logical squares into one
image, so an operand whose two formats pack differently needs a different number
of transfers on each side -- the bug this module exists to make impossible to
write twice.

The helpers are free functions of the machine configuration so both the
mixed-format template and the rounding-mode template read the same layout code.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from mmul_gen.asm import square_lines

if TYPE_CHECKING:  # pragma: no cover - typing only
    from mmul_gen.machine import MachineConfig
    from mmul_gen.templates.base import CaseOutput


@dataclass(frozen=True)
class SquareGeometry:
    """The register groups and logical-square count one format pair needs."""

    source_base: int
    destination_base: int
    nsq: int


def pack_factor(machine: "MachineConfig", element_bits: int) -> int:
    """How many logical squares one physical image holds for a format."""

    return machine.storage_elements(element_bits) // machine.nelem


def span(machine: "MachineConfig", element_bits: int, nsq: int) -> int:
    """M registers spanned by ``nsq`` logical squares of ``element_bits``."""

    return nsq * machine.nregs(element_bits)


def register_group(
    num_m_regs: int, group_span: int, preferred: int, occupied: list[tuple[int, int]]
) -> int:
    """An aligned M-register group of ``group_span`` registers that is free."""

    if group_span > num_m_regs:
        raise ValueError(f"a {group_span}-register operand does not fit in {num_m_regs}")
    candidates = [
        base
        for base in range(0, num_m_regs - group_span + 1, group_span)
        if all(base + group_span <= low or high <= base for low, high in occupied)
    ]
    if not candidates:
        raise ValueError(
            f"no free group of {group_span} M registers in a file of {num_m_regs}"
        )
    return preferred if preferred in candidates else candidates[0]


def geometry(
    machine: "MachineConfig", source_bits: int, destination_bits: int
) -> SquareGeometry:
    """Place a source and a destination operand side by side."""

    nsq = max(pack_factor(machine, source_bits), pack_factor(machine, destination_bits))
    source_span = span(machine, source_bits, nsq)
    destination_span = span(machine, destination_bits, nsq)
    source_base = register_group(machine.num_m_regs, source_span, 0, [])
    destination_base = register_group(
        machine.num_m_regs,
        destination_span,
        16,
        [(source_base, source_base + source_span)],
    )
    return SquareGeometry(source_base, destination_base, nsq)


def transfer_steps(
    machine: "MachineConfig", nsq: int, element_bits: int, base: int, label: str
) -> list[tuple[int, str]]:
    """The register group and image label of every ``mls.rm``/``mss.rm`` step.

    One transfer moves one formed square image.  A packed format fits ``pack``
    logical squares in an image, so a packed operand needs fewer transfers than
    logical squares; a wide one needs exactly one per square.
    """

    pack = pack_factor(machine, element_bits)
    if nsq % pack != 0:
        raise ValueError(f"{nsq} logical squares do not fill {pack}-square images")
    stride = machine.nregs(element_bits)
    return [
        (base + image * stride, label if image == 0 else f"{label}_block{image}")
        for image in range(nsq // pack)
    ]


def emit_square(
    out: "CaseOutput",
    machine: "MachineConfig",
    label: str,
    values: tuple[int, ...],
    element_bits: int,
) -> None:
    """Emit one operand image, one physical square at a time."""

    per_block = machine.storage_elements(element_bits)
    if len(values) % per_block != 0:
        raise ValueError(
            f"{label}: {len(values)} elements do not fill {per_block}-element squares"
        )
    for block in range(len(values) // per_block):
        block_label = label if block == 0 else f"{label}_block{block}"
        out.data.extend(
            square_lines(
                block_label,
                values[block * per_block : (block + 1) * per_block],
                element_bits,
                machine,
            )
        )


def cycles(values: tuple[int, ...], count: int) -> tuple[int, ...]:
    """``count`` elements taken from a short value roster, in order."""

    if not values:
        raise ValueError("a case needs at least one value")
    return tuple(values[index % len(values)] for index in range(count))


def sampled_indices(count: int) -> list[int]:
    """The element positions a case checks: the first few and the last."""

    return sorted({0, 1, 2, count - 1})


__all__ = [
    "SquareGeometry",
    "cycles",
    "emit_square",
    "geometry",
    "pack_factor",
    "register_group",
    "sampled_indices",
    "span",
    "transfer_steps",
]
