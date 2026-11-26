import sys
import db
import library

db.criar_tabelas()

if len(sys.argv) < 2:
    print('Use: python teste_library.py "caminho do arquivo"')
    sys.exit()

musica_id = library.adicionar_arquivo(sys.argv[1])
m = db.obter_musica(musica_id)

print("Título :", m["titulo"])
print("Artista:", m["artista"])
print("Duração:", m["duracao"], "segundos")
print("Formato:", m["formato"])
print("Arquivo:", m["caminho"])
print("Capa   :", m["capa"])