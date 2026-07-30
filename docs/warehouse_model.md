# Modelo warehouse

O schema `warehouse` é a camada final para consumo analítico e Power BI. Ele é
construído a partir do schema `stage`.

## Dimensões

### `warehouse.dim_date`

Calendário para filtros temporais. Chave principal: `date_key`.

### `warehouse.dim_team`

Dimensão de clubes. Chave principal: `team_id`.

### `warehouse.dim_venue`

Dimensão curada de estádios. Chave principal: `venue_key`.

`venue_key` é uma chave interna gerada pelo projeto e usada nos
relacionamentos. `api_venue_id` permanece como atributo opcional de linhagem,
pois a API frequentemente não o informa e, em alguns casos, utiliza IDs
diferentes para o mesmo estádio.

O nome exibido nesta dimensão é o nome canônico. As variações são resolvidas
pelas tabelas `manual.venue_registry` e `manual.venue_name_alias`.

`review_status` informa se o cadastro já foi revisado. No histórico atual,
todos os estádios presentes na dimensão estão como `approved`.

### `warehouse.dim_player`

Dimensão de jogadores. Chave principal: `player_id`.

### `warehouse.dim_season`

Uma linha por edição do Brasileirão. Centraliza período, quantidade de clubes e
partidas e indica se a temporada foi concluída. Chave principal: `season_key`,
o próprio ano.

`is_completed` é a fonte única para controlar a mutabilidade da temporada. O
valor é calculado pelos status das partidas e não deve ser editado manualmente.

### `warehouse.dim_position`

Padroniza posições em `GK`, `DF`, `MF` e `FW`. `Attacker` e `Forward` são
consolidados em `FW` somente no warehouse. Chave principal: `position_key`.

## Ponte

### `warehouse.bridge_team_season`

Relaciona clubes e temporadas e conserva os atributos do clube naquela edição.
Chave principal: `season_key, team_id`.

`venue_key` referencia `dim_venue` e representa o estádio associado ao clube
na temporada. `venue_name` permanece como valor descritivo recebido na origem.

## Fatos

### `warehouse.fact_match`

Uma linha por partida. Grão: `fixture_id`.

`venue_key` referencia o estádio canônico em `dim_venue`. `venue_name` preserva
o texto bruto informado pela API para aquela partida. O Power BI usa
`venue_key` nos relacionamentos, enquanto o nome bruto permite auditoria e
análise de qualidade. O antigo `venue_id` da API não existe mais nesta fato.

### `warehouse.fact_team_match`

Duas linhas por partida: uma para o mandante e outra para o visitante. Grão:
`fixture_id, team_id`.

### `warehouse.fact_player_season`

Uma linha por jogador, clube e temporada. Grão:
`player_id, team_id, season_key`.

## Curadoria de colunas

O stage continua amplo e próximo dos dados transformados. O warehouse omite
atributos constantes ou voláteis que não agregam valor analítico neste projeto:

- país e indicador de seleção dos clubes;
- idade na extração e indicador momentâneo de lesão dos jogadores;
- superfície do estádio;
- liga, país e nome da liga nas partidas;
- descrição longa do status.

`status_short` permanece em `fact_match` para distinguir partidas encerradas,
canceladas, adiadas ou em andamento. `elapsed` representa o minuto transcorrido
informado pela API.

## Construção

Depois de carregar o stage, rode:

```bash
PYTHONPATH=src ./venv/Scripts/python.exe -m football_analytics.load.warehouse
```

O script recria somente o schema `warehouse`. Os schemas `stage`, `manual` e
`etl` são preservados. O cadastro de estádios e seus aliases é atualizado
automaticamente antes da construção das tabelas analíticas.

Consulte `docs/manual_data_corrections.md` para o procedimento de curadoria de
estádios.
