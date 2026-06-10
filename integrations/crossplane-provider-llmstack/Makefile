# Makefile for Crossplane Provider

.PHONY: build test lint package clean

build:
	# Crossplane providers are often just metadata + CRDs in a package
	@echo "Validating CRDs..."
	@if command -v kubectl > /dev/null; then kubectl dry-run -f package/crds/resources.yaml; else echo "kubectl not found, skipping dry-run"; fi

test:
	@echo "No unit tests for CRD-only provider yet."

lint:
	@echo "Linting YAML..."
	@if command -v yamllint > /dev/null; then yamllint package/crds/resources.yaml; else echo "yamllint not found, skipping"; fi

package:
	cd package && tar -czvf ../provider-llmstack.xpkg .

clean:
	rm -f provider-llmstack.xpkg
