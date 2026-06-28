'use client'
import { useState, useEffect } from 'react'
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

// 全体の生成フェーズ管理
type GenPhase =
  | 'idle'         // 未開始
  | 'plan_loading' // 企画生成中
  | 'plan_done'    // 企画完了 → 台本生成待ち
  | 'script_loading' // 台本生成中
  | 'done'         // 全完了

const EXPRESSION_EMOJI: Record<string, string> = {
  normal: '😐',
  smile: '😊',
  surprise: '😲',
  troubled: '😟',
  serious: '😤',
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

// ─────────────────────────────────────────
// メインコンポーネント
// ─────────────────────────────────────────
export default function GeneratePage() {
  const [characters, setCharacters] = useState<any[]>([])
  const [themes, setThemes] = useState<any[]>([])
  const [selectedChar, setSelectedChar] = useState('')
  const [selectedTheme, setSelectedTheme] = useState('')
  const [customTopic, setCustomTopic] = useState('')
  const [aiMode, setAiMode] = useState<'mock' | 'openai' | 'cached' | ''>('')

  const [loading, setLoading] = useState(true)
  const [phase, setPhase] = useState<GenPhase>('idle')
  const [planResult, setPlanResult] = useState<VideoPlan | null>(null)
  const [scriptResult, setScriptResult] = useState<ScriptResult | null>(null)
  const [error, setError] = useState('')

  // 過去の生成履歴
  const [plans, setPlans] = useState<any[]>([])
  const [activeTab, setActiveTab] = useState<'new' | 'history'>('new')
  // 台本セクションの展開状態
  const [expandedSections, setExpandedSections] = useState<Set<number>>(new Set([0]))

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

  // ── Step 1: 企画生成 ──
  const handleGeneratePlan = async () => {
    if (!selectedChar || !selectedTheme) {
      setError('キャラクターとテーマを選択してください')
      return
    }
    setError('')
    setPlanResult(null)
    setScriptResult(null)
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
        || (err.code === 'ECONNABORTED' ? 'タイムアウト: サーバーの応答が遅いです。もう一度お試しください。' : null)
        || '企画生成に失敗しました。しばらく経ってから再試行してください。'
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
      setPhase('done')
      setExpandedSections(new Set([0]))
      // 履歴に追加
      setPlans(prev => [
        {
          id: planResult.id,
          title: planResult.title,
          total_duration_seconds: planResult.total_duration_seconds,
          status: 'draft',
          created_at: new Date().toISOString(),
          has_script: true,
        },
        ...prev.filter(p => p.id !== planResult.id),
      ])
    } catch (err: any) {
      const msg = err.response?.data?.detail
        || (err.code === 'ECONNABORTED' ? 'タイムアウト: 台本の生成に時間がかかっています。もう一度「台本を生成」ボタンを押してください。' : null)
        || '台本生成に失敗しました。しばらく経ってから再試行してください。'
      setError(msg)
      // plan_done に戻してリトライできるようにする
      setPhase('plan_done')
    }
  }

  const toggleSection = (idx: number) => {
    setExpandedSections(prev => {
      const next = new Set(prev)
      next.has(idx) ? next.delete(idx) : next.add(idx)
      return next
    })
  }

  const handleReset = () => {
    setPlanResult(null)
    setScriptResult(null)
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
        setPhase('done')
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

  const isGenerating = phase === 'plan_loading' || phase === 'script_loading'

  return (
    <div className="p-8 max-w-5xl mx-auto">
      {/* ヘッダー */}
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-gray-900">🎬 動画生成</h1>
        <p className="text-sm text-gray-500 mt-1">
          キャラクターとテーマを選ぶだけで、AIが企画・台本を自動作成します
        </p>
      </div>

      {/* ステッププログレスバー（常時表示） */}
      <div className="flex items-center gap-0 mb-8">
        {[
          { key: 'settings', label: '設定', icon: '⚙️' },
          { key: 'plan',     label: '企画生成', icon: '🧠' },
          { key: 'script',   label: '台本生成', icon: '📝' },
          { key: 'done',     label: '完成', icon: '✅' },
        ].map((step, i) => {
          const isActive =
            (step.key === 'settings' && (phase === 'idle')) ||
            (step.key === 'plan' && (phase === 'plan_loading' || phase === 'plan_done')) ||
            (step.key === 'script' && phase === 'script_loading') ||
            (step.key === 'done' && phase === 'done')
          const isDone =
            (step.key === 'settings' && phase !== 'idle') ||
            (step.key === 'plan' && (phase === 'script_loading' || phase === 'done')) ||
            (step.key === 'script' && phase === 'done')
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
                <span className={`text-xs mt-1 font-medium ${
                  isActive ? 'text-purple-600' : isDone ? 'text-green-600' : 'text-gray-400'
                }`}>
                  {step.label}
                </span>
              </div>
              {i < 3 && (
                <div className={`h-0.5 flex-1 -mt-4 ${
                  isDone ? 'bg-green-400' : 'bg-gray-200'
                }`} />
              )}
            </div>
          )
        })}
      </div>

      {/* タブ */}
      <div className="flex gap-2 mb-6">
        {(['new', 'history'] as const).map(tab => (
          <button
            key={tab}
            onClick={() => setActiveTab(tab)}
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

          {/* ── エラーバナー ── */}
          {error && (
            <div className="bg-red-50 text-red-700 text-sm px-4 py-3 rounded-lg border border-red-200 flex items-start gap-2">
              <span className="shrink-0">⚠️</span>
              <span>{error}</span>
            </div>
          )}

          {/* ── Step 0: 設定カード（idle または plan_done/done で再表示） ── */}
          {(phase === 'idle') && (
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
                      <button
                        key={c.id}
                        type="button"
                        onClick={() => setSelectedChar(c.id)}
                        className={`text-left px-4 py-3 rounded-xl border-2 transition-all ${
                          selectedChar === c.id
                            ? 'border-purple-500 bg-purple-50'
                            : 'border-gray-200 hover:border-gray-300'
                        }`}
                      >
                        <div className="flex items-center gap-2">
                          <span className="text-xl">🎭</span>
                          <div>
                            <p className="font-medium text-sm text-gray-800">{c.name}</p>
                            <p className="text-xs text-gray-500">{c.tone || '口調未設定'}</p>
                          </div>
                          {c.is_default && (
                            <span className="ml-auto text-xs bg-green-100 text-green-700 px-1.5 py-0.5 rounded-full">
                              デフォルト
                            </span>
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
                      <button
                        key={t.id}
                        type="button"
                        onClick={() => setSelectedTheme(t.id)}
                        className={`text-left px-4 py-3 rounded-xl border-2 transition-all ${
                          selectedTheme === t.id
                            ? 'border-purple-500 bg-purple-50'
                            : 'border-gray-200 hover:border-gray-300'
                        }`}
                      >
                        <div className="flex items-center gap-2">
                          <span className="text-xl">🎯</span>
                          <div>
                            <p className="font-medium text-sm text-gray-800">{t.name}</p>
                            <p className="text-xs text-gray-500 truncate w-48">
                              {t.main_channel_theme || 'テーマ未設定'}
                            </p>
                          </div>
                          {t.is_default && (
                            <span className="ml-auto text-xs bg-green-100 text-green-700 px-1.5 py-0.5 rounded-full">
                              デフォルト
                            </span>
                          )}
                        </div>
                      </button>
                    ))}
                  </div>
                )}
              </div>

              {/* 追加トピック */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  今回のトピック（任意）
                </label>
                <input
                  type="text"
                  value={customTopic}
                  onChange={e => setCustomTopic(e.target.value)}
                  placeholder="例: ChatGPTを使った副業術5選、最新AIツールまとめ"
                  className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-purple-500"
                />
                <p className="text-xs text-gray-400 mt-1">
                  空白の場合はテーマ設定に基づいてAIが自動決定します
                </p>
              </div>

              {/* Step 1 生成ボタン */}
              <button
                onClick={handleGeneratePlan}
                disabled={!selectedChar || !selectedTheme}
                className="w-full bg-gradient-to-r from-purple-600 to-pink-500 hover:from-purple-700 hover:to-pink-600 disabled:opacity-50 text-white py-3 rounded-xl text-sm font-bold shadow-md transition-all"
              >
                🧠 Step 1: 企画を生成する (~10-15秒)
              </button>
            </div>
          )}

          {/* ── Step 1 ローディング ── */}
          {phase === 'plan_loading' && (
            <div className="bg-white rounded-2xl border border-purple-200 shadow-sm p-8 text-center space-y-4">
              <div className="flex justify-center">
                <div className="w-12 h-12 border-4 border-purple-500 border-t-transparent rounded-full animate-spin" />
              </div>
              <div>
                <p className="font-semibold text-gray-800">🧠 動画企画を生成中...</p>
                <p className="text-sm text-gray-500 mt-1">
                  キャラクターとテーマを分析して、最適な企画を考えています
                </p>
              </div>
              <p className="text-xs text-gray-400">通常10〜15秒かかります</p>
            </div>
          )}

          {/* ── Step 1 完了: 企画表示 + Step 2 ボタン ── */}
          {(phase === 'plan_done' || phase === 'script_loading' || phase === 'done') && planResult && (
            <section className="bg-white rounded-2xl border border-gray-100 shadow-sm p-6">
              <div className="flex items-center justify-between mb-4">
                <h2 className="text-lg font-bold text-gray-900">📋 動画企画 <span className="text-green-500 text-base">✓ 完成</span></h2>
                {phase === 'plan_done' && (
                  <button
                    onClick={handleReset}
                    className="text-sm text-gray-400 hover:text-gray-600"
                  >
                    ↩ やり直す
                  </button>
                )}
              </div>

              {/* AIモードバッジ */}
              {aiMode && (
                <div className="mb-4">
                  <span className={`text-xs px-3 py-1 rounded-full font-medium ${
                    aiMode === 'openai'
                      ? 'bg-green-100 text-green-700'
                      : aiMode === 'cached'
                        ? 'bg-blue-100 text-blue-700'
                        : 'bg-amber-100 text-amber-700'
                  }`}>
                    {aiMode === 'openai' ? '✅ OpenAI GPT-4o で生成' :
                     aiMode === 'cached' ? '💾 キャッシュ済み' :
                     '🔧 モックデータ（OpenAI キー未設定）'}
                  </span>
                </div>
              )}

              <div className="space-y-3">
                <div>
                  <p className="text-xs text-gray-500 mb-1">タイトル（AI提案）</p>
                  <p className="text-xl font-bold text-purple-700">{planResult.title}</p>
                </div>
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 pt-2">
                  <div className="bg-gray-50 rounded-xl p-3">
                    <p className="text-xs text-gray-500 mb-1">🎯 動画の目的</p>
                    <p className="text-sm text-gray-800">{planResult.goal || '—'}</p>
                  </div>
                  <div className="bg-gray-50 rounded-xl p-3">
                    <p className="text-xs text-gray-500 mb-1">👥 ターゲット視聴者</p>
                    <p className="text-sm text-gray-800">{planResult.target_audience || '—'}</p>
                  </div>
                  <div className="bg-gray-50 rounded-xl p-3">
                    <p className="text-xs text-gray-500 mb-1">⏱ 動画尺</p>
                    <p className="text-sm text-gray-800 font-medium">
                      {fmtSec(planResult.total_duration_seconds)}
                    </p>
                  </div>
                  <div className="bg-gray-50 rounded-xl p-3">
                    <p className="text-xs text-gray-500 mb-1">📣 CTA</p>
                    <p className="text-sm text-gray-800">{planResult.cta || '—'}</p>
                  </div>
                </div>

                {/* タイトル候補 */}
                {planResult.youtube_title_candidates?.length > 0 && (
                  <div className="pt-2">
                    <p className="text-xs text-gray-500 mb-2">🏷 YouTubeタイトル候補</p>
                    <div className="space-y-1">
                      {planResult.youtube_title_candidates.map((title, i) => (
                        <div key={i} className="flex items-start gap-2">
                          <span className="text-xs text-gray-400 mt-0.5 w-4 shrink-0">{i + 1}.</span>
                          <p className="text-sm text-gray-700">{title}</p>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {/* タグ */}
                {planResult.youtube_tags?.length > 0 && (
                  <div className="pt-1">
                    <p className="text-xs text-gray-500 mb-2">🔖 タグ</p>
                    <div className="flex flex-wrap gap-1">
                      {planResult.youtube_tags.map((tag, i) => (
                        <span key={i} className="bg-blue-50 text-blue-700 text-xs px-2 py-0.5 rounded-full">
                          #{tag}
                        </span>
                      ))}
                    </div>
                  </div>
                )}

                {/* 概要欄 */}
                {planResult.youtube_description && (
                  <details className="pt-1">
                    <summary className="text-xs text-gray-500 cursor-pointer hover:text-gray-700">
                      📄 概要欄テキスト（クリックで展開）
                    </summary>
                    <pre className="mt-2 text-xs text-gray-600 bg-gray-50 p-3 rounded-lg whitespace-pre-wrap leading-relaxed">
                      {planResult.youtube_description}
                    </pre>
                  </details>
                )}
              </div>

              {/* Step 2 ボタン */}
              {phase === 'plan_done' && (
                <div className="mt-6 pt-5 border-t border-gray-100">
                  <p className="text-sm text-gray-600 mb-3">
                    企画の内容を確認したら、台本を生成します。
                  </p>
                  <button
                    onClick={handleGenerateScript}
                    className="w-full bg-gradient-to-r from-blue-600 to-purple-600 hover:from-blue-700 hover:to-purple-700 text-white py-3 rounded-xl text-sm font-bold shadow-md transition-all"
                  >
                    📝 Step 2: 台本を生成する (~20-30秒)
                  </button>
                </div>
              )}
            </section>
          )}

          {/* ── Step 2 ローディング ── */}
          {phase === 'script_loading' && (
            <div className="bg-white rounded-2xl border border-blue-200 shadow-sm p-8 text-center space-y-4">
              <div className="flex justify-center">
                <div className="w-12 h-12 border-4 border-blue-500 border-t-transparent rounded-full animate-spin" />
              </div>
              <div>
                <p className="font-semibold text-gray-800">📝 台本を生成中...</p>
                <p className="text-sm text-gray-500 mt-1">
                  キャラクターの口調で台本を書いています
                </p>
              </div>
              <p className="text-xs text-gray-400">通常20〜30秒かかります（GPT-4o使用時）</p>
            </div>
          )}

          {/* ── Step 2 完了: 台本表示 ── */}
          {phase === 'done' && scriptResult && planResult && (
            <section className="bg-white rounded-2xl border border-gray-100 shadow-sm p-6">
              <div className="flex items-start justify-between mb-2 flex-wrap gap-2">
                <h2 className="text-lg font-bold text-gray-900">
                  📝 台本 <span className="text-green-500 text-base">✓ 完成</span>
                </h2>
                {/* 文字数インジケーター */}
                {(() => {
                  const totalChars = scriptResult.full_script?.length ?? 0
                  const totalSec = planResult.total_duration_seconds
                  const targetChars = Math.floor(totalSec * 6.5)
                  const pct = Math.min(100, Math.round((totalChars / targetChars) * 100))
                  const estMin = (totalChars / 6.5 / 60).toFixed(1)
                  const ok = pct >= 80
                  return (
                    <div className={`text-xs px-3 py-1.5 rounded-full font-medium flex items-center gap-1.5 ${
                      ok ? 'bg-green-100 text-green-700' : 'bg-amber-100 text-amber-700'
                    }`}>
                      <span>{ok ? '✅' : '⚠️'}</span>
                      <span>{totalChars.toLocaleString()}文字</span>
                      <span className="opacity-60">|</span>
                      <span>読み上げ約{estMin}分</span>
                      <span className="opacity-60">|</span>
                      <span>目標対比 {pct}%</span>
                    </div>
                  )
                })()}
              </div>
              <p className="text-xs text-gray-400 mb-4">
                各セクションをクリックすると詳細を確認できます
              </p>

              {/* 冒頭フック強調表示 */}
              {scriptResult.hook_text && (
                <div className="bg-gradient-to-r from-pink-50 to-purple-50 border border-pink-200 rounded-xl p-4 mb-4">
                  <p className="text-xs font-medium text-pink-600 mb-2">⚡ 冒頭フック（最初の15秒）</p>
                  <p className="text-sm text-gray-800 leading-relaxed">{scriptResult.hook_text}</p>
                </div>
              )}

              {/* セクション一覧 */}
              <div className="space-y-2">
                {scriptResult.sections.map((sec, i) => {
                  const colorClass = SECTION_COLOR[sec.section_type] || SECTION_COLOR.custom
                  const isExpanded = expandedSections.has(i)
                  return (
                    <div
                      key={i}
                      className={`border rounded-xl overflow-hidden ${colorClass}`}
                    >
                      <button
                        onClick={() => toggleSection(i)}
                        className="w-full flex items-center gap-3 px-4 py-3 text-left hover:opacity-80 transition-opacity"
                      >
                        <span className="text-lg">{EXPRESSION_EMOJI[sec.expression] || '😐'}</span>
                        <div className="flex-1 min-w-0">
                          <div className="flex items-center gap-2">
                            <span className="text-xs font-bold uppercase tracking-wide opacity-70">
                              {SECTION_LABEL[sec.section_type] || sec.section_type}
                            </span>
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
                            <p className="text-sm leading-relaxed bg-white bg-opacity-60 rounded-lg p-3 text-gray-800">
                              {sec.narration}
                            </p>
                          </div>
                          {sec.subtitle && (
                            <div>
                              <p className="text-xs font-medium opacity-70 mb-1">💬 字幕テキスト</p>
                              <p className="text-xs bg-white bg-opacity-60 rounded p-2 text-gray-700 italic">
                                {sec.subtitle}
                              </p>
                            </div>
                          )}
                          {sec.direction && (
                            <div>
                              <p className="text-xs font-medium opacity-70 mb-1">🎬 演出指示</p>
                              <p className="text-xs bg-white bg-opacity-60 rounded p-2 text-gray-600">
                                {sec.direction}
                              </p>
                            </div>
                          )}
                        </div>
                      )}
                    </div>
                  )
                })}
              </div>

              {/* 全文表示 */}
              {scriptResult.full_script && (
                <details className="mt-4">
                  <summary className="text-xs text-gray-500 cursor-pointer hover:text-gray-700">
                    📄 台本全文テキスト（クリックで展開・コピー用）
                  </summary>
                  <textarea
                    readOnly
                    value={scriptResult.full_script}
                    rows={12}
                    className="mt-2 w-full text-xs text-gray-700 bg-gray-50 border border-gray-200 rounded-lg p-3 font-mono leading-relaxed outline-none resize-y"
                  />
                </details>
              )}

              {/* 再生成・次ステップ */}
              <div className="mt-6 pt-5 border-t border-gray-100 space-y-4">
                <button
                  onClick={handleReset}
                  className="w-full text-sm text-purple-600 hover:text-purple-700 border border-purple-200 hover:border-purple-300 py-2.5 rounded-xl transition-colors"
                >
                  ↩ 設定を変えて新規生成
                </button>

                {/* 次のステップガイド */}
                <div className="bg-gradient-to-r from-purple-50 to-pink-50 rounded-2xl border border-purple-100 p-5">
                  <h3 className="font-semibold text-purple-800 mb-3">🚀 次のステップ</h3>
                  <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
                    {[
                      { step: '①', label: '台本を確認・編集', icon: '📝', desc: '上の台本を読んで内容を確認' },
                      { step: '②', label: '音声生成（準備中）', icon: '🎤', desc: 'キャラクターの声でナレーション生成' },
                      { step: '③', label: '動画レンダリング（準備中）', icon: '🎬', desc: 'BGM・字幕・素材を合成して動画完成' },
                    ].map(item => (
                      <div key={item.step} className="bg-white rounded-xl p-3 text-center">
                        <div className="text-2xl mb-1">{item.icon}</div>
                        <p className="text-xs font-bold text-purple-700">{item.step} {item.label}</p>
                        <p className="text-xs text-gray-500 mt-1">{item.desc}</p>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            </section>
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
              <div
                key={plan.id}
                className="bg-white rounded-xl border border-gray-100 shadow-sm p-4 flex items-center justify-between gap-4"
              >
                <div className="flex-1 min-w-0">
                  <p className="font-semibold text-gray-800 truncate">{plan.title}</p>
                  <div className="flex items-center gap-3 mt-1">
                    <span className="text-xs text-gray-400">
                      {plan.created_at ? new Date(plan.created_at).toLocaleDateString('ja-JP') : ''}
                    </span>
                    <span className="text-xs text-gray-400">
                      {fmtSec(plan.total_duration_seconds)}
                    </span>
                    <span className={`text-xs px-2 py-0.5 rounded-full ${
                      plan.has_script ? 'bg-green-100 text-green-700' : 'bg-gray-100 text-gray-600'
                    }`}>
                      {plan.has_script ? '台本あり' : '台本なし'}
                    </span>
                  </div>
                </div>
                <button
                  onClick={() => handleLoadPlan(plan.id)}
                  className="shrink-0 bg-purple-50 hover:bg-purple-100 text-purple-700 text-sm px-4 py-2 rounded-lg transition-colors"
                >
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
