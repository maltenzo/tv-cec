#!/bin/bash
# Pull-based: la Pi consulta el remoto, no hace falta abrir nada ni guardar secretos en CI.
set -e
cd "$(dirname "$0")"
git fetch -q
[ "$(git rev-parse HEAD)" = "$(git rev-parse '@{u}')" ] && exit 0
git reset -q --hard '@{u}'
./install.sh
