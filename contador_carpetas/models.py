from dataclasses import dataclass, field


@dataclass
class Folder:
    name: str
    path: str
    files: int = 0
    directories: int = 0
    size: int = 0
    errors: int = 0
    skipped: int = 0
    complete: bool = False

    @property
    def status(self):
        if not self.complete:
            return 'Parcial: detenido o pendiente'
        if self.errors or self.skipped:
            return f'Incompleto: {self.errors} errores, {self.skipped} montajes omitidos'
        return 'Completo'


@dataclass
class Result:
    path: str
    folders: list = field(default_factory=list)
    files: int = 0
    directories: int = 0
    size: int = 0
    errors: int = 0
    skipped: int = 0
    links: int = 0
    cancelled: bool = False
    elapsed: float = 0.0


def sorted_folders(folders, key='files', descending=True):
    return sorted(folders, key=lambda f: (getattr(f, key).casefold() if key == 'name'
                                         else getattr(f, key), f.name), reverse=descending)


def human_size(value):
    number = float(value)
    for unit in ('B', 'KB', 'MB', 'GB', 'TB', 'PB', 'EB'):
        if number < 1024 or unit == 'EB':
            return f'{number:.1f} {unit}' if unit != 'B' else f'{int(number)} B'
        number /= 1024
