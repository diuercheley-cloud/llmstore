# Makefile for VS Code Extension

.PHONY: build test lint package clean

build:
	npm install
	npm run compile

test:
	npm run test

lint:
	npm run lint

package: build
	npx vsce package

clean:
	rm -rf out *.vsix node_modules
