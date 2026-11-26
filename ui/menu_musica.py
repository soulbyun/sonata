from PySide6.QtCore import QSize, Qt, Signal
from PySide6.QtGui import (QBrush, QColor, QIcon, QPainter, QPainterPath, QPen,
                           QPixmap)
from PySide6.QtWidgets import QFrame, QHBoxLayout, QPushButton

from ui import temas, util


# ---------- ícones desenhados à mão (tela de 44 x 44) ----------

def _coracao(p, cheio):
    c = QPainterPath()
    c.moveTo(22, 38)
    c.cubicTo(8, 28, 3, 20, 3, 14)
    c.cubicTo(3, 8, 8, 5, 13, 5)
    c.cubicTo(17, 5, 20, 7, 22, 11)
    c.cubicTo(24, 7, 27, 5, 31, 5)
    c.cubicTo(36, 5, 41, 8, 41, 14)
    c.cubicTo(41, 20, 36, 28, 22, 38)
    c.closeSubpath()
    if cheio:
        p.setBrush(p.pen().color())
    p.drawPath(c)


def _fila(p, cheio):
    p.drawLine(5, 11, 39, 11)
    p.drawLine(5, 22, 39, 22)
    p.drawLine(5, 33, 19, 33)
    p.drawLine(32, 27, 32, 39)   # o "+"
    p.drawLine(26, 33, 38, 33)


def _lixeira(p, cheio):
    p.drawLine(6, 11, 38, 11)
    tampa = QPainterPath()
    tampa.moveTo(16, 11)
    tampa.lineTo(16, 6)
    tampa.lineTo(28, 6)
    tampa.lineTo(28, 11)
    p.drawPath(tampa)
    corpo = QPainterPath()
    corpo.moveTo(10, 11)
    corpo.lineTo(12, 38)
    corpo.lineTo(32, 38)
    corpo.lineTo(34, 11)
    p.drawPath(corpo)
    p.drawLine(18, 18, 18, 31)
    p.drawLine(26, 18, 26, 31)


def _icone(desenhar, cor, cheio=False):
    pm = QPixmap(44, 44)
    pm.fill(Qt.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.Antialiasing)
    p.setPen(QPen(QBrush(QColor(cor)), 3.5, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
    p.setBrush(Qt.NoBrush)
    desenhar(p, cheio)
    p.end()
    return QIcon(pm)


class BotaoMenu(QPushButton):
    """Botão só com ícone: cinza normalmente, colorido quando o mouse passa."""

    def __init__(self, desenhar, dica, cor_hover, cheio=False):
        super().__init__()
        self.setObjectName("botaoMenu")
        self.setToolTip(dica)
        self.setFixedSize(40, 36)
        self.setIconSize(QSize(20, 20))
        self.setCursor(Qt.PointingHandCursor)
        cor_normal = (temas.cor("lilas_claro")
                      if cheio or desenhar is _coracao else util.TEXTO_SUAVE)
        self._normal = _icone(desenhar, cor_normal, cheio)
        self._hover = _icone(desenhar, cor_hover, cheio)
        self.setIcon(self._normal)

    def enterEvent(self, evento):
        self.setIcon(self._hover)
        super().enterEvent(evento)

    def leaveEvent(self, evento):
        self.setIcon(self._normal)
        super().leaveEvent(evento)


class MenuMusica(QFrame):
    """Caixinha que abre com o botão direito: coração, fila e lixeira."""
    acao = Signal(str)   # "favoritar", "playlist" ou "excluir"

    def __init__(self, musica, parent=None):
        super().__init__(parent, Qt.Popup)
        self.setObjectName("menuMusica")
        self.setAttribute(Qt.WA_DeleteOnClose)
        favorita = bool(musica["favorita"])

        b_favorito = BotaoMenu(
            _coracao,
            "Remover dos favoritos" if favorita else "Adicionar aos favoritos",
            temas.cor("texto") if favorita else temas.cor("lilas_claro"),
            cheio=favorita)
        b_playlist = BotaoMenu(_fila, "Adicionar à playlist", util.AZUL)
        b_excluir = BotaoMenu(_lixeira, "Excluir música", temas.cor("perigo"))

        b_favorito.clicked.connect(lambda: self._escolher("favoritar"))
        b_playlist.clicked.connect(lambda: self._escolher("playlist"))
        b_excluir.clicked.connect(lambda: self._escolher("excluir"))

        layout = QHBoxLayout(self)
        layout.setContentsMargins(6, 6, 6, 6)
        layout.setSpacing(2)
        layout.addWidget(b_favorito)
        layout.addWidget(b_playlist)
        layout.addWidget(b_excluir)

    def _escolher(self, nome):
        self.close()
        self.acao.emit(nome)

    def mostrar_em(self, posicao):
        """Abre a caixinha no ponto do clique, sem sair da tela."""
        self.adjustSize()
        tela = self.screen().availableGeometry()
        x = min(posicao.x(), tela.right() - self.width())
        y = min(posicao.y(), tela.bottom() - self.height())
        self.move(max(x, tela.left()), max(y, tela.top()))
        self.show()