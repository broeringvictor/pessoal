from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from typing import Iterable, List, Optional, Tuple

import pandas as pd
import tabula



@dataclass(frozen=True)
class ParametrosExtracao:
    indice_cabecalho: int | None = None
    primeira_linha_dados: int | None = None
    palavras_chave: tuple[str, ...] = ("Data", "Documento", "Número", "Referência")
    auto_detectar_indices: bool = True


# Camada de acesso
def carregar_tabelas_pdf(caminho_pdf: str) -> List[pd.DataFrame]:
    try:
        tabelas = tabula.read_pdf(caminho_pdf, pages="all", multiple_tables=True)
    except Exception as e:
        # Fornece mensagem mais clara quando Java/tabula não está disponível
        raise RuntimeError(
            "Falha ao ler PDF com tabula. Verifique se o Java está instalado e acessível no PATH."
        ) from e
    return [t for t in tabelas if isinstance(t, pd.DataFrame)]


# Localização da tabela alvo
def localizar_tabela_com_palavras_chave(
    tabelas: Iterable[pd.DataFrame], palavras_chave: Iterable[str]
) -> Optional[pd.DataFrame]:
    chaves = list(palavras_chave)
    for tabela in tabelas:
        for _, linha in tabela.iterrows():
            linha_txt = " ".join(linha.astype(str))
            if all(p in linha_txt for p in chaves):
                return tabela
    return None


# Utilitários internos
def _sem_acentos_minusculo(s: str) -> str:
    s = unicodedata.normalize("NFKD", s)
    s = "".join(ch for ch in s if not unicodedata.combining(ch))
    return s.lower()


def detectar_indices_cabecalho_e_dados(
    df: pd.DataFrame, fallback: Tuple[int, int] = (4, 5)
) -> Tuple[int, int]:
    termos = ["data", "documento", "numero", "referencia"]
    try:
        for i, (_, linha) in enumerate(df.iterrows()):
            txt = _sem_acentos_minusculo(" ".join(linha.astype(str)))
            if all(t in txt for t in termos):
                if i + 1 < len(df):
                    return i, i + 1
                break
    except Exception:
        pass
    return fallback


def aplicar_cabecalho_da_linha(df: pd.DataFrame, indice_cabecalho: int) -> pd.DataFrame:
    out = df.copy()
    out.columns = out.iloc[indice_cabecalho]
    return out


def selecionar_linhas_de_dados(df: pd.DataFrame, indice_inicio: int) -> pd.DataFrame:
    return df.iloc[indice_inicio:].reset_index(drop=True).copy()


# Detecta a coluna composta mesmo se o Tabula dividir em várias colunas
def encontrar_coluna_composta(dados: pd.DataFrame) -> Tuple[pd.Series, List[int]]:
    padrao = re.compile(
        r"^(?P<Data>\d{2}/\d{2}/\d{4})\s+(?P<Documento>\d{4,}-\d+)\s+(?P<N1>\d+)\s+(?P<N2>\d+)$"
    )

    def score(series: pd.Series) -> int:
        s = series.astype(str).str.replace(r"\s+", " ", regex=True).str.strip()
        m = s.str.match(padrao)
        return int(m.fillna(False).sum())

    ncols = dados.shape[1]
    candidatas: list[Tuple[pd.Series, List[int], int]] = []

    # Testa colunas individuais
    for i in range(ncols):
        serie = dados.iloc[:, i]
        candidatas.append((serie, [i], score(serie)))

    # Testa combinações col0+col1, col0+col1+col2 (mais comuns)
    if ncols >= 2:
        s01 = dados.iloc[:, 0].astype(str) + " " + dados.iloc[:, 1].astype(str)
        candidatas.append((s01, [0, 1], score(s01)))
    if ncols >= 3:
        s012 = (
            dados.iloc[:, 0].astype(str)
            + " "
            + dados.iloc[:, 1].astype(str)
            + " "
            + dados.iloc[:, 2].astype(str)
        )
        candidatas.append((s012, [0, 1, 2], score(s012)))

    # Escolhe a de maior score; em empate, preferir a que consome menos colunas
    candidatas.sort(key=lambda t: (t[2], -len(t[1])), reverse=True)
    melhor = candidatas[0]

    # Normaliza a série escolhida
    serie_melhor = (
        melhor[0].astype(str).str.replace(r"\s+", " ", regex=True).str.strip()
    )
    return serie_melhor, melhor[1]


def decompor_coluna_composta_em_campos(coluna: pd.Series) -> pd.DataFrame:
    serie = coluna.astype(str).str.replace(r"\s+", " ", regex=True).str.strip()
    padrao = re.compile(
        r"^(?P<Data>\d{2}/\d{2}/\d{4})\s+(?P<Documento>\d{4,}-\d+)\s+(?P<N1>\d+)\s+(?P<N2>\d+)$"
    )
    extraido = serie.str.extract(padrao)

    if extraido.isna().all(axis=None):
        partes = serie.str.split(r"\s+", n=3, expand=True)
        partes.columns = ["Data", "Documento", "N1N2_1", "N1N2_2"]
        partes["N1"] = partes["N1N2_1"].fillna("")
        partes["N2"] = partes["N1N2_2"].fillna("")
        extraido = partes[["Data", "Documento", "N1", "N2"]]

    num_ref = (extraido["N1"].fillna("") + " " + extraido["N2"].fillna("")).str.strip()
    return pd.DataFrame(
        {
            "Data": extraido["Data"],
            "Documento": extraido["Documento"],
            "Número-Referência e Unidade-Consumidora": num_ref,
        }
    )


