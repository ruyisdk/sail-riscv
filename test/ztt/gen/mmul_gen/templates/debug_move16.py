#!/usr/bin/env python3
#
# Copyright (c) Qualcomm Technologies, Inc. and/or its subsidiaries.
# SPDX-License-Identifier: BSD-3-Clause-Clear
#
"""A 16-bit debug move roundtrips the wrapped position 35 and its byte image.

The 16-bit element straddles two bytes, so both ends of the element are
checked in the stored image and not just the low byte.
"""

from __future__ import annotations

DOC_ZH = """\
16 位调试搬移对回绕位置 35 及其字节镜像做往返验证。

16 位元素跨两个字节，因此存储镜像中检查元素的两端，而不只是低字节。
"""

from mmul_gen.templates.debug_move_common import DebugMoveTemplate


class DebugMove16(DebugMoveTemplate):
    """A 16-bit debug move roundtrips the wrapped position 35 and its byte image."""

    summary_zh = "16 位调试搬移对回绕位置 35 及其字节镜像做往返验证。"
    element_bits = 16
    position = 35
    value = 0x1C3D


__all__ = ["DebugMove16"]


DEBUG_MOVE16 = DebugMove16()
