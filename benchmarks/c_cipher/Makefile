CC ?= gcc
CFLAGS ?= -Wall -Wextra -O2

all: cipher cipher_stripped

cipher: main.c
	$(CC) $(CFLAGS) -o cipher main.c

cipher_stripped: cipher
	cp cipher cipher_stripped
	strip --strip-all cipher_stripped

clean:
	rm -f cipher cipher_stripped

.PHONY: all clean
