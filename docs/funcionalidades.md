# S3 Desktop — Guía de funcionalidades

S3 Desktop es una aplicación de escritorio para Windows que te permite conectarte a Amazon S3, ver tus archivos en la nube y trabajar con ellos de forma similar a una carpeta del equipo.

---

## Primer uso

Al abrir la aplicación por primera vez debes definir una **contraseña maestra**. Esa contraseña protege las cuentas de Amazon que guardes en el programa. En los siguientes inicios te pedirá la misma contraseña para desbloquear el acceso.

Si olvidas la contraseña maestra, no podrás recuperar las cuentas guardadas; tendrás que volver a registrarlas.

---

## Cuentas de Amazon

Puedes guardar **una o varias cuentas** de Amazon en la aplicación. Cada cuenta se identifica con un nombre (alias) que tú eliges, para distinguirla fácilmente.

Para cada cuenta necesitas:

- Un nombre o alias
- La clave de acceso y la clave secreta que te proporciona Amazon
- La región (por ejemplo, la zona geográfica del servicio)

Opcionalmente puedes indicar datos adicionales si tu proveedor lo requiere (token temporal o dirección de servicio alternativa).

Al guardar una cuenta, la aplicación comprueba que los datos sean válidos antes de almacenarlos.

### Acciones disponibles

| Acción | Descripción |
|--------|-------------|
| **Clic en una cuenta** | Seleccionar la cuenta activa en el panel lateral |
| **+ Cuenta** | Registrar una nueva cuenta |
| **Editar** | Modificar los datos de la cuenta seleccionada en la lista |

Las cuentas se muestran en una **lista vertical** en el panel izquierdo de la ventana. Al hacer clic en un nombre, esa cuenta pasa a estar activa.

---

## Buckets (contenedores de archivos)

Un *bucket* es el contenedor principal donde Amazon guarda tus archivos. La aplicación **no lista automáticamente** todos tus buckets: tú escribes el **nombre exacto** del bucket que quieres usar.

| Acción | Descripción |
|--------|-------------|
| **Clic en un bucket** | Abrir ese bucket en el explorador de la derecha |
| **+ Bucket** | Agregar un bucket escribiendo su nombre |

Los buckets aparecen en una **lista** debajo de las cuentas, en el mismo panel lateral. Solo se muestran los buckets asociados a la cuenta seleccionada.

Esto es útil cuando tu cuenta solo tiene permiso para acceder a buckets concretos y no puede ver el listado completo.

Las cuentas quedan guardadas de forma protegida en tu equipo y solo son accesibles tras introducir la contraseña maestra.

---

## Explorar archivos y carpetas

La parte derecha de la ventana muestra el contenido del bucket en forma de **lista**, como una ventana de archivos de Windows:

- **Nombre** del archivo o carpeta
- **Tamaño** (solo archivos)
- **Fecha de última modificación**

### Navegación

- Haz **doble clic** en una carpeta para entrar en ella.
- Usa la fila **..** o el botón **↑ Subir** para volver a la carpeta anterior.
- La barra **Ruta** muestra dónde estás dentro del bucket (por ejemplo, `s3://mi-bucket/documentos/2024/`).
- **Actualizar** vuelve a cargar el contenido de la carpeta actual.

---

## Subir archivos

Puedes **arrastrar archivos** desde el Explorador de Windows y soltarlos sobre la lista de la aplicación.

- Si sueltas los archivos en un espacio vacío, se suben a la **carpeta en la que estás**.
- Si sueltas sobre una **carpeta** de la lista, se suben **dentro de esa carpeta**.
- Si un archivo con el mismo nombre ya existe, se **reemplaza** por el nuevo.

El progreso de la subida aparece en el panel de transferencias en la parte inferior.

---

## Descargar archivos

### Un solo archivo

- Clic derecho sobre un archivo → **Descargar**.
- Elige dónde guardarlo en tu equipo.

### Varios archivos a la vez

1. Marca los archivos con la **casilla** de la primera columna.
2. Pulsa **Descargar seleccionados**.
3. Elige una **carpeta destino**; todos los archivos marcados se guardarán ahí.

También puedes usar **Seleccionar todo** para marcar todos los archivos visibles; cuando todos estén marcados, el botón cambia a **Deseleccionar todo**. Si hay muchos archivos, verás un mensaje de espera sobre la lista mientras se completa la selección.

> Las casillas solo aparecen en archivos, no en carpetas.

---

## Gestionar archivos y carpetas

Desde el **menú contextual** (clic derecho) puedes:

| Acción | Qué hace |
|--------|----------|
| **Abrir** | Entrar en una carpeta |
| **Nueva carpeta** | Crear una carpeta en la ubicación actual |
| **Renombrar** | Cambiar el nombre de un archivo o carpeta |
| **Eliminar** | Borrar un archivo o carpeta (pide confirmación) |

El botón **Nueva carpeta** en la barra del explorador también crea carpetas en la ruta actual.

---

## Panel de transferencias

En la parte inferior de la ventana verás el estado de las **subidas y descargas** en curso:

- Dirección (subida o bajada)
- Nombre del archivo
- Estado (en espera, en progreso, completado, error)
- Barra de progreso

Las transferencias se realizan en segundo plano; puedes seguir navegando mientras se completan.

---

## Bloquear la aplicación

El botón **Bloquear**, en el pie del panel lateral, cierra la sesión actual y vuelve a proteger las cuentas guardadas. La próxima vez que abras la aplicación deberás introducir de nuevo la contraseña maestra.

Al cerrar la aplicación también se bloquea el acceso a las cuentas.

---

## Panel lateral (conexión)

En el **lado izquierdo** de la ventana encontrarás todo lo relacionado con **a qué cuenta y bucket estás conectado**:

| Elemento | Función |
|----------|---------|
| **Lista de cuentas** | Ver y elegir la cuenta de Amazon activa |
| **+ Cuenta** | Agregar una nueva cuenta |
| **Editar** | Modificar la cuenta seleccionada |
| **Lista de buckets** | Ver y elegir el bucket que quieres explorar |
| **+ Bucket** | Agregar un bucket por nombre |
| **Por defecto** | Usar la cuenta seleccionada al abrir la aplicación |
| **Eliminar cuenta** | Quitar una cuenta guardada |
| **Bloquear** | Cerrar sesión y proteger las cuentas |

Puedes **redimensionar** el ancho del panel arrastrando el borde entre el panel y el explorador de archivos.

---

## Barra del explorador

| Elemento | Función |
|----------|---------|
| **↑ Subir** | Volver a la carpeta anterior |
| **Ruta** | Ver ubicación actual dentro del bucket |
| **Actualizar** | Recargar la lista |
| **Nueva carpeta** | Crear carpeta aquí |
| **Seleccionar todo / Deseleccionar todo** | Marcar todos los archivos o quitar la selección |
| **Descargar seleccionados** | Bajar los archivos marcados |
| **Eliminar** | Borrar el archivo o carpeta seleccionado en la lista (pide confirmación) |

---

## Datos guardados en tu equipo

La aplicación guarda en tu perfil de Windows:

- Las cuentas de Amazon (protegidas con tu contraseña maestra)
- Los buckets que hayas agregado
- La cuenta predeterminada seleccionada

Nada de esto se envía fuera de tu equipo salvo las operaciones que tú realices explícitamente (subir o bajar archivos con Amazon).
