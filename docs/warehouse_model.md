# Modelo warehouse

O warehouse é a camada final para consumo analítico e Power BI.

Ele é construído a partir do schema `stage`.

# Dimensões

warehouse.dim_date

Calendário para filtros temporais.

Chave principal:

date_key

warehouse.dim_team

Dimensão de clubes.

Chave principal:

team_id

warehouse.dim_venue

Dimensão de estádios.

Chave principal:

venue_id

warehouse.dim_player

Dimensão de jogadores.

Chave principal:

player_id

warehouse.dim_season

Uma linha por edição do Brasileirão. Centraliza o período da competição,
quantidade de clubes e partidas e indica se a temporada foi concluída.

`is_completed` é a fonte única para controlar a mutabilidade da temporada. O
valor é calculado pelos status das partidas e não deve ser editado manualmente.

Chave principal:

season_key (o próprio ano da temporada)

warehouse.dim_position

Padroniza as posições em `GK`, `DF`, `MF` e `FW`. Os valores de origem
`Attacker` e `Forward` são consolidados em `FW` somente no warehouse.

Chave principal:

position_key

# Ponte

warehouse.bridge_team_season

Relaciona clubes e temporadas. Ajuda a responder quais times participaram de
cada edição do Brasileirão.

Chave principal:

season_key, team_id

# Fatos

warehouse.fact_match

Uma linha por partida.

Grão:

fixture_id

warehouse.fact_team_match

Duas linhas por partida: uma para o mandante e uma para o visitante.

Grão:

fixture_id, team_id

warehouse.fact_player_season

Uma linha por jogador, time, liga e temporada.

Grão:

player_id, team_id, season_key

# Curadoria de colunas

O stage continua amplo e fiel aos dados transformados. O warehouse omite
atributos constantes ou voláteis que não agregam valor analítico neste projeto:

- país e indicador de seleção dos clubes;
- idade na extração e indicador momentâneo de lesão dos jogadores;
- superfície do estádio;
- liga, país e nome da liga nas partidas;
- descrição longa do status.

`status_short` permanece em `fact_match` para distinguir partidas encerradas,
canceladas, adiadas ou em andamento. `elapsed` representa o minuto transcorrido
informado pela API.

# Comando

Depois de carregar o stage, rode:

PYTHONPATH=src ./venv/Scripts/python.exe -m football_analytics.load.warehouse

O script recria somente o schema `warehouse`. Ele não apaga o schema `stage`.

# Dados preenchidos manualmente

Alguns atributos que não são fornecidos, estão incompletos ou apresentam
duplicidade na API podem ser corrigidos manualmente, como endereço e capacidade
de estádios.

As correções conhecidas e o procedimento adotado são registrados em
`docs/manual_data_corrections.md`.

As correções persistentes ficam em `manual.venue_corrections`. O schema `manual`
não é removido durante a construção, e suas informações são aplicadas
automaticamente em `dim_venue`, `bridge_team_season` e `fact_match`.

Não devem ser feitas novas edições diretamente em `warehouse.dim_venue`, pois
o schema `warehouse` continua sendo recriado a cada carga.
