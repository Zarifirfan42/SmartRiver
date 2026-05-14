/** Auth API: verification OTP, password reset OTP */
import api from './client'

export async function verifyEmail({ email, otp }) {
  const { data } = await api.post('/auth/verify-email', {
    email: (email || '').trim().toLowerCase(),
    otp: String(otp || '').replace(/\s/g, ''),
  })
  return data
}

export async function resendVerification(email) {
  const { data } = await api.post('/auth/resend-verification', {
    email: (email || '').trim().toLowerCase(),
  })
  return data
}

export async function requestPasswordReset(email) {
  const { data } = await api.post('/auth/forgot-password', {
    email: (email || '').trim().toLowerCase(),
  })
  return data
}

export async function resetPasswordWithOtp({ email, otp, new_password, confirm_password }) {
  const { data } = await api.post('/auth/reset-password', {
    email: (email || '').trim().toLowerCase(),
    otp: String(otp || '').replace(/\s/g, ''),
    new_password,
    confirm_password,
  })
  return data
}
