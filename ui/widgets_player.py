import html

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (QFrame, QHBoxLayout, QLabel, QPushButton,
                               QSizePolicy, QSlider, QStyle, QVBoxLayout)

from ui import util


class SliderClicavel(QSlider):
    """Slider que pula direto para o ponto onde você clica."""

    def __init__(self, *args):
        super().__init__(*args)
        self.arrastando = False

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
    botao.setText("♥" if favorita else "♡")


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
        self.btn_coracao = QPushButton("♡")
        self.btn_coracao.setObjectName("coracao")
        self.btn_coracao.setVisible(False)
        self.btn_coracao.clicked.connect(lambda: self._clicou_coracao())
        esquerda = QHBoxLayout()
        esquerda.setSpacing(12)
        esquerda.addWidget(self.capa)
        esquerda.addLayout(textos, 1)
        esquerda.addWidget(self.btn_coracao)

        # --- centro: controles e progresso ---
        self.btn_shuffle = QPushButton("⇄")
        self.btn_shuffle.setObjectName("botaoIcone")
        self.btn_shuffle.setCheckable(True)
        self.btn_shuffle.toggled.connect(player.definir_shuffle)
        btn_ant = QPushButton("⏮")
        btn_ant.setObjectName("botaoIcone")
        btn_ant.clicked.connect(lambda: player.anterior())
        self.btn_play = QPushButton("▶")
        self.btn_play.setObjectName("botaoPlay")
        self.btn_play.clicked.connect(lambda: player.alternar())
        btn_prox = QPushButton("⏭")
        btn_prox.setObjectName("botaoIcone")
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
        lbl_vol = QLabel("VOL")
        lbl_vol.setObjectName("secao")
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
            lambda tocando: self.btn_play.setText("⏸" if tocando else "▶"))
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


class PainelAtual(QFrame):
    favoritar = Signal(int)

    def __init__(self):
        super().__init__()
        self.setObjectName("painelAtual")
        self.setFixedWidth(280)
        self.musica_id = None

        secao = QLabel("TOCANDO AGORA")
        secao.setObjectName("secao")
        self.capa = QLabel()
        self.capa.setFixedSize(232, 232)
        self.capa.setPixmap(util.pixmap_capa(None, 232))

        self.lbl_titulo = QLabel("Nada tocando")
        self.lbl_titulo.setObjectName("painelTitulo")
        self.lbl_titulo.setWordWrap(True)
        self.lbl_artista = QLabel("")
        self.lbl_artista.setObjectName("painelArtista")
        self.lbl_artista.setWordWrap(True)

        self.btn_coracao = QPushButton("♡")
        self.btn_coracao.setObjectName("coracao")
        self.btn_coracao.setVisible(False)
        self.btn_coracao.clicked.connect(lambda: self._clicou_coracao())

        linha_titulo = QHBoxLayout()
        linha_titulo.addWidget(self.lbl_titulo, 1)
        linha_titulo.addWidget(self.btn_coracao, 0, Qt.AlignTop)

        divisor = QFrame()
        divisor.setObjectName("divisor")
        divisor.setFixedHeight(1)

        self.lbl_album = QLabel("")
        self.lbl_album.setObjectName("painelAlbum")
        self.selo = QLabel("")
        self.selo.setObjectName("selo")
        rodape = QHBoxLayout()
        rodape.addWidget(self.lbl_album, 1)
        rodape.addWidget(self.selo)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 16)
        layout.setSpacing(12)
        layout.addWidget(secao)
        layout.addWidget(self.capa)
        layout.addLayout(linha_titulo)
        layout.addWidget(self.lbl_artista)
        layout.addWidget(divisor)
        layout.addLayout(rodape)
        layout.addStretch()

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