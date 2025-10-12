

from dataclasses import dataclass
from application.conta_agua.interface import ContaAguaRepositoryPort
from typing import Sequence
import uuid
from pure_eval.my_getattr_static import slot_descriptor

from core.entities.conta_agua import ContaAgua

@dataclass(slot=True)
class ContaAguaCommand:
    
    def put(self, conta: ContaAgua) -> ContaAgua:
        return self.repositorio.put(conta)