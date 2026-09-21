# Ztt 测试生成

本目录从手册指令快照与代码内定义的测试输入，生成裸机、自检的 Ztt 汇编测试。目标是让指令
清单与手册保持同步，并为已实现模型提供可重复的编码与执行冒烟测试。测试输入由代码定义，
可以直接从指令定义与生成的汇编中读取。

## 运行矩阵

`run_ztt_tests.py` 负责完整 N/UDS/M/ACC 配置矩阵（120 种组合）的生成、编译与执行；CMake
只从手册快照重新生成 Sail 模型与 GAS 宏，并校验两者同步。脚本可续跑：已生成的源文件、
已编译的 ELF 与已记录的结果会被复用，因此中断的运行会从断点继续。

```sh
# 针对已构建的模拟器跑完整矩阵
python3 test/ztt/run_ztt_tests.py \
    --sim build/c_emulator/sail_riscv_sim \
    --work-dir build/ztt-matrix

# 单个组合，只重新生成并运行它
python3 test/ztt/run_ztt_tests.py --combo n8_u8_m32_a4 \
    --sim build/c_emulator/sail_riscv_sim

# 用逗号分隔的列表在任一轴上收窄扫描范围。合法取值遵循手册：N 是 2 的幂
# （AME_NELEM 是 4 的幂，手册未设上界——N = 128 即 rv64-ztt-16k-8 配置），
# UDS 是 2 的幂，M 为 16 或 32，ACC 为 1/2/4/8/16。
python3 test/ztt/run_ztt_tests.py --n 8,32 --uds 16 --acc 4

# 只生成 + 编译（不需要模拟器）
python3 test/ztt/run_ztt_tests.py

# 列出 120 种组合
python3 test/ztt/run_ztt_tests.py --list
```

每个组合的运行时配置由 `cfg/rv64d_v256_e64_ztt.json.in` 重写 Ztt 参数后渲染，因此矩阵不
依赖 CMake 生成的 JSON 文件。`--jobs` 控制并行度，`--timeout` 控制单个测试的模拟器超时。
`--sim` 指向 spike 时复用同一条流水线。

组合名形如 `n<N>_u<UDS>_m<M>_a<ACC>`（例如 `n8_u8_m32_a4`），每个组合生成一个目录；
运行结果追加记录在 `<work-dir>/results.tsv`，因此中断的运行可以续跑。

## 生成器架构

生成器只有一条单向数据流：

1. `gen/mmul_gen/instructions/` 每条指令一个模块。每个模块声明一个类，其属性是指令的名字、
   摘要、操作数、检查方式，以及一个有序的 `templates` 元组，列出它运行的场景。
2. `gen/mmul_gen/templates/` 每个模板一个模块，每个都是一个有文档的 `Template` 子类，渲染
   一个场景并计算它内嵌的期望值。`gen/mmul_gen/reference.py` 与指令无关的模块
   （`numeric_reference`、`fp_semantics`、`float_formats`、`generator_types`）是唯一的共享
   数值代码。
3. `gen/mmul_gen/catalog.py` 是整个清单——一个显式、有序的 `INSTRUCTION_FAMILIES` 元组——
   加上生成循环。没有函数值注册表、装饰器、导入副作用或隐式注册步骤。
4. `gen/mmul_gen/__main__.py` 解析几何参数、渲染并写出源文件，并可打印清单（`--list`）或
   单个家族（`--family`）。

这种分离是刻意的：读一条新指令时，先看它的指令类与 `templates` 元组，再逐个检查模板的渲染
与期望值计算。改动共享辅助函数应视为跨家族改动，并附上针对性的单元测试。

`gen/mmul_gen/README.md` 记录架构，`gen/mmul_gen/instructions/README.md` 记录指令如何声明
自己，`gen/mmul_gen/templates/README.md` 记录模板。

### 测试

`python3 -m mmul_gen.tests` 运行生成器测试套件。`python3 -m tests`（在 `gen/` 下）是总入口：
它运行共享参考模块测试（`numeric_reference`、`check_manual_sync`、`matrix_geometry`），并
转调生成器套件。

`gen/mmul_gen/tests/golden_sources.json` 以 SHA-256 冻结五种配置的发射汇编，因此模板改动
一旦影响发射结果就会在这里失败。

