from PySide6.QtCore import (QEvent, QEasingCurve, QPoint, QRect, QRectF,
                            QPropertyAnimation, QSettings, QSize,
                            QSequentialAnimationGroup, QTimer, Qt, Signal)
from PySide6.QtGui import (QColor, QCursor, QFont, QIcon, QPainter,
                           QPainterPath, QPixmap, QTransform)
from PySide6.QtWidgets import (
    QApplication, QFrame, QGraphicsOpacityEffect, QHBoxLayout, QLabel,
    QLineEdit, QPushButton, QScrollArea, QSizePolicy, QStackedLayout,
    QStackedWidget, QVBoxLayout, QWidget)

import db
from ui import pagina_musicas as modulo_pagina_musicas
from ui import temas, util
from ui.icones import icone, pixmap
from ui.pagina_artistas import PaginaArtistas
from ui.pagina_musicas import PaginaMusicas
from ui.pagina_playlists import PaginaPlaylists
from ui.texto_esteira import TextoEsteira
from ui.widgets_player import SliderClicavel


def _como_dict(musica):
    if musica is None or isinstance(musica, dict):
        return musica
    return dict(musica)


def geometria_colunas_inicio(largura):
    largura = max(0, int(largura))
    coracao = max(0, largura - 48)
    tempo = max(0, coracao - 92)
    artista = min(484, max(132, tempo - 248))
    largura_artista = max(20, min(240, tempo - artista - 8))
    return {
        "numero": 16,
        "largura_numero": 40,
        "capa": 64,
        "titulo": 112,
        "artista": artista,
        "largura_artista": largura_artista,
        "coracao": coracao,
        "largura_coracao": 28,
        "tempo": tempo,
        "largura_tempo": 64,
    }


modulo_pagina_musicas.geometria_colunas_inicio = geometria_colunas_inicio


def _pixmap_capa_inicio(musica):
    capa = util.pixmap_capa(musica, 168)
    resultado = QPixmap(capa.size())
    resultado.fill(Qt.transparent)
    painter = QPainter(resultado)
    painter.setRenderHint(QPainter.Antialiasing)
    caminho = QPainterPath()
    caminho.addRoundedRect(QRectF(capa.rect()), 3, 3)
    painter.setClipPath(caminho)
    painter.drawPixmap(0, 0, capa)
    painter.end()
    return resultado


