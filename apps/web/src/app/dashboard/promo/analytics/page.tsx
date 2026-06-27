'use client'
import { useState, useEffect } from 'react'
import Link from 'next/link'
import { promoApi } from '@/lib/api'

const PLATFORM_ICONS: Record<string, string> = {
  x: '𝕏', instagram: '📷', tiktok: '🎵', youtube_shorts: '▶️'
}
const STATUS_COLORS: Record<string, string> = {
  draft: 'bg-gray-100 text-gray-600',
  pending_review: 'bg-yellow-100 text-yellow-700',
  approved: 'bg-blue-100 text-blue-700',
  published: 'bg-green-100 text-green-700',
  rejected: 'bg-red-100 text-red-600',
}
const STATUS_LABELS: Record<string, string> = {
  draft: '下書き', pending_review: 'レビュー待ち', approved: '承認済み',
  scheduled: 'スケジュール', published: '投稿済み', rejected: '差し戻し',
}

export default function PromoAnalyticsPage() {
  const [publishedPosts, setPublishedPosts] = useState<any[]>([])
  const [loading, setLoading] = useState(true)
  const [selectedPost, setSelectedPost] = useState<any>(null)
  const [analytics, setAnalytics] = useState<any>(null)
  const [analyticsLoading, setAnalyticsLoading] = useState(false)
  const [form, setForm] = useState<any>({})
  const [saving, setSaving] = useState(false)
  const [toast, setToast] = useState('')
  const [allPosts, setAllPosts] = useState<any[]>([])
  const [showAll, setShowAll] = useState(false)

  const showToast = (msg: string) => {
    setToast(msg)
    setTimeout(() => setToast(''), 3500)
  }

  useEffect(() => {
    Promise.all([
      promoApi.listPosts({ status: 'published', limit: 50 }),
      promoApi.listPosts({ limit: 50 }),
    ]).then(([pubRes, allRes]) => {
      setPublishedPosts(pubRes.data.posts || [])
      setAllPosts(allRes.data.posts || [])
    }).catch(console.error).finally(() => setLoading(false))
  }, [])

  const handleSelect = async (post: any) => {
    setSelectedPost(post)
    setAnalyticsLoading(true)
    try {
      const res = await promoApi.getAnalytics(post.id)
      const a = res.data.analytics
      setAnalytics(a)
      setForm({
        impressions: a?.impressions ?? '',
        likes: a?.likes ?? '',
        comments: a?.comments ?? '',
        shares: a?.shares ?? '',
        saves: a?.saves ?? '',
        profile_clicks: a?.profile_clicks ?? '',
        url_clicks: a?.url_clicks ?? '',
        leads: a?.leads ?? '',
        conversions: a?.conversions ?? '',
        memo: a?.memo ?? '',
      })
    } catch {
      setAnalytics(null)
      setForm({})
    } finally {
      setAnalyticsLoading(false)
    }
  }

  const handleSave = async () => {
    if (!selectedPost) return
    setSaving(true)
    try {
      const payload: any = { run_ai_analysis: true }
      for (const key of ['impressions', 'likes', 'comments', 'shares', 'saves', 'profile_clicks', 'url_clicks', 'leads', 'conversions']) {
        const v = form[key]
        if (v !== '' && v !== undefined) payload[key] = Number(v)
      }
      if (form.memo) payload.memo = form.memo
      const res = await promoApi.upsertAnalytics(selectedPost.id, payload)
      setAnalytics(res.data.analytics)
      showToast('✅ 保存・AI分析完了')
    } catch (e: any) {
      showToast('⚠️ ' + (e.response?.data?.detail || '保存に失敗しました'))
    } finally {
      setSaving(false)
    }
  }

  // 全投稿の集計
  const totalLeads = allPosts.reduce((sum: number, _p: any) => sum, 0)
  const displayPosts = showAll ? allPosts : publishedPosts

  // KPI計算（publishedPostsのanalyticsから）
  const [kpi, setKpi] = useState({ impressions: 0, likes: 0, leads: 0, conversions: 0 })
  useEffect(() => {
    if (publishedPosts.length === 0) return
    Promise.all(publishedPosts.map(p => promoApi.getAnalytics(p.id).catch(() => null)))
      .then(results => {
        const totals = { impressions: 0, likes: 0, leads: 0, conversions: 0 }
        results.forEach(r => {
          if (!r?.data?.analytics) return
          const a = r.data.analytics
          totals.impressions += a.impressions || 0
          totals.likes += a.likes || 0
          totals.leads += a.leads || 0
          totals.conversions += a.conversions || 0
        })
        setKpi(totals)
      })
  }, [publishedPosts])

  return (
    <div className="p-6 max-w-6xl mx-auto">
      {toast && (
        <div className="fixed top-4 right-4 bg-gray-900 text-white px-4 py-2 rounded-lg shadow-lg z-50 text-sm">{toast}</div>
      )}

      <div className="mb-6">
        <h1 className="text-2xl font-bold text-gray-900">📈 宣伝分析</h1>
        <p className="text-gray-500 text-sm mt-0.5">投稿パフォーマンスの記録とAI改善提案</p>
      </div>

      {/* KPI */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
        {[
          { label: '総インプ', value: kpi.impressions.toLocaleString(), color: 'text-blue-600', icon: '👁️' },
          { label: '総いいね', value: kpi.likes.toLocaleString(), color: 'text-pink-600', icon: '❤️' },
          { label: '累計リード', value: kpi.leads.toLocaleString(), color: 'text-purple-600', icon: '🎯' },
          { label: '累計成約', value: kpi.conversions.toLocaleString(), color: 'text-green-600', icon: '🏆' },
        ].map(item => (
          <div key={item.label} className="bg-white rounded-xl p-4 shadow-sm border text-center">
            <p className="text-2xl mb-1">{item.icon}</p>
            <p className={`text-2xl font-bold ${item.color}`}>{item.value}</p>
            <p className="text-xs text-gray-500">{item.label}</p>
          </div>
        ))}
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        {/* 左：投稿リスト */}
        <div className="bg-white rounded-xl border shadow-sm overflow-hidden">
          <div className="px-4 py-3 border-b bg-gray-50 flex items-center justify-between">
            <p className="text-sm font-semibold text-gray-700">
              {showAll ? '全投稿' : '投稿済み'}（{displayPosts.length}件）
            </p>
            <button
              onClick={() => setShowAll(!showAll)}
              className="text-xs text-pink-600 hover:underline"
            >
              {showAll ? '投稿済みのみ' : '全て表示'}
            </button>
          </div>
          {loading ? (
            <div className="p-6 text-center text-gray-400 text-sm">読み込み中...</div>
          ) : displayPosts.length === 0 ? (
            <div className="p-6 text-center text-gray-400 text-sm">
              <p className="mb-2">投稿済み投稿がありません</p>
              <Link href="/dashboard/promo/posts" className="text-pink-600 hover:underline text-xs">
                投稿管理へ →
              </Link>
            </div>
          ) : (
            <div className="divide-y max-h-[600px] overflow-y-auto">
              {displayPosts.map(post => (
                <button
                  key={post.id}
                  onClick={() => handleSelect(post)}
                  className={`w-full text-left px-4 py-3 hover:bg-gray-50 transition-colors ${
                    selectedPost?.id === post.id ? 'bg-pink-50 border-l-4 border-pink-500' : ''
                  }`}
                >
                  <div className="flex items-center gap-1.5 mb-0.5">
                    <span className="text-sm">{PLATFORM_ICONS[post.platform] || '📝'}</span>
                    <span className={`text-xs px-1.5 py-0.5 rounded ${STATUS_COLORS[post.status] || 'bg-gray-100 text-gray-600'}`}>
                      {STATUS_LABELS[post.status] || post.status}
                    </span>
                  </div>
                  <p className="text-xs text-gray-700 line-clamp-2">
                    {post.title || post.body?.slice(0, 60) || '（本文なし）'}
                  </p>
                  <p className="text-xs text-gray-400 mt-0.5">
                    {new Date(post.created_at).toLocaleDateString('ja-JP')}
                  </p>
                </button>
              ))}
            </div>
          )}
        </div>

        {/* 右：分析パネル */}
        <div className="md:col-span-2 space-y-4">
          {!selectedPost ? (
            <div className="bg-white rounded-xl border p-12 text-center text-gray-400">
              <p className="text-3xl mb-2">👈</p>
              <p>投稿を選択して数値を入力してください</p>
              <p className="text-xs mt-2">AIが改善提案を自動生成します</p>
            </div>
          ) : (
            <>
              {/* 選択中の投稿 */}
              <div className="bg-white rounded-xl border shadow-sm p-4">
                <div className="flex items-center justify-between mb-1">
                  <div className="flex items-center gap-2">
                    <span>{PLATFORM_ICONS[selectedPost.platform]}</span>
                    <span className="text-sm font-semibold text-gray-700">
                      {selectedPost.title || selectedPost.body?.slice(0, 50) + '…' || '（本文なし）'}
                    </span>
                  </div>
                  <Link href={`/dashboard/promo/posts/${selectedPost.id}`}
                    className="text-xs text-pink-600 hover:underline">
                    詳細 →
                  </Link>
                </div>
              </div>

              {/* 数値入力 */}
              <div className="bg-white rounded-xl border shadow-sm p-5">
                <h3 className="font-semibold text-gray-700 text-sm mb-4">📊 実績数値を入力</h3>
                {analyticsLoading ? (
                  <div className="text-center text-gray-400 py-4 text-sm">読み込み中...</div>
                ) : (
                  <>
                    <div className="grid grid-cols-2 sm:grid-cols-3 gap-3 mb-4">
                      {[
                        ['impressions', '👁️ インプレッション'],
                        ['likes', '❤️ いいね'],
                        ['comments', '💬 コメント'],
                        ['shares', '🔁 シェア・RT'],
                        ['saves', '🔖 保存'],
                        ['profile_clicks', '👤 プロフクリック'],
                        ['url_clicks', '🔗 URLクリック'],
                        ['leads', '🎯 無料相談申込'],
                        ['conversions', '🏆 成約数'],
                      ].map(([key, label]) => (
                        <div key={key}>
                          <label className="block text-xs text-gray-500 mb-0.5">{label}</label>
                          <input
                            type="number"
                            value={form[key] ?? ''}
                            onChange={e => setForm({...form, [key]: e.target.value})}
                            className="w-full border rounded p-2 text-sm focus:outline-none focus:ring-2 focus:ring-pink-300"
                            placeholder="0"
                            min={0}
                          />
                        </div>
                      ))}
                    </div>
                    <div className="mb-4">
                      <label className="block text-xs text-gray-500 mb-0.5">📝 メモ</label>
                      <textarea
                        value={form.memo ?? ''}
                        onChange={e => setForm({...form, memo: e.target.value})}
                        className="w-full border rounded p-2 text-sm focus:outline-none focus:ring-2 focus:ring-pink-300"
                        rows={2}
                        placeholder="特記事項など"
                      />
                    </div>
                    <button onClick={handleSave} disabled={saving}
                      className="w-full bg-pink-600 text-white py-2.5 rounded-lg text-sm disabled:opacity-50 hover:bg-pink-700 font-medium">
                      {saving ? '⏳ AI分析生成中...' : '💾 保存してAI改善提案を生成する'}
                    </button>
                  </>
                )}
              </div>

              {/* AI分析結果 */}
              {analytics?.ai_analysis && (
                <div className="bg-gradient-to-br from-purple-50 to-pink-50 rounded-xl border border-purple-100 p-5 shadow-sm">
                  <h3 className="font-semibold text-purple-800 mb-3 flex items-center gap-2">
                    <span>🤖</span> AI改善提案
                  </h3>
                  <div className="text-sm text-gray-700 whitespace-pre-wrap leading-relaxed">
                    {analytics.ai_analysis}
                  </div>
                  <p className="text-xs text-gray-400 mt-3">
                    ※ 数値を更新して再保存すると、最新データで分析し直します
                  </p>
                </div>
              )}

              {/* 過去数値サマリー */}
              {analytics && (
                <div className="bg-white rounded-xl border shadow-sm p-4">
                  <h3 className="font-semibold text-gray-700 text-sm mb-3">📋 現在の記録値</h3>
                  <div className="grid grid-cols-3 gap-2">
                    {[
                      ['impressions', 'インプ', analytics.impressions],
                      ['likes', 'いいね', analytics.likes],
                      ['comments', 'コメント', analytics.comments],
                      ['shares', 'シェア', analytics.shares],
                      ['url_clicks', 'URLクリック', analytics.url_clicks],
                      ['leads', 'リード', analytics.leads],
                      ['conversions', '成約', analytics.conversions],
                    ].map(([key, label, val]) => (
                      <div key={key as string} className="text-center bg-gray-50 rounded p-2">
                        <p className="text-xs text-gray-500">{label}</p>
                        <p className="text-lg font-bold text-gray-800">{val ?? '-'}</p>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </>
          )}
        </div>
      </div>
    </div>
  )
}