## 范围与限制

生成器把期望值嵌入每个自检汇编测试。整数二维矩阵乘的期望值使用基于 NumPy 的参考计算，中间
量是精确 Python 整数，回写时显式施加 Ztt 回绕或饱和。另有一个普通 Python 循环独立计算同一
精确矩阵结果；一旦 Python/NumPy 不一致，生成在期望值嵌入汇编之前就失败。所有生成的整数二维
矩阵乘变体都用这套交叉校验计算处理转置、累加/相减、回绕与饱和行为。生成的矩阵乘模板还包含
一个显式的有符号/无符号混合打包源用例，带两个不同的逻辑输入方阵；其静态数据布局在生成的
汇编中可见，并与同一精确参考核对。其余整数运算与浮点期望值使用确定性的 Python 辅助函数或
手写值；Ztt FP8/BF16 编码、六种舍入模式、异常标志与 NaN 细节由专门的浮点语义模块
（`fp_semantics`）给出。

逐元素浮点算术场景包含 quiet NaN 传播、signaling NaN 静默并置 `FFLAGS_NV`，以及编码了无穷
与 signaling NaN 的格式上的无效运算对 `0 * Inf` 与 `Inf - Inf`。E4M3 没有无穷与 signaling
NaN 编码，因此不产生这些用例。log/exp/sqrt 类等其他浮点家族保留各自的标称与舍入场景。

生成的数据、期望偏移与寄存器选择对完整配置矩阵参数化：N（`AME_NELEM`）= 4/8/16/32，
UDS=8/16/32，16 或 32 个 M 寄存器，1/2/4/8/16 个累加器。`run_ztt_tests.py` 为每个
N/UDS/M/ACC 组合生成一个目录（120 个套件），并用匹配的运行时 JSON 配置运行每个源文件。
清单有 141 个有序定义项，覆盖 138 条架构指令助记符，通常发射 141 个源文件。多出的三项/文件
是两个打包累加器跨度检查与一个 `mmov.a.m`/`mmov.m.a` 共享异常检查。元素宽度超过一个原始行
（`N * UDS` 位，按手册的行布局）的 debug move 在架构上非法，会被跳过；例如 N=4/UDS=8 时
`mmove64.m.x` 与 `mmove64.x.m` 对被省略，剩 139 个文件。

`gen/mmul_gen/instructions/` 下每条指令一个模块，`gen/mmul_gen/templates/` 下每个模板一个
模块，架构见 `gen/mmul_gen/README.md`。datatype 域与各个输入配方是记录在家族模块里的生成器
选择，直接从生成的汇编读取。带打包、raw transfer、typed broadcast、strided 或 conversion
特定规则的指令，把那些约束保留在对应的家族模板里。

二维浮点乘法变体一次一个乘积地通过目的 dtype 累加，因此其全 1 期望值遵循顺序舍入：直到
`2^(mantissa_bits+1)` 的值是精确的，超过后 RNE tie 会把运行和钉在该上限（E5M2 上限为 8，
E4M3 为 16）。更宽的格式对每个受支持的 N 都保持精确。

打包转换从当前 UDS 推导其存储/计算对：

- UDS=8：4 位存储，8 位计算
- UDS=16：8 位存储，16 位计算
- UDS=32：16 位存储，32 位计算

转换对覆盖有符号与无符号整数 dtype。打包存储能力单独跟踪，因为位保持操作可以使用不是合法
`mconv.ew` 元组的 SAT 或浮点描述符。debug move 也在每个套件中运行，并按当前寄存器宽度计算
其原始 M 寄存器位置回绕。

在 CMake 选定的 Python 环境中安装生成依赖：

```sh
python3 -m pip install -r test/ztt/gen/requirements.txt
```

CMake 在生成测试前检查 NumPy 可导入。生成器套件在 `gen/` 下手动运行。

生成器测试的规范入口：

```sh
cd sail-ame/test/ztt/gen
python3 -m tests
```

各专项测试模块记录在 `gen/tests/README.md`。`gen/` 下的脚本是生成器实现或校验工具，不是
分散的测试入口。

生成的注释标出每个片段的具名输入用例与操作数值；指令定义与生成的汇编本身就是检查对象。

