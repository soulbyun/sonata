import ctypes
import sys
from pathlib import Path

from PySide6.QtGui import QFont, QFontDatabase, QIcon
from PySide6.QtWidgets import QApplication

import db
from ui import temas
from ui.janela_principal import JanelaPrincipal


def main():
    if sys.platform == "win32":
        try:
            definir_id_aplicativo = (
                ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID)
            definir_id_aplicativo.argtypes = [ctypes.c_wchar_p]
            definir_id_aplicativo.restype = ctypes.c_long
            definir_id_aplicativo("Sonata.Player")
        except (AttributeError, OSError, TypeError, ValueError,
                ctypes.ArgumentError):
            pass

    db.criar_tabelas()
    app = QApplication(sys.argv)
    raiz = Path(__file__).parent
    icone = raiz / "assets" / "icone.ico"
    if icone.is_file():
        app.setWindowIcon(QIcon(str(icone)))

    fontes = raiz / "assets" / "fontes"
    for arquivo in sorted(fontes.glob("*.ttf")):
        QFontDatabase.addApplicationFont(str(arquivo))
    app.setFont(QFont("Manrope", 9))

    qss = raiz / "ui" / "estilo.qss"
    temas.aplicar_estilo(app, qss)
    janela = JanelaPrincipal()
    janela.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()