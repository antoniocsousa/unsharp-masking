#include <stdio.h>
#include <stdlib.h>

#define MAX_HEIGHT 512
#define MAX_WIDTH 512

typedef struct {
    float original[MAX_HEIGHT][MAX_WIDTH];
    float resultado[MAX_HEIGHT][MAX_WIDTH];
} DadosImagem;

static DadosImagem img;

char formato[3];
unsigned int max_valor, height, width;

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

// ========== CARREGA A IMAGEM ==========
int load_image(const char *arquivo_entrada) {
    FILE *arquivo = fopen(arquivo_entrada, "r");
    if (!arquivo) {
        printf("Erro ao abrir o arquivo %s para leitura.\n", arquivo_entrada);
        return 1;
    }

    // Le o cabecalho da imagem PGM
    if (fscanf(arquivo, "%2s", formato) != 1 || formato[0] != 'P' || formato[1] != '2') {
        printf("Erro: O arquivo deve estar no formato PGM P2.\n");
        fclose(arquivo);
        return 1;
    }

    if (fscanf(arquivo, "%d %d %d", &width, &height, &max_valor) != 3) {
        printf("Erro ao ler dimensoes do cabecalho PGM.\n");
        fclose(arquivo);
        return 1;
    }
    
    if (width*height*sizeof(float) < 8000) {
        printf("Erro! A entrada deve ser de pelo menos 8Kbytes.\n");
        return 1;
    }
    
    // Le os pixels da imagem para a matriz estatica float "original"
    for (int i = 0; i < height; i++) {
        for (int j = 0; j < width; j++) {
            int pixel;
            fscanf(arquivo, "%d", &pixel);
            img.original[i][j] = (float)pixel;
        }
    }

    fclose(arquivo);
    return 0;
}

// ========== SALVA IMAGEM PROCESSADA ==========
void save_image(const char *arquivo_saida) {
    FILE *arquivo = fopen(arquivo_saida, "w");
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
            float val = img.resultado[i][j];
            
            if (val < 0.0f) val = 0.0f;
            if (val > 255.0f) val = 255.0f;

            fprintf(arquivo, "%d ", (int)(val + 0.5f)); // Arredondamento simples
        }
        fprintf(arquivo, "\n");
    }

    fclose(arquivo);
}

// ========== PROCESSAMENTO DO UNSHARP MASKING ==========
void unsharp_masking(float ganho_k) {
    // ETAPA 1: Gerar a imagem suavizada com filtro gaussiano
    for (int i = 0; i < height; i++) {
        for (int j = 0; j < width; j++) {
            float soma_ponderada = 0.0f;

            // Laços internos do kernel
            for (int ki = -1; ki <= 1; ki++) {
                for (int kj = -1; kj <= 1; kj++) {
                    // Calcula os índices refletidos caso a janela saia da imagem
                    int idx_i = refletir_indice(i + ki, height);
                    int idx_j = refletir_indice(j + kj, width);

                    soma_ponderada += img.original[idx_i][idx_j] * kernel_desfoque[ki + 1][kj + 1];
                }
            }

            // Utiliza a matriz "resultado" para guardar a imagem suavizada, evitando uma matriz "suavizada" intermediária
            img.resultado[i][j] = soma_ponderada;  
        }
    }

    // ETAPA 2 e 3: Subtração da Máscara e Soma Ponderada (2 laços aninhados)
    for (int i = 0; i < height; i++) {
        for (int j = 0; j < width; j++) {
            // mascara = original - suavizada
            float mascara = img.original[i][j] - img.resultado[i][j];

            // imagem_final = original + (k * mascara)
            img.resultado[i][j] = img.original[i][j] + (ganho_k * mascara);  // Utiliza a mesma matriz "resultado" para guardar a imagem final
        }
    }
}

int main(int argc, char *argv[]) {
    float ganho_k = 1.0f; // Fator de intensidade do realce

    if (load_image(argv[1])) {
        return 1;
    }

    unsharp_masking(ganho_k);

    save_image(argv[2]);

    return 0;
}
