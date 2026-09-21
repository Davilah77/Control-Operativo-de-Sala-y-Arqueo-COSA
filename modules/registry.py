from modules.arqueo import build_arqueo
from modules.informes import build_informes
from modules.inventario import build_inventario
from modules.limpieza import build_limpieza
from modules.recaudacion import build_recaudacion
from modules.temperaturas import build_temperaturas
from modules.temperaturas_buffet import build_temperaturas_buffet
from modules.todo_incluido import build_todo_incluido

from modules.base import ModuleDefinition


AVAILABLE_MODULES = {
    definition.module_id: definition
    for definition in (
        ModuleDefinition("arqueo", "💵 Arqueo de caja", build_arqueo),
        ModuleDefinition("recaudacion", "🧾 Recaudación", build_recaudacion),
        ModuleDefinition("todo_incluido", "🥤 Todo incluido", build_todo_incluido),
        ModuleDefinition("temperaturas", "🌡️ Temperaturas", build_temperaturas),
        ModuleDefinition("temperaturas_buffet", "🍽️ Temp. buffet", build_temperaturas_buffet),
        ModuleDefinition("limpieza", "🧼 Limpieza", build_limpieza),
        ModuleDefinition("inventario", "📦 Inventario", build_inventario),
        ModuleDefinition("informes", "📊 Informes", build_informes),
    )
}
