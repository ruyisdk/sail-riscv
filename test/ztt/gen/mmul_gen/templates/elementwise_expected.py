#!/usr/bin/env python3
#
# Copyright (c) Qualcomm Technologies, Inc. and/or its subsidiaries.
# SPDX-License-Identifier: BSD-3-Clause-Clear
#
"""Expected results of the elementwise integer recipes.

Every expectation is the result of the formula the integer template was handed --
the instruction's own ``evaluate`` -- computed from the operands the case emits
and re-encoded at the element width.  The formula is passed in rather than looked
up on the instruction, so the template carries what it checks; the shared oracle
``numeric_reference`` is not consulted on this path, and a test keeps the two in
step instead.
"""

from __future__ import annotations

from collections.abc import Callable

from mmul_gen.machine import dtype_is_signed_int
from mmul_gen.reference import IntegerDType
from mmul_gen.templates.elementwise_elements import (
    IntegerElements,
    integer_elements,
)
from mmul_gen.templates.elementwise_forms import ElementwiseForm


def _dtype(dtype_name: str, element_bits: int) -> IntegerDType:
    """The non-saturating decode/encode pair one elementwise case runs at."""

    return IntegerDType(
        bits=element_bits,
        signed=dtype_is_signed_int(dtype_name),
        saturating=False,
    )


def integer_expected(
    formula: Callable[[IntegerElements], int],
    form: ElementwiseForm,
    dtype_name: str,
    element_bits: int,
    values: dict[str, int],
) -> int:
    """The result of one case, computed by the formula the template holds.

    The formula states the *exact* result of the operation; re-encoding it at the
    element width is the recipe's job, so no instruction repeats it.  ``form``
    comes along because the operand roles do, and they are read from the
    instruction rather than from each formula.
    """

    dtype = _dtype(dtype_name, element_bits)
    elements = integer_elements(form, dtype, values)
    return dtype.convert_result(formula(elements))[0]


__all__ = ["integer_expected"]
