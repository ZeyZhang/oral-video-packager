---
name: oral-video-packager
description: >-
  把真人出镜的竖屏口播素材包装成带逐句字幕、人物介绍条、知识动画、
  免责声明与片尾卡的成片，适用于医学科普、产品介绍、电商产品分析、
  切片剪辑、知识讲解等场景，按 profile 切换免责声明与审签清单；
  支持长视频按时间码/去静音切出精华片段并自动重映射字幕与动画时间轴；
  可按内容语义把时间轴切成多个镜头，自动切换全屏/推近/分屏/宫格/大字卡等
  八种画面分格并带转场，字幕位置随版式变化，不套固定模板；
  支持 Pillow / Remotion / 外部逐帧三种动画后端，可复用参考成片视觉规格。
  本 skill 应在用户提供「素材视频 + 参考成片」或要求为口播视频添加
  字幕、人物介绍、知识动画、片尾包装、产品卖点、数据图表，或要求把
  长视频切片剪辑、去静音、提取精彩片段，或要求按内容切换分镜/版式/分屏时使用。
agent_created: true
slug: oral-video-packager
version: 1.2.0
displayName: 口播视频包装工具
summary: 把真人出镜的口播素材包装成带逐句字幕、竖排人物名片、知识动画与片尾的竖屏成片
category: 视频创作
platforms:
  - WorkBuddy
tags:
  - 口播视频
  - 字幕
  - 知识动画
  - 视频包装
  - 切片剪辑
license: MIT
visibility: public
---

# 口播视频包装工具

## 用途

把一段真人出镜口播原片，按可选的参考成片风格，加工成可发布的竖屏成片。全流程本地执行：ASR 转写 →（可选）切片剪辑 → 分镜与字幕 → 动画层渲染 → 音画合成 → 质检 → 审签清单。切片阶段可把长视频按时间码或自动去静音切成精华版，并把字幕、动画、人物条的时间轴自动重映射；也可批量导出多条独立切片。医学/健康类内容默认带底部免责声明与片尾免责；**AI 生成合成标识不在画面烧录，由后期/发布环节处理**。工具**只产出草稿，不自动发布**。

## 何时使用

- 提供「素材视频 + 参考成片」，要求把素材做成参考片那种效果
- 要求给口播视频加字幕、人物介绍条、知识动画、片头标题、片尾卡
- 需要把一次性剪辑流程固化，供后续批量/日更复用
- 长口播要切成精华短片、剔除停顿/废话、自动去静音，或批量产出多条切片
- 医学科普、产品介绍、电商分析、知识讲解类短视频的包装与发布前自检
- 不希望所有段落都长成同一个模板，要求「按内容切换画面分格 / 分镜版式」

## bundled 资源

| 路径 | 作用 |
|---|---|
| `scripts/analyze_reference.py` | 拆解参考成片：元信息、2 秒网格拼板、关键帧、待填规格骨架 |
| `scripts/package_video.py` | 主引擎：读配置生成字幕/叠层/成片/审签清单/质检拼板 |
| `scripts/clip_video.py` | 切片剪辑：keep/cut/silence 三种模式、时间轴重映射、批量导出 |
| `scripts/render_remotion.py` | 用 Remotion 渲染自然动效的透明 PNG 帧序列 |
| `scripts/make_dist.py` | 从源码生成 WorkBuddy / SkillHub 两个发布 zip |
| `scripts/shot_engine.py` | 内容驱动分镜：自动规划 shot_plan.json + 八种画面分格逐帧渲染与转场 |
| `remotion/` | Remotion 模板工程（React + spring/interpolate + SVG 动画） |
| `assets/config.example.json` | 完整可跑的医学科普配置示例 |
| `assets/config.clip.example.json` | 切片剪辑配置示例（配置按原片时间轴写，引擎自动重映射） |
| `assets/config.product.example.json` / `config.ecommerce.example.json` | 产品介绍 / 电商分析配置示例 |
| `references/workflow.md` | 配置字段全表、切片剪辑、ffmpeg 坑、合规细则、故障排查 |

