import { defineStore } from 'pinia'
import { setAuthToken } from '../api'

const TOKEN_KEY = 'clawjob_token'
const USER_KEY = 'clawjob_user'
const USER_ID_KEY = 'clawjob_user_id'

export const useAuthStore = defineStore('auth', {
  state: () => ({
    token: localStorage.getItem(TOKEN_KEY) as string | null,
    username: localStorage.getItem(USER_KEY) as string | null,
    userId: (() => {
      const v = localStorage.getItem(USER_ID_KEY)
      return v != null ? parseInt(v, 10) : null
    })(),
    isGuest: false, // 由 loadAccountMe 或 setUser 时设置；也可由 username.startsWith('guest_') 推断
  }),
  getters: {
    isLoggedIn: (state) => !!state.token,
    /* NOTE: translated comment in English. */
    isGuestUser: (state) => state.isGuest || (state.username || '').startsWith('guest_'),
  },
  actions: {
    setUser(token: string, username: string, userId?: number, isGuest?: boolean) {
      this.token = token
      this.username = username
      if (userId != null) {
        this.userId = userId
        localStorage.setItem(USER_ID_KEY, String(userId))
      }
      this.isGuest = isGuest ?? (username || '').startsWith('guest_')
      localStorage.setItem(TOKEN_KEY, token)
      localStorage.setItem(USER_KEY, username)
      setAuthToken(token)
    },
    setIsGuest(isGuest: boolean) {
      this.isGuest = isGuest
    },
    setUserId(userId: number) {
      this.userId = userId
      localStorage.setItem(USER_ID_KEY, String(userId))
    },
    logout() {
      this.token = null
      this.username = null
      this.userId = null
      this.isGuest = false
      localStorage.removeItem(TOKEN_KEY)
      localStorage.removeItem(USER_KEY)
      localStorage.removeItem(USER_ID_KEY)
      setAuthToken(null)
    },
    initFromStorage() {
      if (this.token) setAuthToken(this.token)
    },
  },
})
