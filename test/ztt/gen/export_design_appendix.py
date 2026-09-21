#!/usr/bin/env python3
#
# Copyright (c) Qualcomm Technologies, Inc. and/or its subsidiaries.
# SPDX-License-Identifier: BSD-3-Clause-Clear
#
"""Export the generated tables and appendices of the Ztt test design document.

The script reads the generator's own declarations (``mmul_gen/catalog.py``,
``mmul_gen/machine.py``, ``mmul_gen/templates/``, ``mmul_gen/instructions/``)
and one real generation pass, then writes:

* ``doc/Ztt测试设计文档V0.2.dev20260922.md`` -- the main document, whose
  instruction tables and appendices are regenerated in place;
* ``doc/Ztt测试设计文档附录数据V0.2.dev20260922.md`` -- the definition-level
  data appendix (template x datatype) with real assembly excerpts.

Every number, datatype name, template name, and assembly line in the generated
regions comes from the generator or from the generated ``.S`` sources.  The
script is deterministic and idempotent: running it twice yields identical
files.  It fails loudly (naming the offending module, template, instruction,
or case) rather than emitting a placeholder.

Usage (from the repository root or from this directory)::

    python3 sail-ame/test/ztt/gen/export_design_appendix.py
    python3 export_design_appendix.py            # cwd = sail-ame/test/ztt/gen
"""

from __future__ import annotations

import argparse
import ast
import inspect
import json
import re
import sys
import tempfile
import types
from collections import OrderedDict, defaultdict
from dataclasses import dataclass, fields, is_dataclass, replace
from pathlib import Path

# Importing the generator must not leave bytecode caches in the source tree.
sys.dont_write_bytecode = True

SCRIPT_PATH = Path(__file__).resolve()
GEN_DIR = SCRIPT_PATH.parent
REPO_ROOT = GEN_DIR.parents[3]
if str(GEN_DIR) not in sys.path:
    sys.path.insert(0, str(GEN_DIR))

from mmul_gen.asm import asm_header  # noqa: E402
from mmul_gen.catalog import ALL_INSTRUCTIONS, INSTRUCTION_FAMILIES  # noqa: E402
from mmul_gen.instruction import Instruction  # noqa: E402
from mmul_gen.macros import parse_dtypes  # noqa: E402
from mmul_gen.machine import ALL_DOMAINS, DTypeDomain, MachineConfig  # noqa: E402
from mmul_gen.templates.base import CaseOutput, Template  # noqa: E402

TEST_DIR = GEN_DIR.parent
if str(TEST_DIR) not in sys.path:
    sys.path.insert(0, str(TEST_DIR))

import run_ztt_tests  # noqa: E402

TEMPLATES_DIR = GEN_DIR / "mmul_gen" / "templates"
CATALOG_PATH = GEN_DIR / "mmul_gen" / "catalog.py"
DEFAULT_MACRO_FILE = GEN_DIR.parent / "src" / "ame_macros.inc"
MAIN_DOC = REPO_ROOT / "doc" / "Ztt测试设计文档V0.2.dev20260922.md"
DATA_DOC = REPO_ROOT / "doc" / "Ztt测试设计文档附录数据V0.2.dev20260922.md"

#: The single source of the Chinese rendering of every manual instruction
#: block.  One entry per manual mnemonic; a missing or empty entry fails rather
#: than falling back to the English manual text.
MANUAL_ZH_PATH = REPO_ROOT / "doc" / "instruction_manual_zh.json"

#: The authoritative manual.  The narrative blocks of section 4 are read from
#: these files at generation time; no manual fact is transcribed by hand.
MANUAL_SRC = REPO_ROOT / "riscv-attached-matrix-extension" / "src"
MANUAL_INSTRUCTIONS = MANUAL_SRC / "instructions.adoc"
MANUAL_ENCODING = MANUAL_SRC / "instruction-encoding-allocations.adoc"

#: Chinese gloss of each common-rule section an instruction may cite.  The
#: anchors are read from the manual; these sentences state the cited rule's
#: requirements in the document's language, once, for every instruction that
#: cites it.  A cited rule with no gloss fails rather than appearing as English
#: prose in the document.
_COMMON_RULE_ZH = {
    "ame-common-matmul": (
        "公共规则要求：每个逻辑源方阵为 `N × N`，两个源操作数的第 `s` 个方阵按 "
        "`A[s]`/`B[s]` 配对，累加器是一个 `N × N` 方阵，因此每个输出元素折叠 "
        "`N_sq × N` 个标量乘积；转置在每个配对方阵内生效。实现为每个输出元素取 "
        "`(s,q)` 项的一个固定且确定的排列，以指令执行前的累加器元素播种，并按该顺序"
        "逐个加（或减）乘积，不先单独归约乘积；接受的 tuple 决定带类型的乘法与累加。"
        "寄存器编码不得作为无类型位向量累加，折叠也不得隐式以零播种。实现须文档化其"
        "溢出、饱和、浮点舍入与可选融合乘积行为，并对该 tuple 保持确定性。"
    ),
    "ame-common-arithmetic": (
        "公共规则要求：`Operation` 对操作数成形所选出的每个方阵的每个逻辑元素独立"
        "生效。标准整数算术在数学表达式求值时不中途截断，最后按目的整数 datatype "
        "只转换一次：饱和目的越界即钳位到 `[min,max]` 并置 `amexsat.SAT`，非饱和目的"
        "保留目的宽度的低位。`mhdiff.ew`、`mhdiff.ew.x`、`mmean.ew`、`mmean.ew.x` 在"
        "该转换前按公共标准整数舍入规则对目的 LSB 以下的小数位舍入。"
        "`mexp2.ew`、`mlog2.ew`、`mcos.ew`、`msin.ew`、`mtanh.ew`、`mrec.ew`、"
        "`mrsqrt.ew`、`msqrt.ew` 与 `mfrint*.ew` 家族要求标准浮点源与目的 datatype；"
        "标准浮点运算按目的 datatype 选择舍入（AME 没有全局动态舍入模式），把 IEEE "
        "五类异常标志累积进 `amefflags` 而不修改 `fflags`，并按原子寄存器写回规则 OR "
        "进 `amefflags`；NaN 输入或非法运算产生目的 datatype 的规范静默 NaN，"
        "浮点异常是数据结果，不陷入也不置 `amestatus.UN`。"
    ),
    "ame-common-scalar-operands": (
        "公共规则要求：数据标量 `.ew.x` 指令的 `scalar_dtype = CSR[amestype]`，所需 "
        "tuple 包含 `Md[md]`、`Md[ms2]` 与 `scalar_dtype`，任一描述符为零、未知或不"
        "支持即 tuple 不支持。XLEN 不小于标量宽度时取 X 寄存器操作数的低 "
        "`sizeof(scalar_dtype)` 位并忽略高位，宽度超过 XLEN 时把 X 寄存器位模式零扩展"
        "到该宽度；按 `scalar_dtype` 解释该位串并转换到 `Md[ms2]`，`Operation` 以转换"
        "结果作为 `c`，再把自身结果按适用家族规则转换到 `Md[md]`；精确 tuple 未定义该"
        "标量到 `Md[ms2]` 的转换即 tuple 不支持。控制标量（索引、偏移、移位量、跨度、"
        "打包槽选择）是其指令定义的整数，不使用 `amestype`，也不经过 AME datatype 转换。"
    ),
    "ame-common-register-groups": (
        "公共规则要求：一条计算指令引用的所有张量操作数必须含相同的方阵总数，"
        "指令的方阵数 `N_sq = max(pack_factor)`；打包操作数（`pack_factor > 1`）占 "
        "`N_sq / pack_factor` 个寄存器，单元或宽操作数（`pack_factor = 1`）占 "
        "`N_sq × ceil(sizeof(dtype) / AME_UNIT_DATATYPE_SIZE)` 个寄存器。宽操作数的每"
        "个逻辑方阵须由完整连续的 M 寄存器组拼出，逻辑元素位置不得由截断到单个物理 "
        "M 寄存器的元素计数导出。累加器（`Acc`）操作数不受该规则约束，恒为一个方阵。"
        "`mpack.ew.x` 与 `munpack.ew.x` 以及 `mcolunzip.ew`、`mcolzip.ew`、"
        "`mrowunzip.ew`、`mrowzip.ew` 是显式固定形态例外，其指令自身规则优先于 "
        "`N_sq = max(pack_factor)`；四个 zip/unzip 指令的 `ms1` 与 `ms2` 必须命名不同"
        "的 M 寄存器，相同即在校验任何寄存器读写前触发非法指令异常。普通 1D 逐元素"
        "指令的逻辑元素数为 `N_sq × AME_NELEM`，`Operation` 在该整个范围上生效。"
    ),
    "ame-common-memory": (
        "公共规则要求：AME 与宿主 hart 共用地址空间，访存经与普通 RISC-V 访存相同的"
        "地址翻译、保护、物理内存属性与访问错误检查。元素按 `E` 位字段背靠背打包，"
        "字段间不插字节填充；最低地址字节含 bits 7:0，末尾字段未落在字节边界时加载"
        "忽略该字节未用的高位、存储把未用高位写零。行/列主序互操作传输的完整位串含 "
        "`P × AME_NELEM × E` 位、`total_bytes = ceil(P × AME_NELEM × E / 8)`，打包方阵"
        "按槽号升序、方阵内按指令声明的行主或列主序排列。跨步传输的段地址为 "
        "`(base + seg × stride) mod 2^XLEN`，每段是独立按字节取整的位串：`.st` 有 `N` "
        "段、每段 `P × N × E` 位，`.tst` 有 `P × N` 段、每段 `N × E` 位。跨步存储允许"
        "段地址范围重叠（含 `stride = 0`），最终内存镜像按段号升序、段内字节偏移升序"
        "叠加，后写字节覆盖先写字节；该顺序只决定叠加结果，不允许部分完成：任一段访问"
        "出错则不写入任何已暂存字节。`mls.1r` 与 `mss.1r` 固定 `E = "
        "AME_UNIT_DATATYPE_SIZE`、`P = 1`，其内存镜像是 `mss.rm` 对单元 datatype 的"
        "结果，不依赖实现的物理寄存器内部排布。"
    ),
    "ame-common-state-access": (
        "公共规则要求：任一适用的 `MS` 域为 Off 时，所有 AME 指令（含 `ame.acquire` "
        "与 `ame.release`）以及所有 AME CSR 的读写都触发非法指令异常；全部适用 `MS` "
        "域非 Off 但 `ameown.OWNED = 0` 时，除 `ame.acquire` 与 `ame.release` 外的所有"
        "AME 指令以及可写 AME 上下文 CSR 的访问都触发非法指令异常，只读能力 CSR 与 "
        "`ameown` 仍可读。`OWNED = 1` 时，试图把任一适用 `MS` 域写为 Off 的 CSR 指令"
        "触发非法指令异常且不改变状态，不发生隐式释放，软件必须先执行 `ame.release`。"
        "这些异常先于其他所有 AME 校验，且不改变任何 AME 状态。"
    ),
}

#: Chinese family names and the one-sentence design of each generator family.
#: The instruction design exporter imports these so both documents describe the
#: same modules.
FAMILY_ZH = {
    "accumulator": "累加器与清零",
    "acc_span": "累加器跨度",
    "axis_permute": "行列置换",
    "backend": "后端所有权",
    "broadcast": "标量广播",
    "debug_move": "调试搬移",
    "elementwise": "逐元素运算",
    "float_math": "浮点数学",
    "integer_shift": "整数移位",
    "load_store": "整寄存器加载存储",
    "logexp": "对数与指数",
    "matrix_ops": "矩阵归约与前缀",
    "mconv": "datatype 转换",
    "memory_order": "内存序与格式",
    "mmul": "矩阵乘",
    "pack": "打包与解包",
    "strided_memory": "跨步访存",
    "type_register": "datatype 寄存器",
}

