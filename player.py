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
        self._posicao_pendente = None
        self.shuffle = False
        self.repetir = "off"  # "off", "fila" ou "uma"

        self._midia.positionChanged.connect(self._ao_mudar_posicao)
        self._midia.durationChanged.connect(lambda d: self.duracao_mudou.emit(int(d)))
        self._midia.playbackStateChanged.connect(self._ao_mudar_estado)
        self._midia.mediaStatusChanged.connect(self._ao_mudar_status)

    # ---------- consulta ----------

    @property
    def musica_atual(self):
        if 0 <= self._pos < len(self._ordem):
            indice = self._ordem[self._pos]
            if 0 <= indice < len(self._fila):
                return self._fila[indice]
        return None

    @property
    def fila(self):
        return [
            self._fila[indice] for indice in self._ordem
            if 0 <= indice < len(self._fila)
        ]

    @property
    def indice_fila_atual(self):
        if (0 <= self._pos < len(self._ordem)
                and 0 <= self._ordem[self._pos] < len(self._fila)):
            return self._pos
        return -1

    @property
    def tocando(self):
        return self._midia.playbackState() == QMediaPlayer.PlaybackState.PlayingState

    @property
    def posicao_ms(self):
        if self._posicao_pendente is not None:
            return self._posicao_pendente
        return int(self._midia.position())

    def adicionar_na_fila(self, musica):
        if not self._fila or not self._ordem:
            self._fila = [musica]
            self._ordem = [0]
            self._pos = -1
        else:
            self._fila.append(musica)
            self._ordem.append(len(self._fila) - 1)
        self.fila_mudou.emit()

    def reordenar_fila_playlist(self, musicas):
        ids_playlist = {musica["id"] for musica in musicas}
        atual = self.musica_atual
        if atual is None or atual["id"] not in ids_playlist:
            return False

        fila_atual = self.fila
        quantidades = {}
        for musica in fila_atual:
            musica_id = musica["id"]
            if musica_id in ids_playlist:
                quantidades[musica_id] = quantidades.get(musica_id, 0) + 1

        nova_fila = []
        for musica in musicas:
            musica_id = musica["id"]
            if quantidades.get(musica_id, 0):
                nova_fila.append(musica)
                quantidades[musica_id] -= 1
        for musica in fila_atual:
            musica_id = musica["id"]
            if (musica_id not in ids_playlist
                    or quantidades.get(musica_id, 0) > 0):
                nova_fila.append(musica)
                if musica_id in ids_playlist:
                    quantidades[musica_id] -= 1

        indice_atual = next(
            (i for i, musica in enumerate(nova_fila)
             if musica["id"] == atual["id"]), -1)
        if indice_atual < 0:
            return False

        self._fila = nova_fila
        self._ordem = list(range(len(nova_fila)))
        self._pos = indice_atual
        self.fila_mudou.emit()
        return True

    # ---------- começar a tocar ----------

    def tocar_lista(self, musicas, indice=0):
        """Define a fila e começa a tocar a partir da música de posição 'indice'."""
        self._posicao_pendente = None
        self._fila = list(musicas)
        if not self._fila:
            self._ordem = []
            self._pos = -1
            self.fila_mudou.emit()
            return
        self._montar_ordem(indice)
        self._carregar_e_tocar()

    def carregar_lista_pausada(self, musicas, indice, posicao_ms):
        self._posicao_pendente = None
        self._fila = list(musicas)
        if not self._fila or not 0 <= indice < len(self._fila):
            self._ordem = []
            self._pos = -1
            self.fila_mudou.emit()
            return False

        self._montar_ordem(indice)
        musica = self.musica_atual
        caminho = (RAIZ / musica["caminho"]).resolve()
        self._midia.stop()
        self._midia.setSource(QUrl.fromLocalFile(str(caminho)))
        self._posicao_pendente = max(0, int(posicao_ms))
        self.musica_mudou.emit(musica)
        self.fila_mudou.emit()
        if self._midia.mediaStatus() in (
                QMediaPlayer.MediaStatus.LoadedMedia,
                QMediaPlayer.MediaStatus.BufferedMedia):
            self._aplicar_posicao_pendente()
        return True

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
        self._posicao_pendente = None
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
        elif self.repetir == "fila" or automatica:
            self._pos = 0
        else:
            return
        self._carregar_e_tocar()

    def anterior(self):
        if not self._ordem or self._pos < 0:
            return
        # passou de 3 segundos (ou é a primeira): volta ao início da música
        if self.posicao_ms > 3000 or self._pos == 0:
            self._posicao_pendente = None
            self._midia.setPosition(0)
            return
        self._pos -= 1
        self._carregar_e_tocar()

    def buscar(self, milissegundos):
        self._posicao_pendente = None
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
        sem_atual = self._pos < 0
        self._ordem = [novo_indice[i] for i in self._ordem if i in novo_indice]
        self._fila = nova_fila
        self._pos = -1 if sem_atual else antes

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

    def _aplicar_posicao_pendente(self):
        if self._posicao_pendente is None:
            return
        posicao = self._posicao_pendente
        self._midia.setPosition(posicao)
        if int(self._midia.position()) == posicao:
            self._posicao_pendente = None

    def _ao_mudar_posicao(self, posicao):
        posicao = int(posicao)
        if self._posicao_pendente == posicao:
            self._posicao_pendente = None
        self.posicao_mudou.emit(posicao)

    def _ao_mudar_estado(self, estado):
        self.estado_mudou.emit(estado == QMediaPlayer.PlaybackState.PlayingState)

    def _ao_mudar_status(self, status):
        if status in (
                QMediaPlayer.MediaStatus.LoadedMedia,
                QMediaPlayer.MediaStatus.BufferedMedia):
            self._aplicar_posicao_pendente()
        if status == QMediaPlayer.MediaStatus.EndOfMedia:
            if self.repetir == "uma":
                self._midia.setPosition(0)
                self._midia.play()
            else:
                self.proxima(automatica=True)