# Makefile for Terraform Provider

BINARY=terraform-provider-llmstack

.PHONY: build test lint package clean

build:
	go build -o ${BINARY} main.go

test:
	go test ./...

lint:
	go fmt ./...
	go vet ./...

package: build
	tar -czvf ${BINARY}.tar.gz ${BINARY}

clean:
	rm -f ${BINARY} ${BINARY}.tar.gz
