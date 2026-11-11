# 配置与工程参考

## 0. 分发与安装（SkillHub）

本技能**只通过腾讯 SkillHub（skillhub.cn）分发**，不维护自建下载页或其他分发渠道。

### 用户安装

1. WorkBuddy 左侧「专家·技能·连接器」→ 技能页签 → 在 SkillHub / 技能市场搜索 `oral-video-packager`（或「口播视频包装工具」），点击卡片上的添加按钮一键安装。
2. 也可在对话里直接说「帮我找一个能把口播视频包装成带字幕、人物名片和知识动画成片的技能」，WorkBuddy 会自动检索 SkillHub 并给出候选，确认后安装。
3. 在「已安装」出现该技能后，**新开一个对话**才完全生效。临时停用可在技能开关里关闭，不会删除文件。

上架前的内部试用可用「添加技能 → 上传技能」导入本地包，或解压到 `~/.workbuddy/skills/`，但这不是正式分发渠道。

### 发布者上架 SkillHub

前置：完成 SkillHub 实名认证（腾讯云人脸核身，个人号即可发布）。

使用**扁平结构包** `oral-video-packager-skillhub.zip`：ZIP 根目录直接是 `SKILL.md`。带外层目录的 WorkBuddy 包不符合平台「根目录含 SKILL.md」的校验，不要直接提交。

平台 YAML 校验会拦截缺项，**WorkBuddy 本地格式（`name` + `description` + `agent_created`）不足以上架**，本包已补齐：

| 字段 | 本包取值 | 说明 |
|---|---|---|
| `slug` | `oral-video-packager` | kebab-case、全网唯一、**提交后不可修改**；提示 409 被占用时改成带账号前缀后重新打包 |
| `version` | `1.3.2` | SemVer，同一 slug 下必须递增；每次内容变更都要升版本 |
| `displayName` | `口播视频包装工具` | 市场展示名 |
| `name` / `description` | 保留 | WorkBuddy 识别用，description 含触发词 |
| `summary` / `tags` / `category` / `platforms` / `license` / `visibility` | 见 SKILL.md | 建议项，不阻断发布 |

**描述（description）怎么填**：网页表单里该字段选填、上限 1024 字符，但**建议手填**而非留空（留空会去读 `SKILL.md` 的 frontmatter）。推荐 80–200 字三段式：首句讲用户价值（这工具帮我做什么）→ 中段列核心能力 → 尾段以 `Use when`（或「适用场景：」）集中放触发词。触发词必须保留（字幕、人物名片、知识动画、切片剪辑、去静音、参考成片等），否则对话里不会被自动匹配；避免「最强 / 效率提升 10 倍」等夸大表述，内容合规扫描会拦。本包 `SKILL.md` 与 `manifest.yaml` 的 description 已按此规范写成同一段文案，因此从 GitHub 导入时描述留空也会读到规范版本。

常见驳回原因：`slug` 冲突或格式不对、ZIP 根目录无 `SKILL.md`、包超过 10MB、描述含夸大宣传、脚本被判有隐私或网络风险、审核期间重复提交。被拒后在「版本历史」查看拒绝原因与安全报告（科恩 / 云鼎），修完重新打包并递增 `version` 再提交。

| 网页发布 | CLI 发布 |
|---|---|
| 登录 skillhub.cn → 技能发布页 → 填写名称 / 描述 / 版本 `1.3.2` / 分类「视频创作」/ 标签 → 上传扁平包 → 提交审核 | `skillhub login` → `skillhub init --name --category` → `skillhub push` → `skillhub publish --dry-run` → `skillhub publish` |

CLI 用 `--visibility public|unlisted|private|org` 控制可见范围。

### 从 GitHub 导入（持续迭代推荐）

前置：SkillHub 个人中心 → 左侧栏底部的绑定入口（或「我的 Skills」顶部蓝色卡片）→ 完成 GitHub OAuth 绑定；仓库需公开、非 fork、非归档。

1. 打开 `https://skillhub.cn/dashboard/publish` → 选「从 GitHub 导入」→ 刷新，扫描已绑定账号公开仓库中的 `SKILL.md`（单次最多导入 5 个）。
2. 勾选 `oral-video-packager` → 下一步进入确认页。
3. 逐项核对 Slug（实时查重）、显示名称、版本号 `1.3.2`、描述（留空自动读 `SKILL.md` 的 description）、图标。
4. 点发布 → 三线安全审核 → 上架。以后代码 `git push` 后回到导入页重新同步并递增 `version` 即可，无需重传 zip。

平台限制：仓库 >20MiB、候选目录 >10MiB、文件数 >200 会被拦；`.png` 等二进制文件在导入时会被过滤，因此 `icon.png` 需在确认页单独上传或改用预设图标。后端重打包会剥掉目录前缀，保证 ZIP 根目录就是 `SKILL.md`。本仓库约 20 个源码文件、百 KB 量级，符合限制。

