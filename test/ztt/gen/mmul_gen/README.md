# Ztt 测试生成器（`mmul_gen`）

Ztt 测试生成器：**每条指令一个文件、每个模板一个文件**，按指令家族分组。它是仓库里唯一
的测试生成器，`test/ztt/run_ztt_tests.py` 直接调用它。

覆盖 **141 个源**（`accumulator` 4 条 + `acc_span` 3 条 + `axis_permute` 6 条 + `backend` 2 条 + `broadcast` 1 条 +
`debug_move` 8 条 + `elementwise` 46 条 + `float_math` 10 条 + `integer_shift` 6 条 +
`load_store` 2 条 + `logexp` 12 条 + `matrix_ops` 20 条 + `mconv` 1 条 + `memory_order` 4 条 +
`mmul` 6 条 + `pack` 2 条 + `strided_memory` 4 条 + `type_register` 4 条）。

```sh
cd sail-ame/test/ztt/gen
python3 -m mmul_gen --list                    # 全部家族的清单
python3 -m mmul_gen --family type_register --list
```

```sh
cd sail-ame/test/ztt/gen
python3 -m mmul_gen --list
python3 -m mmul_gen --n 8 --uds 8 --m 32 --acc 4 \
    --out-dir <out-dir>
python3 -m mmul_gen.tests
```

## 目录结构

| 路径                                  | 职责                                                                                                                                             |
| ------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------ |
| `instructions/<family>/<mnemonic>.py` | 每条指令一个文件、每个家族一个包；类继承该家族的基类                                                                                             |
| `catalog.py`                          | **入口。** 有序指令元组与生成循环                                                                                                                |
| `instruction.py`                      | 指令基类：`gen()`、操作数、标题，以及"类只声明身份与公式"的契约                                                                                  |
| `templates/`                          | 每个模板一个模块：一个带 docstring 的 `Template` 子类，拥有自己的数据类型域、用例构建器与渲染器。见 [`templates/README.md`](templates/README.md) |
| `templates/base.py`                   | `Template` 契约、用例模型，以及多于一个模板需要的机制                                                                                            |
| `templates/__init__.py`               | 两层模板登记表：`ALL_TEMPLATES` 是无参共享单例，`TEMPLATE_CLASSES` 是带参、由指令自己构造的类                                                    |
| `tests/test_architecture.py`          | 结构性守卫：指令类只声明身份与公式，模板不回读家族数据                                                                                           |
| `machine.py`                          | `MachineConfig`（N/UDS/M/ACC）与具名的数据类型域                                                                                                 |
| `registers.py`                        | M/ACC 布局声明及其严格解析                                                                                                                       |
| `inputs.py`                           | 激励配方（整数斜坡、打包方阵、浮点边界）                                                                                                         |
| `reference.py`                        | 精确期望值，与 `numeric_reference` 交叉校验                                                                                                      |
| `float_formats.py`                    | 浮点格式的 2 的幂期望值                                                                                                                          |
| `asm.py`                              | 与指令无关的 GAS 发射原语                                                                                                                        |
| `macros.py`                           | 从 `src/ame_macros.inc` 解析数据类型                                                                                                             |
| `__main__.py`                         | CLI：原子地写出生成源，并清理自己产生的过期文件                                                                                                  |

## 指令如何声明

一条指令"是什么"全部放在一个文件里，作为类属性。没有分派表、没有装饰器、没有导入
副作用：

```python
class MmulBtAcc2d(MatrixMultiplyInstruction):
    name = "mmulbtacc.2d"
    summary = "C = C + sum(A x transpose(B))"
    operands = PRODUCT_OPERANDS
    templates = (
        MATRIX_SMALL,
        FLOAT_PAIR_SWEEP,
        PACKED_SMALL,
        SATURATING_BOUNDARY,
        MIXED_SIGNEDNESS_MULTIPLE_SQUARE,
    )
    transposes_rhs = True
```

`name`、`summary`、`operands` 说的是"是什么"，`templates` 说的是"如何被检验"。数据
类型覆盖**不会**被声明第二遍：每个模板拥有自己迭代的、依赖机器的数据类型域
（`INTEGER`、`INTEGER128`、`SATURATING_INTEGER`、`PACKED_INTEGER`、`SOFTFLOAT`、
`SIGNED_PACKED_SOURCE`），指令暴露两个派生视图：

- `datatype_domains` —— 其模板覆盖的域，按声明顺序；
- `supported_dtypes(machine)` —— 这些域在具体 N/UDS 配置下展开、并施加资源谓词后的
  结果。

`--list` 会同时打印两者，因此无需第二个可能漂移的事实来源就能检视覆盖率。它还打印
`input_cases`：每条指令跑的全部输入用例（名字），从它构造出的 `templates` 里读出——声明清单的
模板（如 `GatherScatterIndexed`）报出自己的标签，elementwise 则报出它传给整数场景的那份清单，
两边都只有一处声明：输入用例清单只在声明它的模板里写一次，每个用例自身的注释也只写一次。

