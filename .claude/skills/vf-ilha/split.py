"""Divide um arquivo em partes de ~19 MB para o asset store da Ilha VF.
Nenhuma parte começa com '<' ou espaço (o armazenamento recusaria como markup)."""
import sys, os
CHUNK = 19 * 1024 * 1024
BAD = {0x3C, 0x20, 0x09, 0x0A, 0x0D, 0x0C}
src = sys.argv[1]
data = open(src, "rb").read()
cuts, b = [0], CHUNK
while b < len(data):
    while b < len(data) and data[b] in BAD:
        b += 1
    if b >= len(data):
        break
    cuts.append(b)
    b += CHUNK
cuts.append(len(data))
base, ext = os.path.splitext(src)
for i in range(len(cuts) - 1):
    out = f"{base}.part{i + 1:02d}{ext}"
    open(out, "wb").write(data[cuts[i]:cuts[i + 1]])
    print(out, cuts[i + 1] - cuts[i])
