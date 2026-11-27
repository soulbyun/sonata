import ctypes
import sys

from ui import temas


def _luminancia(cor):
    rgb = int(cor.lstrip("#"), 16)
    canais = (
        (rgb >> 16) & 0xFF,
        (rgb >> 8) & 0xFF,
        rgb & 0xFF,
    )
    lineares = []
    for canal in canais:
        valor = canal / 255
        lineares.append(
            valor / 12.92 if valor <= 0.04045
            else ((valor + 0.055) / 1.055) ** 2.4)
    return (0.2126 * lineares[0] +
            0.7152 * lineares[1] +
            0.0722 * lineares[2])


def _colorref(cor):
    rgb = int(cor.lstrip("#"), 16)
    vermelho = (rgb >> 16) & 0xFF
    verde = (rgb >> 8) & 0xFF
    azul = rgb & 0xFF
    return vermelho | (verde << 8) | (azul << 16)


def ajustar_janela(janela):
    if sys.platform != "win32":
        return

    try:
        from ctypes import wintypes

        dwmapi = ctypes.windll.dwmapi
        definir_atributo = dwmapi.DwmSetWindowAttribute
        definir_atributo.argtypes = [
            wintypes.HWND, wintypes.DWORD, wintypes.LPCVOID, wintypes.DWORD]
        definir_atributo.restype = ctypes.c_long
    except (AttributeError, OSError, TypeError, ValueError):
        return

    hwnd = int(janela.winId())
    escuro = _luminancia(temas.cor("superficie")) < 0.5
    valores = (
        (20, ctypes.c_int(1 if escuro else 0)),
        (35, ctypes.c_uint32(_colorref(temas.cor("superficie_a")))),
        (34, ctypes.c_uint32(_colorref(temas.cor("borda")))),
        (36, ctypes.c_uint32(_colorref(temas.cor("texto")))),
    )
    for atributo, valor in valores:
        try:
            definir_atributo(
                hwnd, atributo, ctypes.byref(valor), ctypes.sizeof(valor))
        except (AttributeError, OSError, TypeError, ValueError,
                ctypes.ArgumentError):
            pass
