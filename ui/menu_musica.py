from PySide6.QtCore import QSize, Qt, Signal
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QFrame, QHBoxLayout, QPushButton

from ui import temas, util
from ui.icones import pixmap


def _icone(nome, cor, cheio=False):
    return QIcon(pixmap(nome, cor=cor, tamanho=20, cheio=cheio))


class BotaoMenu(QPushButton):
    """Botão só com ícone: cinza normalmente, colorido quando o mouse passa."""

    def __init__(self, desenhar, dica, cor_hover, cheio=False):
        super().__init__()
        self.setObjectName("botaoMenu")
        self.setToolTip(dica)
        self.setFixedSize(40, 36)
        self.setIconSize(QSize(20, 20))
        self.setCursor(Qt.PointingHandCursor)
        cor_normal = (
            temas.cor("hud_amarelo") or temas.cor("lilas_claro")
            if cheio or desenhar == "coracao" else util.TEXTO_SUAVE)
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
    """Caixinha de ações de uma música."""
    acao = Signal(str)   # "favoritar", "playlist", "fila" ou "excluir"

    def __init__(self, musica, parent=None):
        super().__init__(parent, Qt.Popup)
        self.setObjectName("menuMusica")
        self.setAttribute(Qt.WA_DeleteOnClose)
        favorita = bool(musica["favorita"])
        cor_favorito = (
            temas.cor("hud_amarelo") or
            (temas.cor("texto") if favorita else temas.cor("lilas_claro")))

        b_favorito = BotaoMenu(
            "coracao", "Favoritar", cor_favorito, cheio=favorita)
        b_playlist = BotaoMenu(
            "playlist", "Adicionar à playlist", util.AZUL)
        b_fila = BotaoMenu(
            "fila-mais", "Adicionar à fila", util.AZUL)
        b_excluir = BotaoMenu(
            "lixeira", "Excluir", temas.cor("perigo"))

        b_favorito.clicked.connect(lambda: self._escolher("favoritar"))
        b_playlist.clicked.connect(lambda: self._escolher("playlist"))
        b_fila.clicked.connect(lambda: self._escolher("fila"))
        b_excluir.clicked.connect(lambda: self._escolher("excluir"))

        layout = QHBoxLayout(self)
        layout.setContentsMargins(6, 6, 6, 6)
        layout.setSpacing(2)
        for botao in (b_favorito, b_playlist, b_fila, b_excluir):
            layout.addWidget(botao)

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
