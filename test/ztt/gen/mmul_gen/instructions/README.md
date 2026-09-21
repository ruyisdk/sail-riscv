# 指令声明（`mmul_gen/instructions`）

一条指令 = 一个文件。文件名是助记符把小写点和横线换成下划线的形式（`mcmovge.ew` →
`mcmovge_ew.py`），文件里一个类，类名是助记符的驼峰形式（`McmovgeEw`）。

## 打开一个指令文件，应该看到它自己

纯整数指令只声明形态、算式，和跑整数检验的那两个模板：

```python
class McmovgeEw(ElementwiseInstruction):
    """Conditional move when greater-or-equal of two matrix operands into the destination."""

    name = "mcmovge.ew"
    summary = "conditional move when greater-or-equal of two matrix operands into the destination"
    subject = "elementwise test cases."
    operands = ()
    form = ElementwiseForm.TERNARY_M

    def evaluate(self, elements: IntegerElements) -> int:
        """``D = B`` when ``A >= 0``, else ``D`` keeps its value; the M form
        shares ``D`` and ``A``."""

        return elements.rhs if elements.lhs >= 0 else elements.dest

    #: Every template this instruction runs, in the order its cases appear.
    templates = (
        ElementwiseIntegerValueRules(BASE_INTEGER_INPUT_CASES, evaluate),
        ElementwiseIntegerValueRules128(BASE_INTEGER_INPUT_CASES, evaluate),
    )
```

一条指令把自己的模板全写出来，每个模板构造时就带上它要检验的值。两个模板系列都拿**函数**：整数
模板拿清单和算式 `evaluate`，浮点标称模板拿 `evaluate_float`。函数都定义在列表之前，因为它们是这
条指令自己的方法，要先有名字才能当参数递过去：

```python
class MaddEw(ElementwiseInstruction):
    """Add of two matrix operands."""

    name = "madd.ew"
    summary = "add of two matrix operands"
    subject = "elementwise test cases."
    operands = ()
    form = ElementwiseForm.BINARY_M

    def evaluate(self, elements: IntegerElements) -> int:
        """``D = A + B`` element by element."""

        return elements.lhs + elements.rhs

    def evaluate_float(self, dtype_name: str, element_bits: int) -> int:
        """The softfloat model's nominal ``add`` operand is this instruction's answer."""

        return FLOAT_OPERATION_VALUES[dtype_name]["add"]

    #: Every template this instruction runs, in the order its cases appear.
    templates = (
        ElementwiseIntegerValueRules(BASE_INTEGER_INPUT_CASES + (
            overflow(IntegerInputKind.ADD, downward=False),
        ), evaluate),
        ElementwiseIntegerValueRules128(BASE_INTEGER_INPUT_CASES + (
            overflow(IntegerInputKind.ADD, downward=False),
        ), evaluate),
        ElementwiseSaturatingBoundary(
            SaturatingExpectation.MAX,
            CasePlan(vector_operands("max", "one"), ZERO, (ZERO, SOURCE)),
        ),
        ElementwiseSaturatingBoundary128(
            SaturatingExpectation.MAX,
            CasePlan(vector_operands("max", "one"), ZERO, (ZERO, SOURCE)),
        ),
        ElementwiseFloatNominal(evaluate_float),
        ElementwiseFloatSpecialValues(FloatArithmeticRole.ADD),
        ElementwiseFloatSemanticsSweep(FloatArithmeticRole.ADD),
    )
```

## 指令怎么把参数交给模板

家族基类**不预留任何可选槽**：一条指令没有的行为就不存在。也没有"先声明值、再由框架按名字筛出
场景"这一层——**模板构造时就拿到自己的值**，指令把要跑的模板逐个列进 `templates`：

```python
class MandEw(ElementwiseInstruction):        # 纯整数指令，只有整数检验
    form = ElementwiseForm.BINARY_M

    def evaluate(self, elements: IntegerElements) -> int:
        return elements.lhs & elements.rhs

    templates = (
        ElementwiseIntegerValueRules(BASE_INTEGER_INPUT_CASES, evaluate),
        ElementwiseIntegerValueRules128(BASE_INTEGER_INPUT_CASES, evaluate),
    )
```

每个模板拿到的都是"**怎么得到期望值**"，而且都是类里写的函数：整数模板拿 `evaluate`，浮点标称模板
拿 `evaluate_float`——它的体通常是一次查表（`FLOAT_OPERATION_VALUES`），比较
类返回全 1 或 0。另外两格拿到的不是函数而是 role：特殊值和舍入格每格是几十上百个用例（同一对操作
数换 6 种舍入模式、换 NaN/±0/无穷等特殊操作数），不是一个"给一次运算返回一个数"的函数能装的，所以
指令在那里声明的是"**套哪一组用例**"。

