import React, { useState } from 'react'
import { Package, Upload, CheckCircle, Shield, Send, Terminal, ArrowRight, ExternalLink } from 'lucide-react'
import { PageHeader } from '../../components/layout/PageHeader'
import { BundleUpload } from './BundleUpload'
import { BundleValidationReport } from './BundleValidationReport'
import { BundleSigningGuide } from './BundleSigningGuide'

type Step = 'upload' | 'validate' | 'test' | 'sign' | 'publish'

const steps: Array<{ key: Step; label: string; icon: React.ReactNode; cli: string }> = [
  { key: 'upload', label: 'Upload', icon: <Upload className="w-4 h-4" />, cli: 'agentctl bundle init' },
  { key: 'validate', label: 'Validate', icon: <CheckCircle className="w-4 h-4" />, cli: 'agent-bundle-validate.sh' },
  { key: 'test', label: 'Test', icon: <Terminal className="w-4 h-4" />, cli: 'agent-bundle-test.sh' },
  { key: 'sign', label: 'Sign', icon: <Shield className="w-4 h-4" />, cli: 'agent-bundle-sign.sh' },
  { key: 'publish', label: 'Publish', icon: <Send className="w-4 h-4" />, cli: 'agent-bundle-publish.sh' },
]

interface Manifest {
  name: string
  version: string
  description?: string
  author?: string
  category?: string
  min_platform_version?: string
  agent_definition?: Record<string, unknown>
  tool_requirements?: Array<{ name: string; version: string }>
  eval_suite?: Record<string, unknown>
  checksums?: Record<string, string>
  signature?: Record<string, string>
  [key: string]: unknown
}

