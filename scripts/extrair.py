"""Extrai o texto dos PDFs lendo cada página em duas colunas (esquerda, depois direita)."""
import glob, os, re, subprocess

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

def n_imagens(pdf):
    saida = subprocess.run(["pdfimages", "-list", pdf], capture_output=True, text=True).stdout
    return max(0, len(saida.strip().splitlines()) - 2)

def main():
    os.makedirs("textos", exist_ok=True)
    os.makedirs("relatorios", exist_ok=True)
    diag = ["arquivo,paginas,caracteres,caracteres_por_pagina,imagens"]
    for pdf in sorted(glob.glob("pdfs/*.pdf")):
        partes = []
        for n, w, h in paginas(pdf):
            esq = texto(pdf, n, 0, w / 2, h)
            dire = texto(pdf, n, w / 2, w / 2, h)
            partes.append(f"=== PÁGINA {n} ===\n{esq}\n--- coluna direita ---\n{dire}")
        destino = "textos/" + os.path.basename(pdf).replace(".pdf", ".txt")
        with open(destino, "w", encoding="utf-8") as f:
            f.write("\n".join(partes))
        chars = sum(len(p) for p in partes)
        diag.append(f"{os.path.basename(pdf)},{len(partes)},{chars},{chars // max(1, len(partes))},{n_imagens(pdf)}")
        print(destino, len(partes), "páginas")
    open("relatorios/diagnostico_pdfs.csv", "w").write("\n".join(diag) + "\n")

if __name__ == "__main__":
    main()
