#!/usr/bin/env python3
#
# Copyright (c) Qualcomm Technologies, Inc. and/or its subsidiaries.
# SPDX-License-Identifier: BSD-3-Clause-Clear
#
"""Backend acquire under contention: the request is refused and changes nothing.

Spec:    backend_management.adoc:160-162 (§5.3.1)
Quote:   "Initial state has zero-valued `M` and `Acc` registers, zero-valued `Md` and `Ad` descriptors, and
         reset-valued writable AME CSRs.  Failure changes neither backend binding, `ameown`, nor `MS`."
Checks:  a contended ame.acquire must report BUSY and leave ameown.OWNED zero.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from mmul_gen.machine import MachineConfig
from mmul_gen.templates.backend_state import (
    BACKEND_STATE_CSR,
    MASK_BUSY,
    STATE_IDLE,
    STATUS_BUSY,
    BackendCase,
)
from mmul_gen.templates.base import Case, CaseOutput

if TYPE_CHECKING:
    from mmul_gen.instruction import Instruction


class AcquireBusyState(BackendCase):
    """A contended request is refused and leaves the backend unowned."""

    name = "busy_state"

    def render(
        self,
        machine: MachineConfig,
        instruction: Instruction,
        case: Case,
        out: CaseOutput,
    ) -> None:
        out.text.extend(
            [
                f"    li      t0, {MASK_BUSY}",
                "    ame.acquire t1, t0",
                f"    EXPECT  t1, {STATUS_BUSY}",
                f"    csrr    t2, {BACKEND_STATE_CSR:#x}",
                f"    EXPECT  t2, {STATE_IDLE}",
            ]
        )


__all__ = ["AcquireBusyState"]


ACQUIRE_BUSY_STATE = AcquireBusyState()
