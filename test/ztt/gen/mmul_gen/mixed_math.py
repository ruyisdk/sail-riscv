#!/usr/bin/env python3
#
# Copyright (c) Qualcomm Technologies, Inc. and/or its subsidiaries.
# SPDX-License-Identifier: BSD-3-Clause-Clear
#
"""Which stimulus and which answer each 1-D math operation gives in mixed form.

The operations of the family split into two kinds.  ``mfrint*``, ``msqrt``,
``mexp2`` and ``mlog2`` have an exactly representable answer for a carefully
chosen source, so their cases can compare the stored element bit for bit.
``mrec``, ``mrsqrt``, ``mcos``, ``msin`` and ``mtanh`` are bounded
approximations whose last bits belong to the implementation.

An exact operation's stimulus is therefore the one whose answer is exactly
representable -- an integral source for the rounding family, a perfect square
for the roots, a power of two for the log/exp pair.  An approximate operation's
stimulus is a small exactly representable value whose answer is inexact, which
is what makes NX the flag to assert.
"""

from __future__ import annotations

import math
from enum import StrEnum
from fractions import Fraction

from mmul_gen.float_formats import exact_root


class MixedMathOperation(StrEnum):
    """One operation of the family, with its mixed-format stimulus and answer."""

    FLOOR = "floor"
    NEAREST = "nearest"
    CEIL = "ceil"
    TRUNC = "trunc"
    SQRT = "sqrt"
    RECIPROCAL = "reciprocal"
    RECIPROCAL_SQRT = "reciprocal_sqrt"
    COS = "cos"
    SIN = "sin"
    TANH = "tanh"
    EXP2 = "exp2"
    LOG2 = "log2"

    @property
    def answer_is_exact(self) -> bool:
        """Whether this operation's case compares the stored element bit for bit."""

        return self not in {
            MixedMathOperation.RECIPROCAL,
            MixedMathOperation.RECIPROCAL_SQRT,
            MixedMathOperation.COS,
            MixedMathOperation.SIN,
            MixedMathOperation.TANH,
        }

    @property
    def stimulus(self) -> tuple[Fraction, ...]:
        """The source values of this operation's case.

        An exact operation's stimulus is chosen so that its answer is exactly
        representable -- an integral source for the rounding family, a perfect
        square for the roots, a power of two for the log/exp pair.  An
        approximate operation's stimulus is a small exactly representable value
        with an inexact answer, which is what makes NX the flag to assert.
        """

        match self:
            case (
                MixedMathOperation.FLOOR
                | MixedMathOperation.NEAREST
                | MixedMathOperation.CEIL
                | MixedMathOperation.TRUNC
            ):
                # Integral on purpose: see the module docstring.
                return (
                    Fraction(3),
                    Fraction(-3),
                    Fraction(2),
                    Fraction(-2),
                    Fraction(4),
                    Fraction(-4),
                )
            case MixedMathOperation.SQRT:
                return (
                    Fraction(1, 4),
                    Fraction(1),
                    Fraction(9, 4),
                    Fraction(4),
                    Fraction(1, 16),
                    Fraction(16),
                    Fraction(64),
                    Fraction(256),
                )
            case MixedMathOperation.EXP2:
                return (
                    Fraction(1),
                    Fraction(2),
                    Fraction(3),
                    Fraction(-1),
                    Fraction(-2),
                    Fraction(4),
                )
            case MixedMathOperation.LOG2:
                return (
                    Fraction(2),
                    Fraction(4),
                    Fraction(8),
                    Fraction(1, 2),
                    Fraction(16),
                    Fraction(1, 4),
                )
            case (
                MixedMathOperation.RECIPROCAL
                | MixedMathOperation.RECIPROCAL_SQRT
                | MixedMathOperation.COS
                | MixedMathOperation.SIN
                | MixedMathOperation.TANH
            ):
                return (Fraction(3), Fraction(5), Fraction(6), Fraction(7))
        raise ValueError(f"{self}: no stimulus")  # pragma: no cover - exhaustive

    def exact_answer(self, value: Fraction) -> Fraction:
        """The mathematical answer of an exact operation for one exact source."""

        match self:
            case MixedMathOperation.FLOOR:
                return Fraction(math.floor(value))
            case MixedMathOperation.CEIL:
                return Fraction(math.ceil(value))
            case MixedMathOperation.TRUNC:
                return Fraction(math.trunc(value))
            case MixedMathOperation.NEAREST:
                return Fraction(round(value))
            case MixedMathOperation.SQRT:
                return exact_root(value)
            case MixedMathOperation.EXP2:
                if value.denominator != 1:
                    raise ValueError(f"2**{value} is not exactly representable")
                exponent = int(value)
                return Fraction(2**exponent) if exponent >= 0 else Fraction(1, 2**-exponent)
            case MixedMathOperation.LOG2:
                answer = 0
                scaled = value
                while scaled < 1:
                    scaled *= 2
                    answer -= 1
                while scaled > 1:
                    scaled /= 2
                    answer += 1
                if scaled != 1:
                    raise ValueError(f"log2({value}) is not an integer")
                return Fraction(answer)
            case _:
                raise ValueError(f"{self} has no exact answer")


__all__ = ["MixedMathOperation"]
