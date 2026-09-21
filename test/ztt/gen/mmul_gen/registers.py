#!/usr/bin/env python3
#
# Copyright (c) Qualcomm Technologies, Inc. and/or its subsidiaries.
# SPDX-License-Identifier: BSD-3-Clause-Clear
#
"""M-register and accumulator layouts.

A layout is declared once, as a tuple of :class:`MRegisterRole` spans, and then
*resolved* into concrete register numbers against a configured register file.
Resolution never substitutes a different register when the requested layout
does not fit: an infeasible layout is simply absent from the returned tuple, so
the generated assembly stays an honest record of what the configured machine
can run.

The declared layout is also part of the review artifact: every generated case
emits its resolved ``M layout``/``ACC layout`` comment.
"""

from __future__ import annotations

from collections.abc import Sequence

from dataclasses import dataclass

from mmul_gen.machine import MachineConfig


@dataclass(frozen=True)
class MRegisterRole:
    """One logical M-register operand and the span it forms.

    ``reuse_of`` records a deliberate temporal alias.  A matrix product may
    write its accumulator result back over the first source group once that
    source has been consumed; the alias must cover exactly the same span.
    """

    role: str
    nregs: int
    reuse_of: str | None = None

    def __post_init__(self) -> None:
        if not self.role:
            raise ValueError("M-register role needs a name")
        if self.nregs <= 0:
            raise ValueError(f"M-register role {self.role!r} has invalid span {self.nregs}")


@dataclass(frozen=True)
class MRegisterGroup:
    """One declared role placed at a concrete base register."""

    role: str
    base: int
    nregs: int
    reuse_of: str | None = None

    def __post_init__(self) -> None:
        if not self.role:
            raise ValueError("M-register group needs a role name")
        if self.base < 0 or self.nregs <= 0:
            raise ValueError(f"invalid M-register group: {self}")
        if self.base % self.nregs:
            raise ValueError(
                f"M-register group {self.role!r} at m{self.base} is not aligned to "
                f"its {self.nregs}-register span"
            )

    @property
    def end(self) -> int:
        return self.base + self.nregs

    @property
    def register_text(self) -> str:
        if self.nregs == 1:
            return f"m{self.base}"
        return f"m{self.base}..m{self.end - 1}"


@dataclass(frozen=True)
class MRegisterLayout:
    """A fully resolved, reviewable M-register layout for one test case."""

    name: str
    description: str
    groups: tuple[MRegisterGroup, ...]

    def __post_init__(self) -> None:
        if not self.name:
            raise ValueError("M-register layout needs a name")
        if not self.groups:
            raise ValueError("M-register layout needs at least one group")

        seen: dict[str, MRegisterGroup] = {}
        for group in self.groups:
            if group.role in seen:
                raise ValueError(f"duplicate M-register role {group.role!r}")
            if group.reuse_of is not None:
                target = seen.get(group.reuse_of)
                if target is None:
                    raise ValueError(
                        f"M-register role {group.role!r} reuses unknown or later role "
                        f"{group.reuse_of!r}"
                    )
                if (group.base, group.nregs) != (target.base, target.nregs):
                    raise ValueError(
                        f"M-register role {group.role!r} must exactly reuse "
                        f"{group.reuse_of!r}"
                    )
            for earlier in seen.values():
                overlaps = group.base < earlier.end and earlier.base < group.end
                aliased = (
                    group.reuse_of == earlier.role
                    and group.base == earlier.base
                    and group.nregs == earlier.nregs
                )
                if overlaps and not aliased:
                    raise ValueError(
                        f"M-register roles {earlier.role!r} and {group.role!r} overlap "
                        "without an explicit temporal alias"
                    )
            seen[group.role] = group

    def group(self, role: str) -> MRegisterGroup:
        for group in self.groups:
            if group.role == role:
                return group
        raise KeyError(f"M-register layout {self.name!r} has no role {role!r}")

    def base(self, role: str) -> int:
        return self.group(role).base

    def comment(self) -> str:
        parts = []
        for group in self.groups:
            text = f"{group.role}={group.register_text}"
            if group.reuse_of is not None:
                text += f" (reuses {group.reuse_of})"
            parts.append(text)
        return f"M layout [{self.name}]: " + ", ".join(parts)


