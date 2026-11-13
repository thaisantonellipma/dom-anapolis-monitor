"""Aplica as regras de alerta (config/regras.json) aos atos e gera o resumo diário."""
import collections, datetime, json, re, statistics, sys, unicodedata

ORDEM = {"ALTA": 3, "MEDIA": 2, "ACOMPANHAR": 1}

def norm(s):
    s = unicodedata.normalize("NFKD", s or "")
    return "".join(c for c in s if not unicodedata.combining(c)).lower()

def brl(v):
    return "R$ " + f"{v:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

def avalia(a, cfg):
    t = norm(a["titulo"] + " " + a["texto"])
    ementa = norm(a["texto"][:700])
    r = []
    def add(regra, sev, motivo):
        r.append({"regra": regra, "sev": sev, "motivo": motivo})
    if re.search(cfg["controle"], norm(a["titulo"]) + " " + ementa):
        add("Controle", "ALTA", "Sindicância, processo disciplinar, penalidade ou apuração")
    v = a["valor_max"]
    if v and a["classe"] != "Portaria":
        if v >= cfg["valor_alto"]:
            add("Valor", "ALTA", f"{brl(v)}, acima do corte alto de {brl(cfg['valor_alto'])}")
        elif v >= cfg["valor_corte"]:
            add("Valor", "MEDIA", f"{brl(v)}, acima do corte de {brl(cfg['valor_corte'])}")
    if re.search(cfg["contratacao_direta"], t) and a["classe"] != "Portaria":
        sev = "ALTA" if v and v >= cfg["valor_corte"] else "MEDIA"
        add("Contratação direta", sev, "Dispensa, inexigibilidade, emergência ou credenciamento")
    if re.search(cfg["aditivo"], norm(a["titulo"]) + " " + ementa) and a["classe"] != "Portaria":
        pct = [float(x.replace(",", ".")) for x in re.findall(r"(?:acrescimo|supressao)[^%]{0,80}?(\d{1,3}(?:,\d+)?)\s*%", t)]
        if pct and max(pct) >= cfg["aditivo_percentual_alto"]:
            add("Aditivo", "ALTA", f"Aditivo/acréscimo de {max(pct):g}% (limite de referência {cfg['aditivo_percentual_alto']}%)")
        else:
            add("Aditivo", "MEDIA", "Aditivo, prorrogação, reajuste ou repactuação")
    if re.search(cfg["cancelamento"], norm(a["titulo"]) + " " + ementa) and a["classe"] in ("Aviso", "Extrato", "Ata", "Termo", "Edital"):
        add("Cancelamento", "MEDIA", "Cancelamento, suspensão, revogação ou licitação fracassada")
    if a["classe"] == "Errata/Retificação":
        add("Retificação", "MEDIA", "Errata ou retificação de ato já publicado")
    if a["classe"] == "Portaria" and re.search(cfg["cargo_estrategico"], ementa):
        add("Cargo estratégico", "MEDIA", "Nomeação, designação ou exoneração em cargo de direção")
    if re.search(cfg["temporario"], t):
        add("Contratação temporária", "MEDIA", "Contratação temporária ou processo seletivo simplificado")
    if a["tipo_edicao"] and "Di" not in a["tipo_edicao"][:2]:
        add("Edição extra", "ACOMPANHAR", f"Publicado em {a['tipo_edicao']}")
    objeto = norm(a["titulo"]) + " " + norm(a["texto"][:900])   # só título e objeto, não cláusulas-padrão
    prior = [nome for nome, rx in cfg["prioridades"].items() if re.search(rx, objeto)]
    for p in prior:
        add("Prioridade de governo", "ACOMPANHAR", p)
    a["prioridades"] = prior
    a["pessoal"] = a["classe"] == "Portaria" and bool(re.search(cfg["pessoal_movimento"], ementa))
    a["alertas"] = r
    a["sev"] = max((x["sev"] for x in r), key=lambda s: ORDEM[s], default="")
    return a

def main(entrada="dados/atos.jsonl", saida="dados/atos_alertas.jsonl"):
    cfg = json.load(open("config/regras.json", encoding="utf-8"))
    atos = [avalia(json.loads(l), cfg) for l in open(entrada, encoding="utf-8")]
    # fornecedor repetido (mesmo CNPJ em vários atos na janela)
    por_cnpj = collections.defaultdict(list)
    for a in atos:
        for c in a["cnpj"]:
            por_cnpj[c].append(a)
    for c, lista in por_cnpj.items():
        for a in lista:
            d0 = datetime.date.fromisoformat(a["data"])
            vizinhos = {x["ordem"] and (x["id_edicao"], x["ordem"]) for x in lista
                        if abs((datetime.date.fromisoformat(x["data"]) - d0).days) <= cfg["fornecedor_repetido_janela_dias"]}
            if len(vizinhos) >= cfg["fornecedor_repetido_min_atos"] and a["classe"] != "Portaria":
                a["alertas"].append({"regra": "Fornecedor recorrente", "sev": "MEDIA",
                                     "motivo": f"CNPJ {c} aparece em {len(vizinhos)} atos em {cfg['fornecedor_repetido_janela_dias']} dias"})
                if ORDEM["MEDIA"] > ORDEM.get(a["sev"], 0):
                    a["sev"] = "MEDIA"
    # resumo diário + alerta de volume de pessoal
    dias = collections.defaultdict(list)
    for a in atos:
        dias[a["data"]].append(a)
    resumo = {}
    for d in sorted(dias):
        xs = dias[d]
        resumo[d] = {"data": d, "edicoes": sorted({f"{x['edicao']} ({x['tipo_edicao']})" for x in xs}),
                     "atos": len(xs), "pessoal": sum(x["pessoal"] for x in xs),
                     "alta": sum(x["sev"] == "ALTA" for x in xs), "media": sum(x["sev"] == "MEDIA" for x in xs),
                     "valor_citado": sum(x["valor_max"] or 0 for x in xs if x["classe"] != "Portaria"),
                     "alertas_dia": []}
    anteriores = []
    for d in sorted(resumo):
        r = resumo[d]
        n_controle = sum(any(al["regra"] == "Controle" for al in x["alertas"]) for x in dias[d])
        if n_controle >= 3:
            r["alertas_dia"].append({"regra": "Controle em lote", "sev": "ALTA",
                "motivo": f"{n_controle} sindicâncias, processos disciplinares ou decisões de controle publicados no mesmo dia"})
        if len(anteriores) >= 5:
            media = statistics.mean(anteriores[-20:])
            if r["pessoal"] >= cfg["pessoal_dia_limiar_minimo"] and r["pessoal"] >= cfg["pessoal_dia_fator_media"] * media:
                r["alertas_dia"].append({"regra": "Volume de pessoal", "sev": "MEDIA",
                    "motivo": f"{r['pessoal']} movimentações de pessoal no dia (média recente {media:.0f})"})
        anteriores.append(r["pessoal"])
    with open(saida, "w", encoding="utf-8") as f:
        for a in atos:
            f.write(json.dumps(a, ensure_ascii=False) + "\n")
    json.dump(resumo, open("dados/resumo_diario.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(len(atos), "atos avaliados")

if __name__ == "__main__":
    main(*sys.argv[1:3])
