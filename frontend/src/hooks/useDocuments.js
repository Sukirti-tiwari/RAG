import { useState, useEffect, useCallback } from 'react'
import { listDocuments, uploadFile, ingestUrl, deleteDocument, getDocStatus } from '../utils/api'

export function useDocuments() {
  const [docs, setDocs] = useState([])
  const [loading, setLoading] = useState(false)

  const refresh = useCallback(async () => {
    try {
      const data = await listDocuments()
      setDocs(data)
    } catch (e) {
      console.error('Failed to list documents', e)
    }
  }, [])

  useEffect(() => { refresh() }, [refresh])

  // Poll processing docs until ready
  useEffect(() => {
    const processing = docs.filter(d => d.status === 'processing')
    if (!processing.length) return
    const timer = setInterval(async () => {
      const updates = await Promise.all(processing.map(d => getDocStatus(d.id)))
      setDocs(prev => prev.map(d => {
        const upd = updates.find(u => u.id === d.id)
        return upd ? { ...d, ...upd } : d
      }))
    }, 2000)
    return () => clearInterval(timer)
  }, [docs])

  const upload = useCallback(async (file, onProgress) => {
    setLoading(true)
    try {
      const { data } = await uploadFile(file, onProgress)
      setDocs(prev => [{ ...data, name: file.name, type: 'file', size: file.size }, ...prev])
      return data
    } finally {
      setLoading(false)
    }
  }, [])

  const addUrl = useCallback(async (url, name) => {
    setLoading(true)
    try {
      const { data } = await ingestUrl(url, name)
      setDocs(prev => [{ ...data, name: name || url, type: 'url', size: 0 }, ...prev])
      return data
    } finally {
      setLoading(false)
    }
  }, [])

  const remove = useCallback(async (id) => {
    await deleteDocument(id)
    setDocs(prev => prev.filter(d => d.id !== id))
  }, [])

  return { docs, loading, refresh, upload, addUrl, remove }
}
