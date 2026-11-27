import random

from PySide6.QtCore import QEvent, QSettings, QSize, QTimer, Qt
from PySide6.QtGui import (QColor, QCursor, QFont, QKeySequence, QPainter,
                           QShortcut)
from PySide6.QtWidgets import (QButtonGroup, QFrame, QHBoxLayout, QLabel,
                               QAbstractButton, QApplication, QLineEdit,
                               QMainWindow, QMenu, QMessageBox, QPlainTextEdit,
                               QPushButton, QStackedWidget, QTextEdit,
                               QVBoxLayout, QWidget)

import db
import library
from player import Player
from ui import temas
from ui.pagina_adicionar import PaginaAdicionar
from ui.pagina_artistas import PaginaArtistas
from ui.pagina_configuracoes import PaginaConfiguracoes
from ui.pagina_editar_musicas import PaginaEditarMusicas
from ui.pagina_musicas import PaginaMusicas
from ui.pagina_playlists import PaginaPlaylists
from ui.icones import icone
from ui.decoracao import DecoracaoOverlay
from ui.janela_windows import ajustar_janela
from ui.textura import aplicar_textura
from ui.widgets_player import BarraPlayer, PainelAtual


class _FaixaHUD(QWidget):
    def __init__(self):
        super().__init__()
        self.setFixedSize(66, 3)

    def paintEvent(self, evento):
        pintor = QPainter(self)
        x = 0
        for nome_cor, largura in (
                ("hud_azul", 40), ("hud_amarelo", 14),
                ("hud_vermelho", 6)):
            pintor.fillRect(
                x, 0, largura, 3, QColor(temas.cor(nome_cor)))
            x += largura + 3
        pintor.end()


def _definir_mafty(widget, ativo):
    if not ativo:
        return
    widget.setProperty("mafty", ativo)
    estilo = widget.style()
    estilo.unpolish(widget)
    estilo.polish(widget)
    widget.update()


