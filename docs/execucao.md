# Guia direto de execução

Os comandos abaixo foram escritos para o Git Bash, executados na raiz do
projeto com o ambiente virtual configurado.

# 1. Reconstruir 2010–2025 usando os JSONs existentes

Use quando os arquivos raw já estiverem salvos e quiser recriar CSVs, stage e
warehouse.

Este procedimento não acessa a API.

```bash
PYTHONPATH=src ./venv/Scripts/python.exe -m football_analytics.transform.all

PYTHONPATH=src ./venv/Scripts/python.exe -m football_analytics.load.stage

PYTHONPATH=src ./venv/Scripts/python.exe -m football_analytics.load.warehouse
```

Resultado:

- recria os CSVs em `data/stage`;
- substitui todo o schema `stage`;
- reconstrói todo o schema `warehouse`;
- reaplica `manual.venue_corrections`;
- preserva os schemas `manual` e `etl`.

# 2. Buscar 2010–2025 na API e fazer a carga completa

Use somente se os JSONs ainda não existirem ou se estiver completando uma
extração histórica interrompida.

O primeiro comando acessa a API. Arquivos históricos existentes são
reutilizados.

```bash
PYTHONPATH=src ./venv/Scripts/python.exe \
  -m football_analytics.extract.historical \
  --start-season 2010 \
  --end-season 2025
```

Depois da extração:

```bash
PYTHONPATH=src ./venv/Scripts/python.exe -m football_analytics.transform.all
PYTHONPATH=src ./venv/Scripts/python.exe -m football_analytics.load.stage
PYTHONPATH=src ./venv/Scripts/python.exe -m football_analytics.load.warehouse
```

# 3. Importar uma temporada em andamento pela primeira vez

Exemplo: importar 2026 enquanto o campeonato ainda está acontecendo.

## 3.1 Ativar a temporada

Este comando não acessa a API.

```bash
PYTHONPATH=src ./venv/Scripts/python.exe \
  -m football_analytics.load.etl_control activate --season 2026
```

## 3.2 Criar o primeiro snapshot completo

Este comando acessa a API. O primeiro snapshot deve incluir jogadores.

```bash
PYTHONPATH=src ./venv/Scripts/python.exe \
  -m football_analytics.extract.season_snapshot --season 2026
```

## 3.3 Atualizar somente essa temporada no banco

Este comando não acessa a API.

```bash
PYTHONPATH=src ./venv/Scripts/python.exe \
  -m football_analytics.pipeline.refresh_season --season 2026
```

Resultado:

- temporadas anteriores permanecem intactas;
- somente 2026 é substituída no stage e no warehouse;
- 2026 permanece com status `active`.

# 4. Atualizar uma temporada que continua em andamento

## Atualização completa, incluindo jogadores

O primeiro comando acessa a API. O segundo não.

```bash
PYTHONPATH=src ./venv/Scripts/python.exe \
  -m football_analytics.extract.season_snapshot --season 2026

PYTHONPATH=src ./venv/Scripts/python.exe \
  -m football_analytics.pipeline.refresh_season --season 2026
```

## Atualização sem buscar novamente os jogadores

Use apenas quando já existir um snapshot anterior completo com jogadores.
O extrator buscará times e partidas e o transform reutilizará o conjunto mais
recente disponível de jogadores.

```bash
PYTHONPATH=src ./venv/Scripts/python.exe \
  -m football_analytics.extract.season_snapshot \
  --season 2026 \
  --skip-players

PYTHONPATH=src ./venv/Scripts/python.exe \
  -m football_analytics.pipeline.refresh_season --season 2026
```

# 5. Importar uma temporada já encerrada que nunca foi carregada

Exemplo: no início de 2027, importar todos os dados finais de 2026.

## 5.1 Ativar temporariamente

```bash
PYTHONPATH=src ./venv/Scripts/python.exe \
  -m football_analytics.load.etl_control activate --season 2026
```

## 5.2 Criar o snapshot final completo

Este comando acessa a API.

```bash
PYTHONPATH=src ./venv/Scripts/python.exe \
  -m football_analytics.extract.season_snapshot --season 2026
```

## 5.3 Carregar e encerrar

Não é necessário executar `refresh_season` antes. O fechamento já faz a carga
de stage e warehouse.

```bash
PYTHONPATH=src ./venv/Scripts/python.exe \
  -m football_analytics.pipeline.close_season --season 2026
```

O comando verifica se ainda existem partidas não finalizadas. Se existirem, a
temporada não será marcada como `closed`.

# 6. Encerrar uma temporada que estava sendo atualizada

Primeiro, crie o último snapshot completo:

```bash
PYTHONPATH=src ./venv/Scripts/python.exe \
  -m football_analytics.extract.season_snapshot --season 2026
```

Depois, faça a carga final e encerre:

```bash
PYTHONPATH=src ./venv/Scripts/python.exe \
  -m football_analytics.pipeline.close_season --season 2026
```

# 7. Reprocessar uma temporada encerrada sem acessar a API

Use somente para uma correção histórica intencional quando o raw correto já
estiver salvo.

```bash
PYTHONPATH=src ./venv/Scripts/python.exe \
  -m football_analytics.pipeline.refresh_season \
  --season 2025 \
  --force
```

`--force` ignora a proteção `closed`, mas não acessa a API.

# 8. Consultar o status das temporadas

```bash
PYTHONPATH=src ./venv/Scripts/python.exe \
  -m football_analytics.load.etl_control list
```

# Resumo rápido

| Situação | Sequência |
|---|---|
| Recriar todo o banco usando raw existente | `transform.all` → `load.stage` → `load.warehouse` |
| Buscar e carregar 2010–2025 | `extract.historical` → reconstrução completa |
| Primeira carga de temporada ativa | `activate` → `season_snapshot` → `refresh_season` |
| Atualizar temporada ativa | `season_snapshot` → `refresh_season` |
| Importar temporada já encerrada | `activate` → `season_snapshot` → `close_season` |
| Encerrar temporada ativa | snapshot final → `close_season` |
| Corrigir temporada fechada usando raw existente | `refresh_season --force` |

# Regra para identificar acesso à API

Somente os módulos dentro de `football_analytics.extract` acessam a API:

- `extract.historical`;
- `extract.season_snapshot`;
- extratores individuais de times, partidas e jogadores.

Comandos de `transform`, `load` e `pipeline` utilizam dados locais e o
PostgreSQL. Eles não consomem requisições da API.
