---
name: vf-nfse
description: Calcula o valor da nota, escolhe código, emissor e CNPJ, monta a descrição e confere o teto do MEI para NFS-e da Visões Filmes (VF LTDA no Simples Nacional e MEI da Crisia). Use quando pedirem nota fiscal, NFS-e, emitir nota, quanto cobrar com imposto embutido, alíquota, DAS, teto do MEI, Agilize, Emissor Nacional, ou quando um erro de emissão aparecer (E0390, falha de esquema XML, 502/503). Prepara tudo para a Crisia clicar em emitir. Nunca emite, nunca digita senha.
---

# vf-nfse

Skill financeira da Visões Filmes (VF). Cuida da nota fiscal de serviço do começo ao rascunho pronto. O clique final em "Emitir NFS-e" é sempre da Crisia.

## Regras que não mudam
1. **Nunca clicar em emitir. Nunca digitar senha.** Preparar o conteúdo e entregar para a Crisia.
2. **A nota sai no CNPJ de quem fez o trabalho e assinou o contrato.** Nunca repartir uma nota entre CNPJs para pagar menos imposto.
3. **Nunca gravar nesta skill, em memória ou em log:** senha, token, chave de API, número de conta bancária, agência, PIX, CPF, RG. Quando a nota exigir dados bancários no corpo (Turbilhão, Borogodó), pedir à Crisia na hora e usar só naquela nota.
4. **Imposto se divide, não se soma.** Valor da nota = custo ÷ (1 − alíquota). Nunca custo × 1,06.
5. **Fato é diferente de estimativa.** Citar a fonte de qualquer valor ou regra fiscal e dizer a data. Em dúvida de enquadramento, não decidir: montar a pergunta para o contador (Agilize).

## Fluxo
1. **Quem fez o trabalho?** VF LTDA ou MEI da Crisia. Isso define o CNPJ, o emissor e o teto.
2. **O CNAE ou o objeto social cobre o serviço?** Ver `references/codigos-e-regras.md`. Serviço de mídias sociais e publicidade sai pela LTDA, não pelo MEI.
3. **Calcular o valor.** Rodar `python3 -I scripts/calcular_nota.py --custo <valor>` (alíquota padrão 6,15%). Mostrar o custo, a alíquota, o valor da nota e o imposto embutido.
4. **Escolher código e emissor.** Item 12 só no Emissor Nacional, com o grupo Evento. Ver tabela abaixo.
5. **Montar a descrição** sem acento e sem travessão, em ASCII puro. Exemplo: `Operacao de projecao mapeada no evento X, 2 diarias, junho de 2026`. Usar vírgula ou dois pontos, nunca travessão.
6. **Conferir antes de entregar** (checklist abaixo).
7. **Entregar o rascunho** à Crisia, dizer em que passo ela clica e o que conferir depois (aba "Notas Emitidas").
8. **Se for MEI:** somar a nota ao acumulado do ano e rodar `--mei-acumulado <total> --nota <valor>`. Alertar a 75%, 90% e 100% do teto.

## Alíquota (Simples Nacional, VF LTDA)
- Em out/2026 a alíquota efetiva da VF é cerca de **6,15%**: RBT12 de R$ 185.274, 2ª faixa do Anexo III (11,20% nominal, parcela a deduzir R$ 9.360). Fórmula: (RBT12 × nominal − dedução) ÷ RBT12.
- **No portal, informar 6,00%.** O 9% que aparece na NFS-e 417 não é a taxa do DAS.
- A VF está perto de R$ 180 mil de RBT12. A taxa muda com o faturamento: revisar todo mês com `--rbt12`.
- O portal não calcula ISSQN no Simples. O imposto tem que estar no preço antes de emitir.
- Alíquota de orçamento sem regra única: apareceram 6%, 8% (orçamento Estrela Guia, out/2026), 9% e 18,5% (Via Parque). Não usar 8%, 9% nem 18,5% sem perguntar ao contador de onde vêm.

