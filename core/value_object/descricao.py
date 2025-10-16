from __future__ import annotations

from dataclasses import dataclass
from typing import ClassVar


@dataclass(frozen=True, slots=True)
class Descricao:
    """Value Object de domínio para a descrição de uma transação.

    Regras:
    - Obrigatoriamente não vazia após normalização.
    - Máximo de 150 caracteres.
    - Normalização: trim e colapso de espaços em branco consecutivos.
    """

    descricao: str
    TAMANHO_MAXIMO: ClassVar[int] = 150

    def __init__(self, *_args, **_kwargs) -> None:  # type: ignore[override]
        raise TypeError("Use as fábricas da classe (ex.: Descricao.criar_de_texto).")

    @classmethod
    def _validar_e_normalizar_texto(cls, texto: str) -> str:
        normalizado = " ".join(texto.strip().split())
        if len(normalizado) == 0:
            raise ValueError("Descrição não pode ser vazia.")
        if len(normalizado) > cls.TAMANHO_MAXIMO:
            raise ValueError(f"Descrição deve ter no máximo {cls.TAMANHO_MAXIMO} caracteres.")
        return normalizado

    @classmethod
    def _criar_interno(cls, descricao_normalizada: str) -> "Descricao":
        instancia = object.__new__(cls)
        object.__setattr__(instancia, "descricao", descricao_normalizada)
        return instancia  # type: ignore[return-value]

    # Fábrica
    @classmethod
    def criar_de_texto(cls, texto: str) -> "Descricao":
        return cls._criar_interno(cls._validar_e_normalizar_texto(texto))

    # Atualização imutável
    def atualizar_descricao(self, novo_texto: str) -> "Descricao":
        return type(self).criar_de_texto(novo_texto)

    # Persistência e semântica
    def para_banco(self) -> str:
        """Retorna string normalizada para armazenamento (ex.: coluna VARCHAR(150))."""
        return self.descricao

    def como_texto(self) -> str:
        return self.descricao

    # Verificações
    def esta_normalizada(self) -> bool:
        return self.descricao == type(self)._validar_e_normalizar_texto(self.descricao)

    def __str__(self) -> str:
        return self.descricao
