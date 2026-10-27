#!/usr/bin/env python3
#
# Copyright (c) Qualcomm Technologies, Inc. and/or its subsidiaries.
# SPDX-License-Identifier: BSD-3-Clause-Clear
#
"""An 8-bit debug move roundtrips the wrapped position 65 and its byte image.

Spec:    instructions.adoc:2510-2512 (§6.62)
Quote:   "The contents of `md` are viewed, in row-major order, as `N = sqrt(AME_NELEM)`
         rows of `row_elements = (N * AME_UNIT_DATATYPE_SIZE) / 8` 8-bit elements
         each, independent of the configured datatype `Md[md]`."
Checks:  position 65 must wrap modulo the raw-view row width to element 1, and the
         mss.rm image must show 0xA5 in that element's single byte

65 wraps to element 1 of the 32-byte raw view, so the check also proves
that the position is taken modulo the view width and not modulo the
register count.
"""

from __future__ import annotations

from mmul_gen.templates.debug_move_common import DebugMoveTemplate


class DebugMove8(DebugMoveTemplate):
    """An 8-bit debug move roundtrips the wrapped position 65 and its byte image."""

    element_bits = 8
    position = 65
    value = 0x1A5


__all__ = ["DebugMove8"]


DEBUG_MOVE8 = DebugMove8()
