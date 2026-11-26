import sys
from pathlib import Path

from PySide6.QtGui import QFont, QFontDatabase
from PySide6.QtWidgets import QApplication

import db
from ui import temas
from ui.janela_principal import JanelaPrincipal


def main():
    db.criar_tabelas()
    app = QApplication(sys.argv)
    raiz = Path(__file__).parent
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