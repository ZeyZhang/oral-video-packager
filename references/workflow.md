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
| `version` | `1.0.0` | SemVer，同一 slug 下必须递增 |
| `displayName` | `口播视频包装工具` | 市场展示名 |
| `name` / `description` | 保留 | WorkBuddy 识别用，description 含触发词 |
| `summary` / `tags` / `category` / `platforms` / `license` / `visibility` | 见 SKILL.md | 建议项，不阻断发布 |

常见驳回原因：`slug` 冲突或格式不对、ZIP 根目录无 `SKILL.md`、包超过 10MB、描述含夸大宣传、脚本被判有隐私或网络风险、审核期间重复提交。被拒后在「版本历史」查看拒绝原因与安全报告（科恩 / 云鼎），修完重新打包并递增 `version` 再提交。

| 网页发布 | CLI 发布 |
|---|---|
| 登录 skillhub.cn → 技能发布页 → 填写名称 / 描述 / 版本 `1.0.0` / 分类「视频创作」/ 标签 → 上传扁平包 → 提交审核 | `skillhub login` → `skillhub init --name --category` → `skillhub push` → `skillhub publish --dry-run` → `skillhub publish` |

CLI 用 `--visibility public|unlisted|private|org` 控制可见范围。

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

`assets/config.example.json` 是本机回归示例，**含 4 个绝对路径，新用户必须替换**：`source`、`reference`（可删）、`output`、`workdir`；若 `ending.avatar` 用参考片裁头像，`ending.avatar.video` 也要改。`person` 的姓名 / 机构 / 科室 / 职称必须由用户提供，不得沿用示例值（见 1b 节）。

### 第一次跑通

```bash
python scripts/analyze_reference.py --video <参考片.mp4> --outdir ref_analysis   # 可选
python scripts/package_video.py --config <你的config.json> --preview-card card.png
python scripts/package_video.py --config <你的config.json>
```

第三条输出成片、`subtitles.srt` / `subtitles.ass`、`contact_sheet.png`、`review_checklist.json`。终端出现 `STATUS: DRAFT_PENDING_HUMAN_REVIEW` 即成功。

### 在对话里怎么用

直接用自然语言描述需求即可，例如「用口播视频包装工具把这段素材做成带字幕、人物名片和知识动画的成片，参考片是这份」。技能依据 `SKILL.md` 的 description 自动匹配，也可在对话里点名调用。脚本会读取本地视频、调用 ffmpeg 并写文件，导入第三方技能时提示权限属预期行为。

## 1. 配置文件字段全表

顶层：

| 字段 | 类型 | 说明 |
|---|---|---|
| `source` | string | 必填，真人出镜原片绝对路径 |
| `reference` | string | 可选，参考成片路径；仅用于风格分析与片尾头像裁切 |
| `output` | string | 成片输出路径 |
| `workdir` | string | 中间帧与临时视频目录，默认 `<output 同级>/.packager_work` |
| `background_time` | number | 取原片哪一秒作为动画段的模糊背景，默认时长 × 0.35 |
| `animation_frames` | string | 可选，外部透明 PNG 帧序列目录；填了即启用外部后端 |
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
| `kind` | `timeline` / `scan` / `resection` / `quote` / `points` |
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
- 小真人窗口挖空由引擎完成：动画段背景帧在该区域 alpha=0，主视频经 `crop → scale → alphamerge → overlay` 变成动态画中画，位于动画浮层之下。
- 叠层顺序：主视频 → 小真人 → 动画/静态浮层 → ASS 字幕。
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

## 5. 医学/健康内容合规细则

2025 年 8 月中央网信办、国家卫健委等四部门《关于规范"自媒体"医疗科普行为的通知》已落地的硬要求：

- 严禁无资质账号生产发布专业医疗科普内容；平台核验医师资格证、执业证并在主页展示。
- 引用转载、医疗旧闻、摆拍剧情、**AI 生成合成的医疗科普信息**、真实健康经历分享，须严格标注信息来源或生成合成内容标识。
- 严禁以介绍健康养生知识形式变相发布医疗、药品、医疗器械、保健食品、特医食品广告；同页面不得出现经营者联系方式、购物链接。
- 重点清理 AI 编造同质化涉医文案、夸大疗效、虚构病例、假冒医生身份、鼓动拒绝就医。
- 违规处置含取消互动、清粉、取消营利权限、禁言、关闭。

2026 年 3 月政协委员提出分级审核、AI 内容标「AI 合成」、高临床指导意义内容强制复核——**属建议、非现行规定**，但按此设计流程无妨。

引擎落地：底部免责（默认两行，不含 AI 标识，黑条高度随行数自适应）、片尾免责、`review_checklist.json` 状态 `DRAFT_PENDING_HUMAN_REVIEW`、`auto_publish: false`。**AI 生成合成标识按用户流程由后期/发布环节添加，工具不烧录**，清单里登记为待办项。发布前仍需：本人/科室审签、职称与资质核对、账号资质认证、平台 AI 标识与来源标注。

## 6. 质检清单

- [ ] 中文字幕无乱码、无裁切，关键词高亮正确
- [ ] 字幕与底部免责小字不重叠
- [ ] 动画段字幕不压左下小真人窗口
- [ ] 片头标题、人物条不遮挡人脸
- [ ] 四段动画按 `start`/`end` 出现，进出场无硬切
- [ ] 片尾卡（头像、对勾、文字）完整，总时长 = 原片 + 片尾
- [ ] 音画同步、原声完整、结尾淡出
- [ ] `review_checklist.json` 已交由人工审签

## 7. 扩展

- **新增动画类型**：在 `package_video.py` 的 `Animator` 加 `_xxx` 方法并在 `frame()` 分派；同时在 `remotion/src/Overlay.tsx` 加同名组件，`Segment.kind` 联合类型补上字面量。
- **换配色**：改 `style.gold` / `gold_light`，Remotion 的 props 会自动同步。
- **改字幕引擎**：ASS 由 `build_subtitles()` 生成，可换成外部 SRT 读取器。
- **接 TTS/补录**：引擎不做配音；在 `audio` 里替换音轨需自行扩展 `compose()` 的 `-map [aout]`。
- **批量日更**：把 `config.json` 模板化，用脚本按选题生成 `subtitles`/`segments`，循环调用引擎；用 WorkBuddy 定时任务驱动，但**不要串发布动作**。

## 8. 故障排查

| 症状 | 排查 |
|---|---|
| `ffmpeg/ffprobe failed` | 确认 ffmpeg 在 PATH；查看命令输出末尾的 stderr |
| 输出全是黑帧 | 检查 `background_time` 是否超出原片时长、帧序列编号是否从 `00000.png` 开始 |
| Remotion render 失败 | 确认 `remotion/node_modules` 存在、`props.json` 已生成、Chrome 路径有效；4.0.542+ 必须用 `--sequence`，`--codec=png` 会报 Codec 错误 |
| 外部帧没生效 | 目录里必须是 `.png`，按文件名排序，数量 ≥ 源视频总帧数 |
| 动画段人物消失 | `pip` 被设为 null，或外部帧在窗口区域不透明 |
| 成片比预期短 | 检查 `ending.duration` 与 concat 的 `list.txt` |
