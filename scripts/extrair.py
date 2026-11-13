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

def main():
    os.makedirs("textos", exist_ok=True)
    for pdf in sorted(glob.glob("pdfs/*.pdf")):
        partes = []
        for n, w, h in paginas(pdf):
            esq = texto(pdf, n, 0, w / 2, h)
            dire = texto(pdf, n, w / 2, w / 2, h)
            partes.append(f"=== PÁGINA {n} ===\n{esq}\n--- coluna direita ---\n{dire}")
        destino = "textos/" + os.path.basename(pdf).replace(".pdf", ".txt")
        with open(destino, "w", encoding="utf-8") as f:
            f.write("\n".join(partes))
        print(destino, len(partes), "páginas")

if __name__ == "__main__":
    main()