审核：内容合规过滤、科恩实验室漏洞扫描、云鼎实验室 AI 模型安全评估三线并行，全部通过才自动上架；另有 TRACE 评测（Trust 为红线维度）。版本采用语义化版本，**同一 Skill 标识下必须递增，且标识提交后不可修改**；更新在「我的技能」里点「更新」上传新包，同样需要重新审核。技能内容每次改动后需重新生成扁平包、递增版本号再走更新流程。

### 运行前置依赖

| 依赖 | 用途 | 验证 / 安装 |
|---|---|---|
| ffmpeg + ffprobe | 抽帧、合成、拼接 | 加入 PATH，`ffprobe -version` 能打印版本即可 |
| Python 3.9+ | 主引擎与参考片分析 | `python --version` |
| Pillow | 逐帧绘制叠层 | `pip install Pillow` |
| 中文字体 | 字幕与竖排名片 | Windows 自带微软雅黑；macOS 用 PingFang；Linux 装 `fonts-noto-cjk` |
| Node 18+ / npm | **仅** Remotion 后端 | `node -v` |
| Chrome 或 Edge | **仅** Remotion 渲染 | 脚本自动探测，无需另装 Chromium |

只用内置 Pillow 后端时，前四项即可，**不需要 Node、npm 或联网**。首次启用 Remotion 后端（zip 不含 `node_modules` 与渲染缓存）：

```bash
cd <skill目录>/remotion
npm install --registry=https://registry.npmmirror.com --no-audit --no-fund
```

### 必改项

`assets/*.example.json` 都是本机回归示例，**含 4 个绝对路径，新用户必须替换**：`source`、`reference`（可删）、`output`、`workdir`；若 `ending.avatar` 用参考片裁头像，`ending.avatar.video` 也要改；切片示例还需改 `clip.output`。`person` 的姓名 / 机构 / 科室 / 职称必须由用户提供，不得沿用示例值（见 1b 节）。

### 第一次跑通

```bash
python scripts/analyze_reference.py --video <参考片.mp4> --outdir ref_analysis   # 可选
python scripts/package_video.py --config <你的config.json> --preview-card card.png
python scripts/package_video.py --config <你的config.json>

# 可选：切片剪辑（配置里写 clip 段，或直接用命令行区间）
python scripts/package_video.py --config <你的config.json> --clip-only
python scripts/package_video.py --config <你的config.json> --clip-ranges "0,12 18,33 41,64"
```

第三条输出成片、`subtitles.srt` / `subtitles.ass`、`contact_sheet.png`、`review_checklist.json`。终端出现 `STATUS: DRAFT_PENDING_HUMAN_REVIEW` 即成功。

### 在对话里怎么用

直接用自然语言描述需求即可，例如「用口播视频包装工具把这段素材做成带字幕、人物名片和知识动画的成片，参考片是这份」。技能依据 `SKILL.md` 的 description 自动匹配，也可在对话里点名调用。脚本会读取本地视频、调用 ffmpeg 并写文件，导入第三方技能时提示权限属预期行为。

## 1. 配置文件字段全表

顶层：

| 字段 | 类型 | 说明 |
|---|---|---|
| `source` | string | 必填，真人出镜原片绝对路径 |
| `profile` | string | 场景预设：`medical`（默认）/ `product` / `ecommerce` / `clip` / `general`，见 1c |
| `reference` | string | 可选，参考成片路径；仅用于风格分析与片尾头像裁切 |
| `output` | string | 成片输出路径 |
| `workdir` | string | 中间帧与临时视频目录，默认 `<output 同级>/.packager_work` |
| `background_time` | number | 取原片哪一秒作为动画段的模糊背景，默认时长 × 0.35 |
| `animation_frames` | string | 可选，外部透明 PNG 帧序列目录；填了即启用外部后端 |
| `clip` | object | 可选，切片剪辑方案；填了即在包装前自动切片并重映射时间轴，见 1d |
| `shots` | object / array | 可选，内容驱动分镜；填了即按语义切换画面分格，见 1e |
| `title_card` | object | `{text, sub, show:[起,止]}` 片头金黄大标题 |
| `person` | object | 竖排人物名片，字段与输入方式见「1b. 人物名片」 |
| `subtitles` | array | `[{start, end, lines:[...]}]`，行内 `**文字**` 为金黄高亮 |
| `segments` | array | 知识动画段，见下表 |
| `disclaimer` | array<string> | 底部常驻免责行，最多 4 行（黑条高度按行数自适应）；医学科普不得省略。AI 生成标识默认不写入，由后期处理 |
| `ending` | object | `{duration, avatar, text, footer}` 片尾卡 |
| `style` | object | 颜色、字号、画中画、模糊度，见下表 |
| `audio` | object | `{fade_out:[起始秒, 时长]}`；原声始终保留 |

