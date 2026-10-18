#!/usr/bin/env python3
"""
Processa uma imagem PGM P2 ou todas as imagens .pgm de um diretorio via STM32.

Argumentos:
  --port PORTA
      Porta serial da placa. Exemplos: /dev/ttyACM0, /dev/ttyUSB0 ou COM5.
      Obrigatorio.

  --input ARQUIVO.pgm
      Processa uma unica imagem PGM P2. Deve ser usado com --output.

  --output ARQUIVO.pgm
      Caminho do arquivo de saida para o modo de imagem unica.
      Opcional; padrao: resultado_stm32.pgm.

  --input-dir DIRETORIO
      Processa todos os arquivos .pgm encontrados diretamente nesse diretorio.
      Deve ser usado com --output-dir. Exclusivo com --input.

  --output-dir DIRETORIO
      Diretorio onde serao salvos os resultados no modo --input-dir.
      Opcional; padrao: resultados_stm32.

  --recursive
      No modo --input-dir, tambem procura arquivos .pgm nos subdiretorios
      e preserva a estrutura de pastas no diretorio de saida.

  --baud VALOR
      Velocidade da comunicacao serial. Padrao: 115200.

  --timeout SEGUNDOS
      Tempo maximo de espera por dados na serial. Padrao: 30 segundos.

Exemplos:
  Uma imagem:
    python stm32_unsharp_batch.py --port /dev/ttyACM0 --input barb.pgm --output barb_result.pgm

  Todas as imagens de um diretorio:
    python stm32_unsharp_batch.py --port /dev/ttyACM0 --input-dir ./original_images --output-dir ./processed_images
"""

import argparse
import sys
import time
from pathlib import Path

import serial

MIN_DIMENSION = 10
MAX_WIDTH = 90
MAX_HEIGHT = 90
ROW_REQUEST = 0xA5
ERROR_BYTE = 0xFF


