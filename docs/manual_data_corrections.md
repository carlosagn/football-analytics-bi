# Correções manuais de dados

Este documento registra informações complementadas ou corrigidas manualmente
quando os dados disponibilizados pela API estão ausentes, desatualizados ou
duplicados.

# Regras

- O JSON da camada raw nunca deve ser alterado.
- O stage deve continuar representando o resultado do processo de transformação.
- Toda correção deve registrar o objeto afetado, o motivo e a alteração feita.
- Endereços e capacidades informados manualmente devem ser conferidos em uma
  fonte confiável antes do uso analítico.
- As correções permanentes devem ser registradas em
  `manual.venue_corrections`, nunca diretamente no warehouse.

# Correções conhecidas

## Estádio duplicado

- Tabela: `warehouse.dim_venue`
- Identificador duplicado: `venue_id = 279`
- Identificador canônico: `venue_id = 19377`
- Ação: direcionar as referências de `279` para `19377` e excluir o registro
  duplicado.

# Migração dos ajustes existentes

Os ajustes que haviam sido feitos em `warehouse.dim_venue` foram migrados para
a tabela persistente com o comando:

```bash
PYTHONPATH=src ./venv/Scripts/python.exe \
  -m football_analytics.load.manual_corrections
```

Esse comando serve para capturar ajustes antigos feitos diretamente na dimensão.
Novas correções devem ser inseridas ou atualizadas diretamente na tabela
`manual.venue_corrections`.

# Armazenamento persistente

A tabela `manual.venue_corrections` fica fora do schema recriado e é aplicada
automaticamente durante a construção do warehouse. Ela armazena:

- identificador original e identificador canônico;
- endereço corrigido;
- capacidade corrigida;
- fonte da informação;
- data da verificação;
- observação.

Atualmente existem 17 estádios com atributos complementados manualmente e um
mapeamento de duplicidade. A unificação `279 -> 19377` é aplicada tanto na
dimensão quanto nas tabelas que referenciam o estádio.
