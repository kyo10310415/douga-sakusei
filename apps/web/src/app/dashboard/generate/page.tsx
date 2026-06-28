'use client'
import { useState, useEffect } from 'react'
import { characterApi, themeApi, videoJobApi } from '@/lib/api'

// ─────────────────────────────────────────
// 型定義
// ─────────────────────────────────────────
type Section = {
  order_index: number
  section_type: string
  title: string
  duration_seconds: number
  narration: string
  subtitle: string
  direction: string
  expression: string
}

type GenerateResult = {
  ai_mode: 'mock' | 'openai'
  video_plan: {
    id: string
    title: string
    goal: string
    target_audience: string
    total_duration_seconds: number
    structure: any[]
    youtube_title_candidates: string[]
    youtube_description: string
    youtube_tags: string[]
    cta: string
  }
  script: {
    id: string
    hook_text: string
    full_script: string
    sections: Section[]
  }
  character: { id: string; name: string }
  theme: { id: string; name: string }
}

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

  const [loading, setLoading] = useState(true)
  const [generating, setGenerating] = useState(false)
  const [genStep, setGenStep] = useState<'idle' | 'plan' | 'script' | 'done'>('idle')
  const [result, setResult] = useState<GenerateResult | null>(null)
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
      // デフォルト選択
      const defChar = c.data.find((x: any) => x.is_default) || c.data[0]
      const defTheme = t.data.find((x: any) => x.is_default) || t.data[0]
      if (defChar) setSelectedChar(defChar.id)
      if (defTheme) setSelectedTheme(defTheme.id)
    }).catch(console.error).finally(() => setLoading(false))
  }, [])

  const handleGenerate = async () => {
    if (!selectedChar || !selectedTheme) {
      setError('キャラクターとテーマを選択してください')
      return
    }
    setError('')
    setResult(null)
    setGenerating(true)
    setGenStep('plan')

    // ステップ表示の疑似進行（実際はサーバー側で一括処理）
    const stepTimer = setTimeout(() => setGenStep('script'), 3000)

    try {
      const res = await videoJobApi.generate({
        character_id: selectedChar,
        theme_id: selectedTheme,
        custom_topic: customTopic || undefined,
      })
      clearTimeout(stepTimer)
      setResult(res.data)
      setGenStep('done')
      setExpandedSections(new Set([0]))
      // 履歴を先頭に追加
      setPlans(prev => [
        {
          id: res.data.video_plan.id,
          title: res.data.video_plan.title,
          total_duration_seconds: res.data.video_plan.total_duration_seconds,
          status: 'draft',
          created_at: new Date().toISOString(),
          has_script: true,
        },
        ...prev,
      ])
    } catch (err: any) {
      clearTimeout(stepTimer)
      setError(err.response?.data?.detail || '生成に失敗しました。しばらく経ってから再試行してください。')
      setGenStep('idle')
    } finally {
      setGenerating(false)
    }
  }

  const toggleSection = (idx: number) => {
    setExpandedSections(prev => {
      const next = new Set(prev)
      next.has(idx) ? next.delete(idx) : next.add(idx)
      return next
    })
  }

  const handleLoadPlan = async (planId: string) => {
    try {
      const res = await videoJobApi.getPlan(planId)
      setResult({
        ai_mode: 'openai',
        video_plan: res.data,
        script: res.data.script,
        character: { id: '', name: '' },
        theme: { id: '', name: '' },
      })
      setGenStep('done')
      setActiveTab('new')
      setExpandedSections(new Set([0]))
    } catch {
      alert('企画の読み込みに失敗しました')
    }
  }

  if (loading) return <div className="p-8 text-gray-400">読み込み中...</div>

  return (
    <div className="p-8 max-w-5xl mx-auto">
      {/* ヘッダー */}
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-gray-900">🎬 動画生成</h1>
        <p className="text-sm text-gray-500 mt-1">
          キャラクターとテーマを選ぶだけで、AIが企画・台本を自動作成します
        </p>
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

          {/* ── 設定カード ── */}
          {genStep === 'idle' || genStep === 'done' ? (
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

              {/* エラー */}
              {error && (
                <div className="bg-red-50 text-red-700 text-sm px-4 py-3 rounded-lg border border-red-200">
                  ⚠️ {error}
                </div>
              )}

              {/* 生成ボタン */}
              <button
                onClick={handleGenerate}
                disabled={generating || !selectedChar || !selectedTheme}
                className="w-full bg-gradient-to-r from-purple-600 to-pink-500 hover:from-purple-700 hover:to-pink-600 disabled:opacity-50 text-white py-3 rounded-xl text-sm font-bold shadow-md transition-all"
              >
                ✨ 企画・台本を生成する
              </button>
            </div>
          ) : null}

          {/* ── 生成中インジケーター ── */}
          {generating && (
            <div className="bg-white rounded-2xl border border-purple-200 shadow-sm p-8 text-center space-y-4">
              <div className="flex justify-center">
                <div className="w-12 h-12 border-4 border-purple-500 border-t-transparent rounded-full animate-spin" />
              </div>
              <div>
                <p className="font-semibold text-gray-800">
                  {genStep === 'plan' ? '🧠 動画企画を生成中...' : '📝 台本を生成中...'}
                </p>
                <p className="text-sm text-gray-500 mt-1">
                  {genStep === 'plan'
                    ? 'キャラクターとテーマを分析して、最適な企画を考えています'
                    : 'キャラクターの口調で台本を書いています...'}
                </p>
              </div>
              {/* ステッププログレス */}
              <div className="flex items-center justify-center gap-2 pt-2">
                {(['plan', 'script', 'done'] as const).map((step, i) => (
                  <div key={step} className="flex items-center gap-2">
                    <div className={`w-6 h-6 rounded-full text-xs flex items-center justify-center font-bold ${
                      genStep === step
                        ? 'bg-purple-600 text-white animate-pulse'
                        : i < ['plan', 'script', 'done'].indexOf(genStep)
                          ? 'bg-green-500 text-white'
                          : 'bg-gray-200 text-gray-500'
                    }`}>
                      {i + 1}
                    </div>
                    {i < 2 && <div className="w-6 h-0.5 bg-gray-200" />}
                  </div>
                ))}
              </div>
              <p className="text-xs text-gray-400">
                OpenAI GPT-4o 使用時は20〜40秒かかる場合があります
              </p>
            </div>
          )}

          {/* ── 生成結果 ── */}
          {result && genStep === 'done' && (
            <div className="space-y-6">

              {/* AIモードバッジ + 再生成ボタン */}
              <div className="flex items-center justify-between">
                <span className={`text-xs px-3 py-1 rounded-full font-medium ${
                  result.ai_mode === 'openai'
                    ? 'bg-green-100 text-green-700'
                    : 'bg-amber-100 text-amber-700'
                }`}>
                  {result.ai_mode === 'openai' ? '✅ OpenAI GPT-4o で生成' : '🔧 モックデータ（OpenAI キー未設定）'}
                </span>
                <button
                  onClick={() => { setResult(null); setGenStep('idle') }}
                  className="text-sm text-purple-600 hover:underline"
                >
                  ↩ 設定を変えて再生成
                </button>
              </div>

              {/* 企画カード */}
              <section className="bg-white rounded-2xl border border-gray-100 shadow-sm p-6">
                <h2 className="text-lg font-bold text-gray-900 mb-4">📋 動画企画</h2>
                <div className="space-y-3">
                  <div>
                    <p className="text-xs text-gray-500 mb-1">タイトル（AI提案）</p>
                    <p className="text-xl font-bold text-purple-700">{result.video_plan.title}</p>
                  </div>
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 pt-2">
                    <div className="bg-gray-50 rounded-xl p-3">
                      <p className="text-xs text-gray-500 mb-1">🎯 動画の目的</p>
                      <p className="text-sm text-gray-800">{result.video_plan.goal || '—'}</p>
                    </div>
                    <div className="bg-gray-50 rounded-xl p-3">
                      <p className="text-xs text-gray-500 mb-1">👥 ターゲット視聴者</p>
                      <p className="text-sm text-gray-800">{result.video_plan.target_audience || '—'}</p>
                    </div>
                    <div className="bg-gray-50 rounded-xl p-3">
                      <p className="text-xs text-gray-500 mb-1">⏱ 動画尺</p>
                      <p className="text-sm text-gray-800 font-medium">
                        {fmtSec(result.video_plan.total_duration_seconds)}
                      </p>
                    </div>
                    <div className="bg-gray-50 rounded-xl p-3">
                      <p className="text-xs text-gray-500 mb-1">📣 CTA</p>
                      <p className="text-sm text-gray-800">{result.video_plan.cta || '—'}</p>
                    </div>
                  </div>

                  {/* タイトル候補 */}
                  {result.video_plan.youtube_title_candidates?.length > 0 && (
                    <div className="pt-2">
                      <p className="text-xs text-gray-500 mb-2">🏷 YouTubeタイトル候補</p>
                      <div className="space-y-1">
                        {result.video_plan.youtube_title_candidates.map((title, i) => (
                          <div key={i} className="flex items-start gap-2">
                            <span className="text-xs text-gray-400 mt-0.5 w-4 shrink-0">{i + 1}.</span>
                            <p className="text-sm text-gray-700">{title}</p>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* タグ */}
                  {result.video_plan.youtube_tags?.length > 0 && (
                    <div className="pt-1">
                      <p className="text-xs text-gray-500 mb-2">🔖 タグ</p>
                      <div className="flex flex-wrap gap-1">
                        {result.video_plan.youtube_tags.map((tag, i) => (
                          <span key={i} className="bg-blue-50 text-blue-700 text-xs px-2 py-0.5 rounded-full">
                            #{tag}
                          </span>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* 概要欄 */}
                  {result.video_plan.youtube_description && (
                    <details className="pt-1">
                      <summary className="text-xs text-gray-500 cursor-pointer hover:text-gray-700">
                        📄 概要欄テキスト（クリックで展開）
                      </summary>
                      <pre className="mt-2 text-xs text-gray-600 bg-gray-50 p-3 rounded-lg whitespace-pre-wrap leading-relaxed">
                        {result.video_plan.youtube_description}
                      </pre>
                    </details>
                  )}
                </div>
              </section>

              {/* 台本カード */}
              <section className="bg-white rounded-2xl border border-gray-100 shadow-sm p-6">
                <div className="flex items-start justify-between mb-2 flex-wrap gap-2">
                  <h2 className="text-lg font-bold text-gray-900">📝 台本</h2>
                  {/* 文字数インジケーター */}
                  {(() => {
                    const totalChars = result.script.full_script?.length ?? 0
                    const totalSec = result.video_plan.total_duration_seconds
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
                {result.script.hook_text && (
                  <div className="bg-gradient-to-r from-pink-50 to-purple-50 border border-pink-200 rounded-xl p-4 mb-4">
                    <p className="text-xs font-medium text-pink-600 mb-2">⚡ 冒頭フック（最初の15秒）</p>
                    <p className="text-sm text-gray-800 leading-relaxed">{result.script.hook_text}</p>
                  </div>
                )}

                {/* セクション一覧 */}
                <div className="space-y-2">
                  {result.script.sections.map((sec, i) => {
                    const colorClass = SECTION_COLOR[sec.section_type] || SECTION_COLOR.custom
                    const isExpanded = expandedSections.has(i)
                    return (
                      <div
                        key={i}
                        className={`border rounded-xl overflow-hidden ${colorClass}`}
                      >
                        {/* セクションヘッダー */}
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

                        {/* セクション詳細（展開時） */}
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
                {result.script.full_script && (
                  <details className="mt-4">
                    <summary className="text-xs text-gray-500 cursor-pointer hover:text-gray-700">
                      📄 台本全文テキスト（クリックで展開・コピー用）
                    </summary>
                    <textarea
                      readOnly
                      value={result.script.full_script}
                      rows={12}
                      className="mt-2 w-full text-xs text-gray-700 bg-gray-50 border border-gray-200 rounded-lg p-3 font-mono leading-relaxed outline-none resize-y"
                    />
                  </details>
                )}
              </section>

              {/* 次のステップガイド */}
              <div className="bg-gradient-to-r from-purple-50 to-pink-50 rounded-2xl border border-purple-100 p-5">
                <h3 className="font-semibold text-purple-800 mb-3">🚀 次のステップ</h3>
                <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
                  {[
                    { step: '①', label: '台本を確認・編集', icon: '📝', desc: '上の台本を読んで内容を確認' },
                    { step: '②', label: '音声生成（準備中）', icon: '🎤', desc: 'キャラクターの声でナレーションを生成' },
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
