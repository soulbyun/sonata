import random

from PySide6.QtCore import QEvent, QPointF, QRectF, Qt
from PySide6.QtGui import (QBrush, QColor, QImage, QLinearGradient, QPainter,
                           QPen, QPixmap, QRadialGradient)
from PySide6.QtWidgets import QWidget

from ui import temas


_CACHE = {}
_LADO = 512


def _com_alfa(cor, alfa):
    resultado = QColor(cor)
    resultado.setAlpha(alfa)
    return resultado


def _desenhar_braco(pintor, x, y, comprimento, vertical, cor, alfa):
    if vertical:
        inicio = QPointF(x, y - comprimento)
        fim = QPointF(x, y + comprimento)
    else:
        inicio = QPointF(x - comprimento, y)
        fim = QPointF(x + comprimento, y)

    gradiente = QLinearGradient(inicio, fim)
    gradiente.setColorAt(0, _com_alfa(cor, 0))
    gradiente.setColorAt(0.5, _com_alfa(cor, alfa))
    gradiente.setColorAt(1, _com_alfa(cor, 0))
    pintor.setPen(QPen(
        QBrush(gradiente), 1.2, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
    pintor.drawLine(inicio, fim)


def _desenhar_cruz(pintor, x, y, raio_h, raio_v, cor, alfa):
    _desenhar_braco(pintor, x, y, raio_h, False, cor, alfa)
    _desenhar_braco(pintor, x, y, raio_v, True, cor, alfa)
    pintor.setPen(Qt.NoPen)
    pintor.setBrush(_com_alfa(cor, alfa))
    pintor.drawEllipse(QPointF(x, y), 1.1, 1.1)


def _gerar_estrelas(textura_cor, textura_destaque):
    chave = ("estrelas", textura_cor, textura_destaque)
    if chave in _CACHE:
        return _CACHE[chave]

    destaque = textura_destaque or textura_cor
    imagem = QImage(
        _LADO, _LADO, QImage.Format_ARGB32_Premultiplied)
    imagem.fill(Qt.transparent)
    pintor = QPainter(imagem)
    pintor.setRenderHint(QPainter.Antialiasing)
    aleatorio = random.Random(7)

    pintor.setPen(Qt.NoPen)
    for _ in range(350):
        diametro = 2 if aleatorio.random() < 0.12 else 1
        x = aleatorio.randint(14, _LADO - diametro - 15)
        y = aleatorio.randint(14, _LADO - diametro - 15)
        pintor.setBrush(_com_alfa(textura_cor, aleatorio.randint(40, 200)))
        pintor.drawEllipse(
            QRectF(x, y, diametro, diametro))

    for _ in range(10):
        x = aleatorio.randint(24, _LADO - 25)
        y = aleatorio.randint(24, _LADO - 25)
        alfa = aleatorio.randint(120, 210)
        _desenhar_cruz(
            pintor, x, y, aleatorio.randint(4, 9),
            aleatorio.randint(4, 9), destaque, alfa)

    for _ in range(3):
        x = aleatorio.randint(32, _LADO - 33)
        y = aleatorio.randint(32, _LADO - 33)
        raio = aleatorio.randint(9, 12)
        halo = QRadialGradient(QPointF(x, y), raio + 4)
        halo.setColorAt(0, _com_alfa(destaque, 24))
        halo.setColorAt(0.55, _com_alfa(destaque, 10))
        halo.setColorAt(1, _com_alfa(destaque, 0))
        pintor.setPen(Qt.NoPen)
        pintor.setBrush(QBrush(halo))
        pintor.drawEllipse(QPointF(x, y), raio + 4, raio + 4)
        _desenhar_cruz(
            pintor, x, y, raio, max(5, raio - 2), destaque, 190)

    pintor.end()
    _CACHE[chave] = QPixmap.fromImage(imagem)
    return _CACHE[chave]


def _gerar_hud(textura_cor, hud_azul):
    chave = ("hud", textura_cor, hud_azul)
    if chave in _CACHE:
        return _CACHE[chave]

    imagem = QImage(_LADO, _LADO, QImage.Format_ARGB32)
    imagem.fill(Qt.transparent)
    aleatorio = random.Random(11)
    cor_grao = QColor(textura_cor)
    total_pixels = _LADO * _LADO
    for indice in aleatorio.sample(
            range(total_pixels), round(total_pixels * 0.04)):
        alfa = aleatorio.randint(10, 45)
        pixel = ((alfa << 24) | (cor_grao.red() << 16) |
                 (cor_grao.green() << 8) | cor_grao.blue())
        imagem.setPixel(indice % _LADO, indice // _LADO, pixel)

    pintor = QPainter(imagem)
    pintor.setPen(QPen(_com_alfa(textura_cor, 8), 1))
    for y in range(0, _LADO, 4):
        pintor.drawLine(0, y, _LADO - 1, y)

    pintor.setPen(QPen(_com_alfa(textura_cor, 60), 1))
    for x in range(32, _LADO, 64):
        for y in range(32, _LADO, 64):
            pintor.drawLine(x - 2, y, x + 2, y)
            pintor.drawLine(x, y - 2, x, y + 2)

    pintor.setPen(QPen(_com_alfa(hud_azul or textura_cor, 150), 1,
                       Qt.SolidLine, Qt.SquareCap))
    for centro_x, centro_y in (
            (96, 96), (416, 96), (96, 416), (416, 416)):
        for linha in range(3):
            for coluna in range(3):
                pintor.drawPoint(
                    centro_x + coluna * 3, centro_y + linha * 3)
    pintor.end()

    _CACHE[chave] = QPixmap.fromImage(imagem)
    return _CACHE[chave]


class _CamadaTextura(QWidget):
    def __init__(self, pai, ladrilho, opacidade):
        super().__init__(pai)
        self._ladrilho = ladrilho
        self._opacidade = opacidade
        self.setAttribute(Qt.WA_TransparentForMouseEvents)
        self.setAttribute(Qt.WA_NoSystemBackground)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setGeometry(pai.contentsRect())
        pai.installEventFilter(self)
        self.show()
        self.lower()

    def eventFilter(self, observado, evento):
        if observado is self.parentWidget() and evento.type() == QEvent.Resize:
            self.setGeometry(observado.contentsRect())
        return super().eventFilter(observado, evento)

    def paintEvent(self, evento):
        pintor = QPainter(self)
        pintor.setOpacity(self._opacidade)
        pintor.drawTiledPixmap(self.rect(), self._ladrilho)
        pintor.end()


def aplicar_textura(widget):
    paleta = temas.TEMAS[temas.tema_atual()][1]
    tipo = paleta["textura"]
    if tipo == "estrelas":
        ladrilho = _gerar_estrelas(
            paleta["textura_cor"], paleta["textura_destaque"])
    elif tipo == "hud":
        ladrilho = _gerar_hud(
            paleta["textura_cor"], paleta.get("hud_azul"))
    else:
        return None

    return _CamadaTextura(widget, ladrilho, paleta["textura_opacidade"])
