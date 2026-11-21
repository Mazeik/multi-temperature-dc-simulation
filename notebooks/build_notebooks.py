"""Converte os roteiros notebooks/src/*.py em notebooks .ipynb executados (com saídas).

Por quê: arquivos .py são fáceis de revisar no Git; o .ipynb com saídas é o que
aparece bonito no GitHub (gráficos e tabelas renderizados).

Formato dos roteiros: células separadas por linhas "# %%" (código) ou
"# %% [markdown]" (texto; cada linha começa com "# ").

Uso:
    python notebooks/build_notebooks.py            # todos
    python notebooks/build_notebooks.py 04a        # só os que contêm "04a" no nome
"""
import sys
from pathlib import Path

import nbformat
from nbclient import NotebookClient

PASTA = Path(__file__).resolve().parent
FONTES = PASTA / "src"


def ler_celulas(texto):
    """Divide o roteiro em células (tipo, conteúdo)."""
    celulas, tipo, linhas = [], None, []
    for linha in texto.splitlines():
        if linha.startswith("# %%"):
            if tipo is not None:
                celulas.append((tipo, linhas))
            tipo = "markdown" if "[markdown]" in linha else "code"
            linhas = []
        else:
            linhas.append(linha)
    if tipo is not None:
        celulas.append((tipo, linhas))

    nb_cells = []
    for tipo, linhas in celulas:
        conteudo = "\n".join(linhas).strip("\n")
        if not conteudo.strip():
            continue
        if tipo == "markdown":
            # remove o "# " do começo de cada linha de texto
            conteudo = "\n".join(l[2:] if l.startswith("# ") else l.lstrip("#") for l in conteudo.splitlines())
            nb_cells.append(nbformat.v4.new_markdown_cell(conteudo))
        else:
            nb_cells.append(nbformat.v4.new_code_cell(conteudo))
    return nb_cells


def main():
    filtro = sys.argv[1] if len(sys.argv) > 1 else ""
    for fonte in sorted(FONTES.glob("*.py")):
        if filtro not in fonte.stem:
            continue
        nb = nbformat.v4.new_notebook()
        nb.cells = ler_celulas(fonte.read_text(encoding="utf-8"))
        nb.metadata["kernelspec"] = {"name": "python3", "display_name": "Python 3", "language": "python"}
        print(f"Executando {fonte.name} ...")
        NotebookClient(nb, timeout=900, kernel_name="python3",
                       resources={"metadata": {"path": str(PASTA)}}).execute()
        destino = PASTA / f"{fonte.stem}.ipynb"
        nbformat.write(nb, destino)
        print(f"  -> {destino.name}")


if __name__ == "__main__":
    main()