`segments` 每项：

| 字段 | 说明 |
|---|---|
| `start` / `end` | 秒，精确到 0.1；与对应口播句对齐 |
| `kind` | 医学 `timeline` / `scan` / `resection`；通用 `features` / `compare` / `stats` / `funnel` / `steps` / `matrix`；共用 `quote` / `points` |
| `title` / `sub` | 金黄主标题、白色副标题（Pillow 与 Remotion 通用） |
| `quote` | 非 quote 段底部的金色强调句 |
| `labels` | timeline 专用，三个时间节点标签 |
| `marker` | scan 专用，扫到病灶时的标注文字 |
| `points` | resection / points 专用，逐条浮现的要点卡 |
| `lines` | quote 专用，`[{text, color:"white"\|"gold", at:0..1}]`，`at` 是该段进度比例 |
| `footer` | quote 专用，底部补充句 |

`style`：

| 字段 | 默认 | 说明 |
|---|---|---|
| `gold` / `gold_light` | `[226,178,38]` / `[245,210,96]` | 主色与高亮色（RGB） |
| `subtitle_size` | 40 | ASS 常规字幕字号 |
| `subtitle_margin_v` | 176 | 字幕底边距，增大可上移 |
| `shift_subtitles_in_segments` | true | 动画段字幕右移缩小，避免压住小真人 |
| `shifted_pos` / `shifted_size` | `[500,1080]` / 32 | 右移后的锚点与字号 |
| `pip` | `[20,770,300,435]` | 左下小真人画中画 x/y/w/h；设 `null` 关闭 |
| `background_blur` / `background_darkness` | 22 / 0.52 | 动画段背景模糊半径、压暗比例 |

`ending.avatar` 两种写法：

```json
{"avatar": "C:/path/avatar.png"}
{"avatar": {"video": "C:/path/reference.mp4", "time": 43.5, "from_reference": [208,486,512,790]}}
```

后者按 720×1280 设计坐标从参考片指定秒数裁切矩形，再做圆形遮罩。

## 1b. 人物名片（参考成片 2.mp4 规格）

名片是**竖排**的，不是横排 lower-third：蓝色渐变块上是白色竖排姓名，左侧浅蓝白底竖条上是两列蓝色竖排文字，姓名块下方是菱形装饰 + 白色竖排职称。参考片里它只在真人出镜段出现，金句卡/模糊背景段隐藏。

| 字段 | 名片位置 | 说明 |
|---|---|---|
| `name` | 蓝渐变块 | 白色竖排姓名，字号 40→22 自适应 |
| `title` | 白底条右列 | 蓝色竖排机构名，**用户输入的重点字段**，字号 22→15 自适应 |
| `department` | 白底条左列 | 蓝色竖排科室；兼容旧字段 `subtitle` |
| `rank` | 姓名块下方 | 菱形 + 白色竖排职称 |
| `show` | — | `[a,b]` 单区间或 `[[a,b],[c,d]]` 多区间，单位秒；缺省 `[[2,12]]` |

设计画布坐标（720×1280）：白底条 x=93–156、y=140–480；蓝渐变姓名块 x=156–210、y=140–275（上深蓝 `#1C5CC4` → 下亮青 `#34BEEE`）；菱形与职称 y=275–440。四个字段任一为空即跳过该部分，全部为空则不绘制名片。改样式编辑 `package_video.py` 的 `CARD` 常量与 `draw_person()`。

输入优先级：**配置文件 < 命令行覆盖 < 交互输入**。

```bash
# 命令行覆盖
python scripts/package_video.py --config c.json \
  --person-name "张三" --person-title "某某大学附属第一医院" \
  --person-department "心内科" --person-rank "主任医师" \
  --person-show "2,12 36,42"

# 交互式逐项输入（需终端）
python scripts/package_video.py --config c.json --ask-person

# 只出一张名片预览，秒级校验长文本是否溢出
python scripts/package_video.py --config c.json \
  --person-title "某某大学附属第一医院心血管内科中心" \
  --preview-card card_preview.png
```

`--person-subtitle` 是 `--person-department` 的兼容别名；`--person-show` 接受 2 个或偶数个秒数，自动两两配对成区间。非交互环境传 `--ask-person` 会打印告警并跳过，不会卡住流水线。

## 1c. 场景预设与通用动画

### 预设（profile）

