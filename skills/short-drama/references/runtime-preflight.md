# 运行时预检与发布纪律

无论从主技能还是子技能进入，都先完成同一套轻量预检。它只检查安装完整性、项目事务状态和已记录的精确引用，不评价创作内容。

## 1. 一条命令完成安装验证、恢复与状态

从 `suite-ref.json` 解析到逻辑安装路径中的 core 后，用当前可用的 Python 3 解释器运行：

```bash
python3 <core>/scripts/project_tool.py preflight <project>
```

若环境的 Python 3 命令名不同，使用该环境已经提供的等价解释器。它依次做三件事，语义与拆成三条命令时完全相同：

1. 运行同一个 `suite_verify`，沿逻辑安装路径逐一检查清单中的八个技能；混装、缺件、额外可执行文件或 hash 不一致时非零退出，停止写入。不要退回源码检出目录“借用”通过验证的兄弟技能。
2. 先恢复未完成事务（等价于 `recover`，可重复执行），再读状态。`next_action` 为 `resolve_blocked_transactions` 时同样非零退出：保持创作者文件原样并先处理冲突，不要绕过 WAL、手改状态文件或假定上次写入成功。
3. 返回 `project` 状态摘要，其中的 accepted/candidate 指针和阻断项是后续工作的当前事实。还没有项目时返回 `project: null` 与 `next_action: initialize`，这是正常入口状态，不是错误。

`suite_verify`、`recover`、`status` 仍可单独运行来诊断某一环，但常规入口只用这一条：三次往返变一次，检查一项不少。

**不要把 `suite-manifest.json` 读进上下文**。它是一份纯 hash 清单，唯一用途是被验证器逐条比对；读进来既不能替代校验，又会挤占本可留给创作内容的篇幅。同理不要直读 `.short-drama/state.json`——它随产物数量线性增长，而状态摘要不会。

同时读取 `status.layout`。`mode=canonical` 使用返回的中文 `roots`，`mode=legacy`
使用返回的旧版英文 `roots`；`mode=mixed` 时停止发布，先合并平行目录。所有负责技能都沿用
同一份 `roots`，不得根据自身模板另建另一种语言的阶段目录。`pinned=false` 的空项目使用
返回的中文根，第一次阶段发布会把布局固定进项目状态。

## 3. 只通过公开生命周期写入

- 负责人用 `publish` 原子发布候选，并给每个外部结构化引用提供精确 input hash。
- `publish` 要求来源与目标不同，候选内容要先落到临时来源再发布。临时来源统一放
  `.short-drama/tmp/<阶段>/`，`publish` 会在提交后自动清理；不要在项目根建
  `_publish_tmp*` 目录，那会堆积成不会被清理的垃圾。
- 上游接受引用不继承候选状态；`authority:candidate` 只用于同次发布的目标或明确的
  候选预览链，后者在接受前必须已由同 hash 的上游接受快照闭合。
- 创作者接受、独立审查和内容修订是不同动作；审查者发布 finding/verdict，不改负责人的来源。
- 每次修订后重新运行适用的结构校验，并让下游刷新旧 hash。
- `package` 是最终文本/JSON 交付闸门，不是接受或审查命令；任何阻断项仍在时不打包。

完整命令参数见 [lifecycle-commands.md](lifecycle-commands.md)，权威边界见 [contract-and-ownership.md](contract-and-ownership.md)。
