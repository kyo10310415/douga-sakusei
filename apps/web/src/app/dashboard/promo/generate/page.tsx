'use client'
import { useState, useEffect } from 'react'
import { useRouter } from 'next/navigation'
import { promoApi, youtubeApi } from '@/lib/api'

const PLATFORMS = [
  { value: 'x', label: 'X（Twitter）', icon: '𝕏', maxChars: 280 },
  { value: 'instagram', label: 'Instagram', icon: '📷', maxChars: 2200 },
  { value: 'tiktok', label: 'TikTok', icon: '🎵', maxChars: 2200 },
  { value: 'youtube_shorts', label: 'YouTube Shorts', icon: '▶️', maxChars: 5000 },
]

const SEGMENTS = [
  { value: 'beginner', label: 'これからVTuberを始める人' },
  { value: '0_1000', label: '登録者0〜1000人' },
  { value: '1000_10000', label: '登録者1000〜1万人' },
]

const GOALS = [
  { value: 'awareness', label: '認知拡大' },
  { value: 'consult', label: '無料相談誘導' },
  { value: 'line', label: 'LINE登録誘導' },
  { value: 'document', label: '資料請求誘導' },
  { value: 'achievement', label: '実績紹介' },
  { value: 'knowhow', label: 'ノウハウ提供' },
]

const TONES = [
  { value: 'gentle', label: '親しみやすい・寄り添い' },
  { value: 'professional', label: 'プロフェッショナル' },
  { value: 'provocative', label: '問題提起・刺さる' },
  { value: 'beginner', label: '初心者向け・やさしい' },
  { value: 'business', label: 'ビジネスライク' },
]

const THEME_EXAMPLES = [
  '「VTuberを始めたいけど何から始めればいい？」という悩みに答える',
  'YouTube登録者が増えない本当の理由3つ',
  'AI活用でVTuber活動の作業時間を半分にする方法',
  '無料相談で改善できた実際の事例紹介',
  '月10時間の活動でも伸びるVTuberの共通点',
  'VTuberコンサルで解決できる悩みランキング TOP5',
]

