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
        """
        Carrega todas as tabelas de um PDF usando as opções configuradas.
        Args:
            file_path: caminho do PDF; se None, usa self.file_path.
        Returns:
            Lista de DataFrames encontrados.
        """
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

    def localizar_tabela_com_palavras_chave(
        self,
        tabelas: Iterable[pd.DataFrame],
        palavras_chave: Iterable[str],
        *,
        normalizar: bool = True,
        exigir_todas: bool = True,
    ) -> Optional[pd.DataFrame]:
        """
        Localiza a primeira tabela cujo texto de alguma linha contenha as palavras-chave.
        Args:
            tabelas: iterável de DataFrames extraídos.
            palavras_chave: termos a procurar.
            normalizar: se True, ignora acentos e caixa (minúsculas).
            exigir_todas: se True, exige que todas as palavras apareçam; caso contrário, qualquer uma.
        """
        chaves = list(palavras_chave)
        if normalizar:
            chaves = [self._sem_acentos_minusculo(p) for p in chaves]

        for tabela in tabelas:
            for _, linha in tabela.iterrows():
                linha_txt = " ".join(linha.astype(str))
                if normalizar:
                    linha_txt = self._sem_acentos_minusculo(linha_txt)
                cond = all(p in linha_txt for p in chaves) if exigir_todas else any(p in linha_txt for p in chaves)
                if cond:
                    return tabela
        return None

    @staticmethod
    def _sem_acentos_minusculo(s: str) -> str:
        s = unicodedata.normalize("NFKD", s)
        s = "".join(ch for ch in s if not unicodedata.combining(ch))
        return s.lower()

if __name__ == "__main__":
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
