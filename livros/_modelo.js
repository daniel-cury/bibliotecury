livro(`
titulo: Nome do Livro
autor: Nome do Autor
ano: 2001
genero: Romance
paginas: 300
nota: 4
lido: 2025
cor: #1F3FB0

## Resumo

Seu resumo aqui.

## O que eu achei

Sua opinião aqui. Separe parágrafos com uma linha em branco.

Dá para usar *itálico*, **negrito**, [links](https://exemplo.com),
listas com "- " no começo da linha e citações com "> ":

> Uma frase marcante do livro.
`);

/*
  COMO USAR ESTE MODELO
  - Só a primeira linha "livro(`" e a última "`);" são código: não apague.
  - Em cima ficam os dados, um por linha ("campo: valor"), até a primeira linha em branco.
    titulo, autor, ano, genero (vira aba no topo), paginas, nota (0 a 5, aceita meia estrela: 3.5 ou 3,5), lido (texto livre).
    cor (opcional) é a cor da lombada. capa (opcional) é a URL de uma imagem de capa.
  - Depois da linha em branco vem o seu texto, livre.
  - Não use o caractere ` (crase invertida) dentro do texto.
*/
