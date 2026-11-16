#!/usr/bin/python3
"""Validate installation/removal in a disposable root using host dependency status."""
import os
from pathlib import Path
import shutil
import subprocess
import tempfile

os.environ['PYTHONDONTWRITEBYTECODE'] = '1'
os.environ['PATH'] = os.environ.get('PATH', '') + ':/usr/sbin:/sbin'
package = Path(__file__).resolve().parent.parent / 'dist/contador-carpetas_1.0.0_all.deb'
with tempfile.TemporaryDirectory(prefix='contador-deb-check-') as directory:
    root = Path(directory)
    (root / 'var/lib/dpkg').mkdir(parents=True)
    shutil.copyfile('/var/lib/dpkg/status', root / 'var/lib/dpkg/status')
    info = root / 'var/lib/dpkg/info'
    info.mkdir()
    for record in (root / 'var/lib/dpkg/status').read_text().split('\n\n'):
        fields = dict(line.split(': ', 1) for line in record.splitlines() if ': ' in line and not line.startswith(' '))
        if 'Package' in fields:
            name = fields['Package']
            if fields.get('Multi-Arch') == 'same':
                name += ':' + fields['Architecture']
            (info / (name + '.list')).touch()
    args = ['dpkg', '--log=' + str(root / 'dpkg.log'), '--root=' + str(root)]
    subprocess.run(args + ['--install', str(package)], check=True)
    code = "import sys; sys.path.insert(0,sys.argv[1]); from contador_carpetas import __version__; print('Installed version:',__version__)"
    subprocess.run(['/usr/bin/python3', '-c', code, str(root / 'usr/lib/contador-carpetas')], check=True)
    subprocess.run(args + ['--remove', 'contador-carpetas'], check=True)
    assert not (root / 'usr/bin/contador-carpetas').exists()
print('Isolated install/import/removal: OK')
