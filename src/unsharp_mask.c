#include <stdio.h>
#include <stdlib.h>

static const float kernel_desfoque[3][3] = {
    {0.07511361f, 0.12384140f, 0.07511361f},
    {0.12384140f, 0.20417996f, 0.12384140f},
    {0.07511361f, 0.12384140f, 0.07511361f}
};

// Função auxiliar que aplica o tratamento de borda (espelhamento)
int refletir_indice(int p, int max) {
    if (p < 0) {
        return -p;                  // Espelha para a direita se for negativo (ex: -1 vira 1)
    }
    if (p >= max) {
        return 2 * max - p - 2;     // Espelha para a esquerda se estourar o limite maximo
    }
    return p;
}

// Algoritmo Unsharp Masking
void unsharp_masking(const char *arquivo_entrada, const char *arquivo_saida, float ganho_k) {
    // ========== CARREGA A IMAGEM ==========
    FILE *arquivo = fopen(arquivo_entrada, "r");
    if (!arquivo) {
        printf("Erro ao abrir o arquivo %s para leitura.\n", arquivo_entrada);
        return;
    }

    char formato[3];
    unsigned int max_valor, height, width;

    // Le o cabecalho da imagem PGM
    if (fscanf(arquivo, "%2s", formato) != 1 || formato[0] != 'P' || formato[1] != '2') {
        printf("Erro: O arquivo deve estar no formato PGM P2.\n");
        fclose(arquivo);
        return;
    }

    if (fscanf(arquivo, "%d %d %d", &width, &height, &max_valor) != 3) {
        printf("Erro ao ler dimensoes do cabecalho PGM.\n");
        fclose(arquivo);
        return;
    }

    float original[height][width];
    float resultado[height][width];

    // Le os pixels da imagem para a matriz estatica float "original"
    for (int i = 0; i < height; i++) {
        for (int j = 0; j < width; j++) {
            int pixel;
            fscanf(arquivo, "%d", &pixel);
            original[i][j] = (float)pixel;
        }
    }

    fclose(arquivo);


    // ========== PROCESSAMENTO DO UNSHARP MASKING ==========
    int margem = 3 / 2;

    // ETAPA 1: Gerar a imagem suavizada com filtro gaussiano
    for (int i = 0; i < height; i++) {
        for (int j = 0; j < width; j++) {
            float soma_ponderada = 0.0f;

            // Laços internos do kernel
            for (int ki = -margem; ki <= margem; ki++) {
                for (int kj = -margem; kj <= margem; kj++) {
                    // Calcula os índices refletidos caso a janela saia da imagem
                    int idx_i = refletir_indice(i + ki, height);
                    int idx_j = refletir_indice(j + kj, width);

                    soma_ponderada += original[idx_i][idx_j] * kernel_desfoque[ki + margem][kj + margem];
                }
            }

            // Utiliza a matriz "resultado" para guardar a imagem suavizada, evitando uma matriz "suavizada" intermediária
            resultado[i][j] = soma_ponderada;  
        }
    }

    // ETAPA 2 e 3: Subtração da Máscara e Soma Ponderada (2 laços aninhados)
    for (int i = 0; i < height; i++) {
        for (int j = 0; j < width; j++) {
            // mascara = original - suavizada
            float mascara = original[i][j] - resultado[i][j];

            // imagem_final = original + (k * mascara)
            resultado[i][j] = original[i][j] + (ganho_k * mascara);  // Utiliza a mesma matriz "resultado" para guardar a imagem final
        }
    }


    // ========== SALVANDO IMAGEM PROCESSADA ==========
    arquivo = fopen(arquivo_saida, "w");
    if (!arquivo) {
        printf("Erro ao criar o arquivo %s para escrita.\n", arquivo_saida);
        return;
    }

    // Escreve o cabecalho do PGM P2
    fprintf(arquivo, "P2\n");
    fprintf(arquivo, "%d %d\n", width, height);
    fprintf(arquivo, "%d\n", max_valor);

    // Escreve a matriz resultante tratando o truncamento de limites (0 a 255)
    for (int i = 0; i < height; i++) {
        for (int j = 0; j < width; j++) {
            float val = resultado[i][j];
            
            if (val < 0.0f) val = 0.0f;
            if (val > 255.0f) val = 255.0f;

            fprintf(arquivo, "%d ", (int)(val + 0.5f)); // Arredondamento simples
        }
        fprintf(arquivo, "\n");
    }

    fclose(arquivo);
}

int main(int argc, char *argv[]) {
    float ganho_k = 1.0f; // Fator de intensidade do realce

    printf("Iniciando o processamento do Unsharp Masking\n");

    unsharp_masking(argv[1], argv[2], ganho_k);

    printf("Processamento concluido com sucesso!\n");
    printf("Arquivo gerado: %s\n", argv[2]);
    printf("===========================================================");

    return 0;
}
