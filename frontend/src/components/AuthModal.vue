<script setup lang="ts">
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { Button } from './ui/button'
import { Input } from './ui/input'
import { useAuthForm } from '../composables/useAuthForm'
import * as api from '../api'

const open = defineModel<boolean>('open', { default: false })
const authTab = defineModel<'login' | 'register'>('tab', { default: 'login' })

const props = defineProps<{
  googleOAuthConfigured?: boolean
  googleConfigError?: string
}>()

const emit = defineEmits<{
  success: []
}>()

const { t } = useI18n()
const googleLoginUrl = computed(() => api.getGoogleLoginUrl())
const googleOAuthConfigured = computed(() => props.googleOAuthConfigured !== false)
const googleConfigError = computed(() => props.googleConfigError || '')

const {
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
} = useAuthForm({
  onSuccess: () => {
    open.value = false
    emit('success')
  },
})

function handleGoogleClick(e: Event) {
  onGoogleLoginClick(e, googleOAuthConfigured.value, googleConfigError.value)
}
</script>

<template>
  <div v-if="open" class="modal-mask" data-testid="auth-modal-mask" @click.self="open = false">
    <div class="modal" data-testid="auth-modal">
      <h3>{{ authTab === 'login' ? t('auth.login') : t('auth.register') }}</h3>
      <div class="tabs">
        <Button
          variant="secondary"
          :class="{ 'ring-2 ring-primary ring-offset-2 ring-offset-background': authTab === 'login' }"
          @click="authTab = 'login'"
        >{{ t('auth.login') }}</Button>
        <Button
          variant="secondary"
          :class="{ 'ring-2 ring-primary ring-offset-2 ring-offset-background': authTab === 'register' }"
          @click="authTab = 'register'"
        >{{ t('auth.register') }}</Button>
      </div>
      <div v-if="authTab === 'login'" class="form">
        <Input v-model="loginForm.username" :placeholder="t('auth.username')" />
        <Input v-model="loginForm.password" type="password" :placeholder="t('auth.password')" />
        <Button :disabled="authLoading" @click="doLogin">{{ t('auth.login') }}</Button>
        <div class="oauth-divider">{{ t('auth.or') }}</div>
        <Button
          as="a"
          :href="googleLoginUrl"
          target="_self"
          variant="secondary"
          class="w-full justify-center"
          :class="{ 'pointer-events-none opacity-60 cursor-not-allowed': !googleOAuthConfigured }"
          :title="!googleOAuthConfigured ? (googleConfigError || String(t('oauthError.server_config'))) : undefined"
          :aria-disabled="(!googleOAuthConfigured).toString()"
          @click="handleGoogleClick"
        >
          {{ t('auth.loginWithGoogle') }}
        </Button>
        <p v-if="!googleOAuthConfigured && googleConfigError" class="hint google-config-hint">{{ googleConfigError }}</p>
      </div>
      <div v-else class="form">
        <Input v-model="registerForm.username" :placeholder="t('auth.username')" />
        <Input v-model="registerForm.email" type="email" :placeholder="t('auth.email')" />
        <div class="form-inline verification-code-row">
          <Input v-model="registerForm.verification_code" maxlength="6" :placeholder="t('auth.verificationCode')" />
          <Button
            type="button"
            variant="secondary"
            :disabled="sendCodeLoading || sendCodeCountdown > 0"
            @click="doSendVerificationCode"
          >
            {{ sendCodeCountdown > 0 ? t('auth.sendCodeCountdown', { n: sendCodeCountdown }) : t('auth.sendVerificationCode') }}
          </Button>
        </div>
        <Input v-model="registerForm.password" type="password" :placeholder="t('auth.password')" />
        <Input v-model="registerForm.referral_code" maxlength="12" :placeholder="t('auth.referralCodePlaceholder')" />
        <Button :disabled="authLoading" @click="doRegister">{{ t('auth.register') }}</Button>
        <div class="oauth-divider">{{ t('auth.or') }}</div>
        <Button
          as="a"
          :href="googleLoginUrl"
          target="_self"
          variant="secondary"
          class="w-full justify-center"
          :class="{ 'pointer-events-none opacity-60 cursor-not-allowed': !googleOAuthConfigured }"
          :title="!googleOAuthConfigured ? (googleConfigError || String(t('oauthError.server_config'))) : undefined"
          :aria-disabled="(!googleOAuthConfigured).toString()"
          @click="handleGoogleClick"
        >
          {{ t('auth.loginWithGoogle') }}
        </Button>
        <p v-if="!googleOAuthConfigured && googleConfigError" class="hint google-config-hint">{{ googleConfigError }}</p>
      </div>
      <p v-if="authError" class="error-msg">{{ authError }}</p>
      <Button variant="secondary" class="close-btn w-full" @click="open = false">{{ t('common.close') }}</Button>
    </div>
  </div>
</template>
