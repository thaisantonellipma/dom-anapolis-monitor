"""Coleta metadados e PDFs das edições do DOM de Anápolis via API pública."""
import json, os, sys, time, urllib.request

BASE = "https://dom.anapolis.go.gov.br"
UA = {"User-Agent": "Mozilla/5.0 (monitor-dom-anapolis)"}


def get(url, binario=False):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=60) as r:
        dado = r.read()
    return dado if binario else json.loads(dado)


def meses(inicio, fim):
    a, m = map(int, inicio.split("-"))
    fa, fm = map(int, fim.split("-"))
    while (a, m) <= (fa, fm):
        yield f"{a:04d}-{m:02d}"
        a, m = (a + 1, 1) if m == 12 else (a, m + 1)


def main(mes_ini, mes_fim, ed_min, ed_max):
    os.makedirs("pdfs", exist_ok=True)
    os.makedirs("dados", exist_ok=True)
    edicoes = []
    for mes in meses(mes_ini, mes_fim):
        for item in get(f"{BASE}/api/diarios/diariosPorDia?data={mes}"):
            d = get(f"{BASE}/api/diarios/{item['id']}")
            time.sleep(0.2)
            numero = int(str(d["numero"]).replace(".", ""))
            if not (ed_min <= numero <= ed_max):
                continue
            midia = (d.get("midias") or [{}])[0]
            edicoes.append({
                "id": d["id"], "numero": d["numero"], "data": d["data"],
                "tipo": (d.get("tipo") or {}).get("descricao"),
                "situacao": d.get("situacaoDescricao"),
                "codigo_icp": d.get("codigo_icp"), "url_pdf": midia.get("url"),
                "bytes": midia.get("size"),
            })
    edicoes.sort(key=lambda e: int(e["numero"].replace(".", "")))
    for e in edicoes:
        if not e["url_pdf"]:
            print("SEM PDF:", e["numero"])
            continue
        destino = f"pdfs/{e['numero'].replace('.', '')}.pdf"
        if not os.path.exists(destino):
            with open(destino, "wb") as f:
                f.write(get(e["url_pdf"], binario=True))
            time.sleep(0.3)
    with open("dados/edicoes.json", "w", encoding="utf-8") as f:
        json.dump(edicoes, f, ensure_ascii=False, indent=1)
    print(f"{len(edicoes)} edições coletadas")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2], int(sys.argv[3]), int(sys.argv[4]))
