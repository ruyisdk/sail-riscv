#!/usr/bin/env python3
#
# Copyright (c) Qualcomm Technologies, Inc. and/or its subsidiaries.
# SPDX-License-Identifier: BSD-3-Clause-Clear
#
"""Saturating integer descriptors broadcast through the scalar ingress.

The body is inherited from the shared scalar-ingress template; only the
datatype domain and the case numbering restart per group.
"""

from __future__ import annotations

DOC_ZH = """\
饱和整数描述符经标量入口广播。

主体继承自共享的标量入口模板；只有 datatype 域和每组的用例编号重新开始。
"""

from mmul_gen.machine import SATURATING_INTEGER
from mmul_gen.templates.broadcast_common import ScalarIngressTemplate


class SaturatingIngressBroadcast(ScalarIngressTemplate):
    """Saturating integer descriptors broadcast through the scalar ingress."""

    summary_zh = "饱和整数描述符经标量入口广播。"
    name = "saturating_ingress"
    dtypes = SATURATING_INTEGER


__all__ = ["SaturatingIngressBroadcast"]


SATURATING_INGRESS = SaturatingIngressBroadcast()