输入也在指令类里写全：四项通用整数用例是 `BASE_INTEGER_INPUT_CASES`（家族基类写一次），
有溢出用例的指令用 `BASE_INTEGER_INPUT_CASES + (overflow(...),)` 组合进来，所以打开任一指令
文件都能看到它跑的完整输入清单（见 [`instructions/README.md`](instructions/README.md)）。

elementwise 家族直接把模板写出来：46 条指令各自列出 `templates`，每个模板**构造时就带上**它
要检验的值（整数清单、饱和配方、软浮点名义答案……），列表的先后就是源里场景段的先后。没有筛
这一步——写进列表的就是会跑的，没写的就不存在——所以打开一个指令文件就能看到它参加哪些检验、
每个检验拿到什么，而 `--list` 报的是每条指令实际渲染的场景数（2 到 7 个不等），不是所有指令
都报同一个数字。

语义差异（`transposes_lhs`、`transposes_rhs`、`negates_product`）是标志位而不是助记符
字符串，因此没有任何模板会去检查助记符前缀。

**它算什么**同样写在指令里。整数 elementwise 指令声明一个方法：

```python
    def evaluate(self, elements: IntegerElements) -> int:
        """``D = B`` when ``A >= 0``, else ``D`` keeps its value; the M form
        shares ``D`` and ``A``."""

        return elements.rhs if elements.lhs >= 0 else elements.dest
```

它返回**精确结果**，由 `integer_expected` 按元素宽度重新编码；`elements` 已经把操作数形态
翻译成 `lhs`/`rhs`/`dest`（含 `_raw` 位读法与 `mask`），所以 M 形式与标量形式的算式写法相同。
这条算式**作为参数交给两条整数模板**（`ElementwiseIntegerValueRules(BASE_INTEGER_INPUT_CASES, evaluate)`），
模板持有它、`integer_expected` 调它，因此漏传在类定义时就报 `TypeError`；
`mmul_gen/tests/test_elementwise_declared_evaluation.py` 再把它与共享 oracle
`numeric_reference` 逐点穷举对齐。完整词汇表见
[`instructions/README.md`](instructions/README.md)。

浮点走同一条思路，只是函数的体不同：类里再声明一个 `evaluate_float(dtype_name, element_bits)`，
交给 `ElementwiseFloatNominal`；体通常是一行查表（`FLOAT_OPERATION_VALUES`，比较类返回全 1 或 0）。
所以"`evaluate` 必须是算出来的"并不成立——**模板持有的是"怎么得到期望值"，整数是算术，浮点是
查表**。浮点的另外两格（特殊值、舍入）没有"一个答案"，各自是几十上百个用例，指令在那里声明的是
role，不写 `evaluate_float`。

`gen(machine)` 是生成器唯一调用的方法；`evaluate` 是整数声明的算式，由整数模板持有；其余家族
没有它。
`gen` 遍历已声明的模板，把每个渲染好的用例交给 `_TestProgram`，后者负责 `.text`/`.data`
的累积与文件框架。

## 模板如何声明

`Template` 是本生成器的主要类类型。一个模板就是一个循环：它迭代的数据类型域、它为
每个数据类型构建的用例、以及它如何渲染这些用例。每个模板都在自己的模块里，是一个
子类：

```python
class PackedSmall(Template):
    """Sub-UDS packed integer source widened into a whole-register product."""

    name = "packed_small"
    dtypes = PACKED_INTEGER

    def build(self, machine, instruction, dtype) -> list[Case]: ...
    def render(self, machine, instruction, case, out) -> None: ...
```

- 类的 docstring **就是**模板的摘要；`--list` 从这里读取，因此不存在第二个会漂移的
  `summary` 字段。
- `build` 计算操作数取值、期望值与寄存器布局，不产出汇编。
- `render` 依据带类型的用例 payload 发射汇编，绝不重算期望值，也绝不重读数据类型表。
- `fits(machine, dtype)` 是资源谓词，默认为"总是可以"；只有当模板需要多于一个
  M 寄存器跨度时才覆盖它。
- 每个用例的 payload 都是 frozen dataclass（`PackedPayload`、`SaturatingPayload`、
  `FloatOverflowPayload`……），而不是字符串键的字典；渲染器会断言自己拿到的 payload
  类型。

`Case` 携带已解析的 `RegisterLayout`，因此生成的 `M layout` / `ACC layout` 注释由程序
构建器统一发射，而不是每个模板各写一遍。装不下当前寄存器文件的布局会被**跳过**，绝不
悄悄重新布局。

### 用继承复用模板

继承适用于"几乎就是另一个模板"的模板，而不是指令。`ones_uniform_128` 是作用在更宽域上
的 `ones_uniform`，因此它继承用例构建器，只覆盖真正不同的部分：

```python
class OnesUniform128(OnesUniform):
    """All-ones 128-bit integer product spanning several M registers."""

    name = "ones_uniform_128"
    dtypes = INTEGER128

    def fits(self, machine, dtype) -> bool:
        return two_register_groups_fit(machine, dtype)

    def render(self, machine, instruction, case, out) -> None: ...
```

