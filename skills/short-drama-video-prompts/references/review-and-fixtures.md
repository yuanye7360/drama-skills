# 视频提示词审查量表与合成案例

## 目录

1. 审查顺序
2. 证据量表
3. 诊断目录
4. 合成正例
5. 合成反例
6. 常见表演症状与修法
7. 演技自评量表（0–5）

## 1. 审查顺序

先验证 refs、显式时长、camera interval、音频否定与 end equality，再由独立 reviewer 看 performability、action feasibility、camera motivation 和 semantic invention。Reviewer 写 finding，不改 motion、shot 或 screenplay。

Finding 必须含 artifact/hash、引用片段、影响、required fix、owner、severity、status。禁止用 prompt 长度、动词数量、固定动作/秒或“AI 味”替代证据。

## 2. 证据量表

| 维度 | 核心问题 | 必须引用 |
|---|---|---|
| Start fidelity | 第一动作是否从 keyframe/shot start 真正可接上？ | start 字段与 prompt 起始句 |
| Ordered action | actor、方向、接触、先后和结果是否清楚？ | action stages |
| Performance | 触发、处理、选择、landing 是否可见且符合 agenda？ | source beat/shot purpose + motion |
| Action budget | duration 内能否保留故事动作、对白与 reaction？ | duration、距离、台词、动作、camera |
| Camera | lock/move 是否一致，且因注意/压力/揭示而发生？ | camera interval + shot purpose |
| Environment | 是否只动了有依据的环境，未发明天气/事件？ | accepted continuity + environment |
| Dialogue/audio | exact refs、`speaker_ref`、可选 `voice_direction_ref`、VO/OS/SFX 与本场 delivery 是否分别保持？ | source audio fields + character voice direction + prompt |
| End fidelity | reported end 是否逐项等于 continuity out？ | end report + source end |
| Economy | frame 已承载外观是否被无谓倾倒？ | reference contents + copy block |
| Shot boundary | 是否偷改 duration/end/next shot，或在单个镜头内部藏未声明的 cut？ | source shot + motion |
| Segment integrity | 每个计时段是否只有一个连续视角？各段相加是否正好等于**所属镜头**的已接受时长？ | segment 列表 + accepted shot duration |
| Container arithmetic | 容器承载了哪些已接受镜头？容器时长是否等于成员时长之和？成员是否顺序连续、同一绑定链、不跨场次、各自可单独审查？ | container 成员列表 + 各镜 accepted duration |
| Deliverable text | 交付文本里是否只剩要拍的画面内容，没有文件名、版本号、锁定标记、草图指代或任务备注？ | prompt 正文 |

语义 finding 的修复应指出删/改哪一段 motion，或该向哪个 owner 发 revision request，而不是笼统说“动作自然一点”。

## 3. 诊断目录

