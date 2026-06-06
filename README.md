# S3 Desktop

Cliente de escritorio Windows para Amazon S3, escrito en Python con PySide6.

## Características

- **Credenciales AWS cifradas** con contraseña maestra (Argon2 + Fernet)
- **Múltiples perfiles** de credenciales (access key / secret key)
- **Explorador S3** estilo lista de archivos con navegación por carpetas
- **Subida por arrastre** desde el Explorador de Windows a la ruta S3 actual
- **Operaciones**: descargar, eliminar, renombrar, crear carpetas
- **Sincronización bidireccional programada** entre carpetas locales y prefijos S3

## Requisitos

- Python 3.11+
- [uv](https://docs.astral.sh/uv/) (recomendado)

## Instalación

```powershell
cd app_s3
uv sync
```

## Ejecución

```powershell
uv run app-s3
```

O:

```powershell
uv run python -m app_s3
```

## Datos de usuario

La aplicación guarda configuración en:

```
%APPDATA%\S3Desktop\
```

Incluye credenciales cifradas, bookmarks de buckets, jobs de sync y logs.

## Tests

```powershell
uv sync --group dev
uv run pytest
uv run ruff check src tests
```

## Estructura del proyecto

```
src/app_s3/
├── domain/           # Modelos y excepciones
├── infrastructure/   # boto3, cifrado, filesystem, sync engine
├── application/      # Servicios de aplicación
├── ui/               # PySide6 (ventanas, diálogos, workers)
└── config/           # Rutas de datos
```

## Empaquetado Windows

Instala dependencias de desarrollo (incluye PyInstaller):

```powershell
uv sync --group dev
```

### PyInstaller (recomendado)

PyInstaller necesita un script `.py` como entrada (no uses `-m app_s3`; en PyInstaller `-m` es para manifiestos de Windows).

```powershell
uv run pyinstaller `
  --name S3Desktop `
  --windowed `
  --icon src/app_s3/assets/app_icon.ico `
  --collect-all PySide6 `
  --copy-metadata app-s3 `
  --paths src `
  scripts/s3desktop_entry.py
```

Resultado:

```
dist\S3Desktop\S3Desktop.exe
```

La carpeta `dist\S3Desktop\` contiene el `.exe` y las DLLs de Qt; cópiala completa para distribuir.

Builds posteriores pueden reutilizar el spec generado:

```powershell
uv run pyinstaller S3Desktop.spec
```

(Asegúrate de que `S3Desktop.spec` incluya `icon='src/app_s3/assets/app_icon.ico'` en la sección `EXE`.)

### Icono personalizado del ejecutable

En Windows, el icono del `.exe` en el Explorador de archivos debe ser un archivo **`.ico` cuadrado** con varios tamaños (16–256 px), no un `.png`.

1. Coloca tu imagen fuente en `src/app_s3/assets/app_icon.png`.
2. Genera el `.ico` (cuadrado, multi-resolución):

```powershell
uv run --with pillow python scripts/generate_app_icon.py
```

3. Empaqueta con `--icon` (o usa `S3Desktop.spec`, que ya apunta a `app_icon.ico`):

```powershell
uv run pyinstaller S3Desktop.spec --clean --noconfirm
```

No modifiques el `.exe` generado con herramientas externas para cambiar el icono; eso puede corromper el archivo y provocar el error *Could not load PyInstaller's embedded PKG archive*.

**Importante:** si cambias el icono pero el Explorador sigue mostrando el anterior, Windows puede estar usando caché. Prueba renombrar el `.exe`, abrirlo de nuevo, o reiniciar el Explorador (`ie4uinit.exe -show` en una consola elevada).

**Dos iconos (opcional):**

| Uso | Archivo | Cómo se aplica |
|-----|---------|----------------|
| Icono del `.exe` en Windows | `app_icon.ico` | `--icon` / `S3Desktop.spec` |
| Icono de ventana/barra de tareas al ejecutar | `app_icon.png` | `get_app_icon()` en `src/app_s3/ui/resources.py` |

Actualiza el PNG y vuelve a ejecutar `scripts/generate_app_icon.py` antes de cada build si quieres que ambos coincidan.

### Alternativa: pyside6-deploy

```powershell
uv run pyside6-deploy -c pyproject.toml
```

Herramienta oficial de Qt para PySide6; requiere más configuración en `pyproject.toml`.