| profile | 适用 | 默认免责 | 审签重点 | 推荐动画 |
|---|---|---|---|---|
| `medical`（默认） | 医学科普、健康讲解 | 不作为诊疗依据、及时就诊 | 资质认证、无疗效承诺、无虚构病例 | `timeline` `scan` `resection` `quote` `points` |
| `product` | 产品介绍、发布、测评 | 参数以官方为准、价格以实时页面为准 | 广告法绝对化用语、参数可核实、授权 | `features` `compare` `stats` `steps` `quote` |
| `ecommerce` | 电商分析、类目与竞品数据 | 不构成经营建议、数据口径以原平台为准 | 数据来源与口径、竞品可比性、时效标注 | `stats` `funnel` `compare` `matrix` `quote` |
| `clip` | 长视频切片、精华剪辑、去静音 | 节选自完整内容、语境以原片为准 | 切点不截断语义、不断章取义、来源与再发布授权、时间轴对齐 | `quote` `points` `features` `compare` `steps` |
| `general` | 泛知识、观点口播 | 无（可自定义） | 事实一致、引用授权、无夸大 | `stats` `features` `steps` `compare` |

用法：配置写 `"profile": "product"`，或命令行 `--profile product`；`--list-profiles` 列出全部。**配置里显式写 `disclaimer` 会覆盖预设**；未写则用预设值，`general` 默认不带免责行。`review_checklist.json` 会记录 `profile` 并输出该场景的审签条目。

示例配置：`assets/config.example.json`（medical）、`config.product.example.json`、`config.ecommerce.example.json`、`config.clip.example.json`。

注意 `clip` 既是预设名，也是配置里的可选对象名（切片方案）；二者同名但不冲突，可同时使用。

### 通用动画类型

| kind | 用途 | 数据字段 |
|---|---|---|
| `features` | 卖点/要点卡网格（最多 6 张，2 列） | `points: string[]` |
| `compare` | 2–3 柱横向对比 | `columns: [{label, value, note?}]` |
| `stats` | 最多 6 柱柱状图 | `bars: [{label, value}]`、`unit?` |
| `funnel` | 最多 5 层转化漏斗 | `stages: [{label, value}]` |
| `steps` | 最多 5 步流程 | `points: string[]` |
| `matrix` | 2×2 四象限 | `cells: [{label, note?}]`、`axes?` |

通用段仍支持 `title` / `sub` / `quote`。Pillow 与 Remotion 两端均已实现；`quote`、`points` 及医学专用 `timeline` / `scan` / `resection` 保持原行为不变。

## 1d. 切片剪辑

适用于长口播切精华、剔除停顿与废话、自动去静音、批量产出多条切片。由 `scripts/clip_video.py` 实现，`package_video.py` 在检测到 `clip` 配置或 `--clip-ranges` 时自动作为**第 0 步**调用。

### 核心约定

配置里 `subtitles` / `segments` / `title_card.show` / `person.show` / `background_time` / `audio.fade_out` 的时间码**一律按原片时间轴填写**。切片后引擎生成 `edit_map.json`（原时间→新时间）并把它们全部重映射到缩短后的时间轴，产物写入 `clipped_config.json`。无需手工改表，也不会出现字幕与画面对不上。

### `clip` 对象

| 字段 | 默认 | 说明 |
|---|---|---|
| `mode` | `keep` | `keep` 保留 `ranges` / `cut` 剔除 `ranges`（保留补集）/ `silence` 自动检测静音并剔除 |
| `ranges` | — | `[[start,end], ...]`，秒，原片时间轴；`silence` 模式可省略 |
| `pad` | 0.08 | 切点保护留白：`keep` 向外扩，`cut` / `silence` 向内缩，避免切在字中间 |
| `min_gap` | 0.0 | 相邻保留段间隔小于此值则合并 |
| `silence` | `{noise:"-35dB", min_duration:0.45, keep:0.12}` | `silence` 模式的检测阈值与保留边距 |
| `batch` | false | 额外导出每段 `clip_XX.mp4` + 已重映射的 `clip_XX.json` |
| `output` | `<workdir>/clipped.mp4` | 剪辑版中间视频路径 |
| `packaged_output` | 同 `output` | 切片后成片输出路径（覆盖顶层 `output`） |

切片用一次 ffmpeg `trim + setpts + atrim + asetpts + concat` 完成帧精确硬切，音画同步裁剪，每段音轨首尾 20ms 淡入淡出防爆音，输出保持源分辨率与帧率。

### 命令

```bash
# 配置驱动：一步完成切片 + 重映射 + 包装
python scripts/package_video.py --config config.clip.example.json

# 只切片，先看 clipped.mp4 / edit_map.json / clipped_config.json
python scripts/package_video.py --config c.json --clip-only

# 不改配置，命令行临时指定保留区间（自动启用切片阶段）
python scripts/package_video.py --config c.json --clip-ranges "0,12 18,33 41,64"
python scripts/package_video.py --config c.json --clip-mode silence
python scripts/package_video.py --config c.json --clip-batch

# 忽略配置里的 clip 段，用原片直接包装
python scripts/package_video.py --config c.json --no-clip

# 独立使用：只切片、不包装、不重映射
python scripts/clip_video.py --source long.mp4 --ranges "0,12 18,33" --output short.mp4
python scripts/clip_video.py --config c.json --mode silence --output short.mp4
```

