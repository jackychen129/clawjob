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
  }),
  getters: {
    isLoggedIn: (state) => !!state.token,
  },
  actions: {
    setUser(token: string, username: string, userId?: number) {
      this.token = token
      this.username = username
      if (userId != null) {
        this.userId = userId
        localStorage.setItem(USER_ID_KEY, String(userId))
      }
      localStorage.setItem(TOKEN_KEY, token)
      localStorage.setItem(USER_KEY, username)
      setAuthToken(token)
    },
    setUserId(userId: number) {
      this.userId = userId
      localStorage.setItem(USER_ID_KEY, String(userId))
    },
    logout() {
      this.token = null
      this.username = null
      this.userId = null
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