| code | classification | enforcer | 默认 severity | owner | 含义 |
|---|---|---|---|---|---|
| VID_SOURCE_REF_UNRESOLVED | structural_invariant | validator | error | video-prompts | shot/keyframe/dialogue/audio ref 未解析 |
| VID_EXPLICIT_TIMING_OVERFLOW | structural_invariant | validator | error | video-prompts | 显式时间终点/非重叠总量超 duration |
| VID_EXPLICIT_TIMING_SHORTFALL | structural_invariant | validator | error | video-prompts | 裁剪到镜头长度内的分段并集短于 duration；开头留空、中间留空与结尾留空都算，余量会被无来源动作填满 |
| VID_TIMING_MODE_INCONSISTENT | structural_invariant | validator | error | video-prompts | `timing_plan.mode` 写 `relative` 却有分段标 `explicit`，两种计时同时声明 |
| VID_EXPLICIT_TIMING_UNDECLARED_OVERLAP | structural_invariant | validator | error | video-prompts | 分段区间重叠但未声明重叠关系，合计无法判定 |
| VID_EXPLICIT_TIMING_UNPARSEABLE | structural_invariant | validator | error | video-prompts | 声明 explicit 却没有可读秒区间，无法做 VID-04 算术 |
| VID_DECLARED_TOTAL_MISMATCH | structural_invariant | validator | error | video-prompts | `declared_total_or_endpoint_seconds` 与分段实际覆盖不一致 |
| VID_DURATION_PROJECTION_STALE | structural_invariant | validator | error | video-prompts | `boundary_refs.duration.value_seconds` 与镜头已接受时长不一致 |
| VID_CAMERA_INTERVAL_CONFLICT | structural_invariant | validator | error | video-prompts | 同一区间 lock 与 move 等显式冲突 |
| VID_END_REPORT_MISMATCH | structural_invariant | validator | error | video-prompts | reported end 不等于 storyboard continuity out |
| VID_BOUNDARY_OVERRIDE | structural_invariant | validator | error | video-prompts | motion 写入 duration/end/next-shot override |
| VID_ACTION_INFEASIBLE | reviewed_invariant | reviewer | error | video-prompts/storyboard | 一般动作负载不可行或掩盖故事变化 |
| VID_SEMANTIC_INVENTION | reviewed_invariant | reviewer | error | video-prompts | 新造故事、关系、知识、状态或音频事实 |
| VID_CAMERA_UNMOTIVATED | craft_default | reviewer | warning | video-prompts | movement 无助于目的/注意变化 |
| VID_REFERENCE_DUMP | craft_default | reviewer | warning | video-prompts | bound frame 已带外观却重复整本 设定集 |
| VID_HIDDEN_CUT_IN_SEGMENT | reviewed_invariant | reviewer | error | video-prompts | 单个计时段内藏入视角或空间跳变，等于一次未申报的剪辑 |
| VID15_SHOT_PACKED_TWICE | structural_invariant | validator | error | video-prompts | 同一镜头被两个容器认领，全集时长凭空多一段 |
| VID15_MEMBER_IS_NOT_AN_EPISODE_SHOT | structural_invariant | validator | error | video-prompts | 容器成员不属于本集镜头集合 |
| VID15_MEMBER_SHOT_HAS_NO_DURATION | structural_invariant | validator | error | video-prompts | 被装箱的镜头没有数值时长，容器时长无从成立 |
| VID15_CONTAINER_DURATION_IS_NOT_THE_SUM | structural_invariant | validator | error | video-prompts | 容器时长不等于成员已接受时长之和 |
| VID15_EPISODE_TOTAL_DOES_NOT_RECONCILE | structural_invariant | validator | error | video-prompts | 容器加散镜不等于全集镜头时长总和 |

`VID15_*` 由 [container_check.py](../scripts/container_check.py) 执行。未装容器的散镜与
时长尚未确定的镜头**只报告不判错**：前者是合法的打包选择，后者是上游还没做完，把它们
写成缺陷会让"进行中"和"做错了"无法区分。
| VID_UNEXECUTABLE_MICRO_METRIC | craft_default | reviewer | warning | video-prompts | 亚秒偏移、厘米位移、角度数等读起来精确却无法执行也无法验证的计量 |
| VID_INNER_MONOLOGUE_ONLY | craft_default | reviewer | warning | video-prompts | 绝大多数段落只有内心活动，没有可拍的可见事件或有来源的声音 |
| VID_STYLE_ALTERNATIVE | taste_option | reviewer | note | video-prompts | 表演/摄影/声音风格的非阻断选择 |

语义问题只能由 reviewer 证据化判断；不要写正则把“缓慢”“同时”或动词数量变成错误。

## 4. 合成正例

以下人物、场景、对白均为虚构合成材料。

### Accepted boundary 摘要

- `SHOT-EP001-014`，duration `5.0s`，purpose：罗静听见门外有人试锁后，选择隐藏登记簿而非立刻逃跑；
- start：她坐在检修台边，左手翻开的登记簿，右手握笔，目光在页上；后方安全门位于她右后侧；
- dialogue：画外男声 `[OS] “里面有人吗？”`；
- end：她仍坐着，左手把登记簿压在工具盒下，右手握笔停在桌沿，目光锁向右后侧安全门；
- camera：接受的单镜头、固定轴线，可在触发后轻微推进。

### 合格 generic prompt

