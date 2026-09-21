#!/usr/bin/env python3
#
# Copyright (c) Qualcomm Technologies, Inc. and/or its subsidiaries.
# SPDX-License-Identifier: BSD-3-Clause-Clear
#
"""Shared declaration of the four strided memory transfers."""

from __future__ import annotations

from mmul_gen.instruction import Instruction
from mmul_gen.machine import MachineConfig


class StridedMemoryInstruction(Instruction, family_base=True):
    """One strided transfer and the banner every one of them emits.

    The direction and the order are not declared here: they are the argument of
    each instruction's ``StridedTransfer`` entries.
    """

    def banner(self, machine: MachineConfig) -> tuple[str, ...]:
        return (
            self.title,
            f"UDS={machine.uds}: normal={machine.uds}, packed={machine.uds // 2}",
        )


__all__ = [
    "StridedMemoryInstruction",
]