FAMILY_DESIGN = {
    "accumulator": "清零与搬移类指令只操作寄存器组存储，datatype 描述符仅用于匹配检查；索引与跨度合法性由共享判定单点给出。",
    "acc_span": "累加器跨度类条目在读写前先校验整个跨度的每个派生索引，跨度非法即触发非法指令，不允许部分搬运。",
    "axis_permute": "行列置换类指令按行或列轴重排元素，索引取自 X 寄存器或 `ms2` 元素；不支持 datatype 组合置不支持。",
    "backend": "所有权类指令只依赖扩展与 MS 域使能，不要求已持有后端；`ame.acquire` 返回描述符校验结果，`ame.release` 释放所有权。",
    "broadcast": "广播类指令把 X 寄存器的标量按显式源 datatype 转换一次后写入目的寄存器组的每个元素。",
    "debug_move": "调试搬移类指令以指令自定的元素宽度访问单个物理寄存器，不读 datatype 描述符，也不置不支持状态。",
    "elementwise": "逐元素类指令把两个逻辑方阵（或一个方阵与一个标量）按元素配对，结果按目的 datatype 归一化后写回。",
    "float_math": "浮点数学类指令对浮点元素做一元超越或舍入运算，结果按目的 datatype 舍入并汇总浮点标志。",
    "integer_shift": "整数移位类指令按元素或标量偏移移位，移出位按手册规则处置。",
    "load_store": "整寄存器加载存储类指令以固定元素宽度在内存与单个物理寄存器之间搬运，不读 datatype 描述符。",
    "logexp": "对数与指数类指令按元素计算对数、指数或按幂缩放，复合表达式按手册要求只做一次目的转换。",
    "matrix_ops": "归约、前缀、聚集/散射与打包类指令按行或列轴重排或折叠元素，索引语义与越界处置按手册规定。",
    "mconv": "转换类指令在支持的 datatype 之间逐元素转换，源与目的可以各自是打包或非打包表示。",
    "memory_order": "内存序类指令按行主或列主格式在内存与寄存器组之间搬运，并区分 acquire/release 序。",
    "mmul": "矩阵乘类指令共享同一 R3 指令类型与计算入口，由旗标区分累加、取负与转置形态。",
    "pack": "打包类指令在打包表示与展开表示之间转换元素布局。",
    "strided_memory": "跨步访存类指令按字节步长在内存与寄存器组之间搬运，并可选择在搬运中转置。",
    "type_register": "datatype 寄存器类指令读写 32 位描述符，描述符的合法性由共享判定给出。",
}

DEFAULT_N = 8
DEFAULT_UDS = 8
DEFAULT_M = 32
DEFAULT_ACC = 4

#: How many lines of a real case an appendix excerpt keeps before it says how
#: many lines it dropped.  The omission is counted, never silent.
SNIPPET_LIMIT = 26
DATA_SNIPPET_LIMIT = 12

#: Template instances whose input/expect symbols are classified from the
#: module's imports.
_ASM_ASSERT_PREFIX = "check_"
_ASM_INPUT_HELPERS = frozenset(
    {
        "data_directive",
        "data_element_line",
        "data_element_lines",
        "dst_square_lines",
        "element_byte_values",
        "hex_value",
        "load_byte_lines",
        "pack_nibbles",
        "repeated_square_lines",
        "row_col_values",
        "sign_extend",
        "square_lines",
    }
)
_STIMULUS_MODULES = frozenset({"mmul_gen.inputs"})
_EXPECT_MODULES = frozenset(
    {"mmul_gen.reference", "mmul_gen.float_formats", "numeric_reference"}
)
_SEMANTIC_MODULES = frozenset({"fp_semantics"})

INSTANCE_INSTRUCTIONS = (
    "mmulacc.2d",
    "mmulaccneg.2d",
    "mmulatacc.2d",
    "mmulataccneg.2d",
    "mmulbtacc.2d",
    "mmulbtaccneg.2d",
)


# ---------------------------------------------------------------------------
# Static prose
# ---------------------------------------------------------------------------

STATIC_FRONT = """\
# Ztt 测试设计文档

> 本文档描述 Ztt 自检用例的详细设计：用例的组织与命名、指令从声明到发射的完整路径、期望值来源与判定方式、冻结基线与回归。

## 1 术语和省略词

| 术语 | 含义 |
| --- | --- |
| 配置参数 | N（`AME_NELEM` 的平方根）、UDS、M 寄存器数、Acc 寄存器数四个维度 |
| 组合 / combo | 配置参数四个维度各取一个值后得到的具体配置，例如 `n8_u8_m32_a4`，目录名 `n{n}_u{uds}_m{m}_a{acc}` |
| 指令声明 | `instructions/` 下描述一条指令的类：名字、摘要、操作数、`templates` 元组 |
| 模板 / template | `templates/` 下的一个发射模块，负责一类模板集合的汇编渲染与期望值计算 |
| 模板集合 / template_set | 一个模板在一次运行中负责的用例集合，决定 `.data` 布局与检查序列 |
| 期望值 | 生成期算好、内嵌进 `.S` 的预期结果，运行时由用例自检 |
| 冻结基线 | `tests/golden_sources.json` 中记录的发射哈希 |
| 自检 | `EXPECT` 宏：比较寄存器与期望值，不等即失败停机 |
| 目标模拟器 | 运行自检汇编的被测实现 |
| 生成清单 | `mmul_gen/catalog.py` 中的有序家族清单与生成循环 |

编码与指令名以手册为准；生成器中的指令名与手册 mnemonic 一致（`mmulacc.2d`），源文件名由 mnemonic 转写而来（`mmulacc_2d.S`）。

## 2 参考文档

| 文档 | 用途 |
| --- | --- |
| `riscv-attached-matrix-extension/src/instructions.adoc` | 指令语义、编码与操作定义（权威） |
| `riscv-attached-matrix-extension/src/parameters.adoc` | 几何参数与取值域（权威） |
| `gen/mmul_gen/README.md` | 生成器总体设计 |
| `gen/mmul_gen/instructions/README.md` | 一条指令如何声明自己 |
| `gen/mmul_gen/templates/README.md` | 模板的检查机制与取舍 |
| `doc/Ztt测试架构设计文档V0.2.dev20260922.md` | 测试体系总体设计 |

## 3 概述引言

### 3.1 软件产品规格

| 维度 | 说明 |
| --- | --- |
| 目标 | 以确定性期望约束目标模拟器 |
| 范围 | 指令 × datatype × 几何参数（N/UDS/M/ACC）的组合覆盖与自检 |
| 产物 | 内嵌期望值、通过后停机的自检汇编，以及运行汇总报告 |

自检汇编不依赖外部金标准文件：期望值在生成期算好并写进 `.S`，运行时用例自己比较并在不一致时报告失败，因此同一份用例可以在不同实现上原样运行。

### 3.2 软件功能简述

#### 3.2.1 用例组织与命名

```text
输出根目录/
  n8_u8_m32_a4/            # combo 目录，与运行时 JSON 同名
    mmulacc_2d.S           # 每条指令一个自检汇编源
    mmulaccneg_2d.S
    ...
    <combo>.json           # 运行时配置（由 cfg 模板渲染）
```

#### 3.2.2 汇编骨架

每个源文件共用同一骨架，宏定义在 `src/test.inc` 与 `src/ame_macros.inc`：

| 结构 | 作用 |
| --- | --- |
| 归属注释 | 首行注明生成器路径，冻结基线比对时归一化掉 |
| `.include "test.inc"` / `"ame_macros.inc"` | 自检宏与 datatype 常量 |
| `.text` | 用例主体：设置 datatype、搬运数据、执行、检查 |
| `.data` | 输入方阵与期望方阵（footer，由家族声明共享）；公共期望方阵以 `0xa5` 预填，用于暴露越界覆写 |

#### 3.2.3 判定与退出

```text
EXPECT reg, expected   ->  li t6, expected; beq reg, t6, ok; RVMODEL_HALT_FAIL
TRAP_GUARD_ARM         ->  安装陷阱处理器并把 s11 计数器清零
EXPECT_TRAP count      ->  EXPECT s11, count   # 被守护指令应产生的陷阱数
```

`EXPECT` 定义于 `src/test.inc:45`：任何一处不等即跳 `RVMODEL_HALT_FAIL`（向 `tohost` 写 3）；全部通过后走 `RVMODEL_HALT_PASS` 正常结束。非法指令用例不靠“跑过去”判定，而由陷阱守护宏计数，处理器遇到非非法指令原因的陷阱直接失败。

#### 3.2.4 配置参数与合法性

四个维度的合法值域集中在 `gen/matrix_geometry.py`，三个命令行入口共用同一套校验：

| 配置参数 | 合法值 | 默认扫描 |
| --- | --- | --- |
| N | 2 的幂，无上界（手册只要求 `AME_NELEM` 为 4 的幂） | 4 / 8 / 16 / 32 |
| UDS | 2 的幂且 ≥ 8 | 8 / 16 / 32 |
| M 寄存器数 | 16 / 32 | 16 / 32 |
| Acc 寄存器数 | 1 / 2 / 4 / 8 / 16 | 1 / 2 / 4 / 8 / 16 |

默认即全量（120 组合）；用户可用 `--n/--uds/--m/--acc` 传逗号分隔的子集。N 的上界只受实现配置约束，例如 `cfg/rv64-ztt-16k-8.yaml` 的 `AME_NELEM: 16384` 对应 N=128。

### 3.3 竞品产品分析

| 维度 | 本体系的定位 |
| --- | --- |
| 判定位置 | 期望值内嵌在用例中，判定不依赖外部金标准文件 |
| 期望值来源 | 生成期独立参考计算，与被测实现不同源 |
| 覆盖驱动 | 由覆盖计划与模板声明驱动，逐指令、逐 datatype、逐几何组合成套生成 |
| 字节级约束 | 以冻结发射哈希锁定发射结果，模板改动影响发射即失败 |

本体系把期望值与覆盖计划解耦：同一套生成逻辑适配不同几何组合，判定基准独立于被测实现产生。

## 4 软件架构

### 4.1 功能模块

| 环节 | 位置 | 作用 |
| --- | --- | --- |
| 测试驱动 | `run_ztt_tests.py` | 组合选择、运行时配置渲染、交叉编译、运行与汇总 |
| 覆盖计划 | `gen/mmul_gen/catalog.py` | 有序的指令清单（`INSTRUCTION_FAMILIES`）与生成循环 |
| 指令生成 | `gen/mmul_gen/instructions`、`gen/mmul_gen/templates` | 每条指令一个声明模块，每个模板一个发射模块 |
| 期望值 | `gen/numeric_reference.py`、`gen/fp_semantics.py` | 生成期确定性参考（精确整数算式 / 浮点边界与舍入） |
| 取值域 | `gen/matrix_geometry.py` | 三个 CLI 共用的合法值与默认扫描轴，唯一权威 |
| 冻结基线 | `gen/mmul_gen/tests/golden_sources.json` | 5 种配置 701 个源的发射哈希 |
| 手册同步 | `gen/check_manual_sync.py` | 手册 ↔ GAS 宏 ↔ 模型 三者指令名一致性检查 |
| 模型/宏重生成 | `test/ztt/CMakeLists.txt` | 由手册快照重生成模型与 GAS 宏；不负责用例矩阵 |
| 手工回归 | `regression/` | 针对特定缺陷的单点确定性用例，不依赖重新生成 |

生成器是仓库中唯一的实现：它不依赖任何第二份生成器；字节级基线以冻结哈希的形式独立存在（见第 7 章）。

### 4.2 系统流程

```text
配置参数 (--n/--uds/--m/--acc)
  -> 组合选择 all_combos -> combo_name(n{u}_u{uds}_m{m}_a{acc})
  -> 运行时配置渲染 render_config(yaml 模板 -> 每组合 JSON)
  -> 生成器 mmul_gen(catalog -> instructions -> templates)
  -> 自检汇编 .S（内嵌期望值，自检失败即报错退出）
  -> 交叉编译 riscv64-unknown-elf-gcc
  -> 运行目标模拟器
  -> 退出码判定 -> 汇总报告
```

组合由 `run_ztt_tests.py:82 all_combos` 生成，命名由 `run_ztt_tests.py:97 combo_name` 决定；生成结果按目录缓存，`run_ztt_tests.py:121 generate_one` 只在目录不存在或无 `.S` 时重新生成。每个组合独占一个输出目录与一份运行时 JSON，二者按 `combo_name` 一一对应。

运行时配置由 `run_ztt_tests.py:102 render_config` 渲染：对 `cfg/*.yaml` 模板做 4 处正则替换（`log2(N)`、`log2(UDS)`、M 个数、Acc 个数），每条模式必须命中恰好一次，未命中即失败。

## 5 软件模块

本章按生成清单的 18 个家族组织；每个模块给出设计方案、软件接口、复用性与兼容性，随后逐条给出指令的手册要求、手册操作定义、编码、公共规则、生成路径、判定、不覆盖与已知边界以及覆盖表。每条指令的手册要求、操作伪代码与编码取自 `riscv-attached-matrix-extension/src/instructions.adoc` 与 `riscv-attached-matrix-extension/src/instruction-encoding-allocations.adoc`；生成路径、判定与不覆盖边界取自生成器声明与真实生成产物。附录 A（模板）与附录 B（输入数据）在第 7 章之后，分别给出模板模块索引与逐 datatype 的输入构造。
"""

