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

export async function getFeedbackReportsFiltered(params = {}) {
  const query = {}
  if (params.dateFrom) query.date_from = params.dateFrom
  if (params.dateTo) query.date_to = params.dateTo
  if (params.name) query.name = params.name.trim()
  if (params.email) query.email = params.email.trim()
  if (params.readStatus === 'read') query.is_read = true
  if (params.readStatus === 'unread') query.is_read = false
  if (params.limit) query.limit = params.limit
  const { data } = await api.get('/feedback', { params: query })
  return Array.isArray(data.reports) ? data.reports : []
}

export async function markFeedbackRead(reportId, isRead = true) {
  try {
    const { data } = await api.patch(`/feedback/${reportId}/read`, { is_read: isRead })
    return data.report
  } catch (err) {
    if (err.response?.status !== 404 && err.response?.status !== 405) throw err
    // Fallback for environments where PATCH route is unavailable/blocked.
    const { data } = await api.post(`/feedback/${reportId}/read`, { is_read: isRead })
    return data.report
  }
}

export async function deleteFeedbackReport(reportId) {
  const { data } = await api.delete(`/feedback/${reportId}`)
  return data
}
