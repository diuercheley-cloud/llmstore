# Agent Bundle Signing

## Overview

Bundle signing provides cryptographic assurance of an agent's authenticity and integrity.

## Signing Process

Publishers use their private keys (ED25519) to sign the bundle manifest. The signature includes the bundle's SHA-256 checksum.

## Configuration

| Flag | Default | Description |
| :--- | :--- | :--- |
| `AGENT_BUNDLE_SIGNATURE_REQUIRED` | `false` | If enabled, the platform will reject any unsigned bundles during installation. |

## Key Management

The platform maintains a registry of verified publisher public keys in the `agent_publisher_profiles` table.
