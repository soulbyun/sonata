import re
from pathlib import Path

from PySide6.QtCore import QByteArray, QRectF
from PySide6.QtGui import QColor, QGuiApplication, QIcon, QPainter, QPixmap
from PySide6.QtSvg import QSvgRenderer

from ui import temas


_PASTA_ICONES = Path(__file__).resolve().parent.parent / "assets" / "icones"
_ALIAS = {
    "musica": "music-notes-simple",
    "coracao": "heart-straight-duotone",
    "artista": "user-circle-duotone",
    "engrenagem": "gear",
}
_CACHE_PIXMAPS = {}
_CACHE_ICONES = {}


def limpar_cache():
    _CACHE_PIXMAPS.clear()
    _CACHE_ICONES.clear()


def _preparar_svg(svg, cor, cheio):
    svg = svg.replace("currentColor", cor)

    def substituir_fill(resultado):
        valor = resultado.group(3)
        if valor.lower() == "none" and not cheio:
            return resultado.group(0)
        aspas = resultado.group(2)
        return f"{resultado.group(1)}{aspas}{cor}{aspas}"

    svg = re.sub(
        r"""(\bfill\s*=\s*)(["'])(.*?)\2""",
        substituir_fill,
        svg,
        flags=re.IGNORECASE,
    )
    if cheio:
        svg = re.sub(
            r"""(\bopacity\s*=\s*)(["'])0\.2\2""",
            lambda resultado: (
                f"{resultado.group(1)}{resultado.group(2)}1"
                f"{resultado.group(2)}"),
            svg,
            flags=re.IGNORECASE,
        )
    return svg


def pixmap(nome, cor=None, tamanho=20, cheio=False) -> QPixmap:
    cor = cor or temas.cor("texto_suave")
    chave = (nome, cor, tamanho, cheio)
    if chave in _CACHE_PIXMAPS:
        return _CACHE_PIXMAPS[chave]

    caminho = _PASTA_ICONES / f"{_ALIAS.get(nome, nome)}.svg"
    if not caminho.is_file():
        imagem = QPixmap()
        _CACHE_PIXMAPS[chave] = imagem
        return imagem

    svg = caminho.read_text(encoding="utf-8")
    svg = _preparar_svg(svg, cor, cheio)
    renderer = QSvgRenderer(QByteArray(svg.encode("utf-8")))

    tela = QGuiApplication.primaryScreen()
    escala = tela.devicePixelRatio() if tela else 1.0
    imagem = QPixmap(max(1, round(tamanho * escala)),
                     max(1, round(tamanho * escala)))
    imagem.setDevicePixelRatio(escala)
    imagem.fill(QColor(0, 0, 0, 0))

    if renderer.isValid():
        pintor = QPainter(imagem)
        renderer.render(pintor, QRectF(0, 0, tamanho, tamanho))
        pintor.end()

    _CACHE_PIXMAPS[chave] = imagem
    return imagem


def icone(nome, cor=None, tamanho=20, cheio=False) -> QIcon:
    chave = (nome, cor, tamanho, cheio)
    if chave in _CACHE_ICONES:
        return _CACHE_ICONES[chave]

    icone_resultado = QIcon()
    icone_resultado.addPixmap(
        pixmap(nome, cor or temas.cor("texto_suave"), tamanho, cheio),
        QIcon.Normal, QIcon.Off)
    icone_resultado.addPixmap(
        pixmap(nome, temas.cor("azul"), tamanho, cheio),
        QIcon.Normal, QIcon.On)
    _CACHE_ICONES[chave] = icone_resultado
    return icone_resultado
