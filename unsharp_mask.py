import torch
import kornia as K


def read_pgm_p2(filename):
    """Lê um arquivo PGM P2."""

    with open(filename, "r") as f:
        # Remove comentários
        tokens = []
        for line in f:
            line = line.split("#")[0]
            tokens.extend(line.split())

    if tokens[0] != "P2":
        raise ValueError("O arquivo não é um PGM P2.")

    width = int(tokens[1])
    height = int(tokens[2])
    max_value = int(tokens[3])

    pixels = list(map(int, tokens[4:]))

    if len(pixels) != width * height:
        raise ValueError(
            f"Número de pixels incorreto: "
            f"esperado {width * height}, encontrado {len(pixels)}"
        )

    image = torch.tensor(
        pixels,
        dtype=torch.float32
    ).reshape(height, width)

    return image, width, height, max_value


def save_pgm_p2(filename, image, max_value):
    """Salva uma imagem como PGM P2."""

    height, width = image.shape

    with open(filename, "w") as f:
        f.write("P2\n")
        f.write(f"{width} {height}\n")
        f.write(f"{max_value}\n")

        for row in image:
            for pixel in row:
                f.write(f"{int(pixel)} ")
            f.write("\n")


def main():

    input_file = "images/monalisa.pgm"
    output_file = "images_Python/monalisa.pgm"

    # --------------------------------------------------
    # 1. Ler PGM P2
    # --------------------------------------------------

    image, width, height, max_value = read_pgm_p2(input_file)

    print(f"Imagem: {width} x {height}")
    print(f"MAXVAL: {max_value}")

    # --------------------------------------------------
    # 2. Normalizar para [0, 1]
    # --------------------------------------------------

    image = image / max_value

    # --------------------------------------------------
    # 3. Adicionar dimensões para a Kornia
    #
    # H x W
    #   ↓
    # B x C x H x W
    #   ↓
    # 1 x 1 x H x W
    # --------------------------------------------------

    image = image.unsqueeze(0).unsqueeze(0)

    # --------------------------------------------------
    # 4. Unsharp Mask da Kornia
    # --------------------------------------------------

    result = K.filters.unsharp_mask(
        image,
        kernel_size=(3, 3),
        sigma=(1.0, 1.0)
    )

    # --------------------------------------------------
    # 5. Remover dimensões B e C
    # --------------------------------------------------

    result = result.squeeze(0).squeeze(0)

    # --------------------------------------------------
    # 6. Voltar de [0, 1] para [0, MAXVAL]
    # --------------------------------------------------

    result = result * max_value

    # --------------------------------------------------
    # 7. Clipping
    # --------------------------------------------------

    result = torch.clamp(result, 0, max_value)

    # --------------------------------------------------
    # 8. Converter para inteiro
    # --------------------------------------------------

    result = result.round().to(torch.int32)

    # --------------------------------------------------
    # 9. Salvar PGM P2
    # --------------------------------------------------

    save_pgm_p2(
        output_file,
        result,
        max_value
    )

    print(f"Resultado salvo em: {output_file}")


if __name__ == "__main__":
    main()