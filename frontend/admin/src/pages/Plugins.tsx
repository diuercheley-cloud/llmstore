import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import api from '../lib/api'
import {
  Package,
  Download,
  Trash2,
  ToggleLeft,
  ToggleRight,
  RefreshCw,
  Shield,
  Star,
  Upload,
  AlertTriangle,
} from 'lucide-react'

type PluginInstall = {
  id: string
  plugin_entry_id: string
  current_version_id: string
  install_path: string
  status: string
  is_enabled: boolean
  config_json: Record<string, unknown>
  created_at: string
  updated_at: string
}

type MarketplaceEntry = {
  id: string
  name: string
  description: string
  author: string
  license: string
  plugin_type: string
  official: boolean
  avg_rating: number
  created_at: string
  updated_at: string
}

type PluginVersion = {
  id: string
  plugin_entry_id: string
  version: string
  release_notes: string | null
  checksum_sha256: string
  min_platform_version: string
  created_at: string
}

function fetchInstalls(): Promise<PluginInstall[]> {
  return api.get('/admin/plugins/installs').then((r) => r.data)
}

function fetchMarketplace(): Promise<MarketplaceEntry[]> {
  return api.get('/admin/plugins/marketplace').then((r) => r.data)
}

function fetchVersions(entryId: string): Promise<PluginVersion[]> {
  return api.get(`/admin/plugins/${entryId}/versions`).then((r) => r.data)
}

type TrustReport = {
  id: string
  trust_score: number
  vulnerabilities_found: number
  report_details: Record<string, unknown>
  is_signed: boolean
  signer_identity: string | null
  scanned_at: string
}

function fetchTrustReport(installId: string): Promise<TrustReport> {
  return api.get(`/admin/plugins/${installId}/trust-report`).then((r) => r.data)
}

function PluginRow({
  install,
  entry,
  onRefresh,
}: {
  install: PluginInstall
  entry?: MarketplaceEntry
  onRefresh: () => void
}) {
  const [showTrust, setShowTrust] = useState(false)
  const [trustReport, setTrustReport] = useState<TrustReport | null>(null)
  const [showVersions, setShowVersions] = useState(false)
  const [versions, setVersions] = useState<PluginVersion[]>([])

  const queryClient = useQueryClient()

  const enableMutation = useMutation({
    mutationFn: () => api.post(`/admin/plugins/${install.id}/enable`),
    onSuccess: () => { queryClient.invalidateQueries({ queryKey: ['installs'] }); onRefresh() },
  })

  const disableMutation = useMutation({
    mutationFn: () => api.post(`/admin/plugins/${install.id}/disable`),
    onSuccess: () => { queryClient.invalidateQueries({ queryKey: ['installs'] }); onRefresh() },
  })

  const uninstallMutation = useMutation({
    mutationFn: () => api.delete(`/admin/plugins/${install.id}`),
    onSuccess: () => { queryClient.invalidateQueries({ queryKey: ['installs'] }); onRefresh() },
  })

  const handleTrust = async () => {
    if (!showTrust) {
      try {
        const report = await fetchTrustReport(install.id)
        setTrustReport(report)
      } catch {
        setTrustReport(null)
      }
    }
    setShowTrust(!showTrust)
  }

  const handleVersions = async () => {
    if (!showVersions) {
      try {
        const v = await fetchVersions(install.plugin_entry_id)
        setVersions(v)
      } catch {
        setVersions([])
      }
    }
    setShowVersions(!showVersions)
  }

  return (
    <div className="bg-white rounded-2xl border border-slate-200 p-5">
      <div className="flex items-start justify-between">
        <div className="flex items-start gap-4">
          <div className={`p-3 rounded-xl ${install.is_enabled ? 'bg-teal-50 text-teal-600' : 'bg-slate-100 text-slate-400'}`}>
            <Package className="w-6 h-6" />
          </div>
          <div>
            <h3 className="font-bold text-lg text-slate-900">{entry?.name ?? install.id.slice(0, 8)}</h3>
            <p className="text-sm text-slate-500 mt-0.5">{entry?.description ?? ''}</p>
            <div className="flex items-center gap-3 mt-2 text-xs text-slate-400">
              <span className="px-2 py-0.5 bg-slate-100 rounded-full">{entry?.plugin_type ?? 'unknown'}</span>
              <span>v{entry ? '?' : '-'}</span>
              <span className={`flex items-center gap-1 ${install.is_enabled ? 'text-teal-600' : 'text-slate-400'}`}>
                <span className={`w-2 h-2 rounded-full ${install.is_enabled ? 'bg-teal-500' : 'bg-slate-300'}`} />
                {install.is_enabled ? 'Enabled' : 'Disabled'}
              </span>
              <span className="text-slate-300">|</span>
              <span>Status: {install.status}</span>
            </div>
          </div>
        </div>
        <div className="flex items-center gap-2">
          {install.is_enabled ? (
            <button
              onClick={() => disableMutation.mutate()}
              className="p-2 rounded-lg hover:bg-amber-50 text-amber-600 transition-colors"
              title="Disable"
            >
              <ToggleRight className="w-5 h-5" />
            </button>
          ) : (
            <button
              onClick={() => enableMutation.mutate()}
              className="p-2 rounded-lg hover:bg-teal-50 text-teal-600 transition-colors"
              title="Enable"
            >
              <ToggleLeft className="w-5 h-5" />
            </button>
          )}
          <button
            onClick={handleTrust}
            className="p-2 rounded-lg hover:bg-purple-50 text-purple-600 transition-colors"
            title="Trust Report"
          >
            <Shield className="w-5 h-5" />
          </button>
          <button
            onClick={() => uninstallMutation.mutate()}
            className="p-2 rounded-lg hover:bg-red-50 text-red-500 transition-colors"
            title="Uninstall"
          >
            <Trash2 className="w-5 h-5" />
          </button>
        </div>
      </div>

      {showTrust && (
        <div className="mt-4 p-4 bg-purple-50 rounded-xl text-sm">
          <div className="flex items-center justify-between mb-2">
            <span className="font-bold text-purple-800">Trust Report</span>
            <button onClick={() => setShowTrust(false)} className="text-purple-400 hover:text-purple-600">✕</button>
          </div>
          {trustReport ? (
            <div className="grid grid-cols-3 gap-3 text-purple-700">
              <div>
                <span className="text-purple-500 text-xs">Score</span>
                <p className="font-bold">{(trustReport.trust_score * 100).toFixed(0)}%</p>
              </div>
              <div>
                <span className="text-purple-500 text-xs">Vulnerabilities</span>
                <p className="font-bold">{trustReport.vulnerabilities_found}</p>
              </div>
              <div>
                <span className="text-purple-500 text-xs">Signed</span>
                <p className="font-bold">{trustReport.is_signed ? 'Yes' : 'No'}</p>
              </div>
              {trustReport.signer_identity && (
                <div className="col-span-3">
                  <span className="text-purple-500 text-xs">Signer</span>
                  <p className="font-mono text-xs">{trustReport.signer_identity}</p>
                </div>
              )}
            </div>
          ) : (
            <p className="text-purple-500">No trust report available for this version.</p>
          )}
        </div>
      )}

      {showVersions && (
        <div className="mt-4 p-4 bg-slate-50 rounded-xl text-sm">
          <div className="flex items-center justify-between mb-2">
            <span className="font-bold text-slate-700">Versions</span>
            <button onClick={() => setShowVersions(false)} className="text-slate-400 hover:text-slate-600">✕</button>
          </div>
          {versions.length > 0 ? (
            <div className="space-y-2">
              {versions.map((v) => (
                <div key={v.id} className="flex items-center justify-between text-slate-600">
                  <span className="font-mono">{v.version}</span>
                  <span className="text-xs text-slate-400">SHA256: {v.checksum_sha256.slice(0, 16)}...</span>
                </div>
              ))}
            </div>
          ) : (
            <p className="text-slate-400">No version info available.</p>
          )}
        </div>
      )}
    </div>
  )
}

