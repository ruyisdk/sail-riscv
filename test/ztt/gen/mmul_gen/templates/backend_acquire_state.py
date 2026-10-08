#!/usr/bin/env python3
#
# Copyright (c) Qualcomm Technologies, Inc. and/or its subsidiaries.
# SPDX-License-Identifier: BSD-3-Clause-Clear
#
"""Backend acquire without contention: ownership is granted and observable."""

from __future__ import annotations

from typing import TYPE_CHECKING

from mmul_gen.machine import MachineConfig
from mmul_gen.templates.backend_state import (
    BACKEND_STATE_CSR,
    MASK_OWNERSHIP,
    STATE_OWNED,
    STATUS_GRANTED,
    BackendCase,
)
from mmul_gen.templates.base import Case, CaseOutput

if TYPE_CHECKING:
    from mmul_gen.instruction import Instruction


class AcquireReleaseState(BackendCase):
    """Ownership taken without contention is reported and observable."""

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
            ]
        )


__all__ = ["AcquireReleaseState"]


ACQUIRE_RELEASE_STATE = AcquireReleaseState()
