"""Camada de inteligência: cruza cada ato do DOM com as promessas do plano de governo.

Para cada ato: promessas tocadas, estágio do ciclo (normativo/planejamento -> licitação -> contratação -> execução),
leitura analítica causal (usa apenas o que já tinha sido publicado antes do ato) e marcação de "fora do plano".
Saída: dados/atos_inteligencia.jsonl
"""
import json, re, sys, unicodedata, collections

EST_NOME = {0: "Pessoal", 1: "Planejamento", 2: "Licitação", 3: "Contratação", 4: "Execução"}
EST_NORM = {"Normativo": 1}


def norm(s):
    s = unicodedata.normalize("NFD", s or "")
    return "".join(c for c in s if unicodedata.category(c) != "Mn").lower()


RX_EXEC = re.compile(r"ordem de servico|aditivo|apostilamento|medicao|termo de recebimento|inaugur|recebimento (provisorio|definitivo)|fiscal (do|de) contrato|gestor (do )?contrato|designa\w* (de )?fiscal|termo de encerramento|rescisao|distrato|prorrogacao")
RX_CONTR = re.compile(r"contrato n|contrato de gestao|ata de registro|homologa|adjudica|ratifica|extrato de contrato|termo de fomento|termo de colaboracao|convenio|inexigibilidade|termo de cessao|termo de permissao|contratacao direta")
RX_LIC = re.compile(r"edital|pregao|concorrencia|aviso de (licitacao|dispensa|contratacao)|dispensa de licitacao|credenciamento|chamamento|cotacao|aviso de intencao|registro de precos")
RX_PLAN = re.compile(r"grupo de trabalho|estudo tecnico|termo de referencia|consulta publica|audiencia publica|plano (municipal|de)|projeto basico|projeto executivo|comissao especial|institui\w* (o )?(programa|comite|comissao|conselho)")
RX_PESSOAL = re.compile(r"nomear|nomeia|exonera|designa|dispensa|cessao de servidor|substitu\w+|ferias|licenca|readaptacao|aposenta|vacancia")


RX_ORGAO = re.compile(r"(secretaria|secretario) municipal de [a-z, ]{0,70}?(?= no uso| por | em | com | de acordo|,|\.|;|\()|companhia municipal de transito e transporte|fundo municipal de [a-z ]{0,40}|\b(cmtt|secult|semesp|semed|semusa|segov|semad|semap|semec|issa|secom|pgm|cgm)\b|obras, habitacao e urbanismo|habitacao e planejamento urbano")


def limpa(s):
    return RX_ORGAO.sub(" ", s)


def estagio(a):
    t = norm(a["titulo"])
    if a.get("pessoal") and not re.search(r"fiscal|gestor", t + " " + norm((a.get("texto") or "")[:300])):
        return 0
    corpo = norm((a.get("texto") or "")[:1500])
    classe = a["classe"]
    for tx in (t, corpo if classe not in ("Portaria", "Lei", "Decreto") else t + " " + corpo[:400]):
        if RX_EXEC.search(tx): return 4
        if RX_CONTR.search(tx): return 3
        if RX_LIC.search(tx): return 2
        if RX_PLAN.search(tx): return 1
    if classe in ("Lei", "Decreto"): return 1
    if a.get("pessoal"): return 0
    return 1 if classe in ("Portaria", "Resolução") else 2 if (a.get("valor_max") or 0) > 0 else 1


RX_OBJ = re.compile(r"objeto\s*[:\-–]\s*(?:o objeto é\s*)?(.{20,300})", re.I | re.S)
RX_FIM_OBJ = re.compile(r"\s+(?:valor|vigencia|vigência|prazo|fundamento|contratad[ao]|processo|data de|fonte|dotac|signat|órgão|orgao|\d+\.\s)\b", re.I)


def objeto_estruturado(a):
    m = RX_OBJ.search(a.get("texto") or "")
    if not m:
        return None
    o = re.sub(r"\s+", " ", m.group(1))
    f = RX_FIM_OBJ.search(o, 25)
    return (o[:f.start()] if f else o).strip()


def objeto_curto(a):
    t = a.get("texto") or ""
    o = objeto_estruturado(a)
    if o is None:
        o = t[len(a["titulo"]):] if t.startswith(a["titulo"][:30]) else t
        o = re.sub(r"^[\s.\-–]*", "", o)
    o = re.sub(r"\s+", " ", o).strip()
    if re.search(r"(\d{2,3}\s+[A-ZÁ-Ú]{3,}.*){3}", o):
        return "Lista nominal (classificação, convocação ou resultado); nomes omitidos."
    return (o[:230].rsplit(" ", 1)[0] + "…") if len(o) > 230 else o