export default function PromoGeneratePage() {
  const router = useRouter()
  const [theme, setTheme] = useState('')
  const [platforms, setPlatforms] = useState<string[]>(['x'])
  const [segment, setSegment] = useState('beginner')
  const [goal, setGoal] = useState('awareness')
  const [tone, setTone] = useState('gentle')
  const [cta, setCta] = useState('')
  const [count, setCount] = useState(1)
  const [weeklyMetricsId, setWeeklyMetricsId] = useState('')
  const [weeklyMetricsList, setWeeklyMetricsList] = useState<any[]>([])
  const [generating, setGenerating] = useState(false)
  const [result, setResult] = useState<any>(null)
  const [error, setError] = useState('')
  const [templates, setTemplates] = useState<any[]>([])

  useEffect(() => {
    // テーマテンプレート取得
    promoApi.listTemplates({ type: 'post_theme' })
      .then(r => setTemplates(r.data.templates || []))
      .catch(() => {})
    // YouTube weekly metrics 一覧取得
    youtubeApi.getWeeklyMetrics(8)
      .then(r => setWeeklyMetricsList(r.data.metrics || []))
      .catch(() => {})
  }, [])

  const togglePlatform = (v: string) => {
    setPlatforms(prev =>
      prev.includes(v) ? prev.filter(p => p !== v) : [...prev, v]
    )
  }

  const handleGenerate = async () => {
    if (!theme.trim()) { setError('テーマを入力してください'); return }
    if (platforms.length === 0) { setError('媒体を1つ以上選択してください'); return }
    setError('')
    setGenerating(true)
    setResult(null)
    try {
      const res = await promoApi.generate({
        theme,
        platforms,
        target_segment: segment,
        goal,
        tone,
        cta,
        count,
        weekly_metrics_id: weeklyMetricsId || undefined,
      })
      setResult(res.data)
    } catch (e: any) {
      setError(e.response?.data?.detail || '生成に失敗しました')
    } finally {
      setGenerating(false)
    }
  }

  return (
    <div className="p-6 max-w-4xl mx-auto">
      <div className="flex items-center gap-3 mb-6">
        <button onClick={() => router.back()} className="text-gray-400 hover:text-gray-600">←</button>
        <div>
          <h1 className="text-2xl font-bold text-gray-900">✨ AI投稿生成</h1>
          <p className="text-gray-500 text-sm mt-0.5">テーマと媒体を選んでAIが宣伝投稿を自動生成します</p>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        {/* 左：フォーム */}
        <div className="md:col-span-2 space-y-5">

          {/* テーマ入力 */}
          <div className="bg-white rounded-xl p-5 shadow-sm border">
            <label className="block text-sm font-semibold text-gray-700 mb-2">
              📌 投稿テーマ <span className="text-red-500">*</span>
            </label>
            <textarea
              value={theme}
              onChange={e => setTheme(e.target.value)}
              placeholder="例：VTuberを始めたいけど何から始めればいい？という悩みに答える"
              className="w-full border rounded-lg p-3 text-sm resize-none focus:outline-none focus:ring-2 focus:ring-pink-300"
              rows={3}
            />
            {/* テンプレート提案 */}
            {templates.length > 0 && (
              <div className="mt-2">
                <p className="text-xs text-gray-500 mb-1">テンプレートから選ぶ：</p>
                <div className="flex flex-wrap gap-1">
                  {templates.slice(0, 6).map((t: any) => (
                    <button
                      key={t.id}
                      onClick={() => setTheme(t.name)}
                      className="text-xs bg-pink-50 hover:bg-pink-100 text-pink-700 px-2 py-1 rounded border border-pink-200"
                    >
                      {t.name}
                    </button>
                  ))}
                </div>
              </div>
            )}
            {templates.length === 0 && (
              <div className="mt-2">
                <p className="text-xs text-gray-500 mb-1">例から選ぶ：</p>
                <div className="flex flex-wrap gap-1">
                  {THEME_EXAMPLES.map(ex => (
                    <button
                      key={ex}
                      onClick={() => setTheme(ex)}
                      className="text-xs bg-gray-50 hover:bg-gray-100 text-gray-600 px-2 py-1 rounded border"
                    >
                      {ex.slice(0, 30)}…
                    </button>
                  ))}
                </div>
              </div>
            )}
          </div>

          {/* 媒体選択 */}
          <div className="bg-white rounded-xl p-5 shadow-sm border">
            <label className="block text-sm font-semibold text-gray-700 mb-3">
              📱 投稿媒体 <span className="text-red-500">*</span>
            </label>
            <div className="grid grid-cols-2 gap-2">
              {PLATFORMS.map(p => (
                <button
                  key={p.value}
                  onClick={() => togglePlatform(p.value)}
                  className={`flex items-center gap-2 p-3 rounded-lg border text-sm font-medium transition-colors ${
                    platforms.includes(p.value)
                      ? 'bg-pink-600 text-white border-pink-600'
                      : 'bg-white text-gray-600 border-gray-200 hover:border-pink-300'
                  }`}
                >
                  <span className="text-lg">{p.icon}</span>
                  <span>{p.label}</span>
                </button>
              ))}
            </div>
          </div>

          {/* ターゲット・目的・トーン */}
          <div className="bg-white rounded-xl p-5 shadow-sm border">
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
              <div>
                <label className="block text-sm font-semibold text-gray-700 mb-1">👥 ターゲット層</label>
                <select
                  value={segment}
                  onChange={e => setSegment(e.target.value)}
                  className="w-full border rounded-lg p-2 text-sm focus:outline-none focus:ring-2 focus:ring-pink-300"
                >
                  {SEGMENTS.map(s => <option key={s.value} value={s.value}>{s.label}</option>)}
                </select>
              </div>
              <div>
                <label className="block text-sm font-semibold text-gray-700 mb-1">🎯 投稿目的</label>
                <select
                  value={goal}
                  onChange={e => setGoal(e.target.value)}
                  className="w-full border rounded-lg p-2 text-sm focus:outline-none focus:ring-2 focus:ring-pink-300"
                >
                  {GOALS.map(g => <option key={g.value} value={g.value}>{g.label}</option>)}
                </select>
              </div>
              <div>
                <label className="block text-sm font-semibold text-gray-700 mb-1">🎨 トーン</label>
                <select
                  value={tone}
                  onChange={e => setTone(e.target.value)}
                  className="w-full border rounded-lg p-2 text-sm focus:outline-none focus:ring-2 focus:ring-pink-300"
                >
                  {TONES.map(t => <option key={t.value} value={t.value}>{t.label}</option>)}
                </select>
              </div>
            </div>
          </div>

          {/* CTA + 生成数 + YouTube連携 */}
          <div className="bg-white rounded-xl p-5 shadow-sm border">
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-semibold text-gray-700 mb-1">🔗 CTA（行動喚起）</label>
                <input
                  type="text"
                  value={cta}
                  onChange={e => setCta(e.target.value)}
                  placeholder="例：プロフのリンクから無料相談はこちら"
                  className="w-full border rounded-lg p-2 text-sm focus:outline-none focus:ring-2 focus:ring-pink-300"
                />
              </div>
              <div>
                <label className="block text-sm font-semibold text-gray-700 mb-1">🔢 生成数（媒体ごと）</label>
                <select
                  value={count}
                  onChange={e => setCount(Number(e.target.value))}
                  className="w-full border rounded-lg p-2 text-sm focus:outline-none focus:ring-2 focus:ring-pink-300"
                >
                  {[1, 2, 3].map(n => <option key={n} value={n}>{n}件</option>)}
                </select>
              </div>
            </div>

            {weeklyMetricsList.length > 0 && (
              <div className="mt-4">
                <label className="block text-sm font-semibold text-gray-700 mb-1">
                  📊 YouTube分析データ連携（任意）
                </label>
                <select
                  value={weeklyMetricsId}
                  onChange={e => setWeeklyMetricsId(e.target.value)}
                  className="w-full border rounded-lg p-2 text-sm focus:outline-none focus:ring-2 focus:ring-pink-300"
                >
                  <option value="">連携しない</option>
                  {weeklyMetricsList.map((wm: any) => (
                    <option key={wm.id} value={wm.id}>
                      {wm.week_start ? new Date(wm.week_start).toLocaleDateString('ja-JP') : wm.id.slice(0, 8)} の週次データ
                    </option>
                  ))}
                </select>
                <p className="text-xs text-gray-400 mt-1">
                  選択すると、その週のYouTube実績をAIプロンプトに反映します
                </p>
              </div>
            )}
          </div>

          {error && (
            <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg text-sm">
              ⚠️ {error}
            </div>
          )}

          <button
            onClick={handleGenerate}
            disabled={generating}
            className="w-full bg-pink-600 hover:bg-pink-700 disabled:opacity-50 text-white py-3 rounded-xl font-semibold text-sm flex items-center justify-center gap-2"
          >
            {generating ? (
              <>
                <span className="animate-spin">⏳</span> AIが生成中...
              </>
            ) : (
              <>
                <span>✨</span> {platforms.length}媒体 × {count}件 の投稿を生成する
              </>
            )}
          </button>
        </div>

        {/* 右：説明パネル */}
        <div className="space-y-4">
          <div className="bg-pink-50 border border-pink-100 rounded-xl p-4">
            <h3 className="font-semibold text-pink-800 mb-2 text-sm">💡 生成の流れ</h3>
            <ol className="text-xs text-pink-700 space-y-1 list-decimal list-inside">
              <li>テーマと媒体を設定</li>
              <li>AIが媒体の文字数・特性に合わせて生成</li>
              <li>NG表現チェックが自動実行される</li>
              <li>投稿管理画面で確認・承認</li>
              <li>Xは自動投稿、他媒体はコピーして手動投稿</li>
            </ol>
          </div>

          <div className="bg-yellow-50 border border-yellow-100 rounded-xl p-4">
            <h3 className="font-semibold text-yellow-800 mb-2 text-sm">⚠️ 禁止表現について</h3>
            <p className="text-xs text-yellow-700">
              「必ず収益化できます」「絶対に伸びます」など景品表示法に触れる恐れのある表現は自動検出・代替案提示されます。
            </p>
          </div>

          <div className="bg-blue-50 border border-blue-100 rounded-xl p-4">
            <h3 className="font-semibold text-blue-800 mb-2 text-sm">📱 媒体の特徴</h3>
            <ul className="text-xs text-blue-700 space-y-1">
              <li><strong>X:</strong> 280文字・自動投稿対応</li>
              <li><strong>Instagram:</strong> ハッシュタグ重要・手動</li>
              <li><strong>TikTok:</strong> トレンド訴求・手動</li>
              <li><strong>YouTube Shorts:</strong> 動画台本として活用</li>
            </ul>
          </div>
        </div>
      </div>

      {/* 生成結果 */}
      {result && (
        <div className="mt-8">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-lg font-bold text-gray-900">
              🎉 {result.generated}件の投稿を生成しました
            </h2>
            <button
              onClick={() => router.push('/dashboard/promo/posts?status=pending_review')}
              className="bg-pink-600 hover:bg-pink-700 text-white px-4 py-2 rounded-lg text-sm"
            >
              投稿管理で確認する →
            </button>
          </div>
          <div className="space-y-4">
            {result.posts.map((post: any) => (
              <div key={post.id} className="bg-white border rounded-xl p-5 shadow-sm">
                <div className="flex items-center justify-between mb-2">
                  <span className="text-sm font-semibold text-gray-600">
                    {post.platform === 'x' ? '𝕏 X' :
                     post.platform === 'instagram' ? '📷 Instagram' :
                     post.platform === 'tiktok' ? '🎵 TikTok' : '▶️ YouTube Shorts'}
                  </span>
                  <div className="flex items-center gap-2">
                    {post.ng_check_passed === false && (
                      <span className="text-xs bg-red-100 text-red-700 px-2 py-0.5 rounded">
                        ⚠️ NG表現あり
                      </span>
                    )}
                    {post.ng_check_passed === true && (
                      <span className="text-xs bg-green-100 text-green-700 px-2 py-0.5 rounded">
                        ✅ NG表現なし
                      </span>
                    )}
                  </div>
                </div>
                {post.title && (
                  <p className="font-semibold text-gray-800 mb-1">{post.title}</p>
                )}
                <p className="text-sm text-gray-700 whitespace-pre-wrap">
                  {post.body || post.caption}
                </p>
                {post.hashtags?.length > 0 && (
                  <p className="text-xs text-blue-500 mt-2">
                    {post.hashtags.map((h: string) => `#${h}`).join(' ')}
                  </p>
                )}
                <div className="mt-3 flex gap-2">
                  <button
                    onClick={() => {
                      navigator.clipboard.writeText(
                        [post.body || post.caption, post.cta, post.hashtags?.map((h: string) => `#${h}`).join(' ')].filter(Boolean).join('\n')
                      )
                    }}
                    className="text-xs border px-3 py-1.5 rounded hover:bg-gray-50"
                  >
                    📋 コピー
                  </button>
                  <button
                    onClick={() => router.push(`/dashboard/promo/posts/${post.id}`)}
                    className="text-xs bg-pink-600 text-white px-3 py-1.5 rounded hover:bg-pink-700"
                  >
                    詳細・編集 →
                  </button>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
