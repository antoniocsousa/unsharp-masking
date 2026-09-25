import cv2
import numpy as np


ARQUIVO_ENTRADA = "monalisa.pgm"
ARQUIVO_C = "monalisa-after.pgm"
ARQUIVO_OPENCV = "monalisa-after-opencv.pgm"

GANHO_K = 3.0


# Mesmo kernel utilizado no programa C
kernel = np.array([
    [1.0 / 16.0, 2.0 / 16.0, 1.0 / 16.0],
    [2.0 / 16.0, 4.0 / 16.0, 2.0 / 16.0],
    [1.0 / 16.0, 2.0 / 16.0, 1.0 / 16.0]
], dtype=np.float32)


# ==========================================================
# Leitura da imagem original
# ==========================================================

original = cv2.imread(
    ARQUIVO_ENTRADA,
    cv2.IMREAD_GRAYSCALE
)

if original is None:
    raise RuntimeError("Não foi possível abrir a imagem original.")


# ==========================================================
# ETAPA 1
# Convolução utilizando exatamente o mesmo kernel
# ==========================================================

suavizada = cv2.filter2D(
    original.astype(np.float32),
    -1,
    kernel,
    borderType=cv2.BORDER_REFLECT_101
)


# ==========================================================
# ETAPA 2 e 3
# máscara = original - suavizada
#
# resultado = original + k * máscara
# ==========================================================

original_float = original.astype(np.float32)

mascara = original_float - suavizada

resultado = original_float + GANHO_K * mascara


# ==========================================================
# Mesmo tratamento utilizado no C
# ==========================================================

resultado = np.clip(resultado, 0.0, 255.0)

# Equivalente ao:
#
# (int)(val + 0.5f)
#
# do C
resultado = np.floor(resultado + 0.5).astype(np.uint8)


# ==========================================================
# Salva resultado do OpenCV
# ==========================================================

cv2.imwrite(
    ARQUIVO_OPENCV,
    resultado
)


# ==========================================================
# COMPARAÇÃO PIXEL A PIXEL
# ==========================================================

resultado_c = cv2.imread(
    ARQUIVO_C,
    cv2.IMREAD_GRAYSCALE
)

if resultado_c is None:
    raise RuntimeError("Não foi possível abrir a saída do C.")


if resultado.shape != resultado_c.shape:
    print("ERRO: as imagens possuem dimensões diferentes.")
    print("OpenCV:", resultado.shape)
    print("C:", resultado_c.shape)
    exit(1)


# Diferença absoluta entre cada pixel
diferenca = np.abs(
    resultado.astype(np.int16) -
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

print(f"Dimensões: {resultado.shape[1]} x {resultado.shape[0]}")
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
            f"OpenCV={resultado[i, j]} | "
            f"diferença={diferenca[i, j]}"
        )