import html

from PySide6.QtCore import (QAbstractAnimation, QEasingCurve,
                            QEvent, QPropertyAnimation, QSettings, QRect,
                            QSize, QTimer, Qt, Signal)
from PySide6.QtGui import QColor, QIcon, QPainter, QPen
from PySide6.QtWidgets import (QFrame, QGraphicsOpacityEffect, QHBoxLayout,
                               QLabel, QListWidget, QListWidgetItem,
                               QPlainTextEdit, QPushButton, QScrollArea,
                               QSizePolicy, QSlider, QStyle, QStyledItemDelegate,
                               QStyleOptionSlider, QVBoxLayout, QWidget)

import db
from ui import temas, util
from ui.icones import icone, pixmap
from ui.texto_esteira import TextoEsteira


class SliderClicavel(QSlider):
    """Slider que pula direto para o ponto onde você clica."""

    def __init__(self, *args):
        super().__init__(*args)
        self.arrastando = False
        self._icone_alca = pixmap(
            "circle-dashed-duotone", cor=temas.cor("azul_claro"), tamanho=18)

    def atualizar_tema(self):
        self._icone_alca = pixmap(
            "circle-dashed-duotone", cor=temas.cor("azul_claro"), tamanho=18)
        self.update()

    def paintEvent(self, evento):
        super().paintEvent(evento)
        opcao = QStyleOptionSlider()
        self.initStyleOption(opcao)
        alca = self.style().subControlRect(
            QStyle.CC_Slider, opcao, QStyle.SC_SliderHandle, self)
        pintor = QPainter(self)
        pintor.drawPixmap(alca, self._icone_alca)
        pintor.end()

    def _mover(self, evento):
        valor = QStyle.sliderValueFromPosition(
            self.minimum(), self.maximum(), int(evento.position().x()), self.width())
        self.setValue(valor)
        self.sliderMoved.emit(valor)

    def mousePressEvent(self, evento):
        if evento.button() == Qt.LeftButton:
            self.arrastando = True
            self._mover(evento)
            evento.accept()
        else:
            super().mousePressEvent(evento)

    def mouseMoveEvent(self, evento):
        if self.arrastando:
            self._mover(evento)

    def mouseReleaseEvent(self, evento):
        self.arrastando = False


def _estilo_coracao(botao, favorita):
    cor = (
        (temas.cor("hud_amarelo") or temas.cor("lilas_claro"))
        if favorita else temas.cor("texto_suave"))
    botao.setText("")
    botao.setIcon(icone("coracao", cor=cor, tamanho=20, cheio=favorita))
    botao.setIconSize(QSize(20, 20))


def _icone_controle(nome, tamanho, cor_padrao=None):
    amarelo = temas.cor("hud_amarelo")
    if not amarelo:
        return icone(nome, cor=cor_padrao, tamanho=tamanho)

    imagem = pixmap(nome, cor=amarelo, tamanho=tamanho)
    resultado = QIcon()
    resultado.addPixmap(imagem, QIcon.Normal, QIcon.Off)
    resultado.addPixmap(imagem, QIcon.Normal, QIcon.On)
    return resultado


class _BotaoDiscreto(QPushButton):
    def __init__(self):
        super().__init__()
        self.setObjectName("botaoIcone")
        self.setIcon(icone("pincel", cor=temas.cor("texto_suave"), tamanho=16))
        self.setIconSize(QSize(16, 16))
        self.setFixedSize(28, 28)
        self.setToolTip("Editar letra")
        self.setFocusPolicy(Qt.NoFocus)
        self._opacidade = QGraphicsOpacityEffect(self)
        self._opacidade.setOpacity(0.25)
        self.setGraphicsEffect(self._opacidade)

    def atualizar_tema(self):
        self.setIcon(icone("pincel", cor=temas.cor("texto_suave"), tamanho=16))

    def enterEvent(self, evento):
        self._opacidade.setOpacity(0.85)
        super().enterEvent(evento)

    def leaveEvent(self, evento):
        self._opacidade.setOpacity(0.25)
        super().leaveEvent(evento)


