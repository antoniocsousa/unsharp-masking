from pathlib import Path
import subprocess


# Diretório raiz do projeto
BASE_DIR = Path(__file__).resolve().parent.parent

# Diretórios
IMAGES_DIR = BASE_DIR / "src" / "images"

C_RESULTS_DIR = BASE_DIR / "src" / "results" / "c"
KORNIA_RESULTS_DIR = BASE_DIR / "src" / "results" / "kornia"

# Programas
C_EXECUTABLE = BASE_DIR / "src" / "unsharp_mask"
KORNIA_SCRIPT = BASE_DIR / "src" / "unsharp_mask.py"


def run_c(input_path, output_path):
    print(f"[C]      {input_path.name}")

    subprocess.run(
        [
            str(C_EXECUTABLE),
            str(input_path),
            str(output_path)
        ],
        check=True
    )


def run_kornia(input_path, output_path):
    print(f"[Kornia] {input_path.name}")

    subprocess.run(
        [
            "python3",
            str(KORNIA_SCRIPT),
            str(input_path),
            str(output_path)
        ],
        check=True
    )


def main():

    C_RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    KORNIA_RESULTS_DIR.mkdir(parents=True, exist_ok=True)

    images = sorted(IMAGES_DIR.glob("*.pgm"))

    if not images:
        print(f"Nenhuma imagem .pgm encontrada em: {IMAGES_DIR}")
        return

    print(f"Encontradas {len(images)} imagens.\n")

    for image_path in images:

        output_name = image_path.stem + "_result.pgm"

        c_output = C_RESULTS_DIR / output_name
        kornia_output = KORNIA_RESULTS_DIR / output_name

        print(f"Processando: {image_path.name}")

        try:
            run_c(image_path, c_output)
            run_kornia(image_path, kornia_output)

            print("  ✓ OK\n")

        except subprocess.CalledProcessError as error:
            print(f"  ✗ Erro ao processar {image_path.name}")
            print(f"    Código de saída: {error.returncode}\n")

    print("Pipeline finalizado.")


if __name__ == "__main__":
    main()