def normalizar_nomes_colunas_alvo(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    mapa_norm: dict[str, str] = {}
    for c in out.columns:
        c_str = str(c)
        c_norm = _sem_acentos_minusculo(c_str)
        # remove tudo que não é letra para comparação exata
        c_key = re.sub(r"[^a-z]", "", c_norm)
        if c_key == "referencia" and c_str != "Referência":
            mapa_norm[c] = "Referência"
        elif c_key == "vencimento" and c_str != "Vencimento":
            mapa_norm[c] = "Vencimento"
        elif c_key in ("totalapagar", "totalapagarrs") and c_str != "Total a Pagar (R$)":
            mapa_norm[c] = "Total a Pagar (R$)"
    if mapa_norm:
        out = out.rename(columns=mapa_norm)
    return out


def renomear_total_para_valor_total(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    rename_map: dict[str, str] = {}
    for c in out.columns:
        if isinstance(c, str) and "Total a Pagar" in c:
            rename_map[c] = "Valor Total"
    if rename_map:
        out = out.rename(columns=rename_map)
    if "Valor Total" in out.columns:
        out["Valor Total"] = (
            out["Valor Total"].astype(str).str.replace("R$", "", regex=False).str.strip()
        )
    return out


def montar_tabela_celesc(
    tabela_bruta: pd.DataFrame,
    params: ParametrosExtracao | None = None,
) -> pd.DataFrame:
    params = params or ParametrosExtracao()

    # Detectar índices se necessário
    if (
        params.auto_detectar_indices
        or params.indice_cabecalho is None
        or params.primeira_linha_dados is None
    ):
        idx_header, idx_data = detectar_indices_cabecalho_e_dados(tabela_bruta)
    else:
        idx_header = int(params.indice_cabecalho)
        idx_data = int(params.primeira_linha_dados)

    com_cabecalho = aplicar_cabecalho_da_linha(tabela_bruta, idx_header)
    dados = selecionar_linhas_de_dados(com_cabecalho, idx_data)

    # Encontrar a coluna composta dinamicamente
    col_composta, cols_consumidas = encontrar_coluna_composta(dados)
    esquerda = decompor_coluna_composta_em_campos(col_composta)

    # Preservar demais colunas não consumidas
    restantes = [i for i in range(dados.shape[1]) if i not in cols_consumidas]
    direita = dados.iloc[:, restantes].copy()

    final = pd.concat([esquerda, direita], axis=1)

    # Limpezas
    if "Data" in final.columns:
        final = final[~final["Data"].isna()].reset_index(drop=True)

    final = normalizar_nomes_colunas_alvo(final)
    final = renomear_total_para_valor_total(final)
    return final


def extrair_tabela_celesc(
    caminho_pdf: str,
    params: ParametrosExtracao | None = None,
) -> pd.DataFrame:
    tabelas = carregar_tabelas_pdf(caminho_pdf)
    params = params or ParametrosExtracao()
    tabela_alvo = localizar_tabela_com_palavras_chave(tabelas, params.palavras_chave)
    if tabela_alvo is None:
        raise ValueError("Tabela com as palavras-chave não foi encontrada no PDF fornecido.")
    return montar_tabela_celesc(tabela_alvo, params)


def obter_tabela_celesc(caminho_pdf: str) -> pd.DataFrame:
    """
    Uso simples: informe o caminho do PDF e receba a tabela final pronta.
    Não imprime, não salva CSV, apenas retorna o DataFrame para reuso.
    """
    return extrair_tabela_celesc(caminho_pdf)


# Validação e Runner de alto nível
def validar_tabela_celesc(df: pd.DataFrame) -> None:
    colunas_requeridas = {
        "Data",
        "Documento",
        "Número-Referência e Unidade-Consumidora",
        "Referência",
        "Vencimento",
        "Valor Total",
    }
    faltando = colunas_requeridas - set(df.columns.astype(str))
    if faltando:
        raise AssertionError(f"Colunas faltando: {faltando}")
    if len(df) == 0:
        raise AssertionError("Tabela vazia")
    if not df["Valor Total"].astype(str).str.contains(",").any():
        raise AssertionError("'Valor Total' sem vírgula")


def run_extraction(
    pdf_path: str,
    out_csv: str | None = None,
    imprimir_resumo: bool = True,
    validar: bool = True,
) -> pd.DataFrame:
    """
    API de alto nível para extração:
    - extrai a tabela Celesc do PDF
    - opcionalmente imprime resumo e salva CSV
    - valida colunas essenciais, se solicitado
    """
    df = extrair_tabela_celesc(pdf_path)

    if validar:
        validar_tabela_celesc(df)

    if imprimir_resumo:
        print("Colunas:", list(df.columns))
        print("Linhas:", len(df))
        print("Prévia:")
        with pd.option_context("display.max_columns", None, "display.width", 200):
            print(df.head(5))

    if out_csv:
        from pathlib import Path as _Path
        p = _Path(out_csv)
        p.parent.mkdir(parents=True, exist_ok=True)
        df.to_csv(p, index=False, encoding="utf-8")
        print(f"CSV salvo em: {p}")

    return df


if __name__ == "__main__":
    from pathlib import Path

    # Caminho robusto para o PDF dentro de core/assets
    pdf_path = Path(__file__).resolve().parents[1] / "assets" / "fatura-luz.pdf"
    # Executa a extração com um resumo impresso; sem salvar CSV por padrão
    run_extraction(str(pdf_path), out_csv=None, imprimir_resumo=True, validar=True)
