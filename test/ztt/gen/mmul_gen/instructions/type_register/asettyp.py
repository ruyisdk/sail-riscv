#!/usr/bin/env python3
#
# Copyright (c) Qualcomm Technologies, Inc. and/or its subsidiaries.
# SPDX-License-Identifier: BSD-3-Clause-Clear
#
"""Generator for ``asettyp``: write the datatype descriptor of an accumulator."""

from __future__ import annotations

from mmul_gen.instruction import (
    ACC_TYPE_OPERAND,
    SCALAR_SOURCE_OPERAND,
    Instruction,
)
from mmul_gen.templates.type_register_acc_roundtrip import (
    AccTypeRoundtrip,
)
from mmul_gen.templates.type_register_acc_unsupported_probe import (
    ACC_TYPE_UNSUPPORTED_PROBE,
)


class Asettyp(Instruction):
    """Write the datatype descriptor of an accumulator."""

    name = "asettyp"
    summary = "write the datatype descriptor of an accumulator"
    subject = "type-register roundtrip test cases."
    operands = (ACC_TYPE_OPERAND, SCALAR_SOURCE_OPERAND,)
    templates = (
        AccTypeRoundtrip("asettyp writes the descriptor and agettyp reads it back"),
        ACC_TYPE_UNSUPPORTED_PROBE,
    )


__all__ = ["Asettyp"]