> 从参考帧的坐姿开始：她的左手仍按在翻开的登记簿上，右手握笔，目光落在页上，右后方是安全门。门外先传来一次短促的试锁声；她的笔尖立刻停住，目光先移向安全门，但身体没有起身。画外男声问“里面有人吗？”，她屏住一拍，没有回答，左手才把登记簿平稳滑入旁边工具盒下方，动作克制，避免纸页发声；右手始终握笔，最后停在桌沿。表演由专注工作转为警觉，再落到压住恐惧后的主动隐瞒。摄影机开头保持固定，在她决定藏起登记簿时做一次很短、很慢的推进，终点仍保持既定轴线，将她的左手、工具盒和望向安全门的视线纳入同一画面。维修间底噪持续，试锁声和画外问话清楚置于门的方向，无音乐突入。5 秒内完成，结尾保持她仍坐着、左手把登记簿压在工具盒下、右手握笔停在桌沿、目光锁向右后侧安全门。

为何有效：开端只重复运动关键事实；动作按声音→接收→决定→隐藏排列；OS 不要求口型；camera 在选择时启动；结尾逐字段落到 accepted boundary，没有写下一镜。

## 5. 合成反例

### 反例 A：外观倾倒与边界改写

> 她有窄长脸、断眉、短卷发，穿墨绿工装、米白 T 恤、深色长裤和短靴，维修间墙壁每一处材料都清晰。她站起来跑到门外，把笔交给陌生人，然后下一镜已经来到街上。

Finding：reference 已携带外观而 motion 没写关键表演；更严重的是 start 从坐姿跳到站立、end 新增跑出/道具转手，并代写下一镜。修复需回到 accepted 坐姿 end；若逃跑是创作意图，向 storyboard 请求新 boundary/shot。

### 反例 B：动作超载但不能靠计数器判

> 5 秒内，她听完整句问话，翻完三页，把册子锁入抽屉，走过房间关闭两扇窗，拆下墙上话筒，打电话说两句，再回到原座位保持完全静止。

Reviewer 应引用房间距离、物件操作、对白和 landing 说明不可行；不能只说“有七个动词”。优先保留与隐藏决定有关的动作，其余删减或请求 split/extend。

### 反例 C：camera 显式矛盾

```text
0–5s：摄影机绝对锁定、没有任何移动。
1–4s：摄影机持续向前 dolly 并手持环绕角色一周。
```

同一区间的 lock/move 可结构阻断。创作者可选择 lock 或 move；若需先锁后推，写不重叠 transition。

### 反例 D：音频语义发明

> 画外问话后，突然响起爆炸，所有灯熄灭，她大喊“我承认了”。

若 source 没有爆炸、停电和这句对白，这会改变故事与 continuity。由 reviewer 引用 source 缺失与 prompt 新句给 `VID_SEMANTIC_INVENTION`，不是因关键词“爆炸”本身被正则禁止。

### 反例 E：段内藏切

```text
段 2（1.6–3.4s）：她把登记簿推入工具盒下方；随即是走廊外一只手停在门把上的近景；
再回到她的侧脸，眉心收紧。
```

技能正文已经规定单个镜头内部只保持一个剪辑边界，但违规通常不出现在 `camera` 字段冲突里，
它藏在**一个计时段内部**的连续叙述中，读起来只是“镜头很有节奏”。量表要能抓到它，
而不只是禁止它：逐段列出空间锚点、被摄主体和机位关系，段内出现没有过渡的空间或主体
跳变，就是一次未申报的剪辑。修复是向 storyboard 请求拆成两个 authored shots，或删掉插入的
外景段落；不能靠补一个转场词把它说圆。

注意与多镜容器区分：容器内**成员镜头之间**的空间与主体跳变是已申报的剪辑，不是缺陷。
判据是跳变落在哪里——落在成员镜头边界上，且该边界能追溯到一个已接受镜头，就成立；落在
某个成员镜头的计时段内部，就是段内藏切。容器时长与成员时长之和不符时另记一条容器算术
缺陷，不要把两者混成同一条 finding。

### 反例 F：不可执行的微计量

```text
0.00–0.37s：眉心下压 0.4 厘米；0.37–0.92s：右手向左平移 3 厘米，头部旋转 7 度；
0.92–1.41s：瞳孔收缩，肩线下沉 1.2 厘米。
```