RX_ROTINA = re.compile(r"medicament|insumo|material (de expediente|hospitalar|de consumo|medico|odontologico|de limpeza|de escritorio|permanente)|combustivel|\bpecas\b|manutencao (preventiva|corretiva|de (veiculos|frota|equipamentos|ar))|locacao de (veiculo|imovel|equipamento|impressora)|outsourcing|\btoner|lei de diretrizes orcamentarias|lei orcamentaria|orcamento (anual|do municipio)|exames? laboratoria|oxigenio|gases medicinais|vigilancia (armada|patrimonial)|gas de cozinha|perfuro|dieta enteral|lavanderia|seguro|assinatura|locacao de maquinas|servicos e procedimentos de assistencia|assistencia a saude|refeic\\w+|alimentacao (hospitalar|prisional)")


def brl(v):
    return "R$ " + f"{v:,.0f}".replace(",", ".") if v is not None else "—"


def data_br(iso):
    return iso[8:] + "/" + iso[5:7]


RX_CTR = re.compile(r"contrato(?: administrativo| de (?:gestao|locacao|obra))?\s*(?:n[ºo°.]*\s*)?(\d{1,4})\s*/\s*(20\d\d)", re.I)


def refs_contrato(a):
    t = norm(a["titulo"] + " " + (a.get("texto") or "")[:600])
    return {f"{int(n)}/{y}" for n, y in RX_CTR.findall(t)}


