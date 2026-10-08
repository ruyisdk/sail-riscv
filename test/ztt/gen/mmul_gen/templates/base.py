#!/usr/bin/env python3
#
# Copyright (c) Qualcomm Technologies, Inc. and/or its subsidiaries.
# SPDX-License-Identifier: BSD-3-Clause-Clear
#
"""Case construction and the template contract.

Every template is a :class:`Template` subclass elsewhere in this package.  This
module holds the contract they share plus the machinery more than one template
needs: the case model, the payload type check, the operand-role declaration, the
M/ACC layout pairing, and the "both spans must fit" resource predicate.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, ClassVar

from mmul_gen.machine import DType, DTypeDomain, MachineConfig
from mmul_gen.registers import MRegisterRole, RegisterLayout, paired_layouts
if TYPE_CHECKING:
    from mmul_gen.instruction import Instruction


@dataclass(frozen=True)
class Case:
    """One fully decided test case, ready to render.

    ``number`` is assigned by the program builder and is the only field that
    changes after construction; it drives the generated label names.
    """

    number: int
    dtype: DType | None
    layout: RegisterLayout | None = None
    payload: object = None
    description: str | None = None


#: Sentinel for "this template has not declared a datatype domain".  A
#: dtype-free template declares ``None`` instead, so the two cases stay
#: distinguishable and inheriting a domain keeps working.
_UNDECLARED = object()


@dataclass
class CaseOutput:
    """The ``.text`` and ``.data`` lines contributed by one case."""

    text: list[str] = field(default_factory=list)
    data: list[str] = field(default_factory=list)


def domain_index(machine: MachineConfig, dtype: DType, domain: DTypeDomain) -> int:
    """The position of one datatype inside its own template's domain.

    Several families restart their ``# case N`` numbering for every datatype
    group, and they count *every* datatype of the group, including the ones an
    instruction then skips.  The position in the domain is therefore the stable
    number; the driver's file-wide case counter is not.
    """

    return domain(machine).index(dtype)


class Template(ABC):
    """One test template: a datatype domain, a case builder, and a renderer.

    A template is the unit of coverage.  Instructions reuse templates by
    holding the same instances, and a template that only needs to vary its
    case builder, its renderer, or its resource predicate is specialised by
    subclassing -- nothing else in the surrounding templates changes.
    """

    #: Label for this template in generated comments, tests, and ``--list``.
    name: ClassVar[str] = ""
    #: The datatype domain this template iterates for every configuration, or
    #: ``None`` for a template with no datatype dimension at all (backend state
    #: and ordering tests).  Such a template builds once per configuration with
    #: a ``None`` dtype, and has to say so explicitly.
    dtypes: ClassVar[DTypeDomain | None] = _UNDECLARED  # type: ignore[assignment]
    #: Input case labels this template covers, in the order it covers them.  The
    #: instruction reports these names in :attr:`Instruction.input_case_names`
    #: and prints them in its file header, so a coverage claim is stated where
    #: the cases are built -- the instruction's ``templates`` -- and nowhere else.
    input_cases: tuple[str, ...] = ()

    @property
    def summary(self) -> str:
        """One-line description, read from the class docstring.

        The docstring is the single source: ``--list``, the generated banner,
        and the inventory all read it from here, so a template cannot drift
        from its own documentation.
        """

        return type(self).__doc__.strip()

    def __init_subclass__(cls, *, family_base: bool = False, **kwargs: object) -> None:
        """Reject an incompletely declared template at class-definition time.

        A family base class is exempt: it exists to be specialised and carries
        neither a name of its own nor a datatype domain.
        """

        super().__init_subclass__(**kwargs)
        if family_base:
            return
        if not (cls.__doc__ or "").strip():
            raise TypeError(f"{cls.__name__} must document what it tests")
        if not cls.name:
            raise TypeError(f"{cls.__name__} must declare 'name'")
        if cls.dtypes is _UNDECLARED:
            raise TypeError(f"{cls.__name__} must declare 'dtypes' (None if dtype-free)")

    def iter_dtypes(self, machine: MachineConfig) -> tuple[DType | None, ...]:
        """The datatypes this template runs for on one configuration.

        A dtype-free template yields a single ``None`` so the driver keeps one
        code path for every template.
        """

        return (None,) if self.dtypes is None else self.dtypes(machine)

    def fits(
        self,
        machine: MachineConfig,
        instruction: "Instruction",
        dtype: DType | None = None,
    ) -> bool:
        """Whether this template covers one datatype of one instruction.

        A dtype-free template gets ``None``.  The instruction is part of the
        question because some operations narrow their datatype support -- an
        arithmetic right shift is defined on signed descriptors only -- and the
        same emission shape serves the whole group.
        """

        return True

    @abstractmethod
    def build(
        self, machine: MachineConfig, instruction: "Instruction", dtype: DType | None
    ) -> Sequence[Case]:
        """Decide operand values, expected values, and register layouts."""

    @abstractmethod
    def render(
        self,
        machine: MachineConfig,
        instruction: "Instruction",
        case: Case,
        out: CaseOutput,
    ) -> None:
        """Emit assembly and data for one case, using only its payload."""


def case_payload[T](expected_type: type[T], case: Case) -> T:
    """Fail fast when a renderer is handed a case it does not understand.

    The payload type is returned, not just checked, so a renderer reads its own
    payload fields without narrowing again.
    """

    if not isinstance(case.payload, expected_type):
        raise TypeError(
            f"case {case.number}: expected {expected_type.__name__}, "
            f"got {type(case.payload).__name__}"
        )
    return case.payload


def flatten(values: Sequence[int]) -> tuple[int, ...]:
    return tuple(int(value) for value in values)


def product_roles(
    machine: MachineConfig,
    element_bits: int,
    *,
    source_bits: int | None = None,
    destination_bits: int | None = None,
) -> tuple[MRegisterRole, ...]:
    """Declare source and post-product destination M-register roles.

    ``md`` deliberately aliases ``ms1`` when their formation spans agree: the
    product has consumed ``ms1`` before ``mmov.m.a`` writes the result, so it is
    a real temporal alias rather than an accidental overlap.
    """

    source_nregs = machine.nregs(source_bits or element_bits)
    destination_nregs = machine.nregs(destination_bits or element_bits)
    return (
        MRegisterRole("ms1", source_nregs),
        MRegisterRole("ms2", source_nregs),
        MRegisterRole(
            "md",
            destination_nregs,
            reuse_of="ms1" if source_nregs == destination_nregs else None,
        ),
    )


def paired_cases(
    machine: MachineConfig,
    dtype: DType,
    case_payload: object,
    *,
    source_bits: int | None = None,
    destination_bits: int | None = None,
    description: str | None = None,
) -> list[Case]:
    """One case per reviewable M/ACC layout pair, all sharing a payload."""

    roles = product_roles(
        machine, dtype.bits, source_bits=source_bits, destination_bits=destination_bits
    )
    return [
        Case(
            number=0,
            dtype=dtype,
            layout=layout,
            payload=case_payload,
            description=description,
        )
        for layout in paired_layouts(machine.num_m_regs, machine.num_acc_regs, roles)
    ]


def register(role: str, layout: RegisterLayout) -> int:
    """Resolved M-register number for one role in one case layout."""

    return layout.m.base(role)


def two_register_groups_fit(machine: MachineConfig, dtype: DType) -> bool:
    """Both source and destination spans must fit the M-register file at once."""

    return 2 * machine.nregs(dtype.bits) <= machine.num_m_regs
