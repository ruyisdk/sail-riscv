#!/usr/bin/env python3
#
# Copyright (c) Qualcomm Technologies, Inc. and/or its subsidiaries.
# SPDX-License-Identifier: BSD-3-Clause-Clear
#
"""Generator for ``agettyp``: read the datatype descriptor of an accumulator."""

from __future__ import annotations

from mmul_gen.instruction import (
    ACC_TYPE_OPERAND,
    SCALAR_DESTINATION_OPERAND,
    Instruction,
)
from mmul_gen.templates.type_register_acc_roundtrip import (
    AccTypeRoundtrip,
)


class Agettyp(Instruction):
    """Read the datatype descriptor of an accumulator."""

    name = "agettyp"
    summary = "read the datatype descriptor of an accumulator"
    subject = "type-register roundtrip test cases."
    operands = (SCALAR_DESTINATION_OPERAND, ACC_TYPE_OPERAND,)
    templates = (AccTypeRoundtrip("agettyp reads a descriptor seeded by asettyp"),)


__all__ = ["Agettyp"]
