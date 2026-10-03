/**
 * ============================================================================
 * @file unsharp_masking.c
 * @brief Implementação do algoritmo Unsharp Masking para imagens PGM P2.
 *
 * @details
 * Este programa implementa o algoritmo de realce de imagens conhecido como
 * Unsharp Masking. O método consiste em suavizar a imagem original utilizando
 * um filtro Gaussiano, obter uma máscara de detalhes através da diferença
 * entre a imagem original e a imagem suavizada e, por fim, adicionar essa
 * máscara à imagem original para realçar suas bordas e detalhes.
 *
 * O processamento é realizado utilizando imagens no formato PGM P2, com
 * pixels representados por valores inteiros.
 *
 * ---------------------------------------------------------------------------
 * ENTRADA:
 *   - Arquivo de imagem no formato PGM P2.
 *   - A imagem deve possuir dimensões máximas de 512x512 pixels.
 *
 * SAIDA:
 *   - Arquivo de imagem processada no formato PGM P2.
 *   - A imagem de saída possui as mesmas dimensões e valor máximo da imagem
 *     de entrada.
 *
 * ---------------------------------------------------------------------------
 * COMO USAR:
 *
 * Compilação:
 *   gcc unsharp_mask.c -o unsharp_mask
 *
 * Execução:
 *   ./unsharp_masking <imagem_entrada.pgm> <imagem_saida.pgm>
 *
 * Exemplo:
 *   ./unsharp_masking images/monalisa.pgm resultado.pgm
 *
 * ---------------------------------------------------------------------------
 * ALGORITMO:
 *
 * O processamento é dividido em três etapas principais:
 *
 *   1. Suavização:
 *      A imagem original é convoluída com um filtro Gaussiano 3x3,
 *      produzindo uma versão suavizada da imagem.
 *
 *   2. Geração da máscara:
 *      A máscara de detalhes é obtida pela diferença entre a imagem original
 *      e a imagem suavizada:
 *
 *          mascara = original - suavizada
 *
 *   3. Realce:
 *      A máscara é adicionada à imagem original, multiplicada pelo fator
 *      de intensidade k:
 *
 *          imagem_final = original + (k * mascara)
 *
 * ---------------------------------------------------------------------------
 * CONTEXTO:
 *   Trabalho desenvolvido para a disciplina de Sistemas Embarcados,
 *   com o objetivo de implementar e documentar um algoritmo de processamento
 *   digital de imagens utilizando a linguagem C.
 *
 * ---------------------------------------------------------------------------
 * AUTORES:
 *   - Antônio Carlos Ferreira de Sousa
 *   - Caio Veras Mota Barreto Alencar
 *
 * ---------------------------------------------------------------------------
 * DATA:
 *   02/10/2026
 *
 * ---------------------------------------------------------------------------
 * COPYRIGHT E PERMISSÃO DE USO:
 *
 * Copyright (c) [ANO] [NOME DOS AUTORES]
 *
 * Este código foi desenvolvido para fins acadêmicos no contexto da disciplina
 * mencionada acima. É permitida a utilização, cópia e modificação do código
 * para fins educacionais, desde que os autores originais sejam devidamente
 * citados.
 *
 * ---------------------------------------------------------------------------
 * PLATAFORMA ALVO:
 *   - Linguagem: C
 *   - Compilador: GCC
 *   - Sistema operacional alvo: Linux
 *   - Arquitetura: compatível com sistemas que suportem a linguagem C
 *
 * ============================================================================
 */

#include <stdio.h>
#include <stdlib.h>


/**
 * @brief Altura máxima suportada pela aplicação.
 *
 * Define a quantidade máxima de linhas que podem ser armazenadas nas matrizes
 * utilizadas pelo programa.
 */
#define MAX_HEIGHT 512


/**
 * @brief Largura máxima suportada pela aplicação.
 *
 * Define a quantidade máxima de colunas que podem ser armazenadas nas matrizes
 * utilizadas pelo programa.
 */
#define MAX_WIDTH 512


/**
 * @struct DadosImagem
 * @brief Armazena os dados das imagens utilizadas durante o processamento.
 *
 * A estrutura contém duas matrizes:
 *
 * - original: armazena os pixels da imagem de entrada;
 * - resultado: armazena inicialmente a imagem suavizada e posteriormente
 *   a imagem resultante do Unsharp Masking.
 *
 * As matrizes utilizam são do tipo float para permitir que os cálculos
 * realizados durante a convolução e o realce sejam feitos com maior precisão.
 */
typedef struct {
    float original[MAX_HEIGHT][MAX_WIDTH];
    float resultado[MAX_HEIGHT][MAX_WIDTH];
} DadosImagem;


/**
 * @brief Estrutura global contendo os dados da imagem.
 */
static DadosImagem img;


/**
 * @brief Formato do arquivo de imagem.
 *
 * Armazena a identificação do formato PGM lido do arquivo.
 * O formato esperado é "P2".
 */