这类写法读起来像精度，实际没有指定任何可执行的东西：执行端无法把厘米和度数对到画面
尺度，审查者也无法验证是否照做；同时它挤掉了真正需要写清的触发、接触与结果。修复是
换成可比较的相对量与接触事实——“手指移到杯沿并停住”“视线从对方脸上落到桌面签名处”。
只有上游提供、且确实能消除歧义时才写具体秒段（见 `motion-recipe.md` 3.6）。

### 反例 G：整段独白

```text
段 1：她想起母亲临走前那句话。段 2：她意识到自己再也回不去了。段 3：她下定决心。
```

三段都只有内心活动，没有一件可拍的事。没有可执行内容时，执行端会自行发明动作与表情
去填满时间，结果与剧本无关。修复是让每段至少落到一个可见事件（目光、接触、位移、决断
动作）或一段有来源的声音；确实需要内心过程时，用已接受的画外音承载，并写清它与画面
事件的相对时机。内心独白本身不是缺陷，把它当作整条提示词的唯一内容才是。

## 6. 常见表演症状与修法

以下是从合成反例里抽出来的、反复出现的表演级症状。诊断目录（第 3 节）管的是结构和语义
违规，这里管的是「结构上没问题，但演起来假」的症状——审查者和撰写者都可以拿它当症状对照表，
先认出症状，再回到对应字段修。

| 症状 | 表现 | 修法（对应本套件字段） |
|---|---|---|
| 面部指示情绪 | 脸在「演」情绪本身——堆砌表情词，而不是让情绪从处理中长出来 | 从 `performance_arcs` 里删掉面部情绪标签，改写成 `visible_leak` 里具体的、当前景别读得到的身体信号，或交给一件手边动作的中断（见 `performance-action-timing.md`「给角色一件手上的事」） |
| 提前演结果 | `receive` 之前，角色已经表现出这场戏最终的情绪状态 | 检查 `ordered_subject_motion` 的先后顺序：反应必须晚于触发来源，不能在触发发生前就已经「演完」 |
| 等对方说完才反应 | 对方台词/动作进行中，角色一直是空白状态，说完才「切换」 | 让 `receive` 在对方台词或动作尚未结束时就开始，呼应 3.3 节「表演过程」里触发—接收的顺序要求 |
| 一个调子演到底 | 整条 `performance_arcs` 只有一种强度或一种手段，没有随受阻变化 | 用 `performance-action-timing.md`「Meisner 五要素」里手段（Tactics）一节逐项检查 `choice` 是否真的换了手段；若确实只需要一次不变的坚持，说清原因而非漏想 |
| 动作逐字翻译台词 | 手势逐字图解台词内容（说「很大」就摊开双手） | 让 `visible_leak` 或 `ordered_subject_motion` 的动作独立于台词字面内容，从角色当下的处理而不是台词词汇生成 |
| 无来由的情绪爆发 | 强烈情绪（哭、吼）突然出现，`mask` 没有先压住什么就直接给结果 | 先写清 `mask` 在压什么、被哪个 `receive` 击穿，再落到 `visible_leak`；不能跳过压制阶段直接给爆发结果 |
| 体态与身份不符 | 一个体力劳动者却有舞者般的轻盈站姿；一个瘾君子的身体毫无使用痕迹 | 按 `performance-action-timing.md`「身体的物理生活：四个参数」设定重心、节奏、开放度，让 `start_anchor`/`ordered_subject_motion` 里的体态符合角色背景 |
| 台词比阶层干净 | 底层/街头角色说着修饰完整、文学化的长句 | 在 delivery 里加入停顿、吞字、说一半改口（见 `camera-audio-continuity.md`「声音表演的完整规则」），呼应 `production-prompt-grammar.md` 的语言经济性；完整对白文本不能改，只调整表演方式 |
| 暴力前的预告 | 「不祥」的停顿、眯眼、缓慢转身，在动作发生前反复铺垫威胁 | 危险感来自周围人的紧张（见 `performance-action-timing.md`「Ensemble 与空间中的动机」），不来自威胁本身的预告；真实暴力通常没有前戏，`ordered_subject_motion` 不必加一段蓄力动作 |
| 群体反应齐步走 | 多人同时、同样地对同一事件反应 | 按「Ensemble 与空间中的动机」把 `attention_handoffs[]` 写出先后差；对应 `VID-16` 禁止全员复制同一 `landing` |
| 死寂的停顿 | 停顿里什么都没发生，只是留白 | 停顿要装着消化、决定或拒绝回答中的一种，写进 `visible_leak` 或 delivery 的停顿说明；确实没有内容时不如删掉停顿 |
| 演给观众看 | 表演对着镜头「眨眼」，暗示「我们都知道这很好笑/很惨」 | `choice` 要基于角色对场内事实的真实信念，不能让角色意识到自己在被观看；喜剧同样要按角色的严肃程度演，不加一层观众视角的调侃 |
| 近景过度表演 | 近景里做大幅面部/肢体动作 | 景别越紧，动作幅度要越小；近景优先只留眼神与念头的变化，把肢体动作留给中/远景（呼应「目光与眨眼」） |
| 目光冻结 / 死眼 | 长时间锁定不动，没有扫视和眨眼变化，近景尤其明显 | 按 `performance-action-timing.md`「目光与眨眼」补眼神先于头转、扫视、眨眼节奏与状态对应、眼睛反光四条 |
| 情绪瞬间归零 | 强烈事件后下一镜（或下一段）角色状态直接回到中性，呼吸/手部毫无余势 | 按 `motion-recipe.md` 3.7 节的余势要求，把呼吸、手部稳定度等状态承接进 `end_report`，除非分镜的 `end_boundary` 明确要求已经平复 |

