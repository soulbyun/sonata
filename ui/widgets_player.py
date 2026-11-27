import html

from PySide6.QtCore import (QAbstractAnimation, QEasingCurve,
                            QPropertyAnimation, QSize, Qt, Signal)
from PySide6.QtGui import QColor, QIcon, QPainter, QPen
from PySide6.QtWidgets import (QFrame, QHBoxLayout, QLabel, QPushButton,
                               QGraphicsOpacityEffect, QSizePolicy, QSlider, QStyle,
                               QStyleOptionSlider, QVBoxLayout)

from ui import temas, util
from ui.icones import icone, pixmap


class SliderClicavel(QSlider):
    """Slider que pula direto para o ponto onde você clica."""

    def __init__(self, *args):
        super().__init__(*args)
        self.arrastando = False
        self._icone_alca = pixmap(
            "circle-dashed-duotone", cor=temas.cor("azul_claro"), tamanho=18)

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


class BarraPlayer(QFrame):
    favoritar = Signal(int)   # id da música

    def __init__(self, player):
        super().__init__()
        self.setObjectName("barraPlayer")
        self.setFixedHeight(88)
        self.player = player
        self.musica_id = None

        # --- esquerda: capa, nome e coração ---
        self.capa = QLabel()
        self.capa.setFixedSize(48, 48)
        self.capa.setPixmap(util.pixmap_capa(None, 48))
        self.lbl_titulo = QLabel("Nada tocando")
        self.lbl_titulo.setObjectName("barraTitulo")
        self.lbl_artista = QLabel("")
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
        btn_ant = QPushButton()
        btn_ant.setObjectName("botaoIcone")
        btn_ant.setIcon(_icone_controle("rewind", 18))
        btn_ant.setIconSize(QSize(18, 18))
        btn_ant.clicked.connect(lambda: player.anterior())
        self.btn_play = QPushButton()
        self.btn_play.setObjectName("botaoPlay")
        cor_play = (
            temas.cor("hud_amarelo") or temas.cor("texto_sobre_destaque"))
        self.btn_play.setIcon(
            _icone_controle("play-duotone", 20, cor_padrao=cor_play))
        self.btn_play.setIconSize(QSize(20, 20))
        self.btn_play.clicked.connect(lambda: player.alternar())
        btn_prox = QPushButton()
        btn_prox.setObjectName("botaoIcone")
        btn_prox.setIcon(_icone_controle("fast-forward", 18))
        btn_prox.setIconSize(QSize(18, 18))
        btn_prox.clicked.connect(lambda: player.proxima())
        self.btn_repetir = QPushButton("↻")
        self.btn_repetir.setObjectName("botaoIcone")
        self.btn_repetir.setCheckable(True)
        self.btn_repetir.clicked.connect(lambda: self._ciclar_repeticao())

        controles = QHBoxLayout()
        controles.setSpacing(6)
        controles.addStretch()
        for b in (self.btn_shuffle, btn_ant, self.btn_play, btn_prox, self.btn_repetir):
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
        lbl_vol = QLabel()
        lbl_vol.setObjectName("secao")
        lbl_vol.setPixmap(pixmap(
            "speaker-high-duotone",
            cor=temas.cor("hud_amarelo") or temas.cor("texto_suave"),
            tamanho=18))
        lbl_vol.setToolTip("Volume")
        self.volume = SliderClicavel(Qt.Horizontal)
        self.volume.setRange(0, 100)
        self.volume.setValue(50)
        self.volume.setFixedWidth(110)
        self.volume.valueChanged.connect(player.definir_volume)
        direita = QHBoxLayout()
        direita.addStretch()
        direita.addWidget(lbl_vol)
        direita.addWidget(self.volume)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(14, 8, 24, 8)
        layout.addLayout(esquerda, 1)
        layout.addLayout(centro, 2)
        layout.addLayout(direita, 1)

        player.estado_mudou.connect(
            lambda tocando: self.btn_play.setIcon(
                _icone_controle(
                    "pause-circle-duotone" if tocando else "play-duotone",
                    20, cor_padrao=cor_play)))
        player.posicao_mudou.connect(self._ao_mudar_posicao)
        player.duracao_mudou.connect(self._ao_mudar_duracao)

    def mostrar_musica(self, m):
        self.musica_id = m["id"] if m is not None else None
        self.capa.setPixmap(util.pixmap_capa(m, 48))
        self.lbl_titulo.setText(m["titulo"] if m is not None else "Nada tocando")
        self.lbl_artista.setText(m["artista"] if m is not None else "")
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

    def __init__(self):
        super().__init__()
        self.setObjectName("painelAtual")
        self.setFixedWidth(280)
        self.musica_id = None
        self._hud = bool(temas.cor("hud"))

        secao = QLabel("TOCANDO AGORA")
        secao.setObjectName("secao")
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

        self.capa = QLabel()
        self.capa.setFixedSize(232, 232)
        self.capa.setPixmap(util.pixmap_capa(None, 232))

        self.lbl_titulo = QLabel("Nada tocando")
        self.lbl_titulo.setObjectName("painelTitulo")
        self.lbl_titulo.setWordWrap(True)
        self.lbl_artista = QLabel("")
        self.lbl_artista.setObjectName("painelArtista")
        self.lbl_artista.setWordWrap(True)

        self.btn_coracao = QPushButton()
        self.btn_coracao.setObjectName("coracao")
        self.btn_coracao.setVisible(False)
        self.btn_coracao.clicked.connect(lambda: self._clicou_coracao())

        linha_titulo = QHBoxLayout()
        linha_titulo.addWidget(self.lbl_titulo, 1)
        linha_titulo.addWidget(self.btn_coracao, 0, Qt.AlignTop)

        informacoes_musica = QVBoxLayout()
        informacoes_musica.setSpacing(4)
        informacoes_musica.addLayout(linha_titulo)
        informacoes_musica.addWidget(self.lbl_artista)

        divisor = QFrame()
        divisor.setObjectName("divisor")
        divisor.setFixedHeight(1)

        self.lbl_album = QLabel("")
        self.lbl_album.setObjectName("painelAlbum")
        self.selo = QLabel("")
        self.selo.setObjectName("selo")
        if self._hud:
            cor_hud = temas.cor("hud_amarelo")
            self.selo.setStyleSheet(
                "QLabel#selo {"
                f"color: {cor_hud};"
                f"border: 1px solid {cor_hud};"
                f"border-radius: {temas.cor('raio')};"
                "}")
        rodape = QHBoxLayout()
        rodape.addWidget(self.lbl_album, 1)
        rodape.addWidget(self.selo)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 16)
        layout.setSpacing(12)
        layout.addLayout(linha_secao)
        layout.addWidget(self.capa)
        layout.addLayout(informacoes_musica)
        layout.addWidget(divisor)
        layout.addLayout(rodape)
        layout.addStretch()

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
        self.musica_id = m["id"] if m is not None else None
        self.capa.setPixmap(util.pixmap_capa(m, 232))
        self.lbl_titulo.setText(m["titulo"] if m is not None else "Nada tocando")
        self.lbl_artista.setText(m["artista"] if m is not None else "")
        self.btn_coracao.setVisible(m is not None)
        _estilo_coracao(self.btn_coracao, m is not None and bool(m["favorita"]))

        album = m["album"] if m is not None else None
        if album:
            self.lbl_album.setText(
                f"<span style='color:{util.TEXTO_SUAVE}'>Álbum</span> {html.escape(album)}")
        else:
            self.lbl_album.setText("")
        formato = m["formato"] if m is not None else None
        self.selo.setText(formato or "")
        self.selo.setVisible(bool(formato))

    def _clicou_coracao(self):
        if self.musica_id is not None:
            self.favoritar.emit(self.musica_id)