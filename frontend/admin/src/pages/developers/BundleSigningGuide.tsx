import React from 'react'
import { Shield, Key, Terminal, FileCheck, ArrowRight } from 'lucide-react'
import { PageHeader } from '../../components/layout/PageHeader'

const steps = [
  {
    icon: <Terminal className="w-5 h-5" />,
    title: '1. Generate Key Pair',
    command: 'openssl genpkey -algorithm ed25519 -out ~/.agentctl/keys/default_ed25519.pem',
    description: 'Creates an ed25519 private key for signing. The public key is extracted automatically.',
  },
  {
    icon: <Key className="w-5 h-5" />,
    title: '2. Sign the Bundle',
    command: './scripts/agent-bundle-sign.sh ./my-bundle',
    description: 'Computes SHA-256 checksum of all bundle files and signs it with your private key.',
  },
  {
    icon: <FileCheck className="w-5 h-5" />,
    title: '3. Signature Stored',
    command: 'cat ./my-bundle/bundle.sig',
    description: 'The signature file contains: algorithm, checksum, base64 signature, public key, and timestamp.',
  },
  {
    icon: <Shield className="w-5 h-5" />,
    title: '4. Platform Verification',
    command: '',
    description: 'The platform verifies signatures using the public key. External bundles always require signatures.',
  },
]

export const BundleSigningGuide: React.FC = () => {
  return (
    <div className="space-y-8">
      <PageHeader
        title="Bundle Signing Guide"
        subtitle="How to sign agent bundles for marketplace publication"
        icon={<Shield className="w-5 h-5" />}
      />

      <div className="bg-card border border-border rounded-xl p-6">
        <h3 className="text-lg font-bold mb-4">Why Sign?</h3>
        <ul className="space-y-2 text-sm text-muted-foreground">
          <li className="flex items-start gap-2">
            <ArrowRight className="w-4 h-4 mt-0.5 shrink-0 text-primary" />
            <span><strong>Trust:</strong> Proves the bundle was created by you</span>
          </li>
          <li className="flex items-start gap-2">
            <ArrowRight className="w-4 h-4 mt-0.5 shrink-0 text-primary" />
            <span><strong>Integrity:</strong> Detects tampering since signing</span>
          </li>
          <li className="flex items-start gap-2">
            <ArrowRight className="w-4 h-4 mt-0.5 shrink-0 text-primary" />
            <span><strong>Marketplace:</strong> Required for public marketplace publish</span>
          </li>
          <li className="flex items-start gap-2">
            <ArrowRight className="w-4 h-4 mt-0.5 shrink-0 text-primary" />
            <span><strong>Security:</strong> Internal bundles require signature in production</span>
          </li>
        </ul>
      </div>

      <div className="space-y-4">
        {steps.map((step, i) => (
          <div key={i} className="bg-card border border-border rounded-xl p-6">
            <div className="flex items-center gap-3 mb-3">
              <div className="p-2 bg-primary/10 text-primary rounded-lg">{step.icon}</div>
              <h4 className="font-bold">{step.title}</h4>
            </div>
            <p className="text-sm text-muted-foreground mb-3">{step.description}</p>
            {step.command && (
              <code className="block bg-black text-green-400 px-4 py-3 rounded-lg text-sm font-mono overflow-x-auto">
                $ {step.command}
              </code>
            )}
          </div>
        ))}
      </div>

      <div className="bg-card border border-border rounded-xl p-6">
        <h3 className="text-lg font-bold mb-3">Signature Format</h3>
        <pre className="bg-black text-green-400 px-4 py-3 rounded-lg text-sm font-mono overflow-x-auto">
{`{
  "algorithm": "ed25519",
  "checksum": "a1b2c3d4...",
  "signature": "base64-encoded-signature...",
  "public_key": "base64-encoded-public-key...",
  "signed_at": "2026-05-30T12:00:00Z"
}`}
        </pre>
      </div>
    </div>
  )
}

export default BundleSigningGuide