STATIC_BACK = """\
## 7 软件可测性

### 7.1 期望值策略

| 类别 | 生成期来源 | 交叉校验 |
| --- | --- | --- |
| 整数 / 打包 / 混合符号 | `reference.py` → `numeric_reference.integer_matmul` 的精确整数算式 | NumPy 路径与纯 Python 循环路径必须一致，不一致即 `AssertionError` |
| 饱和 | 上式 + 钳位到 `[min,max]` | 与状态位期望一并检查 |
| 浮点 | `fp_semantics` 边界编码 + 舍入语义 | 边界值取自共享表，不依赖 NumPy |
| datatype / 状态 | 写入后读回的 roundtrip | 状态转移期望独立列出 |
| 搬运 / 布局 | 按目标布局推导的字节位置 | 哨兵区防越界覆写 |

期望值在生成期算出后**内嵌**进汇编，运行时不再依赖外部金标准；因此同一份 `.S` 可以原样跑在不同实现上，差异会被同一组检查点暴露。

### 7.2 冻结基线与回归

| 机制 | 位置 | 作用 |
| --- | --- | --- |
| 发射哈希 | `mmul_gen/tests/golden_sources.json` | 5 种配置、701 个源的 SHA-256（归一化归属注释） |
| 哈希检查 | `mmul_gen/tests/test_golden_sources.py` | 模板改动一旦影响发射结果即失败 |
| 生成器自测 | `python3 -m mmul_gen.tests` | 清单、数据类型域、寄存器布局、端到端渲染、标签唯一性 |
| 伞形入口 | `python3 -m tests`（在 `gen/`） | 共享参考模块测试 + 委派生成器自测 |
| 手工回归 | `regression/` | 已修问题的单点确定性用例，不依赖重新生成 |
| 手册同步 | `gen/check_manual_sync.py` | 手册 `instructions.json` ↔ GAS 宏 ↔ 模型 `execute` 的指令名集合一致 |

生成器与手册之间的机械链只有一条：`manual-main/instructions.json` → `generators/gen_ztt_macros.rb` → `src/ame_macros.inc` → `macros.parse_dtypes` → `MachineConfig.dtypes`。`check_manual_sync.py` 校验手册、宏与模型三者的指令名集合；catalog 的家族与助记符清单不在这条链上，由生成器自测与冻结哈希约束。`parameters.adoc` 目前只被文档引用，没有代码读取。

### 7.3 可测性手段

| 手段 | 说明 |
| --- | --- |
| 自判定用例 | 期望值内嵌进 `.S`，运行时自比对，不一致即 `RVMODEL_HALT_FAIL` |
| 组合参数化 | 同一套用例适配不同几何组合，非法取值在解析阶段被拒绝 |
| 逐指令覆盖表 | 第 5 章逐条给出模板、datatype 域、输入模式、expect 规则与 case 数 |
| 陷阱守护 | 需要异常路径的用例以 `EXPECT_TRAP` 守护非法指令 |
| 手工回归 | `regression/` 针对特定缺陷的单点确定性用例，不依赖重新生成 |
| 模板与输入数据 | 附录 A 给出模板模块索引，附录 B 给出逐 datatype 的输入构造与真实汇编片段 |

各指令的测试目标、覆盖数据点与流程见第 5 章；逐 datatype 的输入构造与真实汇编片段见附录 A 与附录 B。
"""


# ---------------------------------------------------------------------------
# Fail-fast helper
# ---------------------------------------------------------------------------


def fail(message: str) -> None:
    raise RuntimeError(message)


def require_chinese(value: str, what: str) -> str:
    """The Chinese description of one generator declaration, or a hard failure.

    There is deliberately no fallback to the English field: a missing Chinese
    description is a defect in the declaration, not something the exporter may
    paper over with a placeholder or with the text the document must not show.
    """

    text = value.strip()
    if not text:
        fail(f"{what} has no Chinese description; declare its summary_zh")
    return text


# ---------------------------------------------------------------------------
# Source introspection
# ---------------------------------------------------------------------------


def module_path_to_name(path: Path) -> str:
    relative = path.resolve().relative_to(GEN_DIR)
    return ".".join(relative.with_suffix("").parts)


@dataclass(frozen=True)
class ModuleFacts:
    """AST facts about one template module, read without importing it."""

    path: Path
    name: str
    docstring: str
    doc_zh: str
    imports: dict[str, tuple[str, ...]]
    classes: tuple[str, ...]
    functions: tuple[str, ...]


def read_module_facts(path: Path) -> ModuleFacts:
    text = path.read_text(encoding="utf-8")
    tree = ast.parse(text)
    doc = ast.get_docstring(tree)
    if doc is None or not doc.strip():
        fail(f"module {path} has no docstring; every template module must document itself")
    doc_zh = module_doc_zh(tree, path)
    imports: dict[str, list[str]] = defaultdict(list)
    classes: list[str] = []
    functions: list[str] = []
    for node in tree.body:
        if isinstance(node, ast.ImportFrom) and node.module:
            for alias in node.names:
                imports[node.module].append(alias.name)
        elif isinstance(node, ast.ClassDef):
            classes.append(node.name)
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            functions.append(node.name)
    return ModuleFacts(
        path=path,
        name=module_path_to_name(path),
        docstring=doc.strip(),
        doc_zh=doc_zh,
        imports={key: tuple(value) for key, value in imports.items()},
        classes=tuple(classes),
        functions=tuple(functions),
    )


def module_doc_zh(tree: ast.Module, path: Path) -> str:
    """The module's Chinese description, declared as ``DOC_ZH``.

    The English docstring stays the module's own documentation; ``DOC_ZH`` is
    the design document's only source for the module's Chinese description, so
    the two cannot drift into a translation table kept beside them.
    """

    for node in tree.body:
        if not isinstance(node, ast.Assign):
            continue
        if not any(
            isinstance(target, ast.Name) and target.id == "DOC_ZH"
            for target in node.targets
        ):
            continue
        if not isinstance(node.value, ast.Constant) or not isinstance(node.value.value, str):
            fail(f"{path}: DOC_ZH must be a string literal")
        value = node.value.value.strip()
        if not value:
            fail(f"{path}: DOC_ZH is empty")
        return value
    fail(f"{path}: module must declare a Chinese description in DOC_ZH")
    raise AssertionError("unreachable")


def build_module_facts() -> dict[str, ModuleFacts]:
    paths = sorted(TEMPLATES_DIR.glob("*.py"))
    if not paths:
        fail(f"no template modules found under {TEMPLATES_DIR}")
    facts = [read_module_facts(path) for path in paths]
    return {fact.name: fact for fact in facts}


def build_import_graph(facts: dict[str, ModuleFacts]) -> dict[str, set[str]]:
    """Template-module -> template-modules it imports (for helper closure)."""

    known = set(facts)
    return {
        name: {module for module in fact.imports if module in known}
        for name, fact in facts.items()
    }


def importing_modules(graph: dict[str, set[str]], target: str) -> list[str]:
    """Every module that reaches ``target`` directly or transitively."""

    found: set[str] = set()
    frontier = {target}
    while frontier:
        current = frontier.pop()
        for module, imports in graph.items():
            if module in found or module == target:
                continue
            if current in imports:
                found.add(module)
                frontier.add(module)
    return sorted(found)


# ---------------------------------------------------------------------------
# Stable, compact rendering of generator values
# ---------------------------------------------------------------------------


def stable_repr(value: object, depth: int = 0) -> str:
    """A deterministic rendering of a generator value (never an address)."""

    if depth > 4:
        return "..."
    if value is None or isinstance(value, (int, float, bool, str)):
        return repr(value)
    if isinstance(value, (types.FunctionType, types.MethodType, types.BuiltinFunctionType)):
        return getattr(value, "__qualname__", repr(value))
    if isinstance(value, tuple):
        return "(" + ", ".join(stable_repr(item, depth + 1) for item in value) + ")"
    if isinstance(value, list):
        return "[" + ", ".join(stable_repr(item, depth + 1) for item in value) + "]"
    if isinstance(value, dict):
        return "{" + ", ".join(
            f"{stable_repr(key, depth + 1)}: {stable_repr(value[key], depth + 1)}"
            for key in sorted(value, key=repr)
        ) + "}"
    if is_dataclass(value) and not isinstance(value, type):
        body = ", ".join(
            f"{field.name}={stable_repr(getattr(value, field.name), depth + 1)}"
            for field in fields(value)
        )
        return f"{type(value).__name__}({body})"
    rendered = repr(value)
    if " at 0x" in rendered:
        fail(
            f"cannot render {type(value).__name__} deterministically: {rendered!r}"
        )
    return rendered


def compact(value: object, max_items: int = 4, depth: int = 0) -> str:
    """A bounded rendering used inside table cells."""

    if depth > 3:
        return "..."
    if value is None or isinstance(value, (int, float, bool, str)):
        return repr(value)
    if isinstance(value, (types.FunctionType, types.MethodType, types.BuiltinFunctionType)):
        return getattr(value, "__qualname__", repr(value))
    if isinstance(value, (tuple, list)):
        items = list(value)
        if len(items) <= max_items:
            return "[" + ", ".join(compact(item, max_items, depth + 1) for item in items) + "]"
        head = ", ".join(compact(item, max_items, depth + 1) for item in items[:max_items])
        return f"[{head}, ... 共 {len(items)} 项]"
    if is_dataclass(value) and not isinstance(value, type):
        body = ", ".join(
            f"{field.name}={compact(getattr(value, field.name), max_items, depth + 1)}"
            for field in fields(value)
        )
        return f"{type(value).__name__}({body})"
    return stable_repr(value, depth)


def param_label(instance: object) -> str:
    """A short, deterministic label for one template instance's parameters."""

    attributes = {
        key: value for key, value in vars(instance).items() if not key.startswith("_")
    }
    if not attributes:
        return ""
    parts = []
    for key, value in attributes.items():
        if isinstance(value, (tuple, list)):
            parts.append(f"{key}={len(value)} 项")
        else:
            rendered = compact(value, max_items=3)
            if len(rendered) > 60:
                rendered = rendered[:57] + "..."
            parts.append(f"{key}={rendered}")
    return ", ".join(parts)


def merged_imports(
    data: DesignData, module_name: str
) -> dict[str, tuple[str, ...]]:
    """Imports of one module plus every template module it reaches.

    A family's template often delegates its data construction or its checks to a
    sibling ``*_common`` module, so the symbols that describe the template are
    the closure of its own imports.
    """

    modules = {module_name}
    frontier = {module_name}
    while frontier:
        current = frontier.pop()
        for module in data.graph.get(current, ()):
            if module not in modules:
                modules.add(module)
                frontier.add(module)
    merged: dict[str, list[str]] = defaultdict(list)
    for module in sorted(modules):
        for source, names in data.facts[module].imports.items():
            merged[source].extend(names)
    return {source: tuple(sorted(set(names))) for source, names in merged.items()}


