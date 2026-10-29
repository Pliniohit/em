"""VF Video: servidor MCP de edição de vídeo da Visões Filmes.

Roda no computador (Windows, Mac ou Linux) e dá ao Claude ferramentas de corte
de pausas, áudio, cor, reenquadramento, transcrição e legenda via ffmpeg.
Usa NVENC quando a placa NVIDIA está disponível e faster-whisper na GPU.
"""
from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import tempfile
from pathlib import Path

from mcp.server.fastmcp import FastMCP, Image

mcp = FastMCP("vf-video")

FFMPEG = os.environ.get("VF_FFMPEG", "ffmpeg")
FFPROBE = os.environ.get("VF_FFPROBE", "ffprobe")

FORMATOS = {
    "9:16": (1080, 1920),
    "16:9": (1920, 1080),
    "1:1": (1080, 1080),
    "4:5": (1080, 1350),
}

# Grades leves, pensadas para celular. Ajuste fino continua no Premiere.
CORES = {
    "nublado": "eq=contrast=1.08:saturation=1.10:gamma=0.98,colorbalance=rs=0.03:gs=0.0:bs=-0.03:rm=0.02:bm=-0.02,curves=all='0/0 0.85/0.80 1/0.94'",
    "neutro": "eq=contrast=1.05:saturation=1.05",
    "quente": "eq=contrast=1.06:saturation=1.08,colorbalance=rs=0.05:bs=-0.05:rm=0.03:bm=-0.03",
    "frio": "eq=contrast=1.06:saturation=1.02,colorbalance=rs=-0.03:bs=0.04:bm=0.02",
}

_encoder_cache: str | None = None


