# Guia direto de execução

Os comandos foram escritos para o Git Bash, executados na raiz do projeto com
o ambiente virtual configurado.

# 1. Reconstruir 2010–2025 usando os JSONs existentes

Este procedimento não acessa a API.

```bash
PYTHONPATH=src ./venv/Scripts/python.exe -m football_analytics.transform.all
PYTHONPATH=src ./venv/Scripts/python.exe -m football_analytics.load.stage
PYTHONPATH=src ./venv/Scripts/python.exe -m football_analytics.load.warehouse
```

Ele recria os CSVs, substitui o stage, reconstrói o warehouse e reaplica
`manual.venue_corrections`.

# 2. Buscar 2010–2025 na API e fazer a carga completa

O primeiro comando acessa a API. Arquivos históricos existentes são
reutilizados.

```bash
PYTHONPATH=src ./venv/Scripts/python.exe \
  -m football_analytics.extract.historical \
  --start-season 2010 \
  --end-season 2025
```

Depois:

```bash
PYTHONPATH=src ./venv/Scripts/python.exe -m football_analytics.transform.all
PYTHONPATH=src ./venv/Scripts/python.exe -m football_analytics.load.stage
PYTHONPATH=src ./venv/Scripts/python.exe -m football_analytics.load.warehouse
```

# 3. Importar uma temporada em andamento pela primeira vez

Exemplo: importar 2026 enquanto o campeonato ainda está acontecendo.

Não existe etapa de ativação. Como 2026 ainda não existe em `dim_season`, a
primeira importação é permitida automaticamente.

## 3.1 Criar o primeiro snapshot completo

Este comando acessa a API. O primeiro snapshot deve incluir jogadores.

```bash
PYTHONPATH=src ./venv/Scripts/python.exe \
  -m football_analytics.extract.season_snapshot --season 2026
```

## 3.2 Atualizar somente 2026 no banco

Este comando não acessa a API.

```bash
PYTHONPATH=src ./venv/Scripts/python.exe \
  -m football_analytics.pipeline.refresh_season --season 2026
```

Se houver partidas não finalizadas, `warehouse.dim_season.is_completed` ficará
como `false`, permitindo novas atualizações.

# 4. Atualizar uma temporada incompleta

Enquanto `dim_season.is_completed = false`, use:

```bash
PYTHONPATH=src ./venv/Scripts/python.exe \
  -m football_analytics.extract.season_snapshot --season 2026

PYTHONPATH=src ./venv/Scripts/python.exe \
  -m football_analytics.pipeline.refresh_season --season 2026
```

O primeiro comando acessa a API. O segundo atualiza somente 2026 no stage e no
warehouse.

## Atualizar sem buscar novamente os jogadores

Use apenas quando já existir um snapshot anterior completo com jogadores.

```bash
PYTHONPATH=src ./venv/Scripts/python.exe \
  -m football_analytics.extract.season_snapshot \
  --season 2026 \
  --skip-players

PYTHONPATH=src ./venv/Scripts/python.exe \
  -m football_analytics.pipeline.refresh_season --season 2026
```

# 5. Importar uma temporada já encerrada que nunca foi carregada

Exemplo: no início de 2027, importar os dados finais de 2026.

Como a temporada ainda não existe em `dim_season`, não é necessário ativá-la.

## 5.1 Criar o snapshot final

Este comando acessa a API.

```bash
PYTHONPATH=src ./venv/Scripts/python.exe \
  -m football_analytics.extract.season_snapshot --season 2026
```

## 5.2 Carregar e validar o encerramento

```bash
PYTHONPATH=src ./venv/Scripts/python.exe \
  -m football_analytics.pipeline.close_season --season 2026
```

O comando atualiza stage e warehouse, verifica os status das partidas e
confirma que `dim_season.is_completed = true`. Se houver partidas pendentes, o
campo permanecerá `false` e o encerramento informará o problema.

# 6. Encerrar uma temporada que vinha sendo atualizada

Crie o último snapshot completo e execute o fechamento:

```bash
PYTHONPATH=src ./venv/Scripts/python.exe \
  -m football_analytics.extract.season_snapshot --season 2026

PYTHONPATH=src ./venv/Scripts/python.exe \
  -m football_analytics.pipeline.close_season --season 2026
```

`is_completed` não é preenchido manualmente. Ele é recalculado a partir dos
status das partidas.

# 7. Reprocessar uma temporada concluída

Uma carga normal é bloqueada quando `dim_season.is_completed = true`. Para uma
correção histórica intencional usando o raw existente:

```bash
PYTHONPATH=src ./venv/Scripts/python.exe \
  -m football_analytics.pipeline.refresh_season \
  --season 2025 \
  --force
```

Esse comando não acessa a API.

Se também for necessário consultar novamente a API para uma temporada já
concluída, o snapshot exige a mesma intenção explícita:

```bash
PYTHONPATH=src ./venv/Scripts/python.exe \
  -m football_analytics.extract.season_snapshot \
  --season 2025 \
  --force
```

# 8. Consultar o estado das temporadas

Execute no PostgreSQL:

```sql
SELECT
    season_key,
    season_name,
    start_date,
    end_date,
    number_of_matches,
    is_completed
FROM warehouse.dim_season
ORDER BY season_key;
```

# Resumo rápido

| Situação | Sequência |
|---|---|
| Recriar todo o banco usando raw existente | `transform.all` → `load.stage` → `load.warehouse` |
| Buscar e carregar 2010–2025 | `extract.historical` → reconstrução completa |
| Primeira carga de temporada incompleta | `season_snapshot` → `refresh_season` |
| Atualizar temporada incompleta | `season_snapshot` → `refresh_season` |
| Importar temporada já encerrada | `season_snapshot` → `close_season` |
| Encerrar temporada em andamento | snapshot final → `close_season` |
| Corrigir temporada concluída | `refresh_season --force` |

# Quais comandos acessam a API

Somente os módulos dentro de `football_analytics.extract` acessam a API, como
`extract.historical` e `extract.season_snapshot`.

Comandos de `transform`, `load` e `pipeline` utilizam dados locais e o
PostgreSQL. Eles não consomem requisições da API.
