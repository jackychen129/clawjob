import { reactive, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { useAuthStore } from '../stores/auth'
import * as api from '../api'

export function useAuthForm(options?: { onSuccess?: () => void }) {
  const { t } = useI18n()
  const auth = useAuthStore()

  const authLoading = ref(false)
  const authError = ref('')
  const loginForm = reactive({ username: '', password: '' })
  const registerForm = reactive({
    username: '',
    email: '',
    password: '',
    verification_code: '',
    referral_code: '',
  })
  const sendCodeLoading = ref(false)
  const sendCodeCountdown = ref(0)
  let sendCodeTimer: ReturnType<typeof setInterval> | null = null

  function initReferralFromStorage() {
    try {
      const search = window.location.search
      if (search) {
        const refFromUrl = new URLSearchParams(search.slice(1)).get('ref')
        if (refFromUrl && !registerForm.referral_code) {
          registerForm.referral_code = refFromUrl.trim()
          try {
            localStorage.setItem('clawjob_ref_code', refFromUrl.trim())
          } catch {
            /* ignore */
          }
        }
      }
      if (!registerForm.referral_code) {
        const stored = localStorage.getItem('clawjob_ref_code')
        if (stored) registerForm.referral_code = stored
      }
    } catch {
      /* ignore */
    }
  }

  initReferralFromStorage()

  function doLogin() {
    authError.value = ''
    authLoading.value = true
    api
      .login(loginForm)
      .then((res) => {
        auth.setUser(res.data.access_token, res.data.username, res.data.user_id)
        options?.onSuccess?.()
      })
      .catch((e) => {
        authError.value = e.response?.data?.detail || t('common.loginFailed')
      })
      .finally(() => {
        authLoading.value = false
      })
  }

  function doSendVerificationCode() {
    const email = (registerForm.email || '').trim()
    if (!email || !email.includes('@')) {
      authError.value = t('auth.emailRequired')
      return
    }
    authError.value = ''
    sendCodeLoading.value = true
    api
      .sendVerificationCode({ email })
      .then(() => {
        sendCodeCountdown.value = 60
        if (sendCodeTimer) clearInterval(sendCodeTimer)
        sendCodeTimer = setInterval(() => {
          sendCodeCountdown.value -= 1
          if (sendCodeCountdown.value <= 0 && sendCodeTimer) {
            clearInterval(sendCodeTimer)
            sendCodeTimer = null
          }
        }, 1000)
      })
      .catch((e) => {
        authError.value = e.response?.data?.detail || t('auth.sendCodeFailed')
      })
      .finally(() => {
        sendCodeLoading.value = false
      })
  }

  function doRegister() {
    authError.value = ''
    if (!(registerForm.verification_code || '').trim()) {
      authError.value = t('auth.verificationCodeRequired')
      return
    }
    authLoading.value = true
    const refCode = (registerForm.referral_code || '').trim()
    api
      .register({
        username: registerForm.username,
        email: registerForm.email,
        password: registerForm.password,
        verification_code: registerForm.verification_code,
        ...(refCode ? { referral_code: refCode } : {}),
      })
      .then((res) => {
        auth.setUser(res.data.access_token, res.data.username, res.data.user_id)
        options?.onSuccess?.()
      })
      .catch((e) => {
        authError.value = e.response?.data?.detail || t('common.registerFailed')
      })
      .finally(() => {
        authLoading.value = false
      })
  }

  function onGoogleLoginClick(e: Event, googleOAuthConfigured: boolean, googleConfigError: string) {
    e.preventDefault()
    if (!googleOAuthConfigured) {
      authError.value = googleConfigError || String(t('oauthError.server_config'))
      return
    }
    window.location.href = api.getGoogleLoginUrl()
  }

  return {
    authLoading,
    authError,
    loginForm,
    registerForm,
    sendCodeLoading,
    sendCodeCountdown,
    doLogin,
    doSendVerificationCode,
    doRegister,
    onGoogleLoginClick,
  }
}
