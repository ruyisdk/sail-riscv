#!/usr/bin/env python3
#
# Copyright (c) Qualcomm Technologies, Inc. and/or its subsidiaries.
# SPDX-License-Identifier: BSD-3-Clause-Clear
#
"""A 32-bit debug move roundtrips the wrapped position 19 and its byte image.

The pattern has its sign bit set, so a width that truncated or
sign-extended the value would show up in the roundtrip comparison.
"""

from __future__ import annotations

from mmul_gen.templates.debug_move_common import DebugMoveTemplate


class DebugMove32(DebugMoveTemplate):
    """A 32-bit debug move roundtrips the wrapped position 19 and its byte image."""

    element_bits = 32
    position = 19
    value = 0xF2345678


__all__ = ["DebugMove32"]


DEBUG_MOVE32 = DebugMove32()