## 工作流

### 1. 收集输入

向用户索取：素材视频绝对路径、参考成片路径（可选），以及名片四要素 `name`（姓名）/ `title`（机构）/ `department`（科室）/ `rank`（职称）。**人物信息必须由用户提供**，不得复用 `config.example.json` 里的示例值，也不得从工牌或参考片自行推断后当作用户输入。用户未提供时先询问；用户明确说留空才留空。空字段不绘制，不编造职称。

### 1b. 选择场景预设

按内容类型选 `profile`：`medical`（医学科普，默认）/ `product`（产品介绍）/ `ecommerce`（电商产品分析）/ `clip`（切片剪辑）/ `general`（通用口播）。预设决定底部免责声明、审签清单与推荐动画类型。命令行用 `--profile product`，`--list-profiles` 查看全部；示例见 `assets/config.product.example.json`、`assets/config.ecommerce.example.json`、`assets/config.clip.example.json`。

`clip` 是场景预设，同时 `clip` 也是配置里的可选对象（切片方案）；两者同名但不冲突，`config.clip.example.json` 演示了二者同时使用。

### 2. 拆解参考成片（有参考片时）

```bash
python scripts/analyze_reference.py --video <参考片.mp4> --outdir <分析目录>
```

查看 `contact_sheet.png`（每格 2 秒）与 `key_*.png`，提取标题颜色/字号、字幕位置与描边、人物条、知识动画出现的时间段、片尾样式，写入 `config.json` 的 `style` / `segments` / `ending`。使用视觉查看工具读取拼板，不要凭猜测填写。

### 3. 转写与分镜

对素材音轨执行转写，得到带时间码的口播文本。按语义切成每条 2–5 秒的字幕行，仅删除「嗯、呃」等口癖，**不改写、不新增任何医学结论**。用 `**文字**` 标记需要高亮的关键词。依据内容重点设计 `segments`，每段的 `start`/`end` 对齐相应口播句。

### 4. 填写配置

复制 `assets/config.example.json`，改 `source` / `reference` / `output` / `workdir`，替换 `subtitles`、`segments`、`person`、`disclaimer`、`ending`。完整字段含义见 `references/workflow.md`。

### 4b. 输入人物信息（三种方式）

| 方式 | 用法 |
|---|---|
| 配置文件 | 直接编辑 `person` 的 `name` / `title` / `department` / `rank` |
| 命令行覆盖 | `python scripts/package_video.py --config c.json --person-name "张三" --person-title "某某医院" --person-department "心内科" --person-rank "主任医师"` |
| 交互输入 | 追加 `--ask-person`，逐项提示，回车保留当前值（需真实终端，非交互环境会跳过并告警） |

显示区间用 `--person-show '2,12 36,42'`，支持多个区间；缺省 `[[2,12]]`。改完先用 `--preview-card preview.png` 出一张静态名片图确认竖排文字不溢出，再跑完整合成。竖排文字会按长度自动缩字号，长机构名不会撑破名片。

### 4c. 切片剪辑（可选）

用于长口播切精华、剔除停顿/废话、批量产出多条切片。**配置里所有时间码仍按原片时间轴填写**，引擎切完后自动把字幕、动画段、片头标题、人物名片、背景取帧时间与音频淡出重映射到新时间轴，无需手工改表。

```json
"clip": {
  "mode": "keep",
  "ranges": [[0, 16.1], [18.0, 26.5], [29.4, 36.1]],
  "pad": 0.08,
  "batch": false
}
```

三种模式：`keep` 保留所列区间 / `cut` 剔除所列区间（保留其补集）/ `silence` 用 ffmpeg `silencedetect` 自动去静音（可不写 `ranges`，用 `silence: {noise, min_duration, keep}` 调阈值）。`pad` 是切点保护留白，`min_gap` 合并过近的相邻段。

