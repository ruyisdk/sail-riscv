#!/usr/bin/env python3
#
# Copyright (c) Qualcomm Technologies, Inc. and/or its subsidiaries.
# SPDX-License-Identifier: BSD-3-Clause-Clear
#
"""The family-independent instruction contract every Ztt generator instantiates.

An instruction declares *what it is* (name, summary, operands, title) and *which
templates it covers*.  It contains no assembly at all: the templates own the
rendering.  :meth:`Instruction.gen` is the only executable piece, and it is a
driver, not a template.

The operand vocabulary defined here names the positions an instruction decorates.
An instruction class declares nothing else a template reads by name: whatever a
template needs -- a stimulus, a product shape, an operation -- is passed to that
template when the instruction constructs it, so the class body reads as identity
plus formulas and the template call sites carry the parameters.  A family may
still add a subclass of :class:`Instruction` for what all of its instructions
share, but only for framework hooks such as ``banner``/``data_footer``; see
``instructions/mmul/base.py`` and ``instructions/strided_memory/base.py``.
"""

from __future__ import annotations

from collections.abc import Iterator, Sequence
from dataclasses import dataclass, replace
from mmul_gen.asm import asm_header, instruction_file_name
from mmul_gen.machine import DType, DTypeDomain, MachineConfig
from mmul_gen.templates.base import Case, CaseOutput, Template


@dataclass(frozen=True)
class Operand:
    """One architectural operand of an instruction."""

    role: str
    register_class: str
    description: str


@dataclass(frozen=True)
class GeneratedSource:
    """One rendered assembly test source."""

    name: str
    text: str


ACCUMULATOR_OPERAND = Operand(
    "acc", "acc", "accumulator register, read and written back"
)
FIRST_SOURCE_OPERAND = Operand("ms1", "m", "first source square")
SECOND_SOURCE_OPERAND = Operand("ms2", "m", "second source square")
DESTINATION_OPERAND = Operand("md", "m", "destination square")

#: Operand order of every ``*.2d`` matrix-multiply instruction.
PRODUCT_OPERANDS = (
    ACCUMULATOR_OPERAND,
    FIRST_SOURCE_OPERAND,
    SECOND_SOURCE_OPERAND,
)

M_TYPE_OPERAND = Operand("m", "m", "M register whose datatype descriptor is accessed")
ACC_TYPE_OPERAND = Operand(
    "acc", "acc", "accumulator register whose datatype descriptor is accessed"
)
#: Position of one element inside the raw M-register bit view.
SCALAR_POSITION_OPERAND = Operand("tp", "t", "element position inside the register")
#: M register moved by a raw physical-register transfer.
M_TRANSFER_OPERAND = Operand("m", "m", "M register the instruction transfers")
SCALAR_SOURCE_OPERAND = Operand("ts", "t", "integer register read by the instruction")
SCALAR_DESTINATION_OPERAND = Operand(
    "td", "t", "integer register written by the instruction"
)

#: Storage slot the indexed packed-slot conversion selects.
PACK_SLOT_OPERAND = Operand("ts", "t", "storage slot read or written")
#: Source square of an indexed packed-slot conversion.
PACK_SOURCE_OPERAND = Operand("ms", "m", "source square")


class _TestProgram:
    """Accumulates the ``.text`` and ``.data`` sections of one test file."""

    def __init__(self, instruction: "Instruction", machine: MachineConfig) -> None:
        self._instruction = instruction
        self._machine = machine
        self._text: list[str] = []
        self._data: list[str] = []
        self._case_count = 0

    @property
    def is_empty(self) -> bool:
        """Whether no template contributed a case on this configuration."""

        return self._case_count == 0

    def add_case(self, template: Template, case: Case) -> None:
        case = replace(case, number=self._case_count)
        self._case_count += 1
        if case.description is not None:
            self._text.append(f"    # input: {case.description}")
        if case.layout is not None:
            self._text.extend(case.layout.comment_lines())
        output = CaseOutput()
        template.render(self._machine, self._instruction, case, output)
        self._text.extend(output.text)
        self._data.extend(output.data)

    def build(self) -> GeneratedSource:
        lines = asm_header(
            self._instruction.banner(self._machine),
            acquire_backend=self._instruction.acquires_backend,
        )
        lines.extend(self._text)
        lines.extend(["    RVMODEL_HALT_PASS", ""])
        footer = self._instruction.data_footer(self._machine)
        if self._data or footer or self._instruction.always_emits_data:
            lines.append(".data")
            lines.extend(self._data)
            lines.extend(footer)
        return GeneratedSource(
            name=self._instruction.file_name,
            text="\n".join(lines),
        )


