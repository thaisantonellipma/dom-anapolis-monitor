"""Falha (código 1) se alguma edição conhecida ficou sem texto extraído ou sem atos."""
import json, sys
eds = json.load(open("dados/edicoes.json", encoding="utf-8"))
atos = {}
for l in open("dados/atos.jsonl", encoding="utf-8"):
    a = json.loads(l); atos[a["id_edicao"]] = atos.get(a["id_edicao"], 0) + 1
import os
faltam = [e["numero"] + " " + e["data"] for e in eds if not os.path.exists(f"textos/{e['numero'].replace('.', '')}_{e['id']}.txt")]
vazias = [e["numero"] + " " + e["data"] for e in eds if atos.get(e["id"], 0) == 0]
print(f"{len(eds)} edições; sem texto: {faltam}; sem atos: {vazias}")
sys.exit(1 if faltam or vazias else 0)
