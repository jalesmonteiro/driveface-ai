"""Serviços de exportação de fotos em buffer de memória volátil (io.BytesIO)."""
import io
import zipfile


class ExportService:
    @staticmethod
    def create_zip_stream(files_generator):
        """Gera um buffer de streaming ZIP a partir de gerador de arquivos (filename, BytesIO)."""
        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as zf:
            for filename, content in files_generator:
                zf.writestr(filename, content.read())
        buffer.seek(0)
        return buffer
