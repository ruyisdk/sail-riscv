# 模板（Templates）

每个模板一个模块，外加 `base.py`（契约）与 `__init__.py`（实例化后的清单）；
`ones_uniform.py` 是唯一一个模块内持有共享 `build` 的一对模板。模板是覆盖的最小
单位：它拥有一个数据类型域，为该域内每个数据类型构建用例，并渲染这些用例。

模板按**指令家族**分组，下面的清单也据此分节。同一个模板可以被不同家族的指令复用
（例如 `matrix_small` 服务于 6 条矩阵乘法指令中的 5 条）。

指令不含汇编。指令只列出自己覆盖的模板，因此同一个模板对象服务于所有指令——
`matrix_small` 只在这里写一次，却出现在 5 个生成源里。

```sh
# 本页所有内容的实时视图（随配置变化）。
cd sail-ame/test/ztt/gen
python3 -m mmul_gen --list --uds 8
```

## 模板文件的形状

每个模块都是同样的形状，顺序一致：

```python
"""One-line summary."""

@dataclass(frozen=True)
class SomePayload:          # what `build` decided that `render` needs
    ...

def _some_trick(...): ...   # optional: an emit fragment only this template uses

class SomeTemplate(Template):
    """Summary; also what `--list` prints (read from here, not restated)."""

    name = "some_template"
    dtypes = SOME_DOMAIN

    def fits(self, machine, instruction, dtype) -> bool:   # only when it can decline
        ...

    def build(self, machine, instruction, dtype) -> list[Case]: ...
    def render(self, machine, instruction, case, out) -> None: ...
```

payload 通常是本模块声明的 frozen dataclass，但不总是：
`mixed_signedness_multiple_square` 直接复用
`reference.mixed_signedness_product` 已经返回的 `MixedSignednessProduct` 记录，
而不是把同样的字段再声明一遍。

`build` 决定取值与布局，不产出任何汇编；`render` 依据 payload 渲染汇编与期望数据，
绝不重算期望值。`Template.__init_subclass__` 会拒绝缺少 docstring、`name` 或
`dtypes` 的子类，因此清单里不可能存在未文档化的模板。

`case_payload(PayloadType, case)` 是 `build`/`render` 边界上的类型检查：若某个用例的
payload 来自另一个模板，会立刻抛 `TypeError` 并同时报出两个类型名，而不是稍后以
`AttributeError` 收场。

## 清单

用例数取自 `--n 8 --uds 8 --m 32 --acc 4`，这是所有模板都能存活的
配置。`dtypes` 是该域在该配置下选出的描述符个数。

| 模板                               | 数据类型域             | 使用它的指令           | 用例/数据类型 | dtypes |
| ---------------------------------- | ---------------------- | ---------------------- | ------------- | ------ |
| `ones_uniform`                     | `integer`              | 仅 `mmulacc.2d`        | 4             | 8      |
| `ones_uniform_128`                 | `integer128`           | 仅 `mmulacc.2d`        | 4             | 2      |
| `matrix_small`                     | `integer`              | 除 `mmulacc.2d` 外全部 | 4             | 8      |
| `float_pair_sweep`                 | `softfloat`            | 全部 6 条              | 8             | 6      |
| `packed_small`                     | `packed_integer`       | 全部 6 条              | 4             | 2      |
| `saturating_boundary`              | `saturating_integer`   | 全部 6 条              | 4             | 8      |
| `mixed_signedness_multiple_square` | `signed_packed_source` | 全部 6 条              | 4             | 1      |
| `multi_acc_independent`            | `integer`              | 仅 `mmulacc.2d`        | 3             | 8      |

`type_register` 家族的四个模板（每个用例只选一个寄存器文件，因此只发一条布局注释）：

| 模板                      | 数据类型域    | 使用它的指令         | 用例/数据类型 | dtypes |
| ------------------------- | ------------- | -------------------- | ------------- | ------ |
| `MTypeRoundtrip`          | `every_dtype` | `msettyp`、`mgettyp` | 2             | 30     |
| `AccTypeRoundtrip`        | `every_dtype` | `asettyp`、`agettyp` | 4             | 30     |
| `MTypeUnsupportedProbe`   | `probe_dtype` | 仅 `msettyp`         | 2             | 1      |
| `AccTypeUnsupportedProbe` | `probe_dtype` | 仅 `asettyp`         | 4             | 1      |

轮转类模板对每个描述符覆盖全部寄存器放置（M 侧 low/high，ACC 侧每个累加器）；
探针类模板只在 M 寄存器文件的两个物理边界上运行，并且只针对一个描述符。

`load_store` 家族只有一个模板，两个指令共用它：

| 模板          | 数据类型域    | 使用它的指令       | 用例/数据类型 | dtypes |
| ------------- | ------------- | ------------------ | ------------- | ------ |
| `RawTransfer` | `every_dtype` | `mls.1r`、`mss.1r` | 1             | 30     |

`mls.1r` 与 `mss.1r` 的汇编完全相同（一个用例里先用 load 播种、再用 store 读回），
唯一差别是 `# case N:` 那行的助记符，所以它们是同一个模板对象的两个使用者——
这正是「指令组合模板」而不是「指令拥有模板」的例子。原始传输搬动的是整个物理寄存器
（`n² · uds / 8` 字节），与描述符无关，因此每个描述符产出同样的块，用例也不描述寄存器
布局。

`backend` 家族的四个模板没有数据类型维度（`dtypes = None`），每个配置只构造一个用例：

| 模板                  | 使用它的指令  | 场景                                       |
| --------------------- | ------------- | ------------------------------------------ |
| `AcquireReleaseState` | `ame.acquire` | 无竞争地取得所有权，状态位可观察，随后释放 |
| `AcquireBusyState`    | `ame.acquire` | 有竞争时请求被拒，且不改变状态             |
| `ReleaseState`        | `ame.release` | 释放后状态位回到 idle                      |
| `ReleaseIdleState`    | `ame.release` | 未持有时的释放是空操作                     |

