# Mesa Clara

Aplicación de escritorio para sustituir las hojas compartidas de LibreOffice por formularios protegidos y registros guardados en SQLite.

## Arranque

1. Instala Python 3.11 o posterior.
2. Instala las dependencias con `pip install -r requirements.txt`.
3. Ejecuta `iniciar_app.bat` o `python app.py`.

La base de datos es `restaurante.db`. La aplicación conserva las tablas antiguas y crea automáticamente las que falten. Conviene incluir este archivo en las copias de seguridad.

La rueda de ajustes permite elegir la carpeta donde se guardan los informes. La configuración personal se guarda en `settings.json` y no se incluye en Git.

## Módulos

Cada apartado vive en su propio archivo dentro de `modules/`:

- `arqueo.py`: conteo físico de monedas y billetes y cuadre de caja.
- `recaudacion.py`: venta directa y cantidades de desayunos, almuerzos y cenas por efectivo, VISA y crédito, con precios configurables.
- `todo_incluido.py`: cuadrícula mensual de 31 días, totales y estado de cumplimentación.
- `temperaturas.py`: dos controles diarios del lavavajillas y avisos APPCC.
- `temperaturas_buffet.py`: dos muestras por producto y servicio para expositores calientes, fríos y postres.
- `limpieza.py`: responsables de cada tarea durante la semana.
- `informes.py`: generación de documentos PDF.

`app.py` solo construye la ventana y carga los módulos indicados en `config.json`. Para ocultar un apartado, elimina su nombre de `enabled_modules`; para recuperarlo, vuelve a añadirlo. No hace falta borrar código ni datos.

Los informes se guardan en la carpeta `informes/`, que se crea automáticamente.

## Añadir un módulo

1. Crea un archivo nuevo en `modules/` con una función `build_nombre(parent, app)`.
2. Regístralo en `modules/registry.py`.
3. Añade su identificador a `config.json`.

Las rutas, fechas, números y acceso a la base de datos están centralizados en `core/` para que todos los módulos se comporten igual.

## Privacidad y Git

El repositorio excluye bases de datos, informes, libros de cálculo, copias de seguridad, imágenes, logos y rutas personales. El código publicado utiliza únicamente el nombre neutral `Mesa Clara`.
