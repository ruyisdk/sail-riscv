#!/usr/bin/env python3
#
# Copyright (c) Qualcomm Technologies, Inc. and/or its subsidiaries.
# SPDX-License-Identifier: BSD-3-Clause-Clear
#
"""A 32-bit debug move roundtrips the wrapped position 19 and its byte image.

Spec:    instructions.adoc:2612-2614 (§6.64)
Quote:   "The contents of `md` are viewed, in row-major order, as `N = sqrt(AME_NELEM)`
         rows of `row_elements = (N * AME_UNIT_DATATYPE_SIZE) / 32` 32-bit elements
         each, independent of the configured datatype `Md[md]`."
Checks:  position 19 must wrap modulo the raw-view row width, and 0xF2345678 must
         roundtrip with its sign bit intact and reappear in the mss.rm image

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