```bash
# 一步到位：切片 + 重映射 + 包装
python scripts/package_video.py --config <config.json>
# 只切片，先看中间产物 clipped.mp4 / edit_map.json / clipped_config.json
python scripts/package_video.py --config <config.json> --clip-only
# 不改配置，命令行临时指定保留区间
python scripts/package_video.py --config c.json --clip-ranges "0,12 18,33 41,64"
# 每段单独导出 clip_XX.mp4 + 独立可跑配置
python scripts/package_video.py --config c.json --clip-batch
# 独立使用：只切片不包装
python scripts/clip_video.py --source long.mp4 --ranges "0,12 18,33" --output short.mp4
```

`--clip-mode silence` 自动去静音；`--no-clip` 忽略配置里的 `clip` 段，直接用原片包装。

边界要说清：切点是硬切、不做转场；起点落在被剪区的字幕会被丢弃，跨切点的动画/显示区间会被裁剪，终端会打印丢弃数量；`edit_map.json` 记录原时间→新时间映射供人工复核。`batch: true` 时在 `<workdir>/clips/` 产出每段 `clip_XX.mp4` 与已重映射的 `clip_XX.json`，主成片仍照常输出拼接版。**切片内容必须人工核对切点没有截断半句话、条件或否定词**。

### 4d. 内容驱动分镜（可选，推荐）

默认所有动画段共用「模糊背景 + 圆形小真人」模板。配置加 `shots` 段后，引擎按语义把时间轴切成多个镜头，每段分配不同画面分格（全屏 / 推近 / 左右分屏 / 上下分屏 / 2×2 宫格 / 全屏大字卡 / 巨幅关键词 / 讲解画中画），并做交叉淡化或滑入转场；字幕位置随版式自动调整。

```json
"shots": {"mode": "auto", "transition": "fade", "min_duration": 1.15}
```

```bash
python scripts/package_video.py --config c.json --auto-shots   # 自动规划并出片
python scripts/package_video.py --config c.json --plan-only    # 只出 shot_plan.json
python scripts/package_video.py --config c.json --shot-plan shot_plan.json  # 人工改完回灌
python scripts/package_video.py --config c.json --no-shots     # 回退固定模板路径
```

`shot_plan.json` 每段记录 `layout` / `headline` / `items` / `reason` / `subtitle`，可逐项人工改写。知识段按 `kind` 映射版式且不会被字幕边界切开；含数字或比较词走分屏，短情绪句走大字卡，长讲解走全屏少干扰，动作占比高的段保留完整画面。完整规则见 `references/workflow.md` 第 1e 节。

### 5. 选择动画后端

- **内置 Pillow（默认，零依赖）**：加工程序化示意动画，已用 easeOutCubic 缓动与逐条淡入，适合快速出片。
- **Remotion（更自然，推荐）**：spring 弹性、贝塞尔缓动、SVG 渐变与阴影，动画明显更柔和。首次执行前在 `remotion/` 下运行 `npm install`。
  ```bash
  python scripts/render_remotion.py --config <config.json> --out <anim_frames>
  python scripts/package_video.py --config <config.json> --animation-frames <anim_frames>
  ```
- **外部逐帧（AE / Blender / CSS 录屏 / 任意工具）**：把透明 RGBA PNG 序列放进一个目录，文件名排序后按帧号对应，用同样的 `--animation-frames` 传入。

配置里写 `animation_frames` 字段可在不传命令行参数时自动启用外部后端。

### 6. 合成

```bash
python scripts/package_video.py --config <config.json>
```

引擎自动完成：若配置含 `clip` 段或命令行给了 `--clip-ranges`，先切片并把所有时间码重映射到新时间轴；再生成 ASS/SRT 字幕、片头标题、人物条、免责声明、动画帧、片尾卡、小真人画中画、原声保留与淡出，最后分段拼接输出成片。同时产出 `contact_sheet.png` 与 `review_checklist.json`（切片时额外产出 `edit_map.json`、`clipped_config.json`）。

### 7. 质检

