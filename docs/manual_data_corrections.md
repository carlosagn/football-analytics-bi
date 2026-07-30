# Curadoria de estádios

O projeto trata nomes ausentes, desatualizados ou inconsistentes sem alterar os
JSONs originais e sem colocar regras de limpeza dentro do Power BI.

## Fontes versionadas

As decisões permanentes ficam em dois arquivos do repositório:

- `reference/venues.csv`: atributos canônicos e complementações manuais;
- `reference/venue_aliases.csv`: nome bruto da API, nome canônico, estado da
  revisão e motivo do agrupamento.

Esses arquivos tornam a curadoria reproduzível em outro PostgreSQL. Novas
correções não devem ser feitas diretamente em `warehouse.dim_venue`.

## Estruturas no PostgreSQL

Durante a carga, os arquivos são aplicados em:

- `manual.venue_registry`: cadastro persistente com uma `venue_key` por estádio;
- `manual.venue_name_alias`: associação dos nomes brutos às chaves canônicas;
- `manual.venue_alias_review`: visão de qualidade com partidas, temporadas,
  cidades, IDs da API e estado da revisão.

`manual.venue_corrections` permanece apenas como compatibilidade com os ajustes
feitos antes da criação dos arquivos de referência.

## Regras

- `stage.venue_id` e `stage.venue_name` preservam os valores da API.
- `warehouse.fact_match.venue_name` preserva o nome bruto da partida.
- Os relacionamentos usam somente `venue_key`.
- `api_venue_id` é uma referência auxiliar e nunca é usado isoladamente para
  decidir que dois nomes representam o mesmo estádio.
- Um alias novo recebe `review_status = pending` e continua disponível no
  warehouse para não causar perda de partidas.
- A carga exibe um aviso enquanto existirem aliases pendentes.

## Revisar nomes novos

```sql
SELECT *
FROM manual.venue_alias_review
WHERE review_status = 'pending'
ORDER BY number_of_matches DESC, venue_name_raw;
```

Depois da análise, registre a decisão em `reference/venue_aliases.csv`. Caso
seja necessário complementar endereço, cidade, capacidade, imagem ou ID de
referência, atualize também `reference/venues.csv`.

Em seguida, reconstrua o warehouse ou reprocesse a temporada afetada. O pipeline
atualizará as chaves das fatos automaticamente.

## Estado atual

A curadoria de 2010 a 2025 consolidou 194 nomes brutos em 79 estádios
canônicos. Todos os aliases atuais estão aprovados, as 6.080 partidas foram
preservadas e as 17 complementações manuais anteriores continuam aplicadas.

As decisões históricas e as validações estão detalhadas em
`docs/venue_curation.md`.
