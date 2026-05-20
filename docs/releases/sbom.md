# Entendendo o SBOM (Software Bill of Materials)

O SBOM é o "rótulo de ingredientes" do nosso software. Ele é gerado automaticamente durante o processo de release e armazenado em:
`artifacts/releases/<versao>/python-sbom.txt`
`artifacts/releases/<versao>/node-sbom.json`

## Como usar o SBOM
Em caso de um alerta de segurança em uma biblioteca específica (ex: `requests` ou `lodash`), você pode verificar instantaneamente se a versão instalada na sua stack é vulnerável consultando estes arquivos.

## Formatos Suportados
Atualmente geramos formatos de texto simples e JSON. Futuras versões suportarão padrões como SPDX ou CycloneDX.
