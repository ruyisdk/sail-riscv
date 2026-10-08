#!/usr/bin/env python3
#
# Copyright (c) Qualcomm Technologies, Inc. and/or its subsidiaries.
# SPDX-License-Identifier: BSD-3-Clause-Clear
#
"""Generator for ``ame.acquire``: request ownership of the AME backend."""

from __future__ import annotations

from mmul_gen.instruction import (
    SCALAR_DESTINATION_OPERAND,
    SCALAR_SOURCE_OPERAND,
)
from mmul_gen.instructions.backend.base import BackendInstruction
from mmul_gen.templates.backend_acquire_busy import (
    ACQUIRE_BUSY_STATE,
)
from mmul_gen.templates.backend_acquire_state import (
    ACQUIRE_RELEASE_STATE,
)


class AmeAcquire(BackendInstruction):
    """Take AME ownership and report the outcome in a status register."""

    name = "ame.acquire"
    summary = "take ownership of the AME backend"
    operands = (SCALAR_DESTINATION_OPERAND, SCALAR_SOURCE_OPERAND)
    templates = (ACQUIRE_RELEASE_STATE, ACQUIRE_BUSY_STATE)


__all__ = ["AmeAcquire"]
