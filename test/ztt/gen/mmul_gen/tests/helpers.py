#!/usr/bin/env python3
#
# Copyright (c) Qualcomm Technologies, Inc. and/or its subsidiaries.
# SPDX-License-Identifier: BSD-3-Clause-Clear
#
"""Shared fixtures for the matrix-multiply generator tests."""

from __future__ import annotations

from pathlib import Path

from functools import partial
from typing import TypeVar

from mmul_gen.macros import parse_dtypes
from mmul_gen.machine import MachineConfig
from mmul_gen.templates.elementwise_templates import (
    ElementwiseFloatNominal,
    ElementwiseIntegerValueRules,
    ElementwiseTemplate,
)

GEN_ROOT = Path(__file__).resolve().parents[2]
ZTT_ROOT = GEN_ROOT.parent
MACRO_FILE = ZTT_ROOT / "src" / "ame_macros.inc"

def dtypes():
    return parse_dtypes(MACRO_FILE)

TemplateT = TypeVar("TemplateT", bound=ElementwiseTemplate)

def template_binding(instruction, template_class: type[TemplateT]) -> TemplateT | None:
    """The instance of ``template_class`` among ``instruction``'s templates.

    Every elementwise instruction writes the templates it runs with their
    inputs, so a test reads an input back off the template that checks it rather
    than off a second declaration of the same fact.  A template the instruction
    does not run yields ``None``.
    """

    for template in instruction.templates:
        if isinstance(template, template_class):
            return template
    return None

def required_template(instruction, template_class: type[TemplateT]) -> TemplateT:
    """The instance of ``template_class``, which the instruction must run."""

    template = template_binding(instruction, template_class)
    if template is None:
        raise AssertionError(f"{instruction.name} runs no {template_class.__name__}")
    return template

def integer_formula(instruction):
    """The formula the integer template holds, bound to ``instruction``.

    Read off the template rather than off the class, because that is the copy the
    recipe calls: the instruction hands its ``evaluate`` over when it builds the
    list, so a test that wants to know what the cases are computed with has to ask
    the template.
    """

    template = required_template(instruction, ElementwiseIntegerValueRules)
    return partial(template.evaluate, instruction)


def machine(
    *,
    n: int = 8,
    uds: int = 8,
    num_m_regs: int = 32,
    num_acc_regs: int = 4,
) -> MachineConfig:
    return MachineConfig(
        dtypes=dtypes(),
        n=n,
        uds=uds,
        num_m_regs=num_m_regs,
        num_acc_regs=num_acc_regs,
    )

__all__ = ["GEN_ROOT", "MACRO_FILE", "ZTT_ROOT", "dtypes", "machine"]
