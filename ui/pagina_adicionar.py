from pathlib import Path

from PySide6.QtCore import QSize, Qt, QThread, Signal
from PySide6.QtGui import QColor, QIcon, QPainter, QPixmap
from PySide6.QtWidgets import (QAbstractButton, QButtonGroup, QComboBox,
                               QFileDialog, QFrame, QHBoxLayout, QLabel,
                               QLineEdit, QPushButton, QScrollArea,
                               QVBoxLayout, QWidget)

import db
import library
from ui import temas, util

EXTENSOES = {".mp3", ".wav", ".flac", ".m4a", ".aac", ".ogg", ".opus", ".wma", ".mp4"}
FILTRO_AUDIO = "Áudio (" + " ".join(f"*{e}" for e in sorted(EXTENSOES)) + ")"


def _recortar(pm, lado):
    pm = pm.scaled(lado, lado, Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation)
    return pm.copy((pm.width() - lado) // 2, (pm.height() - lado) // 2, lado, lado)


class Interruptor(QAbstractButton):
    """Chave liga/desliga desenhada à mão."""

    def __init__(self, ligado=True):
        super().__init__()
        self.setCheckable(True)
        self.setChecked(ligado)
        self.setFixedSize(46, 26)
        self.setCursor(Qt.PointingHandCursor)

    def paintEvent(self, evento):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        p.setPen(Qt.NoPen)
        p.setBrush(QColor(util.AZUL if self.isChecked() else temas.cor("borda_forte")))
        p.drawRoundedRect(self.rect(), 13, 13)
        p.setBrush(QColor(temas.cor("texto_sobre_destaque") if self.isChecked()
                          else temas.cor("texto_suave")))
        x = self.width() - 22 if self.isChecked() else 4
        p.drawEllipse(x, 4, 18, 18)
        p.end()


class ZonaArraste(QFrame):
    """Área onde se soltam arquivos (ou se clica para escolhê-los)."""
    arquivos = Signal(list)

    def __init__(self):
        super().__init__()
        self.setObjectName("zonaArraste")
        self.setAcceptDrops(True)
        self.setFixedHeight(170)

        icone = QLabel("↑")
        icone.setObjectName("uploadIcone")
        icone.setAlignment(Qt.AlignCenter)
        texto = QLabel("Arraste arquivos para cá ou")
        texto.setObjectName("infoPagina")
        texto.setAlignment(Qt.AlignCenter)
        botao = QPushButton("Escolher arquivos")
        botao.setObjectName("secundario")
        botao.clicked.connect(lambda: self._escolher())

        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignCenter)
        layout.setSpacing(10)
        layout.addWidget(icone)
        layout.addWidget(texto)
        layout.addWidget(botao, 0, Qt.AlignHCenter)

    def _escolher(self):
        caminhos, _ = QFileDialog.getOpenFileNames(
            self, "Escolher músicas", "", FILTRO_AUDIO)
        if caminhos:
            self.arquivos.emit(caminhos)

    def _realcar(self, ligado):
        self.setProperty("arrastando", ligado)
        self.style().unpolish(self)
        self.style().polish(self)

    def dragEnterEvent(self, evento):
        if evento.mimeData().hasUrls():
            evento.acceptProposedAction()
            self._realcar(True)

    def dragLeaveEvent(self, evento):
        self._realcar(False)

    def dropEvent(self, evento):
        self._realcar(False)
        caminhos = [u.toLocalFile() for u in evento.mimeData().urls() if u.isLocalFile()]
        if caminhos:
            self.arquivos.emit(caminhos)
            evento.acceptProposedAction()