与之相对，指令**组合**模板而不是继承它们：6 条矩阵乘法指令共享 `float_pair_sweep`、
`packed_small`、`saturating_boundary` 与 `mixed_signedness_multiple_square`，5 条共享
`matrix_small`，只有 `mmulacc.2d` 额外使用 `ones_uniform`、`ones_uniform_128` 与
`multi_acc_independent`。共享的实例从不被复制——这正是为什么 `packed_small` 只写一次，
却出现在 6 个生成源里，而不是在 6 个指令文件里各写一遍。

## 新增一条指令

1. 新增 `instructions/<family>/<mnemonic>.py`，写入子类以及它覆盖的模板（已有的模板清单按引用
   复用，不复制）。
2. 在 `instructions/__init__.py` 中登记该类。
3. 在 `catalog.py` 的 `MATRIX_MULTIPLY_INSTRUCTIONS` 中加入实例。

现有指令文件无需任何改动。

## 覆盖

对每条指令，`--list` 会打印确切的 datatype、操作数与模板。这些模板覆盖生成套件需要的
全部配置：

| 模板                                | 覆盖内容                                              |
| ----------------------------------- | ----------------------------------------------------- |
| `ones_uniform` / `ones_uniform_128` | 整寄存器与跨寄存器的全 1 乘积（后者继承前者）         |
| `matrix_small`                      | 位置相关的小矩阵乘积，含转置与取负变体                |
| `float_pair_sweep`                  | 可精确表示的乘积，外加正负号 × 6 种舍入模式的溢出扫描 |
| `packed_small`                      | 窄于 UDS 的打包源在回写时加宽，4/8/16 位存储          |
| `saturating_boundary`               | 必须置起 `amexsat` 并饱和的 `1 x max`                 |
| `multi_acc_independent`             | 每个合法累加器独立播种、累加、读回                    |
| `mixed_signedness_multiple_square`  | 两个符号与取值都不同的打包方阵                        |

生成器在 `N ∈ {4,8,16,32}` × `UDS ∈ {8,16,32}` × `M ∈ {16,32}` ×
`ACC ∈ {1,2,4,8,16}` 的全部 120 种组合上运行，每种组合每条指令一份静态 N 形式。全部 141 条
指令在这 120 种配置上生成源文件，并逐字节校验一致（差额来自 `debug_move`、`matrix_ops`、
`acc_span` 与 `elementwise` 在窄配置下整个源都不生成的情形）。

需要区分的是：这 120 是**生成器被检验的配置空间**，而不是"每个模板在每个组合里都会
运行"。某个模板是否参与某个组合由它的 `fits` 谓词决定，因此各模板的参与范围并不一致：
`ones_uniform_128` 需要两个 M 寄存器跨度，`multi_acc_independent` 至少需要两个累加器。
装不下的用例会被跳过，绝不悄悄重新布局。

各模板的数据类型覆盖，UDS 8/16/32：

- 整数：所有构成完整 M 寄存器的非饱和 `AME_{UINT,INT}{4,8,16,32,64,128}` 描述符
  （128 位仅 `mmulacc.2d` 覆盖）；
- 饱和：所有 `AME_*_SAT` 整数描述符；
- 浮点：`E4M3`、`E5M2`、`FP16`、`BF16`、`FP32`、`FP64`；
- 打包：所有存储宽度窄于当前 UDS 的整数描述符；
- 混合符号：当前 UDS 一半宽度的有符号描述符。

## 验证

```sh
# 单元测试：目录清单、数据类型域、寄存器布局、端到端渲染、局部标签唯一性，
# 以及 5 种配置下发射汇编的哈希与冻结清单一致。
python3 -m mmul_gen.tests
```

`tests/golden_sources.json` 冻结了 5 种配置（701 个源）发射汇编的 SHA-256，比对前把
`Auto-generated by ...` 归属注释归一化掉。模板改动一旦影响发射结果就会在这里失败，
字节级约束不依赖树里存在第二份生成器。

哈希一致只证明“发射结果没变”，不证明“能跑过”。这些源文件可编译并通过：

```sh
python3 test/ztt/run_ztt_tests.py --sim build/c_emulator/sail_riscv_sim
```

### 一个二进制对应一个 N

生成器按选定的 N 生成源文件，`run_ztt_tests.py` 也按同一个 N 建二进制并运行，因此期望值由
Python 参考实现算好后直接发射进源文件，测试内不重算。需要覆盖多个 N 时，按每个 N 各生成
一份源文件。

## 复用的仓库模块

`mmul_gen` 复用仓库中 ISA 参考数据的唯一事实来源：

- `fp_semantics` —— IEEE/OCP 边界编码、舍入模式、异常标志；
- `numeric_reference` —— 交叉校验过的精确整数矩阵乘积；
- `generator_types` —— `DType` 描述符。