@dataclass(frozen=True)
class AccumulatorOperand:
    """A resolved Acc/Ad operand, optionally a packed span."""

    name: str
    description: str
    base: int
    span: int = 1
    #: Span cases that cross the accumulator file are declared with
    #: ``legal=False``: the point of those tests is that the span is rejected,
    #: and the layout comment has to say so.
    legal: bool = True

    def __post_init__(self) -> None:
        if not self.name:
            raise ValueError("accumulator operand needs a name")
        if self.base < 0 or self.span <= 0:
            raise ValueError(f"invalid accumulator operand: {self}")

    @property
    def end(self) -> int:
        return self.base + self.span

    @property
    def register_text(self) -> str:
        if self.span == 1:
            return f"acc{self.base}"
        return f"acc{self.base}..acc{self.end - 1}"

    def comment(self) -> str:
        """Annotation emitted above every accumulator operand.

        The legality word is part of the emitted byte-for-byte contract, so it is
        rendered rather than derived from the span.
        """

        status = "legal" if self.legal else "expected illegal"
        return f"ACC layout [{self.name}, {status}]: {self.register_text}"


@dataclass(frozen=True)
class RegisterLayout:
    """The register-file choices attached to one generated case.

    A case selects the files it addresses; instruction families that touch only
    one file leave the other unset, and the emitted comments follow.
    """

    m: MRegisterLayout | None = None
    acc: AccumulatorOperand | None = None

    def __post_init__(self) -> None:
        if self.m is None and self.acc is None:
            raise ValueError("a register layout must select at least one register file")

    def comment_lines(self) -> list[str]:
        lines = []
        if self.m is not None:
            lines.append(f"    # {self.m.comment()}")
        if self.acc is not None:
            lines.append(f"    # {self.acc.comment()}")
        return lines

    def group_base(self, role: str) -> int:
        """Base M register of ``role`` in this case's M layout."""

        if self.m is None:
            raise ValueError("this case addresses no M-register layout")
        return self.m.base(role)

    def acc_base(self) -> int:
        """Base of this case's accumulator operand."""

        if self.acc is None:
            raise ValueError("this case addresses no accumulator")
        return self.acc.base


