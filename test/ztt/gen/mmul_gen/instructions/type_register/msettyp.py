#!/usr/bin/env python3
#
# Copyright (c) Qualcomm Technologies, Inc. and/or its subsidiaries.
# SPDX-License-Identifier: BSD-3-Clause-Clear
#
"""Generator for ``msettyp``: write the datatype descriptor of an M register."""

from __future__ import annotations

from mmul_gen.instruction import (
    M_TYPE_OPERAND,
    SCALAR_SOURCE_OPERAND,
    Instruction,
)
from mmul_gen.templates.type_register_m_roundtrip import (
    MTypeRoundtrip,
)
from mmul_gen.templates.type_register_m_unsupported_probe import (
    M_TYPE_UNSUPPORTED_PROBE,
)


class Msettyp(Instruction):
    """Write the datatype descriptor of an M register."""

    name = "msettyp"
    summary = "write the datatype descriptor of an M register"
    subject = "type-register roundtrip test cases."
    operands = (M_TYPE_OPERAND, SCALAR_SOURCE_OPERAND,)
    templates = (
        MTypeRoundtrip("msettyp writes the descriptor and mgettyp reads it back"),
        M_TYPE_UNSUPPORTED_PROBE,
    )


__all__ = ["Msettyp"]
