
@staticmethod
class UploadPDF:
    def expand_to_pdf_files(path_texts: Sequence[str], recursive: bool) -> List[str]:
        arquivos: List[str] = []
    for texto in path_texts:
        normalizado = _normalize_path_text(texto)
        if _has_wildcards(normalizado):
            resultados = glob.glob(normalizado, recursive=True)
            for encontrado in sorted(resultados):
                caminho_encontrado = Path(encontrado)
                if caminho_encontrado.is_file() and caminho_encontrado.suffix.lower() == ".pdf":
                    arquivos.append(str(caminho_encontrado.resolve()))
            continue
        caminho = Path(normalizado)
        if caminho.is_dir():
            padrao = "**/*.pdf" if recursive else "*.pdf"
            encontrados = [str(p.resolve()) for p in sorted(caminho.glob(padrao))]
            arquivos.extend(encontrados)
        else:
            if normalizado.lower().endswith(".pdf") and caminho.exists():
                arquivos.append(str(caminho.resolve()))
    vistos: set[str] = set()
    unicos: List[str] = []
    for caminho in arquivos:
        if caminho not in vistos:
            vistos.add(caminho)
            unicos.append(caminho)
    return unicos

    def persistir_uploads_em_temporarios(arquivos_upload: List[UploadFile]) -> tuple[List[str], List[str]]:
        """Valida os uploads e persiste em arquivos temporários .pdf, retornando (caminhos_válidos, nomes_inválidos)."""
        caminhos_temporarios: List[str] = []
        arquivos_invalidos: List[str] = []
        for arquivo in arquivos_upload:
            nome_original = arquivo.filename or "arquivo_sem_nome.pdf"
            if arquivo.content_type not in {"application/pdf", "application/octet-stream"} and not nome_original.lower().endswith(".pdf"):
                arquivos_invalidos.append(nome_original)
                continue
            try:
                with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as temporario:
                    destino_buffer: BinaryIO = cast(BinaryIO, temporario)
                    shutil.copyfileobj(arquivo.file, destino_buffer)
                    caminhos_temporarios.append(temporario.name)
            finally:
                with contextlib.suppress(Exception):
                    arquivo.file.close()
        return caminhos_temporarios, arquivos_invalidos
    
    def sincronizar_contas_a_partir_de_pdfs(caminhos_temporarios: List[str]) -> dict:
        """Orquestra a sincronização no domínio e retorna o resumo produzido pelo serviço."""
        try:
            with get_database_session() as session:
                repositorio = ContaAguaRepository(session)
                servico = ContaAguaSyncService(repositorio)
                comando = ImportarContaAguaCommand(caminhos_arquivos_pdf=caminhos_temporarios)
                resumo = servico.sync_from_pdfs(comando.caminhos_arquivos_pdf)
                return resumo
        except OperationalError as err:
            app_logger.exception("Database connectivity error during SAMAE upload sync")
            raise HTTPException(status_code=503, detail="Database unavailable or unreachable.") from err
        except ProgrammingError as err:
            app_logger.exception("Database schema error during SAMAE upload sync (missing tables?)")
            raise HTTPException(
                status_code=500,
                detail=(
                    "Database schema missing. Run migrations: 'uv run alembic upgrade head' or set INIT_DB_SCHEMA=1 once."
                ),
            ) from err