#!/usr/bin/env python3
#
# Copyright (c) Qualcomm Technologies, Inc. and/or its subsidiaries.
# SPDX-License-Identifier: BSD-3-Clause-Clear
#
"""The mixed-signedness double-square template."""

from __future__ import annotations

DOC_ZH = """\
混合符号性双方阵模板。
"""

from typing import TYPE_CHECKING

from collections.abc import Sequence

from mmul_gen.asm import (
    check_dst_lines,
    data_element_lines,
    hex_value,
    pack_nibbles,
    repeated_square_lines,
)
from mmul_gen.reference import ProductFlags
from mmul_gen.machine import (
    DType,
    MachineConfig,
    SIGNED_PACKED_SOURCE,
    dtype_stem,
)
from mmul_gen.reference import (
    MixedSignednessProduct,
    mixed_signedness_product,
)
from mmul_gen.registers import (
    MRegisterRole,
    m_register_layouts,
)
from mmul_gen.templates.base import (
    Template,
    case_payload,
    paired_cases,
    register,
)

if TYPE_CHECKING:
    from mmul_gen.instruction import Instruction


def _mixed_signedness_fits(machine: MachineConfig, dtype: DType) -> bool:
    source_bits = machine.uds // 2
    roles = (
        MRegisterRole("ms1", machine.nregs(source_bits)),
        MRegisterRole("ms2", machine.nregs(source_bits)),
        MRegisterRole("md", machine.nregs(machine.uds), reuse_of="ms1"),
    )
    return bool(m_register_layouts(machine.num_m_regs, roles))


def _packed_square_data_lines(
    label: str,
    values: Sequence[int],
    element_bits: int,
    machine: MachineConfig,
) -> list[str]:
    """Emit both logical squares in one physically formed packed operand."""

    expected_count = 2 * machine.nelem
    if len(values) != expected_count:
        raise ValueError(
            f"mixed square data needs {expected_count} elements, got {len(values)}"
        )
    lines = [
        f".balign {machine.square_bytes(element_bits)}",
        f"{label}:",
    ]
    if element_bits == 4:
        lines.append(
            "    .byte " + ", ".join(hex_value(value, 8) for value in pack_nibbles(list(values)))
        )
    else:
        lines.extend(data_element_lines(list(values), element_bits))
    return lines


class MixedSignednessMultipleSquare(Template):
    """Two packed squares with different signedness and value."""

    summary_zh = "两个符号性与取值都不同的打包方阵。"
    name = "mixed_signedness_multiple_square"
    dtypes = SIGNED_PACKED_SOURCE

    def __init__(self, product: ProductFlags) -> None:
        """``product`` is the transposed/negated shape of the instruction's product."""

        self.product = product

    def fits(self, machine: MachineConfig, instruction: Instruction, dtype: DType) -> bool:
        return _mixed_signedness_fits(machine, dtype)

    def build(self, machine, instruction, dtype):
        product = mixed_signedness_product(machine.uds, machine.n, self.product)
        return paired_cases(
            machine,
            dtype,
            product,
            source_bits=machine.uds // 2,
            destination_bits=machine.uds,
            description=(
                f"两个打包方阵：{product.lhs_dtype} × {product.rhs_dtype} "
                f"-> {product.dest_dtype}"
            ),
        )

    def render(self, machine, instruction, case, out):
        payload = case_payload(MixedSignednessProduct, case)

        number = case.number
        geometry_uds = machine.uds
        storage_bits = geometry_uds // 2
        stem = dtype_stem(case.dtype.name)
        lhs = register("ms1", case.layout)
        rhs = register("ms2", case.layout)
        destination = register("md", case.layout)
        acc = case.layout.acc.base
        prefix = f"mixed{number}_{stem}_"
        lhs_label = f"{prefix}lhs_square"
        rhs_label = f"{prefix}rhs_square"
        dst_label = f"{prefix}dst_square"

        out.text.extend(
            [
                f"    # mixed signedness/multiple-square case {number}: {instruction.name}",
                f"    li      t0, {payload.lhs_dtype}",
                f"    msettyp m{lhs}, t0",
                f"    li      t0, {payload.rhs_dtype}",
                f"    msettyp m{rhs}, t0",
                f"    li      t0, {payload.dest_dtype}",
                f"    asettyp acc{acc}, t0",
                "",
                f"    la      t1, {lhs_label}",
                f"    mls.rm     m{lhs}, t1",
                f"    la      t2, {rhs_label}",
                f"    mls.rm     m{rhs}, t2",
                f"    mzero.2d.acc acc{acc}",
                f"    {instruction.name} acc{acc}, m{lhs}, m{rhs}",
                f"    msettyp m{destination}, t0",
                f"    mmov.m.a m{destination}, acc{acc}",
                f"    la      t3, {dst_label}",
                f"    mss.rm     m{destination}, t3",
            ]
        )
        out.text.extend(
            check_dst_lines(payload.expected, geometry_uds, machine=machine, label=dst_label)
        )
        out.data.extend(_packed_square_data_lines(lhs_label, payload.lhs, storage_bits, machine))
        out.data.extend(_packed_square_data_lines(rhs_label, payload.rhs, storage_bits, machine))
        out.data.extend(repeated_square_lines(dst_label, 0, geometry_uds, machine))
        out.data.append("")