类体读起来就是"这条指令跑哪些模板、每个模板检验什么"：没列出的模板在它身上不存在，因此不跑，
`templates` 就是它完整的检验清单。列表按源里场景段的先后写；两条 128 位模板（`...128` 结尾的
两个类）跟在各自的根后面，拿的是同一份值。写错类名会当场 `NameError`；写错值的类型由类型检查器
在构造那一行就报出来。顺序写错、或者漏掉一条 128 位模板，由 `test_elementwise_template_table_parity.py`
逐个指令核对。

| 声明                           | 含义                                                                                       | 谁读它                                                |
| ------------------------------ | ------------------------------------------------------------------------------------------ | ----------------------------------------------------- |
| `name` / `summary` / `subject` | 助记符与文档属性                                                                           | `catalog`、`--list`                                   |
| `form`                         | 操作数形态（`BINARY_M` / `BINARY_X` / `TERNARY_M` / `TERNARY_X` / `MOVE_M` / `UNARY_ABS`） | 全部 7 个场景（整数取操作数、发射器选计划、浮点分派） |
| `evaluate`                     | **这条指令在一个元素上算出的精确结果**；作为参数交给两条整数模板                           | 模板持有它的副本，`integer_expected` 用它算每个用例   |
| `templates`                    | **这条指令跑的模板，按源里的先后**，每个模板自己带着要检验的值                             | 驱动按这个列表逐模板建用例                            |

`templates` 里能出现的五个场景类，以及构造它们时要传什么：

| 场景类                           | 构造参数（直接列在 `__init__` 里）                                                         |
| -------------------------------- | ------------------------------------------------------------------------------------------ |
| `ElementwiseIntegerValueRules`   | **整数输入用例清单**（按源里发用例的顺序）+ 这条指令的 `evaluate`                          |
| `ElementwiseSaturatingBoundary`  | `SaturatingExpectation`（往哪一端夹）+ `CasePlan`（哪些方块把它推过去）                    |
| `ElementwiseFloatNominal`        | 这条指令的 `evaluate_float`；比较类再加 `comparison=True`                                  |
| `ElementwiseFloatSpecialValues`  | 算术类给 `FloatArithmeticRole`，比较类给 `FloatSpecialRole.COMPARE_TRUE` / `COMPARE_FALSE` |
| `ElementwiseFloatSemanticsSweep` | `FloatArithmeticRole`（无效运算向量）                                                      |

每个场景拿到的都是**它自己的构造参数**，没有包装类型：饱和那一对拿期望值和操作数计划两个参数，
特殊值场景拿一个 role——`FloatArithmeticRole`（无效运算向量）或 `FloatSpecialRole`（特例行为，
比较的两种结果各占一个成员，所以"比较成不成立"不需要第二个可选参数）。一个模板一个值，所以
"特殊值场景既可能读 special、又可能读 role"这种"或"关系不存在了：一条指令传给它的那一个值就说
明了它是什么（46 条指令里没有一条两者都要）。128 位的那两条属于同一对，值必须一样——
`test_elementwise_template_table_parity.py` 会核对期望值与计划都一致。

**怎么读一个类**：拿 `madd.ew` 来说，AME 没有硬件浮点，浮点语义由 `fp_semantics.py` 这个软件模型
给出——它为每个浮点 dtype 存了一组名义位模式（E4M3 下 `a`=0x3C 即 1.5、`b`=0x40 即
2.0、`add`=0x46 即 3.5）。软浮点场景就是把 `a`/`b` 按 FP8/FP16 装载、跑 `madd.ew`、逐位比对结果是不是
`FLOAT_OPERATION_VALUES[DTYPE]["add"]`。所以类里那个
`def evaluate_float(...)` 读作"**这条指令的软浮点名义答案就是名册里的 `add` 那一项**"，模板那条
`ElementwiseFloatNominal(evaluate_float)` 就是把它交出去；同一个 `FloatArithmeticRole.ADD` 出现在特殊值场景和舍入扫描两个条目里（它们是 ADD 的
无效运算向量），两个条目并排写着，在指令类里直接看得到。`madd.ew` 既是整数加法，也是这套测试里的软浮点加法。判断"某条指令支不支持浮点"最快的
办法是 `python3 -m mmul_gen --list`：`madd.ew` 会列出 3 个软浮点场景、`formed_softfloat` 域和
FP16/BF16/FP32/FP64/E4M3/E5M2 六个 dtype。

没写进 `templates` 就是**那条行为不存在**，对应模板不跑——这是家族表达"这条指令没有这种情况"
的方式。词汇不会写错得静悄悄：类名拼错是 `NameError`，`templates` 里的条目必须是七个场景类之一
（`mmul_gen/tests/test_elementwise_declarations.py`）。整套架构由 `mmul_gen/tests/test_architecture.py` 守着：
**全部 141 条指令**的类上除身份、公式和 elementwise 自己的 `form` 之外不许再有别的成员，任何模板也不许
回读家族数据——包括用 `getattr(instruction, "…")` 把名字藏起来。真正的兜底仍是 120 个配置的逐字节对拍。

