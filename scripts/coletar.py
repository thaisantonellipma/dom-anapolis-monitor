"""Coleta incremental das edições do DOM de Anápolis (API pública) e dos PDFs novos."""
import datetime, json, os, sys, time, urllib.request

BASE = "https://dom.anapolis.go.gov.br"
UA = {"User-Agent": "Mozilla/5.0 (monitor-dom-anapolis)"}
ARQ = "dados/edicoes.json"


def get(url, binario=False, tentativas=3):
    for i in range(tentativas):
        try:
            req = urllib.request.Request(url, headers=UA)
            with urllib.request.urlopen(req, timeout=60) as r:
                dado = r.read()
            return dado if binario else json.loads(dado)
        except Exception as e:
            if i == tentativas - 1:
                raise
            time.sleep(3 * (i + 1))


def meses(ini, fim):
    a, m = ini.year, ini.month
    while (a, m) <= (fim.year, fim.month):
        yield f"{a:04d}-{m:02d}"
        a, m = (a + 1, 1) if m == 12 else (a, m + 1)


def main(data_ini):
    os.makedirs("pdfs", exist_ok=True)
    os.makedirs("dados", exist_ok=True)
    ini = datetime.date.fromisoformat(data_ini)
    hoje = datetime.date.today()
    conhecidas = {e["id"]: e for e in (json.load(open(ARQ, encoding="utf-8")) if os.path.exists(ARQ) else [])}
    novas = 0
    for mes in meses(ini, hoje):
        for item in get(f"{BASE}/api/diarios/diariosPorDia?data={mes}"):
            if item["id"] in conhecidas:
                continue
            d = get(f"{BASE}/api/diarios/{item['id']}")
            time.sleep(0.2)
            midia = (d.get("midias") or [{}])[0]
            if d.get("situacaoDescricao") != "Publicado" or not midia.get("url"):
                print("ignorada (não publicada ou sem PDF):", d.get("numero"), d.get("situacaoDescricao"))
                continue  # não registra: será reavaliada na próxima execução
            if datetime.date.fromisoformat(d["data"]) < ini:
                continue
            conhecidas[d["id"]] = {
                "id": d["id"], "numero": d["numero"], "data": d["data"],
                "tipo": (d.get("tipo") or {}).get("descricao"), "situacao": d.get("situacaoDescricao"),
                "codigo_icp": d.get("codigo_icp"), "url_pdf": midia["url"], "bytes": midia.get("size"),
            }
            novas += 1
    edicoes = sorted(conhecidas.values(), key=lambda e: (e["data"], int(e["numero"].replace(".", "")), e["id"]))
    for e in edicoes:
        chave = f"{e['numero'].replace('.', '')}_{e['id']}"
        if os.path.exists(f"textos/{chave}.txt") or os.path.exists(f"pdfs/{chave}.pdf"):
            continue
        with open(f"pdfs/{chave}.pdf", "wb") as f:
            f.write(get(e["url_pdf"], binario=True))
        time.sleep(0.3)
    json.dump(edicoes, open(ARQ, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(f"{len(edicoes)} edições conhecidas ({novas} novas)")


if __name__ == "__main__":
    main(sys.argv[1])
