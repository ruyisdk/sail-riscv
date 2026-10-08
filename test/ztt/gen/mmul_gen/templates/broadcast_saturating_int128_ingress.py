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

from mmul_gen.machine import SATURATING_INTEGER128
from mmul_gen.templates.broadcast_common import ScalarIngressTemplate


class SaturatingInteger128IngressBroadcast(ScalarIngressTemplate):
    """128-bit saturating integers broadcast through the scalar ingress."""

    name = "saturating_integer128_ingress"
    dtypes = SATURATING_INTEGER128


__all__ = ["SaturatingInteger128IngressBroadcast"]


SATURATING_INTEGER128_INGRESS = SaturatingInteger128IngressBroadcast()
