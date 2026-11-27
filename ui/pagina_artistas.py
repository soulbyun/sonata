import unicodedata

from PySide6.QtCore import QRect, QRectF, QSize, Qt, Signal
from PySide6.QtGui import QColor, QFont
from PySide6.QtWidgets import (QHBoxLayout, QLabel, QLineEdit, QListWidget,
                               QListWidgetItem, QPushButton, QStackedWidget,
                               QStyle, QStyledItemDelegate, QVBoxLayout, QWidget)

import db
from ui import temas, util
from ui.pagina_musicas import PaginaMusicas
from ui.texto_esteira import AnimacaoEsteira


def _chave_ordenacao(texto):
    normalizado = unicodedata.normalize("NFD", texto.casefold())
    return "".join(
        caractere for caractere in normalizado
        if unicodedata.category(caractere) != "Mn")


class LinhaArtista(QStyledItemDelegate):
    """Desenha cada artista da lista."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.itens = []
        lista = parent
        self.esteira = AnimacaoEsteira(
            lista, lambda: lista.viewport().update() if lista is not None else None)

    def sizeHint(self, option, index):
        return QSize(190, 166)

    def paint(self, painter, option, index):
        a = self.itens[index.row()]
        r = option.rect
        painter.save()

        retangulo = QRectF(r.adjusted(3, 3, -3, -3))
        sobre = bool(option.state & QStyle.State_MouseOver)
        selecionado = bool(option.state & QStyle.State_Selected)
        cor_cartao = (
            temas.cor("elevado") if sobre or selecionado
            else temas.cor("cartao"))
        raio = float(str(temas.cor("raio")).replace("px", ""))
        painter.setPen(Qt.NoPen)
        painter.setBrush(QColor(cor_cartao))
        painter.drawRoundedRect(retangulo, raio, raio)

        lado_capa = 88
        x_capa = r.left() + (r.width() - lado_capa) // 2
        painter.drawPixmap(
            x_capa, r.top() + 11, util.pixmap_capa(a["musica_capa"], lado_capa))
        x_texto = r.left() + 12
        largura = max(r.width() - 24, 20)
        fonte_nome = QFont(option.font)
        fonte_nome.setFamily("Zen Maru Gothic")
        fonte_nome.setPixelSize(15)
        self.esteira.pintar(
            painter, QRect(x_texto, r.top() + 104, largura, 20), a["nome"],
            fonte_nome, QColor(util.TEXTO), a["chave"], sobre)

        fonte_info = QFont(option.font)
        fonte_info.setPixelSize(13)
        painter.setFont(fonte_info)
        painter.setPen(QColor(util.TEXTO_SUAVE))
        n = a["total"]
        texto = f"{n} {'música' if n == 1 else 'músicas'} · {a['duracao'] // 60} min"
        painter.drawText(QRect(x_texto, r.top() + 128, largura, 18),
                         Qt.AlignLeft | Qt.AlignVCenter, texto)
        painter.restore()


class PaginaArtistas(QWidget):
    tocar = Signal(list, int)
    tocar_aleatorio = Signal(list)
    acao_musica = Signal(str, object)

    def __init__(self):
        super().__init__()
        self.chave = None      # artista aberto (em minúsculas), ou None na lista
        self.todos = []
        self.exibidos = []

        # ===== parte 1: lista de artistas =====
        titulo = QLabel("Artistas")
        titulo.setObjectName("tituloPagina")
        self.lbl_info = QLabel()
        self.lbl_info.setObjectName("infoPagina")
        textos = QVBoxLayout()
        textos.setSpacing(2)
        textos.addWidget(titulo)
        textos.addWidget(self.lbl_info)

        self.busca = QLineEdit()
        self.busca.setPlaceholderText("Buscar")
        self.busca.textChanged.connect(self._aplicar_filtro)

        topo = QWidget()
        topo_layout = QHBoxLayout(topo)
        topo_layout.setContentsMargins(24, 22, 24, 16)
        topo_layout.addLayout(textos)
        topo_layout.addStretch()
        topo_layout.addWidget(self.busca)

        self.lista = QListWidget()
        self.delegate = LinhaArtista(self.lista)
        self.lista.setItemDelegate(self.delegate)
        self.lista.setMouseTracking(True)
        self.lista.setViewMode(QListWidget.IconMode)
        self.lista.setResizeMode(QListWidget.Adjust)
        self.lista.setMovement(QListWidget.Static)
        self.lista.setGridSize(QSize(190, 166))
        self.lista.setSpacing(8)
        self.lista.setVerticalScrollMode(QListWidget.ScrollPerPixel)
        self.lista.setFocusPolicy(Qt.NoFocus)
        self.lista.itemClicked.connect(self._clicou_artista)

        self.lbl_vazio = QLabel()
        self.lbl_vazio.setObjectName("vazio")
        self.lbl_vazio.setAlignment(Qt.AlignCenter)

        pagina_lista = QWidget()
        col = QVBoxLayout(pagina_lista)
        col.setContentsMargins(0, 0, 0, 0)
        col.setSpacing(0)
        col.addWidget(topo)
        col.addWidget(self.lista, 1)
        col.addWidget(self.lbl_vazio, 1)

        # ===== parte 2: músicas de um artista =====
        self.detalhe = PaginaMusicas("", self._musicas_do_artista)

        btn_voltar = QPushButton("←")
        btn_voltar.setObjectName("botaoIcone")
        btn_voltar.setToolTip("Voltar aos artistas")
        btn_voltar.clicked.connect(lambda: self._voltar())
        self.detalhe.adicionar_a_esquerda(btn_voltar)

        self.detalhe.tocar.connect(self.tocar)
        self.detalhe.tocar_aleatorio.connect(self.tocar_aleatorio)
        self.detalhe.acao_musica.connect(self.acao_musica)

        # ===== junta as duas partes =====
        self.pilha = QStackedWidget()
        self.pilha.addWidget(pagina_lista)   # 0
        self.pilha.addWidget(self.detalhe)   # 1
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.pilha)

    # ---------- usadas pela janela principal ----------

    def carregar(self):
        if self.pilha.currentIndex() == 1 and self.chave is not None:
            self._atualizar_detalhe()
        else:
            self._atualizar_lista()

    def marcar_tocando(self, musica_id):
        self.detalhe.marcar_tocando(musica_id)

    def abrir_artista(self, nome):
        self.pilha.setCurrentIndex(0)
        self._atualizar_lista()
        chave = nome.casefold()
        artista = next(
            (a for a in self.todos if a["nome"].casefold() == chave), None)
        if artista is not None:
            self._abrir(artista["chave"], artista["nome"])

    # ---------- lista de artistas ----------

    def _atualizar_lista(self):
        rolagem = self.lista.verticalScrollBar().value()

        grupos = {}
        for linha in db.listar_musicas():
            m = dict(linha)
            nome = m["artista"] or "Artista desconhecido"
            chave = nome.casefold()
            g = grupos.get(chave)
            if g is None:
                g = {"chave": chave, "nome": nome, "total": 0,
                     "duracao": 0, "musica_capa": m}
                grupos[chave] = g
            g["total"] += 1
            g["duracao"] += m["duracao"]
            if not g["musica_capa"]["capa"] and m["capa"]:
                g["musica_capa"] = m      # prefere uma música que tenha capa

        self.todos = sorted(
            grupos.values(),
            key=lambda g: (_chave_ordenacao(g["nome"]), g["nome"].casefold()))
        self._aplicar_filtro()
        self.lista.verticalScrollBar().setValue(rolagem)

    def _aplicar_filtro(self, _=None):
        termo = self.busca.text().strip().casefold()
        self.exibidos = [a for a in self.todos if termo in a["nome"].casefold()]
        self.delegate.itens = self.exibidos
        self.delegate.esteira.limpar()

        self.lista.clear()
        for _a in self.exibidos:
            self.lista.addItem(QListWidgetItem())

        n = len(self.exibidos)
        self.lbl_info.setText(f"{n} {'artista' if n == 1 else 'artistas'}")
        if termo and self.todos:
            self.lbl_vazio.setText("Nenhum artista encontrado.")
        else:
            self.lbl_vazio.setText("Nenhum artista ainda.\nAdicione músicas para vê-los aqui.")
        self.lista.setVisible(n > 0)
        self.lbl_vazio.setVisible(n == 0)

    def _clicou_artista(self, item):
        artista = self.exibidos[self.lista.row(item)]
        self._abrir(artista["chave"], artista["nome"])

    # ---------- dentro de um artista ----------

    def _musicas_do_artista(self):
        return [m for m in db.listar_musicas()
                if (m["artista"] or "Artista desconhecido").casefold() == self.chave]

    def _abrir(self, chave, nome):
        self.chave = chave
        self.detalhe.busca.clear()
        self.detalhe.definir_titulo(nome)
        self.pilha.setCurrentIndex(1)
        self._atualizar_detalhe()
        self.detalhe.lista.verticalScrollBar().setValue(0)

    def _voltar(self):
        self.pilha.setCurrentIndex(0)
        self.chave = None
        self._atualizar_lista()

    def _atualizar_detalhe(self):
        if not self._musicas_do_artista():   # todas as músicas dele foram excluídas
            self._voltar()
            return
        self.detalhe.carregar()