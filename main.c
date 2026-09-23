#include <stdio.h>
#include <stdlib.h>

// Definicao das dimensoes fixas da matriz (100x80 = 8000 elementos float = 32 Kbytes)
#define HEIGHT 360
#define WIDTH 250

// Estrutura de dados contendo as matrizes estaticas de 8000 floats
typedef struct {
    float original[HEIGHT][WIDTH];
    float suavizada[HEIGHT][WIDTH];
    float mascara[HEIGHT][WIDTH];
    float resultado[HEIGHT][WIDTH];
} DadosImagem;

// Instancia estatica na memoria global (sem alocacao dinamica / malloc)
static DadosImagem img;

// Kernel de desfoque por media (3x3), onde cada elemento vale 1/9
static const float kernel_desfoque[3][3] = {
    {1.0f / 9.0f, 1.0f / 9.0f, 1.0f / 9.0f},
    {1.0f / 9.0f, 1.0f / 9.0f, 1.0f / 9.0f},
    {1.0f / 9.0f, 1.0f / 9.0f, 1.0f / 9.0f}
};

// Função para ler arquivo PGM (Tons de cinza em texto)
int load_pgm(const char *nome_arquivo) {
    FILE *arquivo = fopen(nome_arquivo, "r");
    if (!arquivo) {
        printf("Erro ao abrir o arquivo %s para leitura.\n", nome_arquivo);
        return 0;
    }

    char formato[3];
    int max_valor, w, h;

    // Le o cabecalho da imagem PGM
    if (fscanf(arquivo, "%2s", formato) != 1 || formato[0] != 'P' || formato[1] != '2') {
        printf("Erro: O arquivo deve estar no formato PGM P2.\n");
        fclose(arquivo);
        return 0;
    }

    if (fscanf(arquivo, "%d %d %d", &w, &h, &max_valor) != 3) {
        printf("Erro ao ler dimensoes do cabecalho PGM.\n");
        fclose(arquivo);
        return 0;
    }

    if (w != WIDTH || h != HEIGHT) {
        printf("Erro: A imagem deve ter tamanho exato de %dx%d pixels.\n", WIDTH, HEIGHT);
        fclose(arquivo);
        return 0;
    }

    // Le os pixels da imagem para a matriz estatica float
    for (int i = 0; i < HEIGHT; i++) {
        for (int j = 0; j < WIDTH; j++) {
            int pixel;
            fscanf(arquivo, "%d", &pixel);
            img.original[i][j] = (float)pixel;
        }
    }

    fclose(arquivo);
    return 1;
}


// Função para salvar a imagem resultante em arquivo PGM
void save_pgm(const char *nome_arquivo, float image[HEIGHT][WIDTH]) {
    FILE *arquivo = fopen(nome_arquivo, "w");
    if (!arquivo) {
        printf("Erro ao criar o arquivo %s para escrita.\n", nome_arquivo);
        return;
    }

    // Escreve o cabecalho do PGM P2
    fprintf(arquivo, "P2\n");
    fprintf(arquivo, "%d %d\n", WIDTH, HEIGHT);
    fprintf(arquivo, "255\n");

    // Escreve a matriz resultante tratando o truncamento de limites (0 a 255)
    for (int i = 0; i < HEIGHT; i++) {
        for (int j = 0; j < WIDTH; j++) {
            float val = image[i][j];
            
            if (val < 0.0f) val = 0.0f;
            if (val > 255.0f) val = 255.0f;

            fprintf(arquivo, "%d ", (int)(val + 0.5f)); // Arredondamento simples
        }
        fprintf(arquivo, "\n");
    }

    fclose(arquivo);
}

// Algoritmo Unsharp Masking
void unsharp_masking(float ganho_k) {
    int margem = 3 / 2;
    const char *arquivo_blur = "monalisa-blur.pgm";

    // ETAPA 1: Gerar a imagem suavizada via Convolucao 2D (4 laços aninhados)
    for (int i = 0; i < HEIGHT; i++) {
        for (int j = 0; j < WIDTH; j++) {
            
            // Trata as bordas copiando o pixel original
            if (i < margem || i >= HEIGHT - margem || j < margem || j >= WIDTH - margem) {
                img.suavizada[i][j] = img.original[i][j];
                continue;
            }

            float soma_ponderada = 0.0f;

            // Lacos internos da janela/kernel
            for (int ki = -margem; ki <= margem; ki++) {
                for (int kj = -margem; kj <= margem; kj++) {
                    soma_ponderada += img.original[i + ki][j + kj] * kernel_desfoque[ki + margem][kj + margem];
                }
            }

            img.suavizada[i][j] = soma_ponderada;
        }
    }

    save_pgm(arquivo_blur, img.suavizada);

    // ETAPA 2 e 3: Subtração da Máscara e Soma Ponderada (2 laços aninhados)
    for (int i = 0; i < HEIGHT; i++) {
        for (int j = 0; j < WIDTH; j++) {
            // mascara = original - suavizada
            img.mascara[i][j] = img.original[i][j] - img.suavizada[i][j];

            // imagem_final = original + (k * mascara)
            img.resultado[i][j] = img.original[i][j] + (ganho_k * img.mascara[i][j]);
        }
    }
}

int main() {
    const char *arquivo_entrada = "monalisa.pgm";
    const char *arquivo_mask = "monalisa-mask.pgm";
    const char *arquivo_saida = "monalisa-after.pgm";
    float ganho_k = 3.0f; // Fator de intensidade do realce (tipicamente entre 0.5 e 2.0)

    printf("Iniciando o processamento do Unsharp Masking...\n");

    // 1. Carrega dados de entrada
    if (!load_pgm(arquivo_entrada)) {
        printf("Falha na Leitura. Verifique se 'entrada.pgm' (100x80 PGM P2) existe.\n");
        return 1;
    }

    // 2. Processa o algoritmo
    unsharp_masking(ganho_k);

    // 3. Salva os resultados
    save_pgm(arquivo_saida, img.resultado);
    save_pgm(arquivo_mask, img.mascara);

    printf("Processamento concluido com sucesso!\n");
    printf("Arquivo gerado: %s\n", arquivo_saida);

    return 0;
}