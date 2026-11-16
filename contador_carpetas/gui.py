import os
import threading
import traceback
from pathlib import Path
import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, GLib, GObject, Gio
from . import config, __version__
from .scanner import scan
from .models import human_size
from .export import export_csv
from .logging_setup import setup


class Window(Gtk.Window):
    def __init__(self):
        super().__init__(title='Contador de Carpetas')
        self.settings = config.load()
        self.logger = setup()
        self.result = None
        self.busy = False
        self.closed = False
        self.cancel = threading.Event()
        self.history = []
        self.current_path = None
        self.set_default_size(self.integer('width', 940, 480, 4000), self.integer('height', 600, 320, 3000))
        if all(isinstance(self.settings.get(k), int) for k in ('x', 'y')):
            self.move(self.settings['x'], self.settings['y'])
        self.connect('delete-event', self.close_window)
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        self.add(box)
        menu = Gtk.MenuBar()
        box.pack_start(menu, False, False, 0)
        file_menu = self.submenu(menu, 'Archivo')
        self.menu_item(file_menu, 'Seleccionar directorio…', self.choose)
        self.export_item = self.menu_item(file_menu, 'Exportar CSV…', self.export)
        self.menu_item(file_menu, 'Salir', self.close_window)
        options = self.submenu(menu, 'Opciones')
        self.cross = Gtk.CheckMenuItem(label='Atravesar otros sistemas de archivos')
        self.cross.set_active(bool(self.settings.get('cross_filesystems', False)))
        options.append(self.cross)
        self.apparent = Gtk.CheckMenuItem(label='Usar tamaño aparente de los archivos')
        self.apparent.set_active(bool(self.settings.get('apparent', False)))
        options.append(self.apparent)
        help_menu = self.submenu(menu, 'Ayuda')
        self.menu_item(help_menu, 'Acerca de', self.about)
        toolbar = Gtk.Box(spacing=6, margin_start=8, margin_end=8)
        box.pack_start(toolbar, False, False, 0)
        self.back = Gtk.Button(label='Atrás')
        self.back.connect('clicked', self.go_back)
        toolbar.pack_start(self.back, False, False, 0)
        self.entry = Gtk.Entry()
        last = self.settings.get('last_directory', str(Path.home()))
        self.entry.set_text(last if isinstance(last, str) else str(Path.home()))
        self.entry.connect('activate', self.start)
        toolbar.pack_start(self.entry, True, True, 0)
        self.choose_button = Gtk.Button(label='Elegir…')
        self.choose_button.connect('clicked', self.choose)
        toolbar.pack_start(self.choose_button, False, False, 0)
        self.analyze = Gtk.Button(label='Analizar / Actualizar')
        self.analyze.connect('clicked', self.start)
        toolbar.pack_start(self.analyze, False, False, 0)
        self.stop = Gtk.Button(label='Detener')
        self.stop.connect('clicked', lambda *_: self.cancel.set())
        toolbar.pack_start(self.stop, False, False, 0)
        self.store = Gtk.ListStore(str, GObject.TYPE_UINT64, GObject.TYPE_UINT64,
                                  GObject.TYPE_UINT64, str, str)
        self.tree = Gtk.TreeView(model=self.store)
        widths = self.settings.get('column_widths', [])
        if not isinstance(widths, list):
            widths = []
        for index, title in enumerate(('Carpeta', 'Archivos', 'Tamaño', 'Subdirectorios', 'Estado')):
            renderer = Gtk.CellRendererText()
            column = Gtk.TreeViewColumn(title, renderer)
            if index in (1, 2, 3):
                renderer.set_property('xalign', 1.0)
                column.set_cell_data_func(renderer, self.numeric_cell, index)
            else:
                column.add_attribute(renderer, 'text', index)
            column.set_sort_column_id(index)
            column.set_resizable(True)
            column.set_sizing(Gtk.TreeViewColumnSizing.FIXED)
            width = widths[index] if index < len(widths) and type(widths[index]) is int else (240 if index in (0, 4) else 120)
            column.set_fixed_width(max(60, min(width, 1800)))
            self.tree.append_column(column)
        sort_column = self.integer('sort_column', 1, 0, 4)
        direction = Gtk.SortType.ASCENDING if self.settings.get('sort_ascending', False) else Gtk.SortType.DESCENDING
        self.store.set_sort_column_id(sort_column, direction)
        self.tree.connect('row-activated', self.open_row)
        self.tree.connect('button-press-event', self.context_menu)
        scroll = Gtk.ScrolledWindow()
        scroll.add(self.tree)
        box.pack_start(scroll, True, True, 0)
        self.progress = Gtk.ProgressBar(margin_start=8, margin_end=8)
        box.pack_start(self.progress, False, False, 0)
        self.status = Gtk.Label(label='Seleccione un directorio y pulse Analizar.', xalign=0, wrap=True,
                                margin_start=8, margin_end=8, margin_bottom=8)
        self.status.set_selectable(True)
        box.pack_start(self.status, False, False, 0)
        self.update_controls()
        self.show_all()

    def integer(self, key, default, low, high):
        value = self.settings.get(key, default)
        return max(low, min(high, value)) if type(value) is int else default

    @staticmethod
    def submenu(bar, label):
        item = Gtk.MenuItem(label=label)
        menu = Gtk.Menu()
        item.set_submenu(menu)
        bar.append(item)
        return menu

    @staticmethod
    def menu_item(menu, label, callback):
        item = Gtk.MenuItem(label=label)
        item.connect('activate', callback)
        menu.append(item)
        return item

    @staticmethod
    def numeric_cell(column, renderer, model, iterator, index):
        value = model.get_value(iterator, index)
        renderer.set_property('text', human_size(value) if index == 2 else f'{value:,}'.replace(',', '.'))

    def update_controls(self):
        for widget in (self.analyze, self.choose_button, self.entry, self.cross, self.apparent):
            widget.set_sensitive(not self.busy)
        self.stop.set_sensitive(self.busy)
        self.back.set_sensitive(bool(self.history) and not self.busy)
        self.export_item.set_sensitive(self.result is not None and not self.busy)

    def choose(self, *_):
        if self.busy:
            return
        dialog = Gtk.FileChooserDialog(title='Seleccionar directorio', parent=self,
                                       action=Gtk.FileChooserAction.SELECT_FOLDER)
        dialog.add_buttons('Cancelar', Gtk.ResponseType.CANCEL, 'Seleccionar', Gtk.ResponseType.OK)
        if os.path.isdir(self.entry.get_text()):
            dialog.set_current_folder(self.entry.get_text())
        if dialog.run() == Gtk.ResponseType.OK:
            self.entry.set_text(dialog.get_filename())
        dialog.destroy()

    def start(self, *_, remember=True):
        if self.busy or self.closed:
            return
        path = os.path.abspath(os.path.expanduser(self.entry.get_text()))
        if not os.path.isdir(path):
            self.message('El directorio no existe o no es accesible.')
            return
        if remember and self.current_path and self.current_path != path:
            self.history.append(self.current_path)
        self.current_path = path
        self.entry.set_text(path)
        self.store.clear()
        self.result = None
        self.busy = True
        self.cancel = threading.Event()
        self.update_controls()
        self.status.set_text('Analizando…')
        self.progress.set_fraction(0)
        GLib.timeout_add(100, self.pulse)
        options = dict(cross_filesystems=self.cross.get_active(), apparent=self.apparent.get_active())
        threading.Thread(target=self.worker, args=(path, self.cancel, options), daemon=True).start()

    def pulse(self):
        if self.closed or not self.busy:
            return False
        self.progress.pulse()
        return True

    def worker(self, path, cancel, options):
        try:
            result = scan(path, cancel, progress=lambda *values: GLib.idle_add(self.show_progress, *values),
                          logger=self.logger, **options)
            GLib.idle_add(self.finished, result, None)
        except Exception:
            self.logger.exception('Fallo inesperado del análisis')
            GLib.idle_add(self.finished, None, traceback.format_exc())

    def show_progress(self, files, directories, size):
        if not self.closed and self.busy:
            self.status.set_text(f'Analizando: {files:,} archivos · {directories:,} directorios · {human_size(size)}')
        return False

    def finished(self, result, error):
        if self.closed:
            return False
        self.result = result
        if error:
            self.busy = False
            self.progress.set_fraction(0)
            self.status.set_text('El análisis falló. Consulte el registro de errores.')
        else:
            self.status.set_text('Cargando resultados…')
            self.stop.set_sensitive(False)
            GLib.idle_add(self.publish_rows, iter(result.folders), result)
        self.update_controls()
        return False

    def publish_rows(self, rows, result):
        if self.closed:
            return False
        for _ in range(200):
            row = next(rows, None)
            if row is None:
                break
            self.store.append([row.name, row.files, row.size, row.directories, row.status, row.path])
        else:
            return True
        self.busy = False
        self.progress.set_fraction(0 if result.cancelled else 1)
        state = 'Detenido: resultados parciales' if result.cancelled else ('Incompleto' if result.errors or result.skipped else 'Finalizado')
        self.status.set_text(f'{state} · {result.files:,} archivos · {result.directories:,} directorios · '
                             f'{human_size(result.size)} · {result.elapsed:.2f} s · {result.errors} errores · '
                             f'{result.skipped} montajes omitidos · {result.links} enlaces omitidos. '
                             'Resumen incluido el contenido directo del directorio elegido.')
        self.update_controls()
        return False

    def go_back(self, *_):
        if self.history and not self.busy:
            self.entry.set_text(self.history.pop())
            self.start(remember=False)

    def open_row(self, tree, path, column):
        if not self.busy:
            self.entry.set_text(self.store[path][5])
            self.start()

    def context_menu(self, tree, event):
        if event.button != 3:
            return False
        hit = tree.get_path_at_pos(int(event.x), int(event.y))
        if hit is None:
            return False
        tree.get_selection().select_path(hit[0])
        path = self.store[hit[0]][5]
        menu = Gtk.Menu()
        self.menu_item(menu, 'Abrir en el administrador de archivos', lambda *_: self.open_external(path))
        menu.show_all()
        menu.popup_at_pointer(event)
        return True

    def open_external(self, path):
        try:
            Gio.AppInfo.launch_default_for_uri(Path(path).as_uri(), None)
        except GLib.Error as exc:
            self.message(str(exc))

    def export(self, *_):
        if self.busy or self.result is None:
            return
        dialog = Gtk.FileChooserDialog(title='Exportar CSV', parent=self, action=Gtk.FileChooserAction.SAVE)
        dialog.add_buttons('Cancelar', Gtk.ResponseType.CANCEL, 'Guardar', Gtk.ResponseType.OK)
        dialog.set_current_name('carpetas.csv')
        dialog.set_do_overwrite_confirmation(True)
        if dialog.run() == Gtk.ResponseType.OK:
            try:
                by_path = {row.path: row for row in self.result.folders}
                export_csv(dialog.get_filename(), [by_path[row[5]] for row in self.store])
            except (OSError, UnicodeError) as exc:
                self.message(f'No se pudo exportar: {exc}')
        dialog.destroy()

    def message(self, text):
        dialog = Gtk.MessageDialog(transient_for=self, modal=True, message_type=Gtk.MessageType.INFO,
                                   buttons=Gtk.ButtonsType.CLOSE, text=text)
        dialog.run()
        dialog.destroy()

    def about(self, *_):
        dialog = Gtk.AboutDialog(transient_for=self, modal=True, program_name='Contador de Carpetas',
                                version=__version__, license_type=Gtk.License.GPL_3_0,
                                comments='Conteo recursivo de carpetas para Linux.\nGPL-3.0-or-later.\n'
                                'Los enlaces simbólicos se omiten. Las opciones se aplican al siguiente análisis.')
        dialog.run()
        dialog.destroy()

    def close_window(self, *_):
        self.cancel.set()
        width, height = self.get_size()
        x, y = self.get_position()
        column, direction = self.store.get_sort_column_id()
        self.settings.update(last_directory=self.entry.get_text(), width=width, height=height, x=x, y=y,
                             sort_column=column if column is not None else 1,
                             sort_ascending=direction == Gtk.SortType.ASCENDING,
                             column_widths=[c.get_width() for c in self.tree.get_columns()],
                             cross_filesystems=self.cross.get_active(), apparent=self.apparent.get_active())
        try:
            config.save(self.settings)
        except OSError as exc:
            self.logger.warning('No se pudo guardar la configuración: %s', exc)
        self.closed = True
        self.destroy()
        if Gtk.main_level():
            Gtk.main_quit()
        return True


def main():
    import argparse
    parser = argparse.ArgumentParser(description='Contador y ordenador de carpetas GTK 3')
    parser.add_argument('directorio', nargs='?')
    parser.add_argument('--version', action='version', version=__version__)
    args = parser.parse_args()
    ready, _ = Gtk.init_check()
    if not ready:
        parser.exit(1, 'No se pudo iniciar GTK: se necesita una sesión gráfica.\n')
    window = Window()
    if args.directorio:
        window.entry.set_text(args.directorio)
        window.start()
    Gtk.main()
