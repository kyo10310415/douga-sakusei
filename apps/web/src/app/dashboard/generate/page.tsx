'use client'
import { useState, useEffect, useRef } from 'react'
import { characterApi, themeApi, videoJobApi } from '@/lib/api'

// ─────────────────────────────────────────
// 型定義
// ─────────────────────────────────────────
type PlanSection = {
  section: string
  title: string
  seconds: number
  description: string
}

type VideoPlan = {
  id: string
  title: string
  goal: string
  target_audience: string
  total_duration_seconds: number
  structure: PlanSection[]
  youtube_title_candidates: string[]
  youtube_description: string
  youtube_tags: string[]
  cta: string
}

type ScriptSection = {
  order_index: number
  section_type: string
  title: string
  duration_seconds: number
  narration: string
  subtitle: string
  direction: string
  expression: string
}

type ScriptResult = {
  id: string
  hook_text: string
  full_script: string
  subtitle_text: string
  asset_list: any[]
  sections: ScriptSection[]
}

type VoiceResult = {
  script_id: string
  total_duration_seconds: number
  voice_count: number
  voices: Array<{
    section_id: string
    order_index: number
    section_type: string
    status: 'completed' | 'failed' | 'skipped' | 'cached'
    file_url: string | null
    duration_seconds: number
    error?: string
  }>
}

type RenderStatus = {
  render_job_id: string
  status: string
  progress_percent: number
  current_step: string | null
  error_message: string | null
  output_file_url: string | null
  started_at: string | null
  completed_at: string | null
  youtube_upload: {
    youtube_video_id: string
    youtube_url: string
    privacy_status: string
    upload_status: string
  } | null
}

// ステートマシン
type GenPhase =
  | 'idle'            // 未開始
  | 'plan_loading'    // Step1 企画生成中
  | 'plan_done'       // Step1 完了
  | 'script_loading'  // Step2 台本生成中
  | 'script_done'     // Step2 完了（音声生成前）
  | 'voice_loading'   // Step3 音声生成中
  | 'voice_done'      // Step3 完了（動画生成前）
  | 'video_loading'   // Step4 動画生成ジョブ投入中
  | 'video_polling'   // Step4 バックグラウンド処理中（ポーリング）
  | 'done'            // 全完了（YouTube URL あり）

const EXPRESSION_EMOJI: Record<string, string> = {
  normal: '😐', smile: '😊', surprise: '😲', troubled: '😟', serious: '😤',
}
const SECTION_COLOR: Record<string, string> = {
  hook:    'bg-pink-50 border-pink-300 text-pink-700',
  problem: 'bg-amber-50 border-amber-300 text-amber-700',
  main:    'bg-blue-50 border-blue-300 text-blue-700',
  example: 'bg-indigo-50 border-indigo-300 text-indigo-700',
  summary: 'bg-green-50 border-green-300 text-green-700',
  cta:     'bg-purple-50 border-purple-300 text-purple-700',
  custom:  'bg-gray-50 border-gray-300 text-gray-700',
}
const SECTION_LABEL: Record<string, string> = {
  hook: '冒頭フック', problem: '問題提起', main: '本編',
  example: '具体例', summary: 'まとめ', cta: 'CTA', custom: 'カスタム',
}

function fmtSec(sec: number) {
  const m = Math.floor(sec / 60)
  const s = sec % 60
  return m > 0 ? `${m}分${s > 0 ? s + '秒' : ''}` : `${s}秒`
}

// ステップ定義（プログレスバー用）
const STEPS = [
  { key: 'settings', label: '設定', icon: '⚙️' },
  { key: 'plan',     label: '企画',  icon: '🧠' },
  { key: 'script',   label: '台本',  icon: '📝' },
  { key: 'voice',    label: '音声',  icon: '🎤' },
  { key: 'video',    label: '動画',  icon: '🎬' },
]

function phaseToStepIndex(phase: GenPhase): number {
  switch (phase) {
    case 'idle': return 0
    case 'plan_loading': case 'plan_done': return 1
    case 'script_loading': case 'script_done': return 2
    case 'voice_loading': case 'voice_done': return 3
    case 'video_loading': case 'video_polling': case 'done': return 4
    default: return 0
  }
}

