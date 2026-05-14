#!/usr/bin/env bash
set -euo pipefail

echo "==> Installing uv"
curl -LsSf https://astral.sh/uv/install.sh | sh
export PATH="$HOME/.local/bin:$PATH"

echo "==> Setting up backend"
cd /workspaces/pixeltable-starter-kit/backend
uv sync

echo "==> Setting up frontend"
cd /workspaces/pixeltable-starter-kit/frontend
npm install

echo "==> Copying .env.example → .env (if needed)"
cd /workspaces/pixeltable-starter-kit
if [ ! -f .env ]; then
  cp .env.example .env
  echo "    Created .env — add your ANTHROPIC_API_KEY and OPENAI_API_KEY"
fi

echo "==> Dev container ready!"
echo "    Backend:  cd backend && uv run python setup_pixeltable.py && uv run python main.py"
echo "    Frontend: cd frontend && npm run dev"
