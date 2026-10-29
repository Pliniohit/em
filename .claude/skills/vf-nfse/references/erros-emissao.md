# Erros de emissão e o que fazer

Fonte: handoff de 16/10/2026 (Drive) e instruções da Crisia. Estado em 29/10/2026.

| Sintoma | Causa | O que fazer |
|---|---|---|
| **E0390** ao emitir pelo Agilize | Item 12 (espetáculos, produção de eventos) exige o campo Evento, e o Agilize não tem | Emitir pelo Emissor Nacional (nfse.gov.br), com o grupo Evento |
| **"Falha no esquema XML"** | Acento ou travessão na descrição | Reescrever em ASCII: sem acento, sem travessão, sem aspas curvas. Usar vírgula ou dois pontos |
| Descrição e Evento sumiram | Trocou o código de tributação | Escolher o código primeiro, depois descrição e Evento |
| Campos da etapa 3 vazios depois de voltar | Avançar de etapa zera as seguintes | Voltar e preencher tudo de novo, de cima para baixo |
| **502 ou 503** do portal | Portal instável | Abrir "Notas Emitidas" e conferir se a nota nasceu antes de tentar de novo. Reemitir às cegas duplica |
| Campo **NBS** obrigatório | Passou a ser exigido no Emissor Nacional. A nota de 04/08 (15.03.07) saiu sem | Locação de equipamento audiovisual: 111019000, o residual de máquinas e equipamentos sem operador. Confirmar com a Agilize |
| Nota cancelada por **código errado** | Saiu com 12.16.01 (exibição de filmes) quando o tomador pediu 12.13 | Cancelar e reemitir com 12.13. Para operação de projeção, o código é 12.13 |
| Proposta com **CNPJ da Visões errado** | Dígitos 271 e 781 trocados (14.271.279 em vez de 14.781.279) | Conferir o CNPJ em toda proposta e contrato antes da nota |
| Portal não mostra imposto | No Simples o ISSQN é apurado fora da nota | Colocar o imposto no preço antes de emitir |
| Nota "sumiu" depois de Avançar | Rascunho é gravado a cada Avançar, a nota só nasce no Emitir | Procurar em rascunhos, não em Notas Emitidas |
| Possível **duplicata** | Mesmo tomador, mesma competência, mesmo valor | Conferir em Notas Emitidas antes de emitir. Duas notas de R$ 2.000 em 01/09 (competência 09/2026) ficaram sem conferir no handoff de 16/10 |
| Tomador exige **dados bancários no corpo** (Turbilhão, Borogodó) | Exigência do tomador | Pedir os dados à Crisia na hora. Não gravar em lugar nenhum |

## Regra geral de diagnóstico
1. Ler a mensagem inteira, não só o código.
2. Conferir Notas Emitidas antes de qualquer reemissão.
3. Mexer em uma coisa por vez e reconferir as etapas seguintes.
4. Se o erro não está nesta tabela, não inventar causa: montar a pergunta para a Agilize com o texto exato do erro e o código de tributação usado.
