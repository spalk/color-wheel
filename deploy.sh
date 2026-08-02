#!/usr/bin/env bash
# Публикация палитры на colors.galangal.ru
# Копирует статику из этого репозитория в каталог, который отдаёт Caddy.
#
#   ./deploy.sh            → https://colors.galangal.ru        (прод)
#   ./deploy.sh dev        → https://colors.galangal.ru/dev/   (превью ветки)
#
# Превью — просто подпапка того же сайта: не нужны ни DNS, ни правка Caddy,
# ни sudo. Прод при этом не трогается: --delete работает внутри подпапки,
# а деплой прода подпапки не сносит (см. --exclude ниже).
set -euo pipefail

SRC="$(cd "$(dirname "$0")" && pwd)"
ROOT="/srv/colors"
SLOT="${1:-}"

if [ ! -d "$ROOT" ]; then
  echo "Каталог $ROOT не создан. Один раз выполни:"
  echo "  sudo install -d -o $USER -g $USER $ROOT"
  exit 1
fi

if [ -n "$SLOT" ]; then
  DEST="$ROOT/$SLOT"
  URL="https://colors.galangal.ru/$SLOT/"
  mkdir -p "$DEST"
  KEEP=()
else
  DEST="$ROOT"
  URL="https://colors.galangal.ru"
  # чтобы деплой прода не сносил превью-слоты
  KEEP=(--filter='protect /*/')
fi

# Из authors/ на сайт нужны только работы: дот-карты — исходники,
# их содержимое уже разобрано в palette.json и оттуда в catalog.js.
rsync -a --delete "${KEEP[@]}" \
  --include='index.html' \
  --include='table.html' \
  --include='data.js' \
  --include='catalog.js' \
  --include='authors/' \
  --include='authors/*/' \
  --include='authors/*/example.jpg' \
  --exclude='*' \
  "$SRC"/ "$DEST"/

echo "Опубликовано в $DEST  →  $URL"
if [ -n "$SLOT" ]; then
  echo "Прод не тронут. Удалить превью:  rm -rf $DEST"
fi
