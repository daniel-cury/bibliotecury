/*
  bibliotecury — seus livros
  ─────────────────────────────────────────────────────────────
  Para adicionar um livro, copie um bloco { ... } e edite.
  A ordem aqui é a ordem na prateleira.

  Campos:
    titulo    título do livro
    autor     nome do autor
    ano       ano de publicação
    genero    gênero (vira uma aba no topo da página)
    paginas   número de páginas
    nota      sua nota de 0 a 5
    lido      quando você leu (texto livre: "2025", "março de 2024"…)
    cor       cor da lombada/capa (opcional, ex.: "#1F3FB0")
    capa      URL de uma imagem de capa (opcional; sem ela a capa é gerada)
    resumo    resumo do livro
    opiniao   o que você achou

  Os livros abaixo são EXEMPLOS: troque pelos seus.
*/
window.LIVROS = [
  {
    titulo: "Dom Casmurro",
    autor: "Machado de Assis",
    ano: 1899,
    genero: "Romance",
    paginas: 256,
    nota: 5,
    lido: "2024",
    cor: "#1F3FB0",
    resumo: "Já velho, Bento Santiago tenta \"atar as duas pontas da vida\" e reconta tudo: a infância em Matacavalos, o amor por Capitu, o seminário que não quis, o casamento e a suspeita que envenena o resto da história.",
    opiniao: "Escreva aqui o que você achou deste livro."
  },
  {
    titulo: "A Hora da Estrela",
    autor: "Clarice Lispector",
    ano: 1977,
    genero: "Romance",
    paginas: 88,
    nota: 4,
    lido: "2024",
    cor: "#D9472B",
    resumo: "O narrador Rodrigo S.M. tenta contar a vida de Macabéa, uma datilógrafa nordestina no Rio de Janeiro que mal sabe que existe, e acaba falando tanto de si quanto dela.",
    opiniao: "Escreva aqui o que você achou deste livro."
  },
  {
    titulo: "1984",
    autor: "George Orwell",
    ano: 1949,
    genero: "Ficção científica",
    paginas: 416,
    nota: 5,
    lido: "2023",
    cor: "#141414",
    resumo: "Em Oceania, o Partido vigia tudo e reescreve o passado todos os dias. Winston Smith trabalha falsificando registros, até que começa um diário, e um romance, que são crimes.",
    opiniao: "Escreva aqui o que você achou deste livro."
  },
  {
    titulo: "Cem Anos de Solidão",
    autor: "Gabriel García Márquez",
    ano: 1967,
    genero: "Romance",
    paginas: 448,
    nota: 5,
    lido: "2023",
    cor: "#2F6B4F",
    resumo: "Sete gerações da família Buendía nascem, amam e se repetem em Macondo, uma vila fundada no meio do nada que vive guerras, pestes de insônia e chuvas de quatro anos.",
    opiniao: "Escreva aqui o que você achou deste livro."
  },
  {
    titulo: "Duna",
    autor: "Frank Herbert",
    ano: 1965,
    genero: "Ficção científica",
    paginas: 680,
    nota: 4,
    lido: "2025",
    cor: "#C98A1B",
    resumo: "A Casa Atreides assume o planeta desértico Arrakis, única fonte da especiaria mais valiosa do universo. Traído, o jovem Paul Atreides se refugia entre o povo do deserto.",
    opiniao: "Escreva aqui o que você achou deste livro."
  },
  {
    titulo: "Sapiens",
    autor: "Yuval Noah Harari",
    ano: 2011,
    genero: "Não-ficção",
    paginas: 464,
    nota: 4,
    lido: "2022",
    cor: "#7A2E3A",
    resumo: "Uma história da humanidade em três revoluções (cognitiva, agrícola e científica) e de como ficções compartilhadas, como dinheiro, religiões e nações, permitiram que milhões cooperassem.",
    opiniao: "Escreva aqui o que você achou deste livro."
  },
  {
    titulo: "O Pequeno Príncipe",
    autor: "Antoine de Saint-Exupéry",
    ano: 1943,
    genero: "Fábula",
    paginas: 96,
    nota: 5,
    lido: "2021",
    cor: "#3D6FB6",
    resumo: "Um aviador cai no deserto do Saara e encontra um menino vindo de um asteroide, que conta suas viagens por planetas habitados por adultos muito estranhos.",
    opiniao: "Escreva aqui o que você achou deste livro."
  },
  {
    titulo: "Ensaio sobre a Cegueira",
    autor: "José Saramago",
    ano: 1995,
    genero: "Romance",
    paginas: 312,
    nota: 5,
    lido: "2025",
    cor: "#4A4A46",
    resumo: "Uma epidemia de cegueira branca se espalha por uma cidade sem nome. Os primeiros cegos são trancados num manicômio, e só uma mulher, que finge estar cega, ainda consegue ver.",
    opiniao: "Escreva aqui o que você achou deste livro."
  }
];