def stimulus_symbols(imports: dict[str, tuple[str, ...]]) -> tuple[str, ...]:
    names: list[str] = []
    for module in _STIMULUS_MODULES:
        names.extend(imports.get(module, ()))
    return tuple(sorted(set(names)))


def expect_symbols(imports: dict[str, tuple[str, ...]]) -> tuple[str, ...]:
    names: list[str] = []
    for module in _EXPECT_MODULES:
        names.extend(imports.get(module, ()))
    return tuple(sorted(set(names)))


def semantic_symbols(imports: dict[str, tuple[str, ...]]) -> tuple[str, ...]:
    names: list[str] = []
    for module in _SEMANTIC_MODULES:
        names.extend(imports.get(module, ()))
    return tuple(sorted(set(names)))


def asm_symbols(imports: dict[str, tuple[str, ...]]) -> tuple[str, ...]:
    return tuple(sorted(set(imports.get("mmul_gen.asm", ()))))


def input_helper_symbols(imports: dict[str, tuple[str, ...]]) -> tuple[str, ...]:
    return tuple(name for name in asm_symbols(imports) if name in _ASM_INPUT_HELPERS)


def check_helper_symbols(imports: dict[str, tuple[str, ...]]) -> tuple[str, ...]:
    return tuple(name for name in asm_symbols(imports) if name.startswith(_ASM_ASSERT_PREFIX))


# ---------------------------------------------------------------------------
# Case extraction
# ---------------------------------------------------------------------------

_ASSERT_RE = re.compile(r"^\s*(EXPECT|EXPECT_TRAP)\b")
_GUARD_RE = re.compile(r"^\s*(TRAP_GUARD_ARM|TRAP_GUARD_DISARM)\b")
_LABEL_RE = re.compile(r"^([A-Za-z_][A-Za-z0-9_.]*):\s*$")
_LA_RE = re.compile(r"^\s*la\s+\w+,\s*([A-Za-z_][A-Za-z0-9_.]*)\s*$")
_INSN_RE = re.compile(r"^\s*([a-z][a-z0-9_.]*)\s")


@dataclass
class CaseRecord:
    instruction: str
    instruction_file: str
    number: int
    template_name: str
    template_module: str
    template_class: str
    param: str
    domain: str | None
    dtype: str | None
    description: str | None
    layout: str | None
    payload: object
    text_lines: tuple[str, ...]
    data_lines: tuple[str, ...]

    @property
    def assertions(self) -> tuple[str, ...]:
        return tuple(line.strip() for line in self.text_lines if _ASSERT_RE.match(line))


def label_digest(data_lines: tuple[str, ...] | list[str]) -> tuple[tuple[str, str], ...]:
    """One ``(label, body summary)`` pair per labelled data block."""

    blocks: list[tuple[str, list[str]]] = []
    current: tuple[str, list[str]] | None = None
    for line in data_lines:
        match = _LABEL_RE.match(line)
        if match is not None:
            current = (match.group(1), [])
            blocks.append(current)
        elif current is not None and line.strip():
            current[1].append(line.strip())
    digest = []
    for label, body in blocks:
        if not body:
            fail(f"data label {label!r} has an empty body")
        repeated = next((line for line in body if line.startswith(".rept")), None)
        if repeated is not None:
            inner = body[body.index(repeated) + 1] if body.index(repeated) + 1 < len(body) else ""
            summary = f"{repeated.split()[1]} x `{inner}`"
        else:
            summary = body[0]
            if len(body) > 1:
                summary += f"（共 {len(body)} 行）"
        digest.append((label, summary))
    return tuple(digest)


def assertion_digest(text_lines: tuple[str, ...] | list[str]) -> str:
    """A compact description of every ``EXPECT`` in one case body."""

    by_register: "OrderedDict[str, list[str]]" = OrderedDict()
    trap_values: list[str] = []
    for line in text_lines:
        stripped = line.strip()
        if stripped.startswith("EXPECT_TRAP"):
            trap_values.append(stripped.split(None, 1)[1] if " " in stripped else "")
            continue
        if not stripped.startswith("EXPECT"):
            continue
        body = stripped.split(None, 1)[1] if " " in stripped else ""
        register, _, value = body.partition(",")
        register = register.strip()
        value = value.strip()
        bucket = by_register.setdefault(register, [])
        if value not in bucket:
            bucket.append(value)
    parts = []
    for register, values in by_register.items():
        shown = ", ".join(values[:6])
        if len(values) > 6:
            shown += f", ...（共 {len(values)} 个值）"
        parts.append(f"`{register}`: {shown}")
    if trap_values:
        parts.append(f"`s11`（EXPECT_TRAP）: {', '.join(trap_values)}")
    if not parts:
        guards = tuple(line.strip() for line in text_lines if _GUARD_RE.match(line))
        if guards:
            return "该 case 仅发出 " + "、".join(f"`{guard}`" for guard in guards) + "，EXPECT 断言在后续 case"
        fail("case body carries no EXPECT/EXPECT_TRAP assertion")
    return "；".join(parts)


def first_asserting_case(cases: tuple[CaseRecord, ...]) -> CaseRecord | None:
    return next((case for case in cases if case.assertions), None)


def assertion_anchor(text_lines: tuple[str, ...] | list[str]) -> str:
    """What immediately precedes the first assertion of a case body."""

    lines = list(text_lines)
    first = next(
        (index for index, line in enumerate(lines) if _ASSERT_RE.match(line)), None
    )
    if first is None:
        fail("case body carries no assertion to anchor")
    anchor = "用例体开头"
    for index in range(first - 1, -1, -1):
        stripped = lines[index].strip()
        if not stripped or stripped.startswith("#"):
            continue
        match = _INSN_RE.match(lines[index])
        anchor = match.group(1) if match else stripped
        break
    label = "无"
    for index in range(first - 1, -1, -1):
        match = _LA_RE.match(lines[index])
        if match is not None:
            label = match.group(1)
            break
    return f"{anchor}（数据标签 `{label}`）"


# ---------------------------------------------------------------------------
# Records
# ---------------------------------------------------------------------------


@dataclass
class TemplateInstanceRecord:
    key: str
    name: str
    module: str
    class_name: str
    param: str
    summary_zh: str
    domain_name: str | None
    domain_description: str | None
    domain_dtypes: tuple[str, ...]
    input_cases: tuple[str, ...]
    users: tuple[str, ...]
    cases: tuple[CaseRecord, ...]

    @property
    def first_case(self) -> CaseRecord | None:
        return self.cases[0] if self.cases else None


@dataclass
class InstructionRecord:
    name: str
    summary_zh: str
    manual_zh: str
    family: str
    file_name: str
    class_name: str
    class_module: str
    source_path: str
    source_line: int
    base_module: str
    template_keys: tuple[str, ...]
    supported_dtypes: tuple[str, ...]
    cases_by_template: "OrderedDict[str, tuple[CaseRecord, ...]]"
    total_cases: int

    @property
    def cases(self) -> tuple[CaseRecord, ...]:
        return tuple(
            case for cases in self.cases_by_template.values() for case in cases
        )


@dataclass
class DesignData:
    machine: MachineConfig
    facts: dict[str, ModuleFacts]
    graph: dict[str, set[str]]
    instructions: tuple[InstructionRecord, ...]
    instances: tuple[TemplateInstanceRecord, ...]
    source_lines: int
    source_bytes: int

    @property
    def instances_by_key(self) -> dict[str, TemplateInstanceRecord]:
        return {instance.key: instance for instance in self.instances}


# ---------------------------------------------------------------------------
# Collection
# ---------------------------------------------------------------------------


def instance_key(template: Template) -> str:
    return f"{type(template).__module__}.{type(template).__name__}#{param_label(template)}"


def instance_key_of(record: CaseRecord) -> str:
    return f"{record.template_module}.{record.template_class}#{record.param}"


def _render_cases(
    machine: MachineConfig, instruction: Instruction
) -> tuple[list[CaseRecord], str]:
    """Render every case once, then require the per-case view to rebuild the source."""

    generated = instruction.gen(machine)
    if generated is None:
        fail(f"instruction {instruction.name!r} produced no source on this configuration")

    records: list[CaseRecord] = []
    index = 0
    for template, case in instruction.cases(machine):
        case = replace(case, number=index)
        index += 1
        output = CaseOutput()
        prefix: list[str] = []
        if case.description is not None:
            prefix.append(f"    # input: {case.description}")
        if case.layout is not None:
            prefix.extend(case.layout.comment_lines())
        template.render(machine, instruction, case, output)
        records.append(
            CaseRecord(
                instruction=instruction.name,
                instruction_file=instruction.file_name,
                number=case.number,
                template_name=template.name,
                template_module=type(template).__module__,
                template_class=type(template).__name__,
                param=param_label(template),
                domain=template.dtypes.name if isinstance(template.dtypes, DTypeDomain) else None,
                dtype=case.dtype.name if case.dtype is not None else None,
                description=case.description,
                layout=(
                    " / ".join(case.layout.comment_lines()).strip()
                    if case.layout is not None
                    else None
                ),
                payload=case.payload,
                text_lines=tuple(prefix + output.text),
                data_lines=tuple(output.data),
            )
        )

    rebuilt_lines = list(
        asm_header(
            instruction.banner(machine),
            acquire_backend=instruction.acquires_backend,
        )
    )
    for record in records:
        rebuilt_lines.extend(record.text_lines)
    rebuilt_lines.extend(["    RVMODEL_HALT_PASS", ""])
    footer = instruction.data_footer(machine)
    data_lines = [line for record in records for line in record.data_lines]
    if data_lines or footer or instruction.always_emits_data:
        rebuilt_lines.append(".data")
        rebuilt_lines.extend(data_lines)
        rebuilt_lines.extend(footer)
    rebuilt = "\n".join(rebuilt_lines)
    if rebuilt != generated.text:
        _report_source_mismatch(instruction, rebuilt, generated.text)
    return records, generated.text


def source_matches(stored: str | None, generated: str) -> bool:
    """``write_source`` normalises to exactly one trailing newline."""

    if stored is None:
        return False
    return stored == generated or stored == generated + "\n"


def _report_source_mismatch(instruction: Instruction, rebuilt: str, real: str) -> None:
    rebuilt_lines = rebuilt.split("\n")
    real_lines = real.split("\n")
    for index, (left, right) in enumerate(zip(rebuilt_lines, real_lines)):
        if left != right:
            fail(
                f"per-case reconstruction of {instruction.name!r} diverges at line {index + 1}: "
                f"rebuilt {left!r} vs generated {right!r}"
            )
    fail(
        f"per-case reconstruction of {instruction.name!r} has {len(rebuilt_lines)} lines, "
        f"generated has {len(real_lines)}"
    )


