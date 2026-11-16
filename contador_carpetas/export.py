import csv


def export_csv(path, folders):
    with open(path, 'w', encoding='utf-8-sig', newline='') as stream:
        writer = csv.writer(stream)
        writer.writerow(['nombre', 'ruta_completa', 'archivos', 'directorios', 'tamano_bytes', 'estado'])
        for folder in folders:
            writer.writerow([folder.name, folder.path, folder.files, folder.directories, folder.size, folder.status])
