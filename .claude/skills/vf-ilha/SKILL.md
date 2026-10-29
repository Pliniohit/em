---
name: vf-ilha
description: Processa a fila da Ilha de Edição VF (artifact https://claude.ai/artifact/8BwmHWrsPXstcbKTpmwGYi). Use quando a Cris ou o Plinio disserem "edite a fila", "edita meus vídeos" ou mandarem vídeo pela ilha.
---

# Ilha de Edição VF — rotina

Artifact: https://claude.ai/artifact/8BwmHWrsPXstcbKTpmwGYi (fonte: `editor/index.html`)
Banco: coleção `jobs`. Campos: `titulo`, `status` (rascunho|enviado|editando|pronto|erro),
`brief` {formato, tipo, duracao, silencio, takes, legenda, cor, audio, reframe, xml, plano, notas},
`clips` [{name, size, mime, parts:[assetId…]}], `resultado` {nome, size, parts:[assetId…]}, `nota_claude`.

## Passos
1. `ArtifactData list jobs` → pegar os de `status: enviado`. Marcar `editando` (update com `if_version`).
2. Para cada clip: `Artifact read` com `path` = cada assetId, `out_dir` = `<trabalho>/<job>/parts/`.
   Juntar as partes NA ORDEM com `cat` → arquivo original. Conferir tamanho == `size`.
3. Editar seguindo o brief (ver `.claude/skills/video-use/SKILL.md` para as regras de produção):
   - silêncio: `auto-editor in.mp4 --margin 0.2s --no-open -o cut.mp4` (XML: `--export premiere`)
   - áudio: `loudnorm=I=-14:TP=-1:LRA=11`
   - reenquadrar: crop centralizado no formato pedido; 9:16 = 1080x1920
   - cor: grade leve via `helpers/grade.py` do video-use ou `eq`/`curves`
   - legenda/takes: precisam de transcrição (ElevenLabs Scribe ou Whisper). Hoje a rede do ambiente
     bloqueia api.elevenlabs.io e o download do modelo Whisper → avisar no `nota_claude`.
   - `brief.plano == true`: escrever o plano em `nota_claude`, status `enviado`, e parar até a Cris aprovar.
4. Render final H.264 + AAC, `-movflags +faststart`. Dividir em partes de 19 MB com
   `python3 split.py final.mp4` (nenhuma parte pode começar com `<` ou espaço).
5. Subir cada parte: `Artifact publish` com `url`, `asset: true`, `file_paths`.
6. `update` no job: `resultado` {nome, size, parts}, `status: pronto`, `nota_claude` com o que foi feito
   e o que ficou de fora.
7. Nunca apagar asset de vídeo bruto sem a Cris pedir.
