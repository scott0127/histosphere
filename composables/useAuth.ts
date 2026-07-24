/**
 * Supabase Auth Composable
 * 管理用戶認證狀態 (登入/登出/註冊/密碼重設/個人資料)
 */
import { createClient, type User, type Session } from '@supabase/supabase-js'
import { clearAdminSession } from '~/utils/adminSession'
import { getCurrentAccessToken, setCurrentAccessToken } from '~/utils/authSession'

// Supabase 客戶端 (單例)
const supabaseUrl = import.meta.env.VITE_SUPABASE_URL || ''
const supabaseAnonKey = import.meta.env.VITE_SUPABASE_ANON_KEY || ''

let supabase: ReturnType<typeof createClient> | null = null
let authInitialized = false
let authListenerInitialized = false
let authInitializePromise: Promise<void> | null = null

function clearSharedBrowserSessionState() {
  if (!import.meta.client) return
  clearAdminSession()
  localStorage.removeItem('histosphere-participant-id')
}

function getSupabaseClient() {
  if (!supabase && supabaseUrl && supabaseAnonKey) {
    supabase = createClient(supabaseUrl, supabaseAnonKey)
  }
  return supabase
}

// 全域狀態
const user = ref<User | null>(null)
const session = ref<Session | null>(null)
const loading = ref(true)
const error = ref<string | null>(null)

export function useAuth() {
  const client = getSupabaseClient()

  /**
   * 初始化認證狀態 (在 app 啟動時呼叫)
   */
  async function initialize() {
    if (!client) {
      console.warn('[useAuth] Supabase not configured')
      setCurrentAccessToken(null)
      loading.value = false
      return
    }

    if (authInitialized) {
      loading.value = false
      return
    }

    if (authInitializePromise) {
      await authInitializePromise
      loading.value = false
      return
    }

    authInitializePromise = (async () => {
      // 取得目前 session
      const { data: { session: currentSession } } = await client.auth.getSession()
      session.value = currentSession
      user.value = currentSession?.user ?? null
      setCurrentAccessToken(currentSession?.access_token)

      // 監聽認證狀態變化
      if (!authListenerInitialized) {
        client.auth.onAuthStateChange((event, newSession) => {
          const previousUserId = user.value?.id || null
          const nextUserId = newSession?.user?.id || null
          session.value = newSession
          user.value = newSession?.user ?? null
          setCurrentAccessToken(newSession?.access_token)

          if (event === 'SIGNED_OUT' || (previousUserId && nextUserId && previousUserId !== nextUserId)) {
            clearSharedBrowserSessionState()
          }
        })
        authListenerInitialized = true
      }
      authInitialized = true
    })()

    try {
      await authInitializePromise
    } catch (e) {
      console.error('[useAuth] Initialize error:', e)
      authInitializePromise = null
    } finally {
      loading.value = false
    }
  }

  /**
   * Email/Password 登入
   */
  async function signIn(email: string, password: string) {
    if (!client) {
      error.value = 'Supabase 未設定'
      return { success: false, error: error.value }
    }

    error.value = null
    loading.value = true
    const previousUserId = user.value?.id || null

    try {
      const { data, error: authError } = await client.auth.signInWithPassword({
        email,
        password,
      })

      if (authError) {
        error.value = authError.message
        return { success: false, error: authError.message }
      }

      user.value = data.user
      session.value = data.session
      setCurrentAccessToken(data.session?.access_token)
      if (previousUserId && data.user?.id && previousUserId !== data.user.id) {
        clearSharedBrowserSessionState()
      }
      return { success: true }
    } catch (e: any) {
      error.value = e.message
      return { success: false, error: e.message }
    } finally {
      loading.value = false
    }
  }

  /**
   * Email/Password 註冊
   */
  async function signUp(email: string, password: string, displayName?: string) {
    if (!client) {
      error.value = 'Supabase 未設定'
      return { success: false, error: error.value }
    }

    error.value = null
    loading.value = true

    try {
      const { data, error: authError } = await client.auth.signUp({
        email,
        password,
        options: {
          data: {
            display_name: displayName || email.split('@')[0]
          }
        }
      })

      if (authError) {
        error.value = authError.message
        return { success: false, error: authError.message }
      }

      // 注意: Supabase 預設需要 email 驗證
      // 可在 Supabase Dashboard 關閉
      return { 
        success: true, 
        needsVerification: !data.session,
        user: data.user
      }
    } catch (e: any) {
      error.value = e.message
      return { success: false, error: e.message }
    } finally {
      loading.value = false
    }
  }

  /**
   * 登出
   */
  async function signOut() {
    if (!client) return

    await client.auth.signOut()
    user.value = null
    session.value = null
    setCurrentAccessToken(null)
    clearSharedBrowserSessionState()
  }

  /**
   * 發送密碼重設 Email
   */
  async function resetPasswordForEmail(email: string) {
    if (!client) {
      error.value = 'Supabase 未設定'
      return { success: false, error: error.value }
    }

    error.value = null
    loading.value = true

    try {
      const { error: resetError } = await client.auth.resetPasswordForEmail(email, {
        redirectTo: `${window.location.origin}/auth/reset-password`
      })

      if (resetError) {
        error.value = resetError.message
        return { success: false, error: resetError.message }
      }

      return { success: true }
    } catch (e: any) {
      error.value = e.message
      return { success: false, error: e.message }
    } finally {
      loading.value = false
    }
  }

  /**
   * 更新密碼 (需已登入或從重設連結進入)
   */
  async function updatePassword(newPassword: string) {
    if (!client) {
      error.value = 'Supabase 未設定'
      return { success: false, error: error.value }
    }

    error.value = null
    loading.value = true

    try {
      const { error: updateError } = await client.auth.updateUser({
        password: newPassword
      })

      if (updateError) {
        error.value = updateError.message
        return { success: false, error: updateError.message }
      }

      return { success: true }
    } catch (e: any) {
      error.value = e.message
      return { success: false, error: e.message }
    } finally {
      loading.value = false
    }
  }

  /**
   * 更新用戶資料 (display_name)
   */
  async function updateProfile(displayName: string) {
    if (!client) {
      error.value = 'Supabase 未設定'
      return { success: false, error: error.value }
    }

    error.value = null
    loading.value = true

    try {
      const { data, error: updateError } = await client.auth.updateUser({
        data: { display_name: displayName }
      })

      if (updateError) {
        error.value = updateError.message
        return { success: false, error: updateError.message }
      }

      // 更新本地 user 狀態
      if (data.user) {
        user.value = data.user
      }

      return { success: true }
    } catch (e: any) {
      error.value = e.message
      return { success: false, error: e.message }
    } finally {
      loading.value = false
    }
  }

  /**
   * 取得 JWT Token (用於 API 請求)
   */
  function getAccessToken(): string | null {
    return getCurrentAccessToken()
  }

  /**
   * 檢查是否已登入
   */
  const isAuthenticated = computed(() => !!user.value)

  /**
   * 取得顯示名稱 (優先使用 display_name，否則使用 email)
   */
  const displayName = computed(() => {
    if (!user.value) return null
    return user.value.user_metadata?.display_name || user.value.email?.split('@')[0] || null
  })

  return {
    // 狀態
    user: readonly(user),
    session: readonly(session),
    loading: readonly(loading),
    error: readonly(error),
    isAuthenticated,
    displayName,
    
    // 方法
    initialize,
    signIn,
    signUp,
    signOut,
    resetPasswordForEmail,
    updatePassword,
    updateProfile,
    getAccessToken,
  }
}
