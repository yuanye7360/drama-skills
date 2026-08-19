# `style-lock.jsonl` 填写模板

风格锁是**每条送给图片/视频生成器的提示词起首那一段画风描述**。规则要求它全项目逐字复用
（见 [common-recipe.md 的风格锁小节](../references/common-recipe.md)），而"逐字"这件事只有在
它有一个位置、而不是每次现编时才成立。所以它是一条记录，不是一段口头约定。

```json
{
  "style_lock_id": "LOCK-<stable-id>",
  "status": "candidate",
  "text": "<画风类别 + 线条/表面处理 + 材质对光的响应 + 负面词；描述性，绝不写工作室/画师/品牌/IP 的名字>",
  "direction_ref": {
    "owner": "creator",
    "artifact": "short-drama.json",
    "hash": "<sha256>",
    "field": "/creator_authority/visual_direction"
  },
  "production_profile_ref": {
    "owner": "creator",
    "artifact": "short-drama.json",
    "hash": "<sha256>",
    "field": "/creator_authority/production_profile"
  },
  "provenance": "creator_project"
}
```

发布为 `项目开发/style-lock.jsonl`，归 `short-drama-image-prompts` 所有——它是已接受视觉方向
与制作形态的**投影**，不是第二个视觉方向权威。视觉方向改了就重投影这条记录，不要在下游
各条提示词里各改各的。

## 哪些正文起首必须带它

| 阶段 | 带风格锁 | 为什么 |
|---|---|---|
| 资产图片提示词（人物/场景/道具/变体） | 是 | 生成的就是最终画风的资产 |
| Look Development 风格帧 | 是 | 它测的就是画风本身 |
| 冻结关键帧 | 是 | 关键帧是正式画面，下游视频从它起生成 |
| 多镜容器视频提示词 | 是 | 整段生成，画风要在起首框定 |
| **场次故事板 previs sheet** | **否** | sheet 是黑白规划稿，和最终画风脱钩；带上风格锁等于让 previs 越权占 keyframe 的活 |

渲染脚本按这张表执行：`render_image_prompts.py`、`render_keyframe_prompts.py` 与
`render_container_prompts.py` 都读这条记录并核对正文起首；`render_sheet_prompts.py` 不读它。

## 为什么不放进 `creator_authority`

风格锁是从已接受的 `visual_direction` / `production_profile` 投影出来的可执行文本，投影这件事
属于本阶段。把它写回创作者权威会造成两个后果：投影与来源互相引用形成哈希环，以及
`visual_direction` 的记录 hash 每次改措辞都变动，让全部已发布的下游规格无谓过期。
