import api from './client'

export async function submitFeedback(payload) {
  const { data } = await api.post('/feedback', {
    name: payload.name?.trim() || null,
    email: payload.email?.trim(),
    message: payload.message?.trim(),
  })
  return data
}

export async function getFeedbackReports() {
  const { data } = await api.get('/feedback')
  return Array.isArray(data.reports) ? data.reports : []
}