四个场景共用 `backend_state.py` 里的架构常量（状态 CSR 与请求掩码）。取所有权是这些
用例**要测的东西**，所以指令家族声明 `acquires_backend = False`，头部不再插入标准前导。

`accumulator` 家族有四个模板，每个操作一个，一个模板只服务一条指令：

| 模板                 | 模板名（=`# input:` 标签） | 数据类型域 | 使用它的指令   | 用例/数据类型 | dtypes |
| -------------------- | -------------------------- | ---------- | -------------- | ------------- | ------ |
| `AccumulatorZeroAcc` | `zero_acc`                 | `integer`  | `mzero.2d.acc` | 4             | 8      |
| `AccumulatorZeroM`   | `zero_m`                   | `integer`  | `mzero.2d.m`   | 2             | 8      |
| `AccumulatorAccToM`  | `acc_to_m`                 | `integer`  | `mmov.m.a`     | 4             | 8      |
| `AccumulatorMToAcc`  | `m_to_acc`                 | `integer`  | `mmov.a.m`     | 4             | 8      |

每条用例都是「把某个寄存器文件清零、再拷贝到另一个、然后检查目标方阵全零」，所以一次全零
镜像检查同时证明了清零写满、拷贝搬全、以及没有越界破坏。四个模板共享 `accumulator_common.py`
里的基类与三个发射助手；`AccumulatorAccToM` 与 `AccumulatorZeroAcc` 的汇编相同（搬移前同样用
`mzero.2d.acc` 铺底），区别只在那行 `# input:` 标签，因此复用同一个助手而不是复制代码。

两点只在这个家族出现的细节：`AccumulatorZeroM` 是唯一不涉及累加器的模板（用例只有 M 布局）；
而 `AccumulatorMToAcc` 的目标 M 寄存器**复用**源寄存器（`MRegisterRole(..., reuse_of="ms")`），
因为结果读回时源已被累加器消费掉。另外，`accumulator` 的用例枚举**全部**累加器而不是
low/high/boundary 代表性子集——它每条用例只碰一个累加器，跳过中间某个就等于没测。

`acc_span` 家族是「**同一个源里两种用例编号**」的样板：打包（storage-only）数据类型让一个
M 寄存器装 `pack_factor = UDS / element_bits` 个方阵，于是一个累加器操作数代表一段**连续
span**。三条声明只用两个模板，而且没有家族基类：

| 模板                        | 模板名                | 数据类型域       | 使用它的指令            | 用例/指令（n8/uds8/m32/a4）                      |
| --------------------------- | --------------------- | ---------------- | ----------------------- | ------------------------------------------------ |
| `AccumulatorSpanRouting`    | `acc_span_routing`    | `packed_integer` | `mmov.m.a` / `mmov.a.m` | 12（2 个合法 span × 3 个 M 布局 × 2 个数据类型） |
| `AccumulatorSpanExceptions` | `acc_span_exceptions` | `packed_integer` | `mmov`                  | 每个数据类型 1 条                                |

两处这一族独有的设计：

- **期望值是基址的推论，不是手写清单**：routing 模板先写第一幅图，再往相邻 span 写第二幅
  重叠图，然后在 `build` 里保留「哪个累加器现在装哪个方阵」的物理映射，两次读回的期望
  因此由选中的 span 基址直接推出来——包括两段 span 重叠的位置。写死一张期望表就无法
  解释重叠。
- **用例编号有两种**：routing 的标签数字（`span6_int4_*`）与 `# case 6` 是**文件内全局**
  序号（驱动的 `case.number`），exceptions 的（`exc0_uint4_*`）是**数据类型内**下标。
  两者在同一个源里各不相同，录错会在第一个数据类型边界整段错位。

例外 recipe 把「跨出累加器文件」这条路径写成和正向测试同等强度：先用毒图铺满每个
填充基址，再把越界基址清成零，然后 `EXPECT_TRAP` 两次，最后**逐个**读回所有填充基址——
故意清零的那个读 0，其余仍读毒值。它需要 `Case.layout` 之外的一条文件级 `TRAP_GUARD_ARM`，
而驱动发布局的顺序是「`# input:` → 布局注释 → 用例体」，所以守卫被写成第一个数据类型的
**前导伪用例**，而不是改驱动或绕过布局声明。越界累加器名是这一族的**主题**，`test_generation`
的守卫也据此加强为「越界名必须落在该用例声明的 `expected illegal` span 区间内」。

这一族没有新增数据类型域：域就是 `packed_integer`（整数且窄于 UDS）。两条 routing 指令的源名带族后缀
（`mmov_m_a_acc_span.S` / `mmov_a_m_acc_span.S`），用普通类属性覆盖 `file_name` 即可，
共享的例外 recipe 用 `mmov` 作词干、`acc_span_exceptions.S` 作文件名。

`strided_memory` 家族是「**一个源里三个配方**」的样板：4 条指令（装/存 × 普通/转置）各
一个源，每条源里固定顺序发三个配方，三个配方的数据类型域各不相同，因此正好对应三个模板：

| 模板                     | 模板名                     | 数据类型域           | 配方                                                            |
| ------------------------ | -------------------------- | -------------------- | --------------------------------------------------------------- |
| `StridedNormalSquare`    | `strided_normal_square`    | `semantic`           | 整方阵按段搬，一段一个元素；stride=0 时所有段重叠在同一地址     |
| `StridedPackedStorage`   | `strided_packed_storage`   | `strided_storage`    | 位保持地搬打包镜像（每个 M 寄存器 `UDS / 元素位宽` 个逻辑方阵） |
| `StridedConversionPairs` | `strided_conversion_pairs` | `strided_conversion` | 半 UDS 存储描述符经 mconv 加宽/收窄到全 UDS 孪生后再搬          |

三条配方由 `tests/test_strided_recipe_parity.py` 逐字节校验。

两处这一族独有的细节：**转换对的编号**是无符号在前、有符号在后，所以 `strided_conversion` 域
按该顺序选出描述符，而不是复用 `pack` 家族的 `packed_conversion`；
**家族基类放在指令包**（`instructions/strided_memory/base.py`）而不是模板模块——否则
`templates/__init__` → 模板模块 → `mmul_gen.instruction` → `templates.base` 会成环，模板模块
因此用 `TYPE_CHECKING` + 鸭子类型窄化取 `transfer`。

