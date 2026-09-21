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

DOC_ZH = """\
32 位调试搬移对回绕位置 19 及其字节镜像做往返验证。

模式的符号位被置位，因此截断或符号扩展该值的宽度会在往返比较中暴露。
"""

from mmul_gen.templates.debug_move_common import DebugMoveTemplate


class DebugMove32(DebugMoveTemplate):
    """A 32-bit debug move roundtrips the wrapped position 19 and its byte image."""

    summary_zh = "32 位调试搬移对回绕位置 19 及其字节镜像做往返验证。"
    element_bits = 32
    position = 19
    value = 0xF2345678


__all__ = ["DebugMove32"]


DEBUG_MOVE32 = DebugMove32()
