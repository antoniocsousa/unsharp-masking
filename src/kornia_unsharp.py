#!/usr/bin/env python3
"""
Executa a implementação de Unsharp Mask da Kornia em imagens PGM P2 de um diretório.

Argumentos:
  --input ARQUIVO.pgm       Processa uma única imagem (opcional).
  --output ARQUIVO.pgm      Caminho da saída para --input.
  --input-dir DIRETORIO     Processa imagens PGM P2 de um diretório.
  --output-dir DIRETORIO    Diretório onde as imagens processadas serão salvas.
  --recursive               Procura imagens também nos subdiretórios.
  --kernel-size N           Tamanho ímpar do kernel (padrão: 3).
  --sigma VALOR             Sigma do Gaussian blur (padrão: 1.0).

Exemplos:
  python3 unsharp_kornia_batch.py --input barb.pgm --output barb_kornia.pgm
  python3 unsharp_kornia_batch.py --input-dir ./original_images --output-dir ./kornia_results
  python3 unsharp_kornia_batch.py --input-dir ./original_images --output-dir ./kornia_results --recursive
"""

import argparse
from pathlib import Path

import torch
import kornia as K


def read_pgm(filename: Path):
    """Lê um arquivo PGM P2, ignorando comentários."""
    with filename.open("r", encoding="ascii") as f:
        tokens = []
        for line in f:
            line = line.split("#", 1)[0]
            tokens.extend(line.split())

    if not tokens or tokens[0] != "P2":
        raise ValueError("O arquivo não é um PGM P2.")

    if len(tokens) < 4:
        raise ValueError("Cabeçalho PGM incompleto.")

    width = int(tokens[1])
    height = int(tokens[2])
    max_value = int(tokens[3])

    if width <= 0 or height <= 0:
        raise ValueError(f"Dimensões inválidas: {width}x{height}.")
    if not 1 <= max_value <= 65535:
        raise ValueError(f"MAXVAL inválido: {max_value}.")

    pixel_tokens = tokens[4:]
    expected = width * height
    if len(pixel_tokens) != expected:
        raise ValueError(
            f"Número de pixels incorreto: esperado {expected}, "
            f"encontrado {len(pixel_tokens)}."
        )

    pixels = list(map(int, pixel_tokens))
    if any(pixel < 0 or pixel > max_value for pixel in pixels):
        raise ValueError("Há pixels fora do intervalo definido por MAXVAL.")

    image = torch.tensor(pixels, dtype=torch.float32).reshape(height, width)
    return image, width, height, max_value


def save_pgm(filename: Path, image: torch.Tensor, max_value: int):
    """Salva uma imagem como PGM P2."""
    filename.parent.mkdir(parents=True, exist_ok=True)
    image = image.cpu()
    height, width = image.shape

    with filename.open("w", encoding="ascii") as f:
        f.write("P2\n")
        f.write(f"{width} {height}\n")
        f.write(f"{max_value}\n")
        for row in image:
            f.write(" ".join(str(int(pixel)) for pixel in row.tolist()))
            f.write("\n")


def process_image(input_path: Path, output_path: Path, kernel_size: int, sigma: float):
    """Aplica Unsharp Mask da Kornia em uma imagem e salva o resultado."""
    image, _, _, max_value = read_pgm(input_path)

    # Normalizar para [0, 1] e adicionar dimensões B e C: HxW -> 1x1xHxW.
    image = (image / max_value).unsqueeze(0).unsqueeze(0)

    with torch.no_grad():
        result = K.filters.unsharp_mask(
            image,
            kernel_size=(kernel_size, kernel_size),
            sigma=(sigma, sigma),
        )

    # Remover B e C, voltar à escala original, limitar e arredondar.
    result = result.squeeze(0).squeeze(0) * max_value
    result = torch.clamp(result, 0, max_value).round().to(torch.int32)

    save_pgm(output_path, result, max_value)


def main():
    parser = argparse.ArgumentParser(
        description="Aplica Unsharp Mask da Kornia em uma imagem ou em um diretório de PGM P2."
    )
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--input", type=Path, help="Caminho de uma imagem PGM P2.")
    source.add_argument("--input-dir", type=Path, help="Diretório com imagens PGM P2.")

    parser.add_argument("--output", type=Path, help="Arquivo de saída para --input.")
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("resultados_kornia"),
        help="Diretório de saída (padrão: resultados_kornia).",
    )
    parser.add_argument(
        "--recursive",
        action="store_true",
        help="Procura arquivos .pgm também nos subdiretórios.",
    )
    parser.add_argument(
        "--kernel-size",
        type=int,
        default=3,
        help="Tamanho ímpar do kernel (padrão: 3).",
    )
    parser.add_argument(
        "--sigma",
        type=float,
        default=1.0,
        help="Sigma do Gaussian blur (padrão: 1.0).",
    )
    args = parser.parse_args()

    if args.kernel_size < 3 or args.kernel_size % 2 == 0:
        parser.error("--kernel-size deve ser um número ímpar maior ou igual a 3.")
    if args.sigma <= 0:
        parser.error("--sigma deve ser maior que zero.")

    if args.input is not None:
        if not args.input.is_file():
            parser.error(f"Arquivo de entrada não encontrado: {args.input}")
        output_path = args.output or args.input.with_name(
            f"{args.input.stem}.pgm"
        )
        jobs = [(args.input, output_path)]
    else:
        if not args.input_dir.is_dir():
            parser.error(f"Diretório de entrada não encontrado: {args.input_dir}")

        iterator = args.input_dir.rglob("*") if args.recursive else args.input_dir.iterdir()
        input_files = sorted(
            p for p in iterator
            if p.is_file() and p.suffix.lower() == ".pgm"
        )

        if not input_files:
            parser.error(f"Nenhum arquivo .pgm encontrado em: {args.input_dir}")

        jobs = []
        for input_path in input_files:
            relative_path = input_path.relative_to(args.input_dir)
            output_path = args.output_dir / relative_path.parent / f"{input_path.stem}.pgm"
            jobs.append((input_path, output_path))

    successes = 0
    failures = 0

    for input_path, output_path in jobs:
        try:
            process_image(input_path, output_path, args.kernel_size, args.sigma)
            print(f"[OK] {input_path} -> {output_path}")
            successes += 1
        except Exception as exc:
            print(f"[ERRO] {input_path}: {exc}")
            failures += 1

    print(f"\nConcluído: {successes} sucesso(s), {failures} erro(s).")
    if failures:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
