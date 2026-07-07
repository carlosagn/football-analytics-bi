# Teams

Endpoint

GET /teams

Parâmetros

league
season

Persistência raw

Um JSON completo por temporada:

data/raw/teams/{season}.json

Campos úteis para o transform

team.id
team.name
team.logo
venue.id
venue.capacity

Tabela destino provável

DimTeam
DimVenue

# Fixtures

Endpoint

GET /fixtures

Parâmetros

league
season

Persistência raw

Um JSON completo por temporada:

data/raw/fixtures/{season}.json

# Players

Endpoint

GET /players

Parâmetros

league
season
team
page

Persistência raw

Um JSON por equipe e página:

data/raw/players/{season}/team_{team_id}/page_{page}.json

Observações de plano

No plano gratuito, o parâmetro page aceitou no máximo o valor 3 durante os
testes. Com uma chave de plano pago, o extrator não aplica mais esse limite
artificial e continua até o total de páginas informado pela própria API.

Os arquivos já existentes são preservados. Isso permite interromper e retomar
a extração sem sobrescrever o raw.

# Historical raw extraction

Script

python -m football_analytics.extract.historical

Escopo padrão

Brasileirão Série A, temporadas 2010 até 2025.

O script extrai, nessa ordem:

teams
fixtures
players

Opções úteis

--skip-players
Extrai somente equipes e partidas.

--max-new-player-requests-per-season
Limita o número de novas páginas de jogadores por temporada. Exemplo:
com valor 100, cada ano baixa no máximo 100 novas páginas de jogadores.

--max-new-player-requests-per-run
Alias antigo mantido por compatibilidade. Prefira usar
--max-new-player-requests-per-season.

--max-pages-per-team
Limita páginas por equipe apenas para testes controlados.
