from dataclasses import dataclass
from typing import Callable


@dataclass(frozen=True)
class ModuleDefinition:
    module_id: str
    title: str
    builder: Callable

