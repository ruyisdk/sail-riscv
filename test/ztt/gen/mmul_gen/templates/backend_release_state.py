#!/usr/bin/env python3
#
# Copyright (c) Qualcomm Technologies, Inc. and/or its subsidiaries.
# SPDX-License-Identifier: BSD-3-Clause-Clear
#
"""Backend release: the state register must go back to idle."""

from __future__ import annotations

from typing import TYPE_CHECKING

from mmul_gen.machine import MachineConfig
from mmul_gen.templates.backend_state import (
    BACKEND_STATE_CSR,
    MASK_OWNERSHIP,
    STATE_IDLE,
    STATE_OWNED,
    STATUS_GRANTED,
    BackendCase,
)
from mmul_gen.templates.base import Case, CaseOutput

if TYPE_CHECKING:
    from mmul_gen.instruction import Instruction


class ReleaseState(BackendCase):
    """Releasing owned backend returns the state register to idle."""

    name = "acquire_release_state"

    def render(
        self,
        machine: MachineConfig,
        instruction: Instruction,
        case: Case,
        out: CaseOutput,
    ) -> None:
        out.text.extend(
            [
                f"    li      t0, {MASK_OWNERSHIP}",
                "    ame.acquire t1, t0",
                f"    EXPECT  t1, {STATUS_GRANTED}",
                f"    csrr    t2, {BACKEND_STATE_CSR:#x}",
                f"    EXPECT  t2, {STATE_OWNED}",
                "    ame.release",
                f"    csrr    t2, {BACKEND_STATE_CSR:#x}",
                f"    EXPECT  t2, {STATE_IDLE}",
            ]
        )


__all__ = ["ReleaseState"]


RELEASE_STATE = ReleaseState()
