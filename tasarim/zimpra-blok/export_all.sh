#!/usr/bin/env sh
set -eu
cd "$(dirname "$0")"
command -v openscad >/dev/null 2>&1 || {
  echo "OpenSCAD bulunamadi. Once OpenSCAD kurun." >&2
  exit 1
}
for size in S M L; do
  for part in base face pad abrasive pivot handle lock; do
    openscad -o "${part}_${size}.stl" -D "size=\"${size}\"" -D "part=\"${part}\"" zimpra_blok.scad
  done
done
echo "21 STL olusturuldu. Once slicerda olculeri ve montaji kontrol edin."