`logexp` 家族是「12 条指令共用少数模板」的样板：差异全部写成**指令上的声明**，模板只读声明。

| 模板                         | 模板名                         | 数据类型域              | 由谁使用       |
| ---------------------------- | ------------------------------ | ----------------------- | -------------- |
| `LogExpNominal`              | `nominal`                      | `integer`               | 全部 12 条     |
| `Exp2SaturatingBoundary`     | `exp2_saturating_boundary`     | `saturating_integer`    | `mexp2.ew`     |
| `Exp2Saturating128`          | `exp2_saturating_128`          | `saturating_integer128` | `mexp2.ew`     |
| `LdexpaccSaturatingBoundary` | `ldexpacc_saturating_boundary` | `saturating_integer`    | `mldexpacc.ew` |

指令声明的字段：`src1_label`/`src2_label`（读哪个数据方阵）、`expected`（每个元素的期望值）、
`form`（`unary`/`binary_m`/`ternary_m`/`binary_x`）、`scalar`、`initialize_destination`、
`scalar_dtype_csr`。`mexp2.ew` 因此只比别的指令多两样：多声明两个模板、多声明两个输入用例。
寄存器不够时被跳过的数据类型**仍占编号**：编号是数据类型在自身模板域中的位置，因此跳过的
数据类型会在编号里留下空洞。

饱和组的两个断言是独立的：结果必须钳到最大值，**并且** `amexsat` 必须置位——只有其一通过不算过。

`axis_permute` 家族一个模板服务一条指令，**输入用例是 case 维度而不是模板维度**：
模板的 `build` 对每个数据类型返回 `len(input_cases)` 个用例，`Case.description` 就是那行
`# input: <标签>`，用例顺序与文件内的编号天然一致。

| 模板              | 模板名             | 输入用例                         | 数据类型（UDS=8） | 用例/指令 |
| ----------------- | ------------------ | -------------------------------- | ----------------- | --------- |
| `ColumnBroadcast` | `column_broadcast` | `first_column`, `last_column`    | 8                 | 16        |
| `RowBroadcast`    | `row_broadcast`    | `first_row`, `last_row`          | 8                 | 16        |
| `ColumnIndex`     | `column_index`     | `coordinate_ramp`                | 8                 | 8         |
| `RowIndex`        | `row_index`        | `coordinate_ramp`                | 8                 | 8         |
| `ColumnShift`     | `column_shift`     | `forward_shift`, `reverse_shift` | 8                 | 16        |
| `RowShift`        | `row_shift`        | `forward_shift`, `reverse_shift` | 8                 | 16        |

每条用例都往 `m0` 装一条 `1..nelem` 的斜坡源，做完行/列操作后存回目标方阵，并采样
`(0, 1, n-1, n, nelem-1)` 这五个位置——**这个元组保留、不去重**：`n = 2` 时第 2、3 项
重合，该元素会被检查两遍。广播取首/末行（列）两个用例是为了同时压住「按行读」
和「行距等于活跃长度」；移位取正/负两个方向是为了压住越界那一侧必须读成 0。

`column_index`/`row_index` 同样装载斜坡源（虽然不读它），期望值是坐标本身。

`broadcast` 家族把 `mbcast.m.x` 的**七组**数据类型写进同一个源文件，所以它是「一条指令、八个模板」
（含一个声明输入清单的 dtype-free 模板）：

| 模板                                   | 模板名                          | 数据类型域              | 用例/数据类型（UDS=8 / UDS=32） |
| -------------------------------------- | ------------------------------- | ----------------------- | ------------------------------- |
| `ScalarIngressBroadcast`               | `scalar_ingress`                | `integer`               | 8 / 4                           |
| `Integer128IngressBroadcast`           | `integer128_ingress`            | `integer128`            | 2 / 2                           |
| `SaturatingIngressBroadcast`           | `saturating_ingress`            | `saturating_integer`    | 8 / 4                           |
| `SaturatingInteger128IngressBroadcast` | `saturating_integer128_ingress` | `saturating_integer128` | 2 / 2                           |
| `PackedStorageBroadcast`               | `packed_storage_ingress`        | `packed_storage`        | 4 / 6                           |
| `FloatingBroadcast`                    | `floating_ingress`              | `softfloat`             | 6 / 2                           |
| `UnsupportedDtypeProbe`                | `unsupported_dtype_probe`       | 无（dtype-free）        | 1 / 1                           |

前四个模板（整数/128 位/饱和/饱和 128 位）只有数据类型域不同，发射体完全一样，因此共用一个
基类；后三个各自发射不同内容，各自成文件。三处只在 `broadcast` 出现的写法：

- **用例编号按组重启**：`# case N` 里的 N 是「该数据类型在自己模板域里的位置」，不是全文件计数。
- **输入清单是独立用例**：文件在第一条用例之前一次性列出 7 条 `# input:`，且与配置无关；
  把它做成声明在最前的 dtype-free 模板，既保持无条件性，又落在格式要求的唯一位置上。
- **浮点用原始位型**：广播的标量写成位模式字面量（如 `0x3c00`），不经过宿主浮点库。

两个域覆盖存储与 128 位饱和两类：`packed_storage`（`bits*2 == uds` 的**全部**描述符，含饱和与
浮点——位保持型操作不要求成对）和 `saturating_integer128`。它们在 UDS=32 时把 FP16/BF16 从
浮点组挪到存储组，所以按某一组配置的名单写死会错。

`matrix_ops` 家族是「**用声明代替分派**」最彻底的一次：20 条指令按三个操作形状分成三组，
每组只用一个模板，模板里**没有任何一处**对着助记符分派。差异全部写成指令上的三个枚举声明。

