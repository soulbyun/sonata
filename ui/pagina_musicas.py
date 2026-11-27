from PySide6.QtCore import QRect, QSize, Qt, Signal
from PySide6.QtGui import QColor, QFont
from PySide6.QtWidgets import (QAbstractItemView, QHBoxLayout, QLabel,
                               QLineEdit, QListWidget, QListWidgetItem,
                               QPushButton, QStyle, QStyledItemDelegate,
                               QVBoxLayout, QWidget)

from ui import temas, util
from ui.icones import icone, pixmap
from ui.menu_musica import MenuMusica
from ui.texto_esteira import AnimacaoEsteira


class ListaMusicas(QListWidget):
    ordem_alterada = Signal(list)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.reordenacao_habilitada = False
        self.linha_arrastada = -1
        self.indice_insercao = None
        self._posicao_inicial = None
        self._linha_inicial = -1
        self._id_arrastado = None
        self._ordem_inicial = []
        self.setDropIndicatorShown(False)
        self.setDragDropOverwriteMode(False)
        self.setDefaultDropAction(Qt.MoveAction)
        self.definir_reordenacao(False)

    def definir_reordenacao(self, habilitada):
        self.reordenacao_habilitada = habilitada
        self.setDragEnabled(habilitada)
        self.setAcceptDrops(habilitada)
        modo = (QAbstractItemView.DragDropMode.InternalMove if habilitada
                else QAbstractItemView.DragDropMode.NoDragDrop)
        self.setDragDropMode(modo)

    def mousePressEvent(self, evento):
        self._posicao_inicial = None
        self._linha_inicial = -1
        if self.reordenacao_habilitada and evento.button() == Qt.LeftButton:
            self._posicao_inicial = evento.position().toPoint()
            self._linha_inicial = self.indexAt(self._posicao_inicial).row()
        super().mousePressEvent(evento)

    def mouseMoveEvent(self, evento):
        if (self.reordenacao_habilitada
                and self._posicao_inicial is not None
                and evento.buttons() & Qt.LeftButton):
            ponto = evento.position().toPoint()
            if (ponto - self._posicao_inicial).manhattanLength() < 8:
                return
            if self._linha_inicial >= 0:
                self.setCurrentRow(self._linha_inicial)
                self.linha_arrastada = self._linha_inicial
                self._id_arrastado = self.item(
                    self._linha_inicial).data(Qt.UserRole)
                self._ordem_inicial = self._ids()
                self._posicao_inicial = None
                self.viewport().update()
                self.startDrag(Qt.MoveAction)
                return
            return
        super().mouseMoveEvent(evento)

    def mouseReleaseEvent(self, evento):
        super().mouseReleaseEvent(evento)
        self._posicao_inicial = None
        self._linha_inicial = -1

    def startDrag(self, supported_actions):
        try:
            super().startDrag(supported_actions)
        finally:
            self._limpar_arrasto()

    def dragMoveEvent(self, evento):
        super().dragMoveEvent(evento)
        self.indice_insercao = self._calcular_indice(
            evento.position().toPoint())
        self.viewport().update()

    def dragLeaveEvent(self, evento):
        super().dragLeaveEvent(evento)
        self.indice_insercao = None
        self.viewport().update()

    def dropEvent(self, evento):
        id_arrastado = self._id_arrastado
        ordem_inicial = self._ordem_inicial
        super().dropEvent(evento)
        if evento.isAccepted():
            self._restaurar_selecao(id_arrastado)
            ordem_final = self._ids()
            if ordem_final != ordem_inicial:
                self.ordem_alterada.emit(ordem_final)
        self._limpar_arrasto()

    def _calcular_indice(self, ponto):
        linha = self.indexAt(ponto).row()
        if linha < 0:
            if self.count() == 0:
                return 0
            primeira = self.visualItemRect(self.item(0))
            return 0 if ponto.y() < primeira.top() else self.count()
        retangulo = self.visualItemRect(self.item(linha))
        return linha if ponto.y() < retangulo.center().y() else linha + 1

    def _ids(self):
        return [self.item(i).data(Qt.UserRole) for i in range(self.count())]

    def _restaurar_selecao(self, musica_id):
        if musica_id is None:
            return
        for linha in range(self.count()):
            if self.item(linha).data(Qt.UserRole) == musica_id:
                self.setCurrentRow(linha)
                return

    def _limpar_arrasto(self):
        self.linha_arrastada = -1
        self.indice_insercao = None
        self._id_arrastado = None
        self._ordem_inicial = []
        self.viewport().update()


