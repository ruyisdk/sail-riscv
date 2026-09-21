#!/usr/bin/env python3
#
# Copyright (c) Qualcomm Technologies, Inc. and/or its subsidiaries.
# SPDX-License-Identifier: BSD-3-Clause-Clear
#
"""The immutable description of one generation pass.

:class:`MachineConfig` carries everything an instruction needs to render one
test file: the datatype descriptors parsed from ``ame_macros.inc`` and the
N/UDS/M/ACC register configuration.  Instructions receive it explicitly, so
nothing in this package depends on module-level mutable state.

Datatype *domains* (which descriptors a template iterates) are named functions of
the configuration rather than predicates scattered through templates.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from generator_types import DType


# Widths that participate in the ordinary integer, saturating, and packed
# matrix-product templates.
_INTEGER_WIDTHS = frozenset({4, 8, 16, 32, 64})

# The floating-point descriptors with an IEEE/OCP bit layout the reference
# vectors cover.  FP8/OCP descriptors are listed by name because their width
# alone does not identify the format.
_SOFTFLOAT_DESCRIPTORS = frozenset(
    {
        ("AME_OCP_E4M3_DTYPE", 8),
        ("AME_OCP_E5M2_DTYPE", 8),
        ("AME_FP16_DTYPE", 16),
        ("AME_BF16_DTYPE", 16),
        ("AME_FP32_DTYPE", 32),
        ("AME_FP64_DTYPE", 64),
    }
)

_FLOAT_PREFIXES = ("AME_FP", "AME_BF", "AME_OCP")

#: Descriptor the unsupported-datatype probes seed a register with before
#: presenting an out-of-range code in its place.
_UNSUPPORTED_PROBE_DTYPE = "AME_INT8_DTYPE"

@dataclass(frozen=True)
class DTypeDomain:
    """A named, machine-dependent selection of datatype descriptors.

    Templates iterate a domain; instructions declare the domains they cover.  A
    domain is a first-class value rather than a bare callable so that an
    instruction can be read -- and validated -- without evaluating it.
    """

    name: str
    description: str
    description_zh: str
    select: Callable[["MachineConfig"], tuple[DType, ...]]

    def __call__(self, machine: "MachineConfig") -> tuple[DType, ...]:
        return self.select(machine)


def dtype_is_signed_int(dtype_name: str) -> bool:
    """True for the signed integer descriptors ``AME_INT*``."""

    return dtype_name.startswith("AME_INT")


def dtype_stem(dtype_name: str) -> str:
    """Short, assembler-safe name used inside generated labels."""

    return dtype_name.removeprefix("AME_").removesuffix("_DTYPE").lower()


def _is_one_of(dtype: DType, widths: frozenset[int], *, saturating: bool) -> bool:
    return (
        dtype.bits in widths
        and ("_SAT_" in dtype.name) is saturating
        and not dtype.name.startswith(_FLOAT_PREFIXES)
    )


def _plain_integer(dtypes: tuple[DType, ...]) -> tuple[DType, ...]:
    return tuple(
        dtype for dtype in dtypes if _is_one_of(dtype, _INTEGER_WIDTHS, saturating=False)
    )


def _saturating_integer(dtypes: tuple[DType, ...]) -> tuple[DType, ...]:
    return tuple(
        dtype for dtype in dtypes if _is_one_of(dtype, _INTEGER_WIDTHS, saturating=True)
    )


def _select_integer(machine: "MachineConfig") -> tuple[DType, ...]:
    """Non-saturating integer descriptors formed as whole M registers."""

    return _plain_integer(machine.semantic_dtypes)


def _select_saturating_integer(machine: "MachineConfig") -> tuple[DType, ...]:
    """Saturating integer descriptors formed as whole M registers."""

    return _saturating_integer(machine.semantic_dtypes)


def _select_saturating_integer128(machine: "MachineConfig") -> tuple[DType, ...]:
    """128-bit saturating integer descriptors."""

    return tuple(
        dtype
        for dtype in machine.semantic_dtypes
        if dtype.bits == 128
        and "_SAT_" in dtype.name
        and not dtype.name.startswith(_FLOAT_PREFIXES)
    )


def _select_semantic(machine: "MachineConfig") -> tuple[DType, ...]:
    """Every descriptor that forms a whole-register operand at this UDS.

    A strided transfer is bit-preserving and moves whole squares, so it accepts
    one segment per element for every descriptor at or above the UDS rather than
    for a narrowed group.
    """

    return machine.semantic_dtypes


def _select_strided_storage(machine: "MachineConfig") -> tuple[DType, ...]:
    """Sub-UDS descriptors a bit-preserving transfer can pack into one register.

    The packed-storage recipe exercises every descriptor that is stored narrower
    than the UDS -- saturating and floating ones included -- because the transfer
    itself is bit-preserving and does not depend on an integer-only conversion.
    """

    return tuple(dtype for dtype in machine.formed_dtypes if dtype.bits < machine.uds)


def _select_strided_conversion(machine: "MachineConfig") -> tuple[DType, ...]:
    """The storage half of each conversion pair, unsigned before signed.

    The pair list is the conversion recipe's numbering: pair ``0`` is the
    unsigned pair and pair ``1`` the signed one, which is the order the labels
    print.  ``PACKED_CONVERSION`` holds the same descriptors but in declaration
    order, which would renumber the labels here.
    """

    available = {dtype.name for dtype in machine.dtypes}
    if machine.uds < 8 or machine.uds % 2:
        return ()
    storage_bits = machine.uds // 2
    candidates = (
        (f"AME_UINT{storage_bits}_DTYPE", f"AME_UINT{machine.uds}_DTYPE"),
        (f"AME_INT{storage_bits}_DTYPE", f"AME_INT{machine.uds}_DTYPE"),
    )
    by_name = {dtype.name: dtype for dtype in machine.dtypes}
    return tuple(
        by_name[storage]
        for storage, compute in candidates
        if storage in available and compute in available
    )


def _select_packed_storage(machine: "MachineConfig") -> tuple[DType, ...]:
    """Every descriptor physically stored at half the active UDS.

    A bit-preserving operation that fills storage slots can use any descriptor
    of that width, not just the signed/unsigned conversion pairs: the
    saturating and floating descriptors of the same width are equally valid.
    """

    return tuple(dtype for dtype in machine.dtypes if dtype.bits * 2 == machine.uds)


def _select_formed_integer(machine: "MachineConfig") -> tuple[DType, ...]:
    """Non-saturating integer descriptors, packed or whole.

    A shift forms its source from a single M-register operand, so it accepts the
    sub-UDS descriptors that several-per-row packing unlocks as well as the
    whole-register ones.
    """

    return _plain_integer(machine.formed_dtypes)


def _select_integer128(machine: "MachineConfig") -> tuple[DType, ...]:
    """128-bit integer descriptors, which span several M registers."""

    return tuple(
        dtype
        for dtype in machine.semantic_dtypes
        if dtype.bits == 128
        and "_SAT_" not in dtype.name
        and not dtype.name.startswith(_FLOAT_PREFIXES)
    )


def _select_packed_integer(machine: "MachineConfig") -> tuple[DType, ...]:
    """Integer descriptors stored narrower than one UDS, so several pack per row."""

    return tuple(
        dtype for dtype in _plain_integer(machine.formed_dtypes) if dtype.bits < machine.uds
    )


def _select_packed_conversion(machine: "MachineConfig") -> tuple[DType, ...]:
    """The narrower storage descriptor of each packed conversion pair.

    A packed conversion instruction reads or writes a descriptor stored at half
    the active UDS and widens or narrows it to its same-signedness twin at the
    full UDS.  The pair is identified by its storage half, and a storage
    descriptor without a twin is not a pair at all, so it is left out.
    """

    available = {dtype.name for dtype in machine.dtypes}
    return tuple(
        dtype
        for dtype in machine.dtypes
        if dtype.bits * 2 == machine.uds
        and dtype.name in {f"AME_UINT{dtype.bits}_DTYPE", f"AME_INT{dtype.bits}_DTYPE"}
        and f"AME_{'INT' if dtype_is_signed_int(dtype.name) else 'UINT'}{machine.uds}_DTYPE"
        in available
    )


def _select_softfloat(machine: "MachineConfig") -> tuple[DType, ...]:
    """Floating-point descriptors with a covered IEEE/OCP bit layout."""

    return tuple(
        dtype
        for dtype in machine.semantic_dtypes
        if (dtype.name, dtype.bits) in _SOFTFLOAT_DESCRIPTORS
    )


def _select_formed_saturating_integer(machine: "MachineConfig") -> tuple[DType, ...]:
    """Saturating integer descriptors, packed or whole.

    The elementwise saturating template sweeps every saturating integer a *formed*
    operand may use, which includes the sub-UDS descriptors that packing unlocks.
    """

    return _saturating_integer(machine.formed_dtypes)


def _select_formed_softfloat(machine: "MachineConfig") -> tuple[DType, ...]:
    """Floating-point descriptors a *formed* operand may use.

    The float-math and elementwise families select their floating-point coverage
    from the formed descriptors, which keeps an 8-bit OCP format in play at a
    16-bit UDS: there it is a packed storage format rather than a whole register.
    """

    return tuple(
        dtype
        for dtype in machine.formed_dtypes
        if (dtype.name, dtype.bits) in _SOFTFLOAT_DESCRIPTORS
    )


def _select_signed_packed_source(machine: "MachineConfig") -> tuple[DType, ...]:
    """The signed descriptor stored at half the active UDS.

    The mixed-signedness template pairs this descriptor with its unsigned twin to
    build two physically packed source squares.
    """

    wanted = f"AME_INT{machine.uds // 2}_DTYPE"
    return tuple(dtype for dtype in machine.formed_dtypes if dtype.name == wanted)


def _select_every_dtype(machine: "MachineConfig") -> tuple[DType, ...]:
    """Every descriptor the macro file declares, unfiltered.

    Descriptor roundtrip instructions do not form operands, so no storage ratio
    applies: they must accept exactly the set the assembler knows.
    """

    return machine.dtypes


def _select_probe_dtype(machine: "MachineConfig") -> tuple[DType, ...]:
    """The descriptor an unsupported-datatype probe seeds a register with."""

    return tuple(
        dtype for dtype in machine.dtypes if dtype.name == _UNSUPPORTED_PROBE_DTYPE
    )


INTEGER = DTypeDomain(
    "integer",
    "non-saturating integers formed as whole M registers",
    "以整个 M 寄存器形成的非饱和整数",
    _select_integer,
)
def _select_extra_permute(machine: "MachineConfig") -> tuple[DType, ...]:
    """Full-width descriptors that are not plain integers.

    The zip and gather instructions need two or three *distinct* register
    groups, so they run the saturating and floating descriptors rather than the
    plain integers the other groups already cover.
    """

    plain = set(INTEGER(machine))
    return tuple(
        dtype
        for dtype in machine.semantic_dtypes
        if dtype.bits >= machine.uds and dtype not in plain
    )


EXTRA_PERMUTE = DTypeDomain(
    "extra_permute",
    "full-width non-integer descriptors",
    "满宽度的非整数描述符",
    _select_extra_permute,
)
STRIDED_STORAGE = DTypeDomain(
    "strided_storage",
    "sub-UDS descriptors a strided transfer packs into one register",
    "跨步传输可打包进一个寄存器的亚 UDS 描述符",
    _select_strided_storage,
)
STRIDED_CONVERSION = DTypeDomain(
    "strided_conversion",
    "the storage half of each conversion pair, unsigned before signed",
    "每个转换对的存储侧，无符号在前、有符号在后",
    _select_strided_conversion,
)
SEMANTIC = DTypeDomain(
    "semantic",
    "every descriptor forming a whole-register operand at this UDS",
    "在当前 UDS 下形成整寄存器操作数的每个描述符",
    _select_semantic,
)
PACKED_STORAGE = DTypeDomain(
    "packed_storage",
    "every descriptor stored at half the active UDS",
    "存储在有效 UDS 一半处的每个描述符",
    _select_packed_storage,
)
SATURATING_INTEGER128 = DTypeDomain(
    "saturating_integer128",
    "128-bit saturating integers",
    "128 位饱和整数",
    _select_saturating_integer128,
)
FORMED_INTEGER = DTypeDomain(
    "formed_integer",
    "non-saturating integers formed packed or whole",
    "以打包或整寄存器形式形成的非饱和整数",
    _select_formed_integer,
)
INTEGER128 = DTypeDomain(
    "integer128",
    "128-bit integers spanning several M registers",
    "跨越多个 M 寄存器的 128 位整数",
    _select_integer128,
)
SATURATING_INTEGER = DTypeDomain(
    "saturating_integer",
    "saturating integers formed as whole M registers",
    "以整个 M 寄存器形成的饱和整数",
    _select_saturating_integer,
)
PACKED_INTEGER = DTypeDomain(
    "packed_integer",
    "integers stored narrower than the active UDS",
    "存储宽度小于有效 UDS 的整数",
    _select_packed_integer,
)
PACKED_CONVERSION = DTypeDomain(
    "packed_conversion",
    "the storage half of each packed-storage/widened-compute pair",
    "每个打包存储/加宽计算对的存储侧",
    _select_packed_conversion,
)
SOFTFLOAT = DTypeDomain(
    "softfloat",
    "IEEE/OCP floating-point formats",
    "IEEE/OCP 浮点格式",
    _select_softfloat,
)
FORMED_SATURATING_INTEGER = DTypeDomain(
    "formed_saturating_integer",
    "saturating integers formed packed or whole",
    "以打包或整寄存器形式形成的饱和整数",
    _select_formed_saturating_integer,
)
FORMED_SOFTFLOAT = DTypeDomain(
    "formed_softfloat",
    "softfloat descriptors usable as a formed operand",
    "可作为成形操作数使用的 softfloat 描述符",
    _select_formed_softfloat,
)
SIGNED_PACKED_SOURCE = DTypeDomain(
    "signed_packed_source",
    "the signed integer at half the active UDS",
    "有效 UDS 一半处的有符号整数",
    _select_signed_packed_source,
)
EVERY_DTYPE = DTypeDomain(
    "every_dtype",
    "every datatype descriptor the macro file declares",
    "宏文件声明的每个 datatype 描述符",
    _select_every_dtype,
)
PROBE_DTYPE = DTypeDomain(
    "probe_dtype",
    "the descriptor an unsupported-datatype probe seeds a register with",
    "不支持 datatype 探测用于播种寄存器的描述符",
    _select_probe_dtype,
)

ALL_DOMAINS = (
    SEMANTIC,
    STRIDED_STORAGE,
    STRIDED_CONVERSION,
    INTEGER,
    INTEGER128,
    SATURATING_INTEGER,
    SATURATING_INTEGER128,
    PACKED_INTEGER,
    PACKED_CONVERSION,
    PACKED_STORAGE,
    FORMED_INTEGER,
    FORMED_SATURATING_INTEGER,
    EXTRA_PERMUTE,
    SOFTFLOAT,
    FORMED_SOFTFLOAT,
    SIGNED_PACKED_SOURCE,
    EVERY_DTYPE,
    PROBE_DTYPE,
)


@dataclass(frozen=True)
class MachineConfig:
    """One N/UDS/M/ACC generation pass."""

    dtypes: tuple[DType, ...]
    n: int = 8
    uds: int = 8
    num_m_regs: int = 32
    num_acc_regs: int = 4

    def __post_init__(self) -> None:
        if self.n <= 0:
            raise ValueError(f"invalid matrix dimension N: {self.n}")
        if self.uds <= 0:
            raise ValueError(f"invalid unit datatype size: {self.uds}")
        if self.num_m_regs <= 0:
            raise ValueError(f"invalid M-register file size: {self.num_m_regs}")
        if self.num_acc_regs <= 0:
            raise ValueError(f"invalid accumulator file size: {self.num_acc_regs}")

    @property
    def nelem(self) -> int:
        """Elements in one logical square."""

        return self.n * self.n

    @property
    def semantic_dtypes(self) -> tuple[DType, ...]:
        """Descriptors with an integral whole-register storage ratio."""

        return tuple(
            dtype
            for dtype in self.dtypes
            if dtype.bits >= self.uds and dtype.bits % self.uds == 0
        )

    @property
    def formed_dtypes(self) -> tuple[DType, ...]:
        """Descriptors that a formed operand may use, packed or whole."""

        return tuple(
            dtype
            for dtype in self.dtypes
            if (dtype.bits < self.uds and self.uds % dtype.bits == 0)
            or (dtype.bits >= self.uds and dtype.bits % self.uds == 0)
        )

    def nregs(self, element_bits: int) -> int:
        """M registers spanned by one formed operand of ``element_bits``."""

        if element_bits <= 0:
            raise ValueError(f"element width must be positive, got {element_bits}")
        return max(1, element_bits // self.uds)

    def square_bytes(self, element_bits: int) -> int:
        """Memory footprint of one dtype-formed square."""

        return self.nelem * max(element_bits, self.uds) // 8

    def storage_elements(self, element_bits: int) -> int:
        """Physical elements in one formed square, including packing."""

        if element_bits <= 0:
            raise ValueError(f"element width must be positive, got {element_bits}")
        pack_factor = (
            max(1, self.uds // element_bits) if element_bits < self.uds else 1
        )
        return self.nelem * pack_factor


__all__ = [
    "ALL_DOMAINS",
    "EXTRA_PERMUTE",
    "FORMED_SOFTFLOAT",
    "PACKED_STORAGE",
    "SATURATING_INTEGER128",
    "FORMED_INTEGER",
    "FORMED_SATURATING_INTEGER",
    "DType",
    "DTypeDomain",
    "EVERY_DTYPE",
    "INTEGER",
    "INTEGER128",
    "MachineConfig",
    "PACKED_CONVERSION",
    "PACKED_INTEGER",
    "PROBE_DTYPE",
    "SATURATING_INTEGER",
    "SIGNED_PACKED_SOURCE",
    "SOFTFLOAT",
    "dtype_is_signed_int",
    "dtype_stem",
]