整数清单也是模板参数，写法是组合：四项通用用例（`small_values` / `boundaries` /
`power_of_two` / `bit_patterns`）是全族不变量，`BASE_INTEGER_INPUT_CASES` 在家族基类写一次；
有溢出用例的指令把它接在后面，没有的就只写 `BASE_INTEGER_INPUT_CASES`，所以打开任何一个
指令文件都能看到它跑的**全部**输入。
`overflow(kind, downward=...)` 决定溢出用例的**操作数对**和 `dest` 取哪一端，两者不能互相
推出（`mmulsub` 用乘法配方却落在 floor），所以都由指令声明。128 位场景把标量形式收窄成
`small_values` 一条，那是场景规则不是指令事实，落在 `integer_cases()` 里。
整数场景也没有"恒开"这种特例：清单就是它构造时拿到的参数。`templates` 是必填声明
（`Instruction.__init_subclass__` 在类定义时就要求它非空），忘了给整数条目则由配对测试和
`input_case_names`（找不到整数模板就报错）兜住。`python3 -m mmul_gen --list` 打印的
`input_cases` 是同一份事实的另一种问法：`Instruction.input_case_names` 去问它构造出的模板
（`Template.input_cases`），所以清单只写在 `templates` 里，指令类上没有第二份声明可以漂移。

## `evaluate` 的契约

- 返回**精确结果**，允许超出元素宽度。按宽度重新编码（`convert_result`）是
  `integer_expected` 的职责，所以每一条声明都不必自己取模，也不会漏掉溢出回绕。
- 参数 `elements` 把**形态**翻译成**角色**：
  - `lhs` / `rhs` / `dest`：架构值，已按元素宽度读回；
  - `lhs_raw` / `rhs_raw`：同样的比特按无符号读（位运算指令用的就是它）；
  - `mask`：元素宽度的全 1，也就是比较指令要产出的"真"。
- 标量形式（`.x`）的 `lhs` 就是那个标量，三元 M 形式的 `dest` 与 `lhs` 是同一个方块。
  因此同一个算式在 `madd.ew` 和 `madd.ew.x` 里写法完全相同，差异只由 `form` 承担。
- 每个整数 elementwise 指令**必须**声明它，并且**必须把它交给两条整数模板**：模板构造时就把它
  存下来，`integer_expected` 调的是模板手里这一份。所以漏传是类定义时就报 `TypeError`（少一个位置
  参数），传错一个别的函数则由
  `test_elementwise_declared_evaluation.py::test_every_instruction_hands_its_formula_to_both_integer_templates`
  逐条指令核对"两条模板持有的就是类里声明的那个函数"。类名、值、顺序的其他检查放在
  `test_elementwise_declarations.py` 与 `test_elementwise_template_table_parity.py`，而不是藏在
  `__init_subclass__` 钩子里：从指令文件看得见，而且一次报出所有违规者。这里不留默认实现——
  一个"没写公式却通过测试"的指令是不可接受的。
- 浮点标称走同一条路：类里声明 `def evaluate_float(self, dtype_name, element_bits) -> int`，把它交给
  `ElementwiseFloatNominal`。体通常是一行查表（`FLOAT_OPERATION_VALUES[dtype_name]["add"]`，比较类
  返回 `(1 << element_bits) - 1` 或 0），所以 **`evaluate` 不必是算出来的**；漏传同样在类定义时报
  `TypeError`，传错由
  `test_elementwise_declared_evaluation.py::test_every_instruction_hands_its_float_formula_to_its_nominal_template`
  逐条核对"标称场景持有的就是类里那个函数"。
- `evaluate_float` 只覆盖标称那一格（一个 dtype 一个答案）。特殊值与舍入两格没有"一个答案"，返回的
  是用例向量，指令在那里声明 role——见上一节的表。
- 声明与共享 oracle `numeric_reference` 的一致性由
  `mmul_gen/tests/test_elementwise_declared_evaluation.py` 逐点穷举守着（4 位全立方 +
  8 位全对，两种符号），不一致就是测试失败；`numeric_reference` 是期望值计算与
  逐字节对拍共用的参照实现。

## 家族约定

- `instructions/<family>/base.py` 放家族基类与枚举；`<family>/__init__.py` 只有文档字符串；
  具体指令各占一个文件。
- 指令文件从 `<family>.base` 导入声明词汇（`ElementwiseForm`、`IntegerElements`、
  `FLOAT_OPERATION_VALUES`、`FloatSpecialRole` 等），不再从别处取。
- 新增一条指令 = 加一个文件 + 在 `instructions/__init__.py` 登记类 + 在 `mmul_gen/catalog.py`
  的家族清单里挂上实例；不需要改任何已有指令文件，也不需要动场景表——除非它带来一种
  **新的行为**，那时才在表里加一行。
- 共享模块可以提供机制，但**不得按指令名字分支**：这条由
  `mmul_gen/tests/test_complexity_budget.py` 的不变量守着。
