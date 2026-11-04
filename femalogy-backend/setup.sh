#!/bin/bash
# One-time setup. Everything stays inside this folder:
#   .tools/  -> uv + portable Python 3.12 + download cache
#   .venv/   -> project packages
#   femalogy-dev.db -> local SQLite database
# To remove it all later: delete .tools, .venv and femalogy-dev.db
set -e
cd "$(dirname "$0")"
HERE="$(pwd)"
TOOLS="$HERE/.tools"
export UV_PYTHON_INSTALL_DIR="$TOOLS/python"
export UV_PYTHON_BIN_DIR="$TOOLS/bin"
export UV_CACHE_DIR="$TOOLS/cache"
export UV_PYTHON_PREFERENCE=only-managed   # never touch the Mac's own python
export DATABASE_URL="sqlite:///./femalogy-dev.db"

case "$(uname -s)-$(uname -m)" in
  Darwin-arm64)  TARGET=aarch64-apple-darwin ;;
  Darwin-x86_64) TARGET=x86_64-apple-darwin ;;
  Linux-x86_64)  TARGET=x86_64-unknown-linux-gnu ;;
  Linux-aarch64) TARGET=aarch64-unknown-linux-gnu ;;
  *) echo "Unsupported system: $(uname -s) $(uname -m)"; exit 1 ;;
esac

mkdir -p "$TOOLS"
if [ ! -x "$TOOLS/uv" ]; then
  echo "==> Downloading uv into .tools/"
  curl -fsSL "https://github.com/astral-sh/uv/releases/latest/download/uv-$TARGET.tar.gz" \
    | tar -xz -C "$TOOLS" --strip-components=1
fi
UV="$TOOLS/uv"

echo "==> Installing Python 3.12 + exact package versions from uv.lock into .venv"
"$UV" sync --frozen --extra dev --python 3.12

echo "==> Creating database tables (femalogy-dev.db)"
.venv/bin/alembic upgrade head

echo ""
echo "Done. Start the API with:  ./run.sh"
