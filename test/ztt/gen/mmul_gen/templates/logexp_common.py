#!/usr/bin/env python3
#
# Copyright (c) Qualcomm Technologies, Inc. and/or its subsidiaries.
# SPDX-License-Identifier: BSD-3-Clause-Clear
#
"""The data vocabulary and operand shapes of the integer log/exp family.

Every case works on whole squares: a destination at ``m0``, a first source at
``m1``, and -- for the forms that read two squares -- a second source at ``m2``.
The values those squares hold are named here, so an instruction declares *which*
square it reads instead of restating the number, and the same nominal template
serves all twelve instructions, and it also names the four operand shapes those
instructions come in, so an instruction states its shape as a template argument.
"""

from __future__ import annotations

DOC_ZH = """\
整数 log/exp 家族的数据词汇与操作数形态。

每个用例都作用于整个方阵：目的方阵在 ``m0``，第一源在 ``m1``，对于读取两个方阵的形式，第二源在 ``m2``。这些方阵持有的值在这里命名，因此指令声明它读取*哪个*方阵，而不是重述数字，同一个标称模板服务全部十二条指令；这里还命名这些指令的四种操作数形态，因此指令以模板参数的形式陈述自己的形态。
"""

from enum import StrEnum
from typing import TYPE_CHECKING

from mmul_gen.inputs import int_edge_value
from mmul_gen.machine import dtype_stem

if TYPE_CHECKING:
    from mmul_gen.machine import DType, MachineConfig


class LogExpForm(StrEnum):
    """Operand shape of one integer log/exp instruction."""

    UNARY = "unary"
    BINARY_M = "binary_m"
    TERNARY_M = "ternary_m"
    BINARY_X = "binary_x"

    @property
    def reads_second_source(self) -> bool:
        """Whether the form reads a second M register."""

        return self in (LogExpForm.BINARY_M, LogExpForm.TERNARY_M)


#: The named squares the nominal cases are built from.
DATA_VALUES = {
    "exp_square": 3,
    "pow2_square": 8,
    "mant_square": 3,
    "rd_mant_square": 16,
    "exp_square2": 2,
    "bias_square": 10,
    "dest_init_square": 7,
}
#: Square a case seeds its destination from when it does not trust it.
DESTINATION_SEED_LABEL = "dest_init_square"
#: The square every case stores into and verifies from.
DESTINATION_LABEL = "dst_square"
#: Register bases: the destination and the two source groups.
DESTINATION_REGISTER = 0


def source_registers(machine: "MachineConfig", element_bits: int) -> tuple[int, int]:
    """The first and second source group bases for one element width."""

    nregs = machine.nregs(element_bits)
    return nregs, nregs * 2


def case_prefix(kind: str, index: int, dtype: DType) -> str:
    """Label prefix of one case, unique across the whole file."""

    return f"{kind}{index}_{dtype_stem(dtype.name)}_"


def saturating_max(dtype: DType) -> int:
    """The largest representable value: what saturation must clamp to."""

    return int_edge_value(dtype.name, dtype.bits, "upper_bound")


__all__ = [
    "DATA_VALUES",
    "LogExpForm",
    "DESTINATION_LABEL",
    "DESTINATION_REGISTER",
    "DESTINATION_SEED_LABEL",
    "case_prefix",
    "saturating_max",
    "source_registers",
]
