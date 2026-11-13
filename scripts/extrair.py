"""Extrai o texto dos PDFs lendo cada página em duas colunas (esquerda, depois direita)."""
import glob, os, re, subprocess, sys

def paginas(pdf):
    saida = subprocess.run(["pdfinfo", "-f", "1", "-l", "9999", pdf],
                           capture_output=True, text=True).stdout
    return [(int(n), float(w), float(h))
            for n, w, h in re.findall(r"Page\s+(\d+) size:\s+([\d.]+) x ([\d.]+)", saida)]

def texto(pdf, n, x, largura, altura):
    return subprocess.run(
        ["pdftotext", "-f", str(n), "-l", str(n), "-x", str(int(x)), "-y", "0",
         "-W", str(int(largura)), "-H", str(int(altura)), "-layout", pdf, "-"],
        capture_output=True, text=True).stdout

def texto_auto(pdf, n):
    """Ordem de leitura detectada pelo próprio pdftotext (sem -layout)."""
    return subprocess.run(["pdftotext", "-f", str(n), "-l", str(n), pdf, "-"],
                          capture_output=True, text=True).stdout

def n_imagens(pdf):
    saida = subprocess.run(["pdfimages", "-list", pdf], capture_output=True, text=True).stdout
    return max(0, len(saida.strip().splitlines()) - 2)

def main(modo="colunas", destino_dir="textos"):
    os.makedirs(destino_dir, exist_ok=True)
    os.makedirs("relatorios", exist_ok=True)
    diag = ["arquivo,paginas,caracteres,caracteres_por_pagina,imagens"]
    for pdf in sorted(glob.glob("pdfs/*.pdf")):
        destino = f"{destino_dir}/" + os.path.basename(pdf).replace(".pdf", ".txt")
        if os.path.exists(destino) and modo == "colunas" and destino_dir == "textos":
            continue  # execução incremental: edição já extraída
        partes = []
        for n, w, h in paginas(pdf):
            if modo == "auto":
                partes.append(f"=== PÁGINA {n} ===\n{texto_auto(pdf, n)}")
            else:
                esq = texto(pdf, n, 0, w / 2, h)
                dire = texto(pdf, n, w / 2, w / 2, h)
                partes.append(f"=== PÁGINA {n} ===\n{esq}\n--- coluna direita ---\n{dire}")
        with open(destino, "w", encoding="utf-8") as f:
            f.write("\n".join(partes))
        chars = sum(len(p) for p in partes)
        diag.append(f"{os.path.basename(pdf)},{len(partes)},{chars},{chars // max(1, len(partes))},{n_imagens(pdf)}")
        print(destino, len(partes), "páginas")
    if modo == "colunas":
        open("relatorios/diagnostico_pdfs.csv", "w").write("\n".join(diag) + "\n")

if __name__ == "__main__":
    main(*(sys.argv[1:3]))
