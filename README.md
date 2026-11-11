# 口播视频包装工具

把真人出镜的竖屏口播素材，包装成带逐句字幕、竖排人物名片、知识动画、免责声明与片尾卡的成片。全流程本地运行。

正式分发渠道是**腾讯 SkillHub**；本仓库是源码上游。

## 能力

| 模块 | 说明 |
|---|---|
| 逐句字幕 | 白字黑描边，关键词金黄高亮；动画段自动右移，避让小真人画中画 |
| 人物名片 | 参考成片式竖排样式：蓝渐变姓名块＋双列机构/科室＋菱形职称，字段全部由用户输入 |
| 知识动画 | 内置 Pillow（零依赖、easeOutCubic 缓动）／ Remotion（spring 弹性、SVG 渐变）／ 外部透明 PNG 帧序列 |
| 片头片尾 | 金黄大标题、常驻免责条、黑底圆形头像片尾卡 |
| 切片剪辑 | 长视频按时间码 / 自动去静音切成精华片段，字幕与动画时间轴自动重映射；支持批量导出多条切片 |
| 规格自适应 | 非 720×1280 / 非 30fps 的手机竖屏素材自动等比缩放补边、统一帧率与音频格式，避免叠层与画中画坐标越界 |
| 内容驱动分镜 | 按语义把时间轴切成多个镜头，自动切换全屏 / 推近 / 左右分屏 / 上下分屏 / 2×2 宫格 / 大字卡 / 巨幅关键词 / 画中画八种版式，带转场，字幕位置随版式变化 |
| 合规 | 医学/健康类内容输出审签清单，标记 `DRAFT_PENDING_HUMAN_REVIEW`，不自动发布 |

## 适用场景

通过 `profile` 切换，预设决定免责声明、审签清单与推荐动画：

| 值 | 场景 | 示例配置 |
|---|---|---|
| `medical`（默认） | 医学科普、健康讲解 | `assets/config.example.json` |
| `product` | 产品介绍、发布、测评 | `assets/config.product.example.json` |
| `ecommerce` | 电商数据、类目与竞品分析 | `assets/config.ecommerce.example.json` |
| `clip` | 长视频切片、精华剪辑、去静音 | `assets/config.clip.example.json` |
| `general` | 泛知识、观点口播 | — |

配置加 `shots: {"mode": "auto"}` 可启用内容驱动分镜（见 `references/workflow.md` 第 1e 节），`--plan-only` 只出 `shot_plan.json` 供人工调整，`--shot-plan` 回灌，`--no-shots` 回退固定模板。`--list-profiles` 查看全部；配置里显式写 `disclaimer` 可覆盖预设。除原有医学动画外，新增 `features` / `compare` / `stats` / `funnel` / `steps` / `matrix` 六种通用动画，Pillow 与 Remotion 两端都支持。

切片剪辑由 `scripts/clip_video.py` 提供，是包装前的可选预处理阶段，详见 `references/workflow.md` 第 1d 节。

## 安装

正式渠道是腾讯 SkillHub：在 WorkBuddy 左侧「专家·技能·连接器」→ 技能 → SkillHub 分类搜索 `oral-video-packager` 一键安装；或在对话里说「找一个能把口播视频包装成带字幕、人物名片和知识动画成片的技能」。安装后新开一个对话生效。

本仓库是公开仓库，HTTPS 克隆无需任何凭证。从源码安装有三种方式：

1. **把链接交给 Agent**（最省事）：对 WorkBuddy 说「帮我安装这个仓库里的 skill：https://github.com/ZeyZhang/oral-video-packager」，它会自行 clone、定位 `SKILL.md` 并放到正确的 skills 目录。
2. **一行命令**：
   ```bash
   git clone https://github.com/ZeyZhang/oral-video-packager.git ~/.workbuddy/skills/oral-video-packager
   ```
   Windows 对应 `C:\Users\<用户名>\.workbuddy\skills\oral-video-packager`。
3. **Release 的 zip**：下载后走 WorkBuddy「添加技能 → 上传技能」。

`SKILL.md` 必须位于 `skills/<技能名>/SKILL.md` 这一层，不要多套一层目录；本仓库根目录就是 `SKILL.md`，直接 clone 到目标路径即可。

## 一键安装脚本

脚本会检查依赖、克隆公开仓库，并把文件放到正确的 skills 目录（默认用户级）：

```bash
# macOS / Linux / Git Bash
bash install.sh                # 用户级 ~/.workbuddy/skills/
bash install.sh --project      # 当前项目 .workbuddy/skills/
bash install.sh --dir /path    # 指定 skills 根目录
bash install.sh --force        # 目标已存在时覆盖（先备份）
```

