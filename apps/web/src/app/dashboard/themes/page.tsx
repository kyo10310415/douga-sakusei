'use client'
import { useState, useEffect } from 'react'
import { themeApi } from '@/lib/api'

const PURPOSE_OPTIONS = [
  { value: 'subscriber_growth', label: '登録者増加' },
  { value: 'view_growth', label: '再生数増加' },
  { value: 'product_funnel', label: '商品導線' },
  { value: 'education', label: '教育' },
  { value: 'fan_building', label: 'ファン化' },
]

export default function ThemesPage() {
  const [themes, setThemes] = useState<any[]>([])
  const [loading, setLoading] = useState(true)
  const [showForm, setShowForm] = useState(false)
  const [editingId, setEditingId] = useState<string | null>(null)
  const [form, setForm] = useState({
    name: 'デフォルト設定',
    main_channel_theme: '',
    target_genres: [] as string[],
    excluded_genres: [] as string[],
    target_audience: '',
    purposes: [] as string[],
    default_duration_seconds: 600,
    structure_hook_seconds: 15,
    structure_problem_seconds: 60,
    structure_main_seconds: 420,
    structure_example_seconds: 60,
    structure_summary_seconds: 30,
    structure_cta_seconds: 15,
    thumbnail_policy: '',
    title_policy: '',
    description_template: '',
    pinned_comment_template: '',
    is_default: false,
  })

  const [genreInput, setGenreInput] = useState('')
  const [excludedGenreInput, setExcludedGenreInput] = useState('')

  useEffect(() => { fetchThemes() }, [])

  const fetchThemes = async () => {
    try {
      const res = await themeApi.list()
      setThemes(res.data)
    } catch (err) {
      console.error(err)
    } finally {
      setLoading(false)
    }
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    try {
      if (editingId) {
        await themeApi.update(editingId, form)
        alert('テーマ設定を更新しました')
      } else {
        await themeApi.create(form)
        alert('テーマ設定を作成しました')
      }
      setShowForm(false)
      setEditingId(null)
      fetchThemes()
    } catch (err: any) {
      alert(err.response?.data?.detail || 'エラーが発生しました')
    }
  }

  const addGenre = (type: 'target' | 'excluded') => {
    if (type === 'target' && genreInput.trim()) {
      setForm({ ...form, target_genres: [...form.target_genres, genreInput.trim()] })
      setGenreInput('')
    } else if (type === 'excluded' && excludedGenreInput.trim()) {
      setForm({ ...form, excluded_genres: [...form.excluded_genres, excludedGenreInput.trim()] })
      setExcludedGenreInput('')
    }
  }

  const togglePurpose = (purpose: string) => {
    setForm({
      ...form,
      purposes: form.purposes.includes(purpose)
        ? form.purposes.filter(p => p !== purpose)
        : [...form.purposes, purpose],
    })
  }

  if (loading) return <div className="p-8 text-gray-400">読み込み中...</div>

  return (
    <div className="p-8">
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold text-gray-900">🎯 動画テーマ設定</h1>
        <button
          onClick={() => { setShowForm(true); setEditingId(null) }}
          className="bg-green-600 hover:bg-green-700 text-white px-4 py-2 rounded-lg text-sm font-medium"
        >
          ＋ 新規作成
        </button>
      </div>

      {themes.length === 0 ? (
        <div className="text-center py-16 text-gray-400">
          <div className="text-5xl mb-4">🎯</div>
          <p>テーマ設定がありません</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {themes.map(theme => (
            <div key={theme.id} className="bg-white rounded-xl p-6 shadow-sm border border-gray-100">
              <div className="flex items-center justify-between mb-3">
                <h3 className="font-bold text-gray-900">{theme.name}</h3>
                {theme.is_default && (
                  <span className="bg-green-100 text-green-700 text-xs px-2 py-0.5 rounded-full">デフォルト</span>
                )}
              </div>
              <div className="space-y-2 text-sm text-gray-600">
                {theme.main_channel_theme && <p>テーマ: {theme.main_channel_theme}</p>}
                {theme.target_audience && <p>ターゲット: {theme.target_audience}</p>}
                <p>動画尺: {Math.floor(theme.default_duration_seconds / 60)}分</p>
                {theme.purposes?.length > 0 && (
                  <div className="flex flex-wrap gap-1">
                    {theme.purposes.map((p: string) => (
                      <span key={p} className="bg-blue-50 text-blue-700 text-xs px-2 py-0.5 rounded">
                        {PURPOSE_OPTIONS.find(opt => opt.value === p)?.label || p}
                      </span>
                    ))}
                  </div>
                )}
              </div>
              <button
                onClick={() => {
                  setForm({
                    name: theme.name || '',
                    main_channel_theme: theme.main_channel_theme || '',
                    target_genres: theme.target_genres || [],
                    excluded_genres: theme.excluded_genres || [],
                    target_audience: theme.target_audience || '',
                    purposes: theme.purposes || [],
                    default_duration_seconds: theme.default_duration_seconds || 600,
                    structure_hook_seconds: theme.structure_hook_seconds || 15,
                    structure_problem_seconds: theme.structure_problem_seconds || 60,
                    structure_main_seconds: theme.structure_main_seconds || 420,
                    structure_example_seconds: theme.structure_example_seconds || 60,
                    structure_summary_seconds: theme.structure_summary_seconds || 30,
                    structure_cta_seconds: theme.structure_cta_seconds || 15,
                    thumbnail_policy: theme.thumbnail_policy || '',
                    title_policy: theme.title_policy || '',
                    description_template: theme.description_template || '',
                    pinned_comment_template: theme.pinned_comment_template || '',
                    is_default: theme.is_default || false,
                  })
                  setEditingId(theme.id)
                  setShowForm(true)
                }}
                className="mt-4 w-full bg-gray-100 hover:bg-gray-200 text-gray-700 py-2 rounded-lg text-sm"
              >
                編集
              </button>
            </div>
          ))}
        </div>
      )}

      {/* フォームモーダル */}
      {showForm && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-2xl w-full max-w-2xl max-h-[90vh] overflow-y-auto">
            <div className="p-6 border-b border-gray-100">
              <div className="flex items-center justify-between">
                <h2 className="text-lg font-bold text-gray-900">
                  {editingId ? 'テーマ設定編集' : 'テーマ設定作成'}
                </h2>
                <button onClick={() => setShowForm(false)} className="text-gray-400 hover:text-gray-700 text-xl">×</button>
              </div>
            </div>

            <form onSubmit={handleSubmit} className="p-6 space-y-5">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">設定名</label>
                <input
                  value={form.name}
                  onChange={e => setForm({ ...form, name: e.target.value })}
                  className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-green-500"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">メインチャンネルテーマ</label>
                <textarea
                  value={form.main_channel_theme}
                  onChange={e => setForm({ ...form, main_channel_theme: e.target.value })}
                  rows={2}
                  className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-green-500"
                  placeholder="例: IT・AI・テクノロジー系の情報を初心者向けに解説するチャンネル"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">ターゲット視聴者</label>
                <textarea
                  value={form.target_audience}
                  onChange={e => setForm({ ...form, target_audience: e.target.value })}
                  rows={2}
                  className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-green-500"
                  placeholder="例: 20-35歳の社会人、ITに興味があるが専門知識がない人"
                />
              </div>

              {/* 動画の目的 */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">動画の目的（複数選択可）</label>
                <div className="flex flex-wrap gap-2">
                  {PURPOSE_OPTIONS.map(opt => (
                    <button
                      key={opt.value}
                      type="button"
                      onClick={() => togglePurpose(opt.value)}
                      className={`px-3 py-1.5 rounded-full text-sm font-medium transition-colors ${
                        form.purposes.includes(opt.value)
                          ? 'bg-green-600 text-white'
                          : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                      }`}
                    >
                      {opt.label}
                    </button>
                  ))}
                </div>
              </div>

              {/* 動画尺 */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  デフォルト動画尺: {Math.floor(form.default_duration_seconds / 60)}分
                </label>
                <input
                  type="range" min="300" max="1800" step="60"
                  value={form.default_duration_seconds}
                  onChange={e => setForm({ ...form, default_duration_seconds: parseInt(e.target.value) })}
                  className="w-full"
                />
              </div>

              {/* 動画構成 */}
              <div className="border border-gray-200 rounded-xl p-4">
                <h3 className="font-medium text-gray-700 mb-3">📋 動画構成テンプレート (秒)</h3>
                <div className="grid grid-cols-3 gap-3 text-sm">
                  {[
                    { key: 'structure_hook_seconds', label: '冒頭フック' },
                    { key: 'structure_problem_seconds', label: '問題提起' },
                    { key: 'structure_main_seconds', label: '本編' },
                    { key: 'structure_example_seconds', label: '具体例' },
                    { key: 'structure_summary_seconds', label: 'まとめ' },
                    { key: 'structure_cta_seconds', label: 'CTA' },
                  ].map(item => (
                    <div key={item.key}>
                      <label className="block text-xs text-gray-500 mb-1">{item.label}</label>
                      <input
                        type="number" min="0"
                        value={(form as any)[item.key]}
                        onChange={e => setForm({ ...form, [item.key]: parseInt(e.target.value) })}
                        className="w-full border border-gray-300 rounded px-2 py-1 text-sm outline-none"
                      />
                    </div>
                  ))}
                </div>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">サムネイル方針</label>
                <textarea
                  value={form.thumbnail_policy}
                  onChange={e => setForm({ ...form, thumbnail_policy: e.target.value })}
                  rows={2}
                  className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-green-500"
                  placeholder="例: 顔アップ + 驚き表情 + 数字を大きく表示"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">タイトル方針</label>
                <textarea
                  value={form.title_policy}
                  onChange={e => setForm({ ...form, title_policy: e.target.value })}
                  rows={2}
                  className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-green-500"
                  placeholder="例: 「数字＋簡単」「初心者向け」を含める。30字以内。"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">概要欄テンプレート</label>
                <textarea
                  value={form.description_template}
                  onChange={e => setForm({ ...form, description_template: e.target.value })}
                  rows={4}
                  className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-green-500"
                  placeholder="📌 今回の内容&#10;{content}&#10;&#10;チャンネル登録はこちら：{channel_url}"
                />
              </div>

              <div className="flex items-center gap-2">
                <input
                  type="checkbox"
                  id="theme_default"
                  checked={form.is_default}
                  onChange={e => setForm({ ...form, is_default: e.target.checked })}
                  className="rounded"
                />
                <label htmlFor="theme_default" className="text-sm text-gray-700">デフォルト設定として使用</label>
              </div>

              <div className="flex gap-3 pt-4 border-t border-gray-100">
                <button
                  type="button"
                  onClick={() => setShowForm(false)}
                  className="flex-1 border border-gray-300 text-gray-700 py-2.5 rounded-lg text-sm font-medium"
                >
                  キャンセル
                </button>
                <button
                  type="submit"
                  className="flex-1 bg-green-600 hover:bg-green-700 text-white py-2.5 rounded-lg text-sm font-medium"
                >
                  {editingId ? '更新する' : '作成する'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  )
}
