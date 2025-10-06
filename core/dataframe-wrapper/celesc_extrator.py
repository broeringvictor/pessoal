from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from typing import Iterable, List, Optional, Tuple, Protocol

import pandas as pd
from dataframe_wrapper import DataFrameWrapper


# Porta para inversão de dependência (SOLID - DIP)
class TabelaPdfExtratora(Protocol):
    def carregar_tabelas_pdf(self, file_path: Optional[str] = None) -> List[pd.DataFrame]:
        ...

    def localizar_tabela_com_palavras_chave(
        self,
        tabelas: Iterable[pd.DataFrame],
        palavras_chave: Iterable[str],
        *,
        normalizar: bool = True,
        exigir_todas: bool = True,
    ) -> Optional[pd.DataFrame]:
        ...


@dataclass(frozen=True)
class ParametrosExtracao:
    indice_cabecalho: int | None = None
    primeira_linha_dados: int | None = None
    palavras_chave: tuple[str, ...] = ("Data", "Documento", "Número", "Referência")
    auto_detectar_indices: bool = True


class CelescExtrator:
    """Extrai a tabela principal das faturas CELESC e normaliza colunas essenciais."""

    def __init__(
        self,
        caminho_pdf: str,
        *,
        params: ParametrosExtracao | None = None,
        wrapper: Optional[TabelaPdfExtratora] = None,
        pages: str = "all",
        multiple_tables: bool = True,
        stream: bool = True,
        lattice: bool = False,
    ) -> None:
        self._caminho_pdf = caminho_pdf
        self.params = params or ParametrosExtracao()
        self.wrapper: TabelaPdfExtratora = wrapper or DataFrameWrapper(
            file_path=caminho_pdf,
            pages=pages,
            multiple_tables=multiple_tables,
            stream=stream,
            lattice=lattice,
        )
        self.tabela_final: pd.DataFrame = self._extrair()

    # --- Orquestração -----------------------------------------------------
    def _extrair(self) -> pd.DataFrame:
        tabelas = self.wrapper.carregar_tabelas_pdf(self._caminho_pdf)
        tabela_alvo = self.wrapper.localizar_tabela_com_palavras_chave(
            tabelas,
            self.params.palavras_chave,
            normalizar=True,
            exigir_todas=True,
        )
        if tabela_alvo is None:
            raise ValueError("Tabela com as palavras-chave não foi encontrada no PDF fornecido.")
        return self._montar_tabela_celesc(tabela_alvo, self.params)

    # --- Passos do domínio ------------------------------------------------
    def _montar_tabela_celesc(
        self,
        tabela_bruta: pd.DataFrame,
        params: ParametrosExtracao,
    ) -> pd.DataFrame:
        # Detectar índices se necessário
        if (
            params.auto_detectar_indices
            or params.indice_cabecalho is None
            or params.primeira_linha_dados is None
        ):
            indice_cabecalho, indice_primeira_linha = self._detectar_indices_cabecalho_e_dados(tabela_bruta)
        else:
            indice_cabecalho = int(params.indice_cabecalho)
            indice_primeira_linha = int(params.primeira_linha_dados)

        com_cabecalho = self._aplicar_cabecalho_da_linha(tabela_bruta, indice_cabecalho)
        dados = self._selecionar_linhas_de_dados(com_cabecalho, indice_primeira_linha)

        # Encontrar a coluna composta dinamicamente
        coluna_composta_normalizada, indices_colunas_consumidas = self._encontrar_coluna_composta(dados)
        bloco_esquerda = self._decompor_coluna_composta_em_campos(coluna_composta_normalizada)

        # Preservar demais colunas não consumidas
        colunas_restantes = [i for i in range(dados.shape[1]) if i not in indices_colunas_consumidas]
        bloco_direita = dados.iloc[:, colunas_restantes].copy()

        tabela_final = pd.concat([bloco_esquerda, bloco_direita], axis=1)

        # Limpezas
        if "Data" in tabela_final.columns:
            tabela_final = tabela_final[~tabela_final["Data"].isna()].reset_index(drop=True)

        tabela_final = self._normalizar_nomes_colunas_alvo(tabela_final)
        tabela_final = self._renomear_total_para_valor_total(tabela_final)
        return tabela_final

    # --- Utilitários internos --------------------------------------------
    @staticmethod
    def _sem_acentos_minusculo(texto: str) -> str:
        texto_normalizado = unicodedata.normalize("NFKD", texto)
        texto_sem_acentos = "".join(ch for ch in texto_normalizado if not unicodedata.combining(ch))
        return texto_sem_acentos.lower()

    def _detectar_indices_cabecalho_e_dados(
        self, df: pd.DataFrame, fallback: Tuple[int, int] = (4, 5)
    ) -> Tuple[int, int]:
        termos_cabecalho = ["data", "documento", "numero", "referencia"]
        try:
            for indice, (_, linha) in enumerate(df.iterrows()):
                linha_texto_normalizado = self._sem_acentos_minusculo(" ".join(linha.astype(str)))
                if all(termo in linha_texto_normalizado for termo in termos_cabecalho):
                    if indice + 1 < len(df):
                        return indice, indice + 1
                    break
        except Exception:
            pass
        return fallback

    @staticmethod
    def _aplicar_cabecalho_da_linha(df: pd.DataFrame, indice_cabecalho: int) -> pd.DataFrame:
        out = df.copy()
        out.columns = out.iloc[indice_cabecalho]
        return out

    @staticmethod
    def _selecionar_linhas_de_dados(df: pd.DataFrame, indice_inicio: int) -> pd.DataFrame:
        return df.iloc[indice_inicio:].reset_index(drop=True).copy()

    def _encontrar_coluna_composta(self, dados: pd.DataFrame) -> Tuple[pd.Series, List[int]]:
        padrao_coluna_composta = re.compile(
            r"^(?P<Data>\d{2}/\d{2}/\d{4})\s+(?P<Documento>\d{4,}-\d+)\s+(?P<N1>\d+)\s+(?P<N2>\d+)$"
        )

        def pontuacao_coluna(coluna: pd.Series) -> int:
            texto_normalizado = coluna.astype(str).str.replace(r"\s+", " ", regex=True).str.strip()
            mascara_casamento = texto_normalizado.str.match(padrao_coluna_composta)
            return int(mascara_casamento.fillna(False).sum())

        quantidade_colunas = dados.shape[1]
        candidatas: list[Tuple[pd.Series, List[int], int]] = []

        # Testa colunas individuais
        for indice_coluna in range(quantidade_colunas):
            serie_coluna = dados.iloc[:, indice_coluna]
            candidatas.append((serie_coluna, [indice_coluna], pontuacao_coluna(serie_coluna)))

        # Testa combinações col0+col1, col0+col1+col2 (mais comuns)
        if quantidade_colunas >= 2:
            concat_01 = dados.iloc[:, 0].astype(str) + " " + dados.iloc[:, 1].astype(str)
            candidatas.append((concat_01, [0, 1], pontuacao_coluna(concat_01)))
        if quantidade_colunas >= 3:
            concat_012 = (
                dados.iloc[:, 0].astype(str)
                + " "
                + dados.iloc[:, 1].astype(str)
                + " "
                + dados.iloc[:, 2].astype(str)
            )
            candidatas.append((concat_012, [0, 1, 2], pontuacao_coluna(concat_012)))

        # Escolhe a de maior score; em empate, preferir a que consome menos colunas
        candidatas.sort(key=lambda tpl: (tpl[2], -len(tpl[1])), reverse=True)
        melhor_candidata = candidatas[0]

        # Normaliza a série escolhida
        serie_escolhida_normalizada = (
            melhor_candidata[0].astype(str).str.replace(r"\s+", " ", regex=True).str.strip()
        )
        return serie_escolhida_normalizada, melhor_candidata[1]

    @staticmethod
    def _decompor_coluna_composta_em_campos(coluna: pd.Series) -> pd.DataFrame:
        texto_normalizado = coluna.astype(str).str.replace(r"\s+", " ", regex=True).str.strip()
        padrao_coluna_composta = re.compile(
            r"^(?P<Data>\d{2}/\d{2}/\d{4})\s+(?P<Documento>\d{4,}-\d+)\s+(?P<N1>\d+)\s+(?P<N2>\d+)$"
        )
        extraido = texto_normalizado.str.extract(padrao_coluna_composta)

        if extraido.isna().all(axis=None):
            partes = texto_normalizado.str.split(r"\s+", n=3, expand=True)
            partes.columns = ["Data", "Documento", "N1N2_1", "N1N2_2"]
            partes["N1"] = partes["N1N2_1"].fillna("")
            partes["N2"] = partes["N1N2_2"].fillna("")
            extraido = partes[["Data", "Documento", "N1", "N2"]]

        numero_referencia = (extraido["N1"].fillna("") + " " + extraido["N2"].fillna("")).str.strip()
        return pd.DataFrame(
            {
                "Data": extraido["Data"],
                "Documento": extraido["Documento"],
                "Número-Referência e Unidade-Consumidora": numero_referencia,
            }
        )

    def _normalizar_nomes_colunas_alvo(self, df: pd.DataFrame) -> pd.DataFrame:
        out = df.copy()
        mapa_renomeio: dict[str, str] = {}
        for coluna in out.columns:
            nome_original = str(coluna)
            nome_normalizado = self._sem_acentos_minusculo(nome_original)
            # remove tudo que não é letra para comparação exata
            chave_comparacao = re.sub(r"[^a-z]", "", nome_normalizado)
            if chave_comparacao == "referencia" and nome_original != "Referência":
                mapa_renomeio[coluna] = "Referência"
            elif chave_comparacao == "vencimento" and nome_original != "Vencimento":
                mapa_renomeio[coluna] = "Vencimento"
            elif chave_comparacao in ("totalapagar", "totalapagarrs") and nome_original != "Total a Pagar (R$)":
                mapa_renomeio[coluna] = "Total a Pagar (R$)"
        if mapa_renomeio:
            out = out.rename(columns=mapa_renomeio)
        return out

    @staticmethod
    def _renomear_total_para_valor_total(df: pd.DataFrame) -> pd.DataFrame:
        out = df.copy()
        mapa_renomeio_total: dict[str, str] = {}
        for coluna in out.columns:
            if isinstance(coluna, str) and "Total a Pagar" in coluna:
                mapa_renomeio_total[coluna] = "Valor Total"
        if mapa_renomeio_total:
            out = out.rename(columns=mapa_renomeio_total)
        if "Valor Total" in out.columns:
            out["Valor Total"] = (
                out["Valor Total"].astype(str).str.replace("R$", "", regex=False).str.strip()
            )
        return out


