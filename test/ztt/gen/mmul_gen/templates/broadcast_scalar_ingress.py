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

from mmul_gen.machine import INTEGER
from mmul_gen.templates.broadcast_common import ScalarIngressTemplate


class ScalarIngressBroadcast(ScalarIngressTemplate):
    """Whole-register integer descriptors broadcast through the scalar ingress."""

    name = "scalar_ingress"
    dtypes = INTEGER


__all__ = ["ScalarIngressBroadcast"]


SCALAR_INGRESS = ScalarIngressBroadcast()