def _align_up(value: int, alignment: int) -> int:
    return ((value + alignment - 1) // alignment) * alignment


def _low_bases(roles: Sequence[MRegisterRole], num_m_regs: int) -> dict[str, int] | None:
    bases: dict[str, int] = {}
    cursor = 0
    for role in roles:
        base = _align_up(cursor, role.nregs)
        if base + role.nregs > num_m_regs:
            return None
        bases[role.role] = base
        cursor = base + role.nregs
    return bases


def _high_bases(roles: Sequence[MRegisterRole], num_m_regs: int) -> dict[str, int] | None:
    bases: dict[str, int] = {}
    cursor = num_m_regs
    for role in reversed(roles):
        base = ((cursor - role.nregs) // role.nregs) * role.nregs
        if base < 0:
            return None
        bases[role.role] = base
        cursor = base
    return bases


def _boundary_bases(roles: Sequence[MRegisterRole], num_m_regs: int) -> dict[str, int] | None:
    """Place the first role at m0 and the remaining roles against the high edge."""

    first, *remaining = roles
    if first.nregs > num_m_regs:
        return None
    bases = {first.role: 0}
    cursor = num_m_regs
    for role in reversed(remaining):
        base = ((cursor - role.nregs) // role.nregs) * role.nregs
        if base < first.nregs:
            return None
        bases[role.role] = base
        cursor = base
    return bases


_LAYOUT_PLACEMENTS = (
    ("low", "lowest legal M-register placement", _low_bases),
    ("high", "highest legal M-register placement", _high_bases),
    (
        "boundary",
        "first role at m0 and remaining roles at the M-register-file edge",
        _boundary_bases,
    ),
)


def choose_m_group_base(
    num_m_regs: int,
    element_bits: int,
    uds: int,
    preferred: int,
) -> int:
    """Choose an aligned base, keeping the preferred base when it is legal.

    The suite uses bases such as ``m16``.  Those bases do not exist when an
    implementation exposes fewer M registers, so a caller that needs one group
    falls back to the last aligned group.
    """

    nregs = max(1, element_bits // uds)
    candidates = [
        reg for reg in range(num_m_regs) if reg % nregs == 0 and reg + nregs <= num_m_regs
    ]
    if not candidates:
        raise ValueError(
            f"no legal M register group for element_bits={element_bits}, nregs={nregs}"
        )
    if preferred in candidates:
        return preferred
    return candidates[-1]


def m_register_layouts(
    num_m_regs: int,
    roles: Sequence[MRegisterRole],
) -> tuple[MRegisterLayout, ...]:
    """Resolve declared roles into the low, high, and edge legal layouts."""

    if num_m_regs <= 0:
        raise ValueError(f"invalid M-register file size: {num_m_regs}")
    declared = tuple(roles)
    if not declared:
        raise ValueError("M-register layouts need at least one declared role")

    prior: dict[str, MRegisterRole] = {}
    physical: list[MRegisterRole] = []
    for role in declared:
        if role.role in prior:
            raise ValueError(f"duplicate M-register role {role.role!r}")
        if role.reuse_of is None:
            physical.append(role)
        else:
            target = prior.get(role.reuse_of)
            if target is None:
                raise ValueError(
                    f"M-register role {role.role!r} reuses unknown or later role "
                    f"{role.reuse_of!r}"
                )
            if target.nregs != role.nregs:
                raise ValueError(
                    f"M-register role {role.role!r} cannot reuse {role.reuse_of!r}: "
                    "their spans differ"
                )
        prior[role.role] = role

    layouts: list[MRegisterLayout] = []
    seen: set[tuple[tuple[str, int], ...]] = set()
    for name, description, placement in _LAYOUT_PLACEMENTS:
        bases = placement(physical, num_m_regs)
        if bases is None:
            continue
        resolved: list[MRegisterGroup] = []
        for role in declared:
            if role.reuse_of is None:
                base = bases[role.role]
            else:
                base = next(group.base for group in resolved if group.role == role.reuse_of)
            if base + role.nregs > num_m_regs:
                raise AssertionError("resolved M-register layout exceeds its file")
            resolved.append(MRegisterGroup(role.role, base, role.nregs, role.reuse_of))
        key = tuple((group.role, group.base) for group in resolved)
        if key in seen:
            continue
        seen.add(key)
        layouts.append(MRegisterLayout(name, description, tuple(resolved)))
    return tuple(layouts)


def accumulator_operands(num_acc_regs: int) -> tuple[AccumulatorOperand, ...]:
    """Return every legal single accumulator operand for a configuration."""

    if num_acc_regs <= 0:
        raise ValueError(f"invalid accumulator-file size: {num_acc_regs}")
    return tuple(
        AccumulatorOperand(
            name=f"acc{index}",
            description=f"single accumulator acc{index}",
            base=index,
        )
        for index in range(num_acc_regs)
    )


def representative_accumulator_operands(
    num_acc_regs: int,
) -> tuple[AccumulatorOperand, ...]:
    """Return low, encoding-boundary, and high ordinary ACC operands.

    An ordinary semantic case does not need to repeat once per accumulator:
    the ``multi_acc_independent`` template separately writes, accumulates, and
    reads every legal accumulator.  These operands keep ordinary cases
    reviewable while still covering the low end, both sides of the middle
    register-encoding boundary, and the high end of the file.
    """

    all_operands = accumulator_operands(num_acc_regs)
    indices = (0, (num_acc_regs - 1) // 2, num_acc_regs // 2, num_acc_regs - 1)
    return tuple(all_operands[index] for index in dict.fromkeys(indices))


def packed_span_cases(num_acc_regs: int, span: int) -> tuple[AccumulatorOperand, ...]:
    """Return the low and high legal packed spans, plus the crossing one.

    A packed (storage-only) accumulator datatype makes one M register hold
    ``UDS / element_bits`` squares, so one accumulator operand then denotes the
    consecutive span ``acc .. acc + span - 1``.  The crossing case is the one
    the ISA has to reject, and it is what the span-exception test looks for.
    """

    if num_acc_regs <= 0 or span <= 0:
        raise ValueError(
            f"invalid packed accumulator geometry: {num_acc_regs} registers, span {span}"
        )
    if span > num_acc_regs:
        return ()

    cases = [
        AccumulatorOperand(
            name="span_low",
            description="lowest legal packed accumulator span",
            base=0,
            span=span,
        )
    ]
    high_base = num_acc_regs - span
    if high_base:
        cases.append(
            AccumulatorOperand(
                name="span_high",
                description="highest legal packed accumulator span",
                base=high_base,
                span=span,
            )
        )
    if span > 1:
        cases.append(
            AccumulatorOperand(
                name="span_crossing",
                description="packed span crossing the accumulator-file end",
                base=high_base + 1,
                span=span,
                legal=False,
            )
        )
    return tuple(cases)


def paired_layouts(
    num_m_regs: int,
    num_acc_regs: int,
    roles: Sequence[MRegisterRole],
    *,
    exhaustive_accumulators: bool = False,
) -> tuple[RegisterLayout, ...]:
    """Cycle ACC operands against every reviewable M layout.

    The two lists are cycled to their larger length instead of producing a
    Cartesian product, so ordinary semantics stay reviewable while M layouts
    are still exhausted.  The ACC list is the low/boundary/high representative
    subset by default; ``exhaustive_accumulators`` cycles every legal
    accumulator instead, which is what a utility that only ever touches one
    accumulator per case needs in order to pin each of them down.
    """

    layouts = m_register_layouts(num_m_regs, roles)
    if not layouts:
        return ()
    acc_operands = (
        accumulator_operands(num_acc_regs)
        if exhaustive_accumulators
        else representative_accumulator_operands(num_acc_regs)
    )
    count = max(len(layouts), len(acc_operands))
    return tuple(
        RegisterLayout(
            m=layouts[index % len(layouts)],
            acc=acc_operands[index % len(acc_operands)],
        )
        for index in range(count)
    )


__all__ = [
    "AccumulatorOperand",
    "MRegisterGroup",
    "MRegisterLayout",
    "MRegisterRole",
    "RegisterLayout",
    "accumulator_operands",
    "choose_m_group_base",
    "m_register_layouts",
    "packed_span_cases",
    "paired_layouts",
    "representative_accumulator_operands",
]


def choose_distinct_m_group_bases(
    num_m_regs: int, element_bits: int, machine: MachineConfig, preferred: Sequence[int]
) -> tuple[int, ...]:
    """Choose aligned, non-overlapping M-register groups.

    Preferred bases are considered in operand order: a legal preferred base is
    kept when it does not overlap an earlier operand, otherwise the first
    remaining aligned group is used.  Running out of groups is an error, because
    the caller has already decided this case must fit.
    """

    nregs = machine.nregs(element_bits)
    candidates = [
        reg for reg in range(0, num_m_regs, nregs) if reg + nregs <= num_m_regs
    ]
    if len(candidates) < len(preferred):
        raise ValueError(
            f"need {len(preferred)} distinct groups of {nregs} M registers "
            f"for element_bits={element_bits}, uds={machine.uds}; "
            f"configured file has {num_m_regs}"
        )
    selected: list[int] = []
    for preferred_base in preferred:
        available = [base for base in candidates if base not in selected]
        base = preferred_base if preferred_base in available else available[0]
        selected.append(base)
    return tuple(selected)
