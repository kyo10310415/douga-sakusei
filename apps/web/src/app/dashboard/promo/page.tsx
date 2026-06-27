'use client'
import { useState, useEffect } from 'react'
import Link from 'next/link'
import { promoApi } from '@/lib/api'

const STATUS_LABELS: Record<string, string> = {
  draft: '下書き',
  pending_review: 'レビュー待ち',
  approved: '承認済み',
  scheduled: 'スケジュール済み',
  published: '投稿済み',
  rejected: '差し戻し',
}
const STATUS_COLORS: Record<string, string> = {
  draft: 'bg-gray-100 text-gray-700',
  pending_review: 'bg-yellow-100 text-yellow-800',
  approved: 'bg-blue-100 text-blue-800',
  scheduled: 'bg-purple-100 text-purple-800',
  published: 'bg-green-100 text-green-800',
  rejected: 'bg-red-100 text-red-700',
}
const PLATFORM_ICONS: Record<string, string> = {
  x: '𝕏',
  instagram: '📷',
  tiktok: '🎵',
  youtube_shorts: '▶️',
}

export default function PromoDashboardPage() {
  const [data, setData] = useState<any>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    promoApi.getDashboard()
      .then(r => setData(r.data))
      .catch(console.error)
      .finally(() => setLoading(false))
  }, [])

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-center">
          <div className="text-4xl animate-pulse mb-3">📣</div>
          <p className="text-gray-500">読み込み中...</p>
        </div>
      </div>
    )
  }

  const statusCounts = data?.status_counts || {}
  const platformCounts = data?.platform_counts || {}
  const recentPosts = data?.recent_posts || []

  return (
    <div className="p-6 max-w-6xl mx-auto">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">📣 コンサル宣伝ダッシュボード</h1>
          <p className="text-gray-500 text-sm mt-1">AIで生成した宣伝投稿の管理・分析</p>
        </div>
        <Link
          href="/dashboard/promo/generate"
          className="bg-pink-600 hover:bg-pink-700 text-white px-4 py-2 rounded-lg text-sm font-medium flex items-center gap-2"
        >
          <span>✨</span> 投稿を生成する
        </Link>
      </div>

      {/* KPI カード */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
        <div className="bg-white rounded-xl p-4 shadow-sm border">
          <p className="text-xs text-gray-500 mb-1">総投稿数</p>
          <p className="text-3xl font-bold text-gray-900">{data?.total_posts ?? 0}</p>
        </div>
        <div className="bg-white rounded-xl p-4 shadow-sm border">
          <p className="text-xs text-gray-500 mb-1">投稿済み</p>
          <p className="text-3xl font-bold text-green-600">{statusCounts.published ?? 0}</p>
        </div>
        <div className="bg-white rounded-xl p-4 shadow-sm border">
          <p className="text-xs text-gray-500 mb-1">累計リード数</p>
          <p className="text-3xl font-bold text-blue-600">{data?.total_leads ?? 0}</p>
        </div>
        <div className="bg-white rounded-xl p-4 shadow-sm border">
          <p className="text-xs text-gray-500 mb-1">累計成約数</p>
          <p className="text-3xl font-bold text-purple-600">{data?.total_conversions ?? 0}</p>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-6">
        {/* ステータス別 */}
        <div className="bg-white rounded-xl p-5 shadow-sm border">
          <h2 className="font-semibold text-gray-700 mb-3">ステータス別</h2>
          <div className="space-y-2">
            {Object.entries(STATUS_LABELS).map(([key, label]) => (
              <div key={key} className="flex items-center justify-between">
                <span className={`px-2 py-0.5 rounded text-xs font-medium ${STATUS_COLORS[key]}`}>
                  {label}
                </span>
                <span className="font-bold text-gray-800">{statusCounts[key] ?? 0}件</span>
              </div>
            ))}
          </div>
        </div>

        {/* 媒体別 */}
        <div className="bg-white rounded-xl p-5 shadow-sm border">
          <h2 className="font-semibold text-gray-700 mb-3">媒体別</h2>
          <div className="space-y-2">
            {[['x', 'X（Twitter）'], ['instagram', 'Instagram'], ['tiktok', 'TikTok'], ['youtube_shorts', 'YouTube Shorts']].map(([key, label]) => (
              <div key={key} className="flex items-center justify-between">
                <span className="text-sm text-gray-600 flex items-center gap-1">
                  <span>{PLATFORM_ICONS[key]}</span> {label}
                </span>
                <span className="font-bold text-gray-800">{platformCounts[key] ?? 0}件</span>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* 最近の投稿 */}
      <div className="bg-white rounded-xl shadow-sm border">
        <div className="flex items-center justify-between px-5 py-4 border-b">
          <h2 className="font-semibold text-gray-700">最近の投稿</h2>
          <Link href="/dashboard/promo/posts" className="text-pink-600 hover:underline text-sm">
            すべて見る →
          </Link>
        </div>
        {recentPosts.length === 0 ? (
          <div className="p-8 text-center text-gray-400">
            <p className="text-3xl mb-2">📝</p>
            <p>まだ投稿がありません</p>
            <Link href="/dashboard/promo/generate" className="mt-3 inline-block text-pink-600 hover:underline text-sm">
              最初の投稿を生成する →
            </Link>
          </div>
        ) : (
          <div className="divide-y">
            {recentPosts.map((post: any) => (
              <Link
                key={post.id}
                href={`/dashboard/promo/posts/${post.id}`}
                className="flex items-start gap-3 px-5 py-3 hover:bg-gray-50 transition-colors"
              >
                <span className="text-xl mt-0.5">{PLATFORM_ICONS[post.platform] || '📝'}</span>
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium text-gray-800 truncate">
                    {post.title || post.body?.slice(0, 50) || '（本文なし）'}
                  </p>
                  <p className="text-xs text-gray-400 mt-0.5">
                    {new Date(post.created_at).toLocaleDateString('ja-JP')}
                  </p>
                </div>
                <span className={`text-xs px-2 py-0.5 rounded flex-shrink-0 ${STATUS_COLORS[post.status]}`}>
                  {STATUS_LABELS[post.status]}
                </span>
              </Link>
            ))}
          </div>
        )}
      </div>

      {/* クイックリンク */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mt-6">
        {[
          { href: '/dashboard/promo/generate', label: '投稿生成', icon: '✨', color: 'bg-pink-50 hover:bg-pink-100 border-pink-200' },
          { href: '/dashboard/promo/posts?status=pending_review', label: 'レビュー待ち', icon: '👀', color: 'bg-yellow-50 hover:bg-yellow-100 border-yellow-200' },
          { href: '/dashboard/promo/assets', label: '素材管理', icon: '🖼️', color: 'bg-blue-50 hover:bg-blue-100 border-blue-200' },
          { href: '/dashboard/promo/analytics', label: '分析', icon: '📈', color: 'bg-green-50 hover:bg-green-100 border-green-200' },
        ].map(item => (
          <Link
            key={item.href}
            href={item.href}
            className={`flex items-center gap-2 px-4 py-3 rounded-lg border text-sm font-medium text-gray-700 transition-colors ${item.color}`}
          >
            <span>{item.icon}</span> {item.label}
          </Link>
        ))}
      </div>
    </div>
  )
}
