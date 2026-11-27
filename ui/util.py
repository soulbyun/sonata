from pathlib import Path

from PySide6.QtCore import QRectF, Qt
from PySide6.QtGui import QColor, QPainter, QPainterPath, QPixmap

from ui import temas

RAIZ = Path(__file__).resolve().parent.parent

AZUL = temas.cor("azul")
LILAS = temas.cor("lilas")
TEXTO = temas.cor("texto")
TEXTO_SUAVE = temas.cor("texto_suave")

_cache = {}


def atualizar_tema():
    global AZUL, LILAS, TEXTO, TEXTO_SUAVE
    AZUL = temas.cor("azul")
    LILAS = temas.cor("lilas")
    TEXTO = temas.cor("texto")
    TEXTO_SUAVE = temas.cor("texto_suave")
    _cache.clear()


def fmt_tempo(segundos):
    segundos = int(segundos)
    return f"{segundos // 60}:{segundos % 60:02d}"


def _capa_real(caminho, lado):
    pm = QPixmap(str(RAIZ / caminho))
    if pm.isNull():
        return None
    pm = pm.scaled(lado, lado, Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation)
    return pm.copy((pm.width() - lado) // 2, (pm.height() - lado) // 2, lado, lado)


def _capa_vazia(musica_id, lado):
    pm = QPixmap(lado, lado)
    cores = [temas.cor(nome) for nome in (
        "azul_escuro", "lilas_escuro", "elevado", "borda", "cartao")]
    pm.fill(QColor(cores[musica_id % len(cores)]))
    p = QPainter(pm)
    p.setPen(QColor(temas.cor("texto_suave")))
    fonte = p.font()
    fonte.setPixelSize(int(lado * 0.45))
    p.setFont(fonte)
    p.drawText(pm.rect(), Qt.AlignCenter, "♪")
    p.end()
    return pm


def arredondar_capa(pm):
    raio = int(temas.cor("raio_capa"))
    if pm.isNull() or raio <= 0:
        return pm

    resultado = QPixmap(pm.size())
    resultado.fill(Qt.transparent)
    pintor = QPainter(resultado)
    pintor.setRenderHint(QPainter.Antialiasing)
    caminho = QPainterPath()
    caminho.addRoundedRect(QRectF(pm.rect()), raio, raio)
    pintor.setClipPath(caminho)
    pintor.drawPixmap(0, 0, pm)
    pintor.end()
    return resultado


def pixmap_capa(musica, lado):
    """Capa da música arredondada, ou um quadrado com ♪ se ela não tiver capa."""
    mid = musica["id"] if musica is not None else 0
    raio = temas.cor("raio_capa")
    chave = (temas.tema_atual(), mid, lado, raio)
    if chave not in _cache:
        pm = None
        if musica is not None and musica["capa"]:
            pm = _capa_real(musica["capa"], lado)
        pm = pm or _capa_vazia(mid, lado)
        _cache[chave] = arredondar_capa(pm)
    return _cache[chave]