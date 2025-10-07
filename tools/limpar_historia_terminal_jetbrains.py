from __future__ import annotations

import os
import sys
from typing import Iterable, List


def listar_arquivos_jetbrains_no_diretorio(caminho_diretorio: str) -> List[str]:
    """Retorna os nomes de arquivos no diretório que parecem ser históricos do Terminal do JetBrains
    salvos incorretamente (com o caminho Windows na frente e sufixo pessoal-history*).

    Critérios de identificação:
    - Contém "jetbrains", "terminal", "history" e "pessoal-history" (case-insensitive)
    - É um arquivo regular (não diretório)
    """
    nomes_identificados: List[str] = []
    for nome_de_entrada in os.listdir(caminho_diretorio):
        caminho_completo = os.path.join(caminho_diretorio, nome_de_entrada)
        if not os.path.isfile(caminho_completo):
            continue
        nome_minusculo = nome_de_entrada.lower()
        if (
            "jetbrains" in nome_minusculo
            and "terminal" in nome_minusculo
            and "history" in nome_minusculo
            and "pessoal-history" in nome_minusculo
        ):
            nomes_identificados.append(nome_de_entrada)
    return nomes_identificados


def remover_arquivos(caminho_diretorio: str, nomes_para_apagar: Iterable[str]) -> None:
    for nome_arquivo in nomes_para_apagar:
        caminho_alvo = os.path.join(caminho_diretorio, nome_arquivo)
        try:
            os.remove(caminho_alvo)
            print(f"Removido: {nome_arquivo}")
        except Exception as erro:  # noqa: BLE001
            print(f"Falha ao remover {nome_arquivo}: {erro}")


def caminho_padrao_projeto(atual: str) -> str:
    # Considera que este script está em <repo>/tools; o alvo padrão é o diretório pai
    return os.path.abspath(os.path.join(atual, os.pardir))


def main() -> int:
    # Descobre diretório alvo: argumento 1 ou pai do diretório deste script
    diretorio_alvo = caminho_padrao_projeto(os.path.dirname(__file__))
    argumentos = sys.argv[1:]
    if argumentos and not argumentos[0].startswith("-"):
        diretorio_alvo = os.path.abspath(argumentos[0])
        argumentos = argumentos[1:]

    arquivos_encontrados = listar_arquivos_jetbrains_no_diretorio(diretorio_alvo)

    if not arquivos_encontrados:
        print("Nenhum arquivo de histórico do JetBrains encontrado no diretório alvo.")
        return 0

    print("Arquivos identificados para remoção:")
    for nome in arquivos_encontrados:
        print(f" - {nome}")

    execucao_confirmada = (
        "--confirmar" in argumentos
        or os.environ.get("FORCAR_APAGAR", "").lower() in {"1", "true", "yes", "sim"}
    )

    if not execucao_confirmada:
        print("\nExecução em modo seguro: nada foi apagado.")
        print("Dica: passe --confirmar ou defina FORCAR_APAGAR=1 para executar a exclusão.")
        return 0

    print("\nRemovendo arquivos...")
    remover_arquivos(diretorio_alvo, arquivos_encontrados)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

