from PySide6.QtCore import QRect, QSize, Qt, Signal
from PySide6.QtGui import QColor, QFont
from PySide6.QtWidgets import (QHBoxLayout, QLabel, QLineEdit, QListWidget,
                               QListWidgetItem, QPushButton, QStyle,
                               QStyledItemDelegate, QVBoxLayout, QWidget)

from ui import temas, util
from ui.menu_musica import MenuMusica

class LinhaMusica(QStyledItemDelegate):
    """Desenha cada linha da lista. Só as linhas visíveis são desenhadas,
    então continua rápido mesmo com milhares de músicas."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.musicas = []
        self.id_tocando = None

    def sizeHint(self, option, index):
        return QSize(0, 60)

    def paint(self, painter, option, index):
        m = self.musicas[index.row()]
        tocando = m["id"] == self.id_tocando
        selecionado = bool(option.state & QStyle.State_Selected)
        r = option.rect

        painter.save()

        if tocando:
            painter.fillRect(r, QColor(temas.cor("azul_escuro")))
        elif option.state & QStyle.State_Selected:
            painter.fillRect(r, QColor(temas.cor("elevado")))
        elif option.state & QStyle.State_MouseOver:
            painter.fillRect(r, QColor(temas.cor("cartao")))

        # número (ou ▶ na música que está tocando)
        fonte = QFont(option.font)
        fonte.setPixelSize(13)
        painter.setFont(fonte)
        painter.setPen(QColor(
            temas.cor("azul_claro") if tocando else
            util.TEXTO if selecionado else util.TEXTO_SUAVE))
        painter.drawText(QRect(r.left() + 10, r.top(), 40, r.height()),
                         Qt.AlignCenter, "▶" if tocando else str(index.row() + 1))

        # capa
        painter.drawPixmap(r.left() + 62, r.top() + 10, util.pixmap_capa(m, 40))

        # duração e coração
        x_dur = r.right() - 70
        painter.setPen(QColor(
            util.TEXTO if tocando or selecionado else util.TEXTO_SUAVE))
        painter.drawText(QRect(x_dur, r.top(), 56, r.height()),
                         Qt.AlignRight | Qt.AlignVCenter, util.fmt_tempo(m["duracao"]))
        limite = x_dur - 10
        if m["favorita"]:
            painter.setPen(QColor(
                util.TEXTO if tocando or selecionado
                else temas.cor("lilas_claro")))
            painter.drawText(QRect(x_dur - 40, r.top(), 24, r.height()),
                             Qt.AlignCenter, "♥")
            limite = x_dur - 50

        # título e artista
        x_texto = r.left() + 118
        largura = max(limite - x_texto, 20)

        fonte_titulo = QFont(option.font)
        fonte_titulo.setPixelSize(15)
        painter.setFont(fonte_titulo)
        cor_titulo = (temas.cor("azul_claro") if tocando else
                      util.TEXTO if selecionado else
                      temas.cor("lilas_claro") if m["favorita"] else util.TEXTO)
        painter.setPen(QColor(cor_titulo))
        titulo = painter.fontMetrics().elidedText(m["titulo"], Qt.ElideRight, largura)
        painter.drawText(QRect(x_texto, r.top() + 11, largura, 20),
                         Qt.AlignLeft | Qt.AlignVCenter, titulo)

        fonte_artista = QFont(option.font)
        fonte_artista.setPixelSize(13)
        painter.setFont(fonte_artista)
        painter.setPen(QColor(
            util.TEXTO if tocando or selecionado else util.TEXTO_SUAVE))
        artista = painter.fontMetrics().elidedText(m["artista"], Qt.ElideRight, largura)
        painter.drawText(QRect(x_texto, r.top() + 31, largura, 18),
                         Qt.AlignLeft | Qt.AlignVCenter, artista)

        painter.restore()


class PaginaMusicas(QWidget):
    tocar = Signal(list, int)          # (lista de músicas, posição da escolhida)
    tocar_aleatorio = Signal(list)
    acao_musica = Signal(str, object)   # "favoritar", "playlist" ou "excluir" + a música
    def __init__(self, titulo, buscar_musicas):
        super().__init__()
        self.buscar_musicas = buscar_musicas   # função do db que devolve as músicas
        self.todas = []
        self.exibidas = []

        # --- cabeçalho ---
        self.lbl_titulo = QLabel(titulo)
        self.lbl_titulo.setObjectName("tituloPagina")
        self.lbl_info = QLabel()
        self.lbl_info.setObjectName("infoPagina")

        self.linha_titulo = QHBoxLayout()      # título + botões opcionais ao lado
        self.linha_titulo.setSpacing(8)
        self.linha_titulo.addWidget(self.lbl_titulo)
        self.linha_titulo.addStretch()

        textos = QVBoxLayout()
        textos.setSpacing(2)
        textos.addLayout(self.linha_titulo)
        textos.addWidget(self.lbl_info)

        self.busca = QLineEdit()
        self.busca.setPlaceholderText("Buscar")
        self.busca.textChanged.connect(self._aplicar_filtro)

        btn_shuffle = QPushButton("⇄")
        btn_shuffle.setObjectName("botaoIcone")
        btn_shuffle.clicked.connect(lambda: self._tocar_aleatorio())
        btn_play = QPushButton("▶")
        btn_play.setObjectName("botaoPlay")
        btn_play.clicked.connect(lambda: self._tocar_tudo())

        topo = QWidget()
        self.topo_layout = QHBoxLayout(topo)
        self.topo_layout.setContentsMargins(24, 22, 24, 16)
        self.topo_layout.addLayout(textos)
        self.topo_layout.addStretch()
        self.topo_layout.addWidget(self.busca)
        self.topo_layout.addWidget(btn_shuffle)
        self.topo_layout.addWidget(btn_play)

        # --- lista ---
        self.delegate = LinhaMusica()
        self.lista = QListWidget()
        self.lista.setItemDelegate(self.delegate)
        self.lista.setMouseTracking(True)
        self.lista.setVerticalScrollMode(QListWidget.ScrollPerPixel)
        self.lista.setFocusPolicy(Qt.NoFocus)
        self.lista.itemDoubleClicked.connect(self._duplo_clique)
        self.lista.setContextMenuPolicy(Qt.CustomContextMenu)
        self.lista.customContextMenuRequested.connect(self._menu_contexto)
        self.lbl_vazio = QLabel("Nenhuma música por aqui.")
        self.lbl_vazio.setObjectName("vazio")
        self.lbl_vazio.setAlignment(Qt.AlignCenter)

        self.raiz = QVBoxLayout(self)
        self.raiz.setContentsMargins(0, 0, 0, 0)
        self.raiz.setSpacing(0)
        self.raiz.addWidget(topo)
        self.raiz.addWidget(self.lista, 1)
        self.raiz.addWidget(self.lbl_vazio, 1)

    # ---------- ganchos usados pela tela de playlists ----------

    def definir_titulo(self, texto):
        self.lbl_titulo.setText(texto)

    def definir_texto_vazio(self, texto):
        self.lbl_vazio.setText(texto)

    def adicionar_ao_titulo(self, widget):
        """Coloca um widget logo ao lado do título (ex.: o pincel)."""
        self.linha_titulo.insertWidget(self.linha_titulo.count() - 1, widget)

    def adicionar_a_esquerda(self, widget):
        """Coloca um widget no começo do cabeçalho (ex.: a seta de voltar)."""
        self.topo_layout.insertWidget(0, widget)

    def colocar_acima(self, widget):
        """Coloca um widget acima do cabeçalho (ex.: o banner)."""
        self.raiz.insertWidget(0, widget)

    # ---------- lista ----------

    def carregar(self):
        """Busca as músicas no banco e atualiza a lista, mantendo a rolagem."""
        rolagem = self.lista.verticalScrollBar().value()
        self.todas = [dict(m) for m in self.buscar_musicas()]
        self._aplicar_filtro()
        self.lista.verticalScrollBar().setValue(rolagem)

    def _aplicar_filtro(self, _=None):
        termo = self.busca.text().strip().lower()
        self.exibidas = [m for m in self.todas
                         if termo in m["titulo"].lower() or termo in m["artista"].lower()]
        self.delegate.musicas = self.exibidas

        self.lista.clear()
        for _m in self.exibidas:
            self.lista.addItem(QListWidgetItem())

        n = len(self.exibidas)
        minutos = sum(m["duracao"] for m in self.exibidas) // 60
        self.lbl_info.setText(f"{n} {'música' if n == 1 else 'músicas'} · {minutos} min")
        self.lista.setVisible(n > 0)
        self.lbl_vazio.setVisible(n == 0)

    def marcar_tocando(self, musica_id):
        self.delegate.id_tocando = musica_id
        self.lista.viewport().update()

    def _duplo_clique(self, item):
        self.tocar.emit(self.exibidas, self.lista.row(item))
    def _menu_contexto(self, ponto):
        item = self.lista.itemAt(ponto)
        if item is None:
            return
        linha = self.lista.row(item)
        self.lista.setCurrentRow(linha)
        musica = self.exibidas[linha]
        menu = MenuMusica(musica, self)
        menu.acao.connect(lambda nome, m=musica: self.acao_musica.emit(nome, m))
        menu.mostrar_em(self.lista.viewport().mapToGlobal(ponto))

    def _tocar_tudo(self):
        if self.exibidas:
            self.tocar.emit(self.exibidas, 0)

    def _tocar_aleatorio(self):
        if self.exibidas:
            self.tocar_aleatorio.emit(self.exibidas)