def _run(args: list[str], cwd: str | None = None) -> subprocess.CompletedProcess:
    p = subprocess.run(args, cwd=cwd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    if p.returncode != 0:
        raise RuntimeError(f"ffmpeg falhou ({p.returncode}):\n{p.stderr[-2500:]}")
    return p


def _encoder() -> str:
    """h264_nvenc se a GPU NVIDIA aceitar, senão libx264."""
    global _encoder_cache
    if _encoder_cache is None:
        test = subprocess.run(
            [FFMPEG, "-hide_banner", "-loglevel", "error", "-f", "lavfi", "-i", "color=c=black:s=256x256:d=0.1",
             "-c:v", "h264_nvenc", "-f", "null", "-"],
            capture_output=True, text=True,
        )
        _encoder_cache = "h264_nvenc" if test.returncode == 0 else "libx264"
    return _encoder_cache


def _venc(qualidade: str = "final") -> list[str]:
    enc = _encoder()
    if enc == "h264_nvenc":
        cq = "17" if qualidade == "intermediario" else "21"
        teto = [] if qualidade == "intermediario" else ["-maxrate", "10M", "-bufsize", "20M"]
        return ["-c:v", "h264_nvenc", "-preset", "p6", "-rc", "vbr", "-cq", cq, "-b:v", "0", *teto, "-pix_fmt", "yuv420p"]
    if qualidade == "intermediario":
        return ["-c:v", "libx264", "-preset", "medium", "-crf", "16", "-pix_fmt", "yuv420p"]
    # entrega para redes: teto de 10 Mbps (Instagram recomprime acima disso)
    return ["-c:v", "libx264", "-preset", "medium", "-crf", "20", "-maxrate", "10M", "-bufsize", "20M", "-pix_fmt", "yuv420p"]


def _probe(video: str) -> dict:
    p = _run([FFPROBE, "-v", "error", "-show_format", "-show_streams", "-of", "json", video])
    return json.loads(p.stdout)


def _dur(video: str) -> float:
    return float(_probe(video)["format"]["duration"])


def _saida(video: str, sufixo: str, saida: str | None) -> str:
    if saida:
        return saida
    src = Path(video)
    pasta = src.parent if src.parent.name == "edit" else src.parent / "edit"
    pasta.mkdir(exist_ok=True)
    return str(pasta / f"{src.stem}_{sufixo}.mp4")


def _pausas(video: str, limiar_db: float, min_pausa: float) -> list[tuple[float, float]]:
    p = subprocess.run(
        [FFMPEG, "-hide_banner", "-nostats", "-i", video, "-map", "0:a:0",
         "-af", f"highpass=f=120,silencedetect=n={limiar_db}dB:d={min_pausa}", "-f", "null", "-"],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
    )
    starts = [float(x) for x in re.findall(r"silence_start: ([\d.]+)", p.stderr)]
    ends = [float(x) for x in re.findall(r"silence_end: ([\d.]+)", p.stderr)]
    total = _dur(video)
    if len(ends) < len(starts):
        ends.append(total)
    return list(zip(starts, ends))


def _trechos(total: float, pausas: list[tuple[float, float]], respiro: float) -> list[tuple[float, float]]:
    """Trechos mantidos: tudo menos o miolo de cada pausa (deixa `respiro` nas bordas)."""
    # pausas separadas por menos de 2x o respiro viram uma só (senão sobra um fiapo mudo)
    juntas: list[list[float]] = []
    for s, e in pausas:
        if juntas and s - juntas[-1][1] < 2 * respiro + 0.1:
            juntas[-1][1] = e
        else:
            juntas.append([s, e])
    keep, cur = [], 0.0
    for s, e in juntas:
        cs = 0.0 if s <= 0.05 else s + respiro
        ce = total if e >= total - 0.05 else e - respiro
        if ce - cs <= 0.05:
            continue
        if cs > cur + 0.05:
            keep.append((cur, cs))
        cur = max(cur, ce)
    if total - cur > 0.05:
        keep.append((cur, total))
    return keep


def _grafo_corte(trechos: list[tuple[float, float]]) -> str:
    """trim/atrim por trecho, 30 ms de fade em cada emenda, concat."""
    parts = []
    for i, (s, e) in enumerate(trechos):
        d = e - s
        parts.append(f"[0:v:0]trim=start={s:.3f}:end={e:.3f},setpts=PTS-STARTPTS[v{i}]")
        parts.append(
            f"[0:a:0]atrim=start={s:.3f}:end={e:.3f},asetpts=PTS-STARTPTS,"
            f"afade=t=in:st=0:d=0.03,afade=t=out:st={max(d - 0.03, 0):.3f}:d=0.03[a{i}]"
        )
    ins = "".join(f"[v{i}][a{i}]" for i in range(len(trechos)))
    parts.append(f"{ins}concat=n={len(trechos)}:v=1:a=1[vc][ac]")
    return ";".join(parts)


def _vf_formato(formato: str, largura: int | None) -> str:
    if formato == "original":
        return f"scale={largura}:-2" if largura else "null"
    w, h = FORMATOS[formato]
    if largura:
        h = round(h * largura / w / 2) * 2
        w = largura
    return f"scale={w}:{h}:force_original_aspect_ratio=increase,crop={w}:{h},setsar=1"


AUDIO_CHAIN = "highpass=f=80,afftdn=nf=-25,loudnorm=I={lufs}:TP=-1.0:LRA=11"


@mcp.tool()
def analisar(video: str) -> list:
    """Raio-x do vídeo: resolução, fps, duração, loudness (LUFS), pausas detectadas
    e uma folha de contato com 14 quadros. Use antes de propor o plano de corte."""
    info = _probe(video)
    v = next(s for s in info["streams"] if s["codec_type"] == "video")
    total = float(info["format"]["duration"])
    lp = subprocess.run(
        [FFMPEG, "-hide_banner", "-nostats", "-i", video, "-map", "0:a:0", "-af", "ebur128=framelog=quiet", "-f", "null", "-"],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
    )
    m = re.findall(r"I:\s+(-?[\d.]+) LUFS", lp.stderr)
    lufs = m[-1] if m else "?"
    pz = _pausas(video, -26, 0.4)
    soma = sum(e - s for s, e in pz)
    sheet = Path(tempfile.gettempdir()) / f"vf_sheet_{Path(video).stem}.jpg"
    _run([FFMPEG, "-y", "-loglevel", "error", "-i", video,
          "-vf", f"fps={14 / max(total, 1):.4f},scale=270:-1,tile=7x2", "-frames:v", "1", "-q:v", "4", str(sheet)])
    texto = (
        f"{Path(video).name}: {v['width']}x{v['height']} {v.get('r_frame_rate')} fps, {total:.1f} s, "
        f"{lufs} LUFS. Pausas >=0,4 s a -26 dB: {len(pz)} (total {soma:.1f} s): "
        + ", ".join(f"{s:.1f}-{e:.1f}" for s, e in pz)
        + f". Encoder disponivel: {_encoder()}."
    )
    return [texto, Image(path=str(sheet))]


@mcp.tool()
def cortar_pausas(video: str, saida: str | None = None, limiar_db: float = -26.0,
                  min_pausa: float = 0.4, respiro: float = 0.15) -> str:
    """Corta pausas e silêncios. limiar_db: abaixo disso conta como silêncio (rua: -26; estúdio: -35).
    respiro: segundos mantidos em cada borda da pausa. Gera intermediário de alta qualidade."""
    total = _dur(video)
    trechos = _trechos(total, _pausas(video, limiar_db, min_pausa), respiro)
    out = _saida(video, "corte", saida)
    _run([FFMPEG, "-y", "-hide_banner", "-loglevel", "error", "-i", video,
          "-filter_complex", _grafo_corte(trechos), "-map", "[vc]", "-map", "[ac]",
          *_venc("intermediario"), "-c:a", "aac", "-b:a", "256k", out])
    return f"{out}: {total:.1f} s -> {_dur(out):.1f} s, {len(trechos)} trechos."


@mcp.tool()
def tratar_audio(video: str, saida: str | None = None, lufs: float = -14.0) -> str:
    """Passa-alta 80 Hz, redução leve de ruído e normalização de loudness (-14 LUFS = Instagram/YouTube)."""
    out = _saida(video, "audio", saida)
    _run([FFMPEG, "-y", "-hide_banner", "-loglevel", "error", "-i", video, "-map", "0:v:0", "-map", "0:a:0",
          "-c:v", "copy", "-af", AUDIO_CHAIN.format(lufs=lufs), "-c:a", "aac", "-b:a", "256k", out])
    return out


@mcp.tool()
def corrigir_cor(video: str, preset: str = "nublado", saida: str | None = None) -> str:
    """Grade leve. Presets: nublado (segura o céu, aquece pele), neutro, quente, frio."""
    out = _saida(video, f"cor_{preset}", saida)
    _run([FFMPEG, "-y", "-hide_banner", "-loglevel", "error", "-i", video, "-map", "0:v:0", "-map", "0:a:0?",
          "-vf", CORES[preset], *_venc("intermediario"), "-c:a", "copy", out])
    return out


@mcp.tool()
def quadro_teste(video: str, tempo: float = 5.0, preset: str = "nublado") -> list:
    """Antes/depois de um quadro com o preset de cor, lado a lado. Para aprovar a cor sem renderizar."""
    out = Path(tempfile.gettempdir()) / f"vf_cor_{Path(video).stem}_{preset}.jpg"
    _run([FFMPEG, "-y", "-loglevel", "error", "-ss", str(tempo), "-i", video, "-frames:v", "1",
          "-filter_complex", f"[0:v]scale=540:-2,split[a][b];[b]{CORES[preset]}[c];[a][c]hstack", "-q:v", "3", str(out)])
    return [f"Esquerda: original. Direita: {preset}.", Image(path=str(out))]


@mcp.tool()
def transcrever(video: str, modelo: str = "small", idioma: str = "pt") -> str:
    """Transcreve com faster-whisper (GPU se houver) e grava <video>.srt e <video>.words.json
    (palavra a palavra, para cortes e legenda). Modelos: tiny, base, small, medium, large-v3."""
    from faster_whisper import WhisperModel

    try:
        model = WhisperModel(modelo, device="cuda", compute_type="float16")
    except Exception:
        model = WhisperModel(modelo, device="cpu", compute_type="int8")
    segs, _ = model.transcribe(video, language=idioma, word_timestamps=True, vad_filter=True)
    segs = list(segs)
    base = Path(video).with_suffix("")

    def ts(t: float) -> str:
        h, r = divmod(t, 3600)
        m, s = divmod(r, 60)
        return f"{int(h):02d}:{int(m):02d}:{int(s):02d},{int((s % 1) * 1000):03d}"

    # legenda curta, estilo stories: no máximo 4 palavras por bloco
    blocos, words = [], [w for s in segs for w in (s.words or [])]
    for i in range(0, len(words), 4):
        grupo = words[i:i + 4]
        blocos.append((grupo[0].start, grupo[-1].end, " ".join(w.word.strip() for w in grupo)))
    srt = "\n".join(f"{n}\n{ts(a)} --> {ts(b)}\n{t}\n" for n, (a, b, t) in enumerate(blocos, 1))
    Path(f"{base}.srt").write_text(srt, encoding="utf-8")
    Path(f"{base}.words.json").write_text(
        json.dumps([{"w": w.word, "s": w.start, "e": w.end} for w in words], ensure_ascii=False), encoding="utf-8")
    texto = " ".join(s.text.strip() for s in segs)
    return f"SRT: {base}.srt | palavras: {base}.words.json\n\n{texto}"


@mcp.tool()
def queimar_legenda(video: str, srt: str, saida: str | None = None, tamanho: int = 16,
                    posicao_vertical: int = 520) -> str:
    """Queima a legenda no vídeo (sempre o último passo). posicao_vertical: margem inferior em px do ASS."""
    out = _saida(video, "legenda", saida)
    srt_p = Path(srt).resolve()
    estilo = (f"FontName=Arial,Fontsize={tamanho},Bold=1,PrimaryColour=&H00FFFFFF,OutlineColour=&H00000000,"
              f"BorderStyle=1,Outline=2,Shadow=0,Alignment=2,MarginV={posicao_vertical}")
    # roda dentro da pasta do SRT para evitar o problema do "C:" no filtro subtitles do Windows
    _run([FFMPEG, "-y", "-hide_banner", "-loglevel", "error", "-i", str(Path(video).resolve()),
          "-map", "0:v:0", "-map", "0:a:0?", "-vf", f"subtitles={srt_p.name}:force_style='{estilo}'",
          *_venc("intermediario"), "-c:a", "copy", str(Path(out).resolve())], cwd=str(srt_p.parent))
    return out


@mcp.tool()
def render_final(video: str, formato: str = "9:16", saida: str | None = None, largura: int | None = None) -> str:
    """Render de entrega: reenquadra (crop central) e escala para o formato, H.264 + AAC, faststart.
    Formatos: 9:16, 16:9, 1:1, 4:5, original."""
    out = _saida(video, f"final_{formato.replace(':', 'x')}", saida)
    _run([FFMPEG, "-y", "-hide_banner", "-loglevel", "error", "-i", video, "-map", "0:v:0", "-map", "0:a:0?",
          "-vf", _vf_formato(formato, largura), *_venc("final"), "-r", "30",
          "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", out])
    return f"{out}: {os.path.getsize(out) / 1048576:.1f} MB, {_dur(out):.1f} s"


@mcp.tool()
def editar_talking_head(video: str, formato: str = "9:16", silencio: bool = True, audio: bool = True,
                        cor: str | None = "nublado", legenda: bool = False, limiar_db: float = -26.0,
                        respiro: float = 0.15, saida: str | None = None) -> str:
    """Pipeline completo para depoimento/selfie: corta pausas, trata áudio, cor, formato e
    (opcional) legenda queimada. Uma passada de encode quando não há legenda; duas quando há."""
    total = _dur(video)
    trechos = _trechos(total, _pausas(video, limiar_db, 0.4), respiro) if silencio else [(0.0, total)]
    vchain = ",".join(x for x in [CORES.get(cor) if cor else None, _vf_formato(formato, None)] if x)
    achain = AUDIO_CHAIN.format(lufs=-14) if audio else "anull"
    graph = _grafo_corte(trechos) + f";[vc]{vchain}[vo];[ac]{achain}[ao]"
    out = _saida(video, f"final_{formato.replace(':', 'x')}", saida)
    alvo = out if not legenda else _saida(video, "pre_legenda", None)
    _run([FFMPEG, "-y", "-hide_banner", "-loglevel", "error", "-i", video, "-filter_complex", graph,
          "-map", "[vo]", "-map", "[ao]", *_venc("final" if not legenda else "intermediario"), "-r", "30",
          "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", alvo])
    nota = ""
    if legenda:
        info = transcrever(alvo)
        srt = str(Path(alvo).with_suffix(".srt"))
        queimar_legenda(alvo, srt, out)
        nota = f"\nLegenda: {srt} (revise o texto; se corrigir, rode queimar_legenda de novo).\n" + info.split("\n\n", 1)[-1][:600]
    return (f"{out}: {total:.1f} s -> {_dur(out):.1f} s, {len(trechos)} trechos, "
            f"{os.path.getsize(out) / 1048576:.1f} MB, encoder {_encoder()}.{nota}")


if __name__ == "__main__":
    if not shutil.which(FFMPEG):
        raise SystemExit("ffmpeg nao encontrado. Instale com: winget install Gyan.FFmpeg")
    mcp.run()
