"""Compara as duas leituras do PDF: acts por edição vs. sumário, órgão identificado e SEI da planilha."""
import json, re, glob, os, subprocess, sys
import openpyxl
SEI = re.compile(r"\d{5}\.\d{8}/\d{4}-\d{2}")
eds = json.load(open("dados/edicoes.json", encoding="utf-8"))
wb = openpyxl.load_workbook("historico/Historico_Monitoramento_DOM_Anapolis.xlsx")
seis = set()
for r in wb["Atos monitorados"].iter_rows(min_row=2, values_only=True):
    seis |= set(SEI.findall(r[5] or ""))
out = ["# Comparação das leituras do PDF\n"]
for modo, pasta in (("colunas", "textos"), ("auto", "textos_auto")):
    saida = f"dados/atos_{modo}.jsonl"
    subprocess.run([sys.executable, "scripts/atos.py", pasta, saida], check=True, capture_output=True)
    atos = [json.loads(l) for l in open(saida, encoding="utf-8")]
    dif, soma_sum, soma_seg = 0, 0, 0
    for e in eds:
        t = open(f"{pasta}/{e['numero'].replace('.', '')}_{e['id']}.txt", encoding="utf-8").read()
        suma = len(re.findall(r"\.{5,}\s*\d+\s*$", t, re.M))
        seg = sum(1 for x in atos if x["id_edicao"] == e["id"])
        if suma >= 5:
            dif += abs(suma - seg); soma_sum += suma; soma_seg += seg
    todo = set()
    for f in glob.glob(f"{pasta}/*.txt"):
        todo |= set(SEI.findall(open(f, encoding="utf-8").read()))
    ident = sum(1 for x in atos if x["orgao"] != "Não identificado")
    out.append(f"## Modo {modo}\n- atos: {len(atos)}\n- sumário (edições com ≥5 itens): {soma_sum} | segmentados: {soma_seg} | diferença absoluta: {dif}\n"
               f"- órgão identificado: {ident}/{len(atos)}\n- SEI distintos no texto: {len(todo)} | da planilha presentes: {len(seis & todo)}/{len(seis)}\n")
open("relatorios/comparacao_modos.md", "w", encoding="utf-8").write("\n".join(out))
print("\n".join(out))
