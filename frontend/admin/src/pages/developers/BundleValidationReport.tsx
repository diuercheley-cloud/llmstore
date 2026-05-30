import React, { useState, useCallback } from 'react'
import { Upload, CheckCircle, XCircle, AlertTriangle, FileText, Package } from 'lucide-react'

interface ValidationCheck {
  name: string
  status: 'pass' | 'fail' | 'warn'
  message: string
}

interface BundleManifest {
  name: string
  version: string
  description: string
  author: string
  category: string
  min_platform_version: string
  agent_definition: Record<string, unknown>
  tool_requirements: Array<{ name: string; version: string }>
  eval_suite: Record<string, unknown>
  checksums: Record<string, string>
  signature?: Record<string, string>
}

interface BundleValidationReportProps {
  manifest: BundleManifest | null
  signatureValid: boolean | null
}

export const BundleValidationReport: React.FC<BundleValidationReportProps> = ({ manifest, signatureValid }) => {
  const checks: ValidationCheck[] = []

  if (manifest) {
    // Structure checks
    checks.push({ name: 'manifest_parse', status: 'pass', message: 'manifest.json parsed successfully' })
    checks.push({ name: 'name_present', status: manifest.name ? 'pass' : 'fail', message: manifest.name ? `Name: ${manifest.name}` : 'Missing bundle name' })
    checks.push({ name: 'version_present', status: manifest.version ? 'pass' : 'fail', message: manifest.version ? `Version: ${manifest.version}` : 'Missing version' })
    checks.push({ name: 'author_present', status: manifest.author ? 'pass' : 'warn', message: manifest.author ? `Author: ${manifest.author}` : 'No author defined' })

    // Agent definition
    const ad = manifest.agent_definition
    checks.push({
      name: 'agent_definition',
      status: ad?.instructions && ad?.model_id ? 'pass' : 'fail',
      message: ad?.instructions ? 'Agent definition complete' : 'Missing agent_definition fields (instructions, model_id)',
    })

    // Platform version
    checks.push({
      name: 'platform_version',
      status: manifest.min_platform_version ? 'pass' : 'warn',
      message: manifest.min_platform_version ? `Requires platform >= ${manifest.min_platform_version}` : 'No platform version specified',
    })

    // Tools
    const tools = manifest.tool_requirements || []
    checks.push({
      name: 'tool_requirements',
      status: 'pass',
      message: tools.length > 0 ? `${tools.length} tool(s) required` : 'No external tools required',
    })

    // Eval suite
    const evalCases = (manifest.eval_suite as { cases?: unknown[] })?.cases || []
    checks.push({
      name: 'eval_suite',
      status: evalCases.length > 0 ? 'pass' : 'warn',
      message: evalCases.length > 0 ? `${evalCases.length} eval case(s) defined` : 'No eval cases defined',
    })

    // Signature
    checks.push({
      name: 'signature',
      status: signatureValid === true ? 'pass' : signatureValid === false ? 'fail' : 'warn',
      message: signatureValid === true ? 'Signature verified' : signatureValid === false ? 'Invalid signature' : 'No signature (unsigned)',
    })
  } else {
    checks.push({ name: 'manifest_parse', status: 'fail', message: 'No manifest provided' })
  }

  const passed = checks.filter(c => c.status === 'pass').length
  const failed = checks.filter(c => c.status === 'fail').length
  const warned = checks.filter(c => c.status === 'warn').length

  const statusIcon = (s: string) => {
    switch (s) {
      case 'pass': return <CheckCircle className="w-4 h-4 text-green-500" />
      case 'fail': return <XCircle className="w-4 h-4 text-red-500" />
      case 'warn': return <AlertTriangle className="w-4 h-4 text-amber-500" />
      default: return null
    }
  }

  return (
    <div className="bg-card border border-border rounded-xl p-6">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-lg font-bold flex items-center gap-2">
          <FileText className="w-5 h-5" />
          Validation Report
        </h3>
        <div className="flex gap-3 text-sm">
          <span className="text-green-600">{passed} passed</span>
          {failed > 0 && <span className="text-red-600">{failed} failed</span>}
          {warned > 0 && <span className="text-amber-600">{warned} warnings</span>}
        </div>
      </div>

      <div className="space-y-2">
        {checks.map((check, i) => (
          <div key={i} className="flex items-center gap-3 px-3 py-2 rounded-lg bg-secondary/50 text-sm">
            {statusIcon(check.status)}
            <span className="font-medium min-w-[160px]">{check.name}</span>
            <span className="text-muted-foreground flex-1">{check.message}</span>
          </div>
        ))}
      </div>

      {manifest && (
        <div className="mt-4 pt-4 border-t border-border">
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
            <div><span className="text-muted-foreground">Name:</span> <span className="font-medium">{manifest.name}</span></div>
            <div><span className="text-muted-foreground">Version:</span> <span className="font-medium">{manifest.version}</span></div>
            <div><span className="text-muted-foreground">Category:</span> <span className="font-medium">{manifest.category || 'general'}</span></div>
            <div><span className="text-muted-foreground">Platform:</span> <span className="font-medium">{manifest.min_platform_version || 'any'}</span></div>
          </div>
        </div>
      )}
    </div>
  )
}

export default BundleValidationReport
