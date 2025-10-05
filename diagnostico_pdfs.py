#!/usr/bin/env python3
"""
Script de diagnóstico para testar todos os PDFs e identificar problemas
"""
from pathlib import Path
import sys
sys.path.append(str(Path(__file__).parent))

from core.celesc.celesc_extrator import carregar_tabelas_pdf, localizar_tabela_com_palavras_chave

def diagnosticar_pdf(pdf_path: Path):
    print(f"\n{'='*60}")
    print(f"TESTANDO: {pdf_path.name}")
    print(f"{'='*60}")
    
    if not pdf_path.exists():
        print(f"❌ ERRO: Arquivo não existe: {pdf_path}")
        return
    
    try:
        # Teste 1: Carregamento de tabelas
        print("1. Carregando tabelas do PDF...")
        tabelas = carregar_tabelas_pdf(str(pdf_path))
        print(f"   ✅ {len(tabelas)} tabelas encontradas")
        
        if not tabelas:
            print("   ❌ PROBLEMA: Nenhuma tabela encontrada no PDF")
            return
            
        # Teste 2: Mostrar estrutura de cada tabela
        for i, tabela in enumerate(tabelas):
            print(f"\n   Tabela {i+1}: {tabela.shape[0]} linhas x {tabela.shape[1]} colunas")
            print(f"   Primeiras 3 linhas:")
            for j in range(min(3, len(tabela))):
                linha_str = " | ".join(str(v) for v in tabela.iloc[j].values)
                print(f"     Linha {j}: {linha_str[:120]}...")
        
        # Teste 3: Buscar palavras-chave
        print(f"\n2. Procurando tabela com palavras-chave: Data, Documento, Número, Referência")
        palavras_chave = ("Data", "Documento", "Número", "Referência")
        tabela_alvo = localizar_tabela_com_palavras_chave(tabelas, palavras_chave)
        
        if tabela_alvo is not None:
            print(f"   ✅ Tabela com palavras-chave ENCONTRADA!")
            print(f"   Formato: {tabela_alvo.shape[0]} linhas x {tabela_alvo.shape[1]} colunas")
        else:
            print(f"   ❌ PROBLEMA: Tabela com palavras-chave NÃO ENCONTRADA")
            print(f"   Vamos procurar manualmente por cada palavra...")
            
            for palavra in palavras_chave:
                encontrou = False
                for i, tabela in enumerate(tabelas):
                    for _, linha in tabela.iterrows():
                        linha_txt = " ".join(linha.astype(str))
                        if palavra in linha_txt:
                            print(f"     '{palavra}' encontrada na tabela {i+1}")
                            encontrou = True
                            break
                    if encontrou:
                        break
                if not encontrou:
                    print(f"     '{palavra}' NÃO ENCONTRADA em nenhuma tabela")
        
    except Exception as e:
        print(f"❌ ERRO durante processamento: {type(e).__name__}: {e}")

def main():
    assets_dir = Path(__file__).parent / "core" / "assets"
    pdfs = list(assets_dir.glob("*.pdf"))
    
    print(f"Encontrados {len(pdfs)} arquivos PDF em {assets_dir}")
    
    for pdf_path in sorted(pdfs):
        diagnosticar_pdf(pdf_path)
    
    print(f"\n{'='*60}")
    print("DIAGNÓSTICO CONCLUÍDO")
    print(f"{'='*60}")

if __name__ == "__main__":
    main()