### 重映射规则与边界

- 字幕：起点落在被剪区的直接丢弃；终点跨切点的裁剪到该保留段末尾；映射后不足 0.25 秒的丢弃。
- 动画段：同样裁剪到所在保留段，映射后时长不足原时长 40% 的丢弃，避免动画被压成闪帧。
- 片头标题 / 人物名片：`show` 支持多区间，逐区间映射；完全落在被剪区的区间丢弃，起点被剪的吸附到下一段开头。
- 背景取帧时间与音频淡出：前者映射到新时间轴（失效时取首段中点），后者重算为「新时长 − 淡出时长」。
- 终端会打印丢弃数量；`review_checklist.json` 的 `clip_edit` 记录源时长、保留段数、丢弃计数。
- **硬切不做转场、不补帧、不智能补字幕**。切点是否切断半句话、条件或否定词，必须人工核对 `edit_map.json` 并试听；这是 `clip` 预设审签清单第一条。

### 批量切片

`batch: true` 时在 `<workdir>/clips/` 产出每段 `clip_XX.mp4`（未包装的原片片段）与 `clip_XX.json`（只含该段元素、已重映射，可直接 `--config` 跑包装，输出为 `clip_XX_packaged.mp4`）。主成片仍照常输出拼接后的完整版本。

## 1e. 内容驱动分镜（shots）

默认路径把所有 `segments` 画成同一套「模糊背景 + 圆形小真人 + 金黄卡片」。启用 `shots` 后按内容切分镜头；**默认 `restrained` 风格**：版式统一克制，差异靠配色与特效，而不是把画面切成各种分格。

### 默认：restrained（统一网格 + 主题配色）

所有段落共用同一套排版骨架：真人始终全屏为主体；顶部固定位置一个主题胶囊标签（淡入 + 轻微滑入）；底部固定渐变字幕安全区 + 全片进度线；四角暗角。构图从头到尾不变。

| 元素 | 实现 |
|---|---|
| 全片固定色调 | 6 套色板 `amber` 暖橙 / `slate` 青灰 / `blue` 蓝 / `gold` 金 / `rose` 柔粉 / `sage` 青绿；**一条片只选一套，全片不跳色**。`auto` 按 profile 选（`clip`→amber、`medical`→blue、`product`→gold、`ecommerce`→slate），写具体色板名可手动指定；风格差异体现在不同视频之间 |
| 整帧色调分级 | 对 RGB 三通道施加不同增益（LUT 缓存，快），画面明显偏色但细节与构图不变；`shots.grade: false` 可关 |
| 轻特效 | Ken Burns 缓慢推近（clean 1.03 / push 1.10）、暗角、底部渐变、顶部标签淡入滑入、进度线随全局时间推进、镜头间 smoothstep 交叉淡化、ASS 字幕 `\fad(180,180)` |
| 4 种克制版式 | `clean` 全屏（默认）/ `push` 轻推近 / `caption` 唯一一条金句色带 / `blurpip` 精简画中画 |

自动规则（关键：**全片一套色、版式变化要少**）：知识段标题并入顶部标签（胶囊默认显示片名）；含数字/比较词不再改成分屏；短情绪句最多触发 1 次金句色带；动作占比高的段保留完整画面；`push` ≤2 次、`caption` ≤1 次。顶部胶囊、进度线、色带、片头标题全部使用同一套 accent，镜头间不换色。**`clip` / `general` 场景完全不虚化真人**（`blurpip` 禁用），只有 `medical` / `product` / `ecommerce` 允许最多 2 段精简画中画。

### 可选：expressive（八版式，1.2.0 行为）

`shots.style: "expressive"` 恢复按语义切换 `full` / `focus` / `pip` / `split_v` / `split_h` / `grid` / `card` / `kinetic` 八种画面分格，映射规则：知识段按 `kind`（`quote`→card、`points`/`features`→grid、`steps`/`funnel`→split_h、`stats`/`compare`→split_v）、含数字/比较词→split_v、短情绪句→kinetic、长句→full、动作段→full/focus、连续同版式强制换。适合信息密度高的知识类，**切片 / 生活向不建议**（画面容易显得乱）。

### 配置

| 字段 | 默认 | 说明 |
|---|---|---|
| `shots` | — | `{"mode":"auto","style":"restrained"}`；也可直接给 shot 数组或 `{"plan":[...]}` |
| `shots.style` | `restrained` | `restrained` 统一网格+配色 / `expressive` 八版式 |
| `shots.theme` | `auto` | `auto` 按 profile 选一套**全片固定**；写 `amber`/`blue`/... 手动指定；仅 `dynamic` 才逐段换色（兼容旧行为，不推荐） |
| `shots.grade` | true | 整帧色调分级开关 |
| `shots.transition` | `fade` | `fade` / `slide` / `cut` |
| `shots.transition_duration` | 0.40 | 转场秒数（smoothstep 平滑） |
| `shots.min_duration` | 1.15 | 短切片并入相邻镜头 |
| `shots.debug_label` | false | 调试角标（仅 expressive 生效） |