| 模板                     | 模板名                        | 数据类型域           | 使用它的指令                      | 用例/指令（n8/uds8/m32/a4） |
| ------------------------ | ----------------------------- | -------------------- | --------------------------------- | --------------------------- |
| `ReducePrefixRamp`       | `reduce_row_ramp`             | `integer`            | 10 条归约/前缀                    | 9（两个 `add.row` 为 17）   |
| `ReducePrefixSaturating` | `reduce_saturating_boundary`  | `saturating_integer` | `mreduceadd.row`/`mprefixadd.row` | 8                           |
| `ZipDualSource`          | `zip_dual_source_ramp`        | `integer`            | 4 条 zip/unzip                    | 8                           |
| `ZipExtraSource`         | `zip_extra_dtype_ramp`        | `extra_permute`      | 4 条 zip/unzip                    | 14                          |
| `GatherScatterIndexed`   | `gather_indexed_elements`     | `integer`            | 6 条 gather/scatter               | 8（`mrowscatadd` 为 16）    |
| `GatherExtraIndex`       | `gather_extra_dtype_index`    | `extra_permute`      | 仅 `mcolgather.ew`                | 14                          |
| `ScatterSaturating`      | `scatter_saturating_boundary` | `saturating_integer` | 仅 `mrowscatadd.ew`               | 8                           |

三个枚举**自己带算法**，而模板拿到的不是指令成员、是构造参数（`ReducePrefixRamp(MatrixAxis.ROW, Reduction.SUM)`
这类写法），枚举值本身仍由 `mmul_gen/instructions/matrix_ops/base.py` 声明：

| 声明                                        | 枚举                           | 取值                 | 模板用它的方式                                                                                        |
| ------------------------------------------- | ------------------------------ | -------------------- | ----------------------------------------------------------------------------------------------------- |
| `ReducePrefixInstruction.axis`              | `MatrixAxis`                   | `row`/`column`       | `line_indices`（整行/列）+ `prefix_indices` + `reduce_check_indices`/`prefix_check_indices`（采样点） |
| `ReducePrefixInstruction.reduction`         | `Reduction`                    | `sum`/`max`/`min`    | `aggregate(values)`                                                                                   |
| `ReducePrefixInstruction.prefix`            | `bool`                         | —                    | 取前缀还是整行                                                                                        |
| `ZipInstruction.axis` / `.unzip`            | `MatrixAxis` / `bool`          | —                    | `varying`（谁是被交织的坐标）+ `result_index`（结果落在哪）                                           |
| `GatherScatterInstruction.axis` / `.access` | `MatrixAxis` / `ScatterAccess` | `gather`/`add`/`max` | `source_index`（读哪）+ `result_index`（写哪）+ `combine`/`accumulates`/`by_max`                      |

10 条归约/前缀指令其实是 `axis × reduction × prefix` 的 10 个组合（`row×sum×reduce` =
`mreduceadd.row`，`column×sum×prefix` = `mprefixadd.col` …），所以「一条指令一个期望值表」被
一条通用公式取代。`extra_permute` 域（`bits >= uds` 且不是普通整数）
正是这一族需要的：zip 和 gather 要三个互不重叠的寄存器组，所以它们跑饱和与浮点描述符。

三个只在 `matrix_ops` 出现的写法：

- **零用例也发 `.data`**：整族在「所有类型都放不下」的配置下仍产出 `.data` 段（空的），
  所以三个家族基类都声明 `always_emits_data = True`。
- **采样点是形状的函数而不是助记符的函数**：归约采样 `(0, n-1, nelem-1)`、前缀按轴采样
  `(0, 3, n+2)` 或 `(0, n, 2n+3)`，写成 `MatrixAxis` 的方法。
- **寄存器组数检查不对称**：zip 的普通分支不检查 `2*nregs <= num_m_regs`，extra 分支会跳过
  放不下的类型。

`float_math` 家族是「**一个模板装下整族**」的样板：10 条指令只声明一个 `MathOperation`
枚举成员，整族只有**一个**发射模板——因为生成文件是**按数据类型交错**的：每个数据类型先发它
的 nominal 用例，再发它自己的 boundary 场景，然后才轮到下一个数据类型。框架的管线是
「模板 → 数据类型」，两个模板会把顺序变成「所有 nominal，再所有 boundary」，那是另一个文件。
所以 nominal / boundary / transcendental 三种发射体是同一个模板的三个私有方法，用
`Case.payload` 区分。

| 模板             | 模板名             | 数据类型域         | 使用它的指令 | 用例/指令（n8/uds8/m32/a4）   |
| ---------------- | ------------------ | ------------------ | ------------ | ----------------------------- |
| `FloatMathCases` | `float_math_cases` | `formed_softfloat` | 全部 10 条   | 见下表（清单 1 + 每类型若干） |

用例数按操作类别分（含那 1 条清单用例）：

| 类别       | 指令               | 每个数据类型                                                  | 用例数 |
| ---------- | ------------------ | ------------------------------------------------------------- | ------ |
| 取整       | `mfrintm/n/p/z.ew` | 1 nominal + 6 个舍入模式                                      | 43     |
| 倒数       | `mrec.ew`          | 1 + 24（±0 的 12 个极点 + ±最小次正规的 12 个溢出）           | 151    |
| 倒数平方根 | `mrsqrt.ew`        | 1 + 18（12 个极点 + 6 个负数无效）                            | 115    |
| 平方根     | `msqrt.ew`         | 1 + 12（6 个负数无效 + 6 个 √2 不精确）                       | 79     |
| 超越函数   | `mcos/sin/tanh.ew` | 6（±0、qNaN、±inf、1.0 数值用例；E4M3 没有 inf 编码，只有 4） | 35     |

| 声明        | 取值                    | 说明                                                                        |
| ----------- | ----------------------- | --------------------------------------------------------------------------- |
| `operation` | 10 个成员，一条指令一个 | 枚举成员自己带 nominal 激励、boundary 场景、以及超越函数的 host libm 入口名 |

三处只在 `float_math` 出现的写法：

- **域要用 formed 版本**：`formed_softfloat`。`softfloat` 走 `semantic_dtypes`（`mmul` 用的就是
  它），而这一族走 `formed_dtypes`——UDS=16 时 8 位的 OCP 格式是打包存储、仍要覆盖，
  用错域会整整少两个数据类型。
