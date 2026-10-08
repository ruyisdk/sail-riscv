#!/usr/bin/env python3
#
# Copyright (c) Qualcomm Technologies, Inc. and/or its subsidiaries.
# SPDX-License-Identifier: BSD-3-Clause-Clear
#
"""Generator for ``ame.release``: give ownership of the AME backend back."""

from __future__ import annotations

from mmul_gen.instructions.backend.base import BackendInstruction
from mmul_gen.templates.backend_release_idle import (
    RELEASE_IDLE_STATE,
)
from mmul_gen.templates.backend_release_state import (
    RELEASE_STATE,
)


class AmeRelease(BackendInstruction):
    """Release AME ownership and report a consistent idle state."""

    name = "ame.release"
    summary = "release ownership of the AME backend"
    # ``ame.release`` takes no operands; the empty tuple is the declaration.
    operands = ()
    templates = (RELEASE_STATE, RELEASE_IDLE_STATE)


__all__ = ["AmeRelease"]