export default function Plugins() {
  const [uploading, setUploading] = useState(false)
  const queryClient = useQueryClient()

  const { data: installs, isLoading } = useQuery({
    queryKey: ['installs'],
    queryFn: fetchInstalls,
  })

  const { data: marketplace } = useQuery({
    queryKey: ['marketplace'],
    queryFn: fetchMarketplace,
  })

  const entryMap = new Map<string, MarketplaceEntry>()
  if (marketplace) {
    for (const e of marketplace) entryMap.set(e.id, e)
  }

  const handleUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (!file) return
    setUploading(true)
    try {
      const form = new FormData()
      form.append('file', file)
      await api.post('/admin/plugins/install', form)
      queryClient.invalidateQueries({ queryKey: ['installs'] })
      queryClient.invalidateQueries({ queryKey: ['marketplace'] })
    } catch (err) {
      console.error('Install failed', err)
    } finally {
      setUploading(false)
      e.target.value = ''
    }
  }

  return (
    <div className="max-w-5xl mx-auto px-4 py-8">
      <div className="flex items-center justify-between mb-8">
        <div>
          <h1 className="text-2xl font-black tracking-tight">Plugins</h1>
          <p className="text-sm text-slate-500 mt-1">Gerenciar plugins do ecossistema</p>
        </div>
        <div className="flex items-center gap-3">
          <label className="flex items-center gap-2 px-4 py-2.5 bg-teal-600 text-white rounded-xl font-bold text-sm hover:bg-teal-700 cursor-pointer transition-colors">
            <Upload className="w-4 h-4" />
            {uploading ? 'Installing...' : 'Install Plugin'}
            <input type="file" accept=".zip,.tar,.tar.gz,.tgz" onChange={handleUpload} className="hidden" disabled={uploading} />
          </label>
          <button
            onClick={() => queryClient.invalidateQueries({ queryKey: ['installs'] })}
            className="p-2.5 rounded-xl border border-slate-200 hover:bg-slate-50 transition-colors"
          >
            <RefreshCw className="w-4 h-4 text-slate-500" />
          </button>
        </div>
      </div>

      {isLoading && (
        <div className="text-center py-12 text-slate-400">
          <Package className="w-12 h-12 mx-auto mb-3 opacity-50" />
          <p>Carregando plugins...</p>
        </div>
      )}

      {installs && installs.length === 0 && (
        <div className="text-center py-16">
          <div className="p-6 bg-slate-100 rounded-3xl inline-flex mb-4">
            <Package className="w-10 h-10 text-slate-400" />
          </div>
          <h2 className="text-xl font-bold text-slate-700 mb-2">Nenhum plugin instalado</h2>
          <p className="text-slate-500 text-sm max-w-md mx-auto">
            Faça upload de um arquivo .zip ou .tar.gz contendo um manifest.json válido para instalar um plugin.
          </p>
        </div>
      )}

      {installs && installs.length > 0 && (
        <div className="space-y-4">
          {installs.map((install) => (
            <PluginRow
              key={install.id}
              install={install}
              entry={entryMap.get(install.plugin_entry_id)}
              onRefresh={() => queryClient.invalidateQueries({ queryKey: ['installs', 'marketplace'] })}
            />
          ))}
        </div>
      )}
    </div>
  )
}
