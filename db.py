import sqlite3
from pathlib import Path

PASTA_DADOS = Path(__file__).parent / "dados"
CAMINHO_BANCO = PASTA_DADOS / "sonata.db"


def conectar():
    conexao = sqlite3.connect(CAMINHO_BANCO)
    conexao.row_factory = sqlite3.Row            # acessa colunas pelo nome
    conexao.execute("PRAGMA foreign_keys = ON")  # liga a exclusão em cascata
    return conexao


def criar_tabelas():
    with conectar() as con:
        con.executescript("""
            CREATE TABLE IF NOT EXISTS musicas (
                id        INTEGER PRIMARY KEY AUTOINCREMENT,
                titulo    TEXT NOT NULL,
                artista   TEXT NOT NULL DEFAULT 'Artista desconhecido',
                album     TEXT,
                caminho   TEXT NOT NULL,
                capa      TEXT,
                duracao   INTEGER NOT NULL DEFAULT 0,
                formato   TEXT,
                favorita  INTEGER NOT NULL DEFAULT 0,
                letra     TEXT NOT NULL DEFAULT '',
                reproducoes INTEGER NOT NULL DEFAULT 0
            );

            CREATE TABLE IF NOT EXISTS playlists (
                id      INTEGER PRIMARY KEY AUTOINCREMENT,
                nome    TEXT NOT NULL,
                banner  TEXT
            );

            CREATE TABLE IF NOT EXISTS playlist_musicas (
                playlist_id INTEGER NOT NULL,
                musica_id   INTEGER NOT NULL,
                posicao     INTEGER NOT NULL,
                PRIMARY KEY (playlist_id, musica_id),
                FOREIGN KEY (playlist_id) REFERENCES playlists(id) ON DELETE CASCADE,
                FOREIGN KEY (musica_id)   REFERENCES musicas(id)   ON DELETE CASCADE
            );
        """)
        colunas = {linha["name"] for linha in con.execute("PRAGMA table_info(musicas)")}
        if "letra" not in colunas:
            con.execute("ALTER TABLE musicas ADD COLUMN letra TEXT NOT NULL DEFAULT ''")
        if "reproducoes" not in colunas:
            con.execute(
                "ALTER TABLE musicas ADD COLUMN reproducoes INTEGER NOT NULL DEFAULT 0")


# ---------- músicas ----------

def adicionar_musica(titulo, artista, caminho, capa=None,
                     album=None, duracao=0, formato=None):
    with conectar() as con:
        cursor = con.execute(
            """INSERT INTO musicas (titulo, artista, caminho, capa, album, duracao, formato)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (titulo, artista, caminho, capa, album, duracao, formato),
        )
        return cursor.lastrowid


def definir_letra(musica_id, texto):
    with conectar() as con:
        con.execute("UPDATE musicas SET letra = ? WHERE id = ?", (texto, musica_id))


def atualizar_musica(musica_id, titulo, artista):
    with conectar() as con:
        con.execute(
            "UPDATE musicas SET titulo = ?, artista = ? WHERE id = ?",
            (titulo, artista, musica_id),
        )


def definir_capa_musica(musica_id, caminho_capa):
    with conectar() as con:
        con.execute(
            "UPDATE musicas SET capa = ? WHERE id = ?", (caminho_capa, musica_id)
        )


def listar_musicas():
    with conectar() as con:
        return con.execute("SELECT * FROM musicas ORDER BY id").fetchall()


def listar_favoritas():
    with conectar() as con:
        return con.execute(
            "SELECT * FROM musicas WHERE favorita = 1 ORDER BY id"
        ).fetchall()


def alternar_favorita(musica_id):
    with conectar() as con:
        con.execute(
            "UPDATE musicas SET favorita = 1 - favorita WHERE id = ?", (musica_id,)
        )


def excluir_musica(musica_id):
    with conectar() as con:
        con.execute("DELETE FROM musicas WHERE id = ?", (musica_id,))

def obter_musica(musica_id):
    with conectar() as con:
        return con.execute(
            "SELECT * FROM musicas WHERE id = ?", (musica_id,)
        ).fetchone()


def registrar_reproducao(musica_id):
    with conectar() as con:
        con.execute(
            "UPDATE musicas SET reproducoes = reproducoes + 1 WHERE id = ?",
            (musica_id,),
        )


def listar_mais_tocadas(limite=50):
    with conectar() as con:
        return con.execute(
            """SELECT * FROM musicas
               WHERE reproducoes > 0
               ORDER BY reproducoes DESC, titulo COLLATE NOCASE, titulo
               LIMIT ?""",
            (limite,),
        ).fetchall()


# ---------- playlists ----------

def criar_playlist(nome):
    with conectar() as con:
        cursor = con.execute("INSERT INTO playlists (nome) VALUES (?)", (nome,))
        return cursor.lastrowid


def listar_playlists():
    with conectar() as con:
        return con.execute("SELECT * FROM playlists ORDER BY id").fetchall()


def adicionar_na_playlist(playlist_id, musica_id):
    with conectar() as con:
        con.execute(
            """INSERT OR IGNORE INTO playlist_musicas (playlist_id, musica_id, posicao)
               VALUES (?, ?, (SELECT COALESCE(MAX(posicao), 0) + 1
                              FROM playlist_musicas WHERE playlist_id = ?))""",
            (playlist_id, musica_id, playlist_id),
        )


def listar_musicas_da_playlist(playlist_id):
    with conectar() as con:
        return con.execute(
            """SELECT m.* FROM musicas m
               JOIN playlist_musicas pm ON pm.musica_id = m.id
               WHERE pm.playlist_id = ?
               ORDER BY pm.posicao""",
            (playlist_id,),
        ).fetchall()


def reordenar_playlist(playlist_id, ids_na_ordem):
    with conectar() as con:
        con.executemany(
            """UPDATE playlist_musicas SET posicao = ?
               WHERE playlist_id = ? AND musica_id = ?""",
            ((posicao, playlist_id, musica_id)
             for posicao, musica_id in enumerate(ids_na_ordem)),
        )


def obter_playlist(playlist_id):
    with conectar() as con:
        return con.execute(
            "SELECT * FROM playlists WHERE id = ?", (playlist_id,)
        ).fetchone()


def renomear_playlist(playlist_id, nome):
    with conectar() as con:
        con.execute("UPDATE playlists SET nome = ? WHERE id = ?", (nome, playlist_id))


def definir_banner_playlist(playlist_id, banner):
    with conectar() as con:
        con.execute("UPDATE playlists SET banner = ? WHERE id = ?", (banner, playlist_id))


def excluir_playlist(playlist_id):
    with conectar() as con:
        con.execute("DELETE FROM playlists WHERE id = ?", (playlist_id,))


def resumo_playlists():
    """Cada playlist com o total de músicas e a duração somada (em segundos)."""
    with conectar() as con:
        return con.execute(
            """SELECT p.id, p.nome, p.banner,
                      COUNT(m.id) AS total,
                      COALESCE(SUM(m.duracao), 0) AS duracao
               FROM playlists p
               LEFT JOIN playlist_musicas pm ON pm.playlist_id = p.id
               LEFT JOIN musicas m ON m.id = pm.musica_id
               GROUP BY p.id
               ORDER BY p.id"""
        ).fetchall()