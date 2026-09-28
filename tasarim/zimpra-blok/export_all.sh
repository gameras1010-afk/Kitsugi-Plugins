#!/usr/bin/env sh
set -eu
cd "$(dirname "$0")"
command -v openscad >/dev/null 2>&1 || {
  echo "OpenSCAD bulunamadı. Önce OpenSCAD kurun: https://openscad.org/downloads.html" >&2
  exit 1
}
for size in S M L; do
  for part in base swivel grip; do
    openscad -o "${part}_${size}.stl" -D "size=\"${size}\"" -D "part=\"${part}\"" zimpra_blok.scad
  done
done
echo "Dokuz STL dosyası oluşturuldu. Önce slicer'da ölçüleri ve montajı kontrol edin."
