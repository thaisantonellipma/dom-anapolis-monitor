"""Separa o texto de cada edição em atos e extrai campos (instrumento, órgão, SEI, valores, CNPJ)."""
import glob, json, os, re, sys, unicodedata

SEI = re.compile(r"\d{5}\.\d{8}/\d{4}-\d{2}")
CNPJ = re.compile(r"\d{2}\.\d{3}\.\d{3}/\d{4}-\d{2}")
VALOR = re.compile(r"R\$\s*([\d.]+,\d{2})")
NUM = re.compile(r"N[º°o]\s*\.?\s*([\d.]+)\s*/\s*(\d{4})", re.I)

RODAPE = re.compile(r"equivalente ao publicado|site dom\.anapolis|c[oó]digo de valida", re.I)
CABECALHO = re.compile(r"^(DI[ÁA]RIO OFICIAL|An[áa]polis, \d{1,2} de \w+ de \d{4}.*|=== P[ÁA]GINA \d+ ===|--- coluna direita ---)$")
TIT_NUMERADO = re.compile(r"^(Portaria|PORTARIA|Decreto|DECRETO|Lei Complementar|LEI COMPLEMENTAR|Lei Ordin[áa]ria|LEI ORDIN[ÁA]RIA|Lei|LEI|Resolu[çc][ãa]o|RESOLU[ÇC][ÃA]O)\s+(?:[A-Za-z]{2,12}\s+)?N[º°o]\s*\.?\s*\d")
TIT_MAIUSCULO = re.compile(r"^(EXTRATOS?|EDITAL|TERMO|ATA|AVISO|ERRATA|RETIFICA[ÇC][ÃA]O|CONVOCA[ÇC][ÃA]O|HOMOLOGA[ÇC][ÃA]O|RATIFICA[ÇC][ÃA]O|COMUNICADO|DESPACHO|PORTARIA|DECRETO|RESOLU[ÇC][ÃA]O|LEI)\b")
# rótulos que só são título quando trazem número (senão são campos dentro de um extrato)
TIT_COM_NUMERO = re.compile(r"^(CONTRATO|CONV[ÊE]NIO|CREDENCIAMENTO|INEXIGIBILIDADE|DISPENSA)\b.*N[º°o]\s*\d")

ORGAOS = [
    (r"secretaria municipal de sa[úu]de|semusa|fundo municipal de sa[úu]de", "SEMUSA (Saúde)"),
    (r"secretaria municipal de educa[çc][ãa]o|semed\b|fundo municipal de educa[çc][ãa]o", "SEMED (Educação)"),
    (r"administra[çc][ãa]o, gest[ãa]o de pessoas|semad\b", "SEMAD (Administração e Pessoas)"),
    (r"controladoria[- ]geral|\bcgm\b", "CGM (Controladoria)"),
    (r"instituto de seguridade|\bissa\b", "ISSA (Previdência)"),
    (r"procuradoria[- ]geral|\bpgm\b", "PGM (Procuradoria)"),
    (r"secretaria municipal de governo|segov\b", "SEGOV (Governo)"),
    (r"secretaria municipal de comunica[çc][ãa]o|secom\b", "SECOM (Comunicação)"),
    (r"secretaria municipal de cultura", "Cultura e Turismo"),
    (r"assist[êe]ncia e pol[íi]ticas sociais|assist[êe]ncia social", "Assistência Social"),
    (r"secretaria municipal de obras|semop|infraestrutura", "Obras e Infraestrutura"),
    (r"habita[çc][ãa]o|semohpuma|meio ambiente", "Habitação, Urbanismo e Meio Ambiente"),
    (r"companhia municipal de tr[âa]nsito|\bcmtt\b", "CMTT (Trânsito)"),
    (r"ag[êe]ncia reguladora|\barm\b", "ARM (Regulação)"),
    (r"gabinete do prefeito|o prefeito de an[áa]polis", "Gabinete do Prefeito"),
]

ORGAO_CAB = re.compile(r"^(GABINETE|SECRETARIA|CONTROLADORIA|C[ÂA]MARA|PROCURADORIA|INSTITUTO|COMPANHIA|AG[ÊE]NCIA|FUNDO|FUNDA[ÇC][ÃA]O|CONSELHO|SERVI[ÇC]O|AUTARQUIA|PMA)\b[A-ZÇÃÕÉÊÍÓÚÂ ,.\-–/]+$")

