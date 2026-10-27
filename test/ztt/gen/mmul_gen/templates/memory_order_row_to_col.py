#!/usr/bin/env python3
#
# Copyright (c) Qualcomm Technologies, Inc. and/or its subsidiaries.
# SPDX-License-Identifier: BSD-3-Clause-Clear
#
"""A row-major load followed by a column-major store transposes the ramp.

Spec:    instructions.adoc:5304-5305 (§6.129)
Quote:   "Stores the typed M-register operand beginning at `ms1` to memory in
         column-major format.  The programmed datatype is read from `Md[ms1]`."
Checks:  the rm load followed by the cm store must leave byte 0 at 1, byte E at N+1
         and byte N * E at 2, so a transposed ramp proves the column-major order

The (r, c) element ends up at column-major offset c * N + r, so the
second stored element becomes N+1 and the first element of the next
storage row becomes 2.
"""

from __future__ import annotations

from mmul_gen.templates.memory_order_common import MemoryOrderTemplate


class MemoryOrderRowToCol(MemoryOrderTemplate):
    """A row-major load followed by a column-major store transposes the ramp."""

    source_order = "rm"
    destination_order = "cm"


__all__ = ["MemoryOrderRowToCol"]


MEMORY_ORDER_ROW_TO_COL = MemoryOrderRowToCol()
