#!/usr/bin/env python3
#
# Copyright (c) Qualcomm Technologies, Inc. and/or its subsidiaries.
# SPDX-License-Identifier: BSD-3-Clause-Clear
#
"""The register vocabulary and the case emitter shared by every elementwise recipe.

Every elementwise case has the same shape: load its operand squares into M
registers (or a scalar into a general-purpose register), run the instruction,
and store the destination square.  Which operands, which registers, and which
instruction line differ per instruction and per recipe, so those differences are
a table entry (:class:`CasePlan`); the shared shape is written once here.

A plan names registers symbolically so that one entry describes every
configuration: :data:`ZERO` is the group at register 0, :data:`SOURCE` is the
second operand group, :data:`SCALAR_DEST` is the group a scalar form writes, and
:data:`SCALAR` is the general-purpose register holding a scalar operand.
"""

from __future__ import annotations

import re
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from typing import TypeVar

from mmul_gen.asm import hex_value
from mmul_gen.machine import MachineConfig

#: The general-purpose register a "square" scalar is addressed through.
ADDRESS_TEMP = "t1"

#: The M-register group at register 0.
ZERO = "0"
#: The second operand's M-register group.
SOURCE = "b"
#: The M-register group a scalar form writes its destination to.
SCALAR_DEST = "x"
#: The general-purpose register holding a scalar operand.
SCALAR = "scalar"

#: A plan may also name a group by its resolved number, as "m12".
GROUP = re.compile(r"m[0-9]+\Z")

#: X-register the scalar forms put their destination in, and the source group.
EW_X_DEST_REG = 8
EW_X_SRC_REG = 0

Key = TypeVar("Key")


def x_dest_reg(element_bits: int, machine: MachineConfig) -> int:
    """Pick an X-form destination that does not overlap its M source group.

    The preferred choice is m8 (m16 for 64-bit and up); when that is illegal
    for the configured file, the highest aligned group that stays disjoint from
    m0 is used instead, so an FP64 case on a 16-register implementation still
    gets a legal, non-aliasing destination.
    """

    source_regs = machine.nregs(element_bits)
    preferred = EW_X_DEST_REG if element_bits < 64 else 16
    if preferred + source_regs <= machine.num_m_regs and preferred >= source_regs:
        return preferred
    candidates = [
        reg
        for reg in range(source_regs, machine.num_m_regs, source_regs)
        if reg + source_regs <= machine.num_m_regs
    ]
    if candidates:
        return candidates[-1]
    # Unary and matrix forms still call the type-setup helper; they need no
    # second group, so m0 stays a valid placeholder here.
    return 0


@dataclass(frozen=True)
class Operand:
    """One operand of a case, in emission order.

    ``register`` names the M-register group to load the operand square into, or
    is ``None`` for a scalar operand.  ``source`` says where a scalar's value
    comes from: ``"hex"`` and ``"decimal"`` materialise the number, which the
    integer and float recipes spell differently, and ``"square"`` loads the value
    out of a data square, which the rounding recipes do.  Matrix operands ignore
    it.
    """

    role: str
    temp: str
    register: str | None = None
    source: str = "hex"


@dataclass(frozen=True)
class CasePlan:
    """What one elementwise case loads, and where it stores the answer.

    ``seed`` is an operand loaded before the others, into a group of its own: the
    comparisons use it to plant the *opposite* answer, so a passing test proves
    the instruction wrote the destination rather than leaving it alone.
    """

    operands: tuple[Operand, ...]
    dest: str
    sources: tuple[str, ...]
    seed: Operand | None = None


def vector_operands(first: str, second: str) -> tuple[Operand, ...]:
    """The usual two matrix operands: ``first`` into register 0, ``second`` next."""

    return (Operand(first, "t1", ZERO), Operand(second, "t2", SOURCE))


def plan_for(key: Key, plans: Mapping[Key, CasePlan], recipe: str) -> CasePlan:
    """The plan of one instruction or form, or a fail-fast error naming the recipe."""

    try:
        return plans[key]
    except KeyError:
        raise ValueError(f"unsupported {recipe}: {key}") from None


def plan_lines(
    plan: CasePlan,
    mnemonic: str,
    labels: Mapping[str, str],
    values: Callable[[str], int] | None,
    element_bits: int,
    machine: MachineConfig,
    *,
    store: bool = True,
) -> list[str]:
    """The operand loads and the instruction line of one case.

    ``store`` adds the destination store, which the rounding recipes emit
    themselves so that they can put the flags check between the two.
    """

    source_reg = f"m{machine.nregs(element_bits)}"
    scalar_temps = [
        operand.temp for operand in plan.operands if operand.register is None
    ]
    if len(scalar_temps) > 1:
        raise ValueError(f"{mnemonic} declares more than one scalar operand")

    def register(token: str) -> str:
        if token == ZERO:
            return "m0"
        if token == SOURCE:
            return source_reg
        if token == SCALAR_DEST:
            return f"m{x_dest_reg(element_bits, machine)}"
        if token == SCALAR:
            if not scalar_temps:
                raise ValueError(f"{mnemonic} names a scalar it does not load")
            return scalar_temps[0]
        if GROUP.match(token):
            # A recipe whose registers come from the group chooser names the group
            # it picked by number, because no symbolic name can describe it.
            return token
        raise ValueError(f"{mnemonic} names an unknown register: {token}")

    def scalar_lines(operand: Operand) -> list[str]:
        if operand.source == "square":
            return [
                f"    la      {ADDRESS_TEMP}, {labels[operand.role]}",
                f"    ld      {operand.temp}, 0({ADDRESS_TEMP})",
            ]
        if values is None:
            raise ValueError(
                f"{mnemonic} materialises a scalar but was given no values"
            )
        if operand.source == "hex":
            value = hex_value(values(operand.role), element_bits)
        elif operand.source == "decimal":
            value = str(values(operand.role))
        else:
            raise ValueError(f"{mnemonic} materialises a scalar from {operand.source!r}")
        return [f"    li      {operand.temp}, {value}"]

    lines: list[str] = []
    if plan.seed is not None:
        assert plan.seed.register is not None
        lines.append(f"    la      {plan.seed.temp}, {labels[plan.seed.role]}")
        lines.append(f"    mls.rm     {register(plan.seed.register)}, {plan.seed.temp}")
    for operand in plan.operands:
        if operand.register is None:
            lines.extend(scalar_lines(operand))
            continue
        lines.append(f"    la      {operand.temp}, {labels[operand.role]}")
        lines.append(f"    mls.rm     {register(operand.register)}, {operand.temp}")
    sources = ", ".join(register(token) for token in plan.sources)
    lines.append(f"    {mnemonic} {register(plan.dest)}, {sources}")
    if store:
        lines.append("    la      t3, dst_square")
        lines.append(f"    mss.rm     {register(plan.dest)}, t3")
    return lines


__all__ = [
    "ADDRESS_TEMP",
    "EW_X_DEST_REG",
    "GROUP",
    "EW_X_SRC_REG",
    "SCALAR",
    "SCALAR_DEST",
    "SOURCE",
    "ZERO",
    "CasePlan",
    "Operand",
    "plan_for",
    "plan_lines",
    "vector_operands",
    "x_dest_reg",
]
