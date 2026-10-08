#!/usr/bin/env python3
#
# Copyright (c) Qualcomm Technologies, Inc. and/or its subsidiaries.
# SPDX-License-Identifier: BSD-3-Clause-Clear
#
"""English text of every ``# input:`` case description the generator emits.

The templates address their input cases by stable identifiers, and the same
identifier also names the case in the design document.  This module is the one
place that turns such an identifier into the text the generated assembly
comment carries, so the emitted prose has a single source and cannot drift from
a translation kept beside it.

The design document is Chinese; its wording lives in
``doc/ztt_case_text_zh.json``, keyed by the English text this module returns.

A name with no entry is a generator defect: emitting the identifier instead
would leave an undescribed comment in a delivered source, so the lookup fails
loudly.
"""

from __future__ import annotations

#: Text of the row/column control input cases.
ROW_COLUMN_CASES: dict[str, str] = {
    "coordinate_ramp": "coordinate ramp",
    "first_column": "first column",
    "last_column": "last column",
    "first_row": "first row",
    "last_row": "last row",
    "forward_shift": "forward shift",
    "reverse_shift": "reverse shift",
}

#: Text of the packed-slot input cases.
PACKED_SLOT_CASES: dict[str, str] = {
    "selected_slot": "selected slot",
    "preserved_slot": "preserved slot",
    "signed_boundary_values": "signed boundary values",
}

#: Text of the packed accumulator-span input cases.
SPAN_CASES: dict[str, str] = {
    "span_low": "low packed accumulator span",
    "span_high": "high packed accumulator span",
    "overlapping_readback": "overlapping readback",
    "crossing_span": "span crossing the end of the accumulator file",
    "unsupported_span": "unsupported span",
}

#: Text of the case names that double as template names.
TEMPLATE_CASES: dict[str, str] = {
    "supported_dtype_roundtrip": "round trip of a supported datatype",
    "physical_image_and_register_edge": "physical image and register edge",
    "roundtrip_with_boundary_values": "round trip with boundary values",
    "row_column_roundtrip_with_edge_checks": "row/column round trip with edge checks",
    "position_roundtrip_and_memory_image": "position round trip and memory image",
    "acquire_release_state": "acquire and release state",
    "busy_state": "busy state",
    "acc_to_m": "accumulator read back into an M register",
    "m_to_acc": "M register moved into an accumulator",
    "zero_acc": "accumulator zeroed",
    "zero_m": "M register zeroed",
}

#: Text of the integer-shift input case.
INTEGER_SHIFT_CASE: dict[str, str] = {
    "sign and width edge values with modulo-reduced shift amounts": (
        "sign and width edge values with modulo-reduced shifts"
    ),
}

#: Text of the floating-point special-value cases.
FLOAT_SPECIAL_CASES: dict[str, str] = {
    "signed_zero": "signed zero",
    "negative_infinity": "negative infinity",
    "negative_qnan": "negative quiet NaN",
    "quiet_nan": "quiet NaN",
    "signaling_nan": "signaling NaN",
    "positive_infinity": "positive infinity",
    "infinity_minus_infinity": "infinity minus infinity",
    "zero_times_infinity": "zero times infinity",
}

#: Every case name the generator may emit, mapped to its text.
CASE_DESCRIPTION: dict[str, str] = {
    **ROW_COLUMN_CASES,
    **PACKED_SLOT_CASES,
    **SPAN_CASES,
    **TEMPLATE_CASES,
    **INTEGER_SHIFT_CASE,
    **FLOAT_SPECIAL_CASES,
}


def description(case_name: str) -> str:
    """The description of one case name.

    The name is the generator's own case identifier; an unknown name is a
    defect rather than a value to fall back on, so the lookup raises.
    """

    try:
        return CASE_DESCRIPTION[case_name]
    except KeyError:
        raise KeyError(f"no case description for {case_name!r}") from None


__all__ = [
    "CASE_DESCRIPTION",
    "FLOAT_SPECIAL_CASES",
    "INTEGER_SHIFT_CASE",
    "PACKED_SLOT_CASES",
    "ROW_COLUMN_CASES",
    "SPAN_CASES",
    "TEMPLATE_CASES",
    "description",
]
