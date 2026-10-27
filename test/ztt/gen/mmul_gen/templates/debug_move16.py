#!/usr/bin/env python3
#
# Copyright (c) Qualcomm Technologies, Inc. and/or its subsidiaries.
# SPDX-License-Identifier: BSD-3-Clause-Clear
#
"""A 16-bit debug move roundtrips the wrapped position 35 and its byte image.

Spec:    instructions.adoc:2561-2563 (§6.63)
Quote:   "The contents of `md` are viewed, in row-major order, as `N = sqrt(AME_NELEM)`
         rows of `row_elements = (N * AME_UNIT_DATATYPE_SIZE) / 16` 16-bit elements
         each, independent of the configured datatype `Md[md]`."
Checks:  position 35 must wrap modulo the raw-view row width, and both bytes of the
         0x1C3D element must appear in the mss.rm image

The 16-bit element straddles two bytes, so both ends of the element are
checked in the stored image and not just the low byte.
"""

from __future__ import annotations

from mmul_gen.templates.debug_move_common import DebugMoveTemplate


class DebugMove16(DebugMoveTemplate):
    """A 16-bit debug move roundtrips the wrapped position 35 and its byte image."""

    element_bits = 16
    position = 35
    value = 0x1C3D


__all__ = ["DebugMove16"]


DEBUG_MOVE16 = DebugMove16()
