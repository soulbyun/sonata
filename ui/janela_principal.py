import random

from PySide6.QtCore import Qt
from PySide6.QtGui import QCursor, QFont
from PySide6.QtWidgets import (QButtonGroup, QFrame, QHBoxLayout, QLabel,
                               QMainWindow, QMenu, QMessageBox, QPushButton,
                               QStackedWidget, QVBoxLayout, QWidget)

import db
import library
from player import Player
from ui.pagina_adicionar import PaginaAdicionar
from ui.pagina_artistas import PaginaArtistas
from ui.pagina_configuracoes import PaginaConfiguracoes
from ui.pagina_musicas import PaginaMusicas
from ui.pagina_playlists import PaginaPlaylists
from ui.widgets_player import BarraPlayer, PainelAtual


class JanelaPrincipal(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Sonata")
        self.resize(1280, 800)
        self.setMinimumSize(980, 600)

        self.player = Player()

        # --- páginas ---
        self.pagina_musicas = PaginaMusicas("Músicas", db.listar_musicas)
        self.pagina_favoritas = PaginaMusicas("Favoritas", db.listar_favoritas)
        self.pagina_playlists = PaginaPlaylists()
        self.pagina_artistas = PaginaArtistas()
        self.pagina_adicionar = PaginaAdicionar()
        self.pagina_configuracoes = PaginaConfiguracoes()

        # a posição aqui é a mesma do botão correspondente na barra lateral
        self.paginas = [self.pagina_musicas, self.pagina_favoritas,
                        self.pagina_playlists, self.pagina_artistas]

        self.pilha = QStackedWidget()
        for pagina in self.paginas:                 # 0, 1, 2 e 3
            self.pilha.addWidget(pagina)
        self.pilha.addWidget(self.pagina_adicionar)  # 4
        self.pilha.addWidget(self.pagina_configuracoes)  # 5

        # --- barra lateral ---
        lateral = QFrame()
        lateral.setObjectName("lateral")
        lateral.setFixedWidth(230)
        coluna = QVBoxLayout(lateral)
        coluna.setContentsMargins(12, 20, 12, 14)
        coluna.setSpacing(4)

        logo = QLabel("ソナタ")
        logo.setObjectName("logo")
        logo.setFont(QFont("Zen Maru Gothic"))
        secao = QLabel("BIBLIOTECA")
        secao.setObjectName("secao")
        coluna.addWidget(logo)
        coluna.addSpacing(18)
        coluna.addWidget(secao)

        self.grupo = QButtonGroup(self)
        self.grupo.setExclusive(True)
        for i, nome in enumerate(["Músicas", "Favoritas", "Playlists", "Artistas"]):
            botao = QPushButton(nome)
            botao.setObjectName("navegacao")
            botao.setCheckable(True)
            self.grupo.addButton(botao, i)
            coluna.addWidget(botao)
        self.grupo.button(0).setChecked(True)

        coluna.addStretch()
        btn_adicionar = QPushButton("+  Adicionar música")
        btn_adicionar.setObjectName("adicionar")
        btn_adicionar.setCheckable(True)
        self.grupo.addButton(btn_adicionar, 4)
        coluna.addWidget(btn_adicionar)
        btn_configuracoes = QPushButton("⚙  Configurações")
        btn_configuracoes.setObjectName("navegacao")
        btn_configuracoes.setCheckable(True)
        self.grupo.addButton(btn_configuracoes, 5)
        coluna.addWidget(btn_configuracoes)

        self.grupo.idClicked.connect(self._ir_para)

        # --- painel da direita e barra de baixo ---
        self.painel = PainelAtual()
        self.barra = BarraPlayer(self.player)

        # --- montagem ---
        central = QWidget()
        self.setCentralWidget(central)
        raiz = QVBoxLayout(central)
        raiz.setContentsMargins(0, 0, 0, 0)
        raiz.setSpacing(0)
        corpo = QHBoxLayout()
        corpo.setSpacing(0)
        corpo.addWidget(lateral)
        corpo.addWidget(self.pilha, 1)
        corpo.addWidget(self.painel)
        raiz.addLayout(corpo, 1)
        raiz.addWidget(self.barra)

        # --- ligações ---
        for pagina in self.paginas:
            pagina.tocar.connect(self._tocar)
            pagina.tocar_aleatorio.connect(self._tocar_aleatorio)
            pagina.acao_musica.connect(self._acao_musica)
        self.player.musica_mudou.connect(self._ao_mudar_musica)
        self.barra.favoritar.connect(self._alternar_favorita)
        self.painel.favoritar.connect(self._alternar_favorita)
        self.pagina_adicionar.adicionadas.connect(self.recarregar)

        self.recarregar()

    def recarregar(self):
        for pagina in self.paginas:
            pagina.carregar()

    def _ir_para(self, indice):
        self.pilha.setCurrentIndex(indice)
        if indice < len(self.paginas):
            self.paginas[indice].carregar()

    def _tocar(self, musicas, indice):
        self.player.tocar_lista(musicas, indice)

    def _tocar_aleatorio(self, musicas):
        self.barra.btn_shuffle.setChecked(True)
        self.player.tocar_lista(musicas, random.randrange(len(musicas)))

    def _ao_mudar_musica(self, m):
        if m is None:   # a fila acabou (por exemplo, a música tocando foi excluída)
            self.barra.mostrar_musica(None)
            self.painel.mostrar_musica(None)
            for pagina in self.paginas:
                pagina.marcar_tocando(None)
            return
        atual = db.obter_musica(m["id"]) or m   # lê o estado mais novo no banco
        self.barra.mostrar_musica(atual)
        self.painel.mostrar_musica(atual)
        for pagina in self.paginas:
            pagina.marcar_tocando(m["id"])

    def _alternar_favorita(self, musica_id):
        db.alternar_favorita(musica_id)
        self.recarregar()
        if musica_id == self.barra.musica_id:   # só atualiza se for a que está tocando
            atual = db.obter_musica(musica_id)
            self.barra.mostrar_musica(atual)
            self.painel.mostrar_musica(atual)

    # ---------- menu de botão direito ----------

    def _acao_musica(self, nome, musica):
        if nome == "favoritar":
            self._alternar_favorita(musica["id"])
        elif nome == "playlist":
            self._escolher_playlist(musica)
        elif nome == "excluir":
            self._excluir_musica(musica)

    def _escolher_playlist(self, musica):
        playlists = db.listar_playlists()
        menu = QMenu(self)
        if not playlists:
            aviso = menu.addAction("Nenhuma playlist criada")
            aviso.setEnabled(False)
        for p in playlists:
            acao = menu.addAction(p["nome"].replace("&", "&&"))
            acao.triggered.connect(
                lambda checked=False, pid=p["id"]:
                self._adicionar_na_playlist(pid, musica["id"]))
        menu.exec(QCursor.pos())

    def _adicionar_na_playlist(self, playlist_id, musica_id):
        db.adicionar_na_playlist(playlist_id, musica_id)
        self.recarregar()

    def _excluir_musica(self, musica):
        caixa = QMessageBox(self)
        caixa.setWindowTitle("Excluir música")
        caixa.setText(f"Excluir \"{musica['titulo']}\" da biblioteca?")
        caixa.setInformativeText(
            "A cópia dentro do Sonata será apagada. "
            "O arquivo original continua onde estava.")
        excluir = caixa.addButton("Excluir", QMessageBox.AcceptRole)
        caixa.addButton("Cancelar", QMessageBox.RejectRole)
        caixa.exec()
        if caixa.clickedButton() != excluir:
            return

        self.player.remover_da_fila(musica["id"])   # solta o arquivo se estiver tocando
        try:
            library.excluir(musica["id"])
        except OSError as erro:
            QMessageBox.warning(self, "Não foi possível excluir", str(erro))
        self.recarregar()