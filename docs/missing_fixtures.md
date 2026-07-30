# Partidas ausentes e correções de rodada

As consultas `/fixtures?league=71&season=2010` e
`/fixtures?league=71&season=2013` retornaram, respectivamente, 370 e 340
partidas. Uma nova extração produziu arquivos idênticos aos JSONs históricos,
confirmando que a ausência estava na resposta da API, e não no processo de
extração do projeto.

O pipeline complementa essas lacunas durante o transform. Os JSONs raw não são
alterados.

## Arquivos versionados

- `reference/missing_fixtures_review.csv`: contém as 50 partidas ausentes,
  sendo 10 de 2010 e 40 de 2013, com data, placar, fonte e estado da revisão;
- `reference/fixture_round_corrections.csv`: contém os 10 registros da API de
  maio de 2010 cuja rodada foi informada incorretamente;
- `reference/missing_fixtures_enrichment.csv`: complementa as 50 partidas com
  horário UTC, estádio e placar do intervalo.

Somente linhas com `review_status = confirmed` são aplicadas. Os IDs das
partidas complementares são negativos para não colidirem com os IDs positivos
da API.

## Particularidade de 2010

A API apresenta dois problemas diferentes:

1. as 10 partidas de 8 e 9 de maio, pertencentes à rodada 1, vieram marcadas
   como rodada 38;
2. as 10 partidas reais da rodada 38, disputadas em dezembro, não vieram na
   resposta.

O transform corrige os registros `191927` a `191936` para a rodada 1 e inclui
as 10 partidas finais como rodada 38.

## Construção das tabelas

As partidas confirmadas são incorporadas em `transform_fixtures`. Por isso, a
mesma regra funciona tanto na reconstrução completa quanto na carga incremental
das temporadas afetadas.

Para cada partida complementar:

- `stage.fixtures` recebe uma linha;
- `stage.fixture_team_results` recebe duas linhas, uma por clube;
- `warehouse.fact_match` recebe uma linha;
- `warehouse.fact_team_match` recebe duas linhas, uma por clube.

Data e horário UTC, placar final, placar do intervalo, estádio, clubes, pontos e
indicadores derivados são preenchidos. Árbitro e identificador do estádio na
API permanecem nulos porque não foram confirmados.

O `venue_key` informado durante a revisão foi usado para validar o estádio, mas
não é persistido no arquivo de enriquecimento. Como se trata de uma chave
interna, o warehouse volta a derivá-la pelo nome canônico e pelos aliases. Isso
mantém a reconstrução reproduzível em outro banco.

`fixture_date_utc` é armazenado no PostgreSQL como `timestamp with time zone`.
Uma consulta feita na sessão `America/Sao_Paulo` exibirá automaticamente o
horário local; para visualizar exatamente o valor UTC, pode-se usar
`fixture_date_utc AT TIME ZONE 'UTC'`.

## Validações

Depois das correções, 2010 e 2013 possuem, cada um:

- 380 partidas;
- 38 rodadas com 10 partidas;
- 20 clubes;
- 19 mandos e 19 jogos como visitante por clube;
- 760 registros em `fixture_team_results`;
- nenhum confronto mandante-visitante duplicado.

Vitórias, empates, derrotas, gols marcados e gols sofridos também foram
reconciliados com as classificações históricas das duas temporadas.

Se futuramente a API passar a retornar uma das partidas ausentes, o transform
prioriza o registro da API e não acrescenta o complemento de mesmo mandante e
visitante.