def read_pgm_p2(path: Path):
    """Le PGM P2 e retorna largura, altura e pixels convertidos para 8 bits."""
    try:
        data = path.read_bytes()
    except OSError as exc:
        raise ValueError(f"Nao foi possivel ler '{path}': {exc}") from exc

    tokens, i, n = [], 0, len(data)
    while i < n:
        while i < n and chr(data[i]).isspace():
            i += 1
        if i >= n:
            break
        if data[i] == ord("#"):
            while i < n and data[i] not in (10, 13):
                i += 1
            continue
        start = i
        while i < n and not chr(data[i]).isspace() and data[i] != ord("#"):
            i += 1
        tokens.append(data[start:i].decode("ascii"))

    if len(tokens) < 4 or tokens[0] != "P2":
        raise ValueError("O arquivo precisa ser PGM ASCII no formato P2.")
    try:
        width, height, maxval = map(int, tokens[1:4])
    except ValueError as exc:
        raise ValueError("Cabecalho PGM invalido.") from exc

    if not MIN_DIMENSION <= width <= MAX_WIDTH:
        raise ValueError(f"Largura {width} fora do intervalo {MIN_DIMENSION}..{MAX_WIDTH}.")
    if not MIN_DIMENSION <= height <= MAX_HEIGHT:
        raise ValueError(f"Altura {height} fora do intervalo {MIN_DIMENSION}..{MAX_HEIGHT}.")
    if not 1 <= maxval <= 65535:
        raise ValueError("maxval deve estar entre 1 e 65535.")

    expected, found = width * height, len(tokens) - 4
    if found != expected:
        raise ValueError(f"Esperados {expected} pixels, encontrados {found}.")

    try:
        values = [int(t) for t in tokens[4:]]
    except ValueError as exc:
        raise ValueError("A imagem contem pixel que nao e inteiro.") from exc
    if any(p < 0 or p > maxval for p in values):
        raise ValueError(f"Pixel fora do intervalo 0..{maxval}.")

    if maxval == 255:
        pixels = bytes(values)
    else:
        pixels = bytes((p * 255 + maxval // 2) // maxval for p in values)
    return width, height, pixels


def write_pgm_p2(path: Path, width: int, height: int, pixels: bytes):
    """Salva a imagem como PGM P2 com maxval 255."""
    if len(pixels) != width * height:
        raise ValueError("Quantidade de pixels recebidos nao corresponde as dimensoes.")
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", encoding="ascii", newline="\n") as f:
            f.write(f"P2\n{width} {height}\n255\n")
            for y in range(height):
                row = pixels[y * width:(y + 1) * width]
                f.write(" ".join(map(str, row)) + "\n")
    except OSError as exc:
        raise ValueError(f"Nao foi possivel salvar '{path}': {exc}") from exc


def read_exact(port: serial.Serial, count: int) -> bytes:
    """Le exatamente count bytes, mesmo com leituras seriais parciais."""
    data = bytearray()
    while len(data) < count:
        chunk = port.read(count - len(data))
        if not chunk:
            raise TimeoutError(f"Timeout: recebidos {len(data)} de {count} bytes.")
        data.extend(chunk)
    return bytes(data)


def wait_for_row_request(port: serial.Serial):
    signal = read_exact(port, 1)[0]
    if signal == ERROR_BYTE:
        raise RuntimeError("STM32 rejeitou as dimensoes (resposta 0xFF).")
    if signal != ROW_REQUEST:
        raise RuntimeError(
            f"Byte inesperado 0x{signal:02X}; esperado 0x{ROW_REQUEST:02X}."
        )


def process_image(port: serial.Serial, input_path: Path, output_path: Path):
    """Transfere uma imagem, sincronizando cada linha com o firmware."""
    width, height, pixels = read_pgm_p2(input_path)
    print(f"\n[{input_path.name}] {width}x{height} ({len(pixels)} bytes de pixels)")

    port.write(bytes((width, height)))
    port.flush()
    result = bytearray()

    for y in range(height):
        wait_for_row_request(port)
        row = pixels[y * width:(y + 1) * width]
        port.write(row)
        port.flush()

        # O firmware envia a linha 0 apos receber a linha 1; depois envia
        # uma linha de saida por cada linha recebida, exceto a primeira.
        if y >= 1:
            result.extend(read_exact(port, width))

        if (y + 1) % 10 == 0 or y + 1 == height:
            print(f"  Linhas enviadas: {y + 1}/{height}")

    # O firmware envia a ultima linha processada ao terminar a recepcao.
    result.extend(read_exact(port, width))
    if len(result) != width * height:
        raise RuntimeError(f"Resposta incompleta: {len(result)} bytes recebidos.")

    write_pgm_p2(output_path, width, height, bytes(result))
    print(f"  Resultado salvo: {output_path}")


def main():
    parser = argparse.ArgumentParser(
        description="Processa uma imagem ou todas as imagens PGM de um diretorio via STM32."
    )
    parser.add_argument("--port", required=True, help="Porta serial da placa, por exemplo /dev/ttyACM0 ou COM5.")
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--input", type=Path, help="Caminho de uma imagem PGM P2.")
    source.add_argument("--input-dir", type=Path, help="Diretorio com imagens PGM P2.")
    parser.add_argument("--output", type=Path, default=Path("resultado_stm32.pgm"),
                        help="Arquivo de saida no modo --input.")
    parser.add_argument("--output-dir", type=Path, default=Path("resultados_stm32"),
                        help="Diretorio de saida no modo --input-dir.")
    parser.add_argument("--recursive", action="store_true",
                        help="Busca arquivos PGM tambem nos subdiretorios.")
    parser.add_argument("--baud", type=int, default=115200, help="Baud rate.")
    parser.add_argument("--timeout", type=float, default=30.0, help="Timeout serial em segundos.")
    args = parser.parse_args()

    if args.input:
        if not args.input.is_file():
            parser.error(f"Arquivo nao encontrado: {args.input}")
        jobs = [(args.input, args.output)]
    else:
        if not args.input_dir.is_dir():
            parser.error(f"Diretorio nao encontrado: {args.input_dir}")
        pattern = "**/*" if args.recursive else "*"
        inputs = sorted(p for p in args.input_dir.glob(pattern)
                        if p.is_file() and p.suffix.lower() == ".pgm")
        if not inputs:
            parser.error(f"Nenhum arquivo .pgm encontrado em {args.input_dir}")
        jobs = []
        for source_path in inputs:
            if args.recursive:
                rel = source_path.relative_to(args.input_dir)
                target = (args.output_dir / rel).with_name(f"{source_path.stem}.pgm")
            else:
                target = args.output_dir / f"{source_path.stem}.pgm"
            jobs.append((source_path, target))

    print(f"Porta: {args.port} @ {args.baud} baud")
    print(f"Imagens na fila: {len(jobs)}")

    try:
        with serial.Serial(
            port=args.port, baudrate=args.baud, bytesize=serial.EIGHTBITS,
            parity=serial.PARITY_NONE, stopbits=serial.STOPBITS_ONE,
            timeout=args.timeout, write_timeout=args.timeout
        ) as port:
            # Algumas placas reiniciam quando a porta e aberta.
            time.sleep(0.2)
            port.reset_input_buffer()
            port.reset_output_buffer()

            succeeded, failed = 0, []
            for source_path, target_path in jobs:
                try:
                    process_image(port, source_path, target_path)
                    succeeded += 1
                except (ValueError, TimeoutError, RuntimeError) as exc:
                    failed.append((source_path, str(exc)))
                    print(f"ERRO em {source_path}: {exc}", file=sys.stderr)
                    # Timeout/protocolo pode deixar a serial fora de sincronia.
                    if isinstance(exc, (TimeoutError, RuntimeError)):
                        break

            print(f"\nConcluido: {succeeded}/{len(jobs)} imagem(ns) processada(s).")
            if failed:
                for source_path, message in failed:
                    print(f"Falha - {source_path}: {message}", file=sys.stderr)
                return 1

    except serial.SerialException as exc:
        print(f"Erro na comunicacao serial: {exc}", file=sys.stderr)
        print("Confira a porta, o cabo e se outro programa esta usando a serial.", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
