#!/usr/bin/env python3
#
# Copyright (c) Qualcomm Technologies, Inc. and/or its subsidiaries.
# SPDX-License-Identifier: BSD-3-Clause-Clear
#
"""A 64-bit debug move roundtrips the wrapped position 11 and its byte image.

Spec:    instructions.adoc:2663-2665 (§6.65)
Quote:   "The contents of `md` are viewed, in row-major order, as `N = sqrt(AME_NELEM)`
         rows of `row_elements = (N * AME_UNIT_DATATYPE_SIZE) / 64` 64-bit elements
         each, independent of the configured datatype `Md[md]`."
Checks:  position 11 must wrap modulo the raw-view row width, and the full
         0x0123456789ABCDEF element must roundtrip and reappear in the mss.rm image

This is the widest element one row can hold at uds=8, so the instruction
produces no source at all on configurations whose row is narrower.
"""

from __future__ import annotations

from mmul_gen.templates.debug_move_common import DebugMoveTemplate


class DebugMove64(DebugMoveTemplate):
    """A 64-bit debug move roundtrips the wrapped position 11 and its byte image."""

    element_bits = 64
    position = 11
    value = 0x0123456789ABCDEF


__all__ = ["DebugMove64"]


DEBUG_MOVE64 = DebugMove64()
