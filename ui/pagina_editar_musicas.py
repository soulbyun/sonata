import shutil
import sqlite3
import uuid
from pathlib import Path

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (QCheckBox, QFileDialog, QFrame, QHBoxLayout,
                               QLabel, QLineEdit, QMessageBox, QPushButton,
                               QStackedWidget, QVBoxLayout, QWidget)

import db
import library
from ui import util
from ui.pagina_musicas import PaginaMusicas


class PaginaEditarMusicas(QWidget):
    voltar_solicitado = Signal()
    musicas_atualizadas = Signal()

    def __init__(self):
        super().__init__()
        self._musica = None
        self._capa_selecionada = None

        self.biblioteca = PaginaMusicas(
            "Editar músicas e artistas", db.listar_musicas)
        btn_voltar = QPushButton("Voltar")
        btn_voltar.setObjectName("secundario")
        btn_voltar.clicked.connect(self.voltar_solicitado.emit)
        self.biblioteca.adicionar_a_esquerda(btn_voltar)
        self.biblioteca.lista.itemClicked.connect(self._selecionar_musica)

        self.editor = QWidget()
        titulo = QLabel("Editar música")
        titulo.setObjectName("tituloPagina")

        cartao = QFrame()
        cartao.setObjectName("card")
        conteudo = QVBoxLayout(cartao)
        conteudo.setContentsMargins(24, 24, 24, 24)
        conteudo.setSpacing(14)

        self.capa = QLabel()
        self.capa.setFixedSize(112, 112)
        self.capa.setAlignment(Qt.AlignCenter)
        self.btn_trocar_capa = QPushButton("Trocar capa")
        self.btn_trocar_capa.setObjectName("secundario")
        self.btn_trocar_capa.clicked.connect(self._escolher_capa)
        linha_capa = QHBoxLayout()
        linha_capa.addWidget(self.capa)
        linha_capa.addWidget(self.btn_trocar_capa, 0, Qt.AlignVCenter)
        linha_capa.addStretch()
        conteudo.addLayout(linha_capa)

        rotulo_nome = QLabel("Nome da música")
        rotulo_nome.setObjectName("secao")
        self.campo_nome = QLineEdit()
        self.campo_nome.setObjectName("campoItem")
        conteudo.addWidget(rotulo_nome)
        conteudo.addWidget(self.campo_nome)

        rotulo_artista = QLabel("Artista")
        rotulo_artista.setObjectName("secao")
        self.campo_artista = QLineEdit()
        self.campo_artista.setObjectName("campoArtista")
        conteudo.addWidget(rotulo_artista)
        conteudo.addWidget(self.campo_artista)

        self.aplicar_artista = QCheckBox(
            "Aplicar este artista a todas as músicas do artista antigo")
        conteudo.addWidget(self.aplicar_artista)

        botoes = QHBoxLayout()
        botoes.addStretch()
        self.btn_cancelar = QPushButton("Cancelar")
        self.btn_cancelar.setObjectName("secundario")
        self.btn_cancelar.clicked.connect(self._cancelar)
        self.btn_salvar = QPushButton("Salvar")
        self.btn_salvar.setObjectName("primario")
        self.btn_salvar.clicked.connect(self._salvar)
        botoes.addWidget(self.btn_cancelar)
        botoes.addWidget(self.btn_salvar)
        conteudo.addLayout(botoes)

        layout_editor = QVBoxLayout(self.editor)
        layout_editor.setContentsMargins(40, 30, 40, 30)
        layout_editor.setSpacing(18)
        layout_editor.addWidget(titulo)
        layout_editor.addWidget(cartao)
        layout_editor.addStretch()

        self.pilha = QStackedWidget()
        self.pilha.addWidget(self.biblioteca)
        self.pilha.addWidget(self.editor)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.pilha)

    def carregar(self):
        self.biblioteca.carregar()

    def marcar_tocando(self, musica_id):
        self.biblioteca.marcar_tocando(musica_id)

    def _selecionar_musica(self, item):
        indice = self.biblioteca.lista.row(item)
        if not 0 <= indice < len(self.biblioteca.exibidas):
            return
        musica = dict(self.biblioteca.exibidas[indice])
        self._musica = musica
        self._capa_selecionada = None
        self.campo_nome.setText(musica["titulo"] or "")
        self.campo_artista.setText(musica["artista"] or "")
        self.aplicar_artista.setChecked(False)
        self._mostrar_capa(util.pixmap_capa(musica, 112))
        self.pilha.setCurrentWidget(self.editor)

    def _escolher_capa(self):
        caminho, _ = QFileDialog.getOpenFileName(
            self, "Trocar capa", "",
            "Imagens (*.jpg *.jpeg *.png *.webp)")
        if not caminho:
            return
        pixmap = QPixmap(caminho)
        if pixmap.isNull():
            QMessageBox.warning(
                self, "Capa inválida", "Não foi possível abrir essa imagem.")
            return
        self._capa_selecionada = caminho
        self._mostrar_capa(pixmap)

    def _mostrar_capa(self, pixmap):
        lado = self.capa.width()
        pixmap = pixmap.scaled(
            lado, lado, Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation)
        pixmap = pixmap.copy(
            (pixmap.width() - lado) // 2, (pixmap.height() - lado) // 2,
            lado, lado)
        self.capa.setPixmap(util.arredondar_capa(pixmap))

    def _copiar_capa_selecionada(self):
        origem = Path(self._capa_selecionada)
        library.PASTA_CAPAS.mkdir(parents=True, exist_ok=True)
        extensao = origem.suffix.lower() or ".jpg"
        destino = library.PASTA_CAPAS / f"{uuid.uuid4().hex[:10]}{extensao}"
        shutil.copy2(origem, destino)
        return destino.relative_to(library.RAIZ).as_posix()

    def _salvar(self):
        if self._musica is None:
            return
        titulo = self.campo_nome.text().strip()
        if not titulo:
            QMessageBox.warning(
                self, "Nome obrigatório", "Informe o nome da música.")
            self.campo_nome.setFocus()
            return

        try:
            caminho_capa = (
                self._copiar_capa_selecionada()
                if self._capa_selecionada else None)
            if self.aplicar_artista.isChecked():
                artista_antigo = (self._musica["artista"] or "").casefold()
                artista_novo = self.campo_artista.text().strip()
                for linha in db.listar_musicas():
                    musica = dict(linha)
                    if (musica["artista"] or "").casefold() == artista_antigo:
                        db.atualizar_musica(
                            musica["id"],
                            titulo if musica["id"] == self._musica["id"]
                            else musica["titulo"],
                            artista_novo)
            else:
                db.atualizar_musica(
                    self._musica["id"], titulo,
                    self.campo_artista.text().strip())
            if caminho_capa is not None:
                db.definir_capa_musica(self._musica["id"], caminho_capa)
        except OSError as erro:
            QMessageBox.warning(self, "Falha ao salvar a capa", str(erro))
            return
        except sqlite3.Error as erro:
            QMessageBox.warning(self, "Falha ao salvar", str(erro))
            self.musicas_atualizadas.emit()
            return

        self.pilha.setCurrentWidget(self.biblioteca)
        self.musicas_atualizadas.emit()

    def _cancelar(self):
        self._musica = None
        self._capa_selecionada = None
        self.pilha.setCurrentWidget(self.biblioteca)
