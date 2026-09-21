# 生成器测试

本目录是生成器共享参考模块的 Python 单元测试。规范的套件入口是：

```sh
cd sail-ame/test/ztt/gen
python3 -m tests
```

运行器会发现本目录下每个 `test_*.py` 模块。审阅改动时可以只跑一个聚焦模块：

```sh
python3 -m unittest tests.test_numeric_reference
python3 -m unittest tests.test_manual_sync
python3 -m unittest tests.test_matrix_geometry
```

父目录 `gen/` 下的 Python 文件是生成器实现或校验工具：`mmul_gen/` 是汇编生成器，
`check_manual_sync.py` 把本地输入与机器可读手册对照。运行时 JSON 配置由 Sail 校验，不由测试
生成器校验。这些文件不是测试套件，从生成器根目录可以直接导入。

`tests/test_mmul_gen.py` 转调 `gen/mmul_gen/tests/` 里的生成器套件，所以上面的命令也覆盖它。
专门改生成器时直接运行该套件：

```sh
cd sail-ame/test/ztt/gen
python3 -m mmul_gen.tests
```
