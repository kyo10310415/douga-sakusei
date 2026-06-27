'use client'
import { useState, useEffect } from 'react'
import Link from 'next/link'
import { promoApi } from '@/lib/api'

export default function PromoAssetsPage() {
  const [posts, setPosts] = useState<any[]>([])
  const [selectedPost, setSelectedPost] = useState<any>(null)
  const [assets, setAssets] = useState<any[]>([])
  const [loading, setLoading] = useState(true)
  const [assetsLoading, setAssetsLoading] = useState(false)
  const [genType, setGenType] = useState<'image_prompt' | 'video_script'>('image_prompt')
  const [genDuration, setGenDuration] = useState('30s')
  const [genLoading, setGenLoading] = useState(false)
  const [toast, setToast] = useState('')

  const showToast = (msg: string) => {
    setToast(msg)
    setTimeout(() => setToast(''), 3000)
  }

  useEffect(() => {
    promoApi.listPosts({ limit: 50 })
      .then(r => setPosts(r.data.posts || []))
      .catch(console.error)
      .finally(() => setLoading(false))
  }, [])

  const handleSelectPost = async (post: any) => {
    setSelectedPost(post)
    setAssetsLoading(true)
    try {
      const res = await promoApi.listAssets(post.id)
      setAssets(res.data.assets || [])
    } catch {
      setAssets([])
    } finally {
      setAssetsLoading(false)
    }
  }

  const handleGenerate = async () => {
    if (!selectedPost) return
    setGenLoading(true)
    try {
      const res = await promoApi.generateAsset(selectedPost.id, {
        asset_type: genType,
        duration: genDuration,
      })
      setAssets(prev => [...prev, res.data])
      showToast('✅ 素材を生成しました')
    } catch (e: any) {
      showToast('⚠️ ' + (e.response?.data?.detail || '生成に失敗しました'))
    } finally {
      setGenLoading(false)
    }
  }

  const PLATFORM_ICONS: Record<string, string> = {
    x: '𝕏', instagram: '📷', tiktok: '🎵', youtube_shorts: '▶️'
  }

  const assetTypeLabel: Record<string, string> = {
    image_prompt: '🎨 画像プロンプト',
    video_script: '🎬 動画台本',
    image: '🖼️ 画像',
    thumbnail_prompt: '🖼️ サムネプロンプト',
  }

  return (
    <div className="p-6 max-w-6xl mx-auto">
      {toast && (
        <div className="fixed top-4 right-4 bg-gray-900 text-white px-4 py-2 rounded-lg shadow-lg z-50 text-sm">{toast}</div>
      )}

      <div className="mb-6">
        <h1 className="text-2xl font-bold text-gray-900">🖼️ 素材管理</h1>
        <p className="text-gray-500 text-sm mt-0.5">投稿ごとの画像プロンプト・動画台本を生成・管理</p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        {/* 左：投稿一覧 */}
        <div className="bg-white rounded-xl border shadow-sm overflow-hidden">
          <div className="px-4 py-3 border-b bg-gray-50">
            <p className="text-sm font-semibold text-gray-700">投稿を選択</p>
          </div>
          {loading ? (
            <div className="p-6 text-center text-gray-400 text-sm">読み込み中...</div>
          ) : posts.length === 0 ? (
            <div className="p-6 text-center text-gray-400 text-sm">
              <p className="mb-2">投稿がありません</p>
              <Link href="/dashboard/promo/generate" className="text-pink-600 hover:underline text-xs">
                投稿を生成する →
              </Link>
            </div>
          ) : (
            <div className="divide-y max-h-[600px] overflow-y-auto">
              {posts.map(post => (
                <button
                  key={post.id}
                  onClick={() => handleSelectPost(post)}
                  className={`w-full text-left px-4 py-3 hover:bg-gray-50 transition-colors ${
                    selectedPost?.id === post.id ? 'bg-pink-50 border-l-4 border-pink-500' : ''
                  }`}
                >
                  <div className="flex items-center gap-1.5 mb-0.5">
                    <span className="text-sm">{PLATFORM_ICONS[post.platform] || '📝'}</span>
                    <span className="text-xs text-gray-500">{post.platform}</span>
                  </div>
                  <p className="text-xs text-gray-700 line-clamp-2">
                    {post.title || post.body?.slice(0, 60) || '（本文なし）'}
                  </p>
                </button>
              ))}
            </div>
          )}
        </div>

        {/* 右：素材パネル */}
        <div className="md:col-span-2 space-y-4">
          {!selectedPost ? (
            <div className="bg-white rounded-xl border p-12 text-center text-gray-400">
              <p className="text-3xl mb-2">👈</p>
              <p>左の投稿を選択してください</p>
            </div>
          ) : (
            <>
              {/* 選択中の投稿 */}
              <div className="bg-white rounded-xl border shadow-sm p-4">
                <div className="flex items-center justify-between mb-2">
                  <div className="flex items-center gap-2">
                    <span>{PLATFORM_ICONS[selectedPost.platform]}</span>
                    <span className="text-sm font-semibold text-gray-700">
                      {selectedPost.title || selectedPost.body?.slice(0, 40) + '…' || '（本文なし）'}
                    </span>
                  </div>
                  <Link href={`/dashboard/promo/posts/${selectedPost.id}`}
                    className="text-xs text-pink-600 hover:underline">
                    詳細を見る →
                  </Link>
                </div>
                <p className="text-xs text-gray-500 line-clamp-2">{selectedPost.body || selectedPost.caption}</p>
              </div>

              {/* 素材生成 */}
              <div className="bg-white rounded-xl border shadow-sm p-4">
                <h3 className="font-semibold text-gray-700 text-sm mb-3">AIで素材を生成</h3>
                <div className="flex flex-wrap gap-3 items-end">
                  <div>
                    <label className="block text-xs text-gray-500 mb-1">素材タイプ</label>
                    <select value={genType} onChange={e => setGenType(e.target.value as any)}
                      className="border rounded p-2 text-sm focus:outline-none">
                      <option value="image_prompt">🎨 画像プロンプト</option>
                      <option value="video_script">🎬 動画台本</option>
                    </select>
                  </div>
                  {genType === 'video_script' && (
                    <div>
                      <label className="block text-xs text-gray-500 mb-1">動画尺</label>
                      <select value={genDuration} onChange={e => setGenDuration(e.target.value)}
                        className="border rounded p-2 text-sm focus:outline-none">
                        <option value="15s">15秒</option>
                        <option value="30s">30秒</option>
                        <option value="60s">60秒</option>
                      </select>
                    </div>
                  )}
                  <button onClick={handleGenerate} disabled={genLoading}
                    className="bg-blue-600 text-white px-4 py-2 rounded text-sm disabled:opacity-50 hover:bg-blue-700">
                    {genLoading ? '生成中...' : '✨ AIで生成'}
                  </button>
                </div>
                {genType === 'image_prompt' && (
                  <p className="text-xs text-gray-400 mt-2">
                    💡 生成された英語プロンプトを Midjourney / DALL-E / Stable Diffusion にコピペして利用できます
                  </p>
                )}
                {genType === 'video_script' && (
                  <p className="text-xs text-gray-400 mt-2">
                    💡 生成された台本を CapCut / Premiere など動画ツールのナレーション原稿として利用できます
                  </p>
                )}
              </div>

              {/* 素材一覧 */}
              <div className="bg-white rounded-xl border shadow-sm">
                <div className="px-4 py-3 border-b bg-gray-50 flex items-center justify-between">
                  <p className="text-sm font-semibold text-gray-700">生成済み素材</p>
                  <span className="text-xs text-gray-400">{assets.length}件</span>
                </div>
                {assetsLoading ? (
                  <div className="p-6 text-center text-gray-400 text-sm">読み込み中...</div>
                ) : assets.length === 0 ? (
                  <div className="p-8 text-center text-gray-400 text-sm">
                    <p>素材がありません</p>
                    <p className="text-xs mt-1">上の「AIで生成」から作成できます</p>
                  </div>
                ) : (
                  <div className="divide-y">
                    {assets.map(asset => (
                      <div key={asset.id} className="p-4">
                        <div className="flex items-center justify-between mb-2">
                          <span className="text-xs bg-blue-100 text-blue-700 px-2 py-0.5 rounded">
                            {assetTypeLabel[asset.asset_type] || asset.asset_type}
                          </span>
                          <span className="text-xs text-gray-400">
                            {new Date(asset.created_at).toLocaleDateString('ja-JP')}
                          </span>
                        </div>
                        {asset.prompt && (
                          <div className="mb-2">
                            <p className="text-xs text-gray-500 mb-1">プロンプト（英語）</p>
                            <div className="bg-gray-50 rounded p-2 text-xs font-mono text-gray-700 relative">
                              <p className="pr-16 line-clamp-3">{asset.prompt}</p>
                              <button
                                onClick={() => navigator.clipboard.writeText(asset.prompt).then(() => showToast('📋 コピーしました'))}
                                className="absolute top-2 right-2 text-xs bg-white border px-2 py-0.5 rounded hover:bg-gray-50"
                              >
                                コピー
                              </button>
                            </div>
                          </div>
                        )}
                        {asset.content && (
                          <div>
                            <p className="text-xs text-gray-500 mb-1">
                              {asset.asset_type === 'video_script' ? '台本' : '詳細'}
                            </p>
                            <p className="text-sm text-gray-700 whitespace-pre-wrap leading-relaxed bg-gray-50 rounded p-2">
                              {asset.content}
                            </p>
                            <button
                              onClick={() => navigator.clipboard.writeText(asset.content).then(() => showToast('📋 コピーしました'))}
                              className="mt-1 text-xs border px-2 py-0.5 rounded hover:bg-gray-50"
                            >
                              📋 台本をコピー
                            </button>
                          </div>
                        )}
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  )
}
