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

# Ponte

warehouse.bridge_team_season

Relaciona clubes e temporadas. Ajuda a responder quais times participaram de
cada edição do Brasileirão.

Chave principal:

season, team_id

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

player_id, team_id, league_id, season

# Comando

Depois de carregar o stage, rode:

PYTHONPATH=src ./venv/Scripts/python.exe -m football_analytics.load.warehouse

O script recria somente o schema `warehouse`. Ele não apaga o schema `stage`.
