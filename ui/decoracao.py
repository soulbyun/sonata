from functools import lru_cache
from pathlib import Path

from PySide6.QtCore import QEvent, QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QFont, QFontMetricsF, QImage, QPainter, QPen, QPixmap
from PySide6.QtWidgets import QWidget

from ui import temas


_RAIZ = Path(__file__).resolve().parent.parent
_MARCAS_AUSENTES = set()


@lru_cache(maxsize=8)
def _carregar_marca(caminho):
    origem = QImage(caminho)
    if origem.isNull():
        return QPixmap()
    origem = origem.convertToFormat(QImage.Format_ARGB32)

    linhas_brilho = []
    esquerda = origem.width()
    topo = origem.height()
    direita = -1
    baixo = -1

    for y in range(origem.height()):
        linha = bytearray(origem.width())
        for x in range(origem.width()):
            pixel = origem.pixelColor(x, y)
            brilho = (
                299 * pixel.red() + 587 * pixel.green() +
                114 * pixel.blue() + 500) // 1000
            linha[x] = brilho
            if brilho >= 40:
                esquerda = min(esquerda, x)
                topo = min(topo, y)
                direita = max(direita, x)
                baixo = max(baixo, y)
        linhas_brilho.append(linha)

    if direita < esquerda or baixo < topo:
        return QPixmap()

    largura = direita - esquerda + 1
    altura = baixo - topo + 1
    marca = QImage(largura, altura, QImage.Format_ARGB32)
    for y in range(altura):
        linha = linhas_brilho[topo + y]
        for x in range(largura):
            alfa = linha[esquerda + x]
            marca.setPixel(x, y, (alfa << 24) | 0x00FFFFFF)
    return QPixmap.fromImage(marca)


class DecoracaoOverlay(QWidget):
    def __init__(self, area):
        super().__init__(area)
        self._hud = bool(temas.cor("hud"))
        self._opacidade_marca = temas.cor("marca_dagua_opacidade")
        self._proporcao_marca = temas.cor("marca_dagua_tamanho")
        self._marca_original = QPixmap()
        self._marca_redimensionada = QPixmap()
        self._altura_redimensionada = -1

        caminho = temas.cor("marca_dagua")
        if caminho:
            caminho = Path(caminho)
            if not caminho.is_absolute():
                caminho = _RAIZ / caminho
            caminho = caminho.resolve()
            if caminho.is_file():
                self._marca_original = _carregar_marca(str(caminho))
            elif str(caminho) not in _MARCAS_AUSENTES:
                print(f"Marca d'água não encontrada: {caminho}")
                _MARCAS_AUSENTES.add(str(caminho))

        self.setAttribute(Qt.WA_TransparentForMouseEvents)
        self.setAttribute(Qt.WA_NoSystemBackground)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setGeometry(area.rect())
        area.installEventFilter(self)
        self._atualizar_marca()

        if self._hud or not self._marca_original.isNull():
            self.show()
        else:
            self.hide()

    def eventFilter(self, observado, evento):
        if observado is self.parentWidget() and evento.type() == QEvent.Resize:
            self.setGeometry(observado.rect())
        return super().eventFilter(observado, evento)

    def resizeEvent(self, evento):
        self._atualizar_marca()
        super().resizeEvent(evento)

    def _atualizar_marca(self):
        if self._marca_original.isNull() or self.height() <= 0:
            return

        altura = max(1, round(self.height() * self._proporcao_marca))
        if altura == self._altura_redimensionada:
            return

        self._marca_redimensionada = self._marca_original.scaledToHeight(
            altura, Qt.SmoothTransformation)
        self._altura_redimensionada = altura

    def paintEvent(self, evento):
        pintor = QPainter(self)
        pintor.setRenderHint(QPainter.Antialiasing)

        if not self._marca_redimensionada.isNull():
            x = (self.width() - self._marca_redimensionada.width()) // 2
            y = (self.height() - self._marca_redimensionada.height()) // 2
            pintor.save()
            pintor.setOpacity(self._opacidade_marca)
            pintor.drawPixmap(x, y, self._marca_redimensionada)
            pintor.restore()

        if self._hud:
            self._desenhar_moldura(pintor)

        pintor.end()

    def _desenhar_moldura(self, pintor):
        largura = self.width()
        if largura < 64 or self.height() < 24:
            return

        x_inicio = 10
        x_fim = ((largura - 10) // 2) * 2
        y_linha = 10
        x_regua_inicio = 24
        x_regua_fim = x_fim - 14

        pintor.setPen(QPen(QColor(temas.cor("borda_forte")), 1))
        pintor.drawLine(x_regua_inicio, y_linha, x_regua_fim, y_linha)

        pintor.setPen(QPen(QColor(temas.cor("texto_suave")), 1.5))
        pintor.drawLine(x_inicio, y_linha, x_regua_inicio, y_linha)
        pintor.drawLine(x_inicio, y_linha, x_inicio, 24)
        pintor.drawLine(x_regua_fim, y_linha, x_fim, y_linha)
        pintor.drawLine(x_fim, y_linha, x_fim, 24)

        rotulo = "SNT-001"
        fonte = QFont("Consolas")
        fonte.setPixelSize(9)
        fonte.setStyleHint(QFont.Monospace)
        fonte.setLetterSpacing(QFont.AbsoluteSpacing, 1.5)
        medidas = QFontMetricsF(fonte)
        largura_rotulo = medidas.horizontalAdvance(rotulo)
        x_rotulo = round((largura - 32 - largura_rotulo) / 2) * 2

        cor_marcas = QColor(temas.cor("texto_fraco"))
        cor_marcas.setAlpha(120)
        pintor.setPen(QPen(cor_marcas, 1))
        for x in range(x_regua_inicio, x_regua_fim + 1, 8):
            if x_rotulo <= x <= x_rotulo + largura_rotulo:
                continue
            comprimento = 8 if (x - x_regua_inicio) % 40 == 0 else 4
            pintor.drawLine(x, y_linha, x, y_linha + comprimento)

        pintor.setPen(Qt.NoPen)
        blocos = (
            (32, temas.cor("hud_azul"), 36),
            (72, temas.cor("hud_amarelo"), 12),
            (88, temas.cor("hud_vermelho"), 4),
        )
        for x, cor, bloco_largura in blocos:
            if cor:
                pintor.setBrush(QColor(cor))
                pintor.drawRect(QRectF(x, 8, bloco_largura, 4))

        pintor.setFont(fonte)
        pintor.setPen(QColor(temas.cor("texto_fraco")))
        pintor.drawText(QPointF(x_rotulo, 20), rotulo)
