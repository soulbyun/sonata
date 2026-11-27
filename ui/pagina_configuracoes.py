from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor, QPixmap
from PySide6.QtWidgets import (QFrame, QGridLayout, QHBoxLayout, QLabel,
                               QPushButton, QSizePolicy, QVBoxLayout, QWidget)

from ui import temas


class CartaoTema(QFrame):
    clicado = Signal(str)

    def __init__(self, chave, nome, paleta, selecionado):
        super().__init__()
        self.chave = chave
        self.setObjectName("cartaoTema")
        self.setProperty("selecionado", selecionado)
        self.setProperty("mafty", chave == "mafty")
        self.setCursor(Qt.PointingHandCursor)
        self.setFixedSize(150, 84)

        titulo = QLabel(nome)
        titulo.setObjectName("cardTitulo")
        titulo.setProperty("tituloTema", True)
        titulo.setAlignment(Qt.AlignCenter)

        faixa = QFrame()
        faixa.setObjectName("faixaTema")
        faixa.setFixedHeight(34)

        amostras = QHBoxLayout()
        amostras.setContentsMargins(10, 0, 10, 0)
        amostras.setSpacing(5)
        for nome_cor in ("fundo", "cartao", "azul", "lilas", "texto"):
            amostra = QLabel()
            amostra.setObjectName("amostraTema")
            amostra.setFixedSize(18, 18)
            pixmap = QPixmap(18, 18)
            pixmap.fill(QColor(paleta[nome_cor]))
            amostra.setPixmap(pixmap)
            amostras.addWidget(amostra)

        faixa.setLayout(amostras)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(1, 1, 1, 1)
        layout.setSpacing(4)
        layout.addWidget(faixa)
        layout.addWidget(titulo, 1)

    def mousePressEvent(self, evento):
        if evento.button() == Qt.LeftButton:
            self.clicado.emit(self.chave)
        super().mousePressEvent(evento)

    def definir_selecionado(self, selecionado):
        self.setProperty("selecionado", selecionado)
        estilo = self.style()
        estilo.unpolish(self)
        estilo.polish(self)
        self.update()


class PaginaConfiguracoes(QWidget):
    editar_musicas = Signal()
    tema_solicitado = Signal(str)

    def __init__(self):
        super().__init__()

        titulo = QLabel("Configurações")
        titulo.setObjectName("tituloPagina")
        titulo.setProperty("tituloConfiguracoes", True)

        secao = QLabel("Tema")
        secao.setObjectName("cardTitulo")
        secao.setProperty("secaoConfiguracoes", True)

        coluna = QVBoxLayout(self)
        coluna.setContentsMargins(40, 30, 40, 30)
        coluna.setSpacing(24)
        coluna.addWidget(titulo)

        btn_editar_musicas = QPushButton("Editar músicas e artistas")
        btn_editar_musicas.setObjectName("secundario")
        btn_editar_musicas.setSizePolicy(
            QSizePolicy.Fixed, QSizePolicy.Fixed)
        btn_editar_musicas.clicked.connect(self.editar_musicas.emit)
        coluna.addWidget(btn_editar_musicas, 0, Qt.AlignLeft)

        bloco_temas = QWidget()
        layout_temas = QVBoxLayout(bloco_temas)
        layout_temas.setContentsMargins(0, 0, 0, 0)
        layout_temas.setSpacing(12)
        layout_temas.addWidget(secao)

        self.grade_temas = QWidget()
        self.grade_temas.setSizePolicy(
            QSizePolicy.Ignored, QSizePolicy.Preferred)
        self._layout_temas = QGridLayout(self.grade_temas)
        self._layout_temas.setContentsMargins(0, 0, 0, 0)
        self._layout_temas.setHorizontalSpacing(10)
        self._layout_temas.setVerticalSpacing(10)
        layout_temas.addWidget(self.grade_temas)
        coluna.addWidget(bloco_temas)

        self.cartoes_tema = {}
        for chave, (nome, paleta) in temas.TEMAS.items():
            cartao = CartaoTema(
                chave, nome, paleta, chave == temas.tema_atual())
            cartao.clicado.connect(self._trocar_tema)
            self.cartoes_tema[chave] = cartao

        self._colunas_temas = 0
        self._organizar_cartoes(1)
        coluna.addStretch()

    def resizeEvent(self, evento):
        super().resizeEvent(evento)
        margens = self.layout().contentsMargins()
        largura = self.width() - margens.left() - margens.right()
        colunas = max(1, (largura + 10) // 160)
        if colunas != self._colunas_temas:
            self._organizar_cartoes(colunas)

    def _organizar_cartoes(self, colunas):
        while self._layout_temas.count():
            self._layout_temas.takeAt(0)
        for indice, cartao in enumerate(self.cartoes_tema.values()):
            self._layout_temas.addWidget(
                cartao, indice // colunas, indice % colunas)
        self._colunas_temas = colunas

    def _trocar_tema(self, chave):
        if chave == temas.tema_atual():
            return
        temas.salvar_tema(chave)
        self.tema_solicitado.emit(chave)

    def atualizar_tema(self, chave):
        for nome, cartao in self.cartoes_tema.items():
            cartao.definir_selecionado(nome == chave)
