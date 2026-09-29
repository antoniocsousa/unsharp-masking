# Unsharp Masking em C

Implementação, em C, do algoritmo **Unsharp Masking** (realce de nitidez de imagens), testada contra uma implementação de referência da biblioteca **Kornia** (Python).

> **Em uma frase:** o programa em C deixa a imagem mais nítida, e comparamos o resultado dele com o da Kornia para provar que está correto.
>
> **Resultado:** nas 12 imagens de teste (3.210.250 pixels), o C e a Kornia produziram **exatamente a mesma saída**: 0 pixels diferentes.

---

## Sumário

1. [A ideia do algoritmo](#1-a-ideia-do-algoritmo)
2. [Arquivos do projeto](#2-arquivos-do-projeto)
3. [Como o programa em C funciona](#3-como-o-programa-em-c-funciona)
4. [Exemplo passo a passo com números](#4-exemplo-passo-a-passo-com-números)
5. [A referência em Python](#5-a-referência-em-python)
6. [Como foi feito o teste](#6-como-foi-feito-o-teste)
7. [Resultados](#7-resultados)
8. [Como executar](#8-como-executar)
9. [Limitações e melhorias](#9-limitações-e-melhorias)
10. [Roteiro para a apresentação](#10-roteiro-para-a-apresentação)
11. [Perguntas que o professor pode fazer](#11-perguntas-que-o-professor-pode-fazer)

---

## 1. A ideia do algoritmo

Uma imagem parece **nítida** quando as bordas (transições rápidas de claro para escuro) são bem marcadas. O Unsharp Masking aumenta essas transições em três passos:

| Passo | O que faz | Fórmula |
|---|---|---|
| 1. Borrar | Cria uma versão desfocada da imagem | `B = desfoque(I)` |
| 2. Máscara | Subtrai o borrão da original. Sobra só o **detalhe** (bordas e texturas) | `M = I − B` |
| 3. Realçar | Soma o detalhe de volta à original, reforçado por um ganho `k` | `R = I + k · M` |

- `I` = imagem original, `B` = imagem borrada, `M` = máscara de detalhes, `R` = resultado.
- `k` controla a força. Neste projeto, **`k = 1`**.

**Por que funciona?** Em regiões lisas, original e borrada são quase iguais, então `M ≈ 0` e nada muda. Perto de uma borda, o borrão "suaviza" a transição, então `M` é diferente de zero e, ao somar, a borda fica mais marcada: o lado claro fica um pouco mais claro e o lado escuro, um pouco mais escuro.

Em cada pixel, o cálculo é só: **novo = original + (original − borrado)**.

---

## 2. Arquivos do projeto

```
unsharp-masking/
├── requirements.txt         dependências Python
├── .gitignore
└── src/
    ├── unsharp_mask.c       ★ o algoritmo em C (foco do trabalho)
    ├── unsharp_mask.py      referência (Kornia), usada como "gabarito"
    ├── run_pipeline.py      roda o C e a Kornia em todas as imagens
    ├── test.ipynb           compara os resultados e calcula as métricas
    ├── images/              12 imagens de entrada (.pgm)
    └── results/
        ├── c/               saídas do programa em C
        └── kornia/          saídas da Kornia
```

**Formato das imagens (PGM P2):** as imagens são arquivos de **texto** em tons de cinza. Isso permite ler e escrever imagens em C sem nenhuma biblioteca externa.

```
P2              ← tipo do arquivo
512 512         ← largura e altura
255             ← valor máximo de um pixel (0 = preto, 255 = branco)
168 163 159 ... ← todos os pixels, linha por linha
```

**Fluxo geral:**

```
   images/*.pgm
        │
   ┌────┴─────────────┐
   ▼                  ▼
 C (nosso)        Kornia (referência)
   │                  │
   ▼                  ▼
results/c/      results/kornia/
   └────────┬─────────┘
            ▼
      test.ipynb  →  as duas saídas são iguais?
```

---

## 3. Como o programa em C funciona

Uso: `./unsharp_mask entrada.pgm saida.pgm`

O programa faz quatro coisas, nesta ordem:

```
[A] Ler a imagem  →  [B] Borrar  →  [C] Máscara + realce  →  [D] Salvar
```

### [A] Ler a imagem

O programa abre o arquivo, confere que é `P2`, lê largura, altura e valor máximo, e guarda todos os pixels em uma matriz de `float` chamada `original`. Cria também uma segunda matriz, `resultado`, do mesmo tamanho.

```c
float original[height][width];
float resultado[height][width];
```

> Usamos `float` (e não `int`) porque a etapa seguinte gera valores fracionários, e queremos só arredondar no final.

### [B] Borrar a imagem (filtro gaussiano 3×3)

**O que é "borrar"?** Para cada pixel, o novo valor é uma **média ponderada** dele com seus 8 vizinhos. Imagine uma janela 3×3 centrada no pixel:

```
 vizinho  vizinho  vizinho              pesos
 vizinho  PIXEL    vizinho     ×    0,075  0,124  0,075
 vizinho  vizinho  vizinho           0,124  0,204  0,124
                                     0,075  0,124  0,075
```

Multiplica-se cada vizinho pelo peso correspondente e somam-se os 9 produtos. O pixel do centro tem o maior peso (0,204); os cantos, o menor (0,075). Os pesos somam 1, então o brilho geral da imagem não muda. Esta tabela de pesos é o **kernel**:

```c
static const float kernel_desfoque[3][3] = {
    {0.07511361f, 0.12384140f, 0.07511361f},
    {0.12384140f, 0.20417996f, 0.12384140f},
    {0.07511361f, 0.12384140f, 0.07511361f}
};
```

Esses números vêm da curva gaussiana (o "sino") com σ = 1, que é o mesmo que a Kornia usa nessa configuração.

**O código que faz isso** são quatro laços: os dois de fora percorrem os pixels da imagem (`i`, `j`), e os dois de dentro percorrem a janela 3×3 (`ki`, `kj`, de −1 a +1):

```c
for (int i = 0; i < height; i++) {          // cada linha
    for (int j = 0; j < width; j++) {       // cada coluna
        float soma_ponderada = 0.0f;

        for (int ki = -1; ki <= 1; ki++) {      // linha da janela
            for (int kj = -1; kj <= 1; kj++) {  // coluna da janela
                int idx_i = refletir_indice(i + ki, height);
                int idx_j = refletir_indice(j + kj, width);
                soma_ponderada += original[idx_i][idx_j] * kernel_desfoque[ki+1][kj+1];
            }
        }
        resultado[i][j] = soma_ponderada;   // guarda o pixel borrado
    }
}
```

(`ki + 1` e `kj + 1` só transformam o intervalo −1…+1 em 0…2, que são os índices do kernel.)

**E os pixels da borda da imagem?** Para um pixel na primeira linha, a janela pede a linha "−1", que não existe. A função `refletir_indice` resolve isso **espelhando** a imagem:

```c
int refletir_indice(int p, int max) {
    if (p < 0)     return -p;              // -1 vira 1
    if (p >= max)  return 2 * max - p - 2; // max vira max-2
    return p;
}
```

Exemplo com uma linha de 5 pixels `a b c d e` (índices 0 a 4): o índice `-1` usa o pixel `b` (índice 1), e o índice `5` usa o pixel `d` (índice 3). É como colocar um espelho na borda.

Ao final desta etapa, a matriz `resultado` contém a **imagem borrada `B`**.

### [C] Máscara e realce

Agora, para cada pixel:

```c
float mascara = original[i][j] - resultado[i][j];       // M = I − B
resultado[i][j] = original[i][j] + ganho_k * mascara;   // R = I + k·M
```

**Truque de memória:** em vez de criar uma terceira matriz, reaproveitamos `resultado`. Ela guardava o borrão `B`; depois de calcular a máscara, o mesmo espaço passa a guardar o resultado final `R`. Isso é seguro, porque cada posição `[i][j]` só usa o próprio valor de `resultado` e o de `original`.

### [D] Salvar a imagem

Escreve o cabeçalho (`P2`, dimensões, valor máximo) e, para cada pixel, faz duas correções antes de gravar:

```c
if (val < 0.0f)   val = 0.0f;      // não pode ser menor que 0 (preto)
if (val > 255.0f) val = 255.0f;    // não pode passar de 255 (branco)
fprintf(arquivo, "%d ", (int)(val + 0.5f));   // arredonda para inteiro
```

- **Clipping:** o realce pode produzir números fora de 0–255 (ex.: −20 ou 270). Como isso não é um pixel válido, cortamos.
- **Arredondamento:** somar 0,5 e truncar (`(int)`) arredonda para o inteiro mais próximo.

### Resumo do C em uma tabela

| Parte do código | Para que serve |
|---|---|
| `kernel_desfoque` | Pesos do filtro gaussiano 3×3 |
| `refletir_indice` | Trata os pixels da borda (espelhamento) |
| Leitura (`fscanf`) | Carrega o PGM para a matriz `original` |
| 1º conjunto de laços | Calcula o borrão `B` e guarda em `resultado` |
| 2º conjunto de laços | Calcula `M = I − B` e `R = I + k·M` |
| Escrita (`fprintf`) | Corta em 0–255, arredonda e grava o PGM |
| `main` | Define `k = 1` e chama tudo com os arquivos passados na linha de comando |

**Custo:** para cada pixel, 9 multiplicações. Em uma imagem 512×512 são ≈ 2,4 milhões de multiplicações.

---

## 4. Exemplo passo a passo com números

Para ver o algoritmo funcionando, vamos usar uma imagem minúscula de **5×5**, com uma borda vertical (esquerda escura, direita clara). Todas as linhas são iguais, então basta olhar uma:

```
Entrada (cada linha):   50  50  50  200  200
                                 ↑
                          coluna 2 (centro)
```

### Pixel da coluna 2 (valor 50, ao lado da borda)

**Passo 1: janela 3×3 ao redor do pixel** (as três linhas são iguais):

```
 50   50  200
 50  [50] 200
 50   50  200
```

**Passo 2: borrão** (média ponderada com os pesos do kernel):

```
B = 50 × (0,075+0,124+0,075+0,124+0,204+0,124)   ← as 2 colunas da esquerda (valor 50)
  + 200 × (0,075+0,124+0,075)                    ← a coluna da direita (valor 200)
B = 50 × 0,726 + 200 × 0,274 = 36,3 + 54,8 ≈ 91,1
```

O borrão "puxou" o valor de 50 para 91 porque enxergou o lado claro.

**Passo 3: máscara**

```
M = I − B = 50 − 91,1 = −41,1
```

**Passo 4: realce** (com k = 1)

```
R = I + k·M = 50 + (−41,1) = 8,9   →  arredondado: 9
```

O pixel escuro ao lado da borda ficou **ainda mais escuro** (50 → 9).

### Pixel da coluna 3 (valor 200, do outro lado da borda)

Por simetria: janela `50 200 200`, borrão ≈ 158,9, máscara ≈ +41,1 e resultado ≈ 241,1, ou seja, **200 → 241**, mais claro.

### Pixel longe da borda (coluna 0)

Janela toda com valor 50 (usando o espelhamento na borda da imagem), borrão = 50, máscara = 0, resultado = 50. **Nada muda** onde não há detalhe.

### Resultado (saída real do programa, rodando em C)

```
Entrada:  50  50  50  200  200
Saída:    50  50   9  241  200
```

A transição, que era `50 → 200`, virou `50 → 9 → 241 → 200`. O contraste **na borda** aumentou (o "salto" entre os dois lados ficou bem maior), e é isso que percebemos como maior nitidez. As regiões lisas ficaram intactas.

---

## 5. A referência em Python

`src/unsharp_mask.py` faz a mesma operação, mas usando a biblioteca Kornia. Serve como "resposta certa" para testar o C. Uso: `python3 unsharp_mask.py entrada.pgm saida.pgm`.

O fluxo é:

1. **Ler o PGM** (`read_pgm`) para um tensor do PyTorch.
2. **Normalizar** para 0–1 (divide por 255), que é a escala que a Kornia espera.
3. **Ajustar o formato** do tensor para `1×1×altura×largura`.
4. **Aplicar o filtro** com uma única chamada:
   ```python
   K.filters.unsharp_mask(image, kernel_size=(3, 3), sigma=(1.0, 1.0))
   ```
   Ou seja: gaussiana 3×3 com σ = 1, borda espelhada (padrão) e `resultado = original + (original − borrado)`. Os mesmos parâmetros do C.
5. **Voltar** para a escala 0–255, cortar (`clamp`), arredondar e salvar em PGM (`save_pgm_p2`).

Onde o C precisa implementar tudo na mão, a Kornia faz o mesmo em uma linha.

---

## 6. Como foi feito o teste

### `run_pipeline.py` (gera as saídas)

Para cada `.pgm` em `src/images/`, ele:
1. executa o programa em C → `results/c/<nome>_result.pgm`;
2. executa o script da Kornia → `results/kornia/<nome>_result.pgm`.

Se uma imagem der erro, ele avisa e continua com as outras. (O programa em C precisa estar compilado antes.)

### `test.ipynb` (compara as saídas)

O notebook abre cada par de imagens (C × Kornia), subtrai uma da outra e calcula:

| Métrica | Significado simples |
|---|---|
| **% de pixels iguais** | Quantos pixels são exatamente iguais nas duas saídas |
| **MAE** | Diferença média por pixel |
| **RMSE** | Como o MAE, mas penaliza mais as diferenças grandes |
| **Erro máximo** | A maior diferença encontrada em um único pixel |
| **PSNR (dB)** | Medida de similaridade; fica **infinito** quando as imagens são idênticas |

Ele também mostra gráficos por imagem e um mapa da **diferença absoluta** entre C e Kornia (que aparece todo preto, porque não há diferença).

---

## 7. Resultados

Resumo global do notebook:

```
Imagens testadas:       12
Total de pixels:        3,210,250
Pixels iguais:          3,210,250
Pixels diferentes:      0
Compatibilidade:        100%
Maior erro encontrado:  0
```

Todas as 12 imagens tiveram: **0 pixels diferentes, MAE = 0, RMSE = 0, erro máximo = 0 e PSNR = ∞.**

| Imagem | Dimensão | Imagem | Dimensão |
|---|---|---|---|
| barb | 512×512 | mandrill | 512×512 |
| boat | 512×512 | mountain | 640×480 |
| france | 672×496 | peppers2 | 512×512 |
| frog | 621×498 | washsat | 512×512 |
| goldhill2 | 512×512 | zelda | 512×512 |
| lena2 | 512×512 | library | 464×352 |

**O teste é significativo?** Sim. Comparando a saída com a imagem *original*, o filtro modifica de ~19% a ~96% dos pixels (na maioria das imagens, mais de 80%). Portanto a igualdade C × Kornia não acontece "por nada ter mudado": os dois programas fazem a mesma transformação, de fato.

---

## 8. Como executar

**Requisitos:** `gcc` e Python 3.

**1. Compilar o C**
```bash
cd src
gcc -O2 -o unsharp_mask unsharp_mask.c
```

**2. Preparar o Python**
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install torch kornia numpy opencv-python pandas matplotlib jupyter
```
> O `requirements.txt` do repositório é grande porque inclui bibliotecas de GPU (CUDA) que o projeto **não precisa**. A linha acima instala só o necessário. Note também que `pandas`, `matplotlib` e `jupyter` (usados no notebook) não estão listados no `requirements.txt`.

**3. Rodar uma imagem**
```bash
./unsharp_mask images/lena2.pgm results/c/lena2_result.pgm
python3 unsharp_mask.py images/lena2.pgm results/kornia/lena2_result.pgm
```

**4. Rodar todas as imagens**
```bash
cd ..
python3 src/run_pipeline.py
```

**5. Ver a comparação**
```bash
cd src
jupyter notebook test.ipynb
```

> Para abrir arquivos `.pgm`, use GIMP, IrfanView ou XnView. Para converter para PNG: `convert imagem.pgm imagem.png` (ImageMagick).

---

## 9. Limitações e melhorias

**Limitações do código em C (hoje):**

- **Imagens grandes:** as matrizes são criadas na pilha (`float original[h][w]`), que tem tamanho limitado (~8 MB). Imagens muito grandes (na casa de 1000×1000 ou mais) podem travar o programa. A solução seria usar `malloc`.
- **Valor máximo fixo:** o corte usa 255 direto no código, em vez do valor máximo do cabeçalho. Serve para imagens de 8 bits, como as deste projeto.
- **Só lê PGM P2 (texto)**, sem comentários (`#`) no cabeçalho.
- **Poucas verificações:** não checa se os argumentos foram passados nem se todos os pixels foram lidos.
- **Parâmetros fixos:** `k = 1`, kernel 3×3 e σ = 1 estão no código, não na linha de comando.

**Melhorias possíveis:** alocação dinâmica, `k` e σ como parâmetros, filtro gaussiano *separável* (duas passadas 1D, mais rápido), suporte a PGM binário e imagens coloridas, comparação de tempo C × Python e um `Makefile`.

---

## 10. Roteiro para a apresentação

1. **O problema (1 min):** o que é nitidez; mostrar uma imagem antes e depois.
2. **A ideia (2 min):** `R = I + k·(I − B)`; usar o exemplo `50 50 50 200 200 → 50 50 9 241 200` da seção 4.
3. **O código em C (4 min):** seguir as etapas [A] ler, [B] borrar, [C] máscara e realce, [D] salvar, mostrando o trecho de código de cada uma.
4. **A referência (1 min):** uma chamada da Kornia, com os mesmos parâmetros.
5. **O teste (2 min):** 12 imagens, mesmas entradas; métricas; mapa de diferença todo preto.
6. **Conclusão (1 min):** 100% de igualdade; limitações e melhorias.

---

## 11. Perguntas que o professor pode fazer

**Por que espelhar a borda em vez de usar zero?**
Preencher com zero escureceria as bordas da imagem ao borrar. O espelhamento mantém valores parecidos com os reais e é o comportamento padrão da Kornia.

**Por que o kernel é gaussiano e não uma média simples?**
A gaussiana dá mais peso ao centro e decai suavemente, gerando um desfoque mais natural.

**O que muda se `k` for maior que 1?**
A máscara é mais amplificada, então as bordas ficam mais fortes, mas aparecem mais artefatos (halos) e mais pixels saturam em 0 ou 255.

**Por que usar `float` e não `int`?**
O borrão gera valores fracionários. Arredondar só no final evita acumular erro.

**Por que o PSNR é infinito?**
PSNR = 10·log₁₀(255² / MSE). Sem diferença, MSE = 0 e a divisão tende ao infinito. É o esperado para imagens idênticas.

**Como saber que o teste não é trivial (por exemplo, que o filtro não deixou tudo igual)?**
O filtro altera de ~19% a ~96% dos pixels em relação à imagem original, com mudanças de até ~109 níveis de cinza.

**Por que reaproveitar a matriz `resultado`?**
Economiza memória: o borrão só é usado para calcular a máscara de cada pixel, então o mesmo espaço pode guardar o resultado final.

**Qual a complexidade?**
Tempo O(altura × largura × 9), ou seja, linear no número de pixels. Memória: duas matrizes do tamanho da imagem.

**Por que comparar com a Kornia?**
É uma biblioteca consolidada. Concordar pixel a pixel com ela é uma evidência forte de que o C está correto.