## MEI da Crisia
- DAS fixo de **R$ 86,05 por mês** em 2026 (serviços). Sem alíquota percentual.
- **Teto de R$ 81.000 por ano.** Não há limite mensal.
- Até R$ 97.200 (20% acima): segue MEI no ano, com DAS sobre o excesso. **Acima de R$ 97.200: desenquadramento retroativo.** Uma fonte diverge sobre o alcance da retroatividade, então confirmar com o contador.
- CNAE 9001-9/06 é permitido ao MEI. **5911-1/99 não é.**
- Alertar quando o acumulado passar de 75% (R$ 60.750), 90% (R$ 72.900) e 100% (R$ 81.000).

## Emissor e código
| Serviço | Código | Emissor | Observação |
|---|---|---|---|
| Operação de projeção, produção de eventos, espetáculos | **12.13** | **Emissor Nacional** (nfse.gov.br), grupo Evento | O Agilize não tem esse campo (erro E0390). **Não usar 12.16**: nota cancelada por isso. |
| Locação de projetor e equipamento audiovisual | 15.03.07 + NBS 111019000 | Emissor Nacional | NBS é obrigatório agora. Confirmar com a Agilize. |
| Montagem e desmontagem | 14.06.01 | conforme o caso | |

## Cuidados do portal
- Trocar o código de tributação **apaga a descrição e o Evento**. Escolher o código primeiro.
- Avançar de etapa **zera as etapas seguintes**. Voltar e reconferir tudo.
- Se o portal der **502 ou 503**, conferir "Notas Emitidas" antes de reemitir, para não duplicar.
- Rascunho é gravado a cada "Avançar". A nota só nasce no botão "Emitir NFS-e" do passo 4.
- Mais erros e como resolver: `references/erros-emissao.md`.

## Checklist antes de entregar o rascunho
- [ ] CNPJ do prestador é de quem fez o trabalho e assinou o contrato.
- [ ] O CNPJ da Visões está correto: **14.781.279/0001-00** (já saiu proposta com dígitos trocados).
- [ ] Código bate com o serviço e o emissor tem o campo.
- [ ] Descrição sem acento e sem travessão.
- [ ] Valor = custo ÷ (1 − alíquota), conferido pelo script.
- [ ] Já existe nota igual (mesmo tomador, mesma competência, mesmo valor)? Procurar em "Notas Emitidas" antes. Duas notas de R$ 2.000 em 01/09 para o mesmo tomador, na mesma competência, ficaram sem resolver no handoff de 16/10.
- [ ] Se MEI: acumulado somado e alertas conferidos.
- [ ] Tomador exige dados bancários no corpo? Pedir à Crisia na hora.

## Preço (resumo para quando a nota nasce de um orçamento)
Técnico de campo R$ 500/dia + logística R$ 110/dia + nota. Especialista (Plinio) R$ 800/dia. Plantão remoto R$ 300/dia. Vender projeto fechado, imposto embutido, nunca em linha separada. Piso: nunca abaixo do custo (técnico + logística + imposto). Se a diária de R$ 500 é a própria Crisia ou o Plinio, ela é receita, não custo: separar nas planilhas.

## Onde estão os fatos
- Handoff de 16/10/2026 no Drive: `2026-10-16 Handoff - notas fiscais, Nos do Morro e CNPC.md`. Tem situação de cada nota, auditoria do MEI e regras aprendidas. Não achei o arquivo "Notas fiscais - guia completo e erros (handoff).md" por busca de nome; se ele existir em outra pasta, reler antes de usar esta skill para erros novos.
- Situação das notas muda toda semana: não está nesta skill. Ler o handoff mais recente.
- Fontes das regras fiscais: LC 123/2006 com redação da LC 155/2016 (Anexo III) e blogs contábeis que repetem a tabela; DAS do MEI 2026 em R$ 86,05 (INSS de 5% sobre o salário mínimo de R$ 1.621, mais R$ 5 de ISS). Não são fontes oficiais. Confirmar com a Agilize antes de uso formal.

## Registro
Ao fechar um bloco, acrescentar no diário da colmeia: data, máquina, tomador, valor, código, o que foi conferido. Só acréscimo, nunca reescrever.