class _LinhaTituloInicio(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.ao_redimensionar = None

    def resizeEvent(self, evento):
        super().resizeEvent(evento)
        if self.ao_redimensionar is not None:
            self.ao_redimensionar()


class _CabecalhoColunas(QWidget):
    def __init__(self, lista):
        super().__init__(lista)
        self.lista = lista
        self.setObjectName("cabecalhoMusicasInicio")
        self.setFixedHeight(30)

    def paintEvent(self, evento):
        painter = QPainter(self)
        fonte = QFont(self.font())
        fonte.setPixelSize(11)
        fonte.setLetterSpacing(QFont.AbsoluteSpacing, 1.2)
        painter.setFont(fonte)
        painter.setPen(QColor(temas.cor("texto_fraco")))
        colunas = geometria_colunas_inicio(self.width())
        painter.drawText(
            QRect(
                colunas["numero"], 0, colunas["largura_numero"],
                self.height()),
            Qt.AlignCenter, "#")
        painter.drawText(
            QRect(colunas["capa"], 0,
                  max(20, colunas["artista"] - colunas["capa"] - 8),
                  self.height()),
            Qt.AlignLeft | Qt.AlignVCenter, "TÍTULO")
        painter.drawText(
            QRect(colunas["artista"], 0, colunas["largura_artista"],
                  self.height()),
            Qt.AlignLeft | Qt.AlignVCenter, "ARTISTA")
        painter.drawText(
            QRect(
                colunas["tempo"], 0, colunas["largura_tempo"],
                self.height()),
            Qt.AlignRight | Qt.AlignVCenter, "TEMPO")
        painter.setPen(QColor(temas.cor("borda")))
        painter.drawLine(0, self.height() - 1, self.width(),
                         self.height() - 1)
        painter.end()


class _PopupFila(QFrame):
    fechou = Signal()

    def hideEvent(self, evento):
        super().hideEvent(evento)
        self.fechou.emit()


class PaginaInicio(QWidget):
    tocar = Signal(list, int)
    tocar_aleatorio = Signal(list)
    acao_musica = Signal(str, object)
    playlist_reordenada = Signal(int)
    repetir_mudou = Signal(str)

    def __init__(self, player):
        super().__init__()
        self.player = player
        self.playlist_id = None
        self._musica_atual = None
        self._duracao_ms = 0
        self._aba_atual = 0
        self._buscas = ["", "", "", ""]
        self._clique_pendente = None
        self._painel = None
        self._layout_painel = None
        self._indices_painel = {}
        self._restricoes_painel = {}
        self._painel_original_aberto = None
        self._painel_ativo = False
        self._letra_aberta = False

        raiz = QVBoxLayout(self)
        raiz.setContentsMargins(24, 18, 24, 16)
        raiz.setSpacing(12)
        self.layout_principal = raiz

        self.conteudo_inicio = QWidget()
        self.conteudo_inicio.setObjectName("conteudoInicio")
        self.conteudo_inicio.setSizePolicy(
            QSizePolicy.Expanding, QSizePolicy.Expanding)
        conteudo = QVBoxLayout(self.conteudo_inicio)
        conteudo.setContentsMargins(0, 0, 0, 0)
        conteudo.setSpacing(12)
        self.layout_principal = conteudo
        centro = QWidget()
        centro.setObjectName("centroInicio")
        layout_centro = QHBoxLayout(centro)
        layout_centro.setContentsMargins(0, 0, 0, 0)
        layout_centro.setSpacing(0)
        centro.setSizePolicy(
            QSizePolicy.Expanding, QSizePolicy.Expanding)
        layout_centro.addWidget(self.conteudo_inicio, 1)
        raiz.addWidget(centro, 1)

        titulo = QLabel("Início")
        titulo.setObjectName("tituloPagina")
        self.busca = QLineEdit()
        self.busca.setObjectName("buscaInicio")
        self.busca.setPlaceholderText("Buscar")
        self.busca.setMaximumWidth(280)
        self.busca.textChanged.connect(self._filtrar_aba)
        topo = QHBoxLayout()
        topo.addWidget(titulo)
        topo.addStretch()
        topo.addWidget(self.busca)
        conteudo.addLayout(topo)

        self.divisor_topo = self._divisor()
        conteudo.addWidget(self.divisor_topo)

        self._criar_hero(conteudo)

        self.btn_letra = QPushButton("Letra")
        self.btn_letra.setObjectName("toggleLetraInicio")
        self.btn_letra.setCheckable(True)
        self.btn_letra.setIconSize(QSize(16, 16))
        self.btn_letra.clicked.connect(self._alternar_letra)
        self._atualizar_icone_letra()
        conteudo.addWidget(self.btn_letra, 0, Qt.AlignLeft)

        self.divisor_abas = self._divisor()
        conteudo.addWidget(self.divisor_abas)

        self._criar_abas(conteudo)

        self.area_abas = QScrollArea()
        self.area_abas.setObjectName("areaAbasInicio")
        self.area_abas.setWidgetResizable(True)
        self.area_abas.setFrameShape(QFrame.NoFrame)
        self.area_abas.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.area_abas.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        conteudo.addWidget(self.area_abas, 1)

        self._criar_paginas()
        self.area_abas.setWidget(self.conteudo_abas)
        self._temporizador_clique = QTimer(self)
        self._temporizador_clique.setSingleShot(True)
        self._temporizador_clique.setInterval(
            QApplication.doubleClickInterval())
        self._temporizador_clique.timeout.connect(
            self._tocar_clique_pendente)

        self._popup_fila = _PopupFila(self, Qt.Popup)
        self._popup_fila.setObjectName("popupFilaInicio")
        self._popup_fila.setFixedWidth(280)
        self._popup_layout = QVBoxLayout(self._popup_fila)
        self._popup_layout.setContentsMargins(8, 8, 8, 8)
        self._popup_layout.setSpacing(0)
        self._popup_fila.fechou.connect(self._fila_fechada)

        self._configuracoes = QSettings("Sonata", "Sonata")
        self.volume.setValue(
            self._configuracoes.value("volume", 50, type=int))
        self.volume.valueChanged.connect(self._ao_mudar_volume)

        player.musica_mudou.connect(self._ao_mudar_musica_player)
        player.estado_mudou.connect(self._sincronizar_estado_player)
        player.posicao_mudou.connect(self._sincronizar_estado_player)
        player.duracao_mudou.connect(self._ao_mudar_duracao_player)
        player.fila_mudou.connect(self._atualizar_fila)
        self._sincronizar_estado_player()
        self._atualizar_fila()

    def _divisor(self):
        divisor = QFrame()
        divisor.setObjectName("divisor")
        divisor.setFixedHeight(1)
        return divisor

    def _criar_hero(self, raiz):
        hero = QWidget()
        hero.setObjectName("heroInicio")
        hero.setFixedSize(812, 190)
        layout_hero = QHBoxLayout(hero)
        layout_hero.setContentsMargins(0, 0, 0, 0)
        layout_hero.setSpacing(24)

        self.capa = QLabel()
        self.capa.setObjectName("capaInicio")
        self.capa.setFixedSize(168, 168)
        self.capa.setAlignment(Qt.AlignCenter)
        self.capa.setPixmap(_pixmap_capa_inicio(None))
        self.selo_formato = QLabel()
        self.selo_formato.setObjectName("seloInicio")
        self.selo_formato.setAlignment(Qt.AlignCenter)
        self.selo_formato.hide()
        sobreposicao = QStackedLayout()
        sobreposicao.setStackingMode(QStackedLayout.StackAll)
        sobreposicao.setContentsMargins(0, 0, 0, 0)
        sobreposicao.addWidget(self.capa)
        sobreposicao.addWidget(self.selo_formato)
        sobreposicao.setAlignment(self.selo_formato, Qt.AlignRight | Qt.AlignBottom)
        recipiente_capa = QWidget()
        recipiente_capa.setFixedSize(168, 168)
        recipiente_capa.setLayout(sobreposicao)
        layout_hero.addWidget(recipiente_capa)

        informacoes = QWidget()
        informacoes.setFixedSize(620, 190)
        informacoes.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        coluna_info = QVBoxLayout(informacoes)
        coluna_info.setContentsMargins(0, 0, 0, 0)
        coluna_info.setSpacing(0)
        coluna_info.addStretch()
        self.status = QLabel("")
        self.status.setObjectName("statusInicio")
        self.status.setFixedHeight(14)
        coluna_info.addWidget(self.status)
        coluna_info.addSpacing(6)

        self.titulo_musica = TextoEsteira("Nada tocando")
        self.titulo_musica.setObjectName("tituloMusicaInicio")
        self.titulo_musica.setSizePolicy(
            QSizePolicy.Ignored, QSizePolicy.Fixed)
        self.titulo_musica.setFixedHeight(42)
        self.artista_musica = TextoEsteira("")
        self.artista_musica.setObjectName("artistaMusicaInicio")
        self.artista_musica.setSizePolicy(
            QSizePolicy.Ignored, QSizePolicy.Fixed)
        self.artista_musica.setFixedHeight(36)
        self.artista_musica.setCursor(Qt.PointingHandCursor)
        self.artista_musica.installEventFilter(self)
        self.btn_favorita = QPushButton()
        self.btn_favorita.setObjectName("coracao")
        self.btn_favorita.setFixedSize(34, 34)
        self.btn_favorita.setIconSize(QSize(20, 20))
        self.btn_favorita.setToolTip("Favoritar")
        self.btn_favorita.clicked.connect(self._alternar_favorita)
        self.linha_titulo = _LinhaTituloInicio()
        self.linha_titulo.setObjectName("linhaTituloInicio")
        self.linha_titulo.setFixedHeight(42)
        self.titulo_musica.setParent(self.linha_titulo)
        self.artista_musica.setParent(self.linha_titulo)
        linha_com_favorito = QHBoxLayout()
        linha_com_favorito.setContentsMargins(0, 0, 0, 0)
        linha_com_favorito.setSpacing(16)
        linha_com_favorito.addWidget(self.linha_titulo, 1)
        linha_com_favorito.addWidget(self.btn_favorita)
        coluna_info.addLayout(linha_com_favorito)
        coluna_info.addSpacing(10)

        self.efeito_texto = QGraphicsOpacityEffect(self.linha_titulo)
        self.linha_titulo.setGraphicsEffect(self.efeito_texto)
        self.animacao_texto_saida = QPropertyAnimation(
            self.efeito_texto, b"opacity", self)
        self.animacao_texto_saida.setDuration(75)
        self.animacao_texto_saida.setEasingCurve(
            QEasingCurve.InOutCubic)
        self.animacao_texto_saida.setStartValue(1.0)
        self.animacao_texto_saida.setEndValue(0.0)
        self.animacao_texto_entrada = QPropertyAnimation(
            self.efeito_texto, b"opacity", self)
        self.animacao_texto_entrada.setDuration(75)
        self.animacao_texto_entrada.setEasingCurve(
            QEasingCurve.InOutCubic)
        self.animacao_texto_entrada.setStartValue(0.0)
        self.animacao_texto_entrada.setEndValue(1.0)
        self.grupo_animacao_texto = QSequentialAnimationGroup(self)
        self.grupo_animacao_texto.addAnimation(
            self.animacao_texto_saida)
        self.grupo_animacao_texto.addAnimation(
            self.animacao_texto_entrada)
        self.grupo_animacao_texto.currentAnimationChanged.connect(
            self._ao_mudar_fase_texto)
        self.grupo_animacao_texto.finished.connect(
            lambda: self.efeito_texto.setOpacity(1.0))
        self._textos_pendentes = None
        self._animacao_artista = QPropertyAnimation(
            self.artista_musica, b"pos", self)
        self._animacao_artista.setDuration(200)
        self._animacao_artista.setEasingCurve(
            QEasingCurve.InOutCubic)
        self.linha_titulo.ao_redimensionar = (
            self._reposicionar_titulo_artista)

        self.tempo_atual = QLabel("0:00")
        self.tempo_atual.setObjectName("tempoInicio")
        self.tempo_total = QLabel("0:00")
        self.tempo_total.setObjectName("tempoInicio")
        self.slider_progresso = SliderClicavel(Qt.Horizontal)
        self.slider_progresso.setObjectName("sliderInicio")
        self.slider_progresso.setRange(0, 0)
        self.slider_progresso.setMinimumWidth(120)
        self.slider_progresso.setFixedHeight(20)
        self.slider_progresso.setSizePolicy(
            QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.slider_progresso.sliderMoved.connect(self.player.buscar)
        self.tempo_atual.setFixedHeight(20)
        self.tempo_total.setFixedHeight(20)
        linha_progresso = QHBoxLayout()
        linha_progresso.setContentsMargins(0, 0, 0, 0)
        linha_progresso.setSpacing(8)
        linha_progresso.addWidget(self.tempo_atual)
        linha_progresso.addWidget(self.slider_progresso, 1)
        linha_progresso.addWidget(self.tempo_total)
        coluna_info.addLayout(linha_progresso)
        coluna_info.addSpacing(10)

        linha_controles = QWidget()
        linha_controles.setFixedHeight(48)
        layout_controles = QHBoxLayout(linha_controles)
        layout_controles.setContentsMargins(0, 0, 0, 0)
        layout_controles.setSpacing(0)

        self.btn_shuffle = self._botao_icone("shuffle", 20)
        self.btn_shuffle.setCheckable(True)
        self.btn_shuffle.toggled.connect(self.player.definir_shuffle)
        self.btn_anterior = self._botao_icone("rewind", 20)
        self.btn_anterior.clicked.connect(self.player.anterior)
        self.btn_play = QPushButton()
        self.btn_play.setObjectName("botaoPlay")
        self.btn_play.setProperty("playInicio", True)
        self.btn_play.setFixedSize(48, 48)
        self.btn_play.setIconSize(QSize(20, 20))
        self.btn_play.clicked.connect(self.player.alternar)
        self.btn_proxima = self._botao_icone("fast-forward", 20)
        self.btn_proxima.clicked.connect(self.player.proxima)
        self.btn_repetir = self._botao_icone("repeat", 20)
        self.btn_repetir.setCheckable(True)
        self.btn_repetir.clicked.connect(self._ciclar_repeticao)
        self.btn_repetir.setToolTip("Repetir fila")

        self._botoes_controle = [
            self.btn_shuffle, self.btn_anterior, self.btn_play,
            self.btn_proxima, self.btn_repetir]
        layout_controles.addSpacing(178)
        for indice, botao in enumerate(self._botoes_controle):
            if indice:
                layout_controles.addSpacing(18)
            layout_controles.addWidget(botao)
        layout_controles.addStretch()

        self.btn_fila = self._botao_icone("fila", 20)
        self.btn_fila.setToolTip("Fila")
        self.btn_fila.clicked.connect(self._alternar_fila)
        layout_controles.addWidget(self.btn_fila)
        layout_controles.addSpacing(16)
        self.icone_volume = QLabel()
        self.icone_volume.setObjectName("iconeVolumeInicio")
        layout_controles.addWidget(self.icone_volume)
        layout_controles.addSpacing(8)
        self.volume = SliderClicavel(Qt.Horizontal)
        self.volume.setObjectName("volumeInicio")
        self.volume.setRange(0, 100)
        self.volume.setFixedWidth(90)
        layout_controles.addWidget(self.volume)
        coluna_info.addWidget(linha_controles)
        coluna_info.addStretch()
        layout_hero.addWidget(informacoes)
        raiz.addWidget(hero, 0, Qt.AlignLeft)
        self._reposicionar_titulo_artista()

    def _reposicionar_titulo_artista(self, animar=True):
        if not hasattr(self, "linha_titulo"):
            return
        largura = self.linha_titulo.width()
        if largura <= 0:
            return

        largura_artista_total = self.artista_musica.fontMetrics().horizontalAdvance(
            self.artista_musica.text())
        largura_titulo_total = self.titulo_musica.fontMetrics().horizontalAdvance(
            self.titulo_musica.text())
        x_coracao = largura
        largura_disponivel = max(0, x_coracao)
        largura_artista = min(largura_artista_total, largura_disponivel)
        espaco = 10 if largura_artista and largura_titulo_total else 0
        largura_maxima_titulo = max(
            0, largura_disponivel - largura_artista - espaco)
        largura_titulo = min(
            largura_titulo_total, largura_maxima_titulo)
        posicao_artista = QPoint(
            largura_titulo + (espaco if largura_titulo else 0), 3)

        self.titulo_musica.setGeometry(
            0, 0, largura_titulo, self.titulo_musica.height())
        self.artista_musica.setFixedWidth(largura_artista)
        if animar and self.artista_musica.isVisible():
            self._animacao_artista.stop()
            self._animacao_artista.setStartValue(
                self.artista_musica.pos())
            self._animacao_artista.setEndValue(posicao_artista)
            self._animacao_artista.start()
        else:
            self.artista_musica.move(posicao_artista)
        self.artista_musica.setFixedHeight(36)

    def _botao_icone(self, nome, tamanho):
        botao = QPushButton()
        botao.setObjectName("botaoIcone")
        botao.setFixedSize(36, 36)
        botao.setIcon(icone(nome, tamanho=tamanho))
        botao.setIconSize(QSize(tamanho, tamanho))
        return botao

    def _criar_abas(self, raiz):
        self.abas = QWidget()
        self.abas.setObjectName("barraAbasInicio")
        linha = QHBoxLayout(self.abas)
        linha.setContentsMargins(16, 0, 0, 0)
        linha.setSpacing(20)
        self.botoes_abas = []
        self._icones_abas = []
        for indice, (nome, simbolo) in enumerate((
                ("Músicas", "musica"),
                ("Favoritas", "coracao"),
                ("Playlists", "playlist"),
                ("Artistas", "artista"))):
            botao = QPushButton(nome)
            botao.setObjectName("abaInicio")
            botao.setCheckable(True)
            botao.setIconSize(QSize(20, 16))
            botao.clicked.connect(
                lambda _marcado=False, i=indice: self._selecionar_aba(i))
            self.botoes_abas.append(botao)
            self._icones_abas.append((botao, simbolo))
            linha.addWidget(botao)
        linha.addStretch()
        self.botoes_abas[0].setChecked(True)
        self._atualizar_icones_abas()
        raiz.addWidget(self.abas)

    def _preparar_lista_inicio(self, pagina):
        topo = pagina.raiz.itemAt(0).widget()
        topo.hide()
        cabecalho = _CabecalhoColunas(pagina.lista)
        pagina.raiz.insertWidget(1, cabecalho)
        pagina.lista.setObjectName("listaInicioMusicas")
        pagina.delegate.modo_colunas_inicio = True
        pagina.lista.itemClicked.connect(
            lambda item, p=pagina: self._clique_na_lista(p, item))
        pagina.lista.itemDoubleClicked.connect(
            lambda _item: self._cancelar_clique_pendente())

    def _criar_paginas(self):
        self.pagina_musicas = PaginaMusicas("Músicas", db.listar_musicas)
        self.pagina_favoritas = PaginaMusicas(
            "Favoritas", db.listar_favoritas)
        self._preparar_lista_inicio(self.pagina_musicas)
        self._preparar_lista_inicio(self.pagina_favoritas)

        self.pagina_playlists = PaginaPlaylists()
        self.pagina_artistas = PaginaArtistas()
        self.pagina_artistas.busca.hide()
        self.conteudo_abas = QStackedWidget()
        self.conteudo_abas.setObjectName("conteudoAbasInicio")
        for pagina in (
                self.pagina_musicas, self.pagina_favoritas,
                self.pagina_playlists, self.pagina_artistas):
            self.conteudo_abas.addWidget(pagina)

        for pagina in (self.pagina_musicas, self.pagina_favoritas,
                       self.pagina_artistas):
            pagina.tocar.connect(self._tocar_lista)
            pagina.tocar_aleatorio.connect(self._tocar_aleatorio_lista)
            pagina.acao_musica.connect(self.acao_musica)

        self.pagina_playlists.tocar.connect(self._tocar_playlist)
        self.pagina_playlists.tocar_aleatorio.connect(
            self._tocar_aleatorio_playlist)
        self.pagina_playlists.acao_musica.connect(self.acao_musica)
        self.pagina_playlists.playlist_reordenada.connect(
            self.playlist_reordenada)

    def conectar_painel(self, painel):
        self._painel = painel
        self._layout_painel = painel.layout()
        self._indices_painel = {
            painel.area_letra: self._layout_painel.indexOf(painel.area_letra),
            painel.area_fila: self._layout_painel.indexOf(painel.area_fila),
        }
        self._restricoes_painel = {
            painel.area_letra: (
                painel.area_letra.minimumHeight(),
                painel.area_letra.maximumHeight()),
            painel.area_fila: (
                painel.area_fila.minimumHeight(),
                painel.area_fila.maximumHeight()),
        }

    def entrar(self):
        if self._painel is None or self._painel_ativo:
            return
        self._painel_ativo = True
        self._painel_original_aberto = self._painel._painel_aberto
        self._painel._definir_painel(None)

        area_letra = self._painel.area_letra
        area_fila = self._painel.area_fila
        self._layout_painel.removeWidget(area_letra)
        self._layout_painel.removeWidget(area_fila)
        area_letra.setMinimumHeight(0)
        area_letra.setMaximumHeight(140)
        area_letra.setFixedHeight(140)
        area_fila.setFixedHeight(228)
        self.layout_principal.insertWidget(
            self.layout_principal.indexOf(self.divisor_abas),
            area_letra)
        self._popup_layout.addWidget(area_fila)
        self._letra_aberta = False
        self.btn_letra.setChecked(False)
        area_letra.hide()
        self._atualizar_icone_letra()
        self._sincronizar_estado_player()

    def sair(self):
        if self._painel is None or not self._painel_ativo:
            return
        self._cancelar_clique_pendente()
        self._popup_fila.hide()
        area_letra = self._painel.area_letra
        area_fila = self._painel.area_fila
        self.layout_principal.removeWidget(area_letra)
        self._popup_layout.removeWidget(area_fila)
        for widget in (area_letra, area_fila):
            minimo, maximo = self._restricoes_painel[widget]
            widget.setMinimumHeight(minimo)
            widget.setMaximumHeight(maximo)
        self._layout_painel.insertWidget(
            self._indices_painel[area_letra], area_letra, 1)
        self._layout_painel.insertWidget(
            self._indices_painel[area_fila], area_fila, 1)
        self._painel._definir_painel(self._painel_original_aberto)
        self._painel_ativo = False
        self._painel_original_aberto = None

    def carregar(self):
        self.pagina_musicas.carregar()
        self.pagina_favoritas.carregar()
        self.pagina_playlists.carregar()
        self.pagina_artistas.carregar()
        self._filtrar_aba(self.busca.text())

    def marcar_tocando(self, musica_id):
        self.pagina_musicas.marcar_tocando(musica_id)
        self.pagina_favoritas.marcar_tocando(musica_id)
        self.pagina_playlists.marcar_tocando(musica_id)
        self.pagina_artistas.marcar_tocando(musica_id)

    def mostrar_musica(self, musica):
        musica = _como_dict(musica)
        self._musica_atual = musica
        if musica is None:
            self.capa.setPixmap(_pixmap_capa_inicio(None))
            self.selo_formato.clear()
            self.selo_formato.hide()
            self._definir_textos_musica("Nada tocando", "")
            self.btn_favorita.setEnabled(False)
            self._atualizar_duracao(0)
            self._atualizar_posicao(0)
        else:
            self.capa.setPixmap(_pixmap_capa_inicio(musica))
            formato = musica.get("formato") or ""
            self.selo_formato.setText(formato.upper())
            artista = musica["artista"] or "Artista desconhecido"
            self._definir_textos_musica(
                musica["titulo"], f"— {artista}")
            self.btn_favorita.setEnabled(True)
            self._atualizar_duracao(
                max(0, int(musica.get("duracao") or 0)) * 1000)
            self._atualizar_posicao(self.player.posicao_ms)
        self._atualizar_icone_favorita()
        self._atualizar_estado(self.player.tocando)

    def atualizar_tema(self):
        self._atualizar_icones_abas()
        for botao, nome, tamanho in (
                (self.btn_shuffle, "shuffle", 20),
                (self.btn_anterior, "rewind", 20),
                (self.btn_proxima, "fast-forward", 20),
                (self.btn_repetir, "repeat", 20),
                (self.btn_fila, "fila", 20)):
            botao.setIcon(icone(nome, tamanho=tamanho))
        self.slider_progresso.atualizar_tema()
        self.volume.atualizar_tema()
        for pagina in (
                self.pagina_musicas, self.pagina_favoritas,
                self.pagina_playlists, self.pagina_artistas):
            pagina.atualizar_tema()
        self._atualizar_icone_letra()
        self._atualizar_icone_favorita()
        self._atualizar_volume()
        self._atualizar_estado(self.player.tocando)
        self._atualizar_fila()

    def _atualizar_icones_abas(self):
        for botao, simbolo in self._icones_abas:
            icone_original = icone(simbolo, tamanho=16).pixmap(16, 16)
            com_espaco = QPixmap(20, 16)
            com_espaco.fill(Qt.transparent)
            painter = QPainter(com_espaco)
            painter.drawPixmap(0, 0, icone_original)
            painter.end()
            botao.setIcon(QIcon(com_espaco))

    def _definir_textos_musica(self, titulo, artista):
        textos = (titulo, artista)
        atuais = (
            self.titulo_musica.text(), self.artista_musica.text())
        if textos == atuais:
            if self._textos_pendentes is not None:
                self.grupo_animacao_texto.stop()
                self._textos_pendentes = None
                self.efeito_texto.setOpacity(1.0)
            return
        if textos == self._textos_pendentes:
            return
        if not atuais[0]:
            self.titulo_musica.setText(titulo)
            self.artista_musica.setText(artista)
            self._reposicionar_titulo_artista(False)
            return
        self.grupo_animacao_texto.stop()
        self.efeito_texto.setOpacity(1.0)
        self._textos_pendentes = textos
        self.grupo_animacao_texto.start()

    def _ao_mudar_fase_texto(self, animacao):
        if (animacao is self.animacao_texto_entrada
                and self._textos_pendentes is not None):
            titulo, artista = self._textos_pendentes
            self.titulo_musica.setText(titulo)
            self.artista_musica.setText(artista)
            self._reposicionar_titulo_artista()
            self._textos_pendentes = None

    def _ao_mudar_musica_player(self, *_):
        self._atualizar_estado_do_player(forcar_musica=True)

    def _ao_mudar_duracao_player(self, duracao):
        self._atualizar_estado_do_player(duracao_ms=duracao)

    def _sincronizar_estado_player(self, *_):
        self._atualizar_estado_do_player()

    def _atualizar_estado_do_player(
            self, forcar_musica=False, duracao_ms=None):
        musica = _como_dict(self.player.musica_atual)
        id_exibido = (
            _como_dict(self._musica_atual).get("id")
            if self._musica_atual is not None else None)
        if musica is None:
            if forcar_musica or id_exibido is not None:
                self.mostrar_musica(None)
            self._atualizar_duracao(0)
            self._atualizar_posicao(0)
        else:
            if forcar_musica or musica.get("id") != id_exibido:
                self.mostrar_musica(musica)
            if duracao_ms is not None:
                self._atualizar_duracao(duracao_ms)
            elif self._duracao_ms == 0:
                self._atualizar_duracao(
                    max(0, int(musica.get("duracao") or 0)) * 1000)
            self._atualizar_posicao(self.player.posicao_ms)
        self._atualizar_estado(self.player.tocando)

    def _selecionar_aba(self, indice):
        if indice == self._aba_atual:
            return
        self._cancelar_clique_pendente()
        self._buscas[self._aba_atual] = self.busca.text()
        self._aba_atual = indice
        self.conteudo_abas.setCurrentIndex(indice)
        for i, botao in enumerate(self.botoes_abas):
            botao.setChecked(i == indice)
        self.busca.blockSignals(True)
        self.busca.setText(self._buscas[indice])
        self.busca.blockSignals(False)
        self._filtrar_aba(self._buscas[indice])

    def _filtrar_aba(self, texto):
        if not hasattr(self, "pagina_musicas"):
            return
        self._buscas[self._aba_atual] = texto
        pagina = self.conteudo_abas.widget(self._aba_atual)
        if self._aba_atual in (0, 1, 3):
            pagina.busca.setText(texto)
        else:
            termo = texto.strip().casefold()
            for playlist in self.pagina_playlists._playlists_palco:
                botao = self.pagina_playlists._botoes_playlist.get(
                    playlist["id"])
                if botao is not None:
                    botao.setVisible(termo in playlist["nome"].casefold())
            self.pagina_playlists.layout_seletor.invalidate()
            self.pagina_playlists.seletor_playlists.updateGeometry()

    def _clique_na_lista(self, pagina, item):
        ponto = pagina.lista.viewport().mapFromGlobal(QCursor.pos())
        colunas = geometria_colunas_inicio(
            pagina.lista.viewport().width())
        if (colunas["artista"] <= ponto.x()
                < colunas["artista"] + colunas["largura_artista"]):
            self._cancelar_clique_pendente()
            indice = pagina.lista.row(item)
            if not 0 <= indice < len(pagina.exibidas):
                return
            artista = (
                pagina.exibidas[indice]["artista"]
                or "Artista desconhecido")
            self._abrir_artista(artista)
            return
        self._clique_pendente = (pagina, item)
        self._temporizador_clique.start()

    def _cancelar_clique_pendente(self):
        self._temporizador_clique.stop()
        self._clique_pendente = None

    def _tocar_clique_pendente(self):
        if self._clique_pendente is None:
            return
        pagina, item = self._clique_pendente
        self._clique_pendente = None
        indice = pagina.lista.row(item)
        if not 0 <= indice < len(pagina.exibidas):
            return
        pagina.tocar.emit(pagina.exibidas, indice)

    def _abrir_artista(self, artista):
        self._selecionar_aba(3)
        self.pagina_artistas.abrir_artista(artista)

    def eventFilter(self, observado, evento):
        if (observado is self.artista_musica
                and evento.type() == QEvent.Type.MouseButtonRelease
                and evento.button() == Qt.LeftButton
                and self._musica_atual is not None):
            self._abrir_artista(
                self._musica_atual["artista"] or "Artista desconhecido")
            return True
        return super().eventFilter(observado, evento)

    def showEvent(self, evento):
        super().showEvent(evento)
        self._sincronizar_estado_player()

    def _tocar_lista(self, musicas, indice):
        self.playlist_id = None
        self.tocar.emit(musicas, indice)

    def _tocar_aleatorio_lista(self, musicas):
        self.playlist_id = None
        self.tocar_aleatorio.emit(musicas)

    def _tocar_playlist(self, musicas, indice):
        self.playlist_id = self.pagina_playlists.playlist_id
        self.tocar.emit(musicas, indice)

    def _tocar_aleatorio_playlist(self, musicas):
        self.playlist_id = self.pagina_playlists.playlist_id
        self.tocar_aleatorio.emit(musicas)

    def _alternar_favorita(self):
        if self._musica_atual is not None:
            self.acao_musica.emit("favoritar", self._musica_atual)

    def _atualizar_icone_favorita(self):
        favorita = (
            self._musica_atual is not None
            and bool(self._musica_atual["favorita"]))
        cor = (
            (temas.cor("hud_amarelo") or temas.cor("lilas_claro"))
            if favorita else temas.cor("texto_suave"))
        self.btn_favorita.setIcon(
            icone("coracao", cor=cor, tamanho=20, cheio=favorita))

    def _atualizar_estado(self, tocando):
        tem_musica = self._musica_atual is not None
        if not tem_musica:
            texto = ""
        else:
            texto = "TOCANDO" if tocando else "PAUSADO"
        self.status.setText(texto)
        self.btn_play.setIcon(icone(
            "pause" if tem_musica and tocando else "play",
            cor=temas.cor("texto_sobre_destaque"), tamanho=20))
        for botao in self._botoes_controle:
            botao.setEnabled(tem_musica)
        self.btn_fila.setEnabled(bool(self.player.fila))
        self._definir_marcado(self.btn_shuffle, self.player.shuffle)
        self._atualizar_repeticao()

    def _atualizar_posicao(self, posicao):
        self.tempo_atual.setText(util.fmt_tempo(max(0, posicao) // 1000))
        if not self.slider_progresso.isSliderDown():
            self.slider_progresso.setValue(posicao)

    def _atualizar_duracao(self, duracao):
        self._duracao_ms = max(0, duracao)
        self.slider_progresso.setRange(0, self._duracao_ms)
        self.tempo_total.setText(
            util.fmt_tempo(self._duracao_ms // 1000))

    def _atualizar_fila(self):
        if not hasattr(self, "btn_shuffle"):
            return
        self._definir_marcado(self.btn_shuffle, self.player.shuffle)
        self.btn_fila.setEnabled(bool(self.player.fila))

    def _definir_marcado(self, botao, marcado):
        bloqueado = botao.blockSignals(True)
        botao.setChecked(marcado)
        botao.blockSignals(bloqueado)

    def _ciclar_repeticao(self):
        modo = self.player.ciclar_repeticao()
        self._atualizar_repeticao()
        self.repetir_mudou.emit(modo)

    def sincronizar_repeticao(self):
        self._atualizar_repeticao()

    def _atualizar_repeticao(self):
        modo = self.player.repetir
        self._definir_marcado(self.btn_repetir, modo != "off")
        self.btn_repetir.setToolTip(
            "Repetir faixa" if modo == "uma" else
            "Repetir fila" if modo == "fila" else "Repetir")

    def _ao_mudar_volume(self, volume):
        self.player.definir_volume(volume)
        self._configuracoes.setValue("volume", volume)
        self._atualizar_volume()

    def sincronizar_volume(self, volume):
        bloqueado = self.volume.blockSignals(True)
        self.volume.setValue(volume)
        self.volume.blockSignals(bloqueado)
        self._atualizar_volume()

    def _atualizar_volume(self):
        nome = "speaker-slash" if self.volume.value() == 0 else "speaker-high"
        self.icone_volume.setPixmap(pixmap(
            nome, cor=temas.cor("texto_suave"), tamanho=20))

    def _atualizar_icone_letra(self):
        imagem = pixmap(
            "seta-direita", cor=temas.cor("texto_suave"), tamanho=16)
        if self._letra_aberta:
            imagem = imagem.transformed(
                QTransform().rotate(90), Qt.SmoothTransformation)
        self.btn_letra.setIcon(QIcon(imagem))

    def _alternar_letra(self):
        if self._painel is None or not self._painel_ativo:
            return
        self._letra_aberta = not self._letra_aberta
        if self._popup_fila.isVisible():
            self._popup_fila.hide()
        self._painel._definir_painel(
            "letra" if self._letra_aberta else None)
        self.btn_letra.setChecked(self._letra_aberta)
        self._atualizar_icone_letra()

    def _alternar_fila(self):
        if self._painel is None or not self._painel_ativo:
            return
        if self._popup_fila.isVisible():
            self._popup_fila.hide()
            return
        self._letra_aberta = False
        self.btn_letra.setChecked(False)
        self._atualizar_icone_letra()
        self._painel._definir_painel("fila")
        self._popup_fila.adjustSize()
        posicao = self.btn_fila.mapToGlobal(
            QPoint(0, self.btn_fila.height() + 6))
        self._popup_fila.move(posicao)
        self._popup_fila.show()

    def _fila_fechada(self):
        if self._painel is not None and self._painel_ativo:
            self._painel._definir_painel(None)