### 产物与回灌

`shot_plan.json` 同时写到 `workdir` 和成片目录，含每段 `start/end/layout/palette/headline/items/reason/subtitle/progress`。人工改完用 `--shot-plan <file>` 回灌；`--plan-only` 只出计划。字幕 ASS 按 shot 的 `subtitle` 自动加 `\fad/\pos/\fs`。质检拼板按 `(layout, palette)` 去重采样，保证能看到不同配色。

### 命令

```bash
python scripts/package_video.py --config c.json --auto-shots
python scripts/package_video.py --config c.json --plan-only
python scripts/package_video.py --config c.json --shot-plan shot_plan.json
python scripts/shot_engine.py --config c.json --duration 29.8 --plan-only --out plan.json
python scripts/package_video.py --config c.json --no-shots   # 回退固定模板
```

### 实现与边界

`shot_engine.render()` 把源抽成 JPEG 帧序列，逐帧按当前 shot 渲染（Pillow），镜头切换点渲染前后两套做 crossfade/slide，输出 `shots_main.mp4`（含原声）；`compose_shots()` 只烧 ASS 字幕与拼片尾。旧路径 `build_frames()` + `compose()` 完全不动。分镜模式**不绘制竖排人物名片**、不走 Remotion / 外部帧后端；`segments` 用于规划配色与顶部标签文案，不再由 `Animator` 绘制。切片点本身仍是硬切，转场只发生在镜头之间。

## 2. 动画后端

| 后端 | 命令 | 动效特征 | 适用 |
|---|---|---|---|
| 内置 Pillow | `package_video.py --config c.json` | easeOutCubic 进度、逐条淡入、几何示意 | 零依赖、快速出片、离线 |
| Remotion | `render_remotion.py` 然后 `package_video.py --animation-frames DIR` | spring 弹性、贝塞尔缓动、SVG 渐变/阴影/漂浮、元素 stagger | 观感要求高、需要自然动效 |
| 外部逐帧 | 自行生成透明 RGBA PNG → `--animation-frames DIR` | 不限 | AE / Blender / CSS 动画 / 其他引擎 |

Remotion 首次安装：

```bash
cd remotion
npm install --registry=https://registry.npmmirror.com --no-audit --no-fund
```

`render_remotion.py` 会自动探测本机 Chrome / Edge 并通过 `--browser-executable` 传给 Remotion，无需下载 Chromium。渲染使用 `--sequence --image-format=png`（Remotion 4.0.542+ 已移除 `--codec=png`），输出 `element-<帧号>.png`；透明背景由组件自身保证。引擎按文件名中的帧号建索引而非字典序，避免 `element-10.png` 排在 `element-2.png` 前面。**外部帧只在 `segments` 区间被读取**，其余时间输出透明帧即可。

外部帧约定：720×1280 RGBA，非动画区域保持透明；动画内容放在 y < 740，避免覆盖左下小真人窗口（y ≥ 770）；淡入淡出可交给引擎的 `fade`，也可自行烘焙。

## 3. 时间轴与坐标

- 设计画布恒为 720×1280，所有配置坐标按此填写；引擎在 overlay 时缩放到源视频尺寸。
- **规格自适应**：源不是 720×1280 / 30fps 时自动 `scale=...:force_original_aspect_ratio=decrease,pad=...,fps=30` 统一画布与帧率，音频统一 48kHz 立体声。启用切片时由 `clip_video.render_segments()` 在 concat 后一次完成（不重复转码）；未启用切片时由 `package_video.normalize_source()` 在 probe 后生成 `<workdir>/normalized.mp4`。这样 `compose()` 里硬编码的 PiP crop 与叠层坐标不会越界。手机竖屏（540×960@19fps）实测可直接跑通。
- 小真人窗口挖空由引擎完成：动画段背景帧在该区域 alpha=0，主视频经 `crop → scale → alphamerge → overlay` 变成动态画中画，位于动画浮层之下。
- 叠层顺序：主视频 → 小真人 → 动画/静态浮层 → ASS 字幕。
- 启用切片后，上述时间轴全部按 `edit_map.json` 重映射；`clipped.mp4` 成为新的主视频输入，设计画布与坐标不变。
- 字幕在动画段自动右移（`\pos(500,1080)\fs32`），因为常规居中字幕会压住左下画中画。

## 4. ffmpeg 实战坑（已在引擎中规避）

