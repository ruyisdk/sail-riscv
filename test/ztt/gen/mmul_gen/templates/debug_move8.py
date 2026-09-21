#!/usr/bin/env python3
#
# Copyright (c) Qualcomm Technologies, Inc. and/or its subsidiaries.
# SPDX-License-Identifier: BSD-3-Clause-Clear
#
"""An 8-bit debug move roundtrips the wrapped position 65 and its byte image.

65 wraps to element 1 of the 32-byte raw view, so the check also proves
that the position is taken modulo the view width and not modulo the
register count.
"""

from __future__ import annotations

DOC_ZH = """\
8 位调试搬移对回绕位置 65 及其字节镜像做往返验证。

65 回绕到 32 字节原始视图的元素 1，因此该检查还证明位置是按视图宽度取模、而不是按寄存器个数取模。
"""

from mmul_gen.templates.debug_move_common import DebugMoveTemplate


class DebugMove8(DebugMoveTemplate):
    """An 8-bit debug move roundtrips the wrapped position 65 and its byte image."""

    summary_zh = "8 位调试搬移对回绕位置 65 及其字节镜像做往返验证。"
    element_bits = 8
    position = 65
    value = 0x1A5


__all__ = ["DebugMove8"]


DEBUG_MOVE8 = DebugMove8()
