import shutil
import uuid
from pathlib import Path

from PySide6.QtCore import (QPoint, QRect, QRectF, QSize, Qt, Signal, QTimer,
                            QVariantAnimation)
from PySide6.QtGui import (QBrush, QColor, QFont, QFontMetrics, QIcon,
                           QLinearGradient, QPainter, QPainterPath, QPixmap)
from PySide6.QtWidgets import (QApplication, QFileDialog, QHBoxLayout,
                               QInputDialog, QLabel, QFrame, QLayout,
                               QLineEdit, QMenu, QMessageBox, QPushButton,
                               QStackedWidget, QStyle, QStyledItemDelegate,
                               QSizePolicy, QVBoxLayout, QWidget)

import db
import library
from ui import temas, util
from ui.icones import icone
from ui.pagina_musicas import PaginaMusicas
from ui.texto_esteira import AnimacaoEsteira, TextoEsteira

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
            return util.arredondar_capa(_cobrir(pm, lado, lado))

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
    return util.arredondar_capa(pm)


def _imagem_palco(banner, musicas, largura, altura):
    if banner:
        pm = QPixmap(str(util.RAIZ / banner))
        if not pm.isNull():
            return _cobrir(pm, largura, altura)

    capas = []
    for musica in musicas:
        if not musica.get("capa"):
            continue
        pm = QPixmap(str(util.RAIZ / musica["capa"]))
        if not pm.isNull():
            capas.append(pm)
        if len(capas) == 4:
            break
    if not capas:
        return None

    resultado = QPixmap(largura, altura)
    pintor = QPainter(resultado)
    if len(capas) == 1:
        pintor.drawPixmap(0, 0, _cobrir(capas[0], largura, altura))
    elif len(capas) == 2:
        metade = largura // 2
        for indice, capa in enumerate(capas):
            x = indice * metade
            celula_largura = largura - x if indice == 1 else metade
            pintor.drawPixmap(
                x, 0, _cobrir(capa, celula_largura, altura))
    else:
        metade_largura = largura // 2
        metade_altura = altura // 2
        for indice, capa in enumerate(capas):
            x = (indice % 2) * metade_largura
            y = (indice // 2) * metade_altura
            celula_largura = largura - x if x else metade_largura
            celula_altura = altura - y if y else metade_altura
            pintor.drawPixmap(
                x, y, _cobrir(capa, celula_largura, celula_altura))
    pintor.end()
    return resultado


def _desfocar(pm, largura, altura):
    pm = _cobrir(pm, largura, altura)
    reduzida = pm.scaled(
        max(1, largura // 12), max(1, altura // 12),
        Qt.IgnoreAspectRatio, Qt.SmoothTransformation)
    return reduzida.scaled(
        largura, altura, Qt.IgnoreAspectRatio, Qt.SmoothTransformation)


def _arredondar(pm, raio):
    if pm.isNull() or temas.cor("raio") == "0px":
        return pm
    resultado = QPixmap(pm.size())
    resultado.fill(Qt.transparent)
    pintor = QPainter(resultado)
    pintor.setRenderHint(QPainter.Antialiasing)
    caminho = QPainterPath()
    caminho.addRoundedRect(QRectF(pm.rect()), raio, raio)
    pintor.setClipPath(caminho)
    pintor.drawPixmap(0, 0, pm)
    pintor.end()
    return resultado


def _miniatura_pilula(banner, musicas, lado):
    if not banner and not any(musica.get("capa") for musica in musicas):
        capa = util.pixmap_capa(None, lado)
    else:
        capa = _miniatura(banner, musicas[:4], lado)
    if temas.cor("raio") == "0px":
        return capa
    resultado = QPixmap(capa.size())
    resultado.fill(Qt.transparent)
    pintor = QPainter(resultado)
    pintor.setRenderHint(QPainter.Antialiasing)
    caminho = QPainterPath()
    caminho.addEllipse(QRectF(capa.rect()))
    pintor.setClipPath(caminho)
    pintor.drawPixmap(0, 0, capa)
    pintor.end()
    return resultado


class FluxoLayout(QLayout):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._itens = []
        self.setContentsMargins(0, 0, 0, 0)
        self.setSpacing(8)

    def addItem(self, item):
        self._itens.append(item)
        self.invalidate()

    def count(self):
        return len(self._itens)

    def itemAt(self, indice):
        if 0 <= indice < len(self._itens):
            return self._itens[indice]
        return None

    def takeAt(self, indice):
        if 0 <= indice < len(self._itens):
            return self._itens.pop(indice)
        return None

    def expandingDirections(self):
        return Qt.Orientations()

    def hasHeightForWidth(self):
        return True

    def heightForWidth(self, largura):
        return self._distribuir(QRect(0, 0, largura, 0), True)

    def setGeometry(self, retangulo):
        super().setGeometry(retangulo)
        self._distribuir(retangulo, False)

    def sizeHint(self):
        return QSize(0, self.heightForWidth(self.geometry().width()))

    def minimumSize(self):
        margens = self.contentsMargins()
        largura = max(
            (item.minimumSize().width() for item in self._itens),
            default=0)
        altura = max(
            (item.minimumSize().height() for item in self._itens),
            default=0)
        return QSize(
            largura + margens.left() + margens.right(),
            altura + margens.top() + margens.bottom())

    def _distribuir(self, retangulo, medir):
        margens = self.contentsMargins()
        x_inicio = retangulo.x() + margens.left()
        x = x_inicio
        y = retangulo.y() + margens.top()
        x_final = retangulo.x() + retangulo.width() - margens.right()
        altura_linha = 0
        espaco = self.spacing()

        for item in self._itens:
            tamanho = item.sizeHint().expandedTo(item.minimumSize())
            if altura_linha and x + tamanho.width() > x_final:
                x = x_inicio
                y += altura_linha + espaco
                altura_linha = 0
            if not medir:
                item.setGeometry(QRect(QPoint(x, y), tamanho))
            x += tamanho.width() + espaco
            altura_linha = max(altura_linha, tamanho.height())

        return y + altura_linha + margens.bottom() - retangulo.y()


class RotuloClicavel(QLabel):
    clicado = Signal()

    def mousePressEvent(self, evento):
        if evento.button() == Qt.LeftButton:
            self.clicado.emit()
        super().mousePressEvent(evento)


class Palco(QFrame):
    def __init__(self):
        super().__init__()
        self.setObjectName("palcoPlaylists")
        self._fundo = None
        self._fundo_anterior = None
        self._cache_fundo = None
        self._cache_anterior = None
        self._progresso = 1.0
        self._animacao = QVariantAnimation(self)
        self._animacao.setDuration(200)
        self._animacao.setStartValue(0.0)
        self._animacao.setEndValue(1.0)
        self._animacao.valueChanged.connect(self._animar_fundo)
        self._animacao.finished.connect(self._fim_animacao)

    def definir_fundo(self, pm, animar=True):
        atual = pm if pm is not None and not pm.isNull() else None
        chave_atual = (
            self._fundo.cacheKey() if self._fundo is not None else None)
        chave_nova = atual.cacheKey() if atual else None
        if chave_atual == chave_nova:
            return

        self._animacao.stop()
        self._fundo_anterior = self._fundo
        self._fundo = atual
        self._cache_fundo = None
        self._cache_anterior = None
        if animar:
            self._progresso = 0.0
            self._animacao.start()
        else:
            self._progresso = 1.0
            self._fundo_anterior = None
        self.update()

    def _animar_fundo(self, valor):
        self._progresso = float(valor)
        self.update()

    def _fim_animacao(self):
        self._fundo_anterior = None
        self._cache_anterior = None
        self.update()

    def _fundo_desfocado(self, original, anterior=False):
        atributo = "_cache_anterior" if anterior else "_cache_fundo"
        cache = getattr(self, atributo)
        tamanho = self.size()
        if (cache is None or cache.size() != tamanho):
            cache = _desfocar(original, self.width(), self.height())
            setattr(self, atributo, cache)
        return cache

    def paintEvent(self, evento):
        largura, altura = self.width(), self.height()
        if largura < 1 or altura < 1:
            return

        pintor = QPainter(self)
        pintor.setRenderHint(QPainter.Antialiasing)
        caminho = QPainterPath()
        raio = int(temas.cor("raio").replace("px", ""))
        caminho.addRoundedRect(QRectF(self.rect()), raio, raio)
        pintor.setClipPath(caminho)

        paleta = temas.TEMAS[temas.tema_atual()][1]
        cor_fundo = paleta.get("fundo") or paleta.get("cartao")
        if cor_fundo is None:
            cor_fundo = temas.cor("fundo")
        pintor.fillRect(self.rect(), QColor(cor_fundo))
        if self._fundo_anterior is not None:
            pintor.setOpacity(0.18 * (1.0 - self._progresso))
            pintor.drawPixmap(
                self.rect(),
                self._fundo_desfocado(self._fundo_anterior, anterior=True))
        if self._fundo is not None:
            pintor.setOpacity(0.18 * self._progresso)
            pintor.drawPixmap(
                self.rect(), self._fundo_desfocado(self._fundo))

        pintor.setOpacity(1.0)
        inicio = paleta.get("fundo_a")
        fim = paleta.get("fundo_b")
        if inicio is not None and fim is not None:
            gradiente = QLinearGradient(0, 0, largura, altura)
            cor_inicio = QColor(inicio)
            cor_fim = QColor(fim)
            cor_inicio.setAlphaF(0.85)
            cor_fim.setAlphaF(0.85)
            gradiente.setColorAt(0, cor_inicio)
            gradiente.setColorAt(1, cor_fim)
            pintor.fillRect(self.rect(), QBrush(gradiente))
        else:
            cor_solida = QColor(cor_fundo)
            cor_solida.setAlphaF(0.85)
            pintor.fillRect(self.rect(), cor_solida)
        pintor.end()
        super().paintEvent(evento)


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
        p.setRenderHint(QPainter.Antialiasing)
        caminho = QPainterPath()
        raio = int(temas.cor("raio_capa"))
        caminho.addRoundedRect(QRectF(self.rect()), raio, raio)
        p.setClipPath(caminho)
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
        lista = parent
        self.esteira = AnimacaoEsteira(
            lista, lambda: lista.viewport().update() if lista is not None else None)

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
        self.esteira.pintar(
            painter, QRect(x_texto, r.top() + 13, largura, 20), pl["nome"],
            fonte_nome, QColor(util.TEXTO), index.row(),
            bool(option.state & QStyle.State_MouseOver))

        fonte_info = QFont(option.font)
        fonte_info.setPixelSize(13)
        painter.setFont(fonte_info)
        painter.setPen(QColor(
            util.TEXTO if selecionado else util.TEXTO_SUAVE))
        n = pl["total"]
        if pl.get("inteligente"):
            texto = f"Automática · {n} {'música' if n == 1 else 'músicas'}"
        else:
            texto = (
                f"{n} {'música' if n == 1 else 'músicas'} · "
                f"{pl['duracao'] // 60} min")
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
    playlist_reordenada = Signal(int)

    def __init__(self):
        super().__init__()
        self.playlist_id = None
        self._mais_tocadas_aberta = False
        self._playlist_palco_id = None
        self._playlists_palco = []
        self._botoes_playlist = {}
        self._player = None
        self._musica_clique_pendente = None

        # ===== parte 1: palco e seletor =====
        titulo = QLabel("Playlists")
        titulo.setObjectName("tituloPagina")
        titulo.setProperty("tituloPlaylists", True)

        cor_icone = temas.cor("texto_suave")
        self.btn_pincel = QPushButton()
        self.btn_pincel.setObjectName("botaoIcone")
        self.btn_pincel.setFixedSize(36, 36)
        self.btn_pincel.setIcon(
            icone("pincel", cor=cor_icone, tamanho=20))
        self.btn_pincel.setIconSize(QSize(20, 20))
        self.btn_pincel.setToolTip("Personalizar playlist")
        self.btn_pincel.clicked.connect(self._abrir_menu)

        btn_nova = QPushButton()
        btn_nova.setObjectName("secundario")
        btn_nova.setProperty("botaoIconePlaylist", True)
        btn_nova.setFixedSize(36, 36)
        btn_nova.setIcon(
            icone("playlist", cor=cor_icone, tamanho=20))
        btn_nova.setIconSize(QSize(20, 20))
        btn_nova.setToolTip("Nova playlist")
        btn_nova.clicked.connect(lambda: self._nova())
        self.btn_nova_playlist = btn_nova

        topo = QWidget()
        topo_layout = QHBoxLayout(topo)
        topo_layout.setContentsMargins(24, 22, 24, 16)
        topo_layout.addWidget(titulo)
        topo_layout.addStretch()
        topo_layout.addWidget(self.btn_pincel)
        topo_layout.addWidget(self.btn_nova_playlist)

        self.palco = Palco()
        layout_palco = QVBoxLayout(self.palco)
        layout_palco.setContentsMargins(24, 24, 24, 20)
        layout_palco.setSpacing(20)

        principal_palco = QHBoxLayout()
        principal_palco.setSpacing(24)
        coluna_esquerda = QWidget()
        coluna_esquerda.setFixedWidth(220)
        layout_esquerda = QVBoxLayout(coluna_esquerda)
        layout_esquerda.setContentsMargins(0, 0, 0, 0)
        layout_esquerda.setSpacing(16)

        self.capa_palco = QLabel()
        self.capa_palco.setObjectName("capaPalco")
        self.capa_palco.setFixedSize(220, 220)
        self.capa_palco.setAlignment(Qt.AlignCenter)
        layout_esquerda.addWidget(self.capa_palco)

        self.btn_reproduzir_palco = QPushButton()
        self.btn_reproduzir_palco.setObjectName("botaoPlay")
        self.btn_reproduzir_palco.setProperty("palco", True)
        self.btn_reproduzir_palco.setFixedSize(48, 48)
        self.btn_reproduzir_palco.setIconSize(QSize(20, 20))
        self.btn_reproduzir_palco.setToolTip("Reproduzir playlist")
        self.btn_reproduzir_palco.clicked.connect(
            self._reproduzir_palco)
        layout_esquerda.addWidget(
            self.btn_reproduzir_palco, 0, Qt.AlignHCenter)
        layout_esquerda.addStretch()
        principal_palco.addWidget(coluna_esquerda, 0, Qt.AlignTop)

        informacoes = QWidget()
        coluna_info = QVBoxLayout(informacoes)
        coluna_info.setContentsMargins(0, 0, 0, 0)
        coluna_info.setSpacing(8)

        etiqueta = QLabel("PLAYLIST")
        etiqueta.setObjectName("etiquetaPlaylist")
        coluna_info.addWidget(etiqueta)

        self.nome_palco = TextoEsteira()
        self.nome_palco.setObjectName("nomePalco")
        self.nome_palco.setSizePolicy(
            QSizePolicy.Ignored, QSizePolicy.Preferred)
        self.nome_palco.setFixedHeight(42)
        coluna_info.addWidget(self.nome_palco)

        self.info_palco = QLabel()
        self.info_palco.setObjectName("infoPalco")
        coluna_info.addWidget(self.info_palco)
        principal_palco.addWidget(informacoes, 1)
        layout_palco.addLayout(principal_palco, 1)

        divisor = QFrame()
        divisor.setObjectName("divisor")
        divisor.setFixedHeight(1)
        layout_palco.addWidget(divisor)

        self.seletor_playlists = QWidget()
        self.seletor_playlists.setSizePolicy(
            QSizePolicy.Expanding, QSizePolicy.Minimum)
        self.layout_seletor = FluxoLayout(self.seletor_playlists)
        self.layout_seletor.setSpacing(8)
        layout_palco.addWidget(self.seletor_playlists)

        pagina_palco = QWidget()
        col = QVBoxLayout(pagina_palco)
        col.setContentsMargins(0, 0, 0, 24)
        col.setSpacing(0)
        col.addWidget(topo)
        col.addWidget(self.palco, 1)

        # ===== parte 2: dentro de uma playlist =====
        self.detalhe = PaginaMusicas("", self._musicas_da_playlist)
        self.detalhe.habilitar_reordenacao(self._reordenar_musicas)
        self.banner = Banner()
        self.detalhe.colocar_acima(self.banner)

        self.detalhe.raiz.removeWidget(self.detalhe.lista)
        self.detalhe.raiz.removeWidget(self.detalhe.lbl_vazio)
        self.detalhe.lista.setObjectName("listaPalco")
        self.detalhe.lista.setHorizontalScrollBarPolicy(
            Qt.ScrollBarAlwaysOff)
        self.detalhe.lista.itemClicked.connect(
            self._agendar_tocar_linha)
        self.detalhe.lista.itemDoubleClicked.connect(
            self._cancelar_tocar_linha)
        self._temporizador_clique = QTimer(self)
        self._temporizador_clique.setSingleShot(True)
        self._temporizador_clique.setInterval(
            QApplication.doubleClickInterval())
        self._temporizador_clique.timeout.connect(
            self._tocar_linha_selecionada)
        coluna_info.addWidget(self.detalhe.lista, 1)
        coluna_info.addWidget(self.detalhe.lbl_vazio, 1)

        btn_voltar = QPushButton("←")
        btn_voltar.setObjectName("botaoIcone")
        btn_voltar.setToolTip("Voltar às playlists")
        btn_voltar.clicked.connect(lambda: self._voltar())
        self.detalhe.adicionar_a_esquerda(btn_voltar)

        self.detalhe.definir_texto_vazio(
            "Nenhuma música ainda.")
        self.detalhe.tocar.connect(self.tocar)
        self.detalhe.tocar_aleatorio.connect(self.tocar_aleatorio)
        self.detalhe.acao_musica.connect(self.acao_musica)
        # ===== junta as duas partes =====
        self.pilha = QStackedWidget()
        self.pilha.addWidget(pagina_palco)   # 0
        self.pilha.addWidget(self.detalhe)   # 1
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.pilha)

    # ---------- usadas pela janela principal ----------

    def carregar(self):
        if (self.pilha.currentIndex() == 1
                and (self.playlist_id is not None
                     or self._mais_tocadas_aberta)):
            self._atualizar_detalhe()
        else:
            self._atualizar_lista()

    def marcar_tocando(self, musica_id):
        self.detalhe.marcar_tocando(musica_id)
        self._atualizar_icone_reproducao()

    def showEvent(self, evento):
        super().showEvent(evento)
        player = getattr(self.window(), "player", None)
        if player is not self._player:
            self._player = player
            if player is not None:
                player.estado_mudou.connect(
                    self._atualizar_icone_reproducao)
                player.fila_mudou.connect(
                    self._atualizar_icone_reproducao)
        if self._player is not None:
            musica = self._player.musica_atual
            self.detalhe.marcar_tocando(
                musica["id"] if musica is not None else None)
        self._atualizar_icone_reproducao()

    def atualizar_tema(self):
        cor_icone = temas.cor("texto_suave")
        self.btn_pincel.setIcon(
            icone("pincel", cor=cor_icone, tamanho=20))
        self.btn_nova_playlist.setIcon(
            icone("playlist", cor=cor_icone, tamanho=20))
        self._atualizar_lista()
        if self.pilha.currentIndex() == 1:
            self._atualizar_detalhe()
        self.detalhe.atualizar_tema()
        self._atualizar_icone_reproducao()

    def _fila_corresponde(self, playlist):
        if self._player is None or self._player.musica_atual is None:
            return False
        ids_playlist = sorted(
            musica["id"] for musica in playlist["musicas"])
        ids_fila = sorted(
            musica["id"] for musica in self._player.fila)
        return bool(ids_playlist) and ids_playlist == ids_fila

    def _atualizar_icone_reproducao(self):
        if not hasattr(self, "btn_reproduzir_palco"):
            return
        playlist = next(
            (item for item in self._playlists_palco
             if item["id"] == self._playlist_palco_id),
            self._playlists_palco[0] if self._playlists_palco else None)
        tocando = (
            playlist is not None and self._player is not None
            and self._player.tocando and self._fila_corresponde(playlist))
        nome_icone = "pause" if tocando else "play"
        cor_play = (
            temas.cor("hud_amarelo") or temas.cor("texto_suave"))
        self.btn_reproduzir_palco.setIcon(
            icone(nome_icone, cor=cor_play, tamanho=20))
        self.btn_reproduzir_palco.setIconSize(QSize(20, 20))

    # ---------- lista de playlists ----------

    def _atualizar_lista(self):
        resumo = [dict(r) for r in db.resumo_playlists()]
        for r in resumo:
            musicas = [dict(m) for m in
                       db.listar_musicas_da_playlist(r["id"])]
            r["musicas"] = musicas
            r["miniatura"] = _miniatura(r["banner"], musicas[:4])
        mais_tocadas = [
            dict(m) for m in db.listar_mais_tocadas()]
        inteligente = {
            "id": None,
            "nome": "Mais tocadas",
            "banner": None,
            "total": len(mais_tocadas),
            "duracao": sum(m["duracao"] for m in mais_tocadas),
            "musicas": mais_tocadas,
            "miniatura": _miniatura(None, mais_tocadas[:4]),
            "inteligente": True,
        }
        self._playlists_palco = [inteligente] + resumo
        ids = {playlist["id"] for playlist in self._playlists_palco}
        if self._playlist_palco_id not in ids:
            self._playlist_palco_id = None
        self._atualizar_seletor()
        self._atualizar_palco(False)

    def _atualizar_seletor(self):
        while self.layout_seletor.count():
            item = self.layout_seletor.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.hide()
                widget.deleteLater()
        self._botoes_playlist.clear()

        mafty = temas.cor("raio") == "0px"
        for playlist in self._playlists_palco:
            botao = QPushButton()
            botao.setObjectName("playlistPill")
            botao.setProperty(
                "selecionada",
                playlist["id"] == self._playlist_palco_id)
            botao.setProperty("mafty", mafty)
            botao.setCursor(Qt.PointingHandCursor)
            botao.setFixedHeight(44)
            botao.setMaximumWidth(180)
            botao.setMinimumWidth(90)
            botao.setIcon(QIcon(_miniatura_pilula(
                playlist["banner"], playlist["musicas"], 28)))
            botao.setIconSize(QSize(28, 28))
            largura_texto = 106
            botao.setText(QFontMetrics(botao.font()).elidedText(
                playlist["nome"], Qt.ElideRight, largura_texto))
            botao.setToolTip(playlist["nome"])
            botao.clicked.connect(
                lambda _marcado=False, chave=playlist["id"]:
                self._focar_playlist(chave))
            self.layout_seletor.addWidget(botao)
            self._botoes_playlist[playlist["id"]] = botao

    def _atualizar_palco(self, animar):
        if not self._playlists_palco:
            return
        playlist = next(
            (item for item in self._playlists_palco
             if item["id"] == self._playlist_palco_id),
            self._playlists_palco[0])
        inteligente = bool(playlist.get("inteligente"))
        self._playlist_palco_id = playlist["id"]
        self.playlist_id = playlist["id"]
        self._mais_tocadas_aberta = inteligente

        capa = _miniatura(
            playlist["banner"], playlist["musicas"][:4], 220)
        self.capa_palco.setPixmap(
            _arredondar(
                capa, int(temas.cor("raio").replace("px", ""))))
        self.nome_palco.setText(playlist["nome"])
        total = playlist["total"]
        quantidade = f"{total} {'música' if total == 1 else 'músicas'}"
        if playlist.get("inteligente"):
            quantidade = f"Automática · {quantidade}"
        self.info_palco.setText(quantidade)

        self.btn_pincel.setEnabled(not inteligente)
        self.btn_reproduzir_palco.setEnabled(bool(playlist["musicas"]))
        self.detalhe.definir_reordenacao_bloqueada(inteligente)
        self.detalhe.definir_texto_vazio(
            "Toque algumas músicas para ver as mais tocadas aqui."
            if inteligente else "Nenhuma música ainda.")
        self._temporizador_clique.stop()
        self._musica_clique_pendente = None
        self.detalhe.carregar()

        largura = max(800, self.palco.width())
        altura = max(500, self.palco.height())
        fundo = _imagem_palco(
            playlist["banner"], playlist["musicas"], largura, altura)
        self.palco.definir_fundo(fundo, animar)
        mafty = temas.cor("raio") == "0px"
        for widget in (self.capa_palco, self.btn_reproduzir_palco):
            if widget.property("mafty") != mafty:
                widget.setProperty("mafty", mafty)
                estilo = widget.style()
                estilo.unpolish(widget)
                estilo.polish(widget)
        if self.palco.property("mafty") != mafty:
            self.palco.setProperty("mafty", mafty)
            estilo = self.palco.style()
            estilo.unpolish(self.palco)
            estilo.polish(self.palco)
        self.palco.update()
        self._atualizar_icone_reproducao()

    def _focar_playlist(self, playlist_id):
        if playlist_id == self._playlist_palco_id:
            return
        self._playlist_palco_id = playlist_id
        self.playlist_id = playlist_id
        self._mais_tocadas_aberta = playlist_id is None
        for chave, botao in self._botoes_playlist.items():
            botao.setProperty("selecionada", chave == playlist_id)
            estilo = botao.style()
            estilo.unpolish(botao)
            estilo.polish(botao)
        self._atualizar_palco(True)

    def _abrir_palco(self):
        playlist = next(
            (item for item in self._playlists_palco
             if item["id"] == self._playlist_palco_id),
            self._playlists_palco[0] if self._playlists_palco else None)
        if playlist is not None:
            self._clicou_playlist(playlist)

    def _reproduzir_palco(self):
        playlist = next(
            (item for item in self._playlists_palco
             if item["id"] == self._playlist_palco_id),
            self._playlists_palco[0] if self._playlists_palco else None)
        if playlist is None or not playlist["musicas"]:
            return
        self.playlist_id = playlist["id"]
        self._mais_tocadas_aberta = bool(playlist.get("inteligente"))
        if self._fila_corresponde(playlist):
            self._player.alternar()
            self._atualizar_icone_reproducao()
            return
        self.tocar.emit(playlist["musicas"], 0)

    def _agendar_tocar_linha(self, item):
        self._temporizador_clique.stop()
        self._musica_clique_pendente = item.data(Qt.UserRole)
        self._temporizador_clique.start()

    def _cancelar_tocar_linha(self):
        self._temporizador_clique.stop()
        self._musica_clique_pendente = None

    def _tocar_linha_selecionada(self):
        musica_id = self._musica_clique_pendente
        self._musica_clique_pendente = None
        if musica_id is None:
            return
        indice = next(
            (i for i, musica in enumerate(self.detalhe.exibidas)
             if musica["id"] == musica_id),
            None)
        if indice is None:
            return
        playlist = next(
            (item for item in self._playlists_palco
             if item["id"] == self._playlist_palco_id),
            None)
        musica_atual = (
            self._player.musica_atual
            if self._player is not None else None)
        if (playlist is not None and musica_atual is not None
                and musica_atual["id"]
                == self.detalhe.exibidas[indice]["id"]
                and self._player.tocando
                and self._fila_corresponde(playlist)):
            return
        self.tocar.emit(self.detalhe.exibidas, indice)

    def _nova(self):
        nome, ok = QInputDialog.getText(self, "Nova playlist", "Nome da playlist:")
        nome = nome.strip()
        if ok and nome:
            db.criar_playlist(nome)
            self._atualizar_lista()

    def _clicou_playlist(self, item):
        if not isinstance(item, dict):
            return
        playlist = item
        if playlist["id"] != self._playlist_palco_id:
            self._focar_playlist(playlist["id"])
        if playlist.get("inteligente"):
            self._abrir_mais_tocadas()
            return
        self._abrir(playlist["id"])

    # ---------- dentro da playlist ----------

    def _musicas_da_playlist(self):
        if self._mais_tocadas_aberta or self._playlist_palco_id is None:
            return db.listar_mais_tocadas()
        if self.playlist_id is None:
            return []
        return db.listar_musicas_da_playlist(self.playlist_id)

    def _reordenar_musicas(self, ids_na_ordem):
        if (self._mais_tocadas_aberta or self._playlist_palco_id is None
                or self.playlist_id is None):
            return
        db.reordenar_playlist(self.playlist_id, ids_na_ordem)
        playlist = db.obter_playlist(self.playlist_id)
        if playlist is not None:
            self.banner.definir(playlist["banner"], self.detalhe.todas)
        self.playlist_reordenada.emit(self.playlist_id)

    def _abrir(self, playlist_id):
        self._mais_tocadas_aberta = False
        self.playlist_id = playlist_id
        self._playlist_palco_id = playlist_id
        self.detalhe.definir_reordenacao_bloqueada(False)
        self.detalhe.definir_texto_vazio("Nenhuma música ainda.")
        self.btn_pincel.setEnabled(True)
        self.detalhe.busca.clear()
        self.pilha.setCurrentIndex(1)
        self._atualizar_detalhe()
        self.detalhe.lista.verticalScrollBar().setValue(0)

    def _abrir_mais_tocadas(self):
        self._mais_tocadas_aberta = True
        self.playlist_id = None
        self._playlist_palco_id = None
        self.detalhe.definir_reordenacao_bloqueada(True)
        self.detalhe.definir_texto_vazio(
            "Toque algumas músicas para ver as mais tocadas aqui.")
        self.btn_pincel.setEnabled(False)
        self.detalhe.busca.clear()
        self.pilha.setCurrentIndex(1)
        self._atualizar_detalhe()
        self.detalhe.lista.verticalScrollBar().setValue(0)

    def _voltar(self):
        self.pilha.setCurrentIndex(0)
        self._atualizar_lista()

    def _atualizar_detalhe(self):
        if self._mais_tocadas_aberta:
            self.detalhe.definir_titulo("Mais tocadas")
            self.detalhe.carregar()
            self.banner.definir(None, self.detalhe.todas[:4])
            return
        if self.playlist_id is None:
            return
        playlist = db.obter_playlist(self.playlist_id)
        if playlist is None:           # foi excluída
            self._voltar()
            return
        self.detalhe.definir_titulo(playlist["nome"])
        self.detalhe.carregar()
        self.banner.definir(playlist["banner"], self.detalhe.todas)
        if self.pilha.currentIndex() == 0:
            self._atualizar_lista()

    # ---------- menu do pincel ----------

    def _abrir_menu(self):
        if self.pilha.currentIndex() == 0:
            self.playlist_id = self._playlist_palco_id
            self._mais_tocadas_aberta = self._playlist_palco_id is None
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
        menu.exec(self.btn_pincel.mapToGlobal(
            QPoint(0, self.btn_pincel.height())))

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