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
}

NEVOA = {
    "fundo": "#5F4DB0", "superficie": "#483C8B", "cartao": "#343A8E",
    "elevado": "#565CC0", "borda": "#6C72D0", "borda_forte": "#9298E6",
    "texto": "#FCF8FB", "texto_suave": "#D1D0EF", "texto_fraco": "#BCC0F3",
    "azul": "#969BE7", "azul_claro": "#D1D0EF", "azul_escuro": "#25296B",
    "lilas": "#EEC1DD", "lilas_claro": "#F8DDEC", "lilas_escuro": "#6B3C86",
    "perigo": "#FF9AA8",
    "fundo_a": "#4C52B5", "fundo_b": "#7A48A6",
    "superficie_a": "#363B91", "superficie_b": "#5A3585",
    "texto_sobre_destaque": "#1B1D4A",
    "textura": "grao", "textura_opacidade": 0.09, "textura_cor": "#FFFFFF",
}

TEMAS = {
    "padrao": ("Padrão", PADRAO),
    "lavanda": ("Lavanda", LAVANDA),
    "nevoa": ("Névoa", NEVOA),
}

_configuracoes = QSettings("Sonata", "Sonata")
_tema_salvo = _configuracoes.value("tema", "padrao", type=str)
_tema_em_uso = (
    _tema_salvo if isinstance(_tema_salvo, str) and _tema_salvo in TEMAS
    else "padrao"
)
_CHAVES_NAO_QSS = {"textura", "textura_opacidade", "textura_cor"}
_TOKENS_QSS = sorted(
    set(PADRAO) - _CHAVES_NAO_QSS, key=len, reverse=True)
_REGEX_TOKENS_QSS = re.compile(
    r"@(" + "|".join(re.escape(chave) for chave in _TOKENS_QSS) + r")(?![a-z_])")


def cor(nome):
    return TEMAS[_tema_em_uso][1][nome]


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
