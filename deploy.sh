#!/usr/bin/env bash
# Публикация палитры на colors.galangal.ru
# Копирует статику из этого репозитория в каталог, который отдаёт Caddy.
set -euo pipefail

SRC="$(cd "$(dirname "$0")" && pwd)"
DEST="/srv/colors"

if [ ! -d "$DEST" ]; then
  echo "Каталог $DEST не создан. Один раз выполни:"
  echo "  sudo install -d -o $USER -g $USER $DEST"
  exit 1
fi

# Из authors/ на сайт нужны только работы: дот-карты — исходники,
# их содержимое уже разобрано в palette.json и оттуда в catalog.js.
rsync -a --delete \
  --include='index.html' \
  --include='table.html' \
  --include='data.js' \
  --include='catalog.js' \
  --include='authors/' \
  --include='authors/*/' \
  --include='authors/*/example.jpg' \
  --exclude='*' \
  "$SRC"/ "$DEST"/

echo "Опубликовано в $DEST →  https://colors.galangal.ru"
ls -l "$DEST"
