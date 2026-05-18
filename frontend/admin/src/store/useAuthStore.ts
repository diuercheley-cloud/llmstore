import { create } from 'zustand'
import { persist } from 'zustand/middleware'

interface AuthState {
  token: string | null
  setToken: (token: string | null) => void
  logout: () => void
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set) => ({
      token: localStorage.getItem('adminToken'),
      setToken: (token) => {
        if (token) {
          localStorage.setItem('adminToken', token)
        } else {
          localStorage.removeItem('adminToken')
        }
        set({ token })
      },
      logout: () => {
        localStorage.removeItem('adminToken')
        set({ token: null })
      },
    }),
    {
      name: 'admin-auth-storage',
    }
  )
)
