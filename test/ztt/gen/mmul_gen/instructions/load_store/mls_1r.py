#!/usr/bin/env python3
#
# Copyright (c) Qualcomm Technologies, Inc. and/or its subsidiaries.
# SPDX-License-Identifier: BSD-3-Clause-Clear
#
"""Generator for ``mls.1r``: raw load of one physical M register."""

from __future__ import annotations

from mmul_gen.instruction import (
    M_TRANSFER_OPERAND,
    SCALAR_SOURCE_OPERAND,
    Instruction,
)
from mmul_gen.templates.raw_transfer import (
    RAW_TRANSFER,
)


class Mls1r(Instruction):
    """M register written by the load."""

    name = "mls.1r"
    summary = "load one physical M register from memory"
    subject = "raw load/store test cases."
    operands = (M_TRANSFER_OPERAND, SCALAR_SOURCE_OPERAND)
    templates = (RAW_TRANSFER,)


__all__ = ["Mls1r"]