def collect_design_data(machine: MachineConfig, sources: dict[str, str]) -> DesignData:
    facts = build_module_facts()
    graph = build_import_graph(facts)

    instances: "OrderedDict[str, TemplateInstanceRecord]" = OrderedDict()
    instruction_records: list[InstructionRecord] = []

    for instruction in ALL_INSTRUCTIONS:
        records, generated_text = _render_cases(machine, instruction)
        if not source_matches(sources.get(instruction.file_name), generated_text):
            fail(
                f"generated source for {instruction.name!r} differs from the file written to "
                f"the scratch directory"
            )
        cases_by_template: "OrderedDict[str, tuple[CaseRecord, ...]]" = OrderedDict()
        for template in instruction.templates:
            key = instance_key(template)
            cases_by_template[key] = tuple(
                record for record in records if instance_key_of(record) == key
            )
        classified = sum(len(cases) for cases in cases_by_template.values())
        if classified != len(records):
            fail(
                f"instruction {instruction.name!r}: {len(records)} cases rendered but "
                f"{classified} classified by declared templates; a case belongs to no template"
            )

        for template in instruction.templates:
            key = instance_key(template)
            if key not in instances:
                domain = template.dtypes
                if domain is not None and not isinstance(domain, DTypeDomain):
                    fail(
                        f"template {template.name!r} declares a datatype domain that is not a "
                        f"DTypeDomain: {domain!r}"
                    )
                domain_dtypes = (
                    tuple(dtype.name for dtype in domain(machine)) if domain else ()
                )
                instances[key] = TemplateInstanceRecord(
                    key=key,
                    name=template.name,
                    module=type(template).__module__,
                    class_name=type(template).__name__,
                    param=param_label(template),
                    summary_zh=require_chinese(
                        getattr(type(template), "summary_zh", ""),
                        f"template {template.name!r}",
                    ),
                    domain_name=domain.name if domain else None,
                    domain_description=domain.description_zh if domain else None,
                    domain_dtypes=domain_dtypes,
                    input_cases=tuple(template.input_cases),
                    users=(),
                    cases=(),
                )
            instance = instances[key]
            instances[key] = replace(
                instance, cases=tuple(instance.cases) + cases_by_template[key]
            )

        cls = type(instruction)
        try:
            source_path = inspect.getsourcefile(cls)
            _, source_line = inspect.getsourcelines(cls)
        except (OSError, TypeError) as error:
            fail(f"cannot locate source of instruction class {cls.__name__}: {error}")
        base = cls.__mro__[1]
        instruction_records.append(
            InstructionRecord(
                name=instruction.name,
                summary_zh=require_chinese(instruction.summary_zh, f"instruction {instruction.name!r}"),
                manual_zh=instruction.manual_zh.strip(),
                family="",
                file_name=instruction.file_name,
                class_name=cls.__name__,
                class_module=cls.__module__,
                source_path=(
                    str(Path(source_path).resolve().relative_to(GEN_DIR))
                    if source_path
                    else "<unknown>"
                ),
                source_line=source_line,
                base_module=base.__module__ if base is not Instruction else "mmul_gen.instruction",
                template_keys=tuple(instance_key(template) for template in instruction.templates),
                supported_dtypes=tuple(
                    dtype.name for dtype in instruction.supported_dtypes(machine)
                ),
                cases_by_template=cases_by_template,
                total_cases=len(records),
            )
        )

    users_by_key: dict[str, list[str]] = defaultdict(list)
    for record in instruction_records:
        for key in record.template_keys:
            users_by_key[key].append(record.name)
    for key, instance in list(instances.items()):
        instances[key] = replace(instance, users=tuple(users_by_key[key]))

    family_names_in_order = [
        family.name for family in INSTRUCTION_FAMILIES for _ in family.instructions
    ]
    if len(family_names_in_order) != len(instruction_records):
        fail(
            f"catalog family order lists {len(family_names_in_order)} instructions but "
            f"{len(instruction_records)} were collected"
        )
    final_records = tuple(
        replace(record, family=family_name)
        for record, family_name in zip(instruction_records, family_names_in_order)
    )
    return DesignData(
        machine=machine,
        facts=facts,
        graph=graph,
        instructions=final_records,
        instances=tuple(instances.values()),
        source_lines=sum(text.count("\n") for text in sources.values()),
        source_bytes=sum(len(text.encode("utf-8")) for text in sources.values()),
    )


# ---------------------------------------------------------------------------
# Assembly excerpts
# ---------------------------------------------------------------------------


def excerpt(lines: tuple[str, ...] | list[str], limit: int) -> list[str]:
    lines = list(lines)
    if len(lines) <= limit:
        return lines
    head = limit // 2
    tail = limit - head
    return [
        *lines[:head],
        f"    # ...（片段省略 {len(lines) - limit} 行）",
        *lines[-tail:],
    ]


def fenced_asm(lines: list[str]) -> list[str]:
    return ["```asm", *lines, "```"]


def inline_list(values: tuple[str, ...], limit: int = 8) -> str:
    if not values:
        return ""
    if len(values) <= limit:
        return "、".join(f"`{value}`" for value in values)
    return "、".join(f"`{value}`" for value in values[:limit]) + f" 等 {len(values)} 个"


def cell_text(value: str) -> str:
    return value.replace("|", "\\|").replace("\n", " ")


def combo_label(machine: MachineConfig) -> str:
    return f"n{machine.n}/u{machine.uds}/m{machine.num_m_regs}/a{machine.num_acc_regs}"


# ---------------------------------------------------------------------------
# Manual source
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ManualInstruction:
    """One instruction's facts as the authoritative manual states them."""

    anchor: str
    mnemonic: str
    synopsis: str
    description: str
    operation: str
    common_rules: tuple[str, ...]
    encoding_format: str
    funct7: int
    funct3: int
    opcode: int
    match: int
    mask: int


_MANUAL_ANCHOR_RE = re.compile(r"^\[#ame:doc:inst:([A-Za-z0-9_]+)\]\s*$")
_MANUAL_HEADING_RE = re.compile(r"^=== `([^`]+)`\s*$")
_MANUAL_FIELD_RE = re.compile(r"^([A-Za-z][A-Za-z ]*)::\s*$")
_MANUAL_COMMON_RE = re.compile(r"<<(ame-common-[a-z-]+)>>")
_ENCODING_ATTR_RE = re.compile(r"^:([A-Za-z0-9-]+):\s*(0x[0-9a-fA-F]+|\d+)\s*$")
_WAVEDROM_RE = re.compile(r'^\{"reg":')
_ENCODING_FORMATS = {3: "R3", 2: "R2", 1: "R1", 0: "Fixed"}

_MANUAL_CACHE: dict[str, ManualInstruction] | None = None
_MANUAL_ZH_CACHE: dict[str, str] | None = None


def manual_field(chunk: list[str], name: str) -> list[str]:
    """The lines of one ``Name::`` field, up to the next field or the block end."""

    start = next(
        (index + 1 for index, line in enumerate(chunk) if line.strip() == f"{name}::"),
        None,
    )
    if start is None:
        fail(f"manual block has no {name}:: field")
    end = len(chunk)
    for index in range(start, len(chunk)):
        if _MANUAL_FIELD_RE.match(chunk[index].strip()):
            end = index
            break
    return chunk[start:end]


def manual_text(lines: list[str]) -> str:
    """A field's prose with the AsciiDoc continuation markers removed."""

    kept = [line.strip() for line in lines if line.strip() and line.strip() != "+"]
    if not kept:
        fail("manual field is empty")
    return " ".join(kept)


def manual_code(lines: list[str]) -> str:
    """The body of the first ``----`` delimited block of a field."""

    inside = False
    body: list[str] = []
    for line in lines:
        if line.strip() == "----":
            inside = not inside
            continue
        if inside:
            body.append(line.rstrip())
    if not body:
        fail("manual field has no ``----`` code block")
    return "\n".join(body)


def manual_encoding_attributes() -> dict[str, int]:
    """The selector values the manual's encoding registry declares."""

    attributes: dict[str, int] = {}
    for line in MANUAL_ENCODING.read_text(encoding="utf-8").splitlines():
        match = _ENCODING_ATTR_RE.match(line.strip())
        if match is not None:
            attributes[match.group(1)] = int(match.group(2), 0)
    if "ame-enc-funct3" not in attributes:
        fail(f"{MANUAL_ENCODING} declares no ame-enc-funct3 selector")
    return attributes


def manual_encoding(chunk: list[str], attributes: dict[str, int]) -> dict[str, object]:
    """Decode one instruction's encoding from its wavedrom and the registry."""

    lines = manual_field(chunk, "Encoding")
    wavedrom = next((line.strip() for line in lines if _WAVEDROM_RE.match(line.strip())), None)
    if wavedrom is None:
        fail("manual Encoding field has no wavedrom block")
    for name, value in attributes.items():
        wavedrom = wavedrom.replace("{" + name + "}", str(value))
    # The manual writes its fixed selector values as C-style hex literals, which
    # JSON does not accept; every such literal is an unquoted number.
    wavedrom = re.sub(
        r"0x([0-9a-fA-F]+)", lambda match: str(int(match.group(0), 16)), wavedrom
    )
    try:
        payload = json.loads(wavedrom)
    except json.JSONDecodeError as error:
        fail(f"cannot parse the manual wavedrom encoding: {error}")
    fields = payload["reg"]
    total = sum(field["bits"] for field in fields)
    if total != 32:
        fail(f"manual encoding is {total} bits wide, not 32")
    # The manual's wavedrom lists its fields least-significant first.
    offset = 0
    fixed: dict[int, tuple[int, int]] = {}
    variable = 0
    mask = 0
    match = 0
    for field in fields:
        name = field["name"]
        if isinstance(name, int):
            fixed[offset] = (field["bits"], name)
            mask |= ((1 << field["bits"]) - 1) << offset
            match |= name << offset
        else:
            variable += 1
        offset += field["bits"]
    if variable not in _ENCODING_FORMATS:
        fail(f"manual encoding has {variable} variable register fields")
    for needed in (25, 12, 0):
        if needed not in fixed:
            fail(f"manual encoding has no fixed field at bit {needed}")
    return {
        "encoding_format": _ENCODING_FORMATS[variable],
        "funct7": fixed[25][1],
        "funct3": fixed[12][1],
        "opcode": fixed[0][1],
        "match": match,
        "mask": mask,
    }


def manual_instructions() -> dict[str, ManualInstruction]:
    """Every instruction block of the manual, keyed by mnemonic."""

    global _MANUAL_CACHE
    if _MANUAL_CACHE is not None:
        return _MANUAL_CACHE
    lines = MANUAL_INSTRUCTIONS.read_text(encoding="utf-8").splitlines()
    starts = [index for index, line in enumerate(lines) if _MANUAL_ANCHOR_RE.match(line)]
    if not starts:
        fail(f"{MANUAL_INSTRUCTIONS} declares no instruction blocks")
    attributes = manual_encoding_attributes()
    parsed: dict[str, ManualInstruction] = {}
    for position, start in enumerate(starts):
        end = starts[position + 1] if position + 1 < len(starts) else len(lines)
        chunk = lines[start:end]
        anchor = _MANUAL_ANCHOR_RE.match(chunk[0]).group(1)
        heading = next(
            (
                _MANUAL_HEADING_RE.match(line).group(1)
                for line in chunk[1:4]
                if _MANUAL_HEADING_RE.match(line)
            ),
            None,
        )
        if heading is None:
            fail(f"manual anchor {anchor!r} has no instruction heading")
        mnemonic_text = manual_text(manual_field(chunk, "Mnemonic"))
        mnemonic = re.search(r"`([^`]+)`", mnemonic_text)
        if mnemonic is None:
            fail(f"manual block {heading!r} has no backticked mnemonic")
        parsed[heading] = ManualInstruction(
            anchor=anchor,
            mnemonic=mnemonic.group(1),
            synopsis=manual_text(manual_field(chunk, "Synopsis")),
            description=manual_text(manual_field(chunk, "Description")),
            operation=manual_code(manual_field(chunk, "Operation")),
            common_rules=tuple(
                dict.fromkeys(_MANUAL_COMMON_RE.findall("\n".join(chunk)))
            ),
            **manual_encoding(chunk, attributes),  # type: ignore[arg-type]
        )
    _MANUAL_CACHE = parsed
    return parsed


def manual_instruction(name: str) -> ManualInstruction:
    parsed = manual_instructions()
    if name not in parsed:
        fail(f"the manual declares no instruction {name!r}")
    return parsed[name]


