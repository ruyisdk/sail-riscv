#!/usr/bin/env python3
#
# Copyright (c) Qualcomm Technologies, Inc. and/or its subsidiaries.
# SPDX-License-Identifier: BSD-3-Clause-Clear
#
"""Shared declaration of the indexed packed-slot conversion family.

One indexed packed-slot conversion and the banner it emits.
"""

from __future__ import annotations

from collections.abc import Sequence

from mmul_gen.instruction import Instruction
from mmul_gen.machine import MachineConfig


class PackInstruction(Instruction, family_base=True):
    """Declarative definition of one indexed packed-slot conversion."""

    subject = "indexed packed-slot semantic test cases."

    def banner(self, machine: MachineConfig) -> Sequence[str]:
        return [
            self.title,
            f"UDS={machine.uds}: storage={machine.uds // 2}, compute={machine.uds}",
        ]

__all__ = [
    "PackInstruction",
]
