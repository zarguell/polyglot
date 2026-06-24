#!/usr/bin/env bash
set -euo pipefail

if [ $# -lt 1 ]; then
  echo "Usage: $0 <component-name>"
  echo "Available:"
  ls boilerplate/templates/
  exit 1
fi

NAME="$1"
SRC="boilerplate/templates/${NAME}"

if [ ! -d "$SRC" ]; then
  echo "Error: component '$NAME' not found in boilerplate/templates/"
  exit 1
fi

echo "Activating component: $NAME"

# 1. Copy source files
if [ -d "${SRC}/app" ]; then
  cp -r "${SRC}/app/" "app/components/${NAME}/"
  echo "  ✓ Copied app/ → app/components/${NAME}/"
fi

# 2. Copy migration files
if [ -d "${SRC}/alembic_versions" ]; then
  cp "${SRC}"/alembic_versions/*.py alembic/versions/ 2>/dev/null || true
  echo "  ✓ Copied migrations"
fi

# 3. Merge compose fragment
if [ -f "${SRC}/compose.fragment.yml" ]; then
  echo "  ⚠  Merge compose.fragment.yml into docker-compose.override.yml manually"
  cat "${SRC}/compose.fragment.yml"
fi

# 4. Print env additions
if [ -f "${SRC}/env.additions" ]; then
  echo "  ⚠  Add these env vars to .env:"
  cat "${SRC}/env.additions"
fi

# 5. Add to INSTALLED_COMPONENTS
if grep -q "^INSTALLED_COMPONENTS=" .env 2>/dev/null; then
  if ! grep -q "${NAME}" .env; then
    sed -i '' "s/^INSTALLED_COMPONENTS=.*/&,${NAME}/" .env
    echo "  ✓ Added ${NAME} to INSTALLED_COMPONENTS in .env"
  fi
else
  echo "INSTALLED_COMPONENTS=${NAME}" >> .env
  echo "  ✓ Created INSTALLED_COMPONENTS in .env"
fi

echo ""
echo "Done. Next steps:"
echo "  1. Review and merge any migration files"
echo "  2. Run: alembic upgrade head"
echo "  3. Rebuild: docker compose build"
echo "  4. Restart: docker compose up -d"