class ItemArquivo(QFrame):
    """Uma linha da lista: capa, título, artista e dados do arquivo."""
    remover = Signal(object)

    def __init__(self, caminho):
        super().__init__()
        self.setObjectName("itemArquivo")
        self.caminho = Path(caminho)
        self.capa_escolhida = None
        self._capa_original = None
        self._erro = None
        tags = library.ler_tags(self.caminho)

        # capa (clique para escolher outra)
        self.btn_capa = QPushButton("+ capa")
        self.btn_capa.setObjectName("capaEscolher")
        self.btn_capa.setFixedSize(72, 72)
        self.btn_capa.setIconSize(QSize(72, 72))
        self.btn_capa.setToolTip("Escolher capa")
        self.btn_capa.clicked.connect(lambda: self._escolher_capa())
        embutida = library.extrair_capa(self.caminho)
        if embutida:
            pm = QPixmap()
            if pm.loadFromData(embutida[0]):
                self._mostrar_capa(pm)

        # título e artista
        self.campo_titulo = QLineEdit(tags["titulo"] or self.caminho.stem)
        self.campo_titulo.setObjectName("campoItem")
        self.campo_artista = QLineEdit(tags["artista"] or "")
        self.campo_artista.setObjectName("campoArtista")
        self.campo_artista.setPlaceholderText("Artista desconhecido")

        tamanho = self.caminho.stat().st_size / (1024 * 1024)
        self.lbl_info = QLabel(f"{self.caminho.name} · {tamanho:.1f}".replace(".", ",") + " MB")
        self.lbl_info.setObjectName("infoItem")

        self.selo = QLabel("")
        self.selo.setObjectName("selo")
        btn_remover = QPushButton("✕")
        btn_remover.setObjectName("botaoIcone")
        btn_remover.setToolTip("Tirar da lista")
        btn_remover.clicked.connect(lambda: self.remover.emit(self))

        textos = QVBoxLayout()
        textos.setSpacing(2)
        textos.addWidget(self.campo_titulo)
        textos.addWidget(self.campo_artista)
        textos.addWidget(self.lbl_info)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(16)
        layout.addWidget(self.btn_capa)
        layout.addLayout(textos, 1)
        layout.addWidget(self.selo, 0, Qt.AlignVCenter)
        layout.addWidget(btn_remover, 0, Qt.AlignVCenter)

    def _mostrar_capa(self, pm):
        self._capa_original = QPixmap(pm)
        self.btn_capa.setIcon(QIcon(util.arredondar_capa(_recortar(pm, 72))))
        self.btn_capa.setText("")

    def _escolher_capa(self):
        caminho, _ = QFileDialog.getOpenFileName(
            self, "Escolher capa", "", "Imagens (*.jpg *.jpeg *.png *.webp)")
        if caminho:
            pm = QPixmap(caminho)
            if not pm.isNull():
                self.capa_escolhida = caminho
                self._mostrar_capa(pm)

    def atualizar_selo(self, converter):
        formato = self.caminho.suffix.lstrip(".").upper()
        if converter and formato != "MP3":
            self.selo.setText(f"{formato} → MP3")
        else:
            self.selo.setText(formato)

    def mostrar_erro(self, texto):
        self._erro = texto
        self.lbl_info.setText("Falhou: " + texto)
        self.lbl_info.setStyleSheet(f"color: {temas.cor('perigo')};")

    def atualizar_tema(self):
        if self._capa_original is not None:
            self._mostrar_capa(self._capa_original)
        if self._erro is not None:
            self.lbl_info.setStyleSheet(f"color: {temas.cor('perigo')};")

    def dados(self):
        return {
            "caminho": str(self.caminho),
            "titulo": self.campo_titulo.text().strip() or None,
            "artista": self.campo_artista.text().strip() or None,
            "capa": self.capa_escolhida,
        }


class Importador(QThread):
    """Adiciona os arquivos em segundo plano, para a janela não travar
    enquanto o ffmpeg converte."""
    resultado = Signal(int, str)   # posição na lista, erro ('' = deu certo)

    def __init__(self, itens, converter, kbps, playlist_id):
        super().__init__()
        self.itens = itens
        self.converter = converter
        self.kbps = kbps
        self.playlist_id = playlist_id

    def run(self):
        for i, d in enumerate(self.itens):
            try:
                library.adicionar_arquivo(
                    d["caminho"], titulo=d["titulo"], artista=d["artista"],
                    capa=d["capa"], converter=self.converter, kbps=self.kbps,
                    playlist_id=self.playlist_id)
                self.resultado.emit(i, "")
            except Exception as erro:
                linhas = str(erro).strip().splitlines()
                self.resultado.emit(i, linhas[-1][:120] if linhas else type(erro).__name__)


