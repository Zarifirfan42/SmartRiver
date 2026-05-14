import api from './client'

export async function postAdminWarning(message) {
  const { data } = await api.post('/warnings/', { message })
  return data
}

export async function listAdminWarnings() {
  const { data } = await api.get('/warnings/admin/list')
  return data.items || []
}

export async function deactivateWarning(warningId) {
  const { data } = await api.patch(`/warnings/${warningId}/deactivate`)
  return data
}
