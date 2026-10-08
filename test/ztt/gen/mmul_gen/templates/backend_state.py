#!/usr/bin/env python3
#
# Copyright (c) Qualcomm Technologies, Inc. and/or its subsidiaries.
# SPDX-License-Identifier: BSD-3-Clause-Clear
#
"""Shared shape and architectural constants for the backend-state templates.

The ownership handshake is driven by a request mask and observed through a state
CSR, and all four scenarios use the same two, so they live here instead of in
each scenario file.

Ownership is a state-machine property rather than a data-layout one: these
templates have no datatype dimension, no register layout, and no data section.
Each builds exactly one case whose expected values are architecture constants.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import TYPE_CHECKING

from mmul_gen.case_description import description
from mmul_gen.machine import MachineConfig
from mmul_gen.templates.base import Case, Template

if TYPE_CHECKING:
    from mmul_gen.instruction import Instruction


#: State CSR the acquire/release handshake is observed through.
BACKEND_STATE_CSR = 0xCC3
#: Request mask asking for ownership without waiting.
MASK_OWNERSHIP = 0
#: Request mask asking for ownership and reporting contention.
MASK_BUSY = 2
#: Ownership granted.
STATUS_GRANTED = 1
#: Ownership refused because another agent already holds it.
STATUS_BUSY = 8
#: Backend state: nobody owns it.
STATE_IDLE = 0
#: Backend state: it is owned.
STATE_OWNED = 1


class BackendCase(Template, family_base=True):
    """One fixed backend-state scenario, identical on every configuration."""

    dtypes = None

    def build(
        self, machine: MachineConfig, instruction: Instruction, dtype: None = None
    ) -> Sequence[Case]:
        return [Case(number=1, dtype=None, description=description(self.name))]


__all__ = [
    "BACKEND_STATE_CSR",
    "MASK_BUSY",
    "MASK_OWNERSHIP",
    "STATE_IDLE",
    "STATE_OWNED",
    "STATUS_BUSY",
    "STATUS_GRANTED",
    "BackendCase",
]
