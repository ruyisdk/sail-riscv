#!/usr/bin/env python3
#
# Copyright (c) Qualcomm Technologies, Inc. and/or its subsidiaries.
# SPDX-License-Identifier: BSD-3-Clause-Clear
#
"""Chinese text of every ``# input:`` case description the generator emits.

The templates address their input cases by stable identifiers, and the same
identifier also names the case in the design document.  This module is the one
place that turns such an identifier into the Chinese text the generated
assembly comment and the design document carry, so the delivered prose has a
single source and cannot drift from a translation kept beside it.

A name with no entry is a generator defect: emitting the identifier instead
would leave an untranslated comment in a delivered document, so the lookup
fails loudly.
"""

from __future__ import annotations

#: Chinese text of the row/column control input cases.
ROW_COLUMN_CASES_ZH: dict[str, str] = {
    "coordinate_ramp": "坐标斜坡",
    "first_column": "首列",
    "last_column": "末列",
    "first_row": "首行",
    "last_row": "末行",
    "forward_shift": "正向平移",
    "reverse_shift": "反向平移",
}

#: Chinese text of the packed-slot input cases.
PACKED_SLOT_CASES_ZH: dict[str, str] = {
    "selected_slot": "选中槽位",
    "preserved_slot": "保留槽位",
    "signed_boundary_values": "有符号边界值",
}

#: Chinese text of the packed accumulator-span input cases.
SPAN_CASES_ZH: dict[str, str] = {
    "span_low": "低端打包累加器跨度",
    "span_high": "高端打包累加器跨度",
    "overlapping_readback": "重叠读回",
    "crossing_span": "跨累加器文件末端的跨度",
    "unsupported_span": "不支持的跨度",
}

#: Chinese text of the case names that double as template names.
TEMPLATE_CASES_ZH: dict[str, str] = {
    "supported_dtype_roundtrip": "受支持 datatype 的往返",
    "physical_image_and_register_edge": "物理镜像与寄存器边界",
    "roundtrip_with_boundary_values": "边界值往返",
    "row_column_roundtrip_with_edge_checks": "行/列往返并检查边界",
    "position_roundtrip_and_memory_image": "位置往返与内存镜像",
    "acquire_release_state": "获取与释放状态",
    "busy_state": "忙状态",
    "acc_to_m": "累加器读回 M 寄存器",
    "m_to_acc": "M 寄存器搬入累加器",
    "zero_acc": "累加器清零",
    "zero_m": "M 寄存器清零",
}

#: Chinese text of the integer-shift input case.
INTEGER_SHIFT_CASE_ZH: dict[str, str] = {
    "sign and width edge values with modulo-reduced shift amounts": (
        "符号与位宽边界值，位移量按元素宽度取模"
    ),
}

#: Chinese text of the floating-point special-value cases.
FLOAT_SPECIAL_CASES_ZH: dict[str, str] = {
    "signed_zero": "有符号零",
    "negative_infinity": "负无穷",
    "negative_qnan": "负 quiet NaN",
    "quiet_nan": "quiet NaN",
    "signaling_nan": "signaling NaN",
    "positive_infinity": "正无穷",
    "infinity_minus_infinity": "无穷减无穷",
    "zero_times_infinity": "零乘无穷",
}

#: Every case name the generator may emit, mapped to its Chinese text.
CASE_DESCRIPTION_ZH: dict[str, str] = {
    **ROW_COLUMN_CASES_ZH,
    **PACKED_SLOT_CASES_ZH,
    **SPAN_CASES_ZH,
    **TEMPLATE_CASES_ZH,
    **INTEGER_SHIFT_CASE_ZH,
    **FLOAT_SPECIAL_CASES_ZH,
}


def description_zh(case_name: str) -> str:
    """The Chinese description of one case name.

    The name is the generator's own case identifier; an unknown name is a
    defect rather than a value to fall back on, so the lookup raises.
    """

    try:
        return CASE_DESCRIPTION_ZH[case_name]
    except KeyError:
        raise KeyError(f"no Chinese case description for {case_name!r}") from None


__all__ = [
    "CASE_DESCRIPTION_ZH",
    "FLOAT_SPECIAL_CASES_ZH",
    "INTEGER_SHIFT_CASE_ZH",
    "PACKED_SLOT_CASES_ZH",
    "ROW_COLUMN_CASES_ZH",
    "SPAN_CASES_ZH",
    "TEMPLATE_CASES_ZH",
    "description_zh",
]
