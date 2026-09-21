# 手册 prose 导入

`instructions.json` 是从 Ztt prose 手册提取的结构化接口。它由
`../generators/import_manual_prose.rb` 生成：该脚本默认读取固定的手册 checkout 下的
`src/instructions.adoc`，并解析编码分配表。手册 checkout 在别处时用 `--source` 指定。

当前快照为手册标签 `v0.6`（提交 `8d27acdcee7a189aad4e2907412e0c40a9d4b9e2`），含 138 条
指令。JSON 记录源提交、指令顺序与分类、prose 摘要/操作、WaveDrom 编码，以及推导出的译码器
`mask`/`match`。

手册 checkout 更新后刷新快照：

```bash
ruby ../generators/import_manual_prose.rb
```

prose 快照是当前生成器的唯一输入。