export default function Bundles() {
  const [currentStep, setCurrentStep] = useState<Step>('upload')
  const [manifest, setManifest] = useState<Manifest | null>(null)
  const [signatureValid, setSignatureValid] = useState<boolean | null>(null)
  const [published, setPublished] = useState(false)

  const stepIndex = steps.findIndex(s => s.key === currentStep)

  const handleBundleLoaded = (data: Record<string, unknown>) => {
    setManifest(data as Manifest)
    setSignatureValid(data.signature ? true : null)
    setCurrentStep('validate')
  }

  const handlePublish = () => {
    setPublished(true)
    setCurrentStep('publish')
  }

  return (
    <div className="space-y-8">
      <PageHeader
        title="Agent Bundles"
        subtitle="Create, validate, sign, and publish agent bundles to the marketplace"
        icon={<Package className="w-5 h-5" />}
        badge="Developer"
        badgeVariant="beta"
        actions={
          <a
            href="https://docs.inference-stack.com/developers/bundles"
            target="_blank"
            rel="noopener noreferrer"
            className="btn btn-outline text-sm flex items-center gap-2"
          >
            <ExternalLink size={14} /> Docs
          </a>
        }
      />

      {/* Step Progress */}
      <div className="bg-card border border-border rounded-xl p-4">
        <div className="flex items-center justify-between">
          {steps.map((step, i) => (
            <React.Fragment key={step.key}>
              <button
                onClick={() => i <= stepIndex || (step.key === 'validate' && manifest) ? setCurrentStep(step.key) : undefined}
                className={`
                  flex items-center gap-2 px-3 py-2 rounded-lg text-sm font-medium transition-all
                  ${currentStep === step.key
                    ? 'bg-primary text-primary-foreground'
                    : i < stepIndex || (step.key === 'validate' && manifest)
                      ? 'text-green-600 hover:bg-green-50 cursor-pointer'
                      : 'text-muted-foreground cursor-not-allowed'}
                `}
              >
                {step.icon}
                <span className="hidden sm:inline">{step.label}</span>
              </button>
              {i < steps.length - 1 && (
                <ArrowRight className="w-4 h-4 text-muted-foreground shrink-0" />
              )}
            </React.Fragment>
          ))}
        </div>
      </div>

      {/* Step Content */}
      {currentStep === 'upload' && (
        <BundleUpload onBundleLoaded={handleBundleLoaded} />
      )}

      {currentStep === 'validate' && manifest && (
        <div className="space-y-4">
          <BundleValidationReport manifest={manifest} signatureValid={signatureValid} />
          <div className="flex gap-3">
            <button onClick={() => setCurrentStep('test')} className="btn btn-primary text-sm">
              Continue to Testing
            </button>
            <button onClick={() => setCurrentStep('upload')} className="btn btn-outline text-sm">
              Upload Different Bundle
            </button>
          </div>
        </div>
      )}

      {currentStep === 'test' && (
        <div className="bg-card border border-border rounded-xl p-6 space-y-4">
          <h3 className="text-lg font-bold flex items-center gap-2">
            <Terminal className="w-5 h-5" />
            Bundle Testing
          </h3>
          <div className="bg-black text-green-400 px-4 py-3 rounded-lg text-sm font-mono">
            <p>$ ./scripts/agent-bundle-test.sh ./my-bundle</p>
            <p className="text-muted-foreground mt-2"># Running unit tests...</p>
            <p># Running eval suite...</p>
            <p className="text-green-400"># All tests passed</p>
          </div>
          <p className="text-sm text-muted-foreground">
            Run this command locally to validate your bundle's eval suite and sandbox compatibility.
          </p>
          <div className="flex gap-3">
            <button onClick={() => setCurrentStep('sign')} className="btn btn-primary text-sm">
              Continue to Signing
            </button>
          </div>
        </div>
      )}

      {currentStep === 'sign' && (
        <div className="space-y-4">
          <BundleSigningGuide />
          <div className="flex gap-3">
            <button onClick={() => { setSignatureValid(true); setCurrentStep('publish') }} className="btn btn-primary text-sm">
              Bundle Signed - Continue
            </button>
          </div>
        </div>
      )}

      {currentStep === 'publish' && (
        <div className="bg-card border border-border rounded-xl p-6 space-y-4">
          {published ? (
            <>
              <div className="flex items-center gap-3 p-4 bg-green-50 border border-green-200 rounded-xl">
                <CheckCircle className="w-6 h-6 text-green-600" />
                <div>
                  <h4 className="font-bold text-green-800">Bundle Published!</h4>
                  <p className="text-sm text-green-700">Your bundle is now in draft status. Pending review.</p>
                </div>
              </div>
              <div className="text-sm text-muted-foreground space-y-1">
                <p><strong>Bundle:</strong> {manifest?.name} v{manifest?.version}</p>
                <p><strong>Status:</strong> Draft (pending review)</p>
                <p><strong>Next:</strong> The platform team will review your bundle before it goes live.</p>
              </div>
            </>
          ) : (
            <>
              <h3 className="text-lg font-bold flex items-center gap-2">
                <Send className="w-5 h-5" />
                Publish to Marketplace
              </h3>
              <div className="p-4 bg-amber-50 border border-amber-200 rounded-xl text-sm text-amber-800">
                Publishing will submit your bundle as a draft for review. The bundle must be signed and pass all validation checks.
              </div>
              <div className="bg-black text-green-400 px-4 py-3 rounded-lg text-sm font-mono">
                <p>$ ./scripts/agent-bundle-publish.sh ./my-bundle</p>
                <p className="text-green-400 mt-2"># Bundle published as draft successfully</p>
              </div>
              <button onClick={handlePublish} className="btn btn-primary text-sm">
                Publish Bundle
              </button>
            </>
          )}
        </div>
      )}

      {/* CLI Reference */}
      <div className="bg-card border border-border rounded-xl p-6">
        <h3 className="text-lg font-bold flex items-center gap-2 mb-4">
          <Terminal className="w-5 h-5" />
          CLI Commands
        </h3>
        <div className="space-y-2">
          {[
            { cmd: 'agentctl bundle init my-agent', desc: 'Create bundle skeleton' },
            { cmd: './scripts/agent-bundle-validate.sh ./my-bundle', desc: 'Validate manifest and structure' },
            { cmd: './scripts/agent-bundle-test.sh ./my-bundle', desc: 'Run eval suite and dry-run' },
            { cmd: './scripts/agent-bundle-sign.sh ./my-bundle', desc: 'Sign with ed25519 key' },
            { cmd: './scripts/agent-bundle-publish.sh ./my-bundle', desc: 'Publish as marketplace draft' },
          ].map((item, i) => (
            <div key={i} className="flex items-center gap-4 p-2 rounded-lg hover:bg-secondary/50">
              <code className="text-sm font-mono text-primary min-w-[360px]">$ {item.cmd}</code>
              <span className="text-sm text-muted-foreground">{item.desc}</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}
