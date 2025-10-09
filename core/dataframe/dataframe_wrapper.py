import os
import pandas as pd
import tabula
import unicodedata
from dataclasses import dataclass
from typing import Iterable, List, Optional

@dataclass
class DataFrameWrapper:
    file_path: Optional[str] = None
    pages: str = "all"
    multiple_tables: bool = True
    stream: bool = True
    lattice: bool = False

    def carregar_tabelas_pdf(self, file_path: Optional[str] = None) -> List[pd.DataFrame]:
        """Carrega todas as tabelas de um PDF conforme as opções configuradas."""
        path = file_path or self.file_path
        if not path:
            raise ValueError("Nenhum caminho de PDF foi fornecido.")
        if not os.path.exists(path):
            raise FileNotFoundError(f"Arquivo PDF não encontrado: {path}")

        try:
            tabelas = tabula.read_pdf(
                path,
                pages=self.pages,
                multiple_tables=self.multiple_tables,
                stream=self.stream,
                lattice=self.lattice,
            )
        except Exception as e:
            raise RuntimeError(
                "Falha ao ler o PDF com tabula. Verifique se o Java está instalado e acessível no PATH."
            ) from e

        return [tabela for tabela in tabelas if isinstance(tabela, pd.DataFrame)]

    def carregar_tabelas_csv(self, file_path: Optional[str] = None) -> List[pd.DataFrame]:
        """Carrega tabela de um arquivo CSV usando pandas."""
        path = file_path or self.file_path
        if not path:
            raise ValueError("Nenhum caminho de CSV foi fornecido.")
        if not os.path.exists(path):
            raise FileNotFoundError(f"Arquivo CSV não encontrado: {path}")

        try:
            # Usa pandas para ler CSV, não tabula (que é específico para PDFs)
            dataframe_csv = pd.read_csv(path)
            return [dataframe_csv]  # Retorna como lista para consistência com a interface
        except Exception as e:
            raise RuntimeError(
                "Falha ao ler o arquivo CSV. Verifique o formato e encoding do arquivo."
            ) from e

    def localizar_tabela_com_palavras_chave(
        self,
        tabelas: Iterable[pd.DataFrame],
        palavras_chave: Iterable[str],
        *,
        normalizar: bool = True,
        exigir_todas: bool = True,
    ) -> Optional[pd.DataFrame]:
        """Retorna a primeira tabela cujo texto contenha as palavras-chave."""
        lista_palavras = list(palavras_chave)
        if normalizar:
            lista_palavras = [self._sem_acentos_minusculo(palavra) for palavra in lista_palavras]

        for tabela in tabelas:
            for _, linha in tabela.iterrows():
                linha_texto = " ".join(linha.astype(str))
                if normalizar:
                    linha_texto = self._sem_acentos_minusculo(linha_texto)
                condicao_atendida = (
                    all(palavra in linha_texto for palavra in lista_palavras)
                    if exigir_todas
                    else any(palavra in linha_texto for palavra in lista_palavras)
                )
                if condicao_atendida:
                    return tabela
        return None

    @staticmethod
    def _sem_acentos_minusculo(texto: str) -> str:
        texto_normalizado = unicodedata.normalize("NFKD", texto)
        texto_sem_acentos = "".join(
            caractere for caractere in texto_normalizado if not unicodedata.combining(caractere)
        )
        return texto_sem_acentos.lower()

if __name__ == "__main__":
    def samae():
        try:
            pdf_agua = os.path.normpath(
                os.path.join(os.path.dirname(__file__), "..", "assets", "samae", "segunda-via.pdf")
            )
            wrapper = DataFrameWrapper(file_path=pdf_agua, pages="all", multiple_tables=True, stream=True)
            dfs = wrapper.carregar_tabelas_pdf()
            for cada_tabela in dfs:
                print(cada_tabela)
        except FileNotFoundError as e:
            print(e)
        except (ValueError, RuntimeError) as e:
            print(f"Ocorreu um erro: {e}")

    # samae()

    def csv():
        try:
            caminho_csv_inter = os.path.normpath(
                os.path.join(os.path.dirname(__file__), "..", "assets", "cartao", "inter", "fatura-inter-2024-08.csv")
            )
            wrapper_inter = DataFrameWrapper(file_path=caminho_csv_inter)
            dataframes = wrapper_inter.carregar_tabelas_csv()

            for indice_data, dataframe_atual in enumerate(dataframes, start=1):
                print(f"DataFrame {indice_data}:")
                print(dataframe_atual.head())
                print(f"Shape: {dataframe_atual.shape}")
                print("-" * 50)

        except FileNotFoundError as erro_arquivo:
            print(f"Arquivo não encontrado: {erro_arquivo}")
        except (ValueError, RuntimeError) as erro_processamento:
            print(f"Erro ao processar CSV: {erro_processamento}")

    # csv()  # Descomente para testar manualmente
