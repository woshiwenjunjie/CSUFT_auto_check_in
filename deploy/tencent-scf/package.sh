#!/bin/bash
# ═══════════════════════════════════════════════════════════
# Auto Check-In — Tencent SCF 打包脚本
# 用法: bash package.sh
# 输出: deploy/tencent-scf/scf_package.zip（上传到 SCF 控制台）
# ═══════════════════════════════════════════════════════════
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/../.." && pwd)"
BUILD_DIR=$(mktemp -d)
OUTPUT_ZIP="$SCRIPT_DIR/scf_package.zip"

echo "=== Auto Check-In SCF Package ==="
echo "Project root: $PROJECT_DIR"
echo "Build dir:    $BUILD_DIR"
echo "Output:       $OUTPUT_ZIP"

# ── 1. 复制 SCF 入口文件 ───────────────────────────────
echo "[1/3] 复制入口文件..."
cp "$SCRIPT_DIR/handler.py"     "$BUILD_DIR/"
cp "$SCRIPT_DIR/checkin.py"     "$BUILD_DIR/"
cp "$SCRIPT_DIR/requirements.txt" "$BUILD_DIR/"

# ── 2. 复制核心库文件（保持 src/ 包结构）───────────────
echo "[2/3] 复制核心库..."
mkdir -p "$BUILD_DIR/src"
mkdir -p "$BUILD_DIR/src/core"
mkdir -p "$BUILD_DIR/src/utils"

cp "$PROJECT_DIR/src/__init__.py"        "$BUILD_DIR/src/"
cp "$PROJECT_DIR/src/core/__init__.py"   "$BUILD_DIR/src/core/"
cp "$PROJECT_DIR/src/core/client.py"     "$BUILD_DIR/src/core/"
cp "$PROJECT_DIR/src/utils/__init__.py"  "$BUILD_DIR/src/utils/"
cp "$PROJECT_DIR/src/core/token_client.py"  "$BUILD_DIR/src/core/"
cp "$PROJECT_DIR/src/core/sign_builder.py"  "$BUILD_DIR/src/core/"
cp "$PROJECT_DIR/src/utils/crypto.py"       "$BUILD_DIR/src/utils/"
cp "$PROJECT_DIR/src/utils/sign.py"         "$BUILD_DIR/src/utils/"
cp "$PROJECT_DIR/src/utils/geo.py"          "$BUILD_DIR/src/utils/"
cp "$PROJECT_DIR/src/utils/notification.py" "$BUILD_DIR/src/utils/"

# ── 3. 在 Linux 下安装 pip 依赖 ──────────────────────
echo "[3/3] 安装 pip 依赖..."
echo "  pip 安装中..."
pip install -r "$BUILD_DIR/requirements.txt" -t "$BUILD_DIR"

# ── 压缩 ────────────────────────────────────────────
echo "打包中..."
cd "$BUILD_DIR"
rm -f "$OUTPUT_ZIP"
zip -r "$OUTPUT_ZIP" . --quiet
cd "$PROJECT_DIR"

# ── 清理 ────────────────────────────────────────────
rm -rf "$BUILD_DIR"

echo "=== 完成 ==="
echo "包大小: $(du -h "$OUTPUT_ZIP" | cut -f1)"
echo "上传到: 腾讯云 SCF 控制台 → 函数代码 → 在线安装依赖 → 提交"
echo ""
echo "如需自动部署，运行: python deploy/tencent-scf/deploy.py"