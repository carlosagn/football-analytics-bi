# Football Analytics BI
Projeto de Engenharia de Dados e Business Intelligence para análise do
Campeonato Brasileiro Série A.

Mais do que produzir dashboards sobre futebol, o objetivo é desenvolver um
pipeline completo e reproduzível, desde a extração de uma API REST até a
disponibilização de um Data Warehouse para consumo no Power BI.

## Objetivos
O projeto foi criado como portfólio técnico e ambiente de aprendizado para
demonstrar conhecimentos em:

- Python e consumo de APIs REST;
- processos ETL (Extract, Transform, Load);
- tratamento, validação e qualidade de dados;
- PostgreSQL e SQL;
- modelagem dimensional com dimensões e tabelas fato;
- cargas completas e incrementais;
- Business Intelligence e Power BI;
- organização e documentação de projetos de dados.

## Fonte dos dados
Os dados são obtidos pela API-Football, da API-Sports. A competição utilizada é
o Campeonato Brasileiro Série A, identificado na API pelo `league_id = 71`.

O histórico atualmente processado compreende as temporadas de **2010 a 2025**.

### Extract
Responsável por consultar a API, validar as respostas e preservar o JSON sem
transformações. Temporadas em andamento podem utilizar snapshots imutáveis,
permitindo auditoria e reprocessamento.

### Transform
Converte os JSONs em DataFrames, padroniza nomes e tipos, remove duplicidades e
calcula indicadores derivados. Essa camada não realiza chamadas à API.

### Stage
Mantém no PostgreSQL os dados transformados em uma estrutura ampla e próxima
da origem.

### Warehouse
Camada analítica final, organizada em dimensões e fatos para consumo pelo Power
BI. O warehouse possui chaves, relacionamentos e índices, além de uma camada
persistente para correções manuais controladas.

Como os identificadores de estádios da API são frequentemente ausentes ou
inconsistentes, o modelo utiliza uma `venue_key` interna. Um cadastro
persistente de aliases unifica variações como `Estádio do Maracanã` e
`Estadio Jornalista Mário Filho`, mantendo também o nome bruto para auditoria.

## Modelo analítico
Principais tabelas do warehouse:

| Tipo | Tabela | Granularidade |
|---|---|---|
| Dimensão | `dim_date` | uma linha por data |
| Dimensão | `dim_team` | uma linha por clube |
| Dimensão | `dim_venue` | uma linha por estádio |
| Dimensão | `dim_player` | uma linha por jogador |
| Dimensão | `dim_season` | uma linha por temporada |
| Dimensão | `dim_position` | uma linha por posição padronizada |
| Ponte | `bridge_team_season` | um clube em uma temporada |
| Fato | `fact_match` | uma linha por partida |
| Fato | `fact_team_match` | uma linha por clube em cada partida |
| Fato | `fact_player_season` | um jogador por clube e temporada |

O estado de uma temporada é derivado dos próprios dados por meio de
`dim_season.is_completed`. Temporadas inexistentes ou incompletas aceitam novas
cargas; temporadas concluídas ficam protegidas contra alterações acidentais.

## Indicadores e possibilidades analíticas
O modelo foi preparado para apoiar análises como:

- evolução dos clubes ao longo das temporadas;
- desempenho como mandante e visitante;
- pontos, vitórias, empates, derrotas e saldo de gols;
- desempenho ofensivo e defensivo;
- clean sheets e partidas sem marcar;
- comparação entre clubes e temporadas;
- ranking de jogadores;
- gols, assistências, minutos e participações em gols;
- indicadores por 90 minutos;
- aproveitamento em duelos, dribles e finalizações.

## Fase atual
O projeto está na fase de **consolidação do pipeline de dados e preparação
para o Power BI**.

Já foram concluídos:

- extração histórica das temporadas de 2010 a 2025;
- persistência das respostas brutas em JSON;
- transformação de clubes, estádios, partidas, jogadores e calendário;
- carga do schema `stage` no PostgreSQL;
- construção do modelo dimensional no schema `warehouse`;
- validação de chaves e relacionamentos;
- tratamento persistente de correções manuais de estádios;
- consolidação de 194 nomes de estádios em 79 locais canônicos;
- reconstrução completa do histórico;
- carga incremental isolada por temporada;
- snapshots raw para futuras temporadas em andamento;
- auditoria das execuções em `etl.load_runs`;
- documentação operacional do pipeline.

Volumes atuais do warehouse:

- **6.080** partidas;
- **12.160** registros de desempenho por clube e partida;
- **15.128** registros de estatísticas de jogadores por temporada;
- **5.393** jogadores;
- **39** clubes;
- **16** temporadas.

Próximas etapas:

- conectar o Power BI ao schema `warehouse`;
- configurar o modelo semântico e seus relacionamentos;
- criar medidas DAX;
- desenvolver dashboards de clubes, partidas e jogadores;
- avaliar a automação das atualizações de temporadas futuras;
- estudar uma futura publicação em ambiente de nuvem.

O guia completo de comandos está em
[`docs/execucao.md`](docs/execucao.md).


## Estrutura do repositório

```text
football-analytics-bi/
├── data/                       # dados locais, não versionados
├── docs/                       # arquitetura e guias operacionais
├── reference/                  # regras de negócio e aliases versionados
├── src/football_analytics/
│   ├── config/                 # configurações e constantes
│   ├── extract/                # consumo da API e snapshots raw
│   ├── transform/              # limpeza e transformações
│   ├── load/                   # cargas PostgreSQL e auditoria
│   ├── pipeline/               # orquestração por temporada
│   └── utils/                  # funções reutilizáveis
├── .env.example
├── requirements.txt
└── README.md
```

## Documentação

- [Guia direto de execução](docs/execucao.md)
- [Pipeline incremental](docs/incremental_pipeline.md)
- [Modelo do stage](docs/data_model.md)
- [Modelo do warehouse](docs/warehouse_model.md)
- [Carga no PostgreSQL](docs/postgres_load.md)
- [Inventário da API](docs/api_inventory.md)
- [Correções manuais](docs/manual_data_corrections.md)
- [Resultado da curadoria de estádios](docs/venue_curation.md)

## Princípios do projeto

- dados brutos nunca são modificados manualmente;
- cada camada possui uma responsabilidade clara;
- transformações devem ser determinísticas;
- etapas do ETL podem ser executadas e validadas isoladamente;
- cargas devem preservar o estado anterior em caso de falha;
- regras reutilizáveis pertencem ao pipeline ou ao warehouse, não apenas ao
  dashboard;
- clareza, rastreabilidade e manutenção são priorizadas antes da complexidade.

## Motivção

O futebol foi escolhido por combinar interesse pessoal, grande disponibilidade
de dados e diversas possibilidades analíticas. O resultado é um projeto que
permite explorar todo o ciclo dos dados, da API ao BI, em um domínio conhecido
e visualmente rico.

Este é um projeto independente para fins de estudo e portfólio, sem vínculo
oficial com a organização do Campeonato Brasileiro ou com os provedores dos
dados.
