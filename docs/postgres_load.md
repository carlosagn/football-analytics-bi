# Carga no PostgreSQL local

O banco local deve se chamar `brasileirao`.

# Arquitetura

O fluxo do projeto agora fica assim:

raw -> stage -> warehouse

raw

JSON original da API, preservado sem alteração.

stage

Tabelas limpas e achatadas, ainda próximas da origem. É a camada que recebe o
resultado do transform atual.

warehouse

Modelo final para BI. Essa camada será construída depois a partir do stage, com
nomes, chaves, métricas e regras de negócio finais.

# Configuração

No arquivo `.env`, adicione as variáveis do PostgreSQL:

DB_HOST=localhost
DB_PORT=5432
DB_NAME=brasileirao
DB_USER=postgres
DB_PASSWORD=sua_senha_aqui

Não compartilhe esse arquivo. Ele já está no `.gitignore`.

# Gerar stage

Antes de carregar no banco, gere os CSVs de stage:

PYTHONPATH=src ./venv/Scripts/python.exe -m football_analytics.transform.all

Os arquivos serão criados em:

data/stage

# Carregar stage no banco

PYTHONPATH=src ./venv/Scripts/python.exe -m football_analytics.load.postgres

Por padrão, as tabelas são carregadas no schema `stage`.

O script usa `replace`, então ele recria as tabelas a partir dos CSVs de stage.
Isso é útil durante o desenvolvimento.

# Tabelas carregadas no stage

stage.dates
stage.teams
stage.venues
stage.players
stage.team_seasons
stage.fixtures
stage.fixture_team_results
stage.player_season_stats

# Construir warehouse

Depois de carregar o stage, construa o schema final de BI:

PYTHONPATH=src ./venv/Scripts/python.exe -m football_analytics.load.warehouse

O script recria somente o schema `warehouse`. O schema `stage` permanece como
fonte intermediária.

# Schema antigo analytics

Se você já carregou dados no schema `analytics`, pode manter por enquanto.
Ele não atrapalha.

Quando tiver certeza de que o schema `stage` está correto, você pode excluir o
schema antigo manualmente no PostgreSQL:

DROP SCHEMA analytics CASCADE;

Use esse comando somente depois de conferir que não precisa mais das tabelas
antigas.
