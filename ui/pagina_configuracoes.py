import sys

from PySide6.QtCore import QProcess, Qt, Signal
from PySide6.QtGui import QColor, QPixmap
from PySide6.QtWidgets import (QApplication, QFrame, QHBoxLayout, QLabel,
                               QMessageBox, QVBoxLayout, QWidget)

from ui import temas


class CartaoTema(QFrame):
    clicado = Signal(str)

    def __init__(self, chave, nome, paleta, selecionado):
        super().__init__()
        self.chave = chave
        self.setObjectName("cartaoTema")
        self.setProperty("selecionado", selecionado)
        self.setCursor(Qt.PointingHandCursor)

        titulo = QLabel(nome)
        titulo.setObjectName("cardTitulo")

        faixa = QFrame()
        faixa.setObjectName("faixaTema")
        faixa.setFixedHeight(10)
        faixa.setStyleSheet(
            "background: qlineargradient(x1:0, y1:0, x2:1, y2:0, "
            f"stop:0 {paleta['fundo_a']}, stop:1 {paleta['fundo_b']});"
            "border-top-left-radius: 2px; border-top-right-radius: 2px;")

        amostras = QHBoxLayout()
        amostras.setSpacing(6)
        for nome_cor in ("fundo", "cartao", "azul", "lilas", "texto"):
            amostra = QLabel()
            amostra.setObjectName("amostraTema")
            amostra.setFixedSize(22, 22)
            pixmap = QPixmap(16, 16)
            pixmap.fill(QColor(paleta[nome_cor]))
            amostra.setPixmap(pixmap)
            amostras.addWidget(amostra)

        linha = QWidget()
        conteudo = QHBoxLayout(linha)
        conteudo.setContentsMargins(16, 12, 16, 12)
        conteudo.addWidget(titulo, 1)
        conteudo.addLayout(amostras)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(1, 1, 1, 1)
        layout.setSpacing(0)
        layout.addWidget(faixa)
        layout.addWidget(linha)

    def mousePressEvent(self, evento):
        if evento.button() == Qt.LeftButton:
            self.clicado.emit(self.chave)
        super().mousePressEvent(evento)


class PaginaConfiguracoes(QWidget):
    def __init__(self):
        super().__init__()

        titulo = QLabel("Configurações")
        titulo.setObjectName("tituloPagina")
        subtitulo = QLabel("Personalize o Sonata.")
        subtitulo.setObjectName("infoPagina")

        secao = QLabel("Tema")
        secao.setObjectName("cardTitulo")
        descricao = QLabel("O Sonata reinicia ao trocar de tema.")
        descricao.setObjectName("cardDesc")

        coluna = QVBoxLayout(self)
        coluna.setContentsMargins(40, 30, 40, 30)
        coluna.setSpacing(16)
        coluna.addWidget(titulo)
        coluna.addWidget(subtitulo)
        coluna.addSpacing(8)
        coluna.addWidget(secao)
        coluna.addWidget(descricao)

        for chave, (nome, paleta) in temas.TEMAS.items():
            cartao = CartaoTema(
                chave, nome, paleta, chave == temas.tema_atual())
            cartao.clicado.connect(self._trocar_tema)
            coluna.addWidget(cartao)

        coluna.addStretch()

    def _trocar_tema(self, chave):
        if chave == temas.tema_atual():
            return

        tema_anterior = temas.tema_atual()
        temas.salvar_tema(chave)
        if not QProcess.startDetached(sys.executable, sys.argv):
            temas.salvar_tema(tema_anterior)
            QMessageBox.warning(
                self, "Não foi possível reiniciar",
                "O Sonata não conseguiu reiniciar para aplicar o tema.")
            return
        QApplication.quit()
