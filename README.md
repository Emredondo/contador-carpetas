# Contador de Carpetas 1.0.0

Aplicación nativa para Debian 13 Trixie, Python 3 y GTK 3.
Licencia **GPL-3.0-or-later** (texto completo en LICENSE).

## Instalación y uso

```sh
sudo apt install ./dist/contador-carpetas_1.0.0_all.deb
contador-carpetas
```

Aparece en el menú de utilidades de XFCE. Acepta una ruta como argumento:
`contador-carpetas /ruta/a/carpeta`. Desinstalar: `sudo apt remove contador-carpetas`.
Dependencias oficiales: `python3`, `python3-gi`, `gir1.2-gtk-3.0`. No utiliza pip.

Seleccionar una ruta con «Elegir…» y pulsar «Analizar / Actualizar». «Detener»
conserva resultados parciales. La tabla muestra subcarpetas inmediatas con
estadísticas de todos sus niveles. El orden inicial es archivos de mayor a menor;
pulsar los encabezados alterna el sentido sin repetir el análisis. Doble clic
analiza una carpeta; «Atrás» vuelve al directorio antes analizado. Clic derecho
abre la carpeta en el administrador de archivos. Archivo → Exportar CSV guarda
las filas en el orden visible, en UTF-8 con BOM, incluidos ruta y estado.

El resumen incluye los archivos directamente contenidos en el origen, que no
aparecen en filas. Cuenta directorios descubiertos incluyendo las subcarpetas
inmediatas y excluyendo el origen. Subdirectorios excluye la propia fila.

Por defecto se mide **espacio asignado** (`st_blocks × 512`). Opciones → Usar
tamaño aparente utiliza `st_size`. Unidades de base 1024 rotuladas KB/MB/GB/TB.
Solo cuentan archivos regulares; los vacíos también cuentan. Se omiten todos los
enlaces simbólicos (incluidos los rotos), sockets, dispositivos y FIFO.
Los enlaces omitidos se indican en el resumen. Los enlaces duros cuentan por
entrada, sin deduplicar sus bloques. No se incluyen metadatos ni directorios en
el tamaño. Los resultados son por entrada de archivo, no por inodo único.

Se omiten subdirectorios con `st_dev` distinto del origen, salvo que se habilite
la opción de atravesar sistemas de archivos. La fila/ancestro indica Incompleto.
Las opciones se aplican al siguiente análisis. Los errores se registran sin
abortar el resto. Resultados no exhaustivos muestran Incompleto o Parcial.

## Preferencias y registros

Configuración: `$XDG_CONFIG_HOME/contador-carpetas/settings.json`, por defecto
`~/.config/contador-carpetas/settings.json`. Guarda ruta, geometría, orden,
anchos y opciones al cerrar. Wayland puede ignorar la posición de ventana.
Registro rotativo: `$XDG_STATE_HOME/contador-carpetas/errors.log`, por defecto
`~/.local/state/contador-carpetas/errors.log` (tres archivos de hasta 1 MB).
Solo se escribe configuración, registro y el CSV solicitado, sin modificar el
árbol analizado.

## Código y reconstrucción

Desde la raíz del proyecto, usando el Python del sistema:

```sh
sudo apt install python3 python3-gi gir1.2-gtk-3.0
/usr/bin/python3 -m contador_carpetas
sh scripts/build-deb.sh
```

La construcción requiere `dpkg` y utilidades básicas de Debian, sin privilegios
ni acceso a red. Genera `dist/contador-carpetas_1.0.0_all.deb`. Instala código en
`/usr/lib/contador-carpetas/contador_carpetas`, lanzador en `/usr/bin`, icono y
.desktop en `/usr/share`. No tiene scripts de instalación ni descarga dependencias.

```sh
/usr/bin/python3 -m unittest discover -s tests -v
dpkg-deb --info dist/contador-carpetas_1.0.0_all.deb
desktop-file-validate data/contador-carpetas.desktop
lintian dist/contador-carpetas_1.0.0_all.deb
```

Las pruebas GTK necesitan sesión gráfica; para probar solo el motor:
`/usr/bin/python3 -m unittest discover -s tests -p test_core.py -v`.
Validadores opcionales: paquetes `desktop-file-utils`, `lintian`.

## Arquitectura y límites

`scanner.py`: pila iterativa, un recorrido con `os.scandir`, cancelación y
progreso. `models.py`: estadísticas y formato. `gui.py`: GTK y comunicación
mediante `GLib.idle_add`. Configuración, CSV y registro están en módulos separados.
Memoria proporcional a profundidad y cantidad de carpetas inmediatas, sin cargar
archivos. Un iterador abierto por nivel; no hay límites artificiales, aunque se
aplican límites del sistema (rutas y descriptores). Los errores se registran.

No es una instantánea: cambios simultáneos del árbol pueden afectar los totales.
No debe usarse como frontera de seguridad ante sustituciones maliciosas de rutas
durante el análisis. `st_dev` no distingue bind mounts del mismo sistema de
archivos; pueden contarse de nuevo. Reflinks, compresión y enlaces duros impiden
interpretar el tamaño como bloques físicos exclusivos. Un montaje de red
bloqueado puede retrasar la cancelación hasta que retorne la llamada del sistema.
Las filas aparecen al finalizar o detener; el progreso muestra cifras durante
el recorrido. La publicación por lotes de un número excepcional de carpetas inmediatas
puede demorar, manteniendo activa la interfaz. No se han medido millones de archivos.

CSV conserva nombres originales: importar las columnas de texto como texto en
hojas de cálculo para nombres que comiencen con `=` u otros prefijos de fórmula.
Véase TEST-REPORT.md para las pruebas de esta entrega.

Comprobación de instalación aislada (requiere `fakeroot`):

```sh
fakeroot /usr/bin/python3 scripts/check-package.py
```

El verificador usa el estado de dependencias del sistema y una raíz temporal;
no instala la aplicación en el sistema anfitrión.
