"""Iterative, single-pass traversal; no GTK dependency and no symlink following."""
import os
import stat
import threading
import time
from .models import Folder, Result


def scan(path, cancel=None, cross_filesystems=False, apparent=False, progress=None, logger=None):
    cancel = cancel if cancel is not None else threading.Event()
    result = Result(os.path.abspath(path))
    started = time.monotonic()
    last_update = started

    def report(force=False):
        nonlocal last_update
        now = time.monotonic()
        if progress and (force or now - last_update >= 0.15):
            progress(result.files, result.directories, result.size)
            last_update = now

    def error(exc, folder=None):
        result.errors += 1
        if folder:
            folder.errors += 1
        if logger:
            logger.warning('%s', exc)

    def consume(entry, folder=None):
        try:
            info = entry.stat(follow_symlinks=False)
            if stat.S_ISLNK(info.st_mode):
                result.links += 1
                return None
            if stat.S_ISDIR(info.st_mode):
                result.directories += 1
                if folder:
                    folder.directories += 1
                return info
            if stat.S_ISREG(info.st_mode):
                size = info.st_size if apparent else info.st_blocks * 512
                result.files += 1
                result.size += size
                if folder:
                    folder.files += 1
                    folder.size += size
        except OSError as exc:
            error(exc, folder)
        return None

    try:
        root_device = os.stat(result.path).st_dev
        with os.scandir(result.path) as entries:
            for entry in entries:
                if cancel.is_set():
                    break
                info = consume(entry)
                if info is not None:
                    row = Folder(entry.name, entry.path)
                    if not cross_filesystems and info.st_dev != root_device:
                        row.skipped = 1
                        row.complete = True
                        result.skipped += 1
                    result.folders.append(row)
                report()
        for row in result.folders:
            if cancel.is_set():
                break
            if row.skipped:
                continue
            # Keep one scandir iterator per depth, never a list of every file.
            stack = []
            try:
                try:
                    stack.append(os.scandir(row.path))
                except OSError as exc:
                    error(exc, row)
                while stack and not cancel.is_set():
                    try:
                        entry = next(stack[-1])
                    except StopIteration:
                        stack.pop().close()
                        continue
                    except OSError as exc:
                        error(exc, row)
                        stack.pop().close()
                        continue
                    info = consume(entry, row)
                    if info is not None:
                        if not cross_filesystems and info.st_dev != root_device:
                            row.skipped += 1
                            result.skipped += 1
                        else:
                            try:
                                stack.append(os.scandir(entry.path))
                            except OSError as exc:
                                error(exc, row)
                    report()
                row.complete = not cancel.is_set()
            finally:
                for iterator in stack:
                    iterator.close()
            report()
    except OSError as exc:
        error(exc)
    result.cancelled = cancel.is_set()
    result.elapsed = time.monotonic() - started
    report(True)
    return result
