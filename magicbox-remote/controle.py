#!/usr/bin/env python3
"""Controle remoto via navegador para projetor Android (Magic Box e similares).

O iPhone abre uma pagina web; este servidor recebe os toques e repassa ao
projetor por ADB (`input keyevent / tap / swipe / text`). So usa a biblioteca
padrao do Python. Precisa do `adb` instalado onde o servidor roda.

Uso:
    python3 controle.py --adb 192.168.0.50:5555     # notebook na mesma rede
    python3 controle.py --adb localhost:5555        # Termux no proprio projetor
    python3 controle.py --dry-run                   # teste sem projetor
"""
import argparse
import json
import secrets
import shutil
import socket
import subprocess
import sys
import threading
import unicodedata
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

PAGINA = Path(__file__).with_name("controle.html")

TECLAS = {
    "UP": 19, "DOWN": 20, "LEFT": 21, "RIGHT": 22, "OK": 23,
    "BACK": 4, "HOME": 3, "MENU": 82, "RECENTES": 187,
    "VOL_UP": 24, "VOL_DOWN": 25, "MUTE": 164,
    "PLAY_PAUSE": 85, "ENTER": 66, "DEL": 67, "FORWARD_DEL": 112,
    "SETTINGS": 176,
}


class Adb:
    """Mantem um `adb shell` aberto e escreve comandos nele (bem mais rapido
    que abrir um processo adb por toque)."""

    def __init__(self, alvo, dry_run):
        self.alvo = alvo
        self.dry_run = dry_run
        self.lock = threading.Lock()
        self.shell = None
        self.largura, self.altura = 1920, 1080
        if dry_run:
            return
        if not shutil.which("adb"):
            sys.exit("ERRO: 'adb' nao encontrado. Instale (Termux: pkg install android-tools).")
        if alvo:
            saida = self._run(["connect", alvo])
            print("adb connect:", saida.strip())
        self.largura, self.altura = self._tamanho_tela()
        print(f"Tela do projetor: {self.largura}x{self.altura}")

    def _base(self):
        return ["adb"] + (["-s", self.alvo] if self.alvo else [])

    def _run(self, args):
        r = subprocess.run(["adb"] + args, capture_output=True, text=True, timeout=15)
        return r.stdout + r.stderr

    def _tamanho_tela(self):
        r = subprocess.run(self._base() + ["shell", "wm", "size"],
                           capture_output=True, text=True, timeout=15)
        # "Physical size: 1280x720" e talvez "Override size: ..." (vale o ultimo)
        tamanho = None
        for linha in r.stdout.splitlines():
            if "size:" in linha:
                tamanho = linha.split(":")[1].strip()
        if not tamanho:
            sys.exit("ERRO: nao consegui falar com o projetor via adb.\n"
                     + r.stdout + r.stderr
                     + "\nConfira: depuracao USB/ADB ligada, IP certo, e aceite o pedido na tela.")
        w, h = tamanho.split("x")
        return int(w), int(h)

    def enviar(self, comando):
        if self.dry_run:
            print("[dry-run]", comando)
            return
        with self.lock:
            for tentativa in range(2):
                if self.shell is None or self.shell.poll() is not None:
                    self.shell = subprocess.Popen(
                        self._base() + ["shell"], stdin=subprocess.PIPE,
                        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, text=True)
                try:
                    self.shell.stdin.write(comando + "\n")
                    self.shell.stdin.flush()
                    return
                except (BrokenPipeError, OSError):
                    self.shell = None
            print("Falha ao enviar:", comando)

    def px(self, x, y):
        x = min(max(float(x), 0.0), 1.0)
        y = min(max(float(y), 0.0), 1.0)
        return round(x * (self.largura - 1)), round(y * (self.altura - 1))


def texto_para_input(s):
    """`input text` nao aceita acento nem espaco cru: tira acentos e escapa."""
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode()
    s = s.replace(" ", "%s")
    return "'" + s.replace("'", "'\\''") + "'"


def tratar(adb, cmd):
    t = cmd.get("t")
    if t == "key":
        codigo = TECLAS.get(cmd.get("k"))
        if codigo is None:
            return False
        adb.enviar(f"input keyevent {codigo}")
    elif t == "text":
        s = str(cmd.get("s", ""))[:500]
        if s:
            adb.enviar(f"input text {texto_para_input(s)}")
    elif t == "tap":
        x, y = adb.px(cmd["x"], cmd["y"])
        adb.enviar(f"input tap {x} {y}")
    elif t == "longtap":
        x, y = adb.px(cmd["x"], cmd["y"])
        adb.enviar(f"input swipe {x} {y} {x} {y} 700")
    elif t == "swipe":
        x1, y1 = adb.px(cmd["x1"], cmd["y1"])
        x2, y2 = adb.px(cmd["x2"], cmd["y2"])
        ms = int(min(max(int(cmd.get("ms", 250)), 50), 2000))
        adb.enviar(f"input swipe {x1} {y1} {x2} {y2} {ms}")
    else:
        return False
    return True


def criar_handler(adb, token):
    html = PAGINA.read_bytes()

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *a):
            pass

        def _ok_token(self):
            q = parse_qs(urlparse(self.path).query)
            return q.get("k", [""])[0] == token

        def _responder(self, codigo, corpo=b"", tipo="text/plain; charset=utf-8"):
            self.send_response(codigo)
            self.send_header("Content-Type", tipo)
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(corpo)

        def do_GET(self):
            if urlparse(self.path).path != "/":
                return self._responder(404, b"nao encontrado")
            if not self._ok_token():
                return self._responder(403, "Codigo de acesso errado. Use o link impresso no terminal.".encode())
            self._responder(200, html, "text/html; charset=utf-8")

        def do_POST(self):
            if urlparse(self.path).path != "/cmd" or not self._ok_token():
                return self._responder(403, b"negado")
            try:
                n = int(self.headers.get("Content-Length", 0))
                cmd = json.loads(self.rfile.read(min(n, 4096)))
                ok = tratar(adb, cmd)
            except (ValueError, KeyError, TypeError):
                ok = False
            self._responder(200 if ok else 400, b"ok" if ok else b"comando invalido")

    return Handler


def ip_local():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("10.255.255.255", 1))
        return s.getsockname()[0]
    except OSError:
        return "127.0.0.1"
    finally:
        s.close()


def main():
    p = argparse.ArgumentParser(description="Controle do projetor pelo navegador do iPhone")
    p.add_argument("--adb", help="IP:porta do projetor (ex. 192.168.0.50:5555 ou localhost:5555)")
    p.add_argument("--porta", type=int, default=8080, help="porta da pagina web (padrao 8080)")
    p.add_argument("--dry-run", action="store_true", help="nao usa adb, so imprime os comandos")
    p.add_argument("--token", help="codigo de acesso fixo (padrao: aleatorio a cada execucao)")
    a = p.parse_args()

    adb = Adb(a.adb, a.dry_run)
    token = a.token or secrets.token_urlsafe(6)
    srv = ThreadingHTTPServer(("0.0.0.0", a.porta), criar_handler(adb, token))
    print("\nAbra no iPhone (mesmo Wi-Fi):")
    print(f"  http://{ip_local()}:{a.porta}/?k={token}\n")
    print("Trava: sem o codigo ?k= a pagina recusa (403). Para fixar o codigo use --token.")
    print("Ctrl+C para encerrar.")
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
