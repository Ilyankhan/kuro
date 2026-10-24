#include <stdio.h>
#include <stdlib.h>
#include <string.h>

void print_usage(const char *prog_name) {
    printf("Usage: %s [-e|-d] <text> [-k <key>]\n", prog_name);
    printf("Options:\n");
    printf("  -e <text>   Encrypt text\n");
    printf("  -d <text>   Decrypt text\n");
    printf("  -k <key>    Integer key (1-255, default: 13)\n");
    printf("  -h, --help  Show this help message\n");
}

void transform(char *text, int key, int encrypt) {
    int len = strlen(text);
    int effective_key = encrypt ? key : (26 - (key % 26));
    
    for (int i = 0; i < len; i++) {
        char c = text[i];
        if (c >= 'a' && c <= 'z') {
            text[i] = 'a' + ((c - 'a' + effective_key) % 26);
        } else if (c >= 'A' && c <= 'Z') {
            text[i] = 'A' + ((c - 'A' + effective_key) % 26);
        }
    }
}

int main(int argc, char *argv[]) {
    if (argc < 2) {
        print_usage(argv[0]);
        return 1;
    }

    int mode = 0; // 1 = encrypt, 2 = decrypt
    char *input_text = NULL;
    int key = 13;

    for (int i = 1; i < argc; i++) {
        if (strcmp(argv[i], "-h") == 0 || strcmp(argv[i], "--help") == 0) {
            print_usage(argv[0]);
            return 0;
        } else if (strcmp(argv[i], "-e") == 0) {
            if (i + 1 >= argc) {
                fprintf(stderr, "Error: -e requires an argument\n");
                return 1;
            }
            mode = 1;
            input_text = argv[++i];
        } else if (strcmp(argv[i], "-d") == 0) {
            if (i + 1 >= argc) {
                fprintf(stderr, "Error: -d requires an argument\n");
                return 1;
            }
            mode = 2;
            input_text = argv[++i];
        } else if (strcmp(argv[i], "-k") == 0) {
            if (i + 1 >= argc) {
                fprintf(stderr, "Error: -k requires an integer key\n");
                return 1;
            }
            key = atoi(argv[++i]);
            if (key <= 0 || key > 255) {
                fprintf(stderr, "Error: key must be between 1 and 255\n");
                return 2;
            }
        } else {
            fprintf(stderr, "Unknown option: %s\n", argv[i]);
            print_usage(argv[0]);
            return 1;
        }
    }

    if (mode == 0 || input_text == NULL) {
        fprintf(stderr, "Error: Must specify either -e or -d with text\n");
        return 1;
    }

    char *result = strdup(input_text);
    if (!result) {
        fprintf(stderr, "Memory allocation error\n");
        return 3;
    }

    transform(result, key, mode == 1);
    printf("%s\n", result);
    free(result);

    return 0;
}
