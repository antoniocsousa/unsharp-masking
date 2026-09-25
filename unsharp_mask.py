import cv2
import numpy as np


ARQUIVO_ENTRADA = "monalisa.pgm"
ARQUIVO_OPENCV = "monalisa-after-opencv.pgm"

GANHO_K = 1.0


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
