import cv2
import numpy as np
from pathlib import Path


# ==========================================================
# CONFIGURAÇÃO
# ==========================================================

BASE_DIR = Path(__file__).resolve().parent.parent

C_RESULTS_DIR = BASE_DIR / "src" / "results" / "c"
KORNIA_RESULTS_DIR = BASE_DIR / "src" / "results" / "kornia"

# Quantas diferenças mostrar por imagem
MAX_DIFERENCAS_EXIBIDAS = 10


# ==========================================================
# COMPARAÇÃO DE UMA IMAGEM
# ==========================================================

def comparar_imagens(arquivo_c, arquivo_python):

    imagem_c = cv2.imread(
        str(arquivo_c),
        cv2.IMREAD_GRAYSCALE
    )

    imagem_python = cv2.imread(
        str(arquivo_python),
        cv2.IMREAD_GRAYSCALE
    )

    if imagem_c is None:
        raise RuntimeError(
            f"Não foi possível abrir a saída do C: {arquivo_c}"
        )

    if imagem_python is None:
        raise RuntimeError(
            f"Não foi possível abrir a saída Python: {arquivo_python}"
        )

    # ------------------------------------------------------
    # Verificar dimensões
    # ------------------------------------------------------

    if imagem_c.shape != imagem_python.shape:
        return {
            "status": "DIMENSOES_DIFERENTES",
            "shape_c": imagem_c.shape,
            "shape_python": imagem_python.shape,
        }

    # ------------------------------------------------------
    # Diferença absoluta pixel a pixel
    # ------------------------------------------------------

    diferenca = np.abs(
        imagem_python.astype(np.int16)
        - imagem_c.astype(np.int16)
    )

    # ------------------------------------------------------
    # Estatísticas
    # ------------------------------------------------------

    total_pixels = diferenca.size

    pixels_iguais = np.sum(diferenca == 0)

    pixels_diferentes = np.sum(diferenca != 0)

    maior_diferenca = np.max(diferenca)

    diferenca_media = np.mean(diferenca)

    percentual_iguais = (
        pixels_iguais / total_pixels * 100
    )

    percentual_diferentes = (
        pixels_diferentes / total_pixels * 100
    )

    # ------------------------------------------------------
    # Primeiras diferenças
    # ------------------------------------------------------

    primeiras_diferencas = []

    if pixels_diferentes > 0:

        indices = np.argwhere(diferenca != 0)

        for i, j in indices[:MAX_DIFERENCAS_EXIBIDAS]:

            primeiras_diferencas.append(
                (
                    int(i),
                    int(j),
                    int(imagem_c[i, j]),
                    int(imagem_python[i, j]),
                    int(diferenca[i, j])
                )
            )

    return {
        "status": "PASSOU" if pixels_diferentes == 0 else "FALHOU",
        "shape": imagem_c.shape,
        "total_pixels": total_pixels,
        "pixels_iguais": pixels_iguais,
        "pixels_diferentes": pixels_diferentes,
        "maior_diferenca": maior_diferenca,
        "diferenca_media": diferenca_media,
        "percentual_iguais": percentual_iguais,
        "percentual_diferentes": percentual_diferentes,
        "primeiras_diferencas": primeiras_diferencas,
    }


# ==========================================================
# MAIN
# ==========================================================