```powershell
# Windows PowerShell
.\install.ps1
.\install.ps1 -Project
.\install.ps1 -Force
```

脚本检查 git / ffmpeg / ffprobe / Python / Pillow，缺失会明确列出；Remotion 后端另需 Node 18+ 并在 `remotion/` 下执行 `npm install`。装完新开一个 WorkBuddy 对话生效。

## 依赖

| 依赖 | 用途 | 说明 |
|---|---|---|
| ffmpeg + ffprobe | 抽帧、合成、拼接 | 需加入 PATH |
| Python 3.9+ | 主引擎 | — |
| Pillow | 逐帧绘制 | `pip install Pillow` |
| 中文字体 | 字幕与竖排名片 | Windows 微软雅黑 / macOS PingFang / Linux Noto CJK |
| Node 18+、Chrome/Edge | 仅 Remotion 后端 | 只用内置 Pillow 后端时不需要，也不联网 |

首次使用 Remotion 后端需执行 `cd remotion && npm install`。

## 快速开始

```bash
cp assets/config.example.json myconfig.json
# 示例里的 source / reference / output / workdir 和 ending.avatar.video
# 都是作者本机的 E:/workspace/... 路径，必须全部换成你自己的绝对路径；
# person 的姓名、机构、科室、职称由你提供
python scripts/package_video.py --config myconfig.json --preview-card card.png
python scripts/package_video.py --config myconfig.json

# 切片剪辑：配置里写 clip 段，或用命令行直接给保留区间
python scripts/package_video.py --config myconfig.json --clip-only
python scripts/package_video.py --config myconfig.json --clip-ranges "0,12 18,33 41,64"
```

输出：成片、`subtitles.srt` / `subtitles.ass`、`contact_sheet.png`、`review_checklist.json`；切片时另有 `clipped.mp4`、`edit_map.json`、`clipped_config.json`。

人物信息可由命令行传入，无需改配置文件：

```bash
python scripts/package_video.py --config myconfig.json \
  --person-name "张三" --person-title "某某大学附属第一医院" \
  --person-department "心内科" --person-rank "主任医师"
```

使用 Remotion 动画后端：

```bash
cd remotion && npm install && cd ..
python scripts/render_remotion.py --config myconfig.json --out anim_frames
python scripts/package_video.py --config myconfig.json --animation-frames anim_frames
```

## 目录结构

```
SKILL.md                      技能入口与工作流
scripts/package_video.py      配置驱动主引擎
scripts/clip_video.py         切片剪辑与时间轴重映射
scripts/make_dist.py          生成两个发布 zip 并校验版本一致性
scripts/shot_engine.py        内容驱动分镜规划与八种版式逐帧渲染
scripts/render_remotion.py    Remotion 动画层渲染
scripts/analyze_reference.py  参考成片拆解
assets/config*.example.json   医疗 / 产品 / 电商 / 切片四套配置示例
references/workflow.md        配置字段、切片剪辑、依赖、上架与故障排查
.github/workflows/release.yml push v* tag 自动建 Release
remotion/                     React + spring 动画模板
manifest.yaml / icon.png      SkillHub GitHub 导入元数据与图标
```

## 合规

医学/健康类内容默认带底部免责声明与片尾免责，成片状态为待人工审签，工具不自动发布。AI 生成合成标识由后期/发布环节按平台要求处理。`clip` 预设额外要求人工核对切点未截断语义、标注原片来源与「节选/剪辑」字样，并确认再发布授权。

SkillHub 上架流程见 `references/workflow.md` 第 0 节，网页发布入口为 `https://skillhub.cn/dashboard/publish`。

## 版本与发布

当前版本 **1.2.0**（1.1.0 加切片剪辑、1.1.1 加规格自适应、1.2.0 加内容驱动分镜）。`SKILL.md` 的 `version` 与 `manifest.yaml` 的 `version` 必须一致，`make_dist.py` 会在打包时校验，不一致直接中止。

```bash
python scripts/make_dist.py --src . --out dist   # 两个发布包 + 版本化 zip + SHA256SUMS
git tag -a v1.2.0 -m "v1.2.0"
git push origin main && git push origin v1.2.0  # push tag 自动建 Release 并挂 zip
```

自动发版由 `.github/workflows/release.yml` 完成；首次使用需在仓库 Settings → Actions → General 开启 **Read and write permissions**。SkillHub 从 GitHub 导入时确认页填 `1.2.0`（历史版本已提交过必须递增），历史 Release 资产不会被覆盖。

## 许可证

见 [LICENSE](LICENSE)。
