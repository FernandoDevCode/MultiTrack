from __future__ import annotations


SUPPORTED_INPUT_SUFFIXES = frozenset(
    {".wav", ".flac", ".mp3", ".m4a", ".aac", ".ogg"}
)


def supported_input_filter() -> str:
    suffixes = " ".join(f"*{suffix}" for suffix in sorted(SUPPORTED_INPUT_SUFFIXES))
    return f"Áudio suportado ({suffixes});;Todos os arquivos (*)"
