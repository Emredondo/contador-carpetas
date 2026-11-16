#!/bin/sh
set -eu
cd "$(dirname "$0")/.."
root=$(pwd)
stage=$(mktemp -d)
trap 'rm -rf "$stage"' EXIT HUP INT TERM
mkdir -p "$stage/DEBIAN" "$stage/usr/bin" "$stage/usr/lib/contador-carpetas" "$stage/usr/share/applications" "$stage/usr/share/icons/hicolor/scalable/apps" "$stage/usr/share/doc/contador-carpetas"
cp contador_carpetas/*.py "$stage/usr/lib/contador-carpetas/"
cat > "$stage/usr/bin/contador-carpetas" <<'LAUNCHER'
#!/usr/bin/python3
import sys
sys.path.insert(0, '/usr/lib/contador-carpetas')
from contador_carpetas.gui import main
main()
LAUNCHER
# Install the importable package under the private application directory.
mkdir "$stage/usr/lib/contador-carpetas/contador_carpetas"
mv "$stage/usr/lib/contador-carpetas/"*.py "$stage/usr/lib/contador-carpetas/contador_carpetas/"
chmod 755 "$stage/usr/bin/contador-carpetas"
cp data/contador-carpetas.desktop "$stage/usr/share/applications/"
cp data/contador-carpetas.svg "$stage/usr/share/icons/hicolor/scalable/apps/"
cp README.md "$stage/usr/share/doc/contador-carpetas/"
mkdir -p "$stage/usr/share/man/man1"
gzip -n -9 < data/contador-carpetas.1 > "$stage/usr/share/man/man1/contador-carpetas.1.gz"
cat > "$stage/usr/share/doc/contador-carpetas/copyright" <<'COPYRIGHT'
Format: https://www.debian.org/doc/packaging-manuals/copyright-format/1.0/
Upstream-Name: contador-carpetas
Source: Source archive distributed alongside this package.

Files: *
Copyright: 2026 Contador de Carpetas contributors
License: GPL-3+
 This program is free software: you can redistribute it and/or modify
 it under the terms of the GNU General Public License as published by
 the Free Software Foundation, either version 3 of the License, or
 (at your option) any later version.
 .
 On Debian systems, the complete text of the GNU General Public License
 version 3 can be found in /usr/share/common-licenses/GPL-3.
COPYRIGHT
printf 'contador-carpetas (1.0.0) unstable; urgency=medium\n\n  * Initial release.\n\n -- Contador de Carpetas contributors <contador-carpetas@example.org>  Mon, 16 Nov 2026 12:00:00 -0300\n' | gzip -n -9 > "$stage/usr/share/doc/contador-carpetas/changelog.gz"
cat > "$stage/DEBIAN/control" <<CONTROL
Package: contador-carpetas
Version: 1.0.0
Section: utils
Priority: optional
Architecture: all
Maintainer: Contador de Carpetas contributors <contador-carpetas@example.org>
Depends: python3 (>= 3.11), python3-gi, gir1.2-gtk-3.0
Installed-Size: $(du -sk "$stage/usr" | cut -f1)
Description: Recursive folder counter and sorter for GTK 3
 Native Linux desktop application that ranks immediate subdirectories by
 recursive file count, disk usage or name, with cancellation and CSV export.
CONTROL
find "$stage" -type d -exec chmod 755 {} +
find "$stage" -type f ! -path "$stage/usr/bin/*" -exec chmod 644 {} +
mkdir -p dist
dpkg-deb --root-owner-group --build "$stage" "$root/dist/contador-carpetas_1.0.0_all.deb"
