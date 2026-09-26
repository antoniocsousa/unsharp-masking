import cv2
import numpy as np

# ==========================================================
# COMPARAÇÃO PIXEL A PIXEL
# ==========================================================

ARQUIVO_C = "images_C/monalisa.pgm"
ARQUIVO_PYTHON = "images_Python/monalisa.pgm"

resultado_c = cv2.imread(
    ARQUIVO_C,
    cv2.IMREAD_GRAYSCALE
)

resultado_opencv = cv2.imread(
    ARQUIVO_PYTHON,
    cv2.IMREAD_GRAYSCALE
)

if resultado_c is None:
    raise RuntimeError("Não foi possível abrir a saída do C.")

if resultado_opencv.shape != resultado_c.shape:
    print("ERRO: as imagens possuem dimensões diferentes.")
    print("OpenCV:", resultado_opencv.shape)
    print("C:", resultado_c.shape)
    exit(1)

# Diferença absoluta entre cada pixel
diferenca = np.abs(
    resultado_opencv.astype(np.int16) -
    resultado_c.astype(np.int16)
)

# Pixels exatamente iguais
pixels_iguais = np.sum(diferenca == 0)

# Número total de pixels
total_pixels = diferenca.size

# Pixels diferentes
pixels_diferentes = np.sum(diferenca != 0)

# Maior diferença encontrada
maior_diferenca = np.max(diferenca)


print("========================================")
print("        VALIDAÇÃO UNSHARP MASK")
print("========================================")

print(f"Dimensões: {resultado_opencv.shape[1]} x {resultado_opencv.shape[0]}")
print(f"Total de pixels: {total_pixels}")

print(f"Pixels iguais: {pixels_iguais}")
print(f"Pixels diferentes: {pixels_diferentes}")

print(f"Maior diferença: {maior_diferenca}")

print(
    f"Percentual de pixels iguais: "
    f"{pixels_iguais / total_pixels * 100:.6f}%"
)


if pixels_diferentes == 0:
    print("\nRESULTADO: PASSOU")
    print("As duas implementações produziram exatamente")
    print("o mesmo valor para todos os pixels.")
else:
    print("\nRESULTADO: FALHOU")
    print("Existem diferenças entre as implementações.")

    # Mostra algumas diferenças
    indices = np.argwhere(diferenca != 0)

    print("\nPrimeiras diferenças:")

    for i, j in indices[:20]:
        print(
            f"Pixel [{i}, {j}]: "
            f"C={resultado_c[i, j]} | "
            f"OpenCV={resultado_opencv[i, j]} | "
            f"diferença={diferenca[i, j]}"
        )