def main():

    # ------------------------------------------------------
    # Verificar diretórios
    # ------------------------------------------------------

    if not C_RESULTS_DIR.exists():
        raise RuntimeError(
            f"Diretório não encontrado: {C_RESULTS_DIR}"
        )

    if not KORNIA_RESULTS_DIR.exists():
        raise RuntimeError(
            f"Diretório não encontrado: {KORNIA_RESULTS_DIR}"
        )

    # ------------------------------------------------------
    # Encontrar imagens
    # ------------------------------------------------------

    imagens_c = {
        arquivo.name: arquivo
        for arquivo in C_RESULTS_DIR.glob("*.pgm")
    }

    imagens_python = {
        arquivo.name: arquivo
        for arquivo in KORNIA_RESULTS_DIR.glob("*.pgm")
    }

    nomes_c = set(imagens_c.keys())
    nomes_python = set(imagens_python.keys())

    nomes_comuns = sorted(nomes_c & nomes_python)

    somente_c = sorted(nomes_c - nomes_python)
    somente_python = sorted(nomes_python - nomes_c)

    # ------------------------------------------------------
    # Cabeçalho
    # ------------------------------------------------------

    print()
    print("=" * 70)
    print("                 VALIDAÇÃO UNSHARP MASK")
    print("=" * 70)

    print(f"Imagens C:       {len(imagens_c)}")
    print(f"Imagens Python:  {len(imagens_python)}")
    print(f"Imagens comuns:  {len(nomes_comuns)}")

    # ------------------------------------------------------
    # Arquivos sem correspondente
    # ------------------------------------------------------

    if somente_c:

        print("\n⚠ Imagens presentes apenas no C:")

        for nome in somente_c:
            print(f"   - {nome}")

    if somente_python:

        print("\n⚠ Imagens presentes apenas no Python:")

        for nome in somente_python:
            print(f"   - {nome}")

    if not nomes_comuns:

        print("\nNenhuma imagem correspondente encontrada.")
        return

    # ------------------------------------------------------
    # Estatísticas gerais
    # ------------------------------------------------------

    total_testes = len(nomes_comuns)
    testes_passaram = 0
    testes_falharam = 0

    total_pixels = 0
    total_pixels_iguais = 0
    total_pixels_diferentes = 0

    maior_diferenca_global = 0

    # ------------------------------------------------------
    # Comparar imagens
    # ------------------------------------------------------

    print()
    print("-" * 70)
    print("RESULTADOS")
    print("-" * 70)

    for numero, nome in enumerate(nomes_comuns, start=1):

        arquivo_c = imagens_c[nome]
        arquivo_python = imagens_python[nome]

        resultado = comparar_imagens(
            arquivo_c,
            arquivo_python
        )

        print(
            f"\n[{numero:02d}/{total_testes:02d}] {nome}"
        )

        # --------------------------------------------------
        # Dimensões diferentes
        # --------------------------------------------------

        if resultado["status"] == "DIMENSOES_DIFERENTES":

            print("      DIMENSÕES DIFERENTES")
            print(f"     C:      {resultado['shape_c']}")
            print(f"     Python: {resultado['shape_python']}")

            testes_falharam += 1

            continue

        # --------------------------------------------------
        # Resultado
        # --------------------------------------------------

        if resultado["status"] == "PASSOU":

            print("      PASSOU")

            testes_passaram += 1

        else:

            print("      FALHOU")

            testes_falharam += 1

        # --------------------------------------------------
        # Estatísticas
        # --------------------------------------------------

        altura, largura = resultado["shape"]

        print(
            f"     Dimensões: {largura} x {altura}"
        )

        print(
            f"     Pixels: {resultado['total_pixels']:,}"
        )

        print(
            f"     Iguais: {resultado['pixels_iguais']:,} "
            f"({resultado['percentual_iguais']:.4f}%)"
        )

        print(
            f"     Diferentes: {resultado['pixels_diferentes']:,} "
            f"({resultado['percentual_diferentes']:.4f}%)"
        )

        print(
            f"     Maior diferença: "
            f"{resultado['maior_diferenca']}"
        )

        print(
            f"     Diferença média: "
            f"{resultado['diferenca_media']:.6f}"
        )

        # --------------------------------------------------
        # Atualizar estatísticas globais
        # --------------------------------------------------

        total_pixels += resultado["total_pixels"]

        total_pixels_iguais += resultado["pixels_iguais"]

        total_pixels_diferentes += (
            resultado["pixels_diferentes"]
        )

        maior_diferenca_global = max(
            maior_diferenca_global,
            resultado["maior_diferenca"]
        )

        # --------------------------------------------------
        # Mostrar diferenças
        # --------------------------------------------------

        if resultado["pixels_diferentes"] > 0:

            print(
                f"\n     Primeiras "
                f"{len(resultado['primeiras_diferencas'])} diferenças:"
            )

            for (
                i,
                j,
                valor_c,
                valor_python,
                diferenca
            ) in resultado["primeiras_diferencas"]:

                print(
                    f"       [{i:4d}, {j:4d}] "
                    f"C={valor_c:3d} | "
                    f"Python={valor_python:3d} | "
                    f"Δ={diferenca:3d}"
                )

    # ======================================================
    # RESUMO FINAL
    # ======================================================

    percentual_global = (
        total_pixels_iguais / total_pixels * 100
        if total_pixels > 0
        else 0
    )

    print()
    print("=" * 70)
    print("                         RESUMO")
    print("=" * 70)

    print(
        f"Testes realizados:       {total_testes}"
    )

    print(
        f"Testes aprovados:        {testes_passaram}"
    )

    print(
        f"Testes com diferenças:   {testes_falharam}"
    )

    print(
        f"Total de pixels:         {total_pixels:,}"
    )

    print(
        f"Pixels iguais:           {total_pixels_iguais:,}"
    )

    print(
        f"Pixels diferentes:      {total_pixels_diferentes:,}"
    )

    print(
        f"Compatibilidade global:  "
        f"{percentual_global:.6f}%"
    )

    print(
        f"Maior diferença global:  "
        f"{maior_diferenca_global}"
    )

    print()

    if testes_falharam == 0:

        print(
            "Todas as imagens produziram exatamente "
            "os mesmos pixels."
        )

    else:

        print("⚠ RESULTADO FINAL: FALHOU")
        print(
            "Existem diferenças entre as implementações."
        )

    print("=" * 70)


if __name__ == "__main__":
    main()