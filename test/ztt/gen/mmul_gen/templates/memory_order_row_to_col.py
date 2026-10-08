#!/usr/bin/env python3
#
# Copyright (c) Qualcomm Technologies, Inc. and/or its subsidiaries.
# SPDX-License-Identifier: BSD-3-Clause-Clear
#
"""A row-major load followed by a column-major store transposes the ramp.

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
