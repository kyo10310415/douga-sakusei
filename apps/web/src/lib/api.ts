import axios from 'axios'

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

export const apiClient = axios.create({
  baseURL: `${API_BASE_URL}/api`,
  timeout: 60000,  // 60秒: GPT-4o 台本生成は最大60秒かかる場合がある
  headers: {
    'Content-Type': 'application/json',
  },
})

// 長時間リクエスト用クライアント（AI生成など120秒まで待機）
export const apiClientLong = axios.create({
  baseURL: `${API_BASE_URL}/api`,
  timeout: 120000,
  headers: {
    'Content-Type': 'application/json',
  },
})

// リクエストインターセプター（認証トークン付与）
apiClient.interceptors.request.use((config) => {
  if (typeof window !== 'undefined') {
    const token = localStorage.getItem('access_token')
    if (token) {
      config.headers.Authorization = `Bearer ${token}`
    }
  }
  return config
})

// 長時間クライアントにも同じインターセプターを適用
apiClientLong.interceptors.request.use((config) => {
  if (typeof window !== 'undefined') {
    const token = localStorage.getItem('access_token')
    if (token) {
      config.headers.Authorization = `Bearer ${token}`
    }
  }
  return config
})

// レスポンスインターセプター（認証エラー処理）
const authErrorInterceptor = (error: any) => {
  if (error.response?.status === 401) {
    if (typeof window !== 'undefined') {
      localStorage.removeItem('access_token')
      window.location.href = '/login'
    }
  }
  return Promise.reject(error)
}

apiClient.interceptors.response.use(
  (response) => response,
  authErrorInterceptor,
)

apiClientLong.interceptors.response.use(
  (response) => response,
  authErrorInterceptor,
)

// Auth API
export const authApi = {
  login: (email: string, password: string) =>
    apiClient.post('/auth/login', { email, password }),
  register: (email: string, username: string, password: string) =>
    apiClient.post('/auth/register', { email, username, password }),
  me: () => apiClient.get('/auth/me'),
}

// Dashboard API
export const dashboardApi = {
  getSummary: () => apiClient.get('/dashboard/summary'),
}

// YouTube API
export const youtubeApi = {
  startOAuth: () => apiClient.post('/youtube/oauth/start'),
  getAccounts: () => apiClient.get('/youtube/accounts'),
  disconnectAccount: (accountId: string) => apiClient.delete(`/youtube/accounts/${accountId}`),
  syncWeekly: (accountId?: string) =>
    apiClient.post('/youtube/sync-weekly', null, { params: { youtube_account_id: accountId } }),
  getWeeklyMetrics: (limit = 12) =>
    apiClient.get('/youtube/weekly-metrics', { params: { limit } }),
  getVideos: (limit = 20) =>
    apiClient.get('/youtube/videos', { params: { limit } }),
  getVideoMetrics: (videoId: string) =>
    apiClient.get(`/youtube/video-metrics/${videoId}`),
}