class PaginaAdicionar(QWidget):
    adicionadas = Signal()   # avisa a janela que entraram músicas novas

    def __init__(self):
        super().__init__()
        self.itens = []
        self._lote = []
        self.importador = None
        self._ok = 0
        self._falhas = 0
        self._processados = 0
        self._dados_lote = []
        self._erros_lote = []

        # --- cabeçalho ---
        titulo = QLabel("Adicionar música")
        titulo.setObjectName("tituloPagina")
        subtitulo = QLabel("Escolha arquivos de áudio do seu computador.")
        subtitulo.setObjectName("infoPagina")
        cabecalho = QVBoxLayout()
        cabecalho.setSpacing(2)
        cabecalho.addWidget(titulo)
        cabecalho.addWidget(subtitulo)

        # --- zona de arrastar ---
        self.zona = ZonaArraste()
        self.zona.arquivos.connect(self.adicionar_arquivos)

        # --- cartão de conversão ---
        card = QFrame()
        card.setObjectName("card")
        t_card = QLabel("Converter para MP3 automaticamente")
        t_card.setObjectName("cardTitulo")
        d_card = QLabel("WAV, FLAC, M4A e outros formatos viram MP3 ao adicionar.")
        d_card.setObjectName("cardDesc")
        textos_card = QVBoxLayout()
        textos_card.setSpacing(2)
        textos_card.addWidget(t_card)
        textos_card.addWidget(d_card)

        self.interruptor = Interruptor(True)
        self.interruptor.toggled.connect(self._ao_trocar_conversao)
        topo_card = QHBoxLayout()
        topo_card.addLayout(textos_card, 1)
        topo_card.addWidget(self.interruptor, 0, Qt.AlignTop)

        divisor = QFrame()
        divisor.setObjectName("divisor")
        divisor.setFixedHeight(1)

        self.faixa_qualidade = QWidget()
        linha_q = QHBoxLayout(self.faixa_qualidade)
        linha_q.setContentsMargins(0, 0, 0, 0)
        linha_q.setSpacing(8)
        rotulo_q = QLabel("Qualidade")
        rotulo_q.setObjectName("cardDesc")
        linha_q.addWidget(rotulo_q)
        self.grupo_q = QButtonGroup(self)
        for kbps in (128, 192, 320):
            botao = QPushButton(f"{kbps} kbps")
            botao.setObjectName("qualidade")
            botao.setCheckable(True)
            self.grupo_q.addButton(botao, kbps)   # id do botão - próprio kbps
            linha_q.addWidget(botao)
        self.grupo_q.button(320).setChecked(True)
        linha_q.addStretch()

        col_card = QVBoxLayout(card)
        col_card.setContentsMargins(20, 18, 20, 18)
        col_card.setSpacing(14)
        col_card.addLayout(topo_card)
        col_card.addWidget(divisor)
        col_card.addWidget(self.faixa_qualidade)

        # --- lista de arquivos escolhidos ---
        self.coluna_itens = QVBoxLayout()
        self.coluna_itens.setSpacing(10)

        # --- junto se a janela for pequena ---
        conteudo = QWidget()
        coluna = QVBoxLayout(conteudo)
        coluna.setContentsMargins(40, 30, 40, 10)
        coluna.setSpacing(16)
        coluna.addLayout(cabecalho)
        coluna.addWidget(self.zona)
        coluna.addWidget(card)
        coluna.addLayout(self.coluna_itens)
        coluna.addStretch()

        area = QScrollArea()
        area.setObjectName("areaLista")
        area.setWidgetResizable(True)
        area.setFrameShape(QFrame.NoFrame)
        area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        area.setWidget(conteudo)

        # --- rodapé fixo: playlist e botão ---
        icone_pl = QLabel("☰")
        icone_pl.setObjectName("infoPagina")
        self.combo = QComboBox()
        self.lbl_status = QLabel("")
        self.lbl_status.setObjectName("status")
        self.btn_adicionar = QPushButton("Adicionar à biblioteca")
        self.btn_adicionar.setObjectName("primario")
        self.btn_adicionar.setEnabled(False)
        self.btn_adicionar.clicked.connect(lambda: self._importar())

        rodape = QHBoxLayout()
        rodape.setContentsMargins(40, 12, 40, 20)
        rodape.setSpacing(10)
        rodape.addWidget(icone_pl)
        rodape.addWidget(self.combo)
        rodape.addSpacing(12)
        rodape.addWidget(self.lbl_status, 1)
        rodape.addWidget(self.btn_adicionar)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(area, 1)
        layout.addLayout(rodape)

    # ---------- playlists ----------

    def showEvent(self, evento):
        self.atualizar_playlists()
        super().showEvent(evento)

    def atualizar_playlists(self):
        atual = self.combo.currentData()
        self.combo.clear()
        self.combo.addItem("Sem playlist", None)
        for p in db.listar_playlists():
            self.combo.addItem(p["nome"], p["id"])
        posicao = self.combo.findData(atual)
        if posicao >= 0:
            self.combo.setCurrentIndex(posicao)

    # ---------- lista de arquivos ----------

    def adicionar_arquivos(self, caminhos):
        if self.importador:
            return
        existentes = {i.caminho for i in self.itens}
        novos = []
        for c in caminhos:
            p = Path(c)
            if p.is_dir():   # pasta: pega todas as musga dentro dela
                achados = [f for f in sorted(p.rglob("*"))
                           if f.is_file() and f.suffix.lower() in EXTENSOES]
            elif p.suffix.lower() in EXTENSOES:
                achados = [p]
            else:
                achados = []
            for f in achados:
                if f in existentes:
                    continue
                existentes.add(f)
                novos.append(f)
        if len(novos) > 1:
            dados = [
                {"caminho": str(f), "titulo": f.stem, "artista": "", "capa": None}
                for f in novos
            ]
            self._iniciar_importacao(dados)
            return
        for f in novos:
            item = ItemArquivo(f)
            item.atualizar_selo(self.interruptor.isChecked())
            item.remover.connect(self._remover_item)
            self.itens.append(item)
            self.coluna_itens.addWidget(item)
        self.lbl_status.setText("")
        self._atualizar_botao()

    def _remover_item(self, item):
        if self.importador:
            return
        self._tirar(item)

    def _tirar(self, item):
        if item in self.itens:
            self.itens.remove(item)
        self.coluna_itens.removeWidget(item)
        item.deleteLater()
        self._atualizar_botao()

    def _atualizar_botao(self):
        n = len(self.itens)
        self.btn_adicionar.setText(f"Adicionar {n} à biblioteca" if n else "Adicionar à biblioteca")
        self.btn_adicionar.setEnabled(n > 0 and self.importador is None)

    def _ao_trocar_conversao(self, ligado):
        self.faixa_qualidade.setEnabled(ligado)
        for item in self.itens:
            item.atualizar_selo(ligado)

    def atualizar_tema(self):
        for item in self.itens:
            item.atualizar_tema()
        self.update()

    # ---------- importar ----------

    def _importar(self):
        if not self.itens or self.importador:
            return
        self._iniciar_importacao(
            [i.dados() for i in self.itens], list(self.itens))

    def _iniciar_importacao(self, dados, itens_lote=None):
        self._lote = list(itens_lote or [])
        self._dados_lote = dados
        self._erros_lote = []
        self._ok = self._falhas = self._processados = 0
        self.importador = Importador(
            dados,
            self.interruptor.isChecked(),
            self.grupo_q.checkedId(),
            self.combo.currentData(),
        )
        self.importador.resultado.connect(self._ao_resultado)
        self.importador.finished.connect(self._ao_terminar)
        self.btn_adicionar.setEnabled(False)
        self.lbl_status.setText(f"Adicionando 0 de {len(self._lote)}…")
        self.importador.start()

    def _ao_resultado(self, posicao, erro):
        self._processados += 1
        if self._lote:
            item = self._lote[posicao]
            if erro:
                self._falhas += 1
                item.mostrar_erro(erro)       # fica na lista, com o motivo
            else:
                self._ok += 1
                self._tirar(item)             # deu certo: sai da lista
        elif erro:
            self._falhas += 1
            nome = Path(self._dados_lote[posicao]["caminho"]).name
            self._erros_lote.append(f"{nome}: {erro}")
        else:
            self._ok += 1
        self.lbl_status.setText(
            f"Adicionando {self._processados} de {len(self._dados_lote)}…")

    def _ao_terminar(self):
        self.importador.wait()
        self.importador = None
        self._lote = []
        self._dados_lote = []
        if self._ok:
            self.adicionadas.emit()
        partes = []
        if self._ok:
            partes.append(f"{self._ok} {'música adicionada' if self._ok == 1 else 'músicas adicionadas'}")
        if self._falhas:
            partes.append(f"{self._falhas} {'falhou' if self._falhas == 1 else 'falharam'}")
        resumo = ", ".join(partes) + "."
        if self._erros_lote:
            resumo += " " + " | ".join(self._erros_lote)
        self.lbl_status.setText(resumo)
        self._erros_lote = []
        self._atualizar_botao()