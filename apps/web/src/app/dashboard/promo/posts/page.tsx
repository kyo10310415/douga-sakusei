'use client'
import { useState, useEffect, useCallback } from 'react'
import Link from 'next/link'
import { useSearchParams } from 'next/navigation'
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

export default function PromoPostsPage() {
  const searchParams = useSearchParams()
  const [posts, setPosts] = useState<any[]>([])
  const [total, setTotal] = useState(0)
  const [loading, setLoading] = useState(true)
  const [statusFilter, setStatusFilter] = useState(searchParams.get('status') || '')
  const [platformFilter, setPlatformFilter] = useState('')
  const [actionLoading, setActionLoading] = useState<string | null>(null)
  const [toast, setToast] = useState('')

  const fetchPosts = useCallback(async () => {
    setLoading(true)
    try {
      const res = await promoApi.listPosts({
        status: statusFilter || undefined,
        platform: platformFilter || undefined,
        limit: 50,
      })
      setPosts(res.data.posts || [])
      setTotal(res.data.total || 0)
    } catch (e) {
      console.error(e)
    } finally {
      setLoading(false)
    }
  }, [statusFilter, platformFilter])

  useEffect(() => { fetchPosts() }, [fetchPosts])

  const showToast = (msg: string) => {
    setToast(msg)
    setTimeout(() => setToast(''), 3000)
  }

  const handleApprove = async (id: string) => {
    setActionLoading(id + '_approve')
    try {
      await promoApi.approvePost(id)
      showToast('✅ 承認しました')
      fetchPosts()
    } catch (e: any) {
      showToast('⚠️ ' + (e.response?.data?.detail || '承認に失敗しました'))
    } finally {
      setActionLoading(null)
    }
  }

  const handleDelete = async (id: string) => {
    if (!confirm('この投稿を削除しますか？')) return
    setActionLoading(id + '_delete')
    try {
      await promoApi.deletePost(id)
      showToast('🗑️ 削除しました')
      fetchPosts()
    } catch {
      showToast('削除に失敗しました')
    } finally {
      setActionLoading(null)
    }
  }

  return (
    <div className="p-6 max-w-6xl mx-auto">
      {/* トースト */}
      {toast && (
        <div className="fixed top-4 right-4 bg-gray-900 text-white px-4 py-2 rounded-lg shadow-lg z-50 text-sm">
          {toast}
        </div>
      )}

      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">📝 投稿管理</h1>
          <p className="text-gray-500 text-sm mt-0.5">全{total}件</p>
        </div>
        <Link
          href="/dashboard/promo/generate"
          className="bg-pink-600 hover:bg-pink-700 text-white px-4 py-2 rounded-lg text-sm font-medium flex items-center gap-2"
        >
          <span>✨</span> 投稿を生成する
        </Link>
      </div>

      {/* フィルター */}
      <div className="flex flex-wrap gap-2 mb-5">
        <div className="flex gap-1 flex-wrap">
          {['', ...Object.keys(STATUS_LABELS)].map(s => (
            <button
              key={s}
              onClick={() => setStatusFilter(s)}
              className={`text-xs px-3 py-1.5 rounded-full border transition-colors ${
                statusFilter === s
                  ? 'bg-pink-600 text-white border-pink-600'
                  : 'bg-white text-gray-600 border-gray-200 hover:border-pink-300'
              }`}
            >
              {s ? STATUS_LABELS[s] : 'すべて'}
            </button>
          ))}
        </div>
        <div className="flex gap-1">
          {['', 'x', 'instagram', 'tiktok', 'youtube_shorts'].map(p => (
            <button
              key={p}
              onClick={() => setPlatformFilter(p)}
              className={`text-xs px-3 py-1.5 rounded-full border transition-colors ${
                platformFilter === p
                  ? 'bg-gray-800 text-white border-gray-800'
                  : 'bg-white text-gray-600 border-gray-200 hover:border-gray-400'
              }`}
            >
              {p ? `${PLATFORM_ICONS[p]} ${p === 'x' ? 'X' : p === 'instagram' ? 'Instagram' : p === 'tiktok' ? 'TikTok' : 'YT Shorts'}` : '全媒体'}
            </button>
          ))}
        </div>
      </div>

      {loading ? (
        <div className="text-center py-12 text-gray-400">読み込み中...</div>
      ) : posts.length === 0 ? (
        <div className="bg-white rounded-xl border p-12 text-center">
          <p className="text-4xl mb-3">📝</p>
          <p className="text-gray-500 mb-4">投稿がありません</p>
          <Link
            href="/dashboard/promo/generate"
            className="inline-block bg-pink-600 hover:bg-pink-700 text-white px-5 py-2 rounded-lg text-sm"
          >
            最初の投稿を生成する →
          </Link>
        </div>
      ) : (
        <div className="space-y-3">
          {posts.map(post => (
            <div key={post.id} className="bg-white rounded-xl border shadow-sm p-4 hover:shadow-md transition-shadow">
              <div className="flex items-start gap-3">
                <span className="text-2xl mt-0.5">{PLATFORM_ICONS[post.platform] || '📝'}</span>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 mb-1 flex-wrap">
                    <span className={`text-xs px-2 py-0.5 rounded font-medium ${STATUS_COLORS[post.status]}`}>
                      {STATUS_LABELS[post.status]}
                    </span>
                    {post.ng_check_passed === false && (
                      <span className="text-xs bg-red-50 text-red-600 px-2 py-0.5 rounded border border-red-200">
                        ⚠️ NG表現あり
                      </span>
                    )}
                    <span className="text-xs text-gray-400">
                      {new Date(post.created_at).toLocaleDateString('ja-JP')}
                    </span>
                  </div>
                  {post.title && (
                    <p className="font-semibold text-gray-800 text-sm mb-1">{post.title}</p>
                  )}
                  <p className="text-sm text-gray-600 line-clamp-2">
                    {post.body || post.caption || '（本文なし）'}
                  </p>
                  {post.hashtags?.length > 0 && (
                    <p className="text-xs text-blue-400 mt-1">
                      {post.hashtags.slice(0, 5).map((h: string) => `#${h}`).join(' ')}
                      {post.hashtags.length > 5 && ` +${post.hashtags.length - 5}`}
                    </p>
                  )}
                </div>

                {/* アクション */}
                <div className="flex flex-col gap-1.5 flex-shrink-0">
                  <Link
                    href={`/dashboard/promo/posts/${post.id}`}
                    className="text-xs border px-3 py-1.5 rounded hover:bg-gray-50 text-center"
                  >
                    詳細
                  </Link>
                  {post.status === 'pending_review' && (
                    <button
                      onClick={() => handleApprove(post.id)}
                      disabled={actionLoading === post.id + '_approve'}
                      className="text-xs bg-blue-600 text-white px-3 py-1.5 rounded hover:bg-blue-700 disabled:opacity-50"
                    >
                      {actionLoading === post.id + '_approve' ? '...' : '承認'}
                    </button>
                  )}
                  <button
                    onClick={() => handleDelete(post.id)}
                    disabled={actionLoading === post.id + '_delete'}
                    className="text-xs text-red-400 hover:text-red-600 px-3 py-1.5 rounded hover:bg-red-50 disabled:opacity-50"
                  >
                    削除
                  </button>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