- **期望值来自 host libm，而不是表**：超越函数的窄格式用例复刻仿真器的路径（加宽到 f32 →
  调用**宿主机**的 `cosf`/`sinf`/`tanhf` → 按 RNE 窄化回来），并在生成期用 30 位 mpmath
  参考做 2 ulp 预算的交叉校验——宿主机 libm 漂移会在生成期炸掉，而不是在测试里变成偶发失败。
- **参考表整模块复用**：位模式表来自 `mmul_gen/fp_semantics.py`，由
  `tests/test_fp_semantics_parity.py` 对每张表、每条规则做等值守卫。

`integer_shift` 家族有两个模板，按「移位量从哪来」分，而不是按指令分：三条移位指令
（`msll`/`msrl`/`msra`）各自选用其中一个，所以一个模板服务三条指令。

| 模板                  | 模板名                  | 数据类型域       | 使用它的指令                        | 用例/数据类型 | dtypes            |
| --------------------- | ----------------------- | ---------------- | ----------------------------------- | ------------- | ----------------- |
| `ShiftRegisterSource` | `shift_register_source` | `formed_integer` | `msll.ew`/`msrl.ew`/`msra.ew`       | 1             | 10（`msra` 为 5） |
| `ShiftScalarSource`   | `shift_scalar_source`   | `formed_integer` | `msll.ew.x`/`msrl.ew.x`/`msra.ew.x` | 1             | 10（`msra` 为 5） |

两者只有「移位量从哪来」不同：寄存器形式从第二个 M 操作数读每个元素各自的量，标量形式
复用同一个整数寄存器。移位量的取值走 `0, 1, bits-1, bits, bits+1, 2*bits-1` 的边界扫描——
**等于和超过元素宽度的量**才能压出硬件对移位量的取模约简，而「常量移位」的测试永远碰不到。
源图案则让每个元素的符号位恒为 1。

这个家族第一次用到了框架的三处新能力：

- `formed_integer` 域（`machine.formed_dtypes`）比 `integer` 域多出**子 UDS** 的 4/8 位描述符，
  所以 `AME_UINT4_DTYPE` 这类窄类型也进了用例；四位元素把两个半字节打包在同一行 `.byte` 上
  （不拆行，否则字节就不一致了）。
- `choose_m_group_base(num_m_regs, bits, uds, preferred=16)` 保留首选的 `m16` 基址，寄存器
  文件不够大时退回最后一个对齐的组。
- `fits(machine, instruction, dtype)` 现在能看到指令：`msra` 比其他两条多一条限制——只有
  有符号描述符才有算术右移语义，而三条指令共用同一个模板，限制属于**操作**而不属于模板。

`memory_order` 家族有两个模板，每个方向一个，每个方向被它的加载与存储指令共用：

| 模板                  | 数据类型域 | 使用它的指令       | 用例/数据类型 | dtypes |
| --------------------- | ---------- | ------------------ | ------------- | ------ |
| `MemoryOrderRowToCol` | `integer`  | `mls.rm`、`mss.cm` | 1             | 8      |
| `MemoryOrderColToRow` | `integer`  | `mls.cm`、`mss.rm` | 1             | 8      |

一个用例里同时执行「以某种主序加载、再以另一种主序存回」这一整个往返，所以 `mls.rm` 与
`mss.cm` 的汇编完全相同，只有头部和 `# case` 那行不同——又是一个模板服务两条指令的例子。
两个方向互为逆变换，所以期望值刚好对调（第二个元素与下一存储行首元素分别是 `N+1`/`2` 还是
`2`/`N+1`）。`# input:` 标签只在整个 dtype 循环之前出现一次，由「首个 dtype 的用例带
`description`、其余为 `None`」表达（`raw_transfer` 同一个模式）。

`debug_move` 家族有四个模板，每个宽度一个，每个宽度被两条指令共用：

| 模板          | 数据类型域   | 使用它的指令                 | 用例/数据类型 | dtypes |
| ------------- | ------------ | ---------------------------- | ------------- | ------ |
| `DebugMove8`  | 无（`None`） | `mmove8.m.x`、`mmove8.x.m`   | 1             | —      |
| `DebugMove16` | 无（`None`） | `mmove16.m.x`、`mmove16.x.m` | 1             | —      |
| `DebugMove32` | 无（`None`） | `mmove32.m.x`、`mmove32.x.m` | 1             | —      |
| `DebugMove64` | 无（`None`） | `mmove64.m.x`、`mmove64.x.m` | 1             | —      |

四条指令的用例都同时走两个方向（写进 M 寄存器、再读回来），所以 `.m.x` 与 `.x.m` 的汇编
**完全相同**，只有头部那行不同——这就是「一个模板服务两条指令」而不是写两份近乎相同的模板。
四个模板共享 `debug_move_common.py` 的家族基类，子类只声明三个常量（`element_bits`、
`position`、`value`）。

这个家族也是唯一一个**源集合随配置变化**的：宽度超过一行（`n * uds` 位）的指令在该配置下
整个源都不生成，因为模型对它报 Illegal Instruction，没什么可测的。所以 `n=4, uds=8` 时
只有 6 个源，`n=8, uds=8` 起才有 8 个。

`pack` 家族有两个模板，共享 `pack_common.py` 的形状与三个输入模式：

| 模板          | 数据类型域          | 使用它的指令      | 用例/数据类型 | dtypes |
| ------------- | ------------------- | ----------------- | ------------- | ------ |
| `PackSlots`   | `packed_conversion` | 仅 `mpack.ew.x`   | 3             | 2      |
| `UnpackSlots` | `packed_conversion` | 仅 `munpack.ew.x` | 3             | 2      |

两个模板都继承 `pack_common.py` 里的 dtype-free 家族基类 `PackedSlotConversion`，输入模式
固定为 `selected_slot` / `preserved_slot` / `signed_boundary_values` 三种，选中槽恒为 3。
「选中槽被写对、未选中的槽一个字节都没被动、符号边界值正确」这三件事必须分开测，所以是
三个用例而不是一个用例里的三段——任何一个失败都能立刻定位到是哪一类错误。

