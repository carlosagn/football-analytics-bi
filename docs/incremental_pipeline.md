# Pipeline incremental por temporada

O pipeline incremental atualiza apenas a temporada escolhida. A reconstrução
completa continua disponível para recuperação e mudanças estruturais no modelo.

Para uma lista direta de comandos organizada por situação, consulte
`docs/execucao.md`.

# Estado inicial

As temporadas de 2010 a 2025 são cadastradas automaticamente em
`etl.season_control` com status `closed`. A temporada 2026 não é cadastrada nem
consultada automaticamente.

Adicionar um ano em `SUPPORTED_SEASONS` significa somente que a extração
histórica conhece esse ano. Isso não ativa uma temporada para atualizações.

# Controle operacional

## etl.season_control

Controla se uma temporada pode ser modificada:

- `active`: aceita snapshots e cargas incrementais;
- `closed`: protegida contra alterações acidentais.

Registra ainda ativação, encerramento e a última carga bem-sucedida.

## etl.load_runs

Registra separadamente as cargas de stage e warehouse, incluindo início, fim,
status, contagens e eventual mensagem de erro.

# Raw por snapshot

Temporadas encerradas continuam usando os arquivos históricos existentes. Uma
temporada ativa utiliza snapshots imutáveis:

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
incompletos são ignorados, e o transform escolhe o snapshot completo mais
recente. O manifesto registra temporada, horário, requisições e quantidades.

Se jogadores forem omitidos de um snapshot, o transform continua usando o
último conjunto completo de jogadores disponível.

# Primeira ativação

Quando houver autorização para iniciar 2026:

```bash
PYTHONPATH=src ./venv/Scripts/python.exe \
  -m football_analytics.load.etl_control activate --season 2026
```

Depois, crie o primeiro snapshot:

```bash
PYTHONPATH=src ./venv/Scripts/python.exe \
  -m football_analytics.extract.season_snapshot --season 2026
```

O segundo comando acessa a API. Nenhuma chamada é feita durante as cargas do
banco descritas abaixo.

# Atualização incremental

Com um snapshot completo disponível:

```bash
PYTHONPATH=src ./venv/Scripts/python.exe \
  -m football_analytics.pipeline.refresh_season --season 2026
```

O orquestrador:

1. lê o raw mais recente da temporada;
2. transforma somente a temporada solicitada;
3. valida chaves, conteúdo e temporada;
4. atualiza somente essa fatia no stage;
5. atualiza dimensões e somente essa fatia no warehouse;
6. aplica `manual.venue_corrections`;
7. registra os resultados em `etl.load_runs`.

Stage e warehouse usam transações. Uma falha reverte a etapa afetada e preserva
o estado anterior dessa camada.

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

As tabelas dependentes são removidas antes de `fact_match`, respeitando as
chaves estrangeiras.

# Encerramento

Ao final da competição, crie um snapshot final e execute:

```bash
PYTHONPATH=src ./venv/Scripts/python.exe \
  -m football_analytics.pipeline.close_season --season 2026
```

O comando faz a carga final, verifica se restam partidas com status não final e
marca a temporada como `closed`. Depois disso, novas cargas são bloqueadas.

# Correção histórica intencional

Uma temporada encerrada somente pode ser reprocessada explicitamente:

```bash
PYTHONPATH=src ./venv/Scripts/python.exe \
  -m football_analytics.pipeline.refresh_season --season 2025 --force
```

`--force` não deve ser usado na rotina normal.

# Reconstrução completa

O caminho anterior permanece disponível:

```bash
PYTHONPATH=src ./venv/Scripts/python.exe -m football_analytics.transform.all
PYTHONPATH=src ./venv/Scripts/python.exe -m football_analytics.load.stage
PYTHONPATH=src ./venv/Scripts/python.exe -m football_analytics.load.warehouse
```

Ele deve ser usado para mudanças estruturais, novas regras para todo o histórico
ou recuperação. A rotina de uma temporada ativa deve usar o incremental.

# CSVs

Os CSVs permanecem na reconstrução completa e na inspeção manual. A carga
incremental transforma os JSONs diretamente em DataFrames e atualiza o banco,
sem sobrescrever os CSVs históricos.

# Validações realizadas

O fluxo foi exercitado com 2025, sem chamadas à API e com `--force`:

- 380 partidas;
- 760 resultados por equipe;
- 915 estatísticas jogador-temporada;
- totais históricos preservados em 6.030, 12.060 e 15.128 linhas;
- correções manuais de estádios preservadas;
- reconstrução completa validada depois do teste incremental.
