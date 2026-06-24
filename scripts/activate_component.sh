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

# 3. Check for router prefix conflicts with already-activated components
_check_prefix_conflict() {
  local new_api="app/components/${NAME}/api.py"
  [ ! -f "$new_api" ] && return 0

  local new_prefix
  new_prefix=$(sed -n 's/.*prefix[[:space:]]*=[[:space:]]*"\([^"]*\)".*/\1/p' "$new_api" | head -1)

  [ -z "$new_prefix" ] && return 0

  for installed in app/components/*/; do
    local comp
    comp=$(basename "$installed")
    [ "$comp" = "$NAME" ] && continue
    [ ! -f "${installed}api.py" ] && continue

    local installed_prefix
    installed_prefix=$(sed -n 's/.*prefix[[:space:]]*=[[:space:]]*"\([^"]*\)".*/\1/p' "${installed}api.py" | head -1)

    [ -z "$installed_prefix" ] && continue

    if [ "$new_prefix" = "$installed_prefix" ] \
        || [[ "$new_prefix" = "${installed_prefix}/"* ]] \
        || [[ "$installed_prefix" = "${new_prefix}/"* ]]; then
      echo "  ✗ Router prefix conflict: '${NAME}:${new_prefix}' collides with '${comp}:${installed_prefix}'" >&2
      exit 1
    fi
  done
}

_check_prefix_conflict

# 4. Merge compose fragment
if [ -f "${SRC}/compose.fragment.yml" ]; then
  echo "  ⚠  Merge compose.fragment.yml into docker-compose.override.yml manually"
  cat "${SRC}/compose.fragment.yml"
fi

# 5. Print env additions
if [ -f "${SRC}/env.additions" ]; then
  echo "  ⚠  Add these env vars to .env:"
  cat "${SRC}/env.additions"
fi

# 6. Add to INSTALLED_COMPONENTS
python3 - "$NAME" << 'PYEOF'
import sys, re
name = sys.argv[1]
env_path = ".env"
added = False
with open(env_path) as f:
    content = f.read()
match = re.search(r"^INSTALLED_COMPONENTS=(.*)", content, re.MULTILINE)
if match:
    raw = match.group(1).strip().strip('"').strip("'")
    items = [x.strip() for x in raw.split(",") if x.strip()]
    if name not in items:
        items.append(name)
        added = True
        print("  \u2713 Added " + name + " to INSTALLED_COMPONENTS in .env")
    new_line = "INSTALLED_COMPONENTS=" + ",".join(items)
    content = content[:match.start()] + new_line + content[match.end():]
else:
    content += "INSTALLED_COMPONENTS=" + name + "\n"
    added = True
    print("  \u2713 Created INSTALLED_COMPONENTS in .env")
with open(env_path, "w") as f:
    f.write(content)
if not added:
    print("  \u2192 " + name + " already in INSTALLED_COMPONENTS")
PYEOF

echo ""
echo "Done. Next steps:"
echo "  1. Review and merge any migration files"
echo "  2. Run: alembic upgrade head"
echo "  3. Rebuild: docker compose build"
echo "  4. Restart: docker compose up -d"
