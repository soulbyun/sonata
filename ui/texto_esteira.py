import math
import time

from PySide6.QtCore import QObject, QPointF, QRect, QTimer, Qt
from PySide6.QtGui import QColor, QFont, QFontMetrics, QPainter, QPalette
from PySide6.QtWidgets import QLabel


class AnimacaoEsteira(QObject):
    def __init__(self, parent, atualizar):
        super().__init__(parent)
        self._atualizar = atualizar
        self._estados = {}
        self._pausa = QTimer(self)
        self._pausa.setSingleShot(True)
        self._pausa.timeout.connect(self._organizar_timers)
        self._timer = QTimer(self)
        self._timer.setInterval(33)
        self._timer.timeout.connect(self._avancar)
        self._espaco = 36
        self._passo = 0.65

    def limpar(self):
        self._estados.clear()
        self._pausa.stop()
        self._timer.stop()

    def pintar(self, painter, area, texto, fonte, cor, chave, ativo,
               alinhamento=Qt.AlignLeft):
        texto = str(texto or "")
        area = QRect(area)
        metricas = QFontMetrics(fonte)
        largura = metricas.horizontalAdvance(texto)
        painter.save()
        painter.setClipRect(area, Qt.IntersectClip)
        painter.setFont(fonte)
        painter.setPen(QColor(cor))

        if largura <= area.width() or not ativo:
            self._remover(chave)
            exibido = metricas.elidedText(texto, Qt.ElideRight, area.width())
            painter.drawText(
                area, alinhamento | Qt.AlignVCenter, exibido)
            painter.restore()
            return

        estado = self._estados.get(chave)
        agora = time.monotonic()
        if (estado is None or estado["texto"] != texto
                or estado["fonte"] != fonte
                or estado["largura"] != area.width()):
            estado = {
                "texto": texto,
                "fonte": QFont(fonte),
                "largura": area.width(),
                "texto_largura": largura,
                "ciclo": largura + self._espaco,
                "inicio": agora + 1.0,
                "deslocamento": 0.0,
                "ultima_pintura": agora,
            }
            self._estados[chave] = estado
            self._organizar_timers()
        else:
            estado["ultima_pintura"] = agora

        if estado["inicio"] > agora:
            exibido = metricas.elidedText(texto, Qt.ElideRight, area.width())
            painter.drawText(
                area, alinhamento | Qt.AlignVCenter, exibido)
        else:
            baseline = area.top() + (
                area.height() - metricas.height()) / 2 + metricas.ascent()
            x = area.left() - estado["deslocamento"]
            painter.drawText(QPointF(x, baseline), texto)
            painter.drawText(
                QPointF(x + estado["ciclo"], baseline), texto)
        painter.restore()

    def _remover(self, chave):
        if chave in self._estados:
            del self._estados[chave]
            self._organizar_timers()

    def _organizar_timers(self):
        if not self._estados:
            self._pausa.stop()
            self._timer.stop()
            return
        if self.parent() is not None and not self.parent().isVisible():
            self.limpar()
            return

        agora = time.monotonic()
        prontos = any(e["inicio"] <= agora for e in self._estados.values())
        if prontos:
            self._pausa.stop()
            if not self._timer.isActive():
                self._timer.start()
            return

        self._timer.stop()
        restante = min(e["inicio"] for e in self._estados.values()) - agora
        atraso = max(1, math.ceil(restante * 1000))
        if not self._pausa.isActive() or self._pausa.remainingTime() > atraso:
            self._pausa.start(atraso)

    def _avancar(self):
        if self.parent() is not None and not self.parent().isVisible():
            self.limpar()
            return

        agora = time.monotonic()
        mudou = False
        vencidos = [
            chave for chave, estado in self._estados.items()
            if agora - estado["ultima_pintura"] > 1.5
        ]
        for chave in vencidos:
            del self._estados[chave]
        for estado in self._estados.values():
            if estado["inicio"] <= agora:
                estado["deslocamento"] = (
                    estado["deslocamento"] + self._passo) % estado["ciclo"]
                mudou = True
        if mudou:
            self._atualizar()
        self._organizar_timers()


class TextoEsteira(QLabel):
    def __init__(self, texto="", parent=None):
        super().__init__(parent)
        self._esteira = AnimacaoEsteira(self, self.update)
        self.setTextFormat(Qt.PlainText)
        self.setWordWrap(False)
        self.setText(texto)

    def setText(self, texto):
        self._esteira.limpar()
        super().setText(texto)
        self.update()

    def paintEvent(self, evento):
        painter = QPainter(self)
        self._esteira.pintar(
            painter, self.contentsRect(), self.text(), self.font(),
            self.palette().color(QPalette.WindowText), "texto",
            self.isVisible(), self.alignment())
        painter.end()

    def resizeEvent(self, evento):
        self._esteira.limpar()
        super().resizeEvent(evento)

    def hideEvent(self, evento):
        self._esteira.limpar()
        super().hideEvent(evento)
