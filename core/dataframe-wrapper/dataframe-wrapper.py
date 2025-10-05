import pandas as pd

class DataFrameWrapper:
    """"
    Responsável por transformar arquivos de dados em dataframes do pandas para serem manipulados.

    """
    def __init__(self, dataframe):
        self.dataframe = dataframe
        
    def pdf_to_parquet(self, path):
        
        
        