#!/usr/bin/env python3
#
# Copyright (c) Qualcomm Technologies, Inc. and/or its subsidiaries.
# SPDX-License-Identifier: BSD-3-Clause-Clear
#
"""Whole-register integer descriptors broadcast through the scalar ingress.

The body is inherited from the shared scalar-ingress template; only the
datatype domain and the case numbering restart per group.
"""

from __future__ import annotations

DOC_ZH = """\
整寄存器整数描述符经标量入口广播。

主体继承自共享的标量入口模板；只有 datatype 域和每组的用例编号重新开始。
"""

from mmul_gen.machine import INTEGER
from mmul_gen.templates.broadcast_common import ScalarIngressTemplate


class ScalarIngressBroadcast(ScalarIngressTemplate):
    """Whole-register integer descriptors broadcast through the scalar ingress."""

    summary_zh = "整寄存器整数描述符经标量入口广播。"
    name = "scalar_ingress"
    dtypes = INTEGER


__all__ = ["ScalarIngressBroadcast"]


SCALAR_INGRESS = ScalarIngressBroadcast()
