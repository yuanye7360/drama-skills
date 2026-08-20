# 运行时预检与发布纪律

无论从主技能还是子技能进入，都先完成同一套轻量预检。它只检查安装完整性、项目事务状态和已记录的精确引用，不评价创作内容。

## 0. 一条命令走完第 1–2 步

```bash
python3 <core>/scripts/project_tool.py enter <project>
```

按固定顺序验证安装、恢复事务、读状态，一次返回 `install` / `recovery` / `status` /
`next_action`。顺序本身就是纪律：状态若在恢复之前读取，描述的可能是一个写到一半的项目。
`next_action` 为 `fix_installation` 时安装不可信，**不会**继续跑会写创作者文件的恢复；
为 `resolve_blocked_transactions` 时先处理冲突，不要因为 `status` 其余部分看起来正常就往下走。

项目路径可用位置参数，也可用 `--project`——与各阶段渲染脚本同一种拼法，两者指向不同项目时
报错而不是静默挑一个。下面第 1–2 步的单独命令保留，用于分步排查。

## 1. 验证当前安装

从 `suite-ref.json` 解析到逻辑安装路径中的 core 后，用当前可用的 Python 3 解释器运行：

```bash
python3 <core>/scripts/suite_verify.py <core>
```

若环境的 Python 3 命令名不同，使用该环境已经提供的等价解释器。验证器必须沿逻辑安装路径逐一检查清单中的八个技能；混装、缺件、额外可执行文件或 hash 不一致时停止写入。不要退回源码检出目录“借用”通过验证的兄弟技能。

## 2. 恢复事务，再读状态

定位项目根目录后，先运行：

```bash
python3 <core>/scripts/project_tool.py recover <project>
python3 <core>/scripts/project_tool.py status <project>
```

`recover` 可重复执行。若它报告 blocked，保持创作者文件原样并先处理冲突；不要绕过 WAL、手改状态文件或假定上次写入成功。`status` 中的 accepted/candidate 指针和阻断项是后续工作的当前事实。

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