`mconv` 家族只有一个模板，也是唯一一个同时被两个方向的转换使用的模板：

| 模板             | 数据类型域          | 使用它的指令 | 用例/数据类型 | dtypes |
| ---------------- | ------------------- | ------------ | ------------- | ------ |
| `MconvRoundtrip` | `packed_conversion` | `mconv.ew`   | 1             | 2      |

`mconv.ew` 同时做两个方向的转换（把 packed 存储方阵展宽、再把两个 compute 方阵收窄
回去），所以只能用一个模板。它的数据类型域在该配置下选出**两个**描述符（无符号、有符号各
一个），每个描述符产出**一个**用例，期望值在七个边界值之间轮转。它的头部还有一行 `UDS=<uds>: storage=<uds/2>, compute=<uds>`，
由指令文件覆盖 `banner(machine)` 追加。

每数据类型用例数就是 `paired_cases` 为该数据类型找到的、合法的 M/ACC 布局配对数，
因此它随配置变化，寄存器变少时下降。在
`--m 16 --acc 1` 下：`ones_uniform`、`matrix_small`、
`saturating_boundary` 变成 1 或 3，`float_pair_sweep` 变成 2 或 6，`packed_small` 与
`mixed_signedness_multiple_square` 为 3，而 `ones_uniform_128` 与
`multi_acc_independent` 完全不运行——它们的 `fits` 谓词直接拒绝该配置，而不是把操作数
重新布局。

`elementwise` 是唯一一个**场景写在指令里**的家族：7 个场景类，一条指令跑哪几个由它自己的
`templates` 列表决定——列表就是会跑的清单，没写进去的行为在这条指令身上不存在。所以 `--list`
报的是每条指令自己的场景数：`mand.ew` 报 2 个、`madd.ew` 报 7 个，而不是人人都报 7 个。这 7 个
模板按用例在源里出现的顺序排列：

| 模板                                  | 数据类型域                  | 实际发用例的指令 | 总用例（`--m 32`） | dtypes | 条目怎么构造                                          |
| ------------------------------------- | --------------------------- | ---------------- | ------------------ | ------ | ----------------------------------------------------- |
| `elementwise_integer_value_rules`     | `formed_integer`            | 46/46            | 2040               | 10     | 46/46（整数清单 + 该指令的 `evaluate`）               |
| `elementwise_integer_value_rules_128` | `integer128`                | 46/46            | 268                | 2      | 46/46（同上，用 `wide=True`）                         |
| `elementwise_saturating_boundary`     | `formed_saturating_integer` | 7/46             | 65                 | 10     | `SaturatingExpectation` + `CasePlan`                  |
| `elementwise_saturating_boundary_128` | `saturating_integer128`     | 6/46             | 11                 | 2      | 同上                                                  |
| `elementwise_float_nominal`           | `formed_softfloat`          | 27/46            | 162                | 6      | 该指令的 `evaluate_float`（比较类 `comparison=True`） |
| `elementwise_float_special_values`    | `formed_softfloat`          | 27/46            | 541                | 6      | `FloatArithmeticRole` 或 `FloatSpecialRole`           |
| `elementwise_float_semantics_sweep`   | `formed_softfloat`          | 18/46            | 108                | 6      | `FloatArithmeticRole`                                 |

「实际发用例的指令」这一列不是手写的，而是**从 46 个类的 `templates` 里数出来的**：
7 = `SATURATING_EXPECTED_KIND` 的条目数，6 = `SATURATING_128_INSTRUCTIONS`，
27 = `FLOAT_EXPECTED_KEYS`（23 条标称 + 4 条比较），27 = 9 条特例 + 18 条算术特例，18 =
`ELEMENTWISE_FP_ROUNDING_INSTRUCTIONS`。列表一变，这四个数字会立刻变化。

"哪个场景跑"由指令决定，而且只有一处：指令把要跑的模板**逐个构造**进 `templates`，值当场传进
构造函数——**没有别的门**，没写进列表的模板就不跑，所以指令文件就是它完整的检验清单。128 位的
那两条跟在各自根后面，拿同一份值。场景类的先后由 `ELEMENTWISE_TEMPLATE_CLASSES` 给出，测试对
每条指令的列表核对。
两者合起来由 `test_elementwise_template_table_parity.py` 逐点比对（46 指令 × 7 场景 × 120
配置），所以顺序错、参数给错、少一个场景都会立刻变成对拍失败。场景本身只回答"这个配置放得下
我的用例吗"，也不去猜指令有没有这条行为。

整数两条模板拿的是"清单 + 算式"，浮点标称拿的是"算式 + 一个 `comparison` 标志"——两条路都是类里写
的函数，区别只在函数体：整数是算术，浮点标称是查 `FLOAT_OPERATION_VALUES`（比较类给全 1/0，并靠
那个标志播种目的地与走三组 M 寄存器的规则）。另外两格拿的是 role，因为它们的期望值是一组用例而不
是一个数。
前四个模板把"整数/饱和"和"128 位"分开，是因为 128 位数据类型的用例构造与期望值算完全不同
（跨多个 M 寄存器）；浮点三个模板共用 `formed_softfloat` 域，但各自筛不同的指令：标称、
特例（NaN/无穷/有符号零与无效运算）、舍入扫描。`float_special_values` 的 6 个 dtype 中有一个只发 1 个用例、
其余各发 3 个，差别来自 `NO_INFINITY_DTYPES`——`AME_OCP_E4M3_DTYPE` 没有无穷编码，所以它没有无穷用例。

浮点场景的**用例数随配置变化**：`float_semantics_sweep` 只在声明了 `float_arithmetic` 且
不是标量形式的指令上发用例（标量形式的舍入路径不同，另有两个块覆盖）；三元形式的
`float_special_values` 用目的地的 NaN 而不是加数的 NaN，这些差异都在模板内部按 `form` 分派，
不需要指令文件各写一份。

