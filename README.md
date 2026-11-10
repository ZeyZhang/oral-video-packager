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
| 合规 | 医学/健康类内容输出审签清单，标记 `DRAFT_PENDING_HUMAN_REVIEW`，不自动发布 |

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
```

输出：成片、`subtitles.srt` / `subtitles.ass`、`contact_sheet.png`、`review_checklist.json`。

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
scripts/render_remotion.py    Remotion 动画层渲染
scripts/analyze_reference.py  参考成片拆解
assets/config.example.json    完整配置示例
references/workflow.md        配置字段、依赖、SkillHub 上架与故障排查
remotion/                     React + spring 动画模板
manifest.yaml / icon.png      SkillHub GitHub 导入元数据与图标
```

## 合规

医学/健康类内容默认带底部免责声明与片尾免责，成片状态为待人工审签，工具不自动发布。AI 生成合成标识由后期/发布环节按平台要求处理。

SkillHub 上架流程见 `references/workflow.md` 第 0 节，网页发布入口为 `https://skillhub.cn/dashboard/publish`。

## 许可证

见 [LICENSE](LICENSE)。
