import os
from pathlib import Path
import tempfile
import time
import unittest
from unittest.mock import patch
import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, GLib
from contador_carpetas.gui import Window

class GuiTests(unittest.TestCase):
    def wait(self, window):
        deadline = time.monotonic() + 20
        while window.busy and time.monotonic() < deadline:
            Gtk.main_iteration_do(False)
            time.sleep(.001)
        self.assertFalse(window.busy)

    def test_worker_sort_navigation_preferences(self):
        with tempfile.TemporaryDirectory() as temp, patch.dict(os.environ, XDG_CONFIG_HOME=temp, XDG_STATE_HOME=temp):
            root = Path(temp) / 'root'
            for name, count in [('a', 3), ('b', 7)]:
                folder = root / name
                folder.mkdir(parents=True)
                for i in range(count):
                    (folder / str(i)).touch()
            window = Window()
            window.entry.set_text(str(root))
            window.start()
            self.wait(window)
            self.assertEqual(window.result.files, 10)
            self.assertEqual([row[1] for row in window.store], [7, 3])
            result = window.result
            for column in (0, 2):
                for direction in (Gtk.SortType.ASCENDING, Gtk.SortType.DESCENDING):
                    window.store.set_sort_column_id(column, direction)
                    values = [row[column] for row in window.store]
                    self.assertEqual(values, sorted(values, reverse=direction == Gtk.SortType.DESCENDING))
                    self.assertIs(window.result, result)
            window.store.set_sort_column_id(1, Gtk.SortType.ASCENDING)
            self.assertEqual([row[1] for row in window.store], [3, 7])
            window.open_row(window.tree, Gtk.TreePath.new_from_string('0'), None)
            self.wait(window)
            self.assertEqual(window.current_path, str(root / 'a'))
            window.go_back()
            self.wait(window)
            self.assertEqual(window.current_path, str(root))
            window.close_window()
            restored = Window()
            self.assertEqual(restored.entry.get_text(), str(root))
            self.assertEqual(restored.store.get_sort_column_id()[0], 1)
            restored.close_window()

    def test_responsiveness_and_cancel(self):
        with tempfile.TemporaryDirectory() as temp, patch.dict(os.environ, XDG_CONFIG_HOME=temp, XDG_STATE_HOME=temp):
            folder = Path(temp) / 'root' / 'many'
            folder.mkdir(parents=True)
            for i in range(12000):
                (folder / str(i)).touch()
            window = Window()
            window.entry.set_text(str(folder.parent))
            ticks = []
            timer = GLib.timeout_add(2, lambda: ticks.append(time.monotonic()) or True)
            window.start()
            self.wait(window)
            self.assertEqual(window.result.files, 12000)
            self.assertGreater(len(ticks), 2)
            window.start()
            window.stop.clicked()
            self.wait(window)
            self.assertTrue(window.result.cancelled)
            GLib.source_remove(timer)
            window.close_window()

    def test_many_immediate_folders_batch_publication(self):
        with tempfile.TemporaryDirectory() as temp, patch.dict(os.environ, XDG_CONFIG_HOME=temp, XDG_STATE_HOME=temp):
            root = Path(temp) / 'root'
            root.mkdir()
            for index in range(650):
                (root / str(index)).mkdir()
            window = Window()
            window.entry.set_text(str(root))
            window.start()
            self.wait(window)
            self.assertEqual(len(window.store), 650)
            self.assertEqual(window.result.directories, 650)
            window.close_window()