# --- API de módulo (compatível) -------------------------------------------

def extrair_tabela_celesc(
    caminho_pdf: str,
    params: ParametrosExtracao | None = None,
) -> pd.DataFrame:
    extrator = CelescExtrator(caminho_pdf, params=params)
    return extrator.tabela_final


def obter_tabela_celesc(caminho_pdf: str) -> pd.DataFrame:
    """Retorna a tabela CELESC do PDF informado."""
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
    """Extrai, valida e opcionalmente imprime/salva o resultado em CSV."""
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
        from pathlib import Path
        caminho_saida = Path(out_csv)
        caminho_saida.parent.mkdir(parents=True, exist_ok=True)
        df.to_csv(caminho_saida, index=False, encoding="utf-8")
        print(f"CSV salvo em: {caminho_saida}")

    return df


if __name__ == "__main__":
    from pathlib import Path

    # Diretório com todas as faturas (sempre relativo a este arquivo)
    base_dir = Path(__file__).resolve().parent  # core/dataframe-wrapper
    assets_dir = base_dir.parent / "assets"     # core/assets

    # Busca somente no nível superior de core/assets
    pdfs = list(assets_dir.glob("*.pdf"))
    
    if not pdfs:
        print(f"Nenhum PDF encontrado em: {assets_dir}")
    else:
        print(f"Encontrados {len(pdfs)} PDF(s) para processar em {assets_dir}:")
        
        for pdf_path in sorted(pdfs):
            print(f"\n{'='*50}")
            print(f"Processando: {pdf_path.name}")
            print(f"{'='*50}")
            
            try:
                run_extraction(str(pdf_path), out_csv=None, imprimir_resumo=True, validar=True)
            except Exception as e:
                print(f"ERRO ao processar {pdf_path.name}: {e}")
                continue
