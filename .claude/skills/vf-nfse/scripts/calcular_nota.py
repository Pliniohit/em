#!/usr/bin/env python3
"""Calculadora da skill vf-nfse.

Uso:
  calcular_nota.py --custo 4100                      # valor da nota com a aliquota padrao (6,15%)
  calcular_nota.py --custo 4100 --aliquota 6         # aliquota escolhida
  calcular_nota.py --rbt12 185274                    # aliquota efetiva do Anexo III para esse RBT12
  calcular_nota.py --mei-acumulado 17280 --nota 2780 # impacto no teto do MEI

Regra: valor da nota = custo / (1 - aliquota). Nunca custo * (1 + aliquota).
"""
import argparse
from decimal import Decimal, ROUND_HALF_UP

CENT = Decimal("0.01")
TETO_MEI = Decimal("81000")
TETO_MEI_TOLERANCIA = Decimal("97200")  # 20% acima do teto
ALIQUOTA_PADRAO = Decimal("6.15")  # efetiva da VF em out/2026 (RBT12 ~ R$ 185.274); revisar todo mes

# Anexo III do Simples Nacional: (limite superior do RBT12, aliquota nominal %, parcela a deduzir)
ANEXO_III = [
    (Decimal("180000"), Decimal("6.00"), Decimal("0")),
    (Decimal("360000"), Decimal("11.20"), Decimal("9360")),
    (Decimal("720000"), Decimal("13.50"), Decimal("17640")),
    (Decimal("1800000"), Decimal("16.00"), Decimal("35640")),
    (Decimal("3600000"), Decimal("21.00"), Decimal("125640")),
    (Decimal("4800000"), Decimal("33.00"), Decimal("648000")),
]


def money(x):
    return x.quantize(CENT, rounding=ROUND_HALF_UP)


def br(x):
    s = f"{money(x):,.2f}"
    return "R$ " + s.replace(",", "X").replace(".", ",").replace("X", ".")


def aliquota_efetiva(rbt12):
    for limite, nominal, deducao in ANEXO_III:
        if rbt12 <= limite:
            if rbt12 <= 0:
                return nominal
            return (rbt12 * nominal / 100 - deducao) / rbt12 * 100
    raise SystemExit("RBT12 acima de R$ 4,8 milhoes: fora do Simples Nacional.")


def faixa_do(rbt12):
    for i, (limite, _, _) in enumerate(ANEXO_III, 1):
        if rbt12 <= limite:
            return i, limite
    return None, None


def cmd_nota(custo, aliq):
    a = aliq / 100
    if not (0 <= a < 1):
        raise SystemExit("Aliquota deve estar entre 0 e 100 (em %).")
    nota = custo / (1 - a)
    errado = custo * (1 + a)
    print(f"Custo (o que precisa sobrar): {br(custo)}")
    print(f"Aliquota usada: {aliq:.2f}%")
    print(f"Valor da nota (custo / (1 - aliquota)): {br(nota)}")
    print(f"Imposto embutido: {br(nota - custo)}")
    print(f"Conferencia: nota - imposto = {br(nota * (1 - a))}")
    print(f"Se fosse custo x (1 + aliquota) daria {br(errado)}: faltariam {br(nota * (1 - a) - errado * (1 - a))} depois do imposto.")


def cmd_rbt12(rbt12):
    ef = aliquota_efetiva(rbt12)
    i, limite = faixa_do(rbt12)
    print(f"RBT12: {br(rbt12)} -> faixa {i} do Anexo III (ate {br(limite)})")
    print(f"Aliquota efetiva: {ef:.2f}%  (informar 6,00% no portal; o calculo de preco usa a efetiva)")
    if i == 1:
        print(f"Atencao: faltam {br(limite - rbt12)} para a 2a faixa, onde a efetiva sobe.")
    elif i == 2:
        print(f"Na 2a faixa. Margem ate a 3a faixa: {br(limite - rbt12)}.")


def cmd_mei(acumulado, nota):
    novo = acumulado + nota
    pct = novo / TETO_MEI * 100
    print(f"MEI acumulado no ano: {br(acumulado)}")
    if nota:
        print(f"Nota a somar: {br(nota)}  ->  novo acumulado: {br(novo)}")
    print(f"Uso do teto de {br(TETO_MEI)}: {pct:.1f}%  (sobra {br(max(TETO_MEI - novo, Decimal(0)))})")
    for marca, nome in ((Decimal("75"), "75%"), (Decimal("90"), "90%"), (Decimal("100"), "100%")):
        if pct >= marca:
            print(f"ALERTA: passou de {nome} do teto do MEI.")
    if novo > TETO_MEI_TOLERANCIA:
        print(f"ALERTA GRAVE: acima de {br(TETO_MEI_TOLERANCIA)} (20% sobre o teto). Desenquadramento retroativo. Falar com o contador antes de emitir.")
    elif novo > TETO_MEI:
        print(f"Acima do teto, mas ate {br(TETO_MEI_TOLERANCIA)}: segue MEI no ano, com DAS sobre o excesso. Confirmar com o contador.")


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--custo", type=Decimal)
    p.add_argument("--aliquota", type=Decimal, default=ALIQUOTA_PADRAO, help="em %% (padrao 6,15)")
    p.add_argument("--rbt12", type=Decimal)
    p.add_argument("--mei-acumulado", type=Decimal)
    p.add_argument("--nota", type=Decimal, default=Decimal(0))
    a = p.parse_args()
    feito = False
    if a.custo is not None:
        cmd_nota(a.custo, a.aliquota); feito = True
    if a.rbt12 is not None:
        if feito: print()
        cmd_rbt12(a.rbt12); feito = True
    if a.mei_acumulado is not None:
        if feito: print()
        cmd_mei(a.mei_acumulado, a.nota); feito = True
    if not feito:
        p.print_help()


if __name__ == "__main__":
    main()