class Instruction:
    """Declarative definition of one instruction."""

    #: Architectural mnemonic; also the generated file stem.
    name: str = ""
    #: One-line description of what the instruction does.
    summary: str = ""
    #: Chinese one-line description.  The design document reads this field and
    #: nothing else, so the delivered prose has exactly one source and cannot
    #: drift from a translation kept beside it.
    summary_zh: str = ""
    #: Chinese rendering of the manual's Synopsis and Description, for the
    #: instructions whose design-document section carries a manual-sourced
    #: narrative block.  Empty for an instruction that has no such block yet.
    manual_zh: str = ""
    #: Ordered architectural operands.
    operands: tuple[Operand, ...] = ()
    #: Ordered templates this instruction is generated from.
    templates: tuple[Template, ...] = ()
    #: What the source banner calls this instruction: the banner reads
    #: ``"<mnemonic> <subject>"``.  Families declare it once for all members.
    subject: str = ""

    @property
    def title(self) -> str:
        return f"{self.name} {self.subject}"

    @property
    def input_case_names(self) -> tuple[str, ...]:
        """The names of the input cases this instruction runs.

        Answered by the templates this instruction constructed, so the coverage
        is stated once -- in :attr:`templates` -- and no second declaration can
        drift from what the cases sweep.  A family that derives the names from a
        template it built narrows this view further.
        """

        names: list[str] = []
        for template in self.templates:
            names.extend(name for name in template.input_cases if name not in names)
        return tuple(names)

    def banner(self, machine: MachineConfig) -> Sequence[str]:
        """Description lines the source banner prints, one list entry per line.

        Most instructions describe themselves with :attr:`title` alone; a family
        whose banner carries a configuration line (``UDS=...``) appends it here.
        """

        return [self.title]

    #: Whether the generated header takes AME ownership before the test body.
    #: The backend-state tests declare ``False``: taking ownership is what they
    #: are testing.
    acquires_backend: bool = True
    #: Some families always carry a ``.data`` section, even in a configuration
    #: where every datatype is skipped, because the section itself is part of
    #: the file format they were defined in.
    always_emits_data: bool = False

    def __init_subclass__(cls, *, family_base: bool = False, **kwargs: object) -> None:
        # ``family_base`` is a class keyword, not an inherited attribute, so
        # declaring a family base exempts only that class: every concrete
        # instruction still has to carry the full declaration.
        super().__init_subclass__(**kwargs)
        if family_base:
            return
        for attribute in ("name", "summary", "summary_zh", "templates", "subject"):
            if not getattr(cls, attribute, None):
                raise TypeError(f"{cls.__name__} must declare {attribute!r}")
        # Instructions without operands declare an empty tuple explicitly, so a
        # missing declaration is still caught.
        if not cls.operands and "operands" not in cls.__dict__:
            raise TypeError(f"{cls.__name__} must declare 'operands'")

    @property
    def file_name(self) -> str:
        return instruction_file_name(self.name)

    @property
    def template_names(self) -> tuple[str, ...]:
        return tuple(template.name for template in self.templates)

    @property
    def datatype_domains(self) -> tuple[DTypeDomain, ...]:
        """The datatype domains this instruction covers, in template order.

        Derived from the declared templates rather than declared again, so the
        instruction's stated datatype coverage cannot drift from what it
        actually generates.
        """

        return tuple(
            dict.fromkeys(
                template.dtypes
                for template in self.templates
                if template.dtypes is not None
            )
        )

    def supported_dtypes(self, machine: MachineConfig) -> tuple[DType, ...]:
        """Every datatype this instruction covers for one configuration.

        Derived from the declared templates, so the instruction's datatype
        support cannot drift from what it actually generates.
        """

        supported: dict[str, DType] = {}
        for template in self.templates:
            for dtype in template.iter_dtypes(machine):
                if dtype is None or not template.fits(machine, self, dtype):
                    continue
                supported.setdefault(dtype.name, dtype)
        return tuple(supported.values())

    def template_set(self, machine: MachineConfig) -> tuple[Template, ...]:
        """The templates that actually render here, in render order.

        :attr:`templates` is what the family lets this instruction run; this is
        what produced at least one case on this configuration.  An inventory
        built from it describes the source that is written rather than the
        family's whole template table.
        """

        return tuple(dict.fromkeys(template for template, _ in self.cases(machine)))

    def data_footer(self, machine: MachineConfig) -> list[str]:
        """Lines closing the ``.data`` section of this instruction's sources.

        No template data and no footer means the source carries no ``.data``
        section at all, which is what instructions that keep no expected image
        in memory need.
        """

        return []

    def cases(self, machine: MachineConfig) -> Iterator[tuple["Template", Case]]:
        """Every case this instruction contributes on one configuration.

        The single definition of the coverage pipeline: template -> datatype
        domain -> :meth:`Template.fits` -> :meth:`Template.build`.  Consumers
        that need the cases themselves (a review tool, a test) use this instead
        of re-implementing the loop.
        """

        for template in self.templates:
            for dtype in template.iter_dtypes(machine):
                if not template.fits(machine, self, dtype):
                    continue
                for case in template.build(machine, self, dtype):
                    yield template, case

    def gen(self, machine: MachineConfig) -> GeneratedSource | None:
        """Render this instruction's test source, or ``None``.

        ``None`` means no template could produce a case in this configuration, and
        no file is emitted then -- a source with only a header would be a
        different artifact, not an empty one.
        """

        program = _TestProgram(self, machine)
        for template, case in self.cases(machine):
            program.add_case(template, case)
        if program.is_empty:
            return None
        return program.build()


__all__ = [
    "ACCUMULATOR_OPERAND",
    "ACC_TYPE_OPERAND",
    "DESTINATION_OPERAND",
    "FIRST_SOURCE_OPERAND",
    "GeneratedSource",
    "Instruction",
    "M_TRANSFER_OPERAND",
    "M_TYPE_OPERAND",
    "Operand",
    "PACK_SLOT_OPERAND",
    "PACK_SOURCE_OPERAND",
    "PRODUCT_OPERANDS",
    "SCALAR_DESTINATION_OPERAND",
    "SCALAR_POSITION_OPERAND",
    "SCALAR_SOURCE_OPERAND",
    "SECOND_SOURCE_OPERAND",
]
