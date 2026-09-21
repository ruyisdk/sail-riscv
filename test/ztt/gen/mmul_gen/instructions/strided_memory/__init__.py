#!/usr/bin/env python3
#
# Copyright (c) Qualcomm Technologies, Inc. and/or its subsidiaries.
# SPDX-License-Identifier: BSD-3-Clause-Clear
#
"""Strided memory transfer instruction declarations."""

from __future__ import annotations

from mmul_gen.instructions.strided_memory.mls_st import MlsSt
from mmul_gen.instructions.strided_memory.mls_tst import MlsTst
from mmul_gen.instructions.strided_memory.mss_st import MssSt
from mmul_gen.instructions.strided_memory.mss_tst import MssTst

#: Every strided transfer, in family order.
STRIDED_MEMORY_INSTRUCTIONS = (MlsSt(), MlsTst(), MssSt(), MssTst())

__all__ = ["MlsSt", "MlsTst", "MssSt", "MssTst", "STRIDED_MEMORY_INSTRUCTIONS"]
