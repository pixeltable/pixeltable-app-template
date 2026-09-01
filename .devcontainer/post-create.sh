#!/usr/bin/env bash
set -euo pipefail

echo "==> Installing uv"
curl -LsSf https://astral.sh/uv/install.sh | sh
export PATH="$HOME/.local/bin:$PATH"

echo "==> Setting up chat-agent"
cd /workspaces/pixeltable-starter-kit/chat-agent
uv sync

echo "==> Copying .env.example to .env (if needed)"
cd /workspaces/pixeltable-starter-kit
if [ ! -f .env ]; then
  cp .env.example .env
fi

echo "==> Dev container ready"
echo "    cd chat-agent && uv run pxt schema update app.py agent"
echo "    uv run pxt service run app.py agent --port 8000"
