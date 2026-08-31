#!/usr/bin/env bash
set -euo pipefail

echo "==> Installing uv"
curl -LsSf https://astral.sh/uv/install.sh | sh
export PATH="$HOME/.local/bin:$PATH"

echo "==> Setting up serving"
cd /workspaces/pixeltable-starter-kit/serving
uv sync

echo "==> Copying .env.example to .env (if needed)"
cd /workspaces/pixeltable-starter-kit
if [ ! -f .env ]; then
  cp .env.example .env
fi

echo "==> Dev container ready"
echo "    cd serving && uv run pxt schema update app.py pipeline"
echo "    uv run pxt service run app.py pipeline --port 8000"