`craft_default`：这张表帮助定位症状对应哪个字段，不是新增的校验规则；具体这一镜是否构成缺陷，仍按诊断目录（第 3 节）和证据量表（第 2 节）的既有分级判断。

## 7. 演技自评量表（0–5）

写完一条 `performance_arcs[]`，可以用这个量表快速判断它大概落在哪一级；2 分以下建议直接重写，不必等审查者指出。量表描述的是「这段文字读出来像不像一次真实的行为」，不是打分本身要写进产物。

- **0 分·人偶**：台词照发，行为缺失。`performance_arcs[]` 是空的，或者只写了台词内容本身。
- **1 分·朗读者**：有「表现力」的台词、被指示出来的情绪、图解式的肢体动作。典型症状是本节症状表里的「面部指示情绪」和「动作逐字翻译台词」同时出现。
- **2 分·尽职**：能猜到目标，但只有一种手段、反应总是慢半拍、`visible_leak`/停顿里没有内容。对应症状表的「等对方说完才反应」和「一个调子演到底」。
- **3 分·合格**：目标和节拍都在，能听懂对方并反应，身体动作说得通。缺的是潜台词、出人意料但依然可信的手段变化，以及状态的余势（上一镜的情绪没有延续到这一镜）。
- **4 分·有生命力**：行为连续不中断，手段有对比，`mask`/`visible_leak` 里的潜台词和台词字面不一致，地位能从身体读出来，反应常常先于台词落地，至少有一次意料之外但符合角色逻辑的 `choice`。
- **5 分·磁石**：在 4 分的基础上，角色同时演着两个互相矛盾的真相——帮忙的同时厌恶这么做，道歉的同时在辩解，深爱着对方却已经在心里离开。**两个真相同时存在**是这一级的判据：近景里只有一种、干净不矛盾的情绪，读起来是合成的。

给近景/关键情绪镜头的目标是 4 分以上；一段自评落在 2 分或以下的 `performance_arcs`，在提交审查前应该先按本节和「Meisner 五要素」重写，而不是留给审查者去挑。

**`craft_default`**：这是撰写阶段的自检工具，不是新增的校验字段或必填分数；量表本身不出现在交付文本或规格字段里。

`craft_default`：这张表帮助定位症状对应哪个字段，不是新增的校验规则；具体这一镜是否构成缺陷，仍按诊断目录（第 3 节）和证据量表（第 2 节）的既有分级判断。
