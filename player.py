import random
from pathlib import Path

from PySide6.QtCore import QObject, QUrl, Signal
from PySide6.QtMultimedia import QAudioOutput, QMediaPlayer

RAIZ = Path(__file__).parent


class Player(QObject):
    musica_mudou = Signal(object)   # emite a música atual
    posicao_mudou = Signal(int)     # em milissegundos
    duracao_mudou = Signal(int)     # em milissegundos
    estado_mudou = Signal(bool)     # True = tocando, False = pausado
    fila_mudou = Signal()

    def __init__(self):
        super().__init__()
        self._saida = QAudioOutput()
        self._saida.setVolume(0.5)
        self._midia = QMediaPlayer()
        self._midia.setAudioOutput(self._saida)

        self._fila = []       # músicas, na ordem original
        self._ordem = []      # índices da fila, na ordem em que vão tocar
        self._pos = -1        # posição atual dentro de _ordem
        self.shuffle = False
        self.repetir = "off"  # "off", "fila" ou "uma"

        self._midia.positionChanged.connect(lambda p: self.posicao_mudou.emit(int(p)))
        self._midia.durationChanged.connect(lambda d: self.duracao_mudou.emit(int(d)))
        self._midia.playbackStateChanged.connect(self._ao_mudar_estado)
        self._midia.mediaStatusChanged.connect(self._ao_mudar_status)

    # ---------- consulta ----------

    @property
    def musica_atual(self):
        if 0 <= self._pos < len(self._ordem):
            return self._fila[self._ordem[self._pos]]
        return None

    @property
    def tocando(self):
        return self._midia.playbackState() == QMediaPlayer.PlaybackState.PlayingState

    # ---------- começar a tocar ----------

    def tocar_lista(self, musicas, indice=0):
        """Define a fila e começa a tocar a partir da música de posição 'indice'."""
        self._fila = list(musicas)
        if not self._fila:
            return
        self._montar_ordem(indice)
        self._carregar_e_tocar()

    def _montar_ordem(self, atual):
        ordem = list(range(len(self._fila)))
        if self.shuffle:
            ordem.remove(atual)
            random.shuffle(ordem)
            ordem.insert(0, atual)   # a música atual sempre fica na frente
            self._pos = 0
        else:
            self._pos = atual
        self._ordem = ordem

    def _carregar_e_tocar(self):
        musica = self.musica_atual
        caminho = (RAIZ / musica["caminho"]).resolve()
        self._midia.setSource(QUrl.fromLocalFile(str(caminho)))
        self._midia.play()
        self.musica_mudou.emit(musica)
        self.fila_mudou.emit()

    # ---------- controles ----------

    def alternar(self):
        """Play/pause."""
        if self.tocando:
            self._midia.pause()
        elif self.musica_atual:
            self._midia.play()

    def proxima(self, automatica=False):
        if not self._ordem:
            return
        if self._pos + 1 < len(self._ordem):
            self._pos += 1
        elif self.repetir == "fila":
            self._pos = 0
        elif automatica:
            self._midia.stop()   # acabou a fila
            return
        else:
            return
        self._carregar_e_tocar()

    def anterior(self):
        if not self._ordem:
            return
        # passou de 3 segundos (ou é a primeira): volta ao início da música
        if self._midia.position() > 3000 or self._pos == 0:
            self._midia.setPosition(0)
            return
        self._pos -= 1
        self._carregar_e_tocar()

    def buscar(self, milissegundos):
        self._midia.setPosition(milissegundos)

    def definir_volume(self, volume):
        """Volume de 0 a 100."""
        self._saida.setVolume(volume / 100)

    def definir_shuffle(self, ligado):
        self.shuffle = ligado
        if self._ordem and self._pos >= 0:
            self._montar_ordem(self._ordem[self._pos])
        self.fila_mudou.emit()

    def ciclar_repeticao(self):
        """off -> fila -> uma -> off. Devolve o novo modo."""
        proximo = {"off": "fila", "fila": "uma", "uma": "off"}
        self.repetir = proximo[self.repetir]
        return self.repetir
    def remover_da_fila(self, musica_id):
        """Tira da fila uma música que foi excluída. Se era a que estava
        tocando, passa para a próxima; se não houver próxima, para."""
        if all(m["id"] != musica_id for m in self._fila):
            return
        atual = self.musica_atual
        era_a_atual = atual is not None and atual["id"] == musica_id

        novo_indice = {}
        nova_fila = []
        for i, m in enumerate(self._fila):
            if m["id"] != musica_id:
                novo_indice[i] = len(nova_fila)
                nova_fila.append(m)

        antes = sum(1 for i in self._ordem[:max(self._pos, 0)] if i in novo_indice)
        self._ordem = [novo_indice[i] for i in self._ordem if i in novo_indice]
        self._fila = nova_fila
        self._pos = antes

        if era_a_atual:
            if self._pos < len(self._ordem):
                self._carregar_e_tocar()
            else:
                self._midia.stop()
                self._midia.setSource(QUrl())   # solta o arquivo, para poder apagá-lo
                self._fila, self._ordem, self._pos = [], [], -1
                self.musica_mudou.emit(None)
        self.fila_mudou.emit()
        
    # ---------- eventos internos ----------

    def _ao_mudar_estado(self, estado):
        self.estado_mudou.emit(estado == QMediaPlayer.PlaybackState.PlayingState)

    def _ao_mudar_status(self, status):
        if status == QMediaPlayer.MediaStatus.EndOfMedia:
            if self.repetir == "uma":
                self._midia.setPosition(0)
                self._midia.play()
            else:
                self.proxima(automatica=True)