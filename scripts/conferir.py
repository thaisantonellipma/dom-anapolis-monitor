"""Teste de aceite 2: confere se os atos do histórico aparecem no texto extraído da edição correta."""
import csv, glob, os, re, unicodedata, collections
import openpyxl

SEI = re.compile(r"\d{5}\.\d{8}/\d{4}-\d{2}")
KW = {"arp": r"registro de pre|arp|ata", "portaria": "portaria", "convenio": "conv",
      "contrato": "contrato", "decreto": "decreto", "termo": "termo", "edital": "edital",
      "pregao": "preg", "ata": "ata", "resolucao": "resolu", "lei": "lei"}

def norm(s):
    s = unicodedata.normalize("NFKD", s or "")
    s = "".join(c for c in s if not unicodedata.combining(c)).lower()
    s = re.sub(r"[‐-―−]", "-", s)
    return re.sub(r"[ \t]+", " ", s)

def le_texto(ed):
    arquivos = sorted(glob.glob(f"textos/{ed.replace('.', '')}_*.txt"))
    if not arquivos:
        return None
    return norm("\n".join(open(a, encoding="utf-8").read() for a in arquivos))

STOP = set("sobre para entre ainda outros outras ajustes ato atos aproximadamente processo processos secretaria municipal programa".split())

def por_palavras(texto, assunto):
    tokens = [t for t in re.findall(r"[a-z0-9]{5,}", norm(assunto)) if t not in STOP]
    if len(tokens) < 2:
        return False
    return sum(t in texto for t in tokens) / len(tokens) >= 0.6

def acha_instrumento(texto, instr):
    palavra = norm(instr).split()[0] if instr else ""
    kw = KW.get(palavra, re.escape(palavra))
    for lista, a in re.findall(r"(\d{1,5}(?:\s*(?:,|e)\s*\d{1,5})*)\s*/\s*(\d{4})", instr or ""):
        for n in re.findall(r"\d{1,5}", lista):
            if re.search(kw + r"[\s\S]{0,80}?\b0*" + n + r"\s*/\s*" + a, texto):
                return True
    return False

def main():
    wb = openpyxl.load_workbook("historico/Historico_Monitoramento_DOM_Anapolis.xlsx")
    linhas = list(wb["Atos monitorados"].iter_rows(min_row=2, values_only=True))
    res, cont = [], collections.Counter()
    seis_planilha = collections.defaultdict(set)
    for ed, sec, cat, assunto, instr, sei, valor, *_ in linhas:
        texto = le_texto(ed)
        seis = SEI.findall(sei or "")
        seis_planilha[ed].update(seis)
        if texto is None:
            status = "edicao_nao_coletada"
        else:
            por_sei = any(s in texto for s in seis)
            por_instr = acha_instrumento(texto, instr)
            if por_sei or por_instr:
                status = "achado_" + "+".join(x for x, ok in (("sei", por_sei), ("instrumento", por_instr)) if ok)
            elif por_palavras(texto, assunto):
                status = "achado_provavel_por_palavras"
            elif not seis and not re.search(r"\d+\s*/\s*\d{4}", instr or ""):
                status = "sem_identificador_nao_achado(conferir_manual)"
            else:
                status = "NAO_ACHADO"
        cont[status] += 1
        res.append([ed, sec, assunto, instr, sei, status])
    os.makedirs("relatorios", exist_ok=True)
    with open("relatorios/teste2_conferencia.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f); w.writerow(["edicao", "secretaria", "assunto", "instrumento", "sei", "status"]); w.writerows(res)
    eds = sorted({r[0] for r in res})
    novos = []
    for ed in eds:
        t = le_texto(ed)
        if t is None: continue
        todos = set(SEI.findall(t))
        novos.append((ed, len(todos), len(todos - seis_planilha[ed])))
    with open("relatorios/teste2_resumo.md", "w", encoding="utf-8") as f:
        f.write(f"# Teste 2 - conferência do histórico ({len(res)} atos)\n\n")
        for k, v in cont.most_common(): f.write(f"- {k}: {v}\n")
        f.write("\n## Processos SEI no texto vs. planilha, por edição\n\n| edição | SEI distintos no texto | não estavam na planilha |\n|---|---|---|\n")
        for ed, n, nn in novos: f.write(f"| {ed} | {n} | {nn} |\n")
        f.write("\n## Não achados\n\n")
        for r in res:
            if r[5] in ("NAO_ACHADO", "edicao_nao_coletada") or r[5].startswith("sem_identificador"):
                f.write(f"- ed. {r[0]} | {r[1]} | {r[3]} | SEI: {r[4]} | {r[5]}\n")
    print(open("relatorios/teste2_resumo.md", encoding="utf-8").read())

if __name__ == "__main__":
    main()
