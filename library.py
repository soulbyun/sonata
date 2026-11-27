import shutil
import subprocess
import uuid
from pathlib import Path

from mutagen import File
from mutagen.id3 import ID3
from mutagen.flac import FLAC
from mutagen.mp4 import MP4, MP4Cover

import db

RAIZ = Path(__file__).parent
PASTA_MUSICAS = RAIZ / "dados" / "musicas"
PASTA_CAPAS = RAIZ / "dados" / "capas"


def ler_tags(caminho):
    """Lê título, artista, álbum e duração (em segundos) do arquivo."""
    info = {"titulo": None, "artista": None, "album": None, "duracao": 0}
    try:
        audio = File(caminho, easy=True)
    except Exception:
        audio = None
    if audio is None:
        return info

    if audio.tags:
        info["titulo"] = (audio.tags.get("title") or [None])[0]
        info["artista"] = (audio.tags.get("artist") or [None])[0]
        info["album"] = (audio.tags.get("album") or [None])[0]
    info["duracao"] = int(round(audio.info.length))
    return info


def _ext_imagem(mime):
    return ".png" if mime and "png" in mime else ".jpg"


def extrair_capa(caminho):
    """Procura a capa dentro do arquivo. Devolve (bytes, extensão) ou None."""
    ext = Path(caminho).suffix.lower()
    try:
        if ext == ".mp3":
            for chave, frame in ID3(caminho).items():
                if chave.startswith("APIC"):
                    return frame.data, _ext_imagem(frame.mime)
        elif ext == ".flac":
            fotos = FLAC(caminho).pictures
            if fotos:
                return fotos[0].data, _ext_imagem(fotos[0].mime)
        elif ext in (".m4a", ".mp4"):
            capas = (MP4(caminho).tags or {}).get("covr")
            if capas:
                c = capas[0]
                ext_img = ".png" if c.imageformat == MP4Cover.FORMAT_PNG else ".jpg"
                return bytes(c), ext_img
    except Exception:
        pass
    return None


def converter_para_mp3(origem, destino, kbps=320):
    """Converte qualquer áudio para MP3 usando o ffmpeg."""
    comando = [
        "ffmpeg", "-y", "-i", str(origem),
        "-vn", "-map_metadata", "0",
        "-codec:a", "libmp3lame", "-b:a", f"{kbps}k",
        str(destino),
    ]
    try:
        resultado = subprocess.run(comando, capture_output=True, text=True)
    except FileNotFoundError:
        raise RuntimeError("ffmpeg não encontrado. Feche e abra o terminal e teste 'ffmpeg -version'.")
    if resultado.returncode != 0:
        raise RuntimeError("Falha ao converter:\n" + resultado.stderr[-500:])


def _relativo(caminho):
    return caminho.relative_to(RAIZ).as_posix() if caminho else None


def adicionar_arquivo(origem, titulo=None, artista=None, capa=None,
                      converter=True, kbps=320, playlist_id=None):
    """Adiciona um arquivo de música à biblioteca e devolve o id dele."""
    origem = Path(origem)
    if not origem.exists():
        raise FileNotFoundError(f"Arquivo não encontrado: {origem}")

    PASTA_MUSICAS.mkdir(parents=True, exist_ok=True)
    PASTA_CAPAS.mkdir(parents=True, exist_ok=True)

    tags = ler_tags(origem)
    titulo = titulo or tags["titulo"] or origem.stem
    if artista is None:
        artista = tags["artista"] or "Artista desconhecido"
    else:
        artista = artista.strip()

    nome = uuid.uuid4().hex[:10]   # nome único, evita conflito entre arquivos

    if converter and origem.suffix.lower() != ".mp3":
        destino = PASTA_MUSICAS / f"{nome}.mp3"
        converter_para_mp3(origem, destino, kbps)
    else:
        destino = PASTA_MUSICAS / f"{nome}{origem.suffix.lower()}"
        shutil.copy2(origem, destino)
    formato = destino.suffix.lstrip(".").upper()

    caminho_capa = None
    if capa:                                   # capa escolhida pelo usuário
        capa = Path(capa)
        caminho_capa = PASTA_CAPAS / f"{nome}{capa.suffix.lower()}"
        shutil.copy2(capa, caminho_capa)
    else:                                      # capa de dentro do arquivo
        extraida = extrair_capa(origem)
        if extraida:
            dados, ext = extraida
            caminho_capa = PASTA_CAPAS / f"{nome}{ext}"
            caminho_capa.write_bytes(dados)

    musica_id = db.adicionar_musica(
        titulo, artista, _relativo(destino),
        capa=_relativo(caminho_capa), album=tags["album"],
        duracao=tags["duracao"], formato=formato,
    )
    if playlist_id:
        db.adicionar_na_playlist(playlist_id, musica_id)
    return musica_id


def excluir(musica_id):
    """Exclui a música do banco e apaga a cópia e a capa da pasta dados."""
    m = db.obter_musica(musica_id)
    if m is None:
        return
    for campo in ("caminho", "capa"):
        if m[campo]:
            arquivo = RAIZ / m[campo]
            if arquivo.exists():
                arquivo.unlink()
    db.excluir_musica(musica_id)