def norm(s):
    s = unicodedata.normalize("NFKD", s or "")
    return "".join(c for c in s if not unicodedata.combining(c)).lower()

def valor_para_float(txt):
    return float(txt.replace(".", "").replace(",", "."))

def linhas_limpas(texto):
    saida = []
    for bruta in texto.splitlines():
        l = bruta.strip()
        if not l or CABECALHO.match(l) or RODAPE.search(l):
            continue
        saida.append(l)
    return saida

def eh_titulo(l):
    if re.search(r"\.{5,}", l):  # linha do sumário
        return False
    if TIT_NUMERADO.match(l):
        return True
    if not (len(l) <= 170 and l == l.upper()):
        return False
    return bool(TIT_MAIUSCULO.match(l) or TIT_COM_NUMERO.match(l))

def classe(titulo):
    t = norm(titulo)
    for k, v in (("portaria", "Portaria"), ("decreto", "Decreto"), ("lei", "Lei"), ("resolucao", "Resolução"),
                 ("extrato", "Extrato"), ("edital", "Edital"), ("termo", "Termo"), ("ata", "Ata"),
                 ("aviso", "Aviso"), ("errata", "Errata/Retificação"), ("retifica", "Errata/Retificação"),
                 ("contrato", "Contrato"), ("convenio", "Convênio")):
        if t.startswith(k):
            return v
    return "Outros"

def orgao(texto):
    t = norm(texto[:1200])
    for padrao, nome in ORGAOS:
        if re.search(padrao, t):
            return nome
    return "Não identificado"

def segmentar(arquivo, meta):
    linhas = linhas_limpas(open(arquivo, encoding="utf-8").read())
    atos, atual, cab = [], None, None
    for i, l in enumerate(linhas):
        if ORGAO_CAB.match(l) and len(l) <= 110 and not re.search(r"\d", l) and not TIT_MAIUSCULO.match(l):
            cab = l.strip(" -–")
            continue
        # título do sumário que quebrou de linha: o pontilhado aparece na linha seguinte
        no_sumario = any(re.search(r"\.{5,}", x) for x in linhas[i + 1:i + 3]) and not re.search(r"\.{5,}", l) and len(l) < 80 and l == l.upper()
        if eh_titulo(l) and not no_sumario:
            atual = {"titulo": l, "linhas": [l], "cab": cab}
            atos.append(atual)
        elif atual is not None:
            atual["linhas"].append(l)
    if not atos and linhas:  # edição sem título reconhecível (ex.: resultados em tabela)
        atos = [{"titulo": linhas[min(5, len(linhas) - 1)][:160], "linhas": linhas, "cab": cab}]
    saida = []
    for i, a in enumerate(atos, 1):
        corpo = " ".join(a["linhas"])
        m = NUM.search(a["titulo"]) or NUM.search(corpo[:300])
        valores = [valor_para_float(v) for v in VALOR.findall(corpo)]
        saida.append({
            "edicao": meta["numero"], "tipo_edicao": meta["tipo"], "data": meta["data"],
            "id_edicao": meta["id"], "url_pdf": meta["url_pdf"], "ordem": i,
            "classe": classe(a["titulo"]), "titulo": a["titulo"][:200],
            "instrumento": f"{m.group(1)}/{m.group(2)}" if m else None,
            "orgao": a.get("cab") or orgao(corpo), "sei": sorted(set(SEI.findall(corpo))),
            "cnpj": sorted(set(CNPJ.findall(corpo))),
            "valor_max": max(valores) if valores else None,
            "valores": sorted(set(valores), reverse=True)[:5],
            "texto": corpo[:6000], "excerto": corpo[:420],
        })
    return saida

def main(pasta="textos", saida="dados/atos.jsonl"):
    edicoes = {f"{e['numero'].replace('.', '')}_{e['id']}": e
               for e in json.load(open("dados/edicoes.json", encoding="utf-8"))}
    todos = []
    for arq in sorted(glob.glob(f"{pasta}/*.txt")):
        chave = os.path.basename(arq)[:-4]
        if chave in edicoes:
            todos += segmentar(arq, edicoes[chave])
    with open(saida, "w", encoding="utf-8") as f:
        for a in todos:
            f.write(json.dumps(a, ensure_ascii=False) + "\n")
    print(len(todos), "atos")

if __name__ == "__main__":
    main(*sys.argv[1:3])
