#!/usr/bin/env python3
#
# Copyright (c) Qualcomm Technologies, Inc. and/or its subsidiaries.
# SPDX-License-Identifier: BSD-3-Clause-Clear
#
"""Shared declaration of the backend ownership/ordering family.

One backend ownership or ordering instruction.
"""

from __future__ import annotations

from mmul_gen.instruction import Instruction


class BackendInstruction(Instruction, family_base=True):
    """Declarative definition of one backend ownership/ordering instruction."""

    acquires_backend = False

    subject = "backend-state semantic test cases."

__all__ = [
    "BackendInstruction",
]