class _DelegadoFila(QStyledItemDelegate):
    def paint(self, painter, opcao, indice):
        painter.save()
        area = opcao.rect.adjusted(2, 1, -2, -1)
        if indice.data(Qt.UserRole + 2):
            painter.setPen(QColor(temas.cor("texto_suave")))
            painter.drawText(area, Qt.AlignCenter, str(indice.data(Qt.DisplayRole)))
            painter.restore()
            return

        atual = bool(indice.data(Qt.UserRole + 1))
        sobre = bool(opcao.state & QStyle.State_MouseOver)
        if atual:
            painter.fillRect(area, QColor(temas.cor("azul_escuro")))
        elif sobre:
            painter.fillRect(area, QColor(temas.cor("elevado")))

        cor_texto = temas.cor("azul_claro") if atual else temas.cor("texto")
        painter.setPen(QColor(cor_texto))
        texto = str(indice.data(Qt.DisplayRole))
        texto_area = area.adjusted(8, 0, -36, 0)
        painter.drawText(texto_area, Qt.AlignLeft | Qt.AlignVCenter, texto)

        area_botao = QRect(area.right() - 30, area.top(), 28, area.height())
        if sobre:
            painter.fillRect(area_botao, QColor(temas.cor("cartao")))
        imagem = pixmap(
            "lixeira", cor=temas.cor("texto_suave"), tamanho=16)
        painter.drawPixmap(
            area_botao.center().x() - 8,
            area_botao.center().y() - 8,
            imagem)
        painter.restore()

class _ListaFila(QListWidget):
    tocar = Signal(int)
    remover = Signal(int)

    def __init__(self):
        super().__init__()
        self.setItemDelegate(_DelegadoFila(self))
        self.setUniformItemSizes(True)
        self.setMouseTracking(True)
        self.viewport().setMouseTracking(True)
        self.setVerticalScrollMode(QListWidget.ScrollPerPixel)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setSelectionMode(QListWidget.NoSelection)
        self.setFocusPolicy(Qt.NoFocus)

    def mousePressEvent(self, evento):
        if evento.button() == Qt.LeftButton:
            ponto = evento.position().toPoint()
            item = self.itemAt(ponto)
            if item is not None:
                indice = item.data(Qt.UserRole)
                if indice is not None:
                    if ponto.x() >= self.viewport().width() - 36:
                        self.remover.emit(indice)
                    else:
                        self.tocar.emit(indice)
            evento.accept()
            return
        super().mousePressEvent(evento)


