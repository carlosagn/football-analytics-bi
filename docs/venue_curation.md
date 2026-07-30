# Resultado da curadoria de estádios

## Resultado de 2010 a 2025

| Indicador | Antes | Depois |
|---|---:|---:|
| linhas em `warehouse.dim_venue` | 165 | 79 |
| nomes brutos conhecidos | 194 | 194 |
| aliases pendentes | 28 após a primeira consolidação | 0 |
| partidas | 6.030 | 6.030 |
| partidas com nome e chave de estádio | 6.029 | 6.029 |
| referências órfãs | 0 | 0 |

A única partida sem `venue_key` é a mesma que não possui `venue_name` na
origem.

## Decisões relevantes

- Maracanã, Morumbi, Mineirão, Beira-Rio, São Januário, Arena da Baixada,
  Neo Química Arena e outros estádios com variações de nome foram consolidados.
- `Estádio Municipal Eduardo José Farah` foi associado a
  `Estádio Paulo Constantino`, pois são nomes usados em épocas diferentes para
  o Prudentão.
- `Estádio Palestra Itália` e `Allianz Parque` permanecem separados. Embora
  ocupem o mesmo local e façam parte da mesma continuidade histórica, o modelo
  preserva as duas instalações/eras para não misturar capacidade e estrutura.
- `Estádio Olímpico Monumental` e `Arena do Grêmio` permanecem separados porque
  são estádios físicos distintos.
- O ID da API não é usado sozinho. Há partidas em que o ID aponta para outro
  estádio, enquanto nome e cidade identificam corretamente o local.

## Critérios de aprovação

- retirada de sufixo de cidade e estado;
- diferenças de acentuação, grafia ou capitalização;
- nome oficial e apelido amplamente reconhecido;
- mudança de naming rights;
- mudança histórica de nome do mesmo estádio;
- análise conjunta de nome, cidade, temporadas e ID de origem.

Casos que representem reforma profunda, substituição da instalação ou locais
distintos não são unidos automaticamente.

## Referências consultadas em decisões históricas

- Prefeitura de Presidente Prudente: o antigo nome Eduardo José Farah voltou a
  ser Paulo Constantino em 2013:
  https://www.presidenteprudente.sp.gov.br/site/noticia/22828
- Sociedade Esportiva Palmeiras: histórico do Palestra Itália e do Allianz
  Parque:
  https://www.palmeiras.com.br/parque-antartica/
- Federação Paulista de Futebol: laudo que registra o Allianz Parque como arena
  inaugurada em 2014 em substituição ao antigo Palestra Itália:
  https://conteudo.fpf.org.br/laudosestadios/Laudo%20Seguran%C3%A7a-%20Est.%20Arena%20Allianz%20Parque-24-10-22.pdf

## Validação operacional

```sql
SELECT review_status, COUNT(*)
FROM manual.venue_name_alias
GROUP BY review_status;

SELECT COUNT(*)
FROM warehouse.fact_match f
LEFT JOIN warehouse.dim_venue v ON v.venue_key = f.venue_key
WHERE f.venue_key IS NOT NULL
  AND v.venue_key IS NULL;
```

O primeiro resultado deve mostrar todos os aliases atuais como `approved`. A
segunda consulta deve retornar zero.
