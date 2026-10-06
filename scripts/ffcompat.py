"""Compatibilidade de ffmpeg: o 7+ trocou -filter_complex_script por -/filter_complex (o 8 removeu a opção antiga)."""
import functools, re, subprocess


@functools.lru_cache(maxsize=1)
def _major():
    try:
        out = subprocess.run(['ffmpeg', '-version'], capture_output=True, text=True).stdout
        m = re.search(r'ffmpeg version n?(\d+)', out)
        return int(m.group(1)) if m else 0
    except Exception:
        return 0


def opcao_script():
    """Nome da opção que lê o grafo de filtros de um arquivo, conforme a versão instalada."""
    return '-/filter_complex' if _major() >= 7 else '-filter_complex_script'
