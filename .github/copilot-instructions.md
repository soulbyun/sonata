# Regras

Sonata é um player de músicas offline e local, feito em Python com PySide6 (Qt) e SQLite. 

## Estrutura

- main.py: ponto de partida
- db.py: banco SQLite (NÃO MEXER)
- library.py: adicionar, converter e excluir músicas (NÃO MEXER)
- player.py: tocar, fila, shuffle (NÃO MEXER)
- ui/: telas e widgets (pode alterar, com cuidado)
- ui/estilo.qss: visual (pode alterar)
- dados/: músicas, capas e o banco do usuário (NUNCA tocar)

## Proibido

- Alterar db.py, player.py e library.py.
- Alterar o esquema do banco ou qualquer arquivo dentro de dados/.
- Renomear ou remover qualquer setObjectName usado no estilo.qss. Se precisar de um novo, crie outro e mantenha o antigo.
- Renomear ou remover métodos, atributos e sinais (Signal) que outras telas usam, por exemplo: tocar, tocar_aleatorio, acao_musica, favoritar, adicionadas, carregar, marcar_tocando, mostrar_musica, definir_titulo, definir_texto_vazio, adicionar_ao_titulo, adicionar_a_esquerda, colocar_acima.
- Mudar os parâmetros de funções existentes.
- Instalar bibliotecas novas ou alterar dependências sem pedir antes.
- Apagar arquivos.
- Refatorar, reorganizar ou "limpar" código que não faz parte do pedido.
- Trocar a lista de músicas (QListWidget com LinhaMusica desenhada à mão) por um widget por linha. Ela é feita assim para continuar rápida com milhares de músicas.

## Como trabalhar

- Faça só o que foi pedido, no menor número de arquivos possível.
- Antes de mudar, diga quais arquivos vai alterar.
- Mantenha o estilo do código existente: nomes em português, comentários curtos.
- Cada música é uma linha do banco com as chaves: id, titulo, artista, album, caminho, capa, duracao (segundos), formato, favorita. Caminhos são relativos à raiz do projeto. Não mude isso.
- Ícones e fontes ficam como arquivos dentro do projeto (por exemplo, a pasta assets/), nunca como pacote instalado.
- Se o pedido exigir algo proibido acima, pare e avise em vez de fazer.

## Visual

- Tema Padrão: cantos pouco arredondados (cerca de 3 px), sem gradientes, fundo liso. Deve continuar igual ao de hoje.
- Cada tema define seus próprios fundos. Gradientes e texturas são permitidos, mas somente por meio das chaves do dicionário do tema (fundo_a, fundo_b, superficie_a, superficie_b, textura etc.).
- Temas podem ser claros ou escuros. Não assuma fundo preto nem texto claro: use sempre as chaves de cor do tema.
- Nunca escreva cores ou gradientes soltos fora de ui/temas.py e dos tokens @nome do estilo.qss.
- Não adicionar data de adição nem nome do álbum nas linhas da lista de músicas.