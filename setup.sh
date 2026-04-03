#!/bin/bash
# setup.sh

set -e

echo "🚀 Setting up DeepThought environment..."

# ── 1. 確認 Python 版本 ──────────────────
PYTHON_VERSION=$(python3 --version 2>&1 | cut -d' ' -f2 | cut -d'.' -f1,2)
REQUIRED_VERSION="3.11"

echo "📌 Python version: $PYTHON_VERSION"

if python3 -c "import sys; exit(0 if sys.version_info >= (3,11) else 1)"; then
    echo "✅ Python version OK"
else
    echo "❌ Python 3.11+ required"
    exit 1
fi

# ── 2. 建立 venv ─────────────────────────
echo "📦 Creating virtual environment..."
python3 -m venv .venv

# ── 3. 啟動 venv ─────────────────────────
source .venv/bin/activate
echo "✅ Virtual environment activated"

# ── 4. 升級 pip ──────────────────────────
pip install --upgrade pip setuptools wheel

# ── 5. 安裝依賴 ──────────────────────────
echo "📥 Installing dependencies..."
pip install -r requirements.txt

# ── 6. 建立目錄結構 ──────────────────────
echo "📁 Creating directory structure..."

dirs=(
    "configs"
    "core"
    "agents"
    "data_collection/crawler"
    "data_collection/parser"
    "data_collection/chunker"
    "vectordb"
    "output/templates"
    "services"
    "api"
    "scripts"
    "tests/test_core"
    "tests/test_agents"
    "tests/test_data_collection"
    "tests/test_vectordb"
    "logs"
    "data/raw"
    "data/processed"
    "data/vectorstore"
)

for dir in "${dirs[@]}"; do
    mkdir -p "$dir"
    touch "$dir/__init__.py" 2>/dev/null || true
done

# logs 和 data 不需要 __init__.py
rm -f logs/__init__.py
rm -f data/__init__.py
rm -f data/raw/__init__.py
rm -f data/processed/__init__.py
rm -f data/vectorstore/__init__.py

echo "✅ Directory structure created"

# ── 7. 複製 .env ──────────────────────────
if [ ! -f .env ]; then
    cp .env.example .env
    echo "📝 .env created from .env.example"
    echo "⚠️  Please edit .env with your API keys"
fi

# ── 8. Tree-sitter 語言編譯 ───────────────
echo "🌳 Setting up Tree-sitter languages..."
python3 scripts/setup_treesitter.py

echo ""
echo "✅ DeepThought environment ready!"
echo ""
echo "To activate:"
echo "  source .venv/bin/activate"
echo ""
echo "Next steps:"
echo "  1. Edit .env with your API keys"
echo "  2. python scripts/setup_vectordb.py"
echo "  3. python scripts/ingest_kernel.py"
