#!/usr/bin/env python3
#
# Copyright (c) Qualcomm Technologies, Inc. and/or its subsidiaries.
# SPDX-License-Identifier: BSD-3-Clause-Clear
#
"""A 64-bit debug move roundtrips the wrapped position 11 and its byte image.

This is the widest element one row can hold at uds=8, so the instruction
produces no source at all on configurations whose row is narrower.
"""

from __future__ import annotations

DOC_ZH = """\
64 位调试搬移对回绕位置 11 及其字节镜像做往返验证。

这是在 uds=8 时一行能容纳的最宽元素，因此在行更窄的配置上该指令根本不产生源。
"""

from mmul_gen.templates.debug_move_common import DebugMoveTemplate


class DebugMove64(DebugMoveTemplate):
    """A 64-bit debug move roundtrips the wrapped position 11 and its byte image."""

    summary_zh = "64 位调试搬移对回绕位置 11 及其字节镜像做往返验证。"
    element_bits = 64
    position = 11
    value = 0x0123456789ABCDEF


__all__ = ["DebugMove64"]


DEBUG_MOVE64 = DebugMove64()