Sail 单元测试另外覆盖规范指令的编码/反汇编往返，不调用 `execute`。它们补充解析器、非法
编码、故障原子性、顺序与独立参考测试。

后端所有权辅助函数是单 hart 的 bring-up 模型，共享后端边界是显式的。操作系统软件负责用
架构指令 `mls.1r`/`mss.1r`、datatype 与状态 CSR、以及 `ame.acquire`/`ame.release` 协议
保存与恢复 AME 状态。多 hart、等待与超时推进、后端 drain、跨 hart 绑定与虚拟化所有权属于
平台后端提供方的职责，由它负责后端清单、context 到后端的绑定、原子 acquire 结果、等待与
超时推进、以及释放时的 drain。`extensions.Ztt.ame_backend="shared"` 在配置期被拒绝；
`"dedicated"` 是这个单 hart 模型支持的模式。

## 配置

Sail 配置层是校验运行时 JSON 文件的权威，包括 Ztt 的 N、UDS、寄存器数与扩展约束。汇编
生成器不重复这些检查：CMake 用 `--n`/`--uds`/`--m`/`--acc` 显式传入预期的 N、UDS、M 与
ACC，而 Sail 在每个测试运行时收到匹配的 JSON。生成的套件覆盖完整
N=4/8/16/32 × UDS=8/16/32 × M=16/32 × ACC=1/2/4/8/16 矩阵（120 种组合）。

运行生成器单元测试：

```sh
cd test/ztt/gen
python3 -m tests
```

## 跨 N/UDS 配置冒烟

`src/config/n_config_smoke.S` 编译一次，然后用由 `config/config.json.in` 生成的聚焦运行时
配置 N=4/16/32 × UDS=8/16/32 运行。它读取 `amenlen` 与 `ameudsz`，然后执行一条整数
`madd.ew`，源为打包 UINT8、源/目的为 UINT16。这让测试能区分依赖 UDS 的 pack 因子与成形的
寄存器跨度（UINT8 为 1、2、4）。成形的 UINT16 源与目的总是占两个物理 M 寄存器；冒烟测试
装载并存储完整跨度并校验其全部字节。它还通过转置的步长内存往返 UINT4，并在全部
`(UDS/4)*N` 个段中检查每个活跃字节，包括 UDS=32 的 pack 因子 8 情形。它与完整的
N/UDS/M/ACC 生成矩阵互补，是单个 ELF 的运行时配置检查。

## 手册同步

手册快照存放在 `manual-main/`。在本目录下，从固定的 prose checkout 刷新它并重新生成派生
产物：

```sh
ruby generators/import_manual_prose.rb
cmake -S ../.. -B ../../build -DCMAKE_BUILD_TYPE=Debug -DENABLE_RISCV_ZTT_TESTS=ON
```

配置会刷新 `model/extensions/Ztt/` 下的 Sail 模型与 `src/ame_macros.inc` 宏包含文件。生成的
汇编测试源仍单独放在 `build/test/ztt/generated/` 下。

测试生成器的宏与 Sail 清单可以对照独立的手册快照检查，因此手册更新后仍能检出不一致：

```sh
python3 test/ztt/gen/check_manual_sync.py \
  --instruction-data /path/to/sail-ame/test/ztt/manual-main/instructions.json \
  --expected-macros /path/to/sail-ame/test/ztt/src/ame_macros.inc
```

`--strict` 在手册指令集、宏或 Sail 清单发生分歧时失败；提供 `--sail-model` 会把生成的 Sail
指令清单也纳入检查。提供 `--expected-macros` 时，检查逐字节比较宏编码，包括同名助记符的
编码变化。

`ZTT_INSTRUCTION_DATA` 与 `ZTT_EXPECTED_MACROS` 可以传给 `build_simulator.sh`，让 CMake 在
配置期执行严格检查。导入的快照包含 138 条指令。

聚焦检查某一类时，例如 datatype 管理：

```sh
python3 test/ztt/gen/check_manual_sync.py \
  --instruction-data /path/to/sail-ame/test/ztt/manual-main/instructions.json \
  --expected-macros /path/to/sail-ame/test/ztt/src/ame_macros.inc \
  --check-instructions agettyp asettyp mgettyp msettyp \
  --strict-selected
```
