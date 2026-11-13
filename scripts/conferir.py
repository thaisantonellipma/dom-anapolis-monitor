"""Teste de aceite 2: confere se os atos do histórico aparecem no texto extraído da edição correta."""
import csv, os, re, unicodedata, collections
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
    caminho = f"textos/{ed.replace('.', '')}.txt"
    return norm(open(caminho, encoding="utf-8").read()) if os.path.exists(caminho) else None

def acha_instrumento(texto, instr):
    palavra = norm(instr).split()[0] if instr else ""
    kw = KW.get(palavra, re.escape(palavra))
    for n, a in re.findall(r"(\d{1,5})\s*/\s*(\d{4})", instr or ""):
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
            elif not seis and not re.search(r"\d+\s*/\s*\d{4}", instr or ""):
                status = "sem_identificador(conferir_manual)"
            else:
                status = "NAO_ACHADO"
        cont[status.split("_")[0] if status.startswith("achado") else status] += 1
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
            if r[5] == "NAO_ACHADO" or r[5] == "edicao_nao_coletada":
                f.write(f"- ed. {r[0]} | {r[1]} | {r[3]} | SEI: {r[4]} | {r[5]}\n")
    print(open("relatorios/teste2_resumo.md", encoding="utf-8").read())

if __name__ == "__main__":
    main()