查看 `contact_sheet.png`，逐格确认：中文无乱码、字幕不压免责小字、动画段字幕不压小真人画中画、片尾卡完整、片头/人物条不遮挡人脸。发现问题优先改 `style.shifted_pos` / `segments` 时间，再重跑 `--reuse-frames` 或完整重跑。

### 8. 交付

输出成片 + `subtitles.srt` + `subtitles.ass` + `review_checklist.json`。明确告知成片状态为 `DRAFT_PENDING_HUMAN_REVIEW`，由人完成审签后才可发布。

## Agent 分工（可并行）

复杂项目用 Agent 工具分派独立子任务，各自自包含、互不改写文件：

1. **参考片分析**：给 `analyze_reference.py` 的输出目录，要求列出标题/字幕/人物条/动画段/片尾的精确规格与时间区间。
2. **脚本与分镜**：给转写文本，要求产出 `subtitles` 数组与 `segments` 草案，标注每段对应的原话，禁止新增医学结论。
3. **合规审校**：独立于写作，读 `review_checklist.json` 与字幕，检查疗效承诺、绝对化用语、虚构病例、导购链接、资质与标识。

主流程负责写 `config.json` 并执行引擎；不把医学判断或发布动作交给子 agent。

## 合规与审签

引擎按 `profile` 输出对应审签清单（`review_checklist.json`），成片一律标记 `DRAFT_PENDING_HUMAN_REVIEW`、不自动发布；AI 生成合成标识由后期/发布环节处理。

### medical（医学科普）

依据 2025 年 8 月四部门《关于规范"自媒体"医疗科普行为的通知》：专业医疗科普需账号资质认证；引用转载、AI 生成合成内容、真实健康经历均须标注来源或生成合成标识；不得以健康知识形式变相发布医疗、药品、医疗器械、保健食品广告，同页面不得出现购物链接；严禁夸大疗效、虚构病例、假冒医生身份、AI 编造同质化涉医文案。

因此引擎强制：底部常驻免责声明、片尾免责、审签清单、`auto_publish: false`。AI 生成合成标识按用户流程交由后期/发布环节添加，工具不烧录，并在 `review_checklist.json` 中登记为待办项。不得为提升观感删除免责声明。

### clip（切片剪辑）

切片的特有风险是**断章取义**：硬切可能截断半句话、条件或否定词，跨段拼接可能让两句原本无关的话连在一起。审签清单因此要求逐句核对 `edit_map.json` 的切点、确认节选与上下文一致、标注原片来源与「节选/剪辑」字样，并确认人物肖像与原片版权已获再发布授权。医学科普类素材做切片时，除 `clip` 清单外仍须满足 `medical` 的资质与免责要求——此时建议显式写 `disclaimer` 补齐医学免责行。

## 已知边界

- 叠层按 720×1280（9:16）设计画布绘制。源视频规格不符时（如 540×960@19fps 手机竖屏）会**自动等比缩放/补黑边，并统一为 720×1280@30fps、48kHz 立体声**；切片阶段顺手完成，无切片时由包装入口单独转码一次。非 9:16 素材会加黑边。
- 人物名片竖排规格取自参考成片 `2.mp4`；换风格改 `package_video.py` 的 `CARD` 常量与 `draw_person()`。
- 精确口型同步、数字人替身不在本工具范围内；本工具保留真人出镜。
- 切片是**帧精确硬切**，不做转场与补帧；需柔和过渡请在外部剪辑软件里加工 `clipped.mp4`。跨切点的字幕/动画会被裁剪或丢弃，不做智能补写。**分镜模式**提供镜头间的淡化/滑入转场，但不改变切片点本身。
- 分镜模式由 `shot_engine.py` 逐帧重排画面，**不叠加竖排人物名片**，也不走 Remotion / 外部帧后端（版式由分镜决定）；需要人物名片或 Remotion 动效时用 `--no-shots` 回退旧路径。
- 依赖本机 `ffmpeg` / `ffprobe`、Python 3.9+ 与 Pillow；Remotion 后端另需 Node 18+ 与 Chrome/Edge。
