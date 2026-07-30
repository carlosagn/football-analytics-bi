# Dados de referência

Esta pasta contém regras de negócio pequenas e versionadas, necessárias para
reproduzir a camada analítica.

## `venues.csv`

Cadastro de atributos canônicos ou complementados manualmente. Campos vazios
não apagam valores já disponíveis na origem.

## `venue_aliases.csv`

Mapeia cada variação conhecida para o nome canônico do estádio.

- `review_status`: `approved` para decisões revisadas;
- `match_reason`: motivo do agrupamento, como `city_suffix`, `former_name`,
  `nickname` ou `sponsored_name`.

Quando uma temporada trouxer um nome novo, a carga o registra como `pending`.
Após a revisão, a decisão deve ser adicionada a este arquivo.

## `missing_fixtures_review.csv`

Inventário das partidas que não foram retornadas pela API. Somente linhas com
`review_status = confirmed` entram no transform. Os IDs negativos evitam
colisão com os identificadores da API.

## `fixture_round_corrections.csv`

Correções confirmadas para partidas que vieram da API com a rodada incorreta.
O valor esperado também é registrado para que uma mudança inesperada na origem
interrompa a transformação em vez de aplicar uma correção silenciosa.

As regras completas e as validações estão em `docs/missing_fixtures.md`.

## `missing_fixtures_enrichment.csv`

Complementa as partidas ausentes confirmadas com horário UTC, nome do estádio
e placar do intervalo. A associação é feita pelo `manual_fixture_id`.

`venue_key` não é armazenada nesse arquivo porque é uma chave interna do banco.
Ela é derivada do `venue_name` por meio de `venue_aliases.csv`, preservando a
portabilidade para outra instalação do PostgreSQL.
