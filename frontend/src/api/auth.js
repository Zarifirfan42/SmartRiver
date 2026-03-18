/** Auth API: login, register, me, reset-password */
import api from './client'

export async function resetPassword({ email, new_password, confirm_password }) {
  const { data } = await api.post('/auth/reset-password', {
    email: (email || '').trim().toLowerCase(),
    new_password,
    confirm_password,
  })
  return data
}