// ─────────────────────────────────────────
// メインコンポーネント
// ─────────────────────────────────────────
export default function GeneratePage() {
  const [characters, setCharacters] = useState<any[]>([])
  const [themes, setThemes] = useState<any[]>([])
  const [selectedChar, setSelectedChar] = useState('')
  const [selectedTheme, setSelectedTheme] = useState('')
  const [customTopic, setCustomTopic] = useState('')
  const [aiMode, setAiMode] = useState<string>('')

  const [loading, setLoading] = useState(true)
  const [phase, setPhase] = useState<GenPhase>('idle')
  const [planResult, setPlanResult] = useState<VideoPlan | null>(null)
  const [scriptResult, setScriptResult] = useState<ScriptResult | null>(null)
  const [voiceResult, setVoiceResult] = useState<VoiceResult | null>(null)
  const [renderStatus, setRenderStatus] = useState<RenderStatus | null>(null)
  const [error, setError] = useState('')

  const [plans, setPlans] = useState<any[]>([])
  const [activeTab, setActiveTab] = useState<'new' | 'history'>('new')
  const [expandedSections, setExpandedSections] = useState<Set<number>>(new Set([0]))

  // ポーリング用
  const pollingRef = useRef<ReturnType<typeof setInterval> | null>(null)
  const renderJobIdRef = useRef<string | null>(null)

  useEffect(() => {
    Promise.all([
      characterApi.list(),
      themeApi.list(),
      videoJobApi.listPlans(10),
    ]).then(([c, t, p]) => {
      setCharacters(c.data)
      setThemes(t.data)
      setPlans(p.data)
      const defChar = c.data.find((x: any) => x.is_default) || c.data[0]
      const defTheme = t.data.find((x: any) => x.is_default) || t.data[0]
      if (defChar) setSelectedChar(defChar.id)
      if (defTheme) setSelectedTheme(defTheme.id)
    }).catch(console.error).finally(() => setLoading(false))
  }, [])

  // ポーリング停止（アンマウント時）
  useEffect(() => {
    return () => { if (pollingRef.current) clearInterval(pollingRef.current) }
  }, [])

  // ── Step 1: 企画生成 ──
  const handleGeneratePlan = async () => {
    if (!selectedChar || !selectedTheme) {
      setError('キャラクターとテーマを選択してください')
      return
    }
    setError('')
    setPlanResult(null)
    setScriptResult(null)
    setVoiceResult(null)
    setRenderStatus(null)
    setPhase('plan_loading')
    try {
      const res = await videoJobApi.generatePlan({
        character_id: selectedChar,
        theme_id: selectedTheme,
        custom_topic: customTopic || undefined,
      })
      setAiMode(res.data.ai_mode)
      setPlanResult(res.data.video_plan)
      setPhase('plan_done')
    } catch (err: any) {
      const msg = err.response?.data?.detail
        || (err.code === 'ECONNABORTED' ? 'タイムアウト: もう一度お試しください。' : null)
        || '企画生成に失敗しました。'
      setError(msg)
      setPhase('idle')
    }
  }

  // ── Step 2: 台本生成 ──
  const handleGenerateScript = async () => {
    if (!planResult) return
    setError('')
    setScriptResult(null)
    setPhase('script_loading')
    try {
      const res = await videoJobApi.generateScript({ plan_id: planResult.id })
      setAiMode(res.data.ai_mode)
      setScriptResult(res.data.script)
      setPhase('script_done')
      setExpandedSections(new Set([0]))
      setPlans(prev => [
        { id: planResult.id, title: planResult.title,
          total_duration_seconds: planResult.total_duration_seconds,
          status: 'draft', created_at: new Date().toISOString(), has_script: true },
        ...prev.filter(p => p.id !== planResult.id),
      ])
    } catch (err: any) {
      const msg = err.response?.data?.detail
        || (err.code === 'ECONNABORTED' ? 'タイムアウト: もう一度「台本を生成」ボタンを押してください。' : null)
        || '台本生成に失敗しました。'
      setError(msg)
      setPhase('plan_done')
    }
  }

  // ── Step 3: 音声生成 ──
  const handleGenerateVoice = async () => {
    if (!scriptResult) return
    setError('')
    setVoiceResult(null)
    setPhase('voice_loading')
    try {
      const res = await videoJobApi.generateVoice({ script_id: scriptResult.id })
      setAiMode(res.data.ai_mode)
      setVoiceResult(res.data)
      setPhase('voice_done')
    } catch (err: any) {
      const msg = err.response?.data?.detail
        || (err.code === 'ECONNABORTED' ? 'タイムアウト: 音声生成に時間がかかっています。もう一度お試しください。' : null)
        || '音声生成に失敗しました。'
      setError(msg)
      setPhase('script_done')
    }
  }

  // ── Step 4: 動画生成（Celeryジョブキック→ポーリング）──
  const handleGenerateVideo = async () => {
    if (!scriptResult) return
    setError('')
    setRenderStatus(null)
    setPhase('video_loading')
    try {
      const res = await videoJobApi.generateVideo({ script_id: scriptResult.id })
      const jobId: string = res.data.render_job_id
      renderJobIdRef.current = jobId
      setRenderStatus({
        render_job_id: jobId,
        status: res.data.status,
        progress_percent: res.data.progress_percent ?? 0,
        current_step: '動画生成ジョブを開始しました',
        error_message: null,
        output_file_url: null,
        started_at: null,
        completed_at: null,
        youtube_upload: null,
      })
      setPhase('video_polling')
      startPolling(jobId)
    } catch (err: any) {
      const msg = err.response?.data?.detail || '動画生成ジョブの開始に失敗しました。'
      setError(msg)
      setPhase('voice_done')
    }
  }

  // ポーリング開始
  const startPolling = (jobId: string) => {
    if (pollingRef.current) clearInterval(pollingRef.current)
    pollingRef.current = setInterval(async () => {
      try {
        const res = await videoJobApi.getRenderStatus(jobId)
        const status: RenderStatus = res.data
        setRenderStatus(status)

        // 完了・失敗・レビュー待ちになったらポーリング停止
        if (['waiting_review', 'approved', 'published'].includes(status.status)) {
          if (pollingRef.current) clearInterval(pollingRef.current)
          setPhase('done')
        } else if (status.status === 'failed') {
          if (pollingRef.current) clearInterval(pollingRef.current)
          setError(`動画生成に失敗しました: ${status.error_message || '不明なエラー'}`)
          setPhase('voice_done')
        }
      } catch (e) {
        console.error('[polling] error:', e)
      }
    }, 3000)
  }

  const toggleSection = (idx: number) => {
    setExpandedSections(prev => {
      const next = new Set(prev)
      next.has(idx) ? next.delete(idx) : next.add(idx)
      return next
    })
  }

  const handleReset = () => {
    if (pollingRef.current) clearInterval(pollingRef.current)
    setPlanResult(null)
    setScriptResult(null)
    setVoiceResult(null)
    setRenderStatus(null)
    setPhase('idle')
    setError('')
    setAiMode('')
  }

  const handleLoadPlan = async (planId: string) => {
    try {
      const res = await videoJobApi.getPlan(planId)
      setPlanResult(res.data)
      if (res.data.script) {
        setScriptResult(res.data.script)
        setPhase('script_done')
      } else {
        setPhase('plan_done')
      }
      setActiveTab('new')
      setExpandedSections(new Set([0]))
    } catch {
      alert('企画の読み込みに失敗しました')
    }
  }

  if (loading) return <div className="p-8 text-gray-400">読み込み中...</div>

  const currentStepIndex = phaseToStepIndex(phase)
  const isGenerating = ['plan_loading', 'script_loading', 'voice_loading', 'video_loading'].includes(phase)

  return (
    <div className="p-8 max-w-5xl mx-auto">
      {/* ヘッダー */}
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-gray-900">🎬 動画生成</h1>
        <p className="text-sm text-gray-500 mt-1">
          キャラクターとテーマを選ぶだけで、AIが企画・台本・音声・動画を自動作成します
        </p>
      </div>

      {/* ステッププログレスバー */}
      <div className="flex items-center gap-0 mb-8">
        {STEPS.map((step, i) => {
          const isActive = i === currentStepIndex
          const isDone = i < currentStepIndex
          return (
            <div key={step.key} className="flex items-center flex-1">
              <div className="flex flex-col items-center flex-1">
                <div className={`w-9 h-9 rounded-full flex items-center justify-center text-sm font-bold transition-all ${
                  isDone
                    ? 'bg-green-500 text-white'
                    : isActive
                      ? 'bg-purple-600 text-white ring-4 ring-purple-200'
                      : 'bg-gray-100 text-gray-400'
                }`}>
                  {isDone ? '✓' : i + 1}
                </div>
                <span className={`text-xs mt-1 font-medium text-center leading-tight ${
                  isActive ? 'text-purple-600' : isDone ? 'text-green-600' : 'text-gray-400'
                }`}>
                  {step.icon} {step.label}
                </span>
              </div>
              {i < STEPS.length - 1 && (
                <div className={`h-0.5 flex-1 -mt-4 ${isDone ? 'bg-green-400' : 'bg-gray-200'}`} />
              )}
            </div>
          )
        })}
      </div>

      {/* タブ */}
      <div className="flex gap-2 mb-6">
        {(['new', 'history'] as const).map(tab => (
          <button key={tab} onClick={() => setActiveTab(tab)}
            className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
              activeTab === tab
                ? 'bg-purple-600 text-white'
                : 'bg-white text-gray-600 hover:bg-gray-50 border border-gray-200'
            }`}
          >
            {tab === 'new' ? '✨ 新規生成' : `📋 生成履歴 (${plans.length})`}
          </button>
        ))}
      </div>

      {/* ══════════ 新規生成タブ ══════════ */}
      {activeTab === 'new' && (
        <div className="space-y-6">

          {/* エラーバナー */}
          {error && (
            <div className="bg-red-50 text-red-700 text-sm px-4 py-3 rounded-lg border border-red-200 flex items-start gap-2">
              <span className="shrink-0">⚠️</span>
              <span>{error}</span>
            </div>
          )}

          {/* ════ Step 0: 設定カード ════ */}
          {phase === 'idle' && (
            <div className="bg-white rounded-2xl border border-gray-100 shadow-sm p-6 space-y-5">
              <h2 className="font-semibold text-gray-800">⚙️ 生成設定</h2>

              {/* キャラクター選択 */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  キャラクター <span className="text-red-500">*</span>
                </label>
                {characters.length === 0 ? (
                  <div className="text-sm text-amber-600 bg-amber-50 px-3 py-2 rounded-lg">
                    キャラクターが未登録です。先に「キャラクター設定」で作成してください。
                  </div>
                ) : (
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                    {characters.map(c => (
                      <button key={c.id} type="button" onClick={() => setSelectedChar(c.id)}
                        className={`text-left px-4 py-3 rounded-xl border-2 transition-all ${
                          selectedChar === c.id ? 'border-purple-500 bg-purple-50' : 'border-gray-200 hover:border-gray-300'
                        }`}>
                        <div className="flex items-center gap-2">
                          <span className="text-xl">🎭</span>
                          <div>
                            <p className="font-medium text-sm text-gray-800">{c.name}</p>
                            <p className="text-xs text-gray-500">{c.tone || '口調未設定'}</p>
                          </div>
                          {c.is_default && (
                            <span className="ml-auto text-xs bg-green-100 text-green-700 px-1.5 py-0.5 rounded-full">デフォルト</span>
                          )}
                        </div>
                      </button>
                    ))}
                  </div>
                )}
              </div>

              {/* テーマ選択 */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  動画テーマ設定 <span className="text-red-500">*</span>
                </label>
                {themes.length === 0 ? (
                  <div className="text-sm text-amber-600 bg-amber-50 px-3 py-2 rounded-lg">
                    テーマが未登録です。先に「動画テーマ設定」で作成してください。
                  </div>
                ) : (
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                    {themes.map(t => (
                      <button key={t.id} type="button" onClick={() => setSelectedTheme(t.id)}
                        className={`text-left px-4 py-3 rounded-xl border-2 transition-all ${
                          selectedTheme === t.id ? 'border-purple-500 bg-purple-50' : 'border-gray-200 hover:border-gray-300'
                        }`}>
                        <div className="flex items-center gap-2">
                          <span className="text-xl">🎯</span>
                          <div>
                            <p className="font-medium text-sm text-gray-800">{t.name}</p>
                            <p className="text-xs text-gray-500 truncate w-48">{t.main_channel_theme || 'テーマ未設定'}</p>
                          </div>
                          {t.is_default && (
                            <span className="ml-auto text-xs bg-green-100 text-green-700 px-1.5 py-0.5 rounded-full">デフォルト</span>
                          )}
                        </div>
                      </button>
                    ))}
                  </div>
                )}
              </div>

              {/* 追加トピック */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">今回のトピック（任意）</label>
                <input type="text" value={customTopic} onChange={e => setCustomTopic(e.target.value)}
                  placeholder="例: ChatGPTを使った副業術5選、最新AIツールまとめ"
                  className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-purple-500"
                />
                <p className="text-xs text-gray-400 mt-1">空白の場合はテーマ設定に基づいてAIが自動決定します</p>
              </div>

              <button onClick={handleGeneratePlan} disabled={!selectedChar || !selectedTheme}
                className="w-full bg-gradient-to-r from-purple-600 to-pink-500 hover:from-purple-700 hover:to-pink-600 disabled:opacity-50 text-white py-3 rounded-xl text-sm font-bold shadow-md transition-all">
                🧠 Step 1: 企画を生成する (~10-15秒)
              </button>
            </div>
          )}

          {/* ════ Step 1 ローディング ════ */}
          {phase === 'plan_loading' && <LoadingCard color="purple" title="🧠 動画企画を生成中..." sub="キャラクターとテーマを分析して最適な企画を考えています" eta="通常10〜15秒" />}

          {/* ════ Step 1 完了: 企画表示 ════ */}
          {['plan_done', 'script_loading', 'script_done', 'voice_loading', 'voice_done', 'video_loading', 'video_polling', 'done'].includes(phase) && planResult && (
            <PlanCard plan={planResult} aiMode={aiMode} showRetry={phase === 'plan_done'} onReset={handleReset}>
              {phase === 'plan_done' && (
                <button onClick={handleGenerateScript}
                  className="w-full bg-gradient-to-r from-blue-600 to-purple-600 hover:from-blue-700 hover:to-purple-700 text-white py-3 rounded-xl text-sm font-bold shadow-md transition-all">
                  📝 Step 2: 台本を生成する (~20-30秒)
                </button>
              )}
            </PlanCard>
          )}

          {/* ════ Step 2 ローディング ════ */}
          {phase === 'script_loading' && <LoadingCard color="blue" title="📝 台本を生成中..." sub="キャラクターの口調で台本を書いています" eta="通常20〜30秒（GPT-4o使用時）" />}

          {/* ════ Step 2 完了: 台本表示 ════ */}
          {['script_done', 'voice_loading', 'voice_done', 'video_loading', 'video_polling', 'done'].includes(phase) && scriptResult && planResult && (
            <ScriptCard
              script={scriptResult}
              plan={planResult}
              aiMode={aiMode}
              expandedSections={expandedSections}
              onToggleSection={toggleSection}
            >
              {phase === 'script_done' && (
                <button onClick={handleGenerateVoice}
                  className="w-full bg-gradient-to-r from-green-600 to-teal-600 hover:from-green-700 hover:to-teal-700 text-white py-3 rounded-xl text-sm font-bold shadow-md transition-all">
                  🎤 Step 3: 音声を生成する (~15-60秒)
                </button>
              )}
            </ScriptCard>
          )}

          {/* ════ Step 3 ローディング ════ */}
          {phase === 'voice_loading' && <LoadingCard color="green" title="🎤 音声を生成中..." sub="OpenAI TTS でキャラクターの声を生成しています（セクション数×数秒）" eta="通常15〜60秒" />}

          {/* ════ Step 3 完了: 音声生成結果 ════ */}
          {['voice_done', 'video_loading', 'video_polling', 'done'].includes(phase) && voiceResult && (
            <div className="bg-white rounded-2xl border border-gray-100 shadow-sm p-6">
              <div className="flex items-center justify-between mb-4">
                <h2 className="text-lg font-bold text-gray-900">🎤 音声生成 <span className="text-green-500 text-base">✓ 完成</span></h2>
                <span className="text-sm text-gray-500">
                  {voiceResult.voice_count}セクション ·
                  読み上げ約{(voiceResult.total_duration_seconds / 60).toFixed(1)}分
                </span>
              </div>
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 mb-4">
                {voiceResult.voices.map((v, i) => (
                  <div key={i} className={`rounded-lg p-2 text-center text-xs border ${
                    v.status === 'completed' || v.status === 'cached'
                      ? 'bg-green-50 border-green-200 text-green-700'
                      : v.status === 'failed'
                        ? 'bg-red-50 border-red-200 text-red-700'
                        : 'bg-gray-50 border-gray-200 text-gray-500'
                  }`}>
                    <p className="font-semibold">{SECTION_LABEL[v.section_type] || v.section_type}</p>
                    <p className="mt-0.5 opacity-70">
                      {v.status === 'completed' ? '✅' : v.status === 'cached' ? '💾' : v.status === 'failed' ? '❌' : '⏭️'}
                      {' '}{v.status === 'skipped' ? 'スキップ' : v.status === 'cached' ? 'キャッシュ' : v.status}
                    </p>
                    {v.duration_seconds > 0 && <p className="opacity-50">{v.duration_seconds.toFixed(1)}秒</p>}
                  </div>
                ))}
              </div>
              {phase === 'voice_done' && (
                <button onClick={handleGenerateVideo}
                  className="w-full bg-gradient-to-r from-orange-500 to-red-500 hover:from-orange-600 hover:to-red-600 text-white py-3 rounded-xl text-sm font-bold shadow-md transition-all">
                  🎬 Step 4: 動画を生成してYouTubeにアップロード
                </button>
              )}
            </div>
          )}

          {/* ════ Step 4 ローディング（ジョブキック直後）════ */}
          {phase === 'video_loading' && <LoadingCard color="orange" title="🎬 動画生成ジョブを投入中..." sub="バックグラウンドワーカーに処理を依頼しています" eta="数秒でポーリングを開始します" />}

          {/* ════ Step 4 ポーリング + 完了 ════ */}
          {(phase === 'video_polling' || phase === 'done') && renderStatus && (
            <div className="bg-white rounded-2xl border border-gray-100 shadow-sm p-6">
              <div className="flex items-center justify-between mb-5">
                <h2 className="text-lg font-bold text-gray-900">
                  🎬 動画生成{phase === 'done' ? <span className="text-green-500 text-base ml-2">✓ 完成</span> : <span className="text-orange-500 text-base ml-2">処理中...</span>}
                </h2>
                {phase === 'video_polling' && (
                  <div className="w-5 h-5 border-2 border-orange-400 border-t-transparent rounded-full animate-spin" />
                )}
              </div>

              {/* 進捗バー */}
              <div className="mb-4">
                <div className="flex justify-between text-xs text-gray-500 mb-1">
                  <span>{renderStatus.current_step || '処理中...'}</span>
                  <span>{renderStatus.progress_percent}%</span>
                </div>
                <div className="w-full bg-gray-100 rounded-full h-3 overflow-hidden">
                  <div
                    className={`h-3 rounded-full transition-all duration-700 ${
                      phase === 'done' ? 'bg-green-500' : 'bg-gradient-to-r from-orange-400 to-red-500'
                    }`}
                    style={{ width: `${renderStatus.progress_percent}%` }}
                  />
                </div>
              </div>

              {/* ステータスバッジ */}
              <div className="flex flex-wrap gap-2 text-xs mb-4">
                <StatusBadge status={renderStatus.status} />
                {renderStatus.started_at && (
                  <span className="bg-gray-50 text-gray-600 px-2 py-1 rounded">
                    開始: {new Date(renderStatus.started_at).toLocaleTimeString('ja-JP')}
                  </span>
                )}
                {renderStatus.completed_at && (
                  <span className="bg-gray-50 text-gray-600 px-2 py-1 rounded">
                    完了: {new Date(renderStatus.completed_at).toLocaleTimeString('ja-JP')}
                  </span>
                )}
              </div>

              {/* YouTube 結果 */}
              {renderStatus.youtube_upload && (
                <div className="bg-gradient-to-r from-red-50 to-orange-50 border border-red-200 rounded-xl p-5">
                  <div className="flex items-center gap-2 mb-3">
                    <span className="text-2xl">📺</span>
                    <div>
                      <p className="font-bold text-red-700">YouTubeアップロード完了！</p>
                      <p className="text-xs text-gray-500">
                        ステータス: {renderStatus.youtube_upload.privacy_status === 'private' ? '🔒 非公開' : renderStatus.youtube_upload.privacy_status}
                      </p>
                    </div>
                  </div>
                  <a
                    href={renderStatus.youtube_upload.youtube_url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="block w-full text-center bg-red-600 hover:bg-red-700 text-white py-2.5 rounded-lg text-sm font-bold transition-colors"
                  >
                    YouTube で確認する →
                  </a>
                  <p className="text-xs text-gray-400 mt-2 text-center">
                    現在は非公開状態です。レビュー後に公開してください。
                  </p>
                </div>
              )}

              {/* 動画ファイルURL（R2） */}
              {renderStatus.output_file_url && !renderStatus.youtube_upload && (
                <div className="bg-blue-50 border border-blue-200 rounded-lg p-3 text-sm text-blue-700">
                  <p className="font-medium mb-1">📁 動画ファイル生成完了</p>
                  <a href={renderStatus.output_file_url} target="_blank" rel="noopener noreferrer"
                    className="underline text-xs break-all">
                    {renderStatus.output_file_url}
                  </a>
                </div>
              )}

              {phase === 'done' && (
                <button onClick={handleReset}
                  className="mt-5 w-full text-sm text-purple-600 hover:text-purple-700 border border-purple-200 hover:border-purple-300 py-2.5 rounded-xl transition-colors">
                  ↩ 新しい動画を生成する
                </button>
              )}
            </div>
          )}

        </div>
      )}

      {/* ══════════ 履歴タブ ══════════ */}
      {activeTab === 'history' && (
        <div className="space-y-3">
          {plans.length === 0 ? (
            <div className="text-center py-16 text-gray-400">
              <div className="text-5xl mb-4">📋</div>
              <p>まだ生成した企画がありません</p>
            </div>
          ) : (
            plans.map(plan => (
              <div key={plan.id} className="bg-white rounded-xl border border-gray-100 shadow-sm p-4 flex items-center justify-between gap-4">
                <div className="flex-1 min-w-0">
                  <p className="font-semibold text-gray-800 truncate">{plan.title}</p>
                  <div className="flex items-center gap-3 mt-1">
                    <span className="text-xs text-gray-400">
                      {plan.created_at ? new Date(plan.created_at).toLocaleDateString('ja-JP') : ''}
                    </span>
                    <span className="text-xs text-gray-400">{fmtSec(plan.total_duration_seconds)}</span>
                    <span className={`text-xs px-2 py-0.5 rounded-full ${
                      plan.has_script ? 'bg-green-100 text-green-700' : 'bg-gray-100 text-gray-600'
                    }`}>
                      {plan.has_script ? '台本あり' : '台本なし'}
                    </span>
                  </div>
                </div>
                <button onClick={() => handleLoadPlan(plan.id)}
                  className="shrink-0 bg-purple-50 hover:bg-purple-100 text-purple-700 text-sm px-4 py-2 rounded-lg transition-colors">
                  表示
                </button>
              </div>
            ))
          )}
        </div>
      )}
    </div>
  )
}

// ─────────────────────────────────────────
// サブコンポーネント
// ─────────────────────────────────────────

function LoadingCard({ color, title, sub, eta }: { color: string; title: string; sub: string; eta: string }) {
  const borderColor = color === 'purple' ? 'border-purple-200' : color === 'blue' ? 'border-blue-200' : color === 'green' ? 'border-green-200' : 'border-orange-200'
  const spinColor = color === 'purple' ? 'border-purple-500' : color === 'blue' ? 'border-blue-500' : color === 'green' ? 'border-green-500' : 'border-orange-500'
  return (
    <div className={`bg-white rounded-2xl border ${borderColor} shadow-sm p-8 text-center space-y-4`}>
      <div className="flex justify-center">
        <div className={`w-12 h-12 border-4 ${spinColor} border-t-transparent rounded-full animate-spin`} />
      </div>
      <div>
        <p className="font-semibold text-gray-800">{title}</p>
        <p className="text-sm text-gray-500 mt-1">{sub}</p>
      </div>
      <p className="text-xs text-gray-400">{eta}</p>
    </div>
  )
}

function PlanCard({ plan, aiMode, showRetry, onReset, children }: {
  plan: VideoPlan; aiMode: string; showRetry: boolean; onReset: () => void; children?: React.ReactNode
}) {
  function fmtSec(sec: number) {
    const m = Math.floor(sec / 60); const s = sec % 60
    return m > 0 ? `${m}分${s > 0 ? s + '秒' : ''}` : `${s}秒`
  }
  return (
    <section className="bg-white rounded-2xl border border-gray-100 shadow-sm p-6">
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-lg font-bold text-gray-900">📋 動画企画 <span className="text-green-500 text-base">✓ 完成</span></h2>
        {showRetry && (
          <button onClick={onReset} className="text-sm text-gray-400 hover:text-gray-600">↩ やり直す</button>
        )}
      </div>
      {aiMode && (
        <div className="mb-4">
          <span className={`text-xs px-3 py-1 rounded-full font-medium ${
            aiMode === 'openai' ? 'bg-green-100 text-green-700' : aiMode === 'cached' ? 'bg-blue-100 text-blue-700' : 'bg-amber-100 text-amber-700'
          }`}>
            {aiMode === 'openai' ? '✅ OpenAI GPT-4o で生成' : aiMode === 'cached' ? '💾 キャッシュ済み' : '🔧 モックデータ'}
          </span>
        </div>
      )}
      <div className="space-y-3">
        <div>
          <p className="text-xs text-gray-500 mb-1">タイトル（AI提案）</p>
          <p className="text-xl font-bold text-purple-700">{plan.title}</p>
        </div>
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 pt-2">
          <div className="bg-gray-50 rounded-xl p-3"><p className="text-xs text-gray-500 mb-1">🎯 動画の目的</p><p className="text-sm text-gray-800">{plan.goal || '—'}</p></div>
          <div className="bg-gray-50 rounded-xl p-3"><p className="text-xs text-gray-500 mb-1">👥 ターゲット</p><p className="text-sm text-gray-800">{plan.target_audience || '—'}</p></div>
          <div className="bg-gray-50 rounded-xl p-3"><p className="text-xs text-gray-500 mb-1">⏱ 動画尺</p><p className="text-sm text-gray-800 font-medium">{fmtSec(plan.total_duration_seconds)}</p></div>
          <div className="bg-gray-50 rounded-xl p-3"><p className="text-xs text-gray-500 mb-1">📣 CTA</p><p className="text-sm text-gray-800">{plan.cta || '—'}</p></div>
        </div>
        {plan.youtube_title_candidates?.length > 0 && (
          <div className="pt-2">
            <p className="text-xs text-gray-500 mb-2">🏷 YouTubeタイトル候補</p>
            <div className="space-y-1">
              {plan.youtube_title_candidates.map((t, i) => (
                <div key={i} className="flex items-start gap-2">
                  <span className="text-xs text-gray-400 mt-0.5 w-4 shrink-0">{i + 1}.</span>
                  <p className="text-sm text-gray-700">{t}</p>
                </div>
              ))}
            </div>
          </div>
        )}
        {plan.youtube_tags?.length > 0 && (
          <div className="pt-1">
            <p className="text-xs text-gray-500 mb-2">🔖 タグ</p>
            <div className="flex flex-wrap gap-1">
              {plan.youtube_tags.map((tag, i) => (
                <span key={i} className="bg-blue-50 text-blue-700 text-xs px-2 py-0.5 rounded-full">#{tag}</span>
              ))}
            </div>
          </div>
        )}
      </div>
      {children && <div className="mt-6 pt-5 border-t border-gray-100">{children}</div>}
    </section>
  )
}

function ScriptCard({ script, plan, aiMode, expandedSections, onToggleSection, children }: {
  script: ScriptResult; plan: VideoPlan; aiMode: string; expandedSections: Set<number>; onToggleSection: (i: number) => void; children?: React.ReactNode
}) {
  const totalChars = script.full_script?.length ?? 0
  const targetChars = Math.floor(plan.total_duration_seconds * 6.5)
  const pct = Math.min(100, Math.round((totalChars / targetChars) * 100))
  const estMin = (totalChars / 6.5 / 60).toFixed(1)
  const ok = pct >= 80

  const EXPRESSION_EMOJI: Record<string, string> = { normal: '😐', smile: '😊', surprise: '😲', troubled: '😟', serious: '😤' }
  const SECTION_COLOR: Record<string, string> = {
    hook: 'bg-pink-50 border-pink-300 text-pink-700', problem: 'bg-amber-50 border-amber-300 text-amber-700',
    main: 'bg-blue-50 border-blue-300 text-blue-700', example: 'bg-indigo-50 border-indigo-300 text-indigo-700',
    summary: 'bg-green-50 border-green-300 text-green-700', cta: 'bg-purple-50 border-purple-300 text-purple-700',
    custom: 'bg-gray-50 border-gray-300 text-gray-700',
  }
  const SECTION_LABEL: Record<string, string> = { hook: '冒頭フック', problem: '問題提起', main: '本編', example: '具体例', summary: 'まとめ', cta: 'CTA', custom: 'カスタム' }
  function fmtSec(sec: number) { const m = Math.floor(sec / 60); const s = sec % 60; return m > 0 ? `${m}分${s > 0 ? s + '秒' : ''}` : `${s}秒` }

  return (
    <section className="bg-white rounded-2xl border border-gray-100 shadow-sm p-6">
      <div className="flex items-start justify-between mb-2 flex-wrap gap-2">
        <h2 className="text-lg font-bold text-gray-900">📝 台本 <span className="text-green-500 text-base">✓ 完成</span></h2>
        <div className={`text-xs px-3 py-1.5 rounded-full font-medium flex items-center gap-1.5 ${ok ? 'bg-green-100 text-green-700' : 'bg-amber-100 text-amber-700'}`}>
          <span>{ok ? '✅' : '⚠️'}</span>
          <span>{totalChars.toLocaleString()}文字</span>
          <span className="opacity-60">|</span>
          <span>読み上げ約{estMin}分</span>
          <span className="opacity-60">|</span>
          <span>目標対比 {pct}%</span>
        </div>
      </div>
      <p className="text-xs text-gray-400 mb-4">各セクションをクリックすると詳細を確認できます</p>
      {script.hook_text && (
        <div className="bg-gradient-to-r from-pink-50 to-purple-50 border border-pink-200 rounded-xl p-4 mb-4">
          <p className="text-xs font-medium text-pink-600 mb-2">⚡ 冒頭フック（最初の15秒）</p>
          <p className="text-sm text-gray-800 leading-relaxed">{script.hook_text}</p>
        </div>
      )}
      <div className="space-y-2">
        {script.sections.map((sec, i) => {
          const colorClass = SECTION_COLOR[sec.section_type] || SECTION_COLOR.custom
          const isExpanded = expandedSections.has(i)
          return (
            <div key={i} className={`border rounded-xl overflow-hidden ${colorClass}`}>
              <button onClick={() => onToggleSection(i)} className="w-full flex items-center gap-3 px-4 py-3 text-left hover:opacity-80 transition-opacity">
                <span className="text-lg">{EXPRESSION_EMOJI[sec.expression] || '😐'}</span>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2">
                    <span className="text-xs font-bold uppercase tracking-wide opacity-70">{SECTION_LABEL[sec.section_type] || sec.section_type}</span>
                    <span className="text-xs opacity-60">·</span>
                    <span className="text-xs opacity-70">{fmtSec(sec.duration_seconds)}</span>
                  </div>
                  <p className="font-semibold text-sm truncate">{sec.title}</p>
                </div>
                <span className="text-lg opacity-50">{isExpanded ? '▲' : '▼'}</span>
              </button>
              {isExpanded && (
                <div className="px-4 pb-4 border-t border-current border-opacity-20 space-y-3">
                  <div className="pt-3">
                    <p className="text-xs font-medium opacity-70 mb-1">🎤 ナレーション</p>
                    <p className="text-sm leading-relaxed bg-white bg-opacity-60 rounded-lg p-3 text-gray-800">{sec.narration}</p>
                  </div>
                  {sec.subtitle && (
                    <div>
                      <p className="text-xs font-medium opacity-70 mb-1">💬 字幕テキスト</p>
                      <p className="text-xs bg-white bg-opacity-60 rounded p-2 text-gray-700 italic">{sec.subtitle}</p>
                    </div>
                  )}
                  {sec.direction && (
                    <div>
                      <p className="text-xs font-medium opacity-70 mb-1">🎬 演出指示</p>
                      <p className="text-xs bg-white bg-opacity-60 rounded p-2 text-gray-600">{sec.direction}</p>
                    </div>
                  )}
                </div>
              )}
            </div>
          )
        })}
      </div>
      {script.full_script && (
        <details className="mt-4">
          <summary className="text-xs text-gray-500 cursor-pointer hover:text-gray-700">📄 台本全文テキスト（クリックで展開・コピー用）</summary>
          <textarea readOnly value={script.full_script} rows={12}
            className="mt-2 w-full text-xs text-gray-700 bg-gray-50 border border-gray-200 rounded-lg p-3 font-mono leading-relaxed outline-none resize-y" />
        </details>
      )}
      {children && <div className="mt-6 pt-5 border-t border-gray-100">{children}</div>}
    </section>
  )
}

function StatusBadge({ status }: { status: string }) {
  const map: Record<string, { label: string; cls: string }> = {
    pending:          { label: '⏳ 待機中',         cls: 'bg-gray-100 text-gray-600' },
    generating_assets:{ label: '🖼 素材生成中',     cls: 'bg-blue-100 text-blue-700' },
    rendering:        { label: '🎬 レンダリング中', cls: 'bg-orange-100 text-orange-700' },
    uploading:        { label: '📤 アップロード中', cls: 'bg-yellow-100 text-yellow-700' },
    waiting_review:   { label: '👀 レビュー待ち',   cls: 'bg-purple-100 text-purple-700' },
    approved:         { label: '✅ 承認済み',       cls: 'bg-green-100 text-green-700' },
    published:        { label: '🌐 公開済み',       cls: 'bg-green-200 text-green-800' },
    failed:           { label: '❌ 失敗',           cls: 'bg-red-100 text-red-700' },
  }
  const info = map[status] || { label: status, cls: 'bg-gray-100 text-gray-600' }
  return <span className={`px-2 py-1 rounded text-xs font-medium ${info.cls}`}>{info.label}</span>
}
