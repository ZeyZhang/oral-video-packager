#!/usr/bin/env bash
# 一键安装 oral-video-packager 到 WorkBuddy 的 skills 目录
# 用法: bash install.sh [--project] [--dir PATH] [--force]
set -euo pipefail

REPO="https://github.com/ZeyZhang/oral-video-packager.git"
NAME="oral-video-packager"
SKILLS_ROOT="${HOME}/.workbuddy/skills"
FORCE=0

usage() {
  cat <<'EOF'
用法: bash install.sh [选项]
  (无参数)      安装到用户级 ~/.workbuddy/skills/<name>
  --project     安装到当前项目 .workbuddy/skills/<name>
  --dir PATH    安装到指定 skills 根目录
  --force       目标已存在时覆盖（先备份为 .bak-<时间戳>）
  -h, --help    显示帮助
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --project) SKILLS_ROOT="$(pwd)/.workbuddy/skills"; shift ;;
    --dir) SKILLS_ROOT="$2"; shift 2 ;;
    --force) FORCE=1; shift ;;
    -h|--help) usage; exit 0 ;;
    *) echo "未知参数: $1"; usage; exit 1 ;;
  esac
done

echo "== 检查依赖 =="
missing=0
for cmd in git ffmpeg ffprobe python3; do
  if ! command -v "$cmd" >/dev/null 2>&1; then
    echo "  [缺失] $cmd"
    missing=1
  else
    echo "  [OK]   $cmd"
  fi
done
if command -v python3 >/dev/null 2>&1; then
  if python3 -c "import PIL" >/dev/null 2>&1; then
    echo "  [OK]   Pillow"
  else
    echo "  [缺失] Python 包 Pillow -> pip install Pillow"
    missing=1
  fi
fi
if [[ $missing -eq 1 ]]; then
  echo "请先补齐上述依赖。Remotion 后端另需 Node 18+ 并在 remotion/ 下执行 npm install。"
  exit 1
fi

TARGET="${SKILLS_ROOT}/${NAME}"
if [[ -d "$TARGET" && -n "$(ls -A "$TARGET" 2>/dev/null)" ]]; then
  if [[ $FORCE -eq 0 ]]; then
    echo "目标已存在: $TARGET"
    echo "加 --force 覆盖（会先备份为 ${TARGET}.bak-<时间戳>）"
    exit 1
  fi
  mv "$TARGET" "${TARGET}.bak-$(date +%Y%m%d%H%M%S)"
  echo "已备份原有目录"
fi

TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT
echo "== 克隆公开仓库 =="
git clone --depth 1 "$REPO" "$TMP/src"

echo "== 安装到 $TARGET =="
mkdir -p "$TARGET"
cp -R "$TMP/src/." "$TARGET/"
rm -rf "$TARGET/.git" "$TARGET/remotion/node_modules" "$TARGET/remotion/out" \
       "$TARGET/__pycache__" "$TARGET/scripts/__pycache__"
find "$TARGET" -name '*.pyc' -delete 2>/dev/null || true

if [[ ! -f "$TARGET/SKILL.md" ]]; then
  echo "安装失败：未找到 SKILL.md"
  exit 1
fi

echo "安装完成: $TARGET"
echo "下一步："
echo "  1. 新开一个 WorkBuddy 对话（新技能才会被加载）"
echo "  2. cp $TARGET/assets/config.example.json myconfig.json"
echo "  3. 改掉示例里的 source / reference / output / workdir 路径和人物信息"
echo "  4. python $TARGET/scripts/package_video.py --config myconfig.json"
