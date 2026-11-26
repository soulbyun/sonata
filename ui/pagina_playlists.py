import shutil
import uuid
from pathlib import Path

from PySide6.QtCore import QPoint, QRect, QSize, Qt, Signal
from PySide6.QtGui import QColor, QFont, QPainter, QPixmap
from PySide6.QtWidgets import (QFileDialog, QHBoxLayout, QInputDialog, QLabel,
                               QLineEdit, QListWidget, QListWidgetItem, QMenu,
                               QMessageBox, QPushButton, QStackedWidget, QStyle,
                               QStyledItemDelegate, QVBoxLayout, QWidget)

import db
import library
from ui import temas, util
from ui.pagina_musicas import PaginaMusicas

FILTRO_IMAGEM = "Imagens (*.jpg *.jpeg *.png *.webp)"


def _cobrir(pm, largura, altura):
    """Redimensiona a imagem para preencher o retângulo, cortando o excesso."""
    pm = pm.scaled(largura, altura, Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation)
    return pm.copy((pm.width() - largura) // 2, (pm.height() - altura) // 2,
                   largura, altura)


def _miniatura(banner, musicas, lado=48):
    """Quadradinho da lista: o banner personalizado ou um mosaico de capas."""
    if banner:
        pm = QPixmap(str(util.RAIZ / banner))
        if not pm.isNull():
            return _cobrir(pm, lado, lado)

    pm = QPixmap(lado, lado)
    pm.fill(QColor(temas.cor("elevado")))
    p = QPainter(pm)
    if len(musicas) >= 4:
        metade = lado // 2
        for i, m in enumerate(musicas[:4]):
            p.drawPixmap((i % 2) * metade, (i // 2) * metade,
                         util.pixmap_capa(m, metade))
    elif musicas:
        p.drawPixmap(0, 0, util.pixmap_capa(musicas[0], lado))
    else:
        p.setPen(QColor(util.TEXTO_SUAVE))
        fonte = p.font()
        fonte.setPixelSize(22)
        p.setFont(fonte)
        p.drawText(pm.rect(), Qt.AlignCenter, "♪")
    p.end()
    return pm


class Banner(QWidget):
    """Faixa no topo da playlist: o banner personalizado ou as capas das músicas."""
    ALTURA = 190

    def __init__(self):
        super().__init__()
        self.setFixedHeight(self.ALTURA)
        self.banner = None
        self.musicas = []
        self._cache = None

    def definir(self, caminho, musicas):
        pm = QPixmap(str(util.RAIZ / caminho)) if caminho else None
        self.banner = pm if pm is not None and not pm.isNull() else None
        self.musicas = musicas
        self._cache = None
        self.update()

    def paintEvent(self, evento):
        largura, altura = self.width(), self.height()
        if largura < 1:
            return
        p = QPainter(self)
        p.fillRect(self.rect(), QColor(temas.cor("cartao")))

        if self.banner is not None:
            if self._cache is None or self._cache.width() != largura:
                self._cache = _cobrir(self.banner, largura, altura)
            p.drawPixmap(0, 0, self._cache)
        elif self.musicas:
            n = len(self.musicas)
            for i in range(largura // altura + 1):
                p.drawPixmap(i * altura, 0, util.pixmap_capa(self.musicas[i % n], altura))
        else:
            p.setPen(QColor(util.TEXTO_SUAVE))
            fonte = p.font()
            fonte.setPixelSize(60)
            p.setFont(fonte)
            p.drawText(self.rect(), Qt.AlignCenter, "♪")
        p.end()


class LinhaPlaylist(QStyledItemDelegate):
    """Desenha cada playlist da lista."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.itens = []

    def sizeHint(self, option, index):
        return QSize(0, 66)

    def paint(self, painter, option, index):
        pl = self.itens[index.row()]
        selecionado = bool(option.state & QStyle.State_Selected)
        r = option.rect
        painter.save()

        if selecionado:
            painter.fillRect(r, QColor(temas.cor("elevado")))
        elif option.state & QStyle.State_MouseOver:
            painter.fillRect(r, QColor(temas.cor("cartao")))

        painter.drawPixmap(r.left() + 14, r.top() + 9, pl["miniatura"])

        x_texto = r.left() + 76
        largura = max(r.right() - 50 - x_texto, 20)

        fonte_nome = QFont(option.font)
        fonte_nome.setPixelSize(15)
        painter.setFont(fonte_nome)
        painter.setPen(QColor(util.TEXTO))
        nome = painter.fontMetrics().elidedText(pl["nome"], Qt.ElideRight, largura)
        painter.drawText(QRect(x_texto, r.top() + 13, largura, 20),
                         Qt.AlignLeft | Qt.AlignVCenter, nome)

        fonte_info = QFont(option.font)
        fonte_info.setPixelSize(13)
        painter.setFont(fonte_info)
        painter.setPen(QColor(
            util.TEXTO if selecionado else util.TEXTO_SUAVE))
        n = pl["total"]
        texto = f"{n} {'música' if n == 1 else 'músicas'} · {pl['duracao'] // 60} min"
        painter.drawText(QRect(x_texto, r.top() + 34, largura, 18),
                         Qt.AlignLeft | Qt.AlignVCenter, texto)

        fonte_seta = QFont(option.font)
        fonte_seta.setPixelSize(20)
        painter.setFont(fonte_seta)
        painter.drawText(QRect(r.right() - 40, r.top(), 24, r.height()),
                         Qt.AlignCenter, "›")

        painter.restore()


class PaginaPlaylists(QWidget):
    tocar = Signal(list, int)
    tocar_aleatorio = Signal(list)
    acao_musica = Signal(str, object)
    def __init__(self):
        super().__init__()
        self.playlist_id = None

        # ===== parte 1: lista de playlists =====
        titulo = QLabel("Playlists")
        titulo.setObjectName("tituloPagina")
        self.lbl_info = QLabel()
        self.lbl_info.setObjectName("infoPagina")
        textos = QVBoxLayout()
        textos.setSpacing(2)
        textos.addWidget(titulo)
        textos.addWidget(self.lbl_info)

        btn_nova = QPushButton("+  Nova playlist")
        btn_nova.setObjectName("secundario")
        btn_nova.clicked.connect(lambda: self._nova())

        topo = QWidget()
        topo_layout = QHBoxLayout(topo)
        topo_layout.setContentsMargins(24, 22, 24, 16)
        topo_layout.addLayout(textos)
        topo_layout.addStretch()
        topo_layout.addWidget(btn_nova)

        self.delegate = LinhaPlaylist()
        self.lista = QListWidget()
        self.lista.setItemDelegate(self.delegate)
        self.lista.setMouseTracking(True)
        self.lista.setVerticalScrollMode(QListWidget.ScrollPerPixel)
        self.lista.setFocusPolicy(Qt.NoFocus)
        self.lista.itemClicked.connect(self._clicou_playlist)

        self.lbl_vazio = QLabel("Nenhuma playlist ainda.\nClique em Nova playlist para criar a primeira.")
        self.lbl_vazio.setObjectName("vazio")
        self.lbl_vazio.setAlignment(Qt.AlignCenter)

        pagina_lista = QWidget()
        col = QVBoxLayout(pagina_lista)
        col.setContentsMargins(0, 0, 0, 0)
        col.setSpacing(0)
        col.addWidget(topo)
        col.addWidget(self.lista, 1)
        col.addWidget(self.lbl_vazio, 1)

        # ===== parte 2: dentro de uma playlist =====
        self.detalhe = PaginaMusicas("", self._musicas_da_playlist)
        self.banner = Banner()
        self.detalhe.colocar_acima(self.banner)

        btn_voltar = QPushButton("←")
        btn_voltar.setObjectName("botaoIcone")
        btn_voltar.setToolTip("Voltar às playlists")
        btn_voltar.clicked.connect(lambda: self._voltar())
        self.detalhe.adicionar_a_esquerda(btn_voltar)

        self.btn_pincel = QPushButton("✎")
        self.btn_pincel.setObjectName("botaoIcone")
        self.btn_pincel.setToolTip("Personalizar playlist")
        self.btn_pincel.clicked.connect(lambda: self._abrir_menu())
        self.detalhe.adicionar_ao_titulo(self.btn_pincel)

        self.detalhe.definir_texto_vazio(
            "Esta playlist está vazia.\nAdicione músicas pela aba Adicionar música.")
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
        if self.pilha.currentIndex() == 1 and self.playlist_id is not None:
            self._atualizar_detalhe()
        else:
            self._atualizar_lista()

    def marcar_tocando(self, musica_id):
        self.detalhe.marcar_tocando(musica_id)

    # ---------- lista de playlists ----------

    def _atualizar_lista(self):
        resumo = [dict(r) for r in db.resumo_playlists()]
        for r in resumo:
            musicas = db.listar_musicas_da_playlist(r["id"])
            r["miniatura"] = _miniatura(r["banner"], musicas[:4])
        self.delegate.itens = resumo

        self.lista.clear()
        for _r in resumo:
            self.lista.addItem(QListWidgetItem())

        n = len(resumo)
        self.lbl_info.setText(f"{n} {'playlist' if n == 1 else 'playlists'}")
        self.lista.setVisible(n > 0)
        self.lbl_vazio.setVisible(n == 0)

    def _nova(self):
        nome, ok = QInputDialog.getText(self, "Nova playlist", "Nome da playlist:")
        nome = nome.strip()
        if ok and nome:
            db.criar_playlist(nome)
            self._atualizar_lista()

    def _clicou_playlist(self, item):
        playlist = self.delegate.itens[self.lista.row(item)]
        self._abrir(playlist["id"])

    # ---------- dentro da playlist ----------

    def _musicas_da_playlist(self):
        return db.listar_musicas_da_playlist(self.playlist_id)

    def _abrir(self, playlist_id):
        self.playlist_id = playlist_id
        self.detalhe.busca.clear()
        self.pilha.setCurrentIndex(1)
        self._atualizar_detalhe()
        self.detalhe.lista.verticalScrollBar().setValue(0)

    def _voltar(self):
        self.pilha.setCurrentIndex(0)
        self.playlist_id = None
        self._atualizar_lista()

    def _atualizar_detalhe(self):
        playlist = db.obter_playlist(self.playlist_id)
        if playlist is None:           # foi excluída
            self._voltar()
            return
        self.detalhe.definir_titulo(playlist["nome"])
        self.detalhe.carregar()
        self.banner.definir(playlist["banner"], self.detalhe.todas)

    # ---------- menu do pincel ----------

    def _abrir_menu(self):
        playlist = db.obter_playlist(self.playlist_id)
        if playlist is None:
            return
        menu = QMenu(self)
        a_renomear = menu.addAction("Renomear")
        a_renomear.triggered.connect(self._renomear)
        a_banner = menu.addAction("Escolher banner…")
        a_banner.triggered.connect(self._escolher_banner)
        if playlist["banner"]:
            a_capas = menu.addAction("Usar capas das músicas")
            a_capas.triggered.connect(self._remover_banner)
        menu.addSeparator()
        a_excluir = menu.addAction("Excluir playlist")
        a_excluir.triggered.connect(self._excluir)
        menu.exec(self.btn_pincel.mapToGlobal(QPoint(0, self.btn_pincel.height())))

    def _renomear(self):
        playlist = db.obter_playlist(self.playlist_id)
        if playlist is None:
            return
        nome, ok = QInputDialog.getText(
            self, "Renomear playlist", "Novo nome:", QLineEdit.Normal, playlist["nome"])
        nome = nome.strip()
        if ok and nome:
            db.renomear_playlist(self.playlist_id, nome)
            self._atualizar_detalhe()

    def _apagar_arquivo_banner(self, playlist):
        if playlist is not None and playlist["banner"]:
            arquivo = util.RAIZ / playlist["banner"]
            if arquivo.exists():
                arquivo.unlink()

    def _escolher_banner(self):
        caminho, _ = QFileDialog.getOpenFileName(
            self, "Escolher banner", "", FILTRO_IMAGEM)
        if not caminho or QPixmap(caminho).isNull():
            return
        origem = Path(caminho)
        library.PASTA_CAPAS.mkdir(parents=True, exist_ok=True)
        destino = library.PASTA_CAPAS / f"banner_{uuid.uuid4().hex[:10]}{origem.suffix.lower()}"
        shutil.copy2(origem, destino)

        self._apagar_arquivo_banner(db.obter_playlist(self.playlist_id))
        db.definir_banner_playlist(
            self.playlist_id, destino.relative_to(library.RAIZ).as_posix())
        self._atualizar_detalhe()

    def _remover_banner(self):
        self._apagar_arquivo_banner(db.obter_playlist(self.playlist_id))
        db.definir_banner_playlist(self.playlist_id, None)
        self._atualizar_detalhe()

    def _excluir(self):
        playlist = db.obter_playlist(self.playlist_id)
        if playlist is None:
            return
        caixa = QMessageBox(self)
        caixa.setWindowTitle("Excluir playlist")
        caixa.setText(f"Excluir a playlist \"{playlist['nome']}\"?")
        caixa.setInformativeText("As músicas continuam na biblioteca.")
        excluir = caixa.addButton("Excluir", QMessageBox.AcceptRole)
        caixa.addButton("Cancelar", QMessageBox.RejectRole)
        caixa.exec()
        if caixa.clickedButton() == excluir:
            self._apagar_arquivo_banner(playlist)
            db.excluir_playlist(self.playlist_id)
            self._voltar()