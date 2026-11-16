import csv
import os
from pathlib import Path
import tempfile
import threading
import unittest
from unittest.mock import patch
from contador_carpetas.scanner import scan
from contador_carpetas.models import sorted_folders
from contador_carpetas.export import export_csv
from contador_carpetas import config

class ScannerTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def test_empty(self):
        (self.root / 'empty').mkdir()
        result = scan(self.root)
        self.assertEqual((result.files, result.directories, result.size), (0, 1, 0))
        self.assertTrue(result.folders[0].complete)

    def test_recursive_special_zero_links(self):
        a = self.root / 'Familia ñ, "á"'
        (a / 'Navidad').mkdir(parents=True)
        (a / 'a').write_bytes(b'123')
        (a / 'Navidad' / 'b').write_bytes(b'12345')
        (a / 'cero').touch()
        (self.root / 'directo').write_bytes(b'xx')
        (a / 'ciclo').symlink_to(a, target_is_directory=True)
        (a / 'link').symlink_to(a / 'a')
        (a / 'roto').symlink_to(a / 'missing')
        result = scan(self.root, apparent=True)
        row = result.folders[0]
        self.assertEqual((row.files, row.directories, row.size), (3, 1, 8))
        self.assertEqual((result.files, result.directories, result.size, result.links), (4, 2, 10, 3))

    def test_thousands(self):
        folder = self.root / 'many'
        folder.mkdir()
        for index in range(6000):
            (folder / str(index)).touch()
        result = scan(self.root)
        self.assertEqual(result.files, 6000)
        self.assertEqual(result.folders[0].files, 6000)

    def test_deep(self):
        path = self.root / 'deep'
        path.mkdir()
        for _ in range(180):
            path /= 'd'
            path.mkdir()
        (path / 'leaf').write_bytes(b'a')
        result = scan(self.root, apparent=True)
        self.assertEqual((result.files, result.directories, result.size), (1, 181, 1))
        self.assertEqual(result.folders[0].directories, 180)

    def test_permission_denied(self):
        folder = self.root / 'denied'
        folder.mkdir()
        folder.chmod(0)
        self.addCleanup(folder.chmod, 0o700)
        result = scan(self.root)
        self.assertEqual(result.errors, 1)
        self.assertIn('Incompleto', result.folders[0].status)

    def test_deleted_during_scan(self):
        folder = self.root / 'gone'
        folder.mkdir()
        original = os.scandir
        def disappearing(path):
            if os.fspath(path) == str(folder):
                folder.rmdir()
            return original(path)
        with patch('contador_carpetas.scanner.os.scandir', side_effect=disappearing):
            result = scan(self.root)
        self.assertEqual(result.errors, 1)

    def test_cancel(self):
        folder = self.root / 'many'
        folder.mkdir()
        event = threading.Event()
        original = os.scandir
        def cancelling(path):
            iterator = original(path)
            if os.fspath(path) == str(folder):
                event.set()
            return iterator
        with patch('contador_carpetas.scanner.os.scandir', side_effect=cancelling):
            result = scan(self.root, event)
        self.assertTrue(result.cancelled)
        self.assertFalse(result.folders[0].complete)

    def test_mount_boundary(self):
        (self.root / 'mount').mkdir()
        values = list(os.stat(self.root))
        values[2] += 1
        with patch('contador_carpetas.scanner.os.stat', return_value=os.stat_result(values)):
            result = scan(self.root)
            allowed = scan(self.root, cross_filesystems=True)
        self.assertEqual(result.skipped, 1)
        self.assertEqual(allowed.skipped, 0)

    def test_disk_usage(self):
        folder = self.root / 'sparse'
        folder.mkdir()
        file = folder / 'sparse'
        with file.open('wb') as stream:
            stream.truncate(10_000_000)
        self.assertEqual(scan(self.root).size, file.stat().st_blocks * 512)
        self.assertEqual(scan(self.root, apparent=True).size, 10_000_000)

    def test_sort_csv_config(self):
        for name, count in [('Z á, "x"', 2), ('a', 1)]:
            folder = self.root / name
            folder.mkdir()
            for i in range(count):
                (folder / str(i)).touch()
        folders = scan(self.root).folders
        self.assertEqual([f.files for f in sorted_folders(folders)], [2, 1])
        self.assertEqual([f.files for f in sorted_folders(folders, descending=False)], [1, 2])
        self.assertEqual(sorted_folders(folders, 'name', False)[0].name, 'a')
        output = self.root / 'out.csv'
        export_csv(output, sorted_folders(folders))
        with output.open(encoding='utf-8-sig', newline='') as stream:
            rows = list(csv.DictReader(stream))
        self.assertEqual(rows[0]['nombre'], 'Z á, "x"')
        self.assertEqual(rows[0]['archivos'], '2')
        with patch.dict(os.environ, XDG_CONFIG_HOME=str(self.root)):
            config.save({'width': 800, 'last_directory': 'ñ'})
            self.assertEqual(config.load()['last_directory'], 'ñ')
            config.config_path().write_text('invalid')
            self.assertEqual(config.load(), {})