char formato[3];


/**
 * @brief Valor máximo permitido para os pixels da imagem.
 */
unsigned int max_valor;


/**
 * @brief Altura da imagem em pixels.
 */
unsigned int height;


/**
 * @brief Largura da imagem em pixels.
 */
unsigned int width;


/**
 * @brief Kernel Gaussiano utilizado para suavização da imagem.
 */
static const float kernel_desfoque[3][3] = {
    {0.07511361f, 0.12384140f, 0.07511361f},
    {0.12384140f, 0.20417996f, 0.12384140f},
    {0.07511361f, 0.12384140f, 0.07511361f}
};


/**
 * @brief Realiza o tratamento de bordas através de espelhamento.
 *
 * Quando a janela do filtro ultrapassa os limites da imagem, esta função
 * converte o índice inválido em um índice válido utilizando espelhamento.
 *
 * Exemplos:
 *   - Um índice -1 é convertido para 1.
 *   - Um índice que ultrapassa o limite máximo é refletido para dentro da imagem.
 *
 * @param p Índice que pode estar fora dos limites da imagem.
 * @param max Limite máximo da dimensão correspondente.
 *
 * @return Índice válido após a aplicação do espelhamento.
 */
int refletir_indice(int p, int max) {

    // Caso o índice seja negativo, realiza o espelhamento para a direita.
    if (p < 0) {
        return -p;
    }

    // Caso o índice ultrapasse ou seja igual ao tamanho máximo, realiza o espelhamento para a esquerda.
    if (p >= max) {
        return 2 * max - p - 2;
    }

    // Caso o índice já esteja dentro dos limites da imagem, ele é retornado sem alterações.
    return p;
}


/**
 * @brief Carrega uma imagem PGM P2 para a memória.
 *
 * Abre o arquivo de entrada, verifica se ele está no formato PGM P2,
 * lê as dimensões e o valor máximo dos pixels e carrega todos
 * os pixels para a matriz global img.original.
 *
 * @param arquivo_entrada Caminho para o arquivo PGM P2 de entrada.
 *
 * @return
 *   - 0 se a imagem foi carregada com sucesso;
 *   - 1 caso ocorra algum erro durante a abertura ou leitura do arquivo.
 */
int load_image(const char *arquivo_entrada) {

    // Abre o arquivo de entrada no modo leitura.
    FILE *arquivo = fopen(arquivo_entrada, "r");

    // Verifica se o arquivo foi aberto corretamente.
    if (!arquivo) {
        printf("Erro ao abrir o arquivo %s para leitura.\n", arquivo_entrada);
        return 1;
    }

    // Lê o identificador do formato PGM.
    if (fscanf(arquivo, "%2s", formato) != 1 ||
        formato[0] != 'P' ||
        formato[1] != '2') {

        printf("Erro: O arquivo deve estar no formato PGM P2.\n");
        fclose(arquivo);
        return 1;
    }

    // Lê do cabeçalho:
    if (fscanf(arquivo, "%d %d %d", &width, &height, &max_valor) != 3) {
        printf("Erro ao ler dimensoes do cabecalho PGM.\n");
        fclose(arquivo);
        return 1;
    }

    // Verifica o tamanho ocupado pela imagem
    if (width * height * sizeof(float) < 8000) {
        printf("Erro! A entrada deve ser de pelo menos 8Kbytes.\n");
        return 1;
    }

    // Percorre todas as posições da imagem e lê os valores dos pixels.
    for (int i = 0; i < height; i++) {

        for (int j = 0; j < width; j++) {

            int pixel;

            fscanf(arquivo, "%d", &pixel);

            img.original[i][j] = (float)pixel;
        }
    }

    // Fecha o arquivo após a leitura.
    fclose(arquivo);

    return 0;
}


/**
 * @brief Salva a imagem processada em um arquivo PGM P2.
 *
 * Cria o arquivo de saída, escreve o cabeçalho PGM e, em seguida,
 * grava os valores armazenados na matriz global img.resultado.
 *
 * @param arquivo_saida Caminho para o arquivo PGM P2 de saída.
 *
 * @return void
 */
void save_image(const char *arquivo_saida) {

    // Abre o arquivo de saída no modo escrita.
    FILE *arquivo = fopen(arquivo_saida, "w");

    // Verifica se foi possível criar o arquivo.
    if (!arquivo) {
        printf("Erro ao criar o arquivo %s para escrita.\n", arquivo_saida);
        return;
    }

    // Escreve o cabeçalho do arquivo PGM P2.
    fprintf(arquivo, "P2\n");
    fprintf(arquivo, "%d %d\n", width, height);
    fprintf(arquivo, "%d\n", max_valor);

    // Percorre todos os pixels da imagem resultante.
    for (int i = 0; i < height; i++) {

        for (int j = 0; j < width; j++) {

            float val = img.resultado[i][j];

            // Garante que nenhum pixel fique abaixo do limite inferior permitido para uma imagem PGM.
            if (val < 0.0f)
                val = 0.0f;

            // Garante que nenhum pixel ultrapasse o valor máximo.
            if (val > 255.0f)
                val = 255.0f;

            // Converte o valor float para inteiro.
            fprintf(arquivo, "%d ", (int)(val + 0.5f));
        }

        fprintf(arquivo, "\n");
    }

    // Fecha o arquivo após a gravação.
    fclose(arquivo);
}


