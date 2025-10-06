from __future__ import annotations

"""VO de domínio para valores monetários.

Esta classe especializa o normalizador `ValorMonetario`, herdando toda a
capacidade de parsing/normalização a partir de strings, inteiros, floats
ou Decimal. Mantém semântica de Value Object (imutável e com igualdade por valor).
"""

from decimal import Decimal
from typing import Union

from core.shared.value_objects import ValorMonetario


class Valor(ValorMonetario):
    """Value Object do domínio para representar um valor monetário.

    - Utilize `Valor.criar_de_bruto(...)` para criar a partir de textos como
      "R$ 1.234,56".
    - Utilize `Valor.criar_de_centavos(123456)` para criar a partir de centavos.
    - A propriedade `valor` expõe um `Decimal` com 2 casas.
    - `para_centavos()` retorna inteiro em centavos (ótimo para persistência em banco).
    """

    # Impede construção direta; obrigatoriedade de usar fábricas da classe
    def __init__(self, *_args, **_kwargs) -> None:  # type: ignore[override]
        raise TypeError("Use as fábricas da classe (ex.: Valor.criar_de_bruto, Valor.criar_de_centavos).")

    # Construtor interno para uso exclusivo das fábricas
    @classmethod
    def _criar_interno(cls, valor_normalizado: Decimal) -> "Valor":
        instancia = object.__new__(cls)
        # Inicializa campos do dataclass pai (frozen) garantindo quantização
        ValorMonetario.__init__(instancia, valor_normalizado)  # type: ignore[misc]
        return instancia  # type: ignore[return-value]

    # Criação (aliases mais declarativos sobre a API herdada)
    @classmethod
    def criar_de_bruto(cls, bruto: Union[str, int, float, Decimal]) -> "Valor":
        normalizado = ValorMonetario.from_bruto(bruto).valor
        return cls._criar_interno(normalizado)

    @classmethod
    def criar_de_decimal(cls, valor_decimal: Decimal) -> "Valor":
        return cls._criar_interno(valor_decimal)

    @classmethod
    def criar_de_centavos(cls, centavos: int) -> "Valor":
        normalizado = ValorMonetario.from_centavos(centavos).valor
        return cls._criar_interno(normalizado)

    # Persistência otimizada para banco de dados
    def para_banco(self) -> int:
        """Representação otimizada para banco: inteiro em centavos."""
        return self.to_centavos()

    @classmethod
    def do_banco(cls, centavos: int) -> "Valor":
        """Reconstrói a partir do formato otimizado de banco (centavos)."""
        return cls.criar_de_centavos(centavos)

    # Atualizações imutáveis
    def atualizar_valor(self, novo_valor: Union[str, int, float, Decimal]) -> "Valor":
        """Retorna um novo VO com o valor atualizado a partir de entrada bruta."""
        return type(self).criar_de_bruto(novo_valor)

    def incrementar(self, delta: Union[int, float, Decimal]) -> "Valor":
        """Soma o delta ao valor atual e retorna um novo VO."""
        soma = self.valor + Decimal(str(delta))
        return type(self)._criar_interno(soma)

    def decrementar(self, delta: Union[int, float, Decimal]) -> "Valor":
        """Subtrai o delta do valor atual e retorna um novo VO."""
        sub = self.valor - Decimal(str(delta))
        return type(self)._criar_interno(sub)

    # Verificações
    def esta_normalizado(self) -> bool:
        """Confere se o Decimal está com 2 casas (estado normalizado)."""
        return self.valor == self.valor.quantize(Decimal("0.01"))

    # Ciclo de vida (DDD): VO é imutável e não possui deleção em si.
    # Exponhamos um método de utilidade para sinalizar remoção pelo agregado/repositorio.
    def remover(self) -> None:
        """Em DDD, a remoção do VO é responsabilidade do agregado/repositório.
        Método utilitário sem efeitos colaterais, presente por simetria de API.
        """
        return None

    # Nomes compatíveis com a API herdada, porém mais declarativos
    def para_centavos(self) -> int:
        return self.to_centavos()
