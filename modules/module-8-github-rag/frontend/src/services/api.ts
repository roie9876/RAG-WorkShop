import axios from 'axios'
import type { QueryResponse, QueryConfig, RepoStatus, SyncStatus } from '../types'

const api = axios.create({ baseURL: '/api' })

/* ---- Repos ---- */

export async function indexRepo(repoUrl: string, enableGraphrag = true, forceReindex = false) {
  const { data } = await api.post('/repos/index', { repo_url: repoUrl, enable_graphrag: enableGraphrag, force_reindex: forceReindex })
  return data
}

export async function syncRepo(repoUrl: string, rebuildGraphrag = false) {
  const { data } = await api.post('/repos/sync', { repo_url: repoUrl, rebuild_graphrag: rebuildGraphrag })
  return data
}

export async function getRepoStatus(owner: string, name: string): Promise<RepoStatus> {
  const { data } = await api.get(`/repos/status/${owner}/${name}`)
  return data
}

export async function getSyncStatus(owner: string, name: string): Promise<SyncStatus> {
  const { data } = await api.get(`/repos/sync-status/${owner}/${name}`)
  return data
}

export async function deleteRepo(owner: string, name: string) {
  const { data } = await api.delete(`/repos/${owner}/${name}`)
  return data
}

export async function listRepos(): Promise<{ repos: Record<string, unknown>[]; count: number }> {
  const { data } = await api.get('/repos/list')
  return data
}

/* ---- Query ---- */

export async function executeQuery(
  question: string,
  repoOwner: string,
  repoName: string,
  config: Partial<QueryConfig> = {},
): Promise<QueryResponse> {
  const { data } = await api.post('/query', {
    question,
    repo_owner: repoOwner,
    repo_name: repoName,
    ...config,
  })
  return data
}

/* ---- GraphRAG ---- */

export async function getGraphragStatus(owner: string, name: string) {
  const { data } = await api.get(`/graphrag/status/${owner}/${name}`)
  return data
}

export async function getGraphragEntities(owner: string, name: string, limit = 50) {
  const { data } = await api.get(`/graphrag/entities/${owner}/${name}`, { params: { limit } })
  return data
}

export async function getGraphragRelationships(owner: string, name: string, limit = 50) {
  const { data } = await api.get(`/graphrag/relationships/${owner}/${name}`, { params: { limit } })
  return data
}

/* ---- Index ---- */

export async function listIndexes() {
  const { data } = await api.get('/index/list')
  return data
}

export async function getIndexStats(owner: string, name: string) {
  const { data } = await api.get(`/index/stats/${owner}/${name}`)
  return data
}

/* ---- Config ---- */

export async function getConfig() {
  const { data } = await api.get('/config')
  return data
}

export async function updateConfig(config: Partial<QueryConfig>) {
  const { data } = await api.post('/config', config)
  return data
}