## 逐个模板

### `ones_uniform` —— 全寄存器冒烟测试

- **覆盖** 所有能构成完整 M 寄存器的非饱和整数。
- **激励** 两个源方阵全为 1，累加器用 `mzero.2d.acc` 清零，因此目标值就是 N 个 1×1
  乘积之和。
- **期望值** `uniform_ones_product` = N；当指令对乘积取负时为 −N。
- **自检** 逐字节加载首元素、次元素、末元素的起始字节，各自与期望字节比对
  （`check_dst_lines`）。
- **为什么需要它** 这是最廉价的、可能失败的测试。没有任何取值依赖位置、符号、打包或
  饱和，所以这里一旦失败，问题必定出在形成方式、数据类型或累加/相减语义上，而不是
  数值本身。
- **谁在用** 仅 `mmulacc.2d`：它是唯一一条在得到新乘积后仅靠 `mmov.m.a` 读回累加器
  的指令，这正是"累加器已清零、图像均匀"这个用例有意义的前提。

### `ones_uniform_128` —— 跨多个寄存器的目标

- **覆盖** `AME_{UINT,INT}128`，即跨多个 M 寄存器的描述符。
- **激励与期望值** 原样继承 `ones_uniform`；只有渲染器、数据类型域与谓词不同。
- **自检** 比对首尾两个 128 位元素。128 位元素的值是每个 16 字节槽中**首字节**里的 N
  （取负时其余字节二补数填充），因此端点比对校验的是跨寄存器图像的地址与布局。
- **为什么需要它** 128 位目标是 M 寄存器跨寄存器形成、以及 `movv.m.a` 多寄存器回写
  出问题的地方。
- **谁在用** 仅 `mmulacc.2d`，且仅在两个 M 寄存器跨度都装得下时。

### `matrix_small` —— 位置相关的乘积

- **覆盖** 所有构成完整 M 寄存器的非饱和整数。
- **激励** `small_matrix_inputs` 按行主序构造
  `a[i][j] = (i + 2j + 1) mod 3`、`b[i][j] = (2i + j + 2) mod 3`。取值恒小于 3，
  因此精确乘积在此处所有数据类型下都可表示。
- **期望值** `small_matrix_product` 精确重放点积，并施加指令的 `product_flags`
  （左转置、右转置、取负）。
- **自检** 检查 5 个元素位置——首元素、次元素、第二行首元素、方阵中部某位、末元素
  （`check_dst_element_lines`）——这正是让"位置相关性"真正可观测的原因。
- **为什么需要它** 它是唯一期望值依赖行与列的整数模板，因此能抓到均匀方阵看不见的
  步长、索引、行列混淆。转置变体也是在这里被区分的：`reference.py` 按指令的
  `product_flags` 重放点积，因此转置只在发射出的期望值上体现，激励与代码逐字节相同。
- **谁在用** 5 条普通乘积指令；`mmulacc.2d` 改用 `ones_uniform`。

### `float_pair_sweep` —— 一个模板，两种 payload

- **覆盖** `E4M3`、`E5M2`、`FP16`、`BF16`、`FP32`、`FP64`。
- **激励与期望值** 两种 payload，在 `render` 中分派：
  - `FloatNominalPayload` —— 全 1 乘积，可精确表示，期望值为
    `softfloat_product_expected`，即 2 的幂形式的 N（窄格式受尾数位宽限制）。
  - `FloatOverflowPayload` —— 最大有限值乘 2，遍历所有舍入模式与正负号，期望值按模式
    取自 `float_overflow_boundaries`。
- **自检** nominal 比对期望方阵；overflow 另外断言异常标志（对 `fflags` 的 `EXPECT`
  为 inexact），并与无穷大图像一同校验。
- **为什么需要它** 它是唯一检查**标志位**而不只是数据的模板，也是唯一覆盖舍入模式的
  模板。overflow 扫描正是让舍入模式或标志位传递的回归暴露出来的地方。
- **谁在用** 全部 6 条指令。

### `packed_small` —— 存储宽度窄于 UDS 的源

- **覆盖** 所有存储宽度窄于当前 UDS 的整数描述符。
- **激励** 左手 1、右手 2，做累加。打包指令会把一行中每个存储槽折叠进目标元素，因此
  期望值为 `2 * pack * N`，其中 `pack = uds / element_bits`。
- **期望值** `packed_product`，目标数据类型由 `packed_compute_dtype` 选出——是整寄存器
  类型，而不是存储类型。
- **自检** 比对整寄存器目标图像的首尾元素（`check_dst_lines`）。
- **为什么需要它** 源存储宽度与目标形成宽度不同，因此它是抓加宽或回写错误的地方。
  目标数据类型选错会改变存储图像，而任何同宽模板都发现不了。
- **谁在用** 全部 6 条指令。

### `saturating_boundary` —— 数据加异常标志

- **覆盖** `AME_*_SAT` 整数描述符。
- **激励** 单次累加：全 1 乘以可表示的最大值。若参考乘积**没有**真的饱和，
  `saturating_edge_product` 会直接抛错，因此当激励不再触及边界时是生成期失败，而不是
  悄悄退化成一个普通边界测试。
- **期望值** 饱和后的结果，外加 `amexsat` 读到 1，用 `EXPECT` 断言。
- **自检** 检查首尾元素（`check_dst_element_lines`），并单独断言 `amexsat`。
- **为什么需要它** 它是唯一断言饱和被**上报**、而不仅仅是被钳住的整数模板。回绕型
  回归与标志位缺失是两类不同的缺陷，这里是唯一把两者同时钉住的地方。
- **谁在用** 全部 6 条指令，且仅在两个 M 寄存器跨度都装得下时。

### `multi_acc_independent` —— 一个累加器顶不了另一个

- **覆盖** 非饱和的整寄存器整数。
- **激励** 每个合法累加器都用 `mmov.a.m` 以 `0x11 * (index + 1)` 播种，然后把同一个
  全 1 乘积累加进所有累加器，最后各自读回到自己的目标方阵。
