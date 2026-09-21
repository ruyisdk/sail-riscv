#!/usr/bin/env python3
#
# Copyright (c) Qualcomm Technologies, Inc. and/or its subsidiaries.
# SPDX-License-Identifier: BSD-3-Clause-Clear
#
"""A column-major load followed by a row-major store restores the ramp.

This is the inverse trip of the other template, so the two edge
expectations swap: the second element becomes 2 and the first element of
the next storage row becomes N+1.
"""

from __future__ import annotations

DOC_ZH = """\
先列主序加载、再行主序存储，恢复原斜坡。

这是另一模板的逆行程，因此两个边界期望互换：第二个元素变为 2，下一个存储行的第一个元素变为 N+1。
"""

from mmul_gen.templates.memory_order_common import MemoryOrderTemplate


class MemoryOrderColToRow(MemoryOrderTemplate):
    """A column-major load followed by a row-major store restores the ramp."""

    summary_zh = "先列主序加载、再行主序存储，恢复原斜坡。"
    source_order = "cm"
    destination_order = "rm"


__all__ = ["MemoryOrderColToRow"]


MEMORY_ORDER_COL_TO_ROW = MemoryOrderColToRow()
