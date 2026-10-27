#!/usr/bin/env python3
#
# Copyright (c) Qualcomm Technologies, Inc. and/or its subsidiaries.
# SPDX-License-Identifier: BSD-3-Clause-Clear
#
"""A column-major load followed by a row-major store restores the ramp.

Spec:    instructions.adoc:5335-5336 (§6.130)
Quote:   "Stores the typed M-register operand beginning at `ms1` to memory in
         row-major format.  The programmed datatype is read from `Md[ms1]`."
Checks:  the cm load followed by the rm store must leave byte 0 at 1, byte E at 2 and
         byte N * E at N+1, restoring the linear ramp the other trip transposes

This is the inverse trip of the other template, so the two edge
expectations swap: the second element becomes 2 and the first element of
the next storage row becomes N+1.
"""

from __future__ import annotations

from mmul_gen.templates.memory_order_common import MemoryOrderTemplate


class MemoryOrderColToRow(MemoryOrderTemplate):
    """A column-major load followed by a row-major store restores the ramp."""

    source_order = "cm"
    destination_order = "rm"


__all__ = ["MemoryOrderColToRow"]


MEMORY_ORDER_COL_TO_ROW = MemoryOrderColToRow()