class BarraPlayer(QFrame):
    favoritar = Signal(int)   # id da música

    def __init__(self, player):
        super().__init__()
        self.setObjectName("barraPlayer")
        self.setFixedHeight(88)
        self.player = player
        self.musica_id = None
        self._musica_atual = None

        # --- esquerda: capa, nome e coração ---
        self.capa = QLabel()
        self.capa.setFixedSize(48, 48)
        self.capa.setPixmap(util.pixmap_capa(None, 48))
        self.lbl_titulo = TextoEsteira("Nada tocando")
        self.lbl_titulo.setObjectName("barraTitulo")
        self.lbl_artista = TextoEsteira("")
        self.lbl_artista.setObjectName("barraArtista")
        for rotulo in (self.lbl_titulo, self.lbl_artista):
            rotulo.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Preferred)
        textos = QVBoxLayout()
        textos.setSpacing(2)
        textos.addStretch()
        textos.addWidget(self.lbl_titulo)
        textos.addWidget(self.lbl_artista)
        textos.addStretch()
        self.btn_coracao = QPushButton()
        self.btn_coracao.setObjectName("coracao")
        self.btn_coracao.setVisible(False)
        self.btn_coracao.clicked.connect(lambda: self._clicou_coracao())
        esquerda = QHBoxLayout()
        esquerda.setSpacing(12)
        esquerda.addWidget(self.capa)
        esquerda.addLayout(textos, 1)
        esquerda.addWidget(self.btn_coracao)

        # --- centro: controles e progresso ---
        self.btn_shuffle = QPushButton()
        self.btn_shuffle.setObjectName("botaoIcone")
        self.btn_shuffle.setIcon(_icone_controle("shuffle", 18))
        self.btn_shuffle.setIconSize(QSize(18, 18))
        self.btn_shuffle.setCheckable(True)
        self.btn_shuffle.toggled.connect(player.definir_shuffle)
        self.btn_anterior = QPushButton()
        self.btn_anterior.setObjectName("botaoIcone")
        self.btn_anterior.setIcon(_icone_controle("rewind", 18))
        self.btn_anterior.setIconSize(QSize(18, 18))
        self.btn_anterior.clicked.connect(lambda: player.anterior())
        self.btn_play = QPushButton()
        self.btn_play.setObjectName("botaoPlay")
        cor_play = (
            temas.cor("hud_amarelo") or temas.cor("texto_sobre_destaque"))
        self.btn_play.setIcon(
            _icone_controle("play-duotone", 20, cor_padrao=cor_play))
        self.btn_play.setIconSize(QSize(20, 20))
        self.btn_play.clicked.connect(lambda: player.alternar())
        self.btn_proxima = QPushButton()
        self.btn_proxima.setObjectName("botaoIcone")
        self.btn_proxima.setIcon(_icone_controle("fast-forward", 18))
        self.btn_proxima.setIconSize(QSize(18, 18))
        self.btn_proxima.clicked.connect(lambda: player.proxima())
        self.btn_repetir = QPushButton("↻")
        self.btn_repetir.setObjectName("botaoIcone")
        self.btn_repetir.setCheckable(True)
        self.btn_repetir.clicked.connect(lambda: self._ciclar_repeticao())

        controles = QHBoxLayout()
        controles.setSpacing(6)
        controles.addStretch()
        for b in (self.btn_shuffle, self.btn_anterior, self.btn_play,
                  self.btn_proxima, self.btn_repetir):
            controles.addWidget(b)
        controles.addStretch()

        self.lbl_atual = QLabel("0:00")
        self.lbl_atual.setObjectName("tempo")
        self.lbl_atual.setFixedWidth(40)
        self.lbl_atual.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.lbl_total = QLabel("0:00")
        self.lbl_total.setObjectName("tempo")
        self.lbl_total.setFixedWidth(40)
        self.slider = SliderClicavel(Qt.Horizontal)
        self.slider.sliderMoved.connect(player.buscar)
        progresso = QHBoxLayout()
        progresso.addWidget(self.lbl_atual)
        progresso.addWidget(self.slider, 1)
        progresso.addWidget(self.lbl_total)

        centro = QVBoxLayout()
        centro.setSpacing(4)
        centro.addLayout(controles)
        centro.addLayout(progresso)

        # --- direita: volume ---
        self.lbl_volume = QLabel()
        self.lbl_volume.setObjectName("secao")
        self.lbl_volume.setPixmap(pixmap(
            "speaker-high-duotone",
            cor=temas.cor("hud_amarelo") or temas.cor("texto_suave"),
            tamanho=18))
        self.lbl_volume.setToolTip("Volume")
        self.volume = SliderClicavel(Qt.Horizontal)
        self.volume.setRange(0, 100)
        self._configuracoes = QSettings("Sonata", "Sonata")
        self.volume.setValue(
            self._configuracoes.value("volume", 50, type=int))
        self.volume.setFixedWidth(110)
        self.volume.valueChanged.connect(self._ao_mudar_volume)
        player.definir_volume(self.volume.value())
        direita = QHBoxLayout()
        direita.addStretch()
        self.btn_fila = QPushButton()
        self.btn_fila.setObjectName("botaoIcone")
        self.btn_fila.setIcon(_icone_controle("playlist", 18))
        self.btn_fila.setIconSize(QSize(18, 18))
        self.btn_fila.setToolTip("Fila")
        self.btn_fila.setCheckable(True)
        direita.addWidget(self.btn_fila)
        direita.addSpacing(14)
        direita.addWidget(self.lbl_volume)
        direita.addWidget(self.volume)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(14, 8, 24, 8)
        layout.addLayout(esquerda, 1)
        layout.addLayout(centro, 2)
        layout.addLayout(direita, 1)

        player.estado_mudou.connect(self._ao_mudar_estado)
        player.posicao_mudou.connect(self._ao_mudar_posicao)
        player.duracao_mudou.connect(self._ao_mudar_duracao)

    def atualizar_tema(self):
        self.btn_shuffle.setIcon(_icone_controle("shuffle", 18))
        self.btn_anterior.setIcon(_icone_controle("rewind", 18))
        self.btn_proxima.setIcon(_icone_controle("fast-forward", 18))
        self.btn_fila.setIcon(_icone_controle("playlist", 18))
        self.lbl_volume.setPixmap(pixmap(
            "speaker-high-duotone",
            cor=temas.cor("hud_amarelo") or temas.cor("texto_suave"),
            tamanho=18))
        self.slider.atualizar_tema()
        self.volume.atualizar_tema()
        self._ao_mudar_estado(self.player.tocando)
        _estilo_coracao(
            self.btn_coracao,
            self._musica_atual is not None
            and bool(self._musica_atual["favorita"]))
        self.capa.setPixmap(util.pixmap_capa(self._musica_atual, 48))
        self.lbl_titulo.update()
        self.lbl_artista.update()
        self.update()

    def _ao_mudar_estado(self, tocando):
        cor_play = (
            temas.cor("hud_amarelo") or temas.cor("texto_sobre_destaque"))
        self.btn_play.setIcon(_icone_controle(
            "pause-circle-duotone" if tocando else "play-duotone",
            20, cor_padrao=cor_play))

    def _ao_mudar_volume(self, volume):
        self.player.definir_volume(volume)
        self._configuracoes.setValue("volume", volume)

    def mostrar_musica(self, m):
        self._musica_atual = m
        self.musica_id = m["id"] if m is not None else None
        self.capa.setPixmap(util.pixmap_capa(m, 48))
        self.lbl_titulo.setText(m["titulo"] if m is not None else "Nada tocando")
        self.lbl_artista.setText(
            (m["artista"] or "Artista desconhecido") if m is not None else "")
        self.btn_coracao.setVisible(m is not None)
        _estilo_coracao(self.btn_coracao, m is not None and bool(m["favorita"]))

    def _clicou_coracao(self):
        if self.musica_id is not None:
            self.favoritar.emit(self.musica_id)

    def _ciclar_repeticao(self):
        modo = self.player.ciclar_repeticao()
        self.btn_repetir.setChecked(modo != "off")
        self.btn_repetir.setText("↻1" if modo == "uma" else "↻")

    def _ao_mudar_posicao(self, ms):
        if not self.slider.arrastando:
            self.slider.setValue(ms)
        self.lbl_atual.setText(util.fmt_tempo(ms // 1000))

    def _ao_mudar_duracao(self, ms):
        self.slider.setMaximum(ms)
        self.lbl_total.setText(util.fmt_tempo(ms // 1000))


class _PontoHUD(QFrame):
    def paintEvent(self, evento):
        pintor = QPainter(self)
        pintor.setRenderHint(QPainter.Antialiasing)
        pintor.setPen(Qt.NoPen)
        pintor.setBrush(QColor(temas.cor("hud_vermelho")))
        pintor.drawEllipse(self.rect())
        pintor.end()


class PainelAtual(QFrame):
    favoritar = Signal(int)
    artista_clicado = Signal(str)
    painel_mudou = Signal(str)

    def __init__(self):
        super().__init__()
        self.setObjectName("painelAtual")
        self.setFixedWidth(280)
        self.musica_id = None
        self.player = None
        self._letra = ""
        self._editor_letra = None
        self._painel_aberto = None
        self._ids_fila = None
        self._indice_atual_fila = -1
        self._hud = bool(temas.cor("hud"))
        self._musica_atual = None

        secao = QLabel("TOCANDO AGORA")
        secao.setObjectName("secao")
        secao.setFixedHeight(secao.sizeHint().height())
        secao.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)
        self._ponto_hud = _PontoHUD(self)
        self._ponto_hud.setFixedSize(8, 8)
        self._ponto_hud.hide()
        self._opacidade_ponto = QGraphicsOpacityEffect(self._ponto_hud)
        self._ponto_hud.setGraphicsEffect(self._opacidade_ponto)
        self._animacao_ponto = QPropertyAnimation(
            self._opacidade_ponto, b"opacity", self)
        self._animacao_ponto.setDuration(2400)
        self._animacao_ponto.setKeyValueAt(0, 1.0)
        self._animacao_ponto.setKeyValueAt(0.5, 0.35)
        self._animacao_ponto.setKeyValueAt(1, 1.0)
        self._animacao_ponto.setLoopCount(-1)
        self._animacao_ponto.setEasingCurve(QEasingCurve.InOutSine)

        linha_secao = QHBoxLayout()
        linha_secao.setContentsMargins(0, 0, 0, 0)
        linha_secao.setSpacing(6)
        linha_secao.addWidget(secao)
        if self._hud:
            linha_secao.addWidget(self._ponto_hud, 0, Qt.AlignVCenter)
        linha_secao.addStretch()
        self._linha_secao = linha_secao

        self.capa = QLabel()
        self.capa.setFixedSize(232, 232)
        self.capa.setPixmap(util.pixmap_capa(None, 232))

        self.lbl_titulo = TextoEsteira("Nada tocando")
        self.lbl_titulo.setObjectName("painelTitulo")
        self.lbl_titulo.setFixedHeight(self.lbl_titulo.sizeHint().height())
        self.lbl_artista = TextoEsteira("")
        self.lbl_artista.setObjectName("painelArtista")
        self.lbl_artista.setFixedHeight(self.lbl_artista.sizeHint().height())
        self.lbl_artista.setCursor(Qt.PointingHandCursor)
        self.lbl_artista.setToolTip("Ver artista")
        self.lbl_artista.installEventFilter(self)
        for rotulo in (self.lbl_titulo, self.lbl_artista):
            rotulo.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Fixed)

        self.btn_coracao = QPushButton()
        self.btn_coracao.setObjectName("coracao")
        self.btn_coracao.setProperty("acaoPainel", True)
        self.btn_coracao.setFixedSize(36, 36)
        self.btn_coracao.setIconSize(QSize(20, 20))
        self.btn_coracao.setToolTip("Favoritar")
        self.btn_coracao.setVisible(False)
        self.btn_coracao.clicked.connect(lambda: self._clicou_coracao())

        informacoes_musica = QVBoxLayout()
        informacoes_musica.setContentsMargins(0, 0, 0, 0)
        informacoes_musica.setSpacing(4)
        informacoes_musica.addWidget(self.lbl_titulo)
        informacoes_musica.addWidget(self.lbl_artista)

        divisor = QFrame()
        divisor.setObjectName("divisor")
        divisor.setFixedHeight(1)

        self.lbl_album = QLabel("")
        self.lbl_album.setObjectName("painelAlbum")
        self.lbl_album.setFixedHeight(self.lbl_album.sizeHint().height())
        self.lbl_album.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Fixed)
        self.lbl_album.hide()
        self.selo = QLabel("")
        self.selo.setObjectName("selo")
        self.selo.setSizePolicy(QSizePolicy.Maximum, QSizePolicy.Maximum)
        self.selo.hide()
        self._atualizar_estilo_selo()
        self.btn_letra = QPushButton()
        self.btn_letra.setObjectName("secundario")
        self.btn_letra.setProperty("acaoPainel", True)
        self.btn_letra.setIcon(icone("letra", tamanho=20))
        self.btn_letra.setIconSize(QSize(20, 20))
        self.btn_letra.setFixedSize(36, 36)
        self.btn_letra.setToolTip("Letra")
        self.btn_letra.setCheckable(True)
        self.btn_letra.setEnabled(False)
        self.btn_letra.clicked.connect(
            lambda: self._alternar_painel("letra"))
        self.btn_fila = QPushButton()
        self.btn_fila.setObjectName("secundario")
        self.btn_fila.setProperty("acaoPainel", True)
        self.btn_fila.setIcon(icone("playlist", tamanho=20))
        self.btn_fila.setIconSize(QSize(20, 20))
        self.btn_fila.setFixedSize(36, 36)
        self.btn_fila.setToolTip("Fila")
        self.btn_fila.setCheckable(True)
        self.btn_fila.clicked.connect(
            lambda: self._alternar_painel("fila"))
        linha_acoes = QWidget()
        linha_acoes.setFixedHeight(36)
        linha_acoes.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        botoes_painel = QHBoxLayout(linha_acoes)
        botoes_painel.setContentsMargins(0, 0, 0, 0)
        botoes_painel.setSpacing(10)
        botoes_painel.addStretch()
        botoes_painel.addWidget(self.btn_coracao)
        botoes_painel.addWidget(self.btn_letra)
        botoes_painel.addWidget(self.btn_fila)
        botoes_painel.addStretch()

        self.area_letra = QScrollArea()
        self.area_letra.setObjectName("areaLista")
        self.area_letra.setWidgetResizable(True)
        self.area_letra.setFrameShape(QFrame.NoFrame)
        self.area_letra.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.area_letra.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.area_letra.setMinimumHeight(220)
        self.conteudo_letra = QWidget()
        self.layout_letra = QVBoxLayout(self.conteudo_letra)
        self.layout_letra.setContentsMargins(2, 2, 2, 2)
        self.layout_letra.setSpacing(4)
        self.lbl_letra = QLabel()
        self.lbl_letra.setObjectName("letraTexto")
        self.lbl_letra.setTextFormat(Qt.PlainText)
        self.lbl_letra.setWordWrap(True)
        self.lbl_letra.setAlignment(Qt.AlignLeft | Qt.AlignTop)
        self.layout_letra.addWidget(self.lbl_letra)
        self.btn_editar_letra = _BotaoDiscreto()
        self.btn_editar_letra.clicked.connect(self._alternar_edicao_letra)
        self.layout_letra.addWidget(self.btn_editar_letra, 0, Qt.AlignRight)
        self.area_letra.setWidget(self.conteudo_letra)
        self.area_letra.hide()

        self.area_fila = _ListaFila()
        self.area_fila.setObjectName("areaLista")
        self.area_fila.setMinimumHeight(220)
        self.area_fila.tocar.connect(self._tocar_na_fila)
        self.area_fila.remover.connect(self._remover_indice_fila)
        self.area_fila.hide()

        self._espacador_inferior = QWidget()
        self._espacador_inferior.setSizePolicy(
            QSizePolicy.Minimum, QSizePolicy.Expanding)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 16)
        layout.setSpacing(12)
        layout.addLayout(linha_secao)
        layout.addWidget(self.capa)
        layout.addLayout(informacoes_musica)
        layout.addWidget(linha_acoes)
        layout.addWidget(self.selo, 0, Qt.AlignLeft)
        layout.addWidget(self.lbl_album)
        layout.addWidget(divisor)
        layout.addWidget(self.area_letra, 1)
        layout.addWidget(self.area_fila, 1)
        layout.addWidget(self._espacador_inferior, 1)

    def conectar_player(self, player):
        self.player = player
        player.fila_mudou.connect(self.atualizar_fila)
        self.atualizar_fila()

    def atualizar_tema(self):
        self._hud = bool(temas.cor("hud"))
        if self._hud:
            if self._linha_secao.indexOf(self._ponto_hud) < 0:
                self._linha_secao.insertWidget(
                    1, self._ponto_hud, 0, Qt.AlignVCenter)
        else:
            self._linha_secao.removeWidget(self._ponto_hud)
            self._animacao_ponto.stop()
            self._opacidade_ponto.setOpacity(1.0)
            self._ponto_hud.hide()
        self._atualizar_estilo_selo()
        self.capa.setPixmap(util.pixmap_capa(self._musica_atual, 232))
        self.btn_letra.setIcon(icone("letra", tamanho=20))
        self.btn_fila.setIcon(icone("playlist", tamanho=20))
        self.btn_editar_letra.atualizar_tema()
        _estilo_coracao(
            self.btn_coracao,
            self._musica_atual is not None
            and bool(self._musica_atual["favorita"]))
        self._definir_album(self._musica_atual)
        if self.player is not None and self._hud:
            self.definir_tocando(self.player.tocando)
        self.area_letra.viewport().update()
        self.area_fila.viewport().update()
        self.update()

    def _atualizar_estilo_selo(self):
        if not self._hud:
            self.selo.setStyleSheet("")
            return
        cor_hud = temas.cor("hud_amarelo")
        self.selo.setStyleSheet(
            "QLabel#selo {"
            f"color: {cor_hud};"
            f"border: 1px solid {cor_hud};"
            f"border-radius: {temas.cor('raio')};"
            "}")

    def abrir_fila(self):
        self._definir_painel("fila")

    def _definir_painel(self, nome):
        self._painel_aberto = nome
        self.area_letra.setVisible(nome == "letra")
        self.area_fila.setVisible(nome == "fila")
        self._espacador_inferior.setVisible(nome not in ("letra", "fila"))
        self.btn_letra.setChecked(nome == "letra")
        self.btn_fila.setChecked(nome == "fila")
        self.painel_mudou.emit(nome or "")

    def _alternar_painel(self, nome):
        self._definir_painel(None if self._painel_aberto == nome else nome)

    def _atualizar_letra(self):
        self.lbl_letra.setText(
            self._letra or "Sem letra. Toque no lápis para adicionar.")

    def _alternar_edicao_letra(self):
        if self._editor_letra is not None:
            self._salvar_letra()
            return
        if self.musica_id is None:
            return

        self.lbl_letra.hide()
        self._editor_letra = QPlainTextEdit()
        self._editor_letra.setObjectName("editorLetra")
        self._editor_letra.setLineWrapMode(QPlainTextEdit.WidgetWidth)
        self._editor_letra.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self._editor_letra.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self._editor_letra.setFixedHeight(88)
        self._editor_letra.setPlainText(self._letra)
        self._editor_letra.installEventFilter(self)
        self.layout_letra.insertWidget(0, self._editor_letra)
        self._editor_letra.setFocus()

    def _salvar_letra(self):
        editor = self._editor_letra
        if editor is None:
            return

        texto = editor.toPlainText()
        if self.musica_id is not None:
            db.definir_letra(self.musica_id, texto)
        self._letra = texto
        editor.removeEventFilter(self)
        self.layout_letra.removeWidget(editor)
        editor.deleteLater()
        self._editor_letra = None
        self._atualizar_letra()
        self.lbl_letra.show()

    def eventFilter(self, watched, evento):
        if (watched is self.lbl_artista
                and evento.type() == QEvent.Type.MouseButtonRelease
                and evento.button() == Qt.LeftButton
                and self.musica_id is not None):
            self.artista_clicado.emit(self.lbl_artista.text())
            return True
        if (watched is self._editor_letra
                and evento.type() == QEvent.Type.FocusOut):
            QTimer.singleShot(0, self._salvar_letra)
        return super().eventFilter(watched, evento)

    def atualizar_fila(self):
        musicas = self.player.fila if self.player is not None else []
        ids = [musica["id"] for musica in musicas]
        if ids != self._ids_fila:
            self.area_fila.clear()
            if not musicas:
                vazio = QListWidgetItem("Fila vazia")
                vazio.setSizeHint(QSize(0, 34))
                vazio.setData(Qt.UserRole + 2, True)
                self.area_fila.addItem(vazio)
            else:
                for indice, musica in enumerate(musicas):
                    item = QListWidgetItem(musica["titulo"])
                    item.setSizeHint(QSize(0, 34))
                    item.setData(Qt.UserRole, indice)
                    item.setToolTip(
                        "Clique para tocar; use a lixeira para remover")
                    self.area_fila.addItem(item)
            self._ids_fila = ids
            self._indice_atual_fila = -1

        atual = self.player.indice_fila_atual
        if 0 <= self._indice_atual_fila < self.area_fila.count():
            self.area_fila.item(
                self._indice_atual_fila).setData(Qt.UserRole + 1, False)
        if 0 <= atual < len(musicas):
            self.area_fila.item(atual).setData(Qt.UserRole + 1, True)
        self._indice_atual_fila = atual
        self.area_fila.viewport().update()

    def _tocar_na_fila(self, indice):
        if self.player is None:
            return
        musicas = self.player.fila
        if 0 <= indice < len(musicas):
            self.player.tocar_lista(musicas, indice)

    def _remover_indice_fila(self, indice):
        if self.player is None:
            return
        musicas = self.player.fila
        if 0 <= indice < len(musicas):
            self.player.remover_da_fila(musicas[indice]["id"])

    def definir_tocando(self, tocando: bool):
        if not self._hud:
            return
        if tocando:
            self._ponto_hud.show()
            if self._animacao_ponto.state() != QAbstractAnimation.Running:
                self._animacao_ponto.start()
            return

        self._animacao_ponto.stop()
        self._opacidade_ponto.setOpacity(1.0)
        self._ponto_hud.hide()

    def paintEvent(self, evento):
        super().paintEvent(evento)
        if not self._hud:
            return

        capa = self.capa.geometry()
        esquerda = capa.left() - 6
        direita = capa.right() + 6
        topo = capa.top() - 6
        baixo = capa.bottom() + 6
        comprimento = 14

        pintor = QPainter(self)
        pintor.setRenderHint(QPainter.Antialiasing)
        pintor.setPen(QPen(QColor(temas.cor("hud_amarelo")), 2))
        pintor.drawLine(esquerda, topo, esquerda + comprimento, topo)
        pintor.drawLine(esquerda, topo, esquerda, topo + comprimento)
        pintor.drawLine(direita - comprimento, topo, direita, topo)
        pintor.drawLine(direita, topo, direita, topo + comprimento)
        pintor.drawLine(esquerda, baixo - comprimento, esquerda, baixo)
        pintor.drawLine(esquerda, baixo, esquerda + comprimento, baixo)
        pintor.drawLine(direita, baixo - comprimento, direita, baixo)
        pintor.drawLine(direita - comprimento, baixo, direita, baixo)
        pintor.end()

    def mostrar_musica(self, m):
        if self._editor_letra is not None:
            self._salvar_letra()
        self._musica_atual = m
        self.musica_id = m["id"] if m is not None else None
        self._letra = dict(m).get("letra", "") if m is not None else ""
        self.capa.setPixmap(util.pixmap_capa(m, 232))
        self.lbl_titulo.setText(m["titulo"] if m is not None else "Nada tocando")
        self.lbl_artista.setText(
            (m["artista"] or "Artista desconhecido") if m is not None else "")
        self.btn_coracao.setVisible(m is not None)
        _estilo_coracao(self.btn_coracao, m is not None and bool(m["favorita"]))

        self._definir_album(m)
        formato = m["formato"] if m is not None else None
        self.selo.setText(formato or "")
        self.selo.setVisible(bool(formato))
        self.btn_letra.setEnabled(m is not None)
        self.btn_editar_letra.setEnabled(m is not None)
        self._atualizar_letra()
        self.atualizar_fila()

    def _definir_album(self, m):
        album = m["album"] if m is not None else None
        if album:
            self.lbl_album.setText(
                f"<span style='color:{util.TEXTO_SUAVE}'>Álbum</span> {html.escape(album)}")
        else:
            self.lbl_album.setText("")
        self.lbl_album.setVisible(bool(album))

    def _clicou_coracao(self):
        if self.musica_id is not None:
            self.favoritar.emit(self.musica_id)