/**
 * @brief Executa o algoritmo de Unsharp Masking.
 *
 * O processamento é realizado em três etapas:
 *
 * 1. Suavização da imagem original utilizando um filtro Gaussiano 3x3;
 * 2. Cálculo da máscara de detalhes através da diferença entre a imagem
 *    original e a imagem suavizada;
 * 3. Aplicação da máscara sobre a imagem original para realizar o realce.
 *
 * A matriz img.resultado é reutilizada entre as etapas. Inicialmente,
 * ela armazena a imagem suavizada e posteriormente é sobrescrita com
 * a imagem final.
 *
 * A utilização da mesma matriz evita a necessidade de criar uma terceira
 * matriz para armazenar a imagem suavizada.
 *
 * @param ganho_k Fator de intensidade utilizado no realce da imagem.
 *                Quanto maior o valor, maior a contribuição da máscara
 *                de detalhes no resultado.
 *
 * @return void
 */
void unsharp_masking(float ganho_k) {

    /*
     * ================================================================
     * ETAPA 1 — SUAVIZAÇÃO DA IMAGEM
     * ================================================================
     *
     * Nesta etapa, cada pixel da imagem original é substituído por uma
     * combinação ponderada de seus vizinhos.
     */
    for (int i = 0; i < height; i++) {

        for (int j = 0; j < width; j++) {

            // Acumula o resultado da convolução do kernel com os vizinhos do pixel atual.
            float soma_ponderada = 0.0f;

            // Percorre as linhas do kernel
            for (int ki = -1; ki <= 1; ki++) {

                // Percorre as três colunas do kernel
                for (int kj = -1; kj <= 1; kj++) {

                    // Calcula os índices correspondentes na imagem.
                    int idx_i = refletir_indice(i + ki, height);
                    int idx_j = refletir_indice(j + kj, width);

                    // Realiza a convolução:
                    soma_ponderada += img.original[idx_i][idx_j] * kernel_desfoque[ki + 1][kj + 1];
                }
            }

            //  Armazena temporariamente a imagem suavizada.
            //  A matriz resultado será posteriormente reutilizada para armazenar a imagem final.
            img.resultado[i][j] = soma_ponderada;
        }
    }


    /*
     * ================================================================
     * ETAPA 2 E 3 — MÁSCARA E REALCE
     * ================================================================
     *
     * Primeiro é calculada a máscara de detalhes:
     *
     *     mascara = original - suavizada
     *
     * Depois a máscara é adicionada à imagem original:
     *
     *     imagem_final = original + (k * mascara)
     */
    for (int i = 0; i < height; i++) {

        for (int j = 0; j < width; j++) {

            /*
             * Calcula a máscara de detalhes.
             *
             * Regiões onde existe uma grande diferença entre o pixel
             * original e o pixel suavizado correspondem principalmente
             * a regiões de borda e detalhes.
             */
            float mascara = img.original[i][j] - img.resultado[i][j];

            // Aplica a máscara sobre a imagem original.
            img.resultado[i][j] = img.original[i][j] + (ganho_k * mascara);
        }
    }
}


/**
 * @brief Função principal da aplicação.
 *
 * Obtém os caminhos dos arquivos de entrada e saída através dos argumentos
 * fornecidos pela linha de comando, carrega a imagem, executa o algoritmo
 * Unsharp Masking e salva o resultado.
 *
 * @param argc Quantidade de argumentos fornecidos pela linha de comando.
 * @param argv Vetor contendo os argumentos da linha de comando.
 *
 * @return
 *   - 0 se o processamento for concluído;
 *   - 1 caso ocorra erro no carregamento da imagem.
 *
 * @note
 * Os argumentos esperados são:
 *   argv[0] -> nome do executável;
 *   argv[1] -> caminho da imagem de entrada;
 *   argv[2] -> caminho da imagem de saída.
 */
int main(int argc, char *argv[]) {
    // Fator de intensidade do realce.
    float ganho_k = 1.0f;

    //  Carrega a imagem de entrada.
    //  argv[1] contém o caminho fornecido pelo usuário.
    if (load_image(argv[1])) {
        return 1;
    }

    // Executa o algoritmo de Unsharp Masking utilizando o fator de intensidade definido em ganho_k.
    unsharp_masking(ganho_k);

    // Salva a imagem resultante no caminho especificado em argv[2].
    save_image(argv[2]);

    return 0;
}
