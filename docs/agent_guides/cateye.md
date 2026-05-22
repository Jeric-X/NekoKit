# CatEye 图片识别工具 -- 智能体使用指南

---

## 一、工作原则

1. **预设优先**：收到图片相关请求时，优先匹配场景预设并按工具链执行，避免自行编排
2. **context 驱动**：同一张图片的历史分析会自动积累为 context，后续调用 vision 时自动注入。主动利用 context 可提升多轮对话的分析质量
3. **最小调用**：核心工具内部自动完成预处理和缓存查写，无需额外调用辅助工具。大多数场景 1-2 次调用即可完成

---

## 二、场景预设

收到图片请求时，先匹配下表中的触发关键词，再按对应工具链执行。

### 内置预设

| 编码 | 名称 | 工具链 | 触发关键词 |
|------|------|--------|-----------|
| `extract_text` | 文字提取 | `ocr` | 提取文字、OCR、识别文字、台词、字幕、公告、文案、这写的什么 |
| `identify_character` | 角色识别 | `search` → `vision` | 这是谁、角色识别、认人、动漫角色、游戏角色、虚拟主播 |
| `find_anime_source` | 番剧溯源 | `search` | 这是什么番、番名、动漫名称、哪一集、找番、认番 |
| `understand_meme` | 表情包解读 | `vision` | 梗图、表情包、什么意思、笑点、玩梗、斗图 |
| `analyze_chart` | 图片分析 | `vision` | 分析一下、游戏截图、攻略、面板、配装、抽卡、数据图 |

`analyze_chart` 的模式选择：日常内容（游戏截图、活动图、地图等）用 `daily`；涉及数据、图表、复杂逻辑时用 `professional`。

### 获取与自定义

- `nkit_ce_scene(action="list")`：列出所有预设（含自定义）
- `nkit_ce_scene(action="get", scene_code="...")`：获取预设详情
- `nkit_ce_scene(action="update", scene_code="...", preset_json="...")`：创建或更新自定义预设。内置预设不可覆盖，使用新编码即可

自定义预设格式：

```json
{
  "name": "场景名",
  "description": "描述",
  "tool_chain": ["nkit_ce_search", "nkit_ce_vision"],
  "model_preference": "daily",
  "trigger_keywords": ["关键词1", "关键词2"],
  "is_preset": false
}
```

---

## 三、工具速查

| 工具 | 用途 | 关键参数 |
|------|------|---------|
| `nkit_ce_ocr` | 文字识别 | `image_url` |
| `nkit_ce_search` | 以图搜图 | `image_url`, `scene`(auto/anime/moe/illustration/general), `provider`(可选，强制指定供应商) |
| `nkit_ce_vision` | 视觉理解 | `image_url`, `prompt`, `mode`(daily/professional) |
| `nkit_ce_cache` | 缓存管理 | `image_url`, `action`(check/store/update), `task_type`(ocr/search/vision), `result`(JSON), `evaluation`(-2~2) |
| `nkit_ce_scene` | 场景预设 | `action`(list/get/update), `scene_code`, `preset_json` |

搜图供应商由管理员配置，可能包含自定义供应商。`scene` 参数会自动映射到对应供应商，不确定时使用 `auto`。

---

## 四、Context 机制

### 自动行为

核心工具每次执行后，分析结果会自动存入 context。同一张图片再次调用 `nkit_ce_vision` 时，历史分析记录会自动注入到系统 prompt 中，无需 agent 手动传递。

### 主动利用

1. **多轮深化**：用户对同一张图追问时，直接调用 vision 即可——历史 context 自动注入，无需重复描述前序分析
2. **跨工具协作**：先 search 再 vision 时，search 结果已自动存入 context，vision 调用时会感知到搜图结果
3. **场景操控**：通过 `nkit_ce_scene` 更新预设的 `description` 和 `model_preference`，影响后续同场景调用的 context 注入内容
4. **缓存主动查询**：通过 `nkit_ce_cache(action="check")` 查看已有缓存，避免重复分析；通过 `evaluation` 参数对分析质量打分，低分结果在 context 中权重降低

### Context 生命周期

- 存储键：`cat_eye:ctx:{image_hash}`
- 有效期：7 天，每次更新自动续期
- 缓存键：`cat_eye:cache:{image_hash}_{task_type}`，有效期 48 小时

---

## 五、异常处理

- 核心工具失败时，尝试替代工具（如 OCR 失败 → vision）
- 特定搜图供应商失败时，使用 `scene="auto"` 或切换 `provider`
- 所有工具失败时，告知用户限制并说明可能原因