def processar(entrada, registro_in):
    cfg = json.load(open("config/promessas.json", encoding="utf-8"))
    regras = json.load(open("config/regras.json", encoding="utf-8"))
    corte = regras["valor_corte"]
    prom = {p["id"]: p for p in cfg["promessas"]}
    for p in prom.values():
        p["_rx"] = re.compile(p["regex"])
        p["_dx"] = re.compile(p["direto"]) if p.get("direto") else None
    atos = [json.loads(l) for l in open(entrada, encoding="utf-8")]
    atos.sort(key=lambda a: (a["data"], a["id_edicao"], a["ordem"]))
    registro_out = {}
    estado = {pid: {"n": 0, "max": 0, "ultimo": None, "valor": 0.0, "forn": collections.Counter(), "seis": set()} for pid in prom}
    ciclo_sei = collections.defaultdict(list)
    vistos_valor = set()
    for a in atos:
        oe = objeto_estruturado(a)
        if oe:
            objeto = limpa(norm(a["titulo"]) + " " + norm(oe))
        elif a["classe"] in ("Ata", "Extrato", "Termo", "Contrato", "Errata/Retificação"):
            objeto = ""  # extratos sem campo Objeto trazem endereço/CNPJ do fornecedor: não confiável
        else:
            objeto = limpa(norm(a["titulo"]) + " " + norm((a.get("texto") or "")[:700]))
        a["sem_obj"] = (objeto == "")
        est = estagio(a)
        toca = []
        for pid, p in prom.items():
            if est == 0:
                break
            n = len(list(p["_rx"].finditer(objeto)))
            if n:
                toca.append((n, pid))
        toca.sort(key=lambda x: (-x[0], x[1]))
        todos = [pid for _, pid in toca[:4]]
        a["est"] = est
        a["prom"] = [pid for pid in todos if prom[pid].get("_dx") is None or prom[pid]["_dx"].search(objeto)][:3]
        a["ap"] = [pid for pid in todos if pid not in a["prom"]]
        refs = refs_contrato(a)
        a["herd"] = None
        if not a["prom"] and not a["ap"] and est > 0:
            for r in sorted(refs):
                if r in registro_in:
                    a["prom"] = [registro_in[r]]; a["herd"] = r; a["sem_obj"] = False
                    break
        if a["prom"] and est in (2, 3, 4) and a["herd"] is None and oe:
            for r in refs:
                registro_out.setdefault(r, a["prom"][0])
        # valor contratado (dedupe por SEI+valor), só contratação/execução e fora de Portaria
        vc = None
        if a["classe"] != "Portaria" and est in (3, 4) and a.get("valor_max"):
            chave = (tuple(a.get("sei") or []) or (a["titulo"],), a["valor_max"])
            if chave not in vistos_valor:
                vistos_valor.add(chave); vc = a["valor_max"]
        a["vc"] = vc
        a["fp"] = False
        a["leit"] = None
        a["obj"] = objeto_curto(a)
        a["rot"] = bool(RX_ROTINA.search(norm(a["titulo"]) + " " + norm(a["obj"])))
        sev = a.get("sev")
        pessoal_puro = a.get("pessoal") and est == 0
        # ciclo do processo SEI
        ciclo = []
        for s in a.get("sei") or []:
            ciclo += [x for x in ciclo_sei[s] if x not in ciclo]
        a["ciclo"] = ciclo[-4:]
        if a["prom"] and not pessoal_puro:
            pid = a["prom"][0]; p = prom[pid]; e = estado[pid]
            partes = []
            if a["herd"]:
                partes.append(f"Ato sobre o Contrato nº {a['herd']}, ligado a esta promessa por publicação anterior do mesmo contrato.")
            if e["n"] == 0:
                partes.append("Primeiro ato do DOM ligado a essa promessa desde 03/07.")
            else:
                partes.append(f"{e['n']} ato(s) anteriores desde 03/07; estágio mais avançado até aqui: {EST_NOME[e['max']]}; último movimento em {data_br(e['ultimo'])}.")
            if est > e["max"] and est >= 2:
                partes.append(f"Avança de estágio: {EST_NOME[e['max']]} → {EST_NOME[est]}.")
                if p["base"] in ("risco", "sem_evidencia") and est >= 3:
                    partes.append("Isso contraria a classificação atual de risco/sem evidência; reavaliar o placar.")
            if est == 4:
                partes.append("Instrumento em execução sofre ato de acompanhamento: conferir prazo, acréscimos e se a entrega prometida mantém a data.")
            tit = norm(a["titulo"] + " " + (a.get("texto") or "")[:500])
            if re.search(r"rescisao|distrato|cancelament|revogacao|suspens", tit):
                partes.append("Possível retrocesso: o ato desfaz ou suspende instrumento ligado à promessa.")
            v = a.get("valor_max") if a["classe"] != "Portaria" else None
            if v and v >= corte and est >= 2:
                ref = e["valor"]
                partes.append(f"Valor de {brl(v)}" + (f", {v / (ref + v) * 100:.0f}% do total já citado para a promessa ({brl(ref + v)})." if ref else "; primeiro valor relevante registrado para a promessa."))
            for c in a.get("cnpj") or []:
                if e["forn"][c] >= 2:
                    partes.append(f"O fornecedor {c} já aparece em {e['forn'][c]} atos desta promessa.")
            outras = [prom[x]["nome"] for x in a["prom"][1:]]
            if outras:
                partes.append("Também toca: " + "; ".join(outras) + ".")
            if ciclo:
                partes.append("Mesmo processo SEI aparece antes em: " + "; ".join(f"{data_br(d)} {c}" for d, c in ciclo[-3:]) + ".")
            a["leit"] = " ".join(partes)
        elif a["ap"] and not pessoal_puro and (a.get("valor_max") or 0) >= corte and a["classe"] != "Portaria":
            a["leit"] = f"Custeio ou insumo ligado a «{prom[a['ap'][0]]['nome']}» ({brl(a['valor_max'])}): apoia a política, mas não conta como entrega da promessa."
        elif not a["prom"] and not a["ap"] and not pessoal_puro and not a["sem_obj"] and (a.get("valor_max") or 0) >= corte and a["classe"] != "Portaria" and not RX_ROTINA.search(norm(a["titulo"]) + " " + norm(objeto_curto(a))):
            a["fp"] = True
            if est == 4 and not oe:
                a["leit"] = f"Aditivo, prorrogação ou apostilamento de {brl(a['valor_max'])} cujo objeto não consta neste ato e cujo contrato original não foi publicado desde 03/07. Conferir no SEI a que entrega corresponde e se ela está no plano."
            else:
                a["leit"] = f"Sem ligação com nenhuma promessa do plano. Valor de {brl(a['valor_max'])} (em ata de registro de preços, é teto potencial): verificar se é demanda herdada, contingência ou nova frente de gasto."
        # atualiza estado depois de calcular a leitura (causal)
        for pid in a["prom"]:
            if pessoal_puro:
                continue
            e = estado[pid]
            e["n"] += 1; e["max"] = max(e["max"], est); e["ultimo"] = a["data"]
            if vc: e["valor"] += vc
            for c in a.get("cnpj") or []: e["forn"][c] += 1
        for s in a.get("sei") or []:
            ciclo_sei[s].append((a["data"], a["classe"]))
    return atos, estado, registro_out, prom


def main(entrada="dados/atos_alertas.jsonl", saida="dados/atos_inteligencia.jsonl"):
    _, _, registro, _ = processar(entrada, {})
    atos, estado, _, prom = processar(entrada, registro)
    print(len(registro), "contratos mapeados a promessas;", sum(1 for a in atos if a.get("herd")), "atos herdaram vínculo")
    with open(saida, "w", encoding="utf-8") as f:
        for a in atos:
            f.write(json.dumps(a, ensure_ascii=False) + "\n")
    print(len(atos), "atos;", sum(1 for a in atos if a["prom"]), "ligados ao plano;", sum(1 for a in atos if a["fp"]), "fora do plano")
    for pid, p in prom.items():
        print(f"{pid} {p['nome'][:48]:48} {estado[pid]['n']:4} atos  est.máx {EST_NOME[estado[pid]['max']]:12} valor {brl(estado[pid]['valor'])}")


if __name__ == "__main__":
    main(*sys.argv[1:3])