class LinhaMusica(QStyledItemDelegate):
    """Desenha cada linha da lista. Só as linhas visíveis são desenhadas,
    então continua rápido mesmo com milhares de músicas."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.musicas = []
        self.id_tocando = None
        self.lista = parent
        lista = self.lista
        self.esteira = AnimacaoEsteira(
            lista, lambda: lista.viewport().update() if lista is not None else None)

    def sizeHint(self, option, index):
        return QSize(0, 60)

    def paint(self, painter, option, index):
        m = self.musicas[index.row()]
        tocando = m["id"] == self.id_tocando
        selecionado = bool(option.state & QStyle.State_Selected)
        r = option.rect

        painter.save()
        if self.lista.linha_arrastada == index.row():
            painter.setOpacity(0.45)

        if tocando:
            painter.fillRect(r, QColor(temas.cor("azul_escuro")))
            if temas.cor("hud"):
                painter.fillRect(
                    QRect(r.left(), r.top(), 3, r.height()),
                    QColor(temas.cor("hud_azul")))
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
            cor_coracao = (
                temas.cor("hud_amarelo") or
                (util.TEXTO if tocando or selecionado
                 else temas.cor("lilas_claro")))
            coracao = pixmap(
                "coracao", cor=cor_coracao, tamanho=18, cheio=True)
            painter.drawPixmap(
                x_dur - 34, r.top() + (r.height() - 18) // 2, coracao)
            limite = x_dur - 50

        # título e artista
        x_texto = r.left() + 118
        largura = max(limite - x_texto, 20)

        fonte_titulo = QFont(option.font)
        fonte_titulo.setFamily("Zen Maru Gothic")
        fonte_titulo.setPixelSize(15)
        painter.setFont(fonte_titulo)
        cor_titulo = (temas.cor("azul_claro") if tocando else
                      util.TEXTO if selecionado else
                      temas.cor("lilas_claro") if m["favorita"] else util.TEXTO)
        painter.setPen(QColor(cor_titulo))
        ativo = tocando or bool(option.state & QStyle.State_MouseOver)
        self.esteira.pintar(
            painter, QRect(x_texto, r.top() + 11, largura, 20), m["titulo"],
            fonte_titulo, QColor(cor_titulo), m["id"], ativo)

        fonte_artista = QFont(option.font)
        fonte_artista.setFamily("Zen Maru Gothic")
        fonte_artista.setPixelSize(13)
        painter.setFont(fonte_artista)
        painter.setPen(QColor(
            util.TEXTO if tocando or selecionado else util.TEXTO_SUAVE))
        self.esteira.pintar(
            painter, QRect(x_texto, r.top() + 31, largura, 18),
            m["artista"] or "Artista desconhecido", fonte_artista,
            QColor(util.TEXTO if tocando or selecionado else util.TEXTO_SUAVE),
            (m["id"], "artista"), ativo)

        painter.restore()
        if self.lista.indice_insercao in (index.row(), index.row() + 1):
            cor = temas.cor("hud_azul") or temas.cor("azul_claro")
            y = r.top() if self.lista.indice_insercao == index.row() else r.bottom()
            painter.fillRect(QRect(r.left(), y, r.width(), 1), QColor(cor))


class PaginaMusicas(QWidget):
    tocar = Signal(list, int)          # (lista de músicas, posição da escolhida)
    tocar_aleatorio = Signal(list)
    acao_musica = Signal(str, object)   # "favoritar", "playlist" ou "excluir" + a música
    def __init__(self, titulo, buscar_musicas):
        super().__init__()
        self.buscar_musicas = buscar_musicas   # função do db que devolve as músicas
        self.todas = []
        self.exibidas = []
        self._callback_reordenacao = None

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

        btn_shuffle = QPushButton()
        btn_shuffle.setObjectName("botaoIcone")
        cor_controles = (
            temas.cor("hud_amarelo") or temas.cor("texto_suave"))
        btn_shuffle.setIcon(
            icone("shuffle", cor=cor_controles, tamanho=18))
        btn_shuffle.setIconSize(QSize(18, 18))
        btn_shuffle.clicked.connect(lambda: self._tocar_aleatorio())
        btn_play = QPushButton()
        btn_play.setObjectName("botaoPlay")
        btn_play.setIcon(icone("play", cor=cor_controles, tamanho=20))
        btn_play.setIconSize(QSize(20, 20))
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
        self.lista = ListaMusicas()
        self.delegate = LinhaMusica(self.lista)
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

    def habilitar_reordenacao(self, callback):
        self._callback_reordenacao = callback
        self.lista.ordem_alterada.connect(self._ao_reordenar_lista)
        self.lista.definir_reordenacao(not self.busca.text().strip())

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
                         if termo in m["titulo"].lower()
                         or termo in (m["artista"] or "Artista desconhecido").lower()]
        self.lista.definir_reordenacao(
            self._callback_reordenacao is not None and not termo)
        self.delegate.musicas = self.exibidas
        self.delegate.esteira.limpar()

        self.lista.clear()
        for musica in self.exibidas:
            item = QListWidgetItem()
            item.setData(Qt.UserRole, musica["id"])
            self.lista.addItem(item)

        n = len(self.exibidas)
        minutos = sum(m["duracao"] for m in self.exibidas) // 60
        self.lbl_info.setText(f"{n} {'música' if n == 1 else 'músicas'} · {minutos} min")
        self.lista.setVisible(n > 0)
        self.lbl_vazio.setVisible(n == 0)

    def _ao_reordenar_lista(self, ids_na_ordem):
        musicas_por_id = {musica["id"]: musica for musica in self.exibidas}
        if any(musica_id not in musicas_por_id for musica_id in ids_na_ordem):
            return
        self.exibidas = [musicas_por_id[musica_id] for musica_id in ids_na_ordem]
        self.todas = list(self.exibidas)
        self.delegate.musicas = self.exibidas
        self.delegate.esteira.limpar()
        self.lista.viewport().update()
        if self._callback_reordenacao is not None:
            self._callback_reordenacao(ids_na_ordem)

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