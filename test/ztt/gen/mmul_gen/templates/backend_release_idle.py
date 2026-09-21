#!/usr/bin/env python3
#
# Copyright (c) Qualcomm Technologies, Inc. and/or its subsidiaries.
# SPDX-License-Identifier: BSD-3-Clause-Clear
#
"""Backend release while unowned: the release must be a no-op."""

from __future__ import annotations

DOC_ZH = """\
未持有时释放后端：释放必须是空操作。
"""

from typing import TYPE_CHECKING

from mmul_gen.machine import MachineConfig
from mmul_gen.templates.backend_state import (
    BACKEND_STATE_CSR,
    STATE_IDLE,
    BackendCase,
)
from mmul_gen.templates.base import Case, CaseOutput

if TYPE_CHECKING:
    from mmul_gen.instruction import Instruction


class ReleaseIdleState(BackendCase):
    """Releasing an unowned backend is a no-op that leaves it idle."""

    summary_zh = "释放未持有的后端是空操作，后端保持 idle。"
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
                "    ame.release",
                f"    csrr    t2, {BACKEND_STATE_CSR:#x}",
                f"    EXPECT  t2, {STATE_IDLE}",
            ]
        )


__all__ = ["ReleaseIdleState"]


RELEASE_IDLE_STATE = ReleaseIdleState()