// Character API
export const characterApi = {
  list: () => apiClient.get('/characters'),
  create: (data: any) => apiClient.post('/characters', data),
  get: (id: string) => apiClient.get(`/characters/${id}`),
  update: (id: string, data: any) => apiClient.put(`/characters/${id}`, data),
  uploadImage: (id: string, imageType: string, file: File) => {
    const formData = new FormData()
    formData.append('image_type', imageType)
    formData.append('file', file)
    return apiClient.post(`/characters/${id}/images`, formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
  },
}

// Theme API
export const themeApi = {
  list: () => apiClient.get('/themes'),
  create: (data: any) => apiClient.post('/themes', data),
  update: (id: string, data: any) => apiClient.put(`/themes/${id}`, data),
  delete: (id: string) => apiClient.delete(`/themes/${id}`),
}

// Analysis API
export const analysisApi = {
  run: (weeklyMetricsId?: string) =>
    apiClient.post('/analysis/run', null, {
      params: { weekly_metrics_id: weeklyMetricsId },
    }),
  getReports: (limit = 10) =>
    apiClient.get('/analysis/reports', { params: { limit } }),
  getReport: (id: string) => apiClient.get(`/analysis/reports/${id}`),
}

// Video Jobs API
export const videoJobApi = {
  list: (limit = 20, status?: string) =>
    apiClient.get('/video-jobs', { params: { limit, status } }),
  create: (data: any) => apiClient.post('/video-jobs', data),
  get: (id: string) => apiClient.get(`/video-jobs/${id}`),
  retry: (id: string) => apiClient.post(`/video-jobs/${id}/retry`),
  cancel: (id: string) => apiClient.post(`/video-jobs/${id}/cancel`),

  // ── 2ステップ生成（Render 30秒タイムアウト対策）──
  // Step1: 企画のみ生成 (~10-15秒) → plan_id を返す
  generatePlan: (data: { character_id: string; theme_id: string; custom_topic?: string }) =>
    apiClientLong.post('/video-jobs/generate/plan', data),
  // Step2: plan_id をもとに台本生成 (~20-30秒) → script を返す
  generateScript: (data: { plan_id: string }) =>
    apiClientLong.post('/video-jobs/generate/script', data),

  // 後方互換（旧一括生成エンドポイント）
  generate: (data: { character_id: string; theme_id: string; custom_topic?: string }) =>
    apiClientLong.post('/video-jobs/generate', data),

  // Step3: 台本の各セクションを OpenAI TTS で音声生成 (~15-60秒)
  generateVoice: (data: { script_id: string }) =>
    apiClientLong.post('/video-jobs/generate/voice', data),

  // Step4: FFmpeg動画合成＋YouTubeアップロードを Celery でキック（即時レスポンス）
  generateVideo: (data: { script_id: string }) =>
    apiClientLong.post('/video-jobs/generate/video', data),

  // Step4 進捗ポーリング: render_job_id の状態・進捗・YouTube URL を返す
  getRenderStatus: (renderJobId: string) =>
    apiClient.get(`/video-jobs/render/${renderJobId}`),

  listPlans: (limit = 20) =>
    apiClient.get('/video-jobs/plans', { params: { limit } }),
  getPlan: (planId: string) =>
    apiClient.get(`/video-jobs/plans/${planId}`),
}

// Review API
export const reviewApi = {
  get: (videoId: string) => apiClient.get(`/reviews/${videoId}`),
  updateChecklist: (videoId: string, data: any) =>
    apiClient.put(`/reviews/${videoId}/checklist`, data),
  requestRegenerate: (videoId: string, reason: string) =>
    apiClient.post(`/reviews/${videoId}/request-regenerate`, { reason }),
  approve: (videoId: string) => apiClient.post(`/reviews/${videoId}/approve`),
  publish: (videoId: string) => apiClient.post(`/reviews/${videoId}/publish`),
}

// Settings API
export const settingsApi = {
  get: () => apiClient.get('/settings'),
  update: (data: any) => apiClient.put('/settings', data),
  getScheduler: () => apiClient.get('/settings/scheduler'),
  updateScheduler: (data: any) => apiClient.put('/settings/scheduler', data),
}

// Promo API（コンサル宣伝システム）
export const promoApi = {
  // ── 生成 ──
  generate: (data: {
    theme: string
    platforms: string[]
    target_segment: string
    goal: string
    tone: string
    cta: string
    count: number
    weekly_metrics_id?: string
  }) => apiClient.post('/promo/generate', data),

  // ── 投稿 CRUD ──
  listPosts: (params?: { status?: string; platform?: string; limit?: number; offset?: number }) =>
    apiClient.get('/promo/posts', { params }),
  getPost: (id: string) => apiClient.get(`/promo/posts/${id}`),
  updatePost: (id: string, data: any) => apiClient.put(`/promo/posts/${id}`, data),
  deletePost: (id: string) => apiClient.delete(`/promo/posts/${id}`),

  // ── ワークフロー ──
  approvePost: (id: string) => apiClient.post(`/promo/posts/${id}/approve`),
  rejectPost: (id: string, reason: string) =>
    apiClient.post(`/promo/posts/${id}/reject`, { reason }),
  publishPost: (id: string) => apiClient.post(`/promo/posts/${id}/publish`),
  ngCheck: (id: string) => apiClient.post(`/promo/posts/${id}/ng-check`),

  // ── 素材 ──
  listAssets: (postId: string) => apiClient.get(`/promo/posts/${postId}/assets`),
  generateAsset: (postId: string, data: { asset_type: string; duration?: string }) =>
    apiClient.post(`/promo/posts/${postId}/assets/generate`, data),

  // ── 分析 ──
  getAnalytics: (postId: string) => apiClient.get(`/promo/analytics/${postId}`),
  upsertAnalytics: (postId: string, data: any) =>
    apiClient.post(`/promo/analytics/${postId}`, data),

  // ── テンプレート ──
  listTemplates: (params?: { type?: string; platform?: string }) =>
    apiClient.get('/promo/templates', { params }),

  // ── ダッシュボード ──
  getDashboard: () => apiClient.get('/promo/dashboard'),
}
