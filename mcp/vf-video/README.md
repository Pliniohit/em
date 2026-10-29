# VF Video: MCP de edição da Visões Filmes

Ferramentas: `analisar`, `cortar_pausas`, `tratar_audio`, `corrigir_cor`, `quadro_teste`,
`transcrever`, `queimar_legenda`, `render_final`, `editar_talking_head` (pipeline completo).

## Instalação no DESKTOP (Windows, PowerShell)

```powershell
winget install Gyan.FFmpeg
winget install Python.Python.3.12
$dest = "$env:USERPROFILE\Downloads\claude\vf-video"
New-Item -ItemType Directory -Force $dest | Out-Null
# copie server.py e requirements.txt desta pasta para $dest (ou clone o repo pliniohit/em)
cd $dest
py -3.12 -m venv .venv
.\.venv\Scripts\pip install -r requirements.txt
.\.venv\Scripts\pip install nvidia-cublas-cu12 nvidia-cudnn-cu12   # Whisper na RTX 5070
```

Feche e abra o PowerShell depois do `winget` para o `ffmpeg` entrar no PATH.

## Ligar no Claude Desktop

Arquivo `%APPDATA%\Claude\claude_desktop_config.json`, dentro de `"mcpServers"`:

```json
"vf-video": {
  "command": "C:\\Users\\Bem-vindo(a)\\Downloads\\claude\\vf-video\\.venv\\Scripts\\python.exe",
  "args": ["C:\\Users\\Bem-vindo(a)\\Downloads\\claude\\vf-video\\server.py"]
}
```

Reinicie o Claude Desktop.

## Ligar no Claude Code

```powershell
claude mcp add vf-video --scope user -- "$env:USERPROFILE\Downloads\claude\vf-video\.venv\Scripts\python.exe" "$env:USERPROFILE\Downloads\claude\vf-video\server.py"
```

## Uso

"Analise D:\00 Clientes\...\IMG_7995.mov" → plano → "edite como talking head 9:16 com legenda".
Saídas vão para a subpasta `edit\` ao lado do vídeo. O bruto nunca é alterado.