| 现象 | 原因 | 处理 |
|---|---|---|
| `Unrecognized option 'vsync'` | ffmpeg 7+ 移除 `-vsync` | 用 `-fps_mode vfr` |
| 视频流比音频短 2 秒、片尾卡不显示 | `tpad` 放在 `ass` 之后、后面再接 `overlay` 时未延长输出流 | 改为「主体 + 独立 2 秒片尾」两个文件，用 concat demuxer `-c copy` 拼接 |
| `ass=E:/...` 报错 | filter_complex 里冒号是分隔符 | ffmpeg 工作目录设为 workdir，滤镜写 `ass=subtitles.ass` 相对路径 |
| 中文变方块 | 缺中文字体 | 自动探测 `msyhbd.ttc` / `simhei.ttf` / Noto CJK；ASS 用 `Microsoft YaHei` |
| 示意图透出背景书架 | 半透明填充叠在模糊背景上 | 图形填充统一用 alpha 255 |
| PNG 帧序列只有 1 帧 | 单帧图片作为 overlay 输入 | 帧序列用 `-framerate <fps> -start_number 0 -i frames/%05d.png` |
| `alphamerge` 尺寸不符 | 蒙版与画中画尺寸不一致 | 两侧都 `scale` 到 `pip` 的 w/h，蒙版先 `format=gray` |

## 5. 合规细则

以下医学条款**仅 `medical` 预设适用**，依据 2025 年 8 月中央网信办、国家卫健委等四部门《关于规范"自媒体"医疗科普行为的通知》。

2025 年 8 月中央网信办、国家卫健委等四部门《关于规范"自媒体"医疗科普行为的通知》已落地的硬要求：

- 严禁无资质账号生产发布专业医疗科普内容；平台核验医师资格证、执业证并在主页展示。
- 引用转载、医疗旧闻、摆拍剧情、**AI 生成合成的医疗科普信息**、真实健康经历分享，须严格标注信息来源或生成合成内容标识。
- 严禁以介绍健康养生知识形式变相发布医疗、药品、医疗器械、保健食品、特医食品广告；同页面不得出现经营者联系方式、购物链接。
- 重点清理 AI 编造同质化涉医文案、夸大疗效、虚构病例、假冒医生身份、鼓动拒绝就医。
- 违规处置含取消互动、清粉、取消营利权限、禁言、关闭。

2026 年 3 月政协委员提出分级审核、AI 内容标「AI 合成」、高临床指导意义内容强制复核——**属建议、非现行规定**，但按此设计流程无妨。

引擎落地：底部免责（默认两行，不含 AI 标识，黑条高度随行数自适应）、片尾免责、`review_checklist.json` 状态 `DRAFT_PENDING_HUMAN_REVIEW`、`auto_publish: false`。**AI 生成合成标识按用户流程由后期/发布环节添加，工具不烧录**，清单里登记为待办项。发布前仍需：本人/科室审签、职称与资质核对、账号资质认证、平台 AI 标识与来源标注。

### 其他场景的合规要点

- `product`：遵守《广告法》，避免「最」「第一」等绝对化用语；参数、认证、检测报告与销量数据须可溯源；价格与促销标注有效期与适用条件；肖像、品牌标识、音乐与字体需授权。
- `ecommerce`：标注数据来源、时间区间与统计口径；竞品信息来自公开可核实渠道，不作不当比较；预测值明确标注；价格与排名标注采集时间；不诱导交易或规避平台规则。
- `clip`：逐句核对切点未截断语义、节选与上下文一致；标注原片来源、发布时间与「节选/剪辑」；确认肖像、原片版权与音乐已获再发布授权；字幕与动画按新时间轴重新对齐。医学素材做切片时仍须叠加 `medical` 的资质与免责要求。
- `general`：事实与字幕一致，引用可溯源，无未经验证的承诺。

四者同样要求成片待人工审签、不自动发布；AI 生成合成标识由后期/发布环节处理。

## 6. 质检清单

- [ ] 中文字幕无乱码、无裁切，关键词高亮正确
- [ ] 字幕与底部免责小字不重叠
- [ ] 动画段字幕不压左下小真人窗口
- [ ] 片头标题、人物条不遮挡人脸
- [ ] 四段动画按 `start`/`end` 出现，进出场无硬切
- [ ] 片尾卡（头像、对勾、文字）完整，总时长 = 原片 + 片尾
- [ ] 音画同步、原声完整、结尾淡出
- [ ] `review_checklist.json` 已交由人工审签
- [ ] 切片项目额外核对：`edit_map.json` 切点未截断语义、`clipped_config.json` 时间轴无残留、片尾免责与来源标注齐全

## 7. 扩展

