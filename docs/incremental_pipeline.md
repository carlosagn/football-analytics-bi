# Pipeline incremental por temporada

O pipeline incremental atualiza apenas a temporada escolhida. A reconstrução
completa continua disponível para recuperação e mudanças estruturais.

Para os comandos organizados por situação, consulte `docs/execucao.md`.

# Controle pelo estado dos dados

Não existe uma tabela operacional para ativar ou encerrar temporadas. A fonte
única dessa informação é `warehouse.dim_season.is_completed`.

| Estado em `dim_season` | Comportamento |
|---|---|
| temporada ainda não existe | primeira extração e carga permitidas |
| `is_completed = false` | snapshots e atualizações permitidos |
| `is_completed = true` | carga normal bloqueada; correção exige `--force` |

Adicionar um ano em `SUPPORTED_SEASONS` não cria dados no banco e não acessa
a API.

# Como is_completed é calculado

O campo é derivado dos status das partidas no stage. Uma temporada é
considerada concluída quando todas as partidas possuem um dos status finais
aceitos:

- `FT`;
- `AET`;
- `PEN`;
- `CANC`.

Se existir uma partida agendada, em andamento, adiada ou com outro status não
final, `is_completed` será `false`.

# Controle das execuções

O schema `etl` permanece apenas para auditoria. `etl.load_runs` registra as
cargas de stage e warehouse com temporada, início, fim, status, contagens e
eventual mensagem de erro.

# Raw por snapshot

Temporadas históricas continuam usando os arquivos existentes. Novas extrações
utilizam snapshots imutáveis:

```text
data/raw/snapshots/2026/snapshot_20260713T080000Z/
    teams.json
    fixtures.json
    players/
        team_131/
            page_001.json
    _SUCCESS.json
```

`_SUCCESS.json` é criado somente no fim de uma extração completa. Diretórios
incompletos são ignorados. O transform escolhe o snapshot completo mais recente
e, quando necessário, o último snapshot que contenha jogadores.

# Primeira importação de uma temporada

Não é necessário cadastrar ou ativar a temporada. Se ela ainda não existir em
`dim_season`, o snapshot é permitido:

```bash
PYTHONPATH=src ./venv/Scripts/python.exe \
  -m football_analytics.extract.season_snapshot --season 2026

PYTHONPATH=src ./venv/Scripts/python.exe \
  -m football_analytics.pipeline.refresh_season --season 2026
```

O primeiro comando acessa a API. O segundo utiliza o raw local.

# Atualização incremental

Enquanto `is_completed = false`, o orquestrador:

1. lê o raw mais recente da temporada;
2. transforma somente a temporada solicitada;
3. valida chaves, conteúdo e temporada;
4. atualiza somente essa fatia no stage;
5. atualiza dimensões e somente essa fatia no warehouse;
6. recalcula `dim_season`, incluindo `is_completed`;
7. atualiza o cadastro persistente de estádios e aplica os aliases de nomes;
8. registra o resultado em `etl.load_runs`.

Stage e warehouse usam transações. Uma falha reverte a etapa afetada.

# Estratégia no stage

| Tabela | Estratégia |
|---|---|
| `dates` | substitui as chaves presentes na nova fatia |
| `teams` | substitui os clubes presentes na nova fatia |
| `venues` | substitui os estádios presentes na nova fatia |
| `players` | substitui os jogadores presentes na nova fatia |
| `team_seasons` | substitui somente a temporada |
| `fixtures` | substitui somente a temporada |
| `fixture_team_results` | substitui somente a temporada |
| `player_season_stats` | substitui somente a temporada |

Os dados são carregados primeiro em um schema temporário com os mesmos tipos
do stage. A substituição ocorre somente depois das validações.

# Estratégia no warehouse

Dimensões recebem inserções ou atualizações pelas respectivas chaves. Apenas
a temporada solicitada é substituída em:

- `bridge_team_season`;
- `fact_match`;
- `fact_team_match`;
- `fact_player_season`;
- registro correspondente em `dim_season`.

O cadastro `manual.venue_registry` também recebe nomes novos encontrados na
temporada. `manual.venue_name_alias` resolve esses nomes para a `venue_key`
utilizada em `dim_venue`, `bridge_team_season` e `fact_match`.

Um nome ainda não existente nos arquivos de `reference` é carregado como
`pending`, sem perda de partidas. A execução exibe um aviso e o caso fica
disponível em `manual.venue_alias_review` até que a decisão seja versionada.

# Encerramento

`close_season` executa a carga final e confirma que não existem partidas com
status pendente:

```bash
PYTHONPATH=src ./venv/Scripts/python.exe \
  -m football_analytics.pipeline.close_season --season 2026
```

O comando não marca o campo manualmente. `is_completed` é recalculado pelos
dados das partidas. Se permanecer `false`, o encerramento falha e informa os
status pendentes.

# Correção histórica

Uma temporada com `is_completed = true` fica protegida. Para reprocessar
intencionalmente o raw de uma temporada concluída:

```bash
PYTHONPATH=src ./venv/Scripts/python.exe \
  -m football_analytics.pipeline.refresh_season \
  --season 2025 \
  --force
```

# Reconstrução completa

```bash
PYTHONPATH=src ./venv/Scripts/python.exe -m football_analytics.transform.all
PYTHONPATH=src ./venv/Scripts/python.exe -m football_analytics.load.stage
PYTHONPATH=src ./venv/Scripts/python.exe -m football_analytics.load.warehouse
```

Esse caminho recalcula `dim_season.is_completed` para todas as temporadas.

# Correções históricas versionadas

Durante a transformação de 2010 ou 2013, as correções em
`reference/fixture_round_corrections.csv` e
`reference/missing_fixtures_review.csv` são reaplicadas automaticamente. A
carga incremental e a reconstrução completa produzem, portanto, o mesmo
resultado sem modificar os JSONs raw.

# CSVs

Os CSVs permanecem na reconstrução completa e na inspeção manual. A carga
incremental transforma os JSONs diretamente em DataFrames e atualiza o banco.
