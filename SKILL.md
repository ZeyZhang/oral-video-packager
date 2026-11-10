---
name: oral-video-packager
description: >-
  把真人出镜的竖屏口播素材包装成带逐句字幕、人物介绍条、知识动画、
  免责声明与片尾卡的成片，可复用参考成片的视觉规格，支持 Pillow /
  Remotion / 外部逐帧三种动画后端，并内置医学科普合规与人工审签清单。
  本 skill 应在用户提供「素材视频 + 参考成片」或要求为口播视频添加
  字幕、人物介绍、知识动画、片尾包装时使用。
agent_created: true
slug: oral-video-packager
version: 1.0.0
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
license: MIT
visibility: public
---

# 口播视频包装工具

## 用途

把一段真人出镜口播原片，按可选的参考成片风格，加工成可发布的竖屏成片。全流程本地执行：ASR 转写 → 分镜与字幕 → 动画层渲染 → 音画合成 → 质检 → 审签清单。医学/健康类内容默认带底部免责声明与片尾免责；**AI 生成合成标识不在画面烧录，由后期/发布环节处理**。工具**只产出草稿，不自动发布**。

## 何时使用

- 提供「素材视频 + 参考成片」，要求把素材做成参考片那种效果
- 要求给口播视频加字幕、人物介绍条、知识动画、片头标题、片尾卡
- 需要把一次性剪辑流程固化，供后续批量/日更复用
- 医学科普、知识讲解类短视频的包装与发布前自检

## bundled 资源

| 路径 | 作用 |
|---|---|
| `scripts/analyze_reference.py` | 拆解参考成片：元信息、2 秒网格拼板、关键帧、待填规格骨架 |
| `scripts/package_video.py` | 主引擎：读配置生成字幕/叠层/成片/审签清单/质检拼板 |
| `scripts/render_remotion.py` | 用 Remotion 渲染自然动效的透明 PNG 帧序列 |
| `remotion/` | Remotion 模板工程（React + spring/interpolate + SVG 动画） |
| `assets/config.example.json` | 完整可跑的配置示例（含真实字幕与四段知识动画） |
| `references/workflow.md` | 配置字段全表、ffmpeg 坑、合规细则、故障排查、扩展动画类型 |

## 工作流

### 1. 收集输入

向用户索取：素材视频绝对路径、参考成片路径（可选），以及名片四要素 `name`（姓名）/ `title`（机构）/ `department`（科室）/ `rank`（职称）。**人物信息必须由用户提供**，不得复用 `config.example.json` 里的示例值，也不得从工牌或参考片自行推断后当作用户输入。用户未提供时先询问；用户明确说留空才留空。空字段不绘制，不编造职称。

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

引擎自动完成：生成 ASS/SRT 字幕、片头标题、人物条、免责声明、动画帧、片尾卡、小真人画中画、原声保留与淡出，最后分段拼接输出成片。同时产出 `contact_sheet.png` 与 `review_checklist.json`。

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

## 合规硬约束（医学/健康内容）

依据 2025 年 8 月四部门《关于规范"自媒体"医疗科普行为的通知》：专业医疗科普需账号资质认证；引用转载、AI 生成合成内容、真实健康经历均须标注来源或生成合成标识；不得以健康知识形式变相发布医疗、药品、医疗器械、保健食品广告，同页面不得出现购物链接；严禁夸大疗效、虚构病例、假冒医生身份、AI 编造同质化涉医文案。

因此引擎强制：底部常驻免责声明、片尾免责、审签清单、`auto_publish: false`。AI 生成合成标识按用户流程交由后期/发布环节添加，工具不烧录，并在 `review_checklist.json` 中登记为待办项。不得为提升观感删除免责声明。

## 已知边界

- 叠层按 720×1280（9:16）设计画布绘制，非 9:16 素材会告警且可能变形。
- 人物名片竖排规格取自参考成片 `2.mp4`；换风格改 `package_video.py` 的 `CARD` 常量与 `draw_person()`。
- 精确口型同步、数字人替身不在本工具范围内；本工具保留真人出镜。
- 依赖本机 `ffmpeg` / `ffprobe`、Python 3.9+ 与 Pillow；Remotion 后端另需 Node 18+ 与 Chrome/Edge。