- **新增动画类型**：在 `package_video.py` 的 `Animator` 加 `_xxx` 方法并在 `frame()` 分派；同时在 `remotion/src/Overlay.tsx` 加同名组件，`Segment.kind` 联合类型补上字面量。
- **换配色**：改 `style.gold` / `gold_light`，Remotion 的 props 会自动同步。
- **改字幕引擎**：ASS 由 `build_subtitles()` 生成，可换成外部 SRT 读取器。
- **接 TTS/补录**：引擎不做配音；在 `audio` 里替换音轨需自行扩展 `compose()` 的 `-map [aout]`。
- **批量日更**：把 `config.json` 模板化，用脚本按选题生成 `subtitles`/`segments`，循环调用引擎；用 WorkBuddy 定时任务驱动，但**不要串发布动作**。
- **改切片规则**：`clip_video.py` 的 `build_ranges()` 决定保留段，`remap_config()` 决定时间轴重映射；`render_segments()` 决定 ffmpeg 切片与拼接滤镜。
- **发版**：`python scripts/make_dist.py --src . --out dist` 从源码生成两个 zip；push `v*` tag 触发 `.github/workflows/release.yml` 自动建 Release，见第 9 节。

## 8. 故障排查

| 症状 | 排查 |
|---|---|
| `ffmpeg/ffprobe failed` | 确认 ffmpeg 在 PATH；查看命令输出末尾的 stderr |
| 输出全是黑帧 | 检查 `background_time` 是否超出原片时长、帧序列编号是否从 `00000.png` 开始 |
| Remotion render 失败 | 确认 `remotion/node_modules` 存在、`props.json` 已生成、Chrome 路径有效；4.0.542+ 必须用 `--sequence`，`--codec=png` 会报 Codec 错误 |
| 外部帧没生效 | 目录里必须是 `.png`，按文件名排序，数量 ≥ 源视频总帧数 |
| 动画段人物消失 | `pip` 被设为 null，或外部帧在窗口区域不透明 |
| 成片比预期短 | 检查 `ending.duration` 与 concat 的 `list.txt`；切片项目先看 `edit_map.json` 的保留段总长 |
| 切片后字幕/动画错位或消失 | 查看终端的 dropped 计数与 `clipped_config.json`；被剪区的字幕会被丢弃，跨切点动画会被裁剪，必要时调整 `clip.ranges` 避开知识点 |
| 切片声音有爆音 | 每段已有 20ms 淡入淡出；若源音频本身削波，调小 `clip.silence.noise` 或改用外部音频处理 |
| `--clip-only` 报错 | 需要配置里有 `clip` 段或命令行给 `--clip-ranges`；`--no-clip` 与 `--clip-only` 不能同时使用 |
| 分镜模式首帧报 `FileNotFoundError: 00000.jpg` | ffmpeg image2 可能从 00001 起编号；引擎已改为按实际文件列表索引并在抽帧时显式 `-start_number 0` |
| 分镜模式没有人物名片 / Remotion 动效 | 设计如此，见 1e；用 `--no-shots` 回退旧路径 |
| 手机素材画中画错位 / 黑屏 | 确认日志出现 `normalize ... -> 720x1280@30`；未归一化时 PiP `crop=400:580:160:250` 会越界 |
| `show` 报 `list <= float` | 重映射后的 `show` 是多区间列表；引擎用 `in_ranges()` 处理，勿改回单区间假设 |

## 9. 版本与发布

当前版本 **`1.3.2`**（1.3.1 全片固定色调；1.3.2 把 `description` 改为三段式触发文案）。任何内容改动都要同步递增版本，否则 SkillHub 会判重复提交。

| 位置 | 作用 |
|---|---|
| `SKILL.md` frontmatter `version` | SkillHub / WorkBuddy 读取的主版本 |
| `manifest.yaml` `version` | SkillHub 从 GitHub 导入时读取，必须与上一行一致 |
| `git tag v1.3.2` | GitHub Release 与自动发版的触发器 |

发布流程：

```bash
# 1. 升版本后从源码生成两个发布包（内容一致，仅目录层级不同）
python scripts/make_dist.py --src . --out dist
#    dist/oral-video-packager.zip            带外层目录，WorkBuddy「添加技能 → 上传技能」
#    dist/oral-video-packager-skillhub.zip  扁平根目录 SKILL.md，SkillHub 网页上传
#    dist/oral-video-packager-v1.3.2.zip    Release 附件（WorkBuddy 格式）

# 2. 提交并打 tag；push tag 会自动建 GitHub Release 并挂上 zip
git add -A && git commit -m "feat: ..."
git tag -a v1.3.2 -m "v1.3.2"
git push origin main && git push origin v1.3.2
```

`.github/workflows/release.yml` 在 push `v*` tag 时运行 `make_dist.py`，用仓库自带的 `GITHUB_TOKEN` 创建 Release 并附上 zip。首次使用需在仓库 Settings → Actions → General → Workflow permissions 勾选 **Read and write permissions**，否则建 Release 会因权限不足失败（不影响 tag 本身）。

SkillHub 侧：从 GitHub 导入时确认页版本号填 `1.3.2`（历史版本已提交过则必须递增）；网页上传则用扁平包。历史 Release 资产不覆盖。
