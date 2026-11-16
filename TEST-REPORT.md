# Informe de pruebas — 16 de noviembre de 2026

Entorno: Debian GNU/Linux 13 Trixie, Python 3.13, PyGObject y GTK 3 del sistema.

## Resultado

**13 pruebas automatizadas aprobadas** (10 de motor/utilidades, 3 de GTK).
La sesión gráfica de las pruebas utilizó el backend Broadway de GTK 3.

- Directorios vacíos: cero archivos/bytes y estado completo.
- 6.000 archivos: conteo exacto sin duplicados.
- 180 niveles de subdirectorios: conteo de archivos, carpetas y bytes correcto.
- Archivos vacíos, espacios, acentos, comas y comillas: admitidos.
- Directorio sin permisos: prueba real con chmod 000; error registrado como
  resultado incompleto, sin abortar el análisis.
- Directorio eliminado al entrar: error recuperable (eliminación controlada).
- Enlaces a archivos, directorios, ciclos y destinos inexistentes: omitidos.
- Límite entre sistemas de archivos: prueba controlada simulando st_dev distinto;
  omisión predeterminada y recorrido habilitado verificados. No se montaron
  sistemas de archivos adicionales.
- Cancelación: motor y botón Detener; resultado parcial y retorno de la interfaz.
- Archivo disperso de 10 MB: diferencia entre tamaño aparente y bloques asignados.
- Ordenamiento: archivos, tamaño y nombre en ambos sentidos; el cambio del modelo
  GTK conserva el mismo resultado sin lanzar otro análisis.
- CSV: nombres especiales, rutas, conteos y lectura de vuelta correctos.
- Configuración: persistencia XDG, recuperación ante JSON inválido y reapertura.
- GTK: navegación con doble clic y Atrás, carga por lotes de 650 carpetas inmediatas.
- GTK: análisis de 12.000 archivos con eventos de temporizador atendidos mientras
  trabaja el hilo de análisis; cancelación en una nueva ejecución.

Revisión visual con temas claro y oscuro: texto legible, tabla, controles,
indicador de progreso y resumen. Capturas en dist/preview-light.png y
preview-dark.png. El ejemplo de la orden de trabajo produce Vacaciones: 1.000
archivos y Familia: 600 archivos.

## Paquete Debian

- Generación mediante scripts/build-deb.sh y dpkg-deb: correcta; arquitectura all,
  propietarios root/root, permisos y rutas de sistema estándar.
- desktop-file-validate: sin incidencias.
- lintian: sin errores ni advertencias.
- apt-get -s install ./dist/contador-carpetas_1.0.0_all.deb: dependencias resueltas
  en Debian 13, instalación y configuración previstas correctamente.
- Instalación, importación de la versión 1.0.0 y desinstalación mediante dpkg en
  una raíz temporal con fakeroot y el estado de dependencias del anfitrión.
  El sistema del usuario no se modificó. Script: scripts/check-package.py.

## Alcance y pendientes de validación manual

No se hizo una instalación global con APT en el equipo del usuario. La apertura
externa mediante el administrador de archivos, la entrada del menú de XFCE y
los diálogos interactivos de selección/exportación requieren comprobación manual
en el escritorio de destino. Los archivos desktop y la llamada Gio están incluidos.
No se midieron millones de archivos, sistemas de red bloqueados ni montajes reales.
Los límites de rutas, descriptores, enlaces duros y bind mounts están documentados
en README.md. Las pruebas de respuesta no constituyen una garantía de latencia
para cualquier disco, sistema de archivos o cantidad de carpetas.
