import re
from pathlib import Path

from PySide6.QtCore import QSettings


PADRAO = {
    "fundo": "#111216",
    "superficie": "#0b0c0f",
    "cartao": "#171920",
    "elevado": "#1e2028",
    "borda": "#23252d",
    "borda_forte": "#343742",
    "texto": "#f2f3f7",
    "texto_suave": "#a3a7b3",
    "texto_fraco": "#6b6f7c",
    "azul": "#93b7f1",
    "azul_claro": "#b2cbf6",
    "azul_escuro": "#1b2536",
    "lilas": "#CCAAFE",
    "lilas_claro": "#dcc3ff",
    "lilas_escuro": "#2a2140",
    "perigo": "#e07a7a",
    "fundo_a": "#111216",
    "fundo_b": "#111216",
    "superficie_a": "#0b0c0f",
    "superficie_b": "#0b0c0f",
    "texto_sobre_destaque": "#0e0f11",
    "textura": None,
    "textura_opacidade": 0.0,
    "textura_cor": "#FFFFFF",
    "textura_destaque": None,
}

LAVANDA = {
    "fundo": "#EEE9F8", "superficie": "#E4DDF3", "cartao": "#FBFAFF",
    "elevado": "#F7F4FD", "borda": "#D8D0EC", "borda_forte": "#C2B8E0",
    "texto": "#3B3556", "texto_suave": "#6A6190", "texto_fraco": "#7B71A3",
    "azul": "#6B77BA", "azul_claro": "#4A549A", "azul_escuro": "#DDE0F5",
    "lilas": "#CC7B9E", "lilas_claro": "#B35C85", "lilas_escuro": "#F4DEE7",
    "perigo": "#C25565",
    "fundo_a": "#EEE9F8", "fundo_b": "#EEE9F8",
    "superficie_a": "#E4DDF3", "superficie_b": "#E4DDF3",
    "texto_sobre_destaque": "#FFFFFF",
    "textura": "grao", "textura_opacidade": 0.04, "textura_cor": "#3B3556",
    "textura_destaque": None,
}

MOONRISE = {
    "fundo": "#1B2254", "superficie": "#101540", "cartao": "#1A2352",
    "elevado": "#26306A", "borda": "#2E3A78", "borda_forte": "#4757A0",
    "texto": "#F7F3EA", "texto_suave": "#B8C2E8", "texto_fraco": "#8E9AD0",
    "azul": "#E9C47C", "azul_claro": "#F6DCA0", "azul_escuro": "#22337A",
    "lilas": "#B9A7F2", "lilas_claro": "#D6C9FA", "lilas_escuro": "#3A2F7A",
    "perigo": "#FF9A8A",
    "fundo_a": "#0E1740", "fundo_b": "#2B2A66",
    "superficie_a": "#0A1030", "superficie_b": "#1A1B4A",
    "texto_sobre_destaque": "#0E1740",
    "textura": "estrelas", "textura_opacidade": 0.45,
    "textura_cor": "#FFFFFF", "textura_destaque": "#E9C47C",
}

MAFTY = {
    "fundo": "#12141B", "superficie": "#0A0B10", "cartao": "#12151D",
    "elevado": "#1B202C", "borda": "#262B3A", "borda_forte": "#434B63",
    "texto": "#EEF0F6", "texto_suave": "#A9B0CC", "texto_fraco": "#6F7694",
    "azul": "#4A68FF", "azul_claro": "#8FA2FF", "azul_escuro": "#16205E",
    "lilas": "#F0002E", "lilas_claro": "#F6495E", "lilas_escuro": "#4A1736",
    "perigo": "#F02842",
    "fundo_a": "#0E1016", "fundo_b": "#171A24",
    "superficie_a": "#090A0F", "superficie_b": "#0F1118",
    "texto_sobre_destaque": "#FFFFFF",
    "textura": "hud", "textura_opacidade": 0.5,
    "textura_cor": "#FFFFFF",
    "hud_amarelo": "#F2D400", "hud_vermelho": "#F0002E",
    "hud_azul": "#4A68FF",
    "raio": "0px", "raio_puxador": "0px",
    "hud": True, "acento_hud": "#A8E10C",
    "marca_dagua": "assets/texturas/mafty.jpg",
    "marca_dagua_opacidade": 0.06, "marca_dagua_tamanho": 0.5,
    "raio_capa": 0,
}

TEMAS = {
    "padrao": ("Padrão", PADRAO),
    "lavanda": ("Lavanda", LAVANDA),
    "moonrise": ("Moonrise", MOONRISE),
    "mafty": ("Mafty", MAFTY),
}

_PADROES_OPCIONAIS = {
    "raio": "3px",
    "raio_capa": 6,
    "raio_puxador": "5px",
    "hud": False,
    "acento_hud": "#A8E10C",
    "hud_amarelo": None,
    "hud_vermelho": None,
    "hud_azul": None,
    "marca_dagua": None,
    "marca_dagua_opacidade": 0.0,
    "marca_dagua_tamanho": 0.5,
}

_configuracoes = QSettings("Sonata", "Sonata")
_tema_salvo = _configuracoes.value("tema", "padrao", type=str)
_tema_em_uso = (
    _tema_salvo if isinstance(_tema_salvo, str) and _tema_salvo in TEMAS
    else "padrao"
)
_CHAVES_NAO_QSS = {
    "textura", "textura_opacidade", "textura_cor", "textura_destaque",
    "hud_amarelo", "hud_vermelho", "hud_azul",
    "hud", "marca_dagua", "marca_dagua_opacidade", "marca_dagua_tamanho"}
_TOKENS_QSS = sorted(
    (set(PADRAO) | set(_PADROES_OPCIONAIS)) - _CHAVES_NAO_QSS,
    key=len, reverse=True)
_REGEX_TOKENS_QSS = re.compile(
    r"@(" + "|".join(re.escape(chave) for chave in _TOKENS_QSS) + r")(?![a-z_])")


def cor(nome):
    paleta = TEMAS[_tema_em_uso][1]
    if nome in paleta:
        return paleta[nome]
    if nome in _PADROES_OPCIONAIS:
        return _PADROES_OPCIONAIS[nome]
    raise KeyError(nome)


def salvar_tema(chave):
    global _tema_em_uso
    if not isinstance(chave, str) or chave not in TEMAS:
        raise ValueError(f"Tema desconhecido: {chave}")
    _configuracoes.setValue("tema", chave)
    _tema_em_uso = chave


def tema_atual():
    return _tema_em_uso


def aplicar_estilo(app, caminho_qss):
    estilo = Path(caminho_qss).read_text(encoding="utf-8")
    estilo = _REGEX_TOKENS_QSS.sub(
        lambda match: cor(match.group(1)), estilo)
    app.setStyleSheet(estilo)