class JanelaPrincipal(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Sonata")
        self.resize(1280, 800)
        self.setMinimumSize(980, 600)
        self._janela_windows_ajustada = False
        tema_mafty = temas.tema_atual() == "mafty"

        self.player = Player()
        self._playlist_tocando_id = None
        self._configuracoes_reproducao = QSettings("Sonata", "Sonata")
        self._temporizador_salvamento = QTimer(self)
        self._temporizador_salvamento.setInterval(5000)
        self._temporizador_salvamento.timeout.connect(
            self._salvar_estado_se_tocando)
        self._estado_tocando_previo = False
        self._restaurando_reproducao = False
        self._atalhos = []
        self._registrar_atalhos()
        QApplication.instance().installEventFilter(self)

        # --- páginas ---
        self.pagina_musicas = PaginaMusicas("Músicas", db.listar_musicas)
        self.pagina_favoritas = PaginaMusicas("Favoritas", db.listar_favoritas)
        self.pagina_playlists = PaginaPlaylists()
        self.pagina_artistas = PaginaArtistas()
        self.pagina_adicionar = PaginaAdicionar()
        self.pagina_configuracoes = PaginaConfiguracoes()
        self.pagina_editar_musicas = PaginaEditarMusicas()

        # a posição aqui é a mesma do botão correspondente na barra lateral
        self.paginas = [self.pagina_musicas, self.pagina_favoritas,
                        self.pagina_playlists, self.pagina_artistas]

        self.pilha = QStackedWidget()
        _definir_mafty(self.pilha, tema_mafty)
        for pagina in self.paginas:                 # 0, 1, 2 e 3
            self.pilha.addWidget(pagina)
        self.pilha.addWidget(self.pagina_adicionar)  # 4
        self.pilha.addWidget(self.pagina_configuracoes)  # 5
        self.pilha.addWidget(self.pagina_editar_musicas)  # 6

        # --- barra lateral ---
        lateral = QFrame()
        lateral.setObjectName("lateral")
        _definir_mafty(lateral, tema_mafty)
        lateral.setFixedWidth(230)
        coluna = QVBoxLayout(lateral)
        coluna.setContentsMargins(12, 20, 12, 14)
        coluna.setSpacing(4)

        logo = QLabel("ソナタ")
        logo.setObjectName("logo")
        logo.setFont(QFont("Zen Maru Gothic", 24, QFont.Bold))
        secao = QLabel("BIBLIOTECA")
        secao.setObjectName("secao")
        coluna.addWidget(logo)
        if temas.cor("hud"):
            coluna.addWidget(_FaixaHUD(), 0, Qt.AlignLeft)
        coluna.addSpacing(18)
        coluna.addWidget(secao)

        self.grupo = QButtonGroup(self)
        self.grupo.setExclusive(True)
        itens_navegacao = [
            ("Músicas", "musica"),
            ("Favoritas", "coracao"),
            ("Playlists", "playlist"),
            ("Artistas", "artista"),
        ]
        for i, (nome, nome_icone) in enumerate(itens_navegacao):
            botao = QPushButton(f"  {nome}")
            botao.setObjectName("navegacao")
            botao.setIcon(icone(nome_icone, tamanho=18))
            botao.setIconSize(QSize(18, 18))
            botao.setCheckable(True)
            self.grupo.addButton(botao, i)
            coluna.addWidget(botao)
        self.grupo.button(0).setChecked(True)

        coluna.addStretch()
        btn_adicionar = QPushButton("  Adicionar música")
        btn_adicionar.setObjectName("adicionar")
        btn_adicionar.setIcon(icone("music-notes-plus-duotone", tamanho=18))
        btn_adicionar.setIconSize(QSize(18, 18))
        btn_adicionar.setCheckable(True)
        self.grupo.addButton(btn_adicionar, 4)
        coluna.addWidget(btn_adicionar)
        btn_configuracoes = QPushButton("  Configurações")
        btn_configuracoes.setObjectName("navegacao")
        btn_configuracoes.setIcon(icone("engrenagem", tamanho=18))
        btn_configuracoes.setIconSize(QSize(18, 18))
        btn_configuracoes.setCheckable(True)
        self.grupo.addButton(btn_configuracoes, 5)
        coluna.addWidget(btn_configuracoes)

        self.grupo.idClicked.connect(self._ir_para)

        # --- painel da direita e barra de baixo ---
        self.painel = PainelAtual()
        self.barra = BarraPlayer(self.player)
        _definir_mafty(self.painel, tema_mafty)
        _definir_mafty(self.barra, tema_mafty)

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

        superficies_texturizadas = (lateral, self.painel)
        if not tema_mafty:
            superficies_texturizadas += (self.barra,)
        for superficie in superficies_texturizadas:
            aplicar_textura(superficie)
        self.decoracao = DecoracaoOverlay(self.pilha)
        self.textura_pilha = aplicar_textura(self.pilha)
        self._elevar_overlays()
        self.pilha.currentChanged.connect(self._elevar_overlays)

        # --- ligações ---
        for pagina in self.paginas:
            if pagina is self.pagina_playlists:
                pagina.tocar.connect(self._tocar_playlist)
                pagina.tocar_aleatorio.connect(self._tocar_aleatorio_playlist)
            else:
                pagina.tocar.connect(self._tocar)
                pagina.tocar_aleatorio.connect(self._tocar_aleatorio)
            pagina.acao_musica.connect(self._acao_musica)
        self.pagina_playlists.playlist_reordenada.connect(
            self._ao_reordenar_playlist)
        self.player.musica_mudou.connect(self._ao_mudar_musica)
        self.player.estado_mudou.connect(self.painel.definir_tocando)
        self.player.estado_mudou.connect(self._ao_mudar_estado_reproducao)
        self.painel.conectar_player(self.player)
        self.barra.favoritar.connect(self._alternar_favorita)
        self.barra.btn_fila.clicked.connect(self._abrir_fila)
        self.painel.favoritar.connect(self._alternar_favorita)
        self.painel.painel_mudou.connect(
            lambda nome: self.barra.btn_fila.setChecked(nome == "fila"))
        self.painel.artista_clicado.connect(self._abrir_artista_do_painel)
        self.pagina_adicionar.adicionadas.connect(self.recarregar)
        self.pagina_configuracoes.editar_musicas.connect(
            self._abrir_edicao_musicas)
        self.pagina_editar_musicas.voltar_solicitado.connect(
            lambda: self.pilha.setCurrentWidget(self.pagina_configuracoes))
        self.pagina_editar_musicas.musicas_atualizadas.connect(
            self._ao_atualizar_musicas_editadas)

        self.recarregar()
        self._restaurar_estado_reproducao()

    def _registrar_atalhos(self):
        atalhos = (
            (Qt.Key_Space, self.player.alternar),
            (Qt.Key_Right, self.player.proxima),
            (Qt.Key_Left, self.player.anterior),
        )
        for tecla, acao in atalhos:
            atalho = QShortcut(QKeySequence(tecla), self)
            atalho.setContext(Qt.WindowShortcut)
            atalho.activated.connect(
                lambda tecla=tecla, acao=acao: self._executar_atalho(
                    tecla, acao))
            self._atalhos.append(atalho)

    def _executar_atalho(self, tecla, acao):
        foco = QApplication.focusWidget()
        if isinstance(foco, (QLineEdit, QTextEdit, QPlainTextEdit)):
            return
        if tecla == Qt.Key_Space and isinstance(foco, QAbstractButton):
            return
        acao()

    def eventFilter(self, observado, evento):
        if (evento.type() == QEvent.Type.KeyPress
                and evento.key() == Qt.Key_Space
                and isinstance(QApplication.focusWidget(), QAbstractButton)):
            return True
        return super().eventFilter(observado, evento)

    def showEvent(self, evento):
        super().showEvent(evento)
        if not self._janela_windows_ajustada:
            self._janela_windows_ajustada = True
            ajustar_janela(self)

    def _elevar_overlays(self, indice=None):
        self.decoracao.raise_()
        if self.textura_pilha is not None:
            self.textura_pilha.raise_()

    def recarregar(self):
        for pagina in self.paginas:
            pagina.carregar()
        self.pagina_editar_musicas.carregar()

    def _salvar_estado_reproducao(self):
        musica = self.player.musica_atual
        if musica is None:
            return
        self._configuracoes_reproducao.setValue(
            "reproducao/musica_id", musica["id"])
        self._configuracoes_reproducao.setValue(
            "reproducao/posicao_ms", self.player.posicao_ms)
        self._configuracoes_reproducao.sync()

    def _salvar_estado_se_tocando(self):
        if self.player.tocando:
            self._salvar_estado_reproducao()

    def _ao_mudar_estado_reproducao(self, tocando):
        if self._restaurando_reproducao:
            self._estado_tocando_previo = tocando
            self._temporizador_salvamento.stop()
            return
        if tocando:
            self._salvar_estado_reproducao()
            self._temporizador_salvamento.start()
        else:
            self._temporizador_salvamento.stop()
            if self._estado_tocando_previo:
                self._salvar_estado_reproducao()
        self._estado_tocando_previo = tocando

    def _limpar_estado_reproducao(self):
        self._configuracoes_reproducao.remove("reproducao/musica_id")
        self._configuracoes_reproducao.remove("reproducao/posicao_ms")
        self._configuracoes_reproducao.sync()

    def _restaurar_estado_reproducao(self):
        chave_id = "reproducao/musica_id"
        if not self._configuracoes_reproducao.contains(chave_id):
            return
        try:
            musica_id = int(self._configuracoes_reproducao.value(chave_id))
        except (TypeError, ValueError):
            self._limpar_estado_reproducao()
            return

        musica = db.obter_musica(musica_id)
        if musica is None or not (
                library.RAIZ / musica["caminho"]).is_file():
            self._limpar_estado_reproducao()
            return

        musicas = [dict(linha) for linha in db.listar_musicas()]
        indice = next(
            (i for i, linha in enumerate(musicas)
             if linha["id"] == musica_id), None)
        if indice is None:
            self._limpar_estado_reproducao()
            return

        try:
            posicao_ms = int(self._configuracoes_reproducao.value(
                "reproducao/posicao_ms", 0))
        except (TypeError, ValueError):
            posicao_ms = 0

        self._restaurando_reproducao = True
        try:
            restaurado = self.player.carregar_lista_pausada(
                musicas, indice, posicao_ms)
        finally:
            self._restaurando_reproducao = False
        if not restaurado:
            self._limpar_estado_reproducao()

    def closeEvent(self, evento):
        self._temporizador_salvamento.stop()
        self._salvar_estado_reproducao()
        super().closeEvent(evento)

    def _abrir_edicao_musicas(self):
        self.pagina_editar_musicas.carregar()
        self.pilha.setCurrentWidget(self.pagina_editar_musicas)

    def _ao_atualizar_musicas_editadas(self):
        self.recarregar()
        musica_id = self.barra.musica_id
        if musica_id is None:
            return
        musica = db.obter_musica(musica_id)
        if musica is not None:
            self.barra.mostrar_musica(musica)
            self.painel.mostrar_musica(musica)

    def _abrir_artista_do_painel(self, nome):
        self.grupo.button(3).setChecked(True)
        self.pilha.setCurrentWidget(self.pagina_artistas)
        self.pagina_artistas.abrir_artista(nome)

    def _ir_para(self, indice):
        self.pilha.setCurrentIndex(indice)
        if indice < len(self.paginas):
            self.paginas[indice].carregar()

    def _tocar(self, musicas, indice):
        self._playlist_tocando_id = None
        self.player.tocar_lista(musicas, indice)

    def _tocar_playlist(self, musicas, indice):
        self._playlist_tocando_id = self.pagina_playlists.playlist_id
        self.player.tocar_lista(musicas, indice)

    def _tocar_aleatorio(self, musicas):
        self._playlist_tocando_id = None
        self.barra.btn_shuffle.setChecked(True)
        self.player.tocar_lista(musicas, random.randrange(len(musicas)))

    def _tocar_aleatorio_playlist(self, musicas):
        self._playlist_tocando_id = self.pagina_playlists.playlist_id
        self.barra.btn_shuffle.setChecked(True)
        self.player.tocar_lista(musicas, random.randrange(len(musicas)))

    def _ao_reordenar_playlist(self, playlist_id):
        if self._playlist_tocando_id != playlist_id:
            return
        musicas = db.listar_musicas_da_playlist(playlist_id)
        self.player.reordenar_fila_playlist(musicas)

    def _ao_mudar_musica(self, m):
        if m is None:   # a fila acabou (por exemplo, a música tocando foi excluída)
            self._playlist_tocando_id = None
            self.barra.mostrar_musica(None)
            self.painel.mostrar_musica(None)
            for pagina in self.paginas:
                pagina.marcar_tocando(None)
            self.pagina_editar_musicas.marcar_tocando(None)
            return
        atual = db.obter_musica(m["id"]) or m   # lê o estado mais novo no banco
        self.barra.mostrar_musica(atual)
        self.painel.mostrar_musica(atual)
        for pagina in self.paginas:
            pagina.marcar_tocando(m["id"])
        self.pagina_editar_musicas.marcar_tocando(m["id"])
        if not self._restaurando_reproducao:
            self._salvar_estado_reproducao()

    def _abrir_fila(self):
        self.painel.show()
        self.painel.abrir_fila()

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
        elif nome == "fila":
            self.player.adicionar_na_fila(musica)
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