def manual_zh_table() -> dict[str, str]:
    """The Chinese rendering of every manual instruction block.

    The table is the single source of the Chinese manual prose; a mnemonic the
    manual declares but the table does not render is a defect, not something the
    exporter may paper over with the English text.
    """

    global _MANUAL_ZH_CACHE
    if _MANUAL_ZH_CACHE is not None:
        return _MANUAL_ZH_CACHE
    if not MANUAL_ZH_PATH.is_file():
        fail(f"{MANUAL_ZH_PATH} is missing; the Chinese manual renderings are required")
    raw = json.loads(MANUAL_ZH_PATH.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        fail(f"{MANUAL_ZH_PATH} must hold an object keyed by mnemonic")
    table: dict[str, str] = {}
    for key, value in raw.items():
        if not isinstance(value, str) or not value.strip():
            fail(f"{MANUAL_ZH_PATH}: {key!r} has no Chinese rendering")
        table[key] = value.strip()
    missing = tuple(name for name in manual_instructions() if name not in table)
    if missing:
        fail(f"{MANUAL_ZH_PATH} renders no manual text for {missing!r}")
    _MANUAL_ZH_CACHE = table
    return table


# ---------------------------------------------------------------------------
# Instruction tables
# ---------------------------------------------------------------------------


def clause(text: str) -> str:
    """A summary used as one clause of a ``；``-joined cell: drop the final period."""

    return text[:-1] if text.endswith("。") else text


def cell_input_mode(imports: dict[str, tuple[str, ...]], instance: TemplateInstanceRecord) -> str:
    parts: list[str] = [clause(instance.summary_zh)]
    if instance.input_cases:
        parts.append("输入用例：" + inline_list(instance.input_cases))
    stimulus = stimulus_symbols(imports)
    if stimulus:
        parts.append("激励：" + inline_list(stimulus))
    helpers = input_helper_symbols(imports)
    if helpers:
        parts.append("数据构造：" + inline_list(helpers))
    return cell_text("；".join(parts))


def cell_expect_rule(imports: dict[str, tuple[str, ...]], instance: TemplateInstanceRecord) -> str:
    parts: list[str] = []
    expected = expect_symbols(imports)
    if expected:
        parts.append("参考：" + inline_list(expected))
    semantic = semantic_symbols(imports)
    if semantic:
        parts.append("语义表：" + inline_list(semantic))
    checks = check_helper_symbols(imports)
    if checks:
        parts.append("断言：" + inline_list(checks))
    representative = first_asserting_case(instance.cases)
    if representative is not None:
        parts.append("期望：" + assertion_digest(representative.text_lines))
    if not parts:
        parts.append(clause(instance.summary_zh))
    return cell_text("；".join(parts))


def cell_domain(instance: TemplateInstanceRecord) -> str:
    if instance.domain_name is None:
        return "无（dtype-free）"
    if not instance.domain_dtypes:
        return f"`{instance.domain_name}`（该组合下选出 0 个描述符）"
    return f"`{instance.domain_name}`（{inline_list(instance.domain_dtypes, limit=6)}）"


# ---------------------------------------------------------------------------
# Manual-sourced narrative blocks
# ---------------------------------------------------------------------------


def render_manual_narrative(data: DesignData, record: InstructionRecord) -> list[str]:
    """The manual-sourced block that precedes one instruction's coverage table.

    Every instruction the manual declares carries one.  Every fact here is read
    from the manual or from the generator; the authored sentences are the Chinese
    glosses of the cited common rules, and the Chinese requirement comes from
    :data:`MANUAL_ZH_PATH`, so a missing rendering fails instead of falling back
    to the English manual text.  A generator-only recipe with no manual block
    reports that absence instead of inventing a narrative.
    """

    manual = manual_instructions().get(record.name)
    if manual is None:
        return [
            "**手册要求**",
            "",
            f"手册 `instructions.adoc` 中没有 `{record.name}` 的指令块：该条目只存在于"
            f"生成清单（`{record.source_path}:{record.source_line}`，"
            f"`{record.class_name}`），是生成器专属的配方，不是手册定义的指令。"
            "本节的覆盖表仍按生成器声明给出，不套用手册叙述块。",
            "",
        ]
    if manual.mnemonic.split()[0] != record.name:
        fail(
            f"manual mnemonic {manual.mnemonic!r} does not match instruction {record.name!r}"
        )
    table = manual_zh_table()
    manual_zh = table[record.name]
    if record.manual_zh and record.manual_zh != manual_zh:
        fail(
            f"instruction {record.name!r} declares manual_zh that differs from "
            f"{MANUAL_ZH_PATH}"
        )
    lines = [
        "**手册要求**",
        "",
        manual_zh,
        "",
        "**手册操作定义**",
        "",
        "```text",
        manual.operation,
        "```",
        "",
        "**编码**",
        "",
        "| 项目 | 值 |",
        "| --- | --- |",
        f"| 助记符 | `{manual.mnemonic}` |",
        f"| 指令格式 | {manual.encoding_format} |",
        f"| funct7 | `0x{manual.funct7:02x}` |",
        f"| funct3 | `0x{manual.funct3:x}` |",
        f"| opcode | `0x{manual.opcode:02x}` |",
        f"| MATCH / MASK | `0x{manual.match:08x}` / `0x{manual.mask:08x}` |",
        "",
    ]
    if manual.common_rules:
        lines.extend(["**公共规则**", ""])
        for rule in manual.common_rules:
            gloss = _COMMON_RULE_ZH.get(rule)
            if gloss is None:
                fail(f"common rule {rule!r} has no Chinese gloss")
            lines.append(f"- 手册公共规则 `<<{rule}>>`。{gloss}")
        lines.append("")
    lines.extend(render_generation_path(data, record))
    lines.extend(render_verdict(data, record))
    lines.extend(render_coverage_gaps(data, record, manual))
    return lines


def render_generation_path(data: DesignData, record: InstructionRecord) -> list[str]:
    instances = data.instances_by_key
    templates = "、".join(
        f"`{instances[key].name}`（{len(record.cases_by_template[key])} 个 case）"
        for key in record.template_keys
    )
    return [
        "**生成路径**",
        "",
        f"由 `{record.source_path}:{record.source_line}`（`{record.class_name}`）声明，"
        f"家族基类模块 `{record.base_module}`；在 {combo_label(data.machine)} 组合下运行 "
        f"{len(record.template_keys)} 个模板：{templates}。",
        "",
    ]


def render_verdict(data: DesignData, record: InstructionRecord) -> list[str]:
    expect = sum(
        1
        for case in record.cases
        for line in case.assertions
        if not line.startswith("EXPECT_TRAP")
    )
    traps = sum(
        1
        for case in record.cases
        for line in case.assertions
        if line.startswith("EXPECT_TRAP")
    )
    guards = sorted(
        {
            line.strip()
            for case in record.cases
            for line in case.text_lines
            if _GUARD_RE.match(line)
        }
    )
    checks = sorted(
        {
            symbol
            for key in record.template_keys
            for symbol in check_helper_symbols(
                merged_imports(data, data.instances_by_key[key].module)
            )
        }
    )
    lines = ["**判定**", ""]
    lines.append(
        f"该组合下 {record.total_cases} 个 case 共 {expect} 处 `EXPECT` 断言"
        + (f"，另有 {traps} 处 `EXPECT_TRAP`" if traps else "，不含 `EXPECT_TRAP` 陷阱守护用例")
        + "；期望值在生成期算好后内嵌进 `.S`，运行时逐寄存器与逐内存比较，"
        "任何一处不等即 `RVMODEL_HALT_FAIL`。"
    )
    if checks:
        lines.extend(["", "断言由模板的 " + inline_list(tuple(checks)) + " 发出。"])
    if guards:
        lines.extend(["", "陷阱守护宏：" + inline_list(tuple(guards)) + "。"])
    lines.append("")
    return lines


def render_coverage_gaps(
    data: DesignData, record: InstructionRecord, manual: ManualInstruction
) -> list[str]:
    all_dtypes = tuple(dtype.name for dtype in data.machine.dtypes)
    missing = tuple(name for name in all_dtypes if name not in record.supported_dtypes)
    lines = ["**不覆盖与已知边界**", ""]
    covered = (
        f"该组合下覆盖 {len(record.supported_dtypes)} 个描述符"
        f"（{inline_list(record.supported_dtypes, limit=8)}）"
    )
    if missing:
        lines.append(f"- datatype：{covered}，未覆盖 {len(missing)} 个：{inline_list(missing)}。")
    else:
        lines.append(f"- datatype：{covered}，手册声明的标准描述符全部覆盖。")
    match_hex = f"0x{manual.match:08x}"
    asserted = any(
        match_hex in line for case in record.cases for line in case.text_lines
    )
    if not asserted:
        lines.append(
            f"- 编码：用例以助记符 `{manual.mnemonic}` 发射指令，由汇编器编码，"
            f"未对指令字做解码断言（MATCH `{match_hex}` / MASK `0x{manual.mask:08x}` "
            f"未在 `.S` 中断言）。"
        )
    has_trap = any(
        line.startswith("EXPECT_TRAP") for case in record.cases for line in case.assertions
    )
    if not has_trap:
        lines.append(
            "- 异常路径：用例不含 `EXPECT_TRAP` 陷阱守护。手册公共规则 "
            "`<<ame-common-operand-validation>>` 要求的非法指令路径（编码越界的 acc/m、"
            "零跨度、越界跨度）与 unsupported tuple 置位 `amestatus.UN` 的路径，"
            "以及 `<<ame-common-state-access>>` 要求的未持有后端时执行即非法指令的路径，"
            "都未在这些用例中覆盖。"
        )
    lines.append(
        "- 自定义 datatype tuple：生成器只发射 `ame_macros.inc` 声明的标准描述符，"
        "手册 `<<ame-common-datatype-support>>` 允许的自定义 tuple 的转换、饱和与融合行为"
        "不在用例范围内。"
    )
    lines.append("")
    return lines


def render_instruction_section(
    data: DesignData, record: InstructionRecord, number: str
) -> list[str]:
    instances = data.instances_by_key
    lines = [
        f"#### {number} {record.name}",
        "",
        record.summary_zh,
        "",
    ]
    lines.extend(render_manual_narrative(data, record))
    lines.extend(
        [
            "| 模板 | datatype 域 | 输入模式 | expect 规则 | case 数 |",
            "| --- | --- | --- | --- | --- |",
        ]
    )
    for key in record.template_keys:
        instance = instances[key]
        imports = merged_imports(data, instance.module)
        lines.append(
            "| "
            + " | ".join(
                [
                    f"`{instance.name}`",
                    cell_domain(instance),
                    cell_input_mode(imports, instance),
                    cell_expect_rule(imports, instance),
                    str(len(record.cases_by_template[key])),
                ]
            )
            + " |"
        )
    lines.extend(
        [
            "",
            f"本指令在 {combo_label(data.machine)} 组合下共 "
            f"{record.total_cases} 个 case；声明位于 `{record.source_path}:{record.source_line}`"
            f"（`{record.class_name}`），家族基类模块 `{record.base_module}`。",
            "",
        ]
    )
    return lines


def family_shared_modules(records: list[InstructionRecord]) -> tuple[str, ...]:
    modules = {
        record.base_module
        for record in records
        if record.base_module != "mmul_gen.instruction"
    }
    return tuple(sorted(modules))


def catalog_registration_lines() -> dict[str, int]:
    text = CATALOG_PATH.read_text(encoding="utf-8").splitlines()
    found: dict[str, int] = {}
    pattern = re.compile(r'Family\(\s*"([a-z_]+)"')
    for index, line in enumerate(text, start=1):
        match = pattern.search(line)
        if match is not None:
            found[match.group(1)] = index
    return found


def render_family_section(
    data: DesignData, family, index: int, registration: dict[str, int]
) -> list[str]:
    records = [record for record in data.instructions if record.family == family.name]
    if not records:
        fail(f"family {family.name!r} has no collected instruction records")
    shared = family_shared_modules(records)
    total_cases = sum(record.total_cases for record in records)
    templates = tuple(
        dict.fromkeys(key for record in records for key in record.template_keys)
    )
    all_dtypes = tuple(dtype.name for dtype in data.machine.dtypes)
    covered = tuple(
        name
        for name in all_dtypes
        if any(name in record.supported_dtypes for record in records)
    )
    design = FAMILY_DESIGN.get(family.name)
    if design is None:
        fail(f"family {family.name!r} has no Chinese design sentence")
    lines = [
        f"### 5.{index} {FAMILY_ZH[family.name]}（`{family.name}`）",
        "",
        f"本模块由生成清单家族 `{family.name}` 界定，共 {len(records)} 个条目，"
        f"在 {combo_label(data.machine)} 组合下产出 {total_cases} 个 case；"
        f"注册于 `mmul_gen/catalog.py:{registration.get(family.name, 0)}`。",
        "",
        f"#### 5.{index}.1 设计方案",
        "",
        design,
        "",
        f"每条指令一个声明模块，负责名字、摘要、操作数与模板元组；发射由模板模块完成。"
        f"本模块声明位于 `mmul_gen/instructions/`，家族基类模块 "
        + inline_list(tuple(sorted({record.base_module for record in records})))
        + "。",
        "",
        f"#### 5.{index}.2 软件接口",
        "",
        f"本模块 {len(records)} 条指令："
        + inline_list(tuple(record.name for record in records))
        + "；声明的模板元组共 "
        + str(len(templates))
        + " 个："
        + inline_list(templates)
        + "。每条指令的声明位置、模板清单、datatype 域、输入模式、expect 规则与 case 数"
        "见各自小节。",
        "",
        f"#### 5.{index}.3 复用性",
        "",
        "同族指令共用模板模块："
        + (inline_list(shared) if shared else "（无家族共享声明模块）")
        + "；模板按运算形态复用，发射逻辑与指令身份解耦。",
        "",
        f"#### 5.{index}.4 兼容性",
        "",
        f"本模块在 {combo_label(data.machine)} 组合下覆盖 "
        f"{len(covered)} / {len(all_dtypes)} 个 datatype 描述符"
        + (f"（{inline_list(covered, limit=8)}）" if covered else "")
        + "；编码与助记符以手册为准，生成器只发射 `ame_macros.inc` 声明的标准描述符。",
        "",
    ]
    for offset, record in enumerate(records, start=5):
        lines.extend(render_instruction_section(data, record, f"5.{index}.{offset}"))
    return lines


# ---------------------------------------------------------------------------
# Appendix A: template modules
# ---------------------------------------------------------------------------


def instances_by_module(data: DesignData) -> dict[str, list[TemplateInstanceRecord]]:
    grouped: dict[str, list[TemplateInstanceRecord]] = defaultdict(list)
    for instance in data.instances:
        grouped[instance.module].append(instance)
    return grouped


def render_appendix_a_index(data: DesignData) -> list[str]:
    """The main document's Appendix A: an index into the data appendix."""

    grouped = instances_by_module(data)
    lines = [
        "## 附录 A 模板",
        "",
        "本附录由 `sail-ame/test/ztt/gen/export_design_appendix.py` 生成。",
        "",
        f"`gen/mmul_gen/templates/` 下共 {len(data.facts)} 个模块。每个模块的模块说明、"
        "模板内容（如何构造输入、发射什么代码、参与哪些指令）、断言放置，以及真实生成的"
        f"汇编片段，见 `doc/{DATA_DOC.name}` 的附录 A；下表为索引。",
        "",
        "| 模块 | 说明 | 模板（case 数） | 参与指令数 |",
        "| --- | --- | --- | --- |",
    ]
    for module_name in sorted(data.facts):
        facts = data.facts[module_name]
        owned = sorted(grouped.get(module_name, ()), key=lambda item: (item.name, item.key))
        summary_line = facts.doc_zh.splitlines()[0].strip()
        if owned:
            template_cell = "、".join(
                f"`{name}`（{sum(len(item.cases) for item in group)}）"
                for name, group in (
                    (group[0].name, group) for group in group_instances_by_name(owned)
                )
            )
            users = len({user for instance in owned for user in instance.users})
            user_cell = str(users)
        else:
            defined = [*facts.classes, *facts.functions]
            template_cell = "共享机制：" + (
                inline_list(tuple(defined), limit=4) if defined else "无顶层类或函数"
            )
            user_cell = "不直接参与指令"
        lines.append(
            f"| `{facts.path.relative_to(GEN_DIR)}` | {cell_text(summary_line)} | "
            f"{template_cell} | {user_cell} |"
        )
    lines.append("")
    return lines


def render_appendix_a_full(data: DesignData) -> list[str]:
    lines = [
        "## 附录 A 模板（全量）",
        "",
        "本附录由 `sail-ame/test/ztt/gen/export_design_appendix.py` 生成。",
        "",
        "逐个列出 `gen/mmul_gen/templates/` 下的全部模块。每个模块给出模块说明、它定义的"
        "模板（或它提供的共享机制）、这些模板参与的指令，以及这些模板产生的 case 在 `.S` "
        "中的断言放置；汇编片段取自真实生成的 `.S`。",
        "",
    ]
    grouped = instances_by_module(data)
    for index, module_name in enumerate(sorted(data.facts), start=1):
        facts = data.facts[module_name]
        lines.extend(
            [
                f"### A.{index} `{facts.path.relative_to(GEN_DIR)}`",
                "",
                "**说明**",
                "",
                facts.doc_zh,
                "",
            ]
        )
        owned = sorted(grouped.get(module_name, ()), key=lambda item: (item.name, item.key))
        if owned:
            lines.extend(["**模板内容**", ""])
            for group in group_instances_by_name(owned):
                lines.extend(render_template_group(group))
            representative = next(
                (
                    case
                    for instance in owned
                    for case in instance.cases
                    if case.assertions
                ),
                None,
            )
            if representative is not None:
                lines.extend(
                    [
                        f"实际生成汇编片段（`{representative.instruction_file}`，"
                        f"case {representative.number}，模板 `{representative.template_name}`，"
                        f"datatype `{representative.dtype}`）：",
                        "",
                        *fenced_asm(excerpt(representative.text_lines, SNIPPET_LIMIT)),
                        "",
                    ]
                )
        else:
            lines.extend(render_helper_content(data, facts))
        lines.extend(render_module_assertions(data, module_name))
    return lines


def group_instances_by_name(
    instances: list[TemplateInstanceRecord],
) -> list[list[TemplateInstanceRecord]]:
    grouped: "OrderedDict[str, list[TemplateInstanceRecord]]" = OrderedDict()
    for instance in instances:
        grouped.setdefault(instance.name, []).append(instance)
    return list(grouped.values())


def render_template_group(group: list[TemplateInstanceRecord]) -> list[str]:
    head = group[0]
    parameters = [instance.param for instance in group if instance.param]
    if not parameters:
        parameter_text = "无构造参数"
    elif len(parameters) == 1:
        parameter_text = f"参数：{parameters[0]}"
    else:
        shown = "；".join(parameters[:3])
        parameter_text = f"参数化实例 {len(group)} 个（{shown} 等）"
    users = tuple(
        sorted({user for instance in group for user in instance.users})
    )
    cases = [case for instance in group for case in instance.cases]
    lines = [
        f"- 模板 `{head.name}`（类 `{head.class_name}`，{parameter_text}）：{head.summary_zh}"
    ]
    if head.domain_name is not None:
        lines.append(f"  - datatype 域 `{head.domain_name}`：{head.domain_description}。")
    else:
        lines.append("  - 无 datatype 维度：每个配置构造一个 dtype-free 用例。")
    if head.input_cases:
        lines.append("  - 输入用例：" + inline_list(head.input_cases) + "。")
    lines.append(
        "  - 参与指令："
        + (inline_list(users, limit=12) if users else "无（声明但未产出用例）")
        + "。"
    )
    lines.append(f"  - 该组合下 case 数：{len(cases)}。")
    return lines


def render_helper_content(data: DesignData, facts: ModuleFacts) -> list[str]:
    importers = importing_modules(data.graph, facts.name)
    defined = [*facts.classes, *facts.functions]
    lines = ["**模板内容**", ""]
    lines.append(
        "本模块不定义具体模板，提供共享机制："
        + (inline_list(tuple(defined)) if defined else "无顶层类或函数")
        + "。"
    )
    if importers:
        lines.extend(["", "导入它的模板模块：" + inline_list(tuple(importers), limit=12) + "。"])
    lines.append("")
    return lines


def render_module_assertions(data: DesignData, module_name: str) -> list[str]:
    cases = [
        case
        for instance in data.instances
        if instance.module == module_name
        for case in instance.cases
    ]
    lines = ["**断言放置**", ""]
    if not cases:
        lines.extend(
            [
                "本模块自身不产出 case；其断言行为由导入它的模板模块决定。",
                "",
            ]
        )
        return lines
    anchors: "OrderedDict[str, int]" = OrderedDict()
    macros: "OrderedDict[str, int]" = OrderedDict()
    registers: "OrderedDict[str, int]" = OrderedDict()
    for case in cases:
        if not case.assertions:
            continue
        anchor = assertion_anchor(case.text_lines)
        anchors[anchor] = anchors.get(anchor, 0) + 1
        for assertion in case.assertions:
            macro = assertion.split(None, 1)[0]
            macros[macro] = macros.get(macro, 0) + 1
            body = assertion.split(None, 1)[1] if " " in assertion else ""
            register = body.partition(",")[0].strip()
            registers[register] = registers.get(register, 0) + 1
    lines.append(
        "断言宏：" + "、".join(f"`{macro}`（{count} 处）" for macro, count in macros.items()) + "。"
    )
    lines.extend(
        [
            "",
            "检查寄存器："
            + "、".join(f"`{register}`（{count} 处）" for register, count in registers.items())
            + "。",
            "",
            "首个断言前的锚点：",
            "",
            "| 锚点 | case 数 |",
            "| --- | --- |",
        ]
    )
    for anchor, count in sorted(anchors.items(), key=lambda item: (-item[1], item[0])):
        lines.append(f"| {cell_text(anchor)} | {count} |")
    lines.append("")
    representative = first_asserting_case(tuple(cases)) or cases[0]
    lines.extend(
        [
            f"代表断言（`{representative.instruction_file}`，case {representative.number}）："
            + "；".join(f"`{item}`" for item in representative.assertions[:6])
            + "。",
            "",
        ]
    )
    return lines


# ---------------------------------------------------------------------------
# Appendix B: instance level
# ---------------------------------------------------------------------------


def render_appendix_b(data: DesignData) -> list[str]:
    lines = [
        "## 附录 B 输入数据",
        "",
        "本附录由 `sail-ame/test/ztt/gen/export_design_appendix.py` 生成。",
        "",
        "### B.1 定义级全量（模板 × datatype）",
        "",
        "定义级全量按模板 × datatype 列出输入构造、expect 规则与实际生成汇编片段，内容较长，"
        f"单独成文：`doc/{DATA_DOC.name}`。",
        "",
        "### B.2 实例级（" + combo_label(data.machine) + "，2D 矩阵乘家族）",
        "",
        "对 2D 矩阵乘家族的六条指令，逐 case 列出模板、datatype、输入与 expect。",
        "",
    ]
    for record in data.instructions:
        if record.name in INSTANCE_INSTRUCTIONS:
            lines.extend(render_instance_table(data, record))
    return lines


def render_instance_table(data: DesignData, record: InstructionRecord) -> list[str]:
    instances = data.instances_by_key
    lines = [
        f"#### B.2.{INSTANCE_INSTRUCTIONS.index(record.name) + 1} {record.name}",
        "",
        f"{clause(record.summary_zh)}；共 {record.total_cases} 个 case。",
        "",
        "| case 号 | 指令 | 模板 | datatype | 输入（模式与关键参数） | expect（期望值或判定规则） |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    for key in record.template_keys:
        instance = instances[key]
        for case in record.cases_by_template[key]:
            lines.append(
                "| "
                + " | ".join(
                    [
                        str(case.number),
                        f"`{case.instruction}`",
                        f"`{case.template_name}`",
                        f"`{case.dtype}`" if case.dtype else "无",
                        cell_text(payload_input_summary(case, instance)),
                        cell_text(assertion_digest(case.text_lines)),
                    ]
                )
                + " |"
            )
    lines.append("")
    return lines


def payload_input_summary(case: CaseRecord, instance: TemplateInstanceRecord) -> str:
    mode = case.description or instance.summary_zh
    parts = [mode]
    if case.payload is not None:
        parts.append(compact(case.payload, max_items=3))
    if case.layout:
        parts.append("布局 " + layout_summary(case.layout))
    return "（".join([parts[0], "；".join(parts[1:]) + "）"]) if len(parts) > 1 else parts[0]


def layout_summary(layout: str) -> str:
    """Turn the emitted layout comment lines into one cell-sized phrase."""

    fragments = [
        fragment.strip().lstrip("#").strip()
        for fragment in layout.split(" / ")
        if fragment.strip()
    ]
    return "；".join(fragments)


# ---------------------------------------------------------------------------
# Data appendix (definition level)
# ---------------------------------------------------------------------------


def render_data_doc(data: DesignData) -> str:
    lines = [
        "# Ztt 测试设计文档附录数据",
        "",
        "> 本附录由 `sail-ame/test/ztt/gen/export_design_appendix.py` 生成，"
        f"对应代表组合 {combo_label(data.machine)}。",
        "",
    ]
    lines.extend(render_appendix_a_full(data))
    lines.extend(
        [
            "## 附录 B 输入数据（定义级全量）",
            "",
            "逐个模板实例列出它覆盖的每个 datatype 的输入构造与 expect 规则，并附一段真实生成的"
            "汇编片段。",
            "",
        ]
    )
    by_module: dict[str, list[TemplateInstanceRecord]] = defaultdict(list)
    for instance in data.instances:
        by_module[instance.module].append(instance)
    for module_index, module_name in enumerate(sorted(by_module), start=1):
        facts = data.facts[module_name]
        instances = sorted(by_module[module_name], key=lambda item: (item.name, item.key))
        lines.extend(
            [
                f"### B.{module_index} `{facts.path.relative_to(GEN_DIR)}`",
                "",
                facts.doc_zh,
                "",
            ]
        )
        for instance_index, instance in enumerate(instances, start=1):
            lines.extend(
                render_data_instance(
                    data, facts, instance, f"B.{module_index}.{instance_index}"
                )
            )
    return "\n".join(lines).rstrip("\n") + "\n"


def render_data_instance(
    data: DesignData, facts: ModuleFacts, instance: TemplateInstanceRecord, number: str
) -> list[str]:
    lines = [
        f"#### {number} `{instance.name}`（`{instance.class_name}`"
        + (f"；{instance.param}" if instance.param else "")
        + "）",
        "",
        instance.summary_zh,
        "",
    ]
    if instance.domain_name is not None:
        lines.append(f"datatype 域 `{instance.domain_name}`：{instance.domain_description}。")
    else:
        lines.append("datatype 域：无（dtype-free）。")
    lines.append("")
    lines.append(
        "参与指令：" + (inline_list(instance.users, limit=12) if instance.users else "无") + "。"
    )
    lines.append("")
    by_dtype: "OrderedDict[str, list[CaseRecord]]" = OrderedDict()
    for case in instance.cases:
        by_dtype.setdefault(case.dtype or "无", []).append(case)
    if by_dtype:
        lines.extend(
            [
                "| datatype | 输入构造 | expect 规则 |",
                "| --- | --- | --- |",
            ]
        )
        for dtype, cases in by_dtype.items():
            first = first_asserting_case(tuple(cases)) or cases[0]
            inputs = (
                "；".join(
                    f"`{label}`: {summary}" for label, summary in label_digest(first.data_lines)
                )
                or instance.summary_zh
            )
            lines.append(
                f"| `{dtype}` | {cell_text(inputs)} | "
                f"{cell_text(assertion_digest(first.text_lines))} |"
            )
        lines.append("")
    else:
        lines.extend(["该组合下不产出用例。", ""])
    first = first_asserting_case(instance.cases) or instance.first_case
    if first is not None:
        lines.extend(
            [
                f"实际生成汇编片段（`{first.instruction_file}`，case {first.number}，"
                f"datatype `{first.dtype}`）：",
                "",
                *fenced_asm(excerpt(first.text_lines, SNIPPET_LIMIT)),
                "",
            ]
        )
        if first.data_lines:
            lines.extend(
                [
                    "该 case 的 `.data` 片段：",
                    "",
                    *fenced_asm(excerpt(first.data_lines, DATA_SNIPPET_LIMIT)),
                    "",
                ]
            )
        else:
            lines.extend(["该 case 不发射 `.data` 段，输入与期望均在 `.text` 中构造。", ""])
    return lines


# ---------------------------------------------------------------------------
# Assembly of the main document
# ---------------------------------------------------------------------------


def render_performance_section(data: DesignData) -> list[str]:
    """Chapter 6: the deterministic generation-time scale facts.

    Every number is read from the generator's own default sweep or from the
    sources a real generation pass produced; no runtime performance figure is
    stated because none is measured here.
    """

    combos = run_ztt_tests.all_combos()
    combo = combo_label(data.machine)
    total_cases = sum(record.total_cases for record in data.instructions)
    expect = sum(
        1
        for record in data.instructions
        for case in record.cases
        for line in case.assertions
        if not line.startswith("EXPECT_TRAP")
    )
    traps = sum(
        1
        for record in data.instructions
        for case in record.cases
        for line in case.assertions
        if line.startswith("EXPECT_TRAP")
    )
    dtypes = tuple(dtype.name for dtype in data.machine.dtypes)
    busiest = max(data.instructions, key=lambda record: (record.total_cases, record.name))
    return [
        "## 6 软件性能指标",
        "",
        "| 项目 | 指标 |",
        "| --- | --- |",
        f"| 组合数 | 默认 {len(run_ztt_tests.N_VALUES)} × {len(run_ztt_tests.UDS_VALUES)} × "
        f"{len(run_ztt_tests.MREG_VALUES)} × {len(run_ztt_tests.ACC_VALUES)} = "
        f"{len(combos)} 个几何组合 |",
        f"| 单组合源文件 | {len(data.instructions)} 个 `.S`（与生成清单条目数一致） |",
        f"| 单组合源规模 | {combo} 组合下共 {data.source_lines} 行 / {data.source_bytes} 字节 |",
        f"| 单组合用例规模 | {combo} 组合下共 {total_cases} 个 case |",
        f"| 单组合断言规模 | {combo} 组合下共 {expect} 处 `EXPECT`"
        + (f"，另有 {traps} 处 `EXPECT_TRAP`" if traps else "，不含 `EXPECT_TRAP`")
        + " |",
        f"| 单组合 datatype | {combo} 组合覆盖 {len(dtypes)} 个 datatype 描述符 |",
        f"| 单指令最大 case 数 | {combo} 组合下 `{busiest.name}` 为 "
        f"{busiest.total_cases} 个 case |",
        "| 生成方式 | 生成期确定性计算，生成结果按目录缓存，已生成的组合不重复生成 |",
        "| 运行期开销 | 判定为逐寄存器与逐内存比较，开销随 case 数与几何规模增长 |",
        "",
        "上表为生成期与用例规模事实，不包含目标模拟器的运行时间指标。",
        "",
    ]


def render_main_doc(data: DesignData) -> str:
    registration = catalog_registration_lines()
    names = [record.name for record in data.instructions]
    unique_files = {record.file_name for record in data.instructions}
    unique_names = set(names)
    lines: list[str] = [STATIC_FRONT.rstrip("\n"), ""]
    lines.extend(
        [
            f"清单共 {len(data.instructions)} 个条目 / {len(unique_files)} 个唯一文件名 / "
            f"{len(unique_names)} 个助记符，分属 {len(INSTRUCTION_FAMILIES)} 个家族；"
            f"在 {combo_label(data.machine)} 组合下共 "
            f"{sum(record.total_cases for record in data.instructions)} 个 case。",
            "",
            "每条指令一张覆盖表：它声明的模板、每个模板的 datatype 域、输入模式、expect 规则"
            "以及该组合下的 case 数。模板的完整说明见附录 A，逐 datatype 的输入构造与真实汇编"
            "片段见附录 B。",
            "",
        ]
    )
    for index, family in enumerate(INSTRUCTION_FAMILIES, start=1):
        lines.extend(render_family_section(data, family, index, registration))
    lines.extend(render_performance_section(data))
    lines.append(STATIC_BACK.rstrip("\n"))
    lines.append("")
    lines.extend(render_appendix_a_index(data))
    lines.extend(render_appendix_b(data))
    return "\n".join(lines).rstrip("\n") + "\n"


# ---------------------------------------------------------------------------
# Generation pass
# ---------------------------------------------------------------------------


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--macro-file", type=Path, default=DEFAULT_MACRO_FILE)
    parser.add_argument("--n", type=int, default=DEFAULT_N)
    parser.add_argument("--uds", type=int, default=DEFAULT_UDS)
    parser.add_argument("--m", type=int, default=DEFAULT_M)
    parser.add_argument("--acc", type=int, default=DEFAULT_ACC)
    parser.add_argument("--main-doc", type=Path, default=MAIN_DOC)
    parser.add_argument("--data-doc", type=Path, default=DATA_DOC)
    parser.add_argument("--check", action="store_true", help="verify outputs are current")
    return parser.parse_args(argv)


def generate_sources(machine: MachineConfig) -> dict[str, str]:
    """Write one real generation pass to a scratch directory and read it back."""

    from mmul_gen.__main__ import write_source

    sources: dict[str, str] = {}
    with tempfile.TemporaryDirectory(prefix="ztt-design-") as directory:
        out_dir = Path(directory)
        for instruction in ALL_INSTRUCTIONS:
            source = instruction.gen(machine)
            if source is None:
                fail(f"instruction {instruction.name!r} produced no source")
            write_source(out_dir, source)
            path = out_dir / source.name
            if not path.is_file():
                fail(f"generator did not write {source.name!r} to the scratch directory")
            sources[source.name] = path.read_text(encoding="utf-8")
    return sources


def _validate(data: DesignData) -> None:
    """Fail-fast invariants over the collected records."""

    if not data.instances:
        fail("no template instances collected")
    if len(data.instructions) != len(ALL_INSTRUCTIONS):
        fail(
            f"collected {len(data.instructions)} instructions, catalog declares "
            f"{len(ALL_INSTRUCTIONS)}"
        )
    for instance in data.instances:
        if not instance.summary_zh.strip():
            fail(f"template {instance.name!r} has an empty Chinese summary")
        if instance.module not in data.facts:
            fail(f"template {instance.name!r} lives outside templates/: {instance.module}")
        for case in instance.cases:
            if case.dtype is None and instance.domain_name is not None:
                fail(
                    f"template {instance.name!r} declares domain {instance.domain_name!r} "
                    f"but produced a dtype-free case {case.number}"
                )
        if instance.cases and first_asserting_case(instance.cases) is None:
            fail(
                f"template {instance.name!r} produced {len(instance.cases)} cases but none "
                f"carries an EXPECT/EXPECT_TRAP assertion"
            )
    for fact in data.facts.values():
        if not fact.doc_zh.strip():
            fail(f"module {fact.name!r} has an empty Chinese description")
    manual = manual_instructions()
    table = manual_zh_table()
    for record in data.instructions:
        if not record.summary_zh.strip():
            fail(f"instruction {record.name!r} has an empty Chinese summary")
        if record.name in manual:
            if record.manual_zh and record.manual_zh != table[record.name]:
                fail(
                    f"instruction {record.name!r} declares manual_zh that differs from "
                    f"{MANUAL_ZH_PATH}"
                )
        elif record.manual_zh:
            fail(
                f"instruction {record.name!r} declares manual_zh but the manual has no "
                f"block for it"
            )
    for domain in ALL_DOMAINS:
        if not isinstance(domain, DTypeDomain):
            fail(f"datatype domain {domain!r} is not a DTypeDomain")
        if not domain.description_zh.strip():
            fail(f"datatype domain {domain.name!r} has an empty Chinese description")


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    machine = MachineConfig(
        dtypes=parse_dtypes(args.macro_file),
        n=args.n,
        uds=args.uds,
        num_m_regs=args.m,
        num_acc_regs=args.acc,
    )
    sources = generate_sources(machine)
    data = collect_design_data(machine, sources)
    _validate(data)
    main_text = render_main_doc(data)
    data_text = render_data_doc(data)

    outputs = {args.main_doc: main_text, args.data_doc: data_text}
    if args.check:
        stale = [
            str(path)
            for path, text in outputs.items()
            if not path.is_file() or path.read_text(encoding="utf-8") != text
        ]
        if stale:
            fail("generated outputs are stale: " + ", ".join(stale))
        print("generated outputs are current")
        return 0
    for path, text in outputs.items():
        path.write_text(text, encoding="utf-8")
    print(f"wrote {args.main_doc} ({main_text.count(chr(10))} lines)")
    print(f"wrote {args.data_doc} ({data_text.count(chr(10))} lines)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