- **期望值** `seeded_ones_product` = seed + N，逐累加器。
- **自检** 每个累加器的目标方阵独立比对（`check_dst_lines`），且各自有独立的数据标签
  （`..._acc0_dst`、`..._acc1_dst`……），因此不一致时能指出是哪个累加器。
- **为什么需要它** 种子互不相同且有间隔，因此"某个累加器串到另一个"或"某个操作数把两个
  累加器别名到同一寄存器"会立刻改变存储结果。均匀种子会掩盖这一切。
- **谁在用** 仅 `mmulacc.2d`，且仅在至少存在两个累加器时。

### `mixed_signedness_multiple_square` —— 一个操作数装两个方阵

- **覆盖** 半个当前 UDS 宽度的有符号整数描述符。
- **激励** `_packed_square_data_lines` 把两个**逻辑**方阵（符号与取值都不同）打包进
  同一个物理形成的操作数，因此一次 `mls.rm` 加载就能同时得到两者。
- **期望值** `mixed_signedness_product` 返回一个 `MixedSignednessProduct`，描述两半；
  校验按几何宽度而非元素宽度进行。
- **自检** 把存储方阵与期望图像逐个字节比对（`check_dst_lines`），按几何宽度而非元素
  宽度进行。
- **为什么需要它** 它是唯一"一个操作数内装两个不同符号方阵"的模板，打包源的符号扩展
  与"乘积是否读了两半"都在这里裁定。
- **谁在用** 全部 6 条指令。

### `MTypeRoundtrip` / `AccTypeRoundtrip` —— 描述符往返

对宏文件里声明的**每一个**描述符（`every_dtype`，不做 UDS 过滤：往返不形成操作数，
所以没有存储比例可言），把类型码写进寄存器再读回，并与类型码宏比较。M 侧覆盖每个
合法放置（跨越 1/2/4/8/16 个寄存器时分别落在 low 与 high），ACC 侧覆盖每个累加器。
`# case N:` 行的说明文字来自指令的 `case_action`，因为那句话同时点了写入方与读出方。

### `MTypeUnsupportedProbe` / `AccTypeUnsupportedProbe` —— 非法类型码

先把寄存器播种成 `AME_INT8_DTYPE`，再送入编码之外的 `0x80000008`：状态位必须报告
拒绝，且描述符必须仍读出播种值。这是**错误路径**的覆盖，与往返模板是两回事，所以
是独立的模板而不是往返模板里的一个分支。

## 检查机制

生成器只输出**静态 N** 形式：N 在生成期已知，因此期望值可以精确算好后作为立即数发射，
检查也只需比对固定的几个位置。全部渲染器共用两个原语：

| 原语                      | 用途                                           |
| ------------------------- | ---------------------------------------------- |
| `check_dst_lines`         | 均匀期望方阵：比对首元素与末元素               |
| `check_dst_element_lines` | 位置相关的期望方阵：比对恰好一个指定下标的元素 |

两者都带元素下标，因此断言本身指明它检查的位置；比对通过 `EXPECT` 宏完成，失败时
`RVMODEL_HALT_FAIL` 向 `tohost` 写入统一码 3——也就是说，静态形式只告诉你**这个源失败了**，
定位靠读汇编。这一点比下面提到的运行期编码粗，但它就是这 720 个生成源一直以来实际使用的
方式。

### 为什么没有 `--generic-n`

早期版本还支持一个 `--generic-n` 模式：表按最大 N 生成、检查循环以运行期读到的
`amenlen` 为界，于是一个二进制可以配合同一批 ≤ 32 的不同 N 配置运行。它已被移除。

原因是它与静态 N 的**目标冲突**：N 一变期望值就变，而二进制里的立即数是生成期固定的。
所以 `--generic-n` 只能改用在测试内用汇编重算期望值，用放弃"期望值来自 Python 参考实现"
这一强保证，换取"一个二进制跨 N"。而那个"跨 N"能力在本项目里没有需求方：
`run_ztt_tests.py` 为每个组合渲染一份模型配置，永远是按 N 建二进制、再按同一个 N 跑。
更要紧的是，一个二进制能覆盖的 N 值并没有变多——N 在模型里是 2 的幂，32 以下的幂正好是
4/8/16/32，与静态矩阵相同。

如果将来确实需要"一个二进制覆盖多种 N 配置"，正确做法是把每个受支持 N 的期望值都打进
二进制、再按 `amenlen` 在运行期选择，而不是在测试内重算公式；但这需要真实需求才值得引入。

## 继承与复用

只有一个模板继承另一个：`OnesUniform128` 继承 `OnesUniform`，覆盖 `render`、
`dtypes`、`fits`，并原样继承 `build`。这是整个生成器里唯一一处模板体通过继承被真正
共享的地方，也是应当遵循的范式：当用例构造完全相同、只有渲染或适用域不同时才用子类。

`FloatPairSweep` 展示了另一处接缝——`render` 分派到 `self._render_nominal` /
`self._render_overflow`，于是"一个模板有两种 payload 形状"可以保持一个公开入口、两个
私有实现。

指令复用模板靠的是**组合**而非继承：它们持有同一批实例。6 条指令共享
`float_pair_sweep`、`packed_small`、`saturating_boundary` 与
`mixed_signedness_multiple_square`；5 条共享 `matrix_small`；只有 `mmulacc.2d` 额外
加上 `ones_uniform`、`ones_uniform_128` 与 `multi_acc_independent`。
`mmul_gen.tests.test_templates` 同时钉住了"同一对象被共享"与上面那条继承关系。

## 新增一个模板

1. 新增 `<name>.py`，写入 payload、类与 docstring。
2. 在 `__init__.py` 中实例化，并加入 `ALL_TEMPLATES`。
3. 在需要覆盖它的每条指令的 `templates` 元组中加入该实例。
4. 在上层 README 的覆盖表中补一行。

`build` 与 `render` 是唯一的必需成员；只有当模板需要多于一个 M 寄存器跨度时才需要
`fits`。除新模块与上面两处声明之外，不需要改动任何东西。
