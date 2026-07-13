# Modelo stage inicial

Este modelo parte dos arquivos raw de `teams`, `fixtures` e `players`.
A ideia é transformar JSON em tabelas utilizáveis no PostgreSQL, sem ainda
fechar o desenho final do warehouse.

Na reconstrução completa, o transform também materializa CSVs em
`data/stage`. Na rotina incremental, os DataFrames são carregados diretamente
no schema `stage`, substituindo somente a temporada solicitada. Os CSVs não são
a fonte oficial da rotina incremental. Consulte `docs/incremental_pipeline.md`.

# Tabelas de stage

stage.teams

Uma linha por time. Guarda nome, código, país, ano de fundação e logo.

stage.venues

Uma linha por estádio. Guarda nome, cidade, capacidade, superfície e imagem.

stage.players

Uma linha por jogador. Guarda dados biográficos, nacionalidade, altura, peso,
data/local de nascimento, status de lesão e foto.

stage.dates

Calendário derivado das datas das partidas. Útil para filtros por ano, mês,
trimestre, dia da semana e fim de semana.

stage.team_seasons

Uma linha por time em cada temporada. Serve para responder quais clubes
participaram de cada edição e qual estádio estava associado ao time naquele ano.

stage.fixtures

Uma linha por partida. Guarda rodada, data, árbitro, estádio, mandante,
visitante, placar, gols por tempo, vencedor, empate, pontos, total de gols,
ambos marcam e faixas over 1.5 / 2.5 / 3.5.

stage.fixture_team_results

Duas linhas por partida: uma para o mandante e outra para o visitante. Essa
tabela facilita análises por clube, como pontos, vitórias, derrotas, saldo,
clean sheets, jogos sem marcar, desempenho como mandante e visitante.

stage.player_season_stats

Uma linha por jogador, time e temporada. Guarda estatísticas agregadas do
jogador no campeonato, incluindo jogos, minutos, gols, assistências, passes,
desarmes, duelos, dribles, faltas, cartões e pênaltis. Também inclui métricas
derivadas como gols por 90, assistências por 90, participações em gols por 90,
aproveitamento de finalizações no alvo, duelos ganhos e dribles certos.

# Próximo passo: warehouse

O warehouse será construído a partir do stage. Nele, os nomes devem ficar mais
definitivos para BI, por exemplo:

warehouse.dim_team
warehouse.dim_player
warehouse.dim_venue
warehouse.dim_date
warehouse.fact_match
warehouse.fact_team_match
warehouse.fact_player_season
