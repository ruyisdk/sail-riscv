#!/usr/bin/env python3
#
# Copyright (c) Qualcomm Technologies, Inc. and/or its subsidiaries.
# SPDX-License-Identifier: BSD-3-Clause-Clear
#
"""128-bit saturating integers broadcast through the scalar ingress.

The body is inherited from the shared scalar-ingress template; only the
datatype domain and the case numbering restart per group.
"""

from __future__ import annotations

DOC_ZH = """\
128 位饱和整数经标量入口广播。

主体继承自共享的标量入口模板；只有 datatype 域和每组的用例编号重新开始。
"""

from mmul_gen.machine import SATURATING_INTEGER128
from mmul_gen.templates.broadcast_common import ScalarIngressTemplate


class SaturatingInteger128IngressBroadcast(ScalarIngressTemplate):
    """128-bit saturating integers broadcast through the scalar ingress."""

    summary_zh = "128 位饱和整数经标量入口广播。"
    name = "saturating_integer128_ingress"
    dtypes = SATURATING_INTEGER128


__all__ = ["SaturatingInteger128IngressBroadcast"]


SATURATING_INTEGER128_INGRESS = SaturatingInteger128IngressBroadcast()
