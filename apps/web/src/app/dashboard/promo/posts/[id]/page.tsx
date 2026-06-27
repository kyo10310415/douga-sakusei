'use client'
import { useState, useEffect } from 'react'
import { useParams, useRouter } from 'next/navigation'
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

export default function PostDetailPage() {
  const params = useParams()
  const router = useRouter()
  const postId = params.id as string

  const [post, setPost] = useState<any>(null)
  const [assets, setAssets] = useState<any[]>([])
  const [analytics, setAnalytics] = useState<any>(null)
  const [loading, setLoading] = useState(true)
  const [editing, setEditing] = useState(false)
  const [editData, setEditData] = useState<any>({})
  const [saving, setSaving] = useState(false)
  const [actionLoading, setActionLoading] = useState('')
  const [toast, setToast] = useState('')
  const [tab, setTab] = useState<'content' | 'assets' | 'analytics'>('content')
  const [genAssetType, setGenAssetType] = useState<'image_prompt' | 'video_script'>('image_prompt')
  const [genDuration, setGenDuration] = useState('30s')
  const [genLoading, setGenLoading] = useState(false)
  const [rejectReason, setRejectReason] = useState('')
  const [showRejectInput, setShowRejectInput] = useState(false)
  const [analyticsForm, setAnalyticsForm] = useState<any>({})
  const [savingAnalytics, setSavingAnalytics] = useState(false)

  const showToast = (msg: string) => {
    setToast(msg)
    setTimeout(() => setToast(''), 3500)
  }

  const loadPost = async () => {
    try {
      const [postRes, assetsRes, analyticsRes] = await Promise.allSettled([
        promoApi.getPost(postId),
        promoApi.listAssets(postId),
        promoApi.getAnalytics(postId),
      ])
      if (postRes.status === 'fulfilled') {
        setPost(postRes.value.data)
        setEditData({
          title: postRes.value.data.title || '',
          body: postRes.value.data.body || '',
          caption: postRes.value.data.caption || '',
          hashtags: (postRes.value.data.hashtags || []).join(' '),
          cta: postRes.value.data.cta || '',
          memo: postRes.value.data.memo || '',
        })
      }
      if (assetsRes.status === 'fulfilled') {
        setAssets(assetsRes.value.data.assets || [])
      }
      if (analyticsRes.status === 'fulfilled') {
        const a = analyticsRes.value.data.analytics
        setAnalytics(a)
        if (a) {
          setAnalyticsForm({
            impressions: a.impressions ?? '',
            likes: a.likes ?? '',
            comments: a.comments ?? '',
            shares: a.shares ?? '',
            saves: a.saves ?? '',
            profile_clicks: a.profile_clicks ?? '',
            url_clicks: a.url_clicks ?? '',
            leads: a.leads ?? '',
            conversions: a.conversions ?? '',
            memo: a.memo ?? '',
          })
        }
      }
    } catch (e) {
      console.error(e)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { loadPost() }, [postId])

  const handleSave = async () => {
    setSaving(true)
    try {
      const hashtags = editData.hashtags
        .split(/[\s,　]+/)
        .map((h: string) => h.replace(/^#/, '').trim())
        .filter(Boolean)
      await promoApi.updatePost(postId, {
        ...editData,
        hashtags,
      })
      showToast('✅ 保存しました')
      setEditing(false)
      loadPost()
    } catch (e: any) {
      showToast('⚠️ ' + (e.response?.data?.detail || '保存に失敗しました'))
    } finally {
      setSaving(false)
    }
  }

  const handleApprove = async () => {
    setActionLoading('approve')
    try {
      await promoApi.approvePost(postId)
      showToast('✅ 承認しました')
      loadPost()
    } catch (e: any) {
      showToast('⚠️ ' + (e.response?.data?.detail || '承認に失敗しました'))
    } finally {
      setActionLoading('')
    }
  }

  const handleReject = async () => {
    setActionLoading('reject')
    try {
      await promoApi.rejectPost(postId, rejectReason)
      showToast('🔄 差し戻しました')
      setShowRejectInput(false)
      setRejectReason('')
      loadPost()
    } catch {
      showToast('差し戻しに失敗しました')
    } finally {
      setActionLoading('')
    }
  }

  const handlePublish = async () => {
    if (!confirm('この投稿を実際に投稿しますか？')) return
    setActionLoading('publish')
    try {
      const res = await promoApi.publishPost(postId)
      if (res.data.success) {
        showToast(`🎉 投稿しました！${res.data.external_post_url ? ' URLをコピーしました' : ''}`)
        if (res.data.external_post_url) {
          navigator.clipboard.writeText(res.data.external_post_url).catch(() => {})
        }
      } else {
        showToast('⚠️ 投稿に失敗: ' + (res.data.error_message || '不明なエラー'))
      }
      loadPost()
    } catch (e: any) {
      showToast('⚠️ ' + (e.response?.data?.detail || '投稿に失敗しました'))
    } finally {
      setActionLoading('')
    }
  }

  const handleNgCheck = async () => {
    setActionLoading('ng')
    try {
      const res = await promoApi.ngCheck(postId)
      const passed = res.data.ng_check?.passed
      showToast(passed ? '✅ NG表現なし' : '⚠️ NG表現が検出されました')
      loadPost()
    } catch {
      showToast('NGチェックに失敗しました')
    } finally {
      setActionLoading('')
    }
  }

  const handleGenerateAsset = async () => {
    setGenLoading(true)
    try {
      const asset = await promoApi.generateAsset(postId, {
        asset_type: genAssetType,
        duration: genDuration,
      })
      setAssets(prev => [...prev, asset.data])
      showToast('✅ 素材を生成しました')
    } catch (e: any) {
      showToast('⚠️ ' + (e.response?.data?.detail || '素材生成に失敗しました'))
    } finally {
      setGenLoading(false)
    }
  }

  const handleSaveAnalytics = async () => {
    setSavingAnalytics(true)
    try {
      const payload: any = { run_ai_analysis: true }
      for (const key of ['impressions', 'likes', 'comments', 'shares', 'saves', 'profile_clicks', 'url_clicks', 'leads', 'conversions']) {
        const v = analyticsForm[key]
        if (v !== '' && v !== undefined) payload[key] = Number(v)
      }
      if (analyticsForm.memo) payload.memo = analyticsForm.memo
      const res = await promoApi.upsertAnalytics(postId, payload)
      setAnalytics(res.data.analytics)
      showToast('✅ 分析データを保存しAI分析を実行しました')
    } catch (e: any) {
      showToast('⚠️ ' + (e.response?.data?.detail || '保存に失敗しました'))
    } finally {
      setSavingAnalytics(false)
    }
  }

  const copyText = () => {
    const text = [post?.body || post?.caption, post?.cta, post?.hashtags?.map((h: string) => `#${h}`).join(' ')].filter(Boolean).join('\n')
    navigator.clipboard.writeText(text).then(() => showToast('📋 コピーしました'))
  }

  if (loading) {
    return <div className="min-h-screen flex items-center justify-center"><p className="text-gray-400">読み込み中...</p></div>
  }
  if (!post) {
    return <div className="p-6"><p className="text-red-500">投稿が見つかりません</p></div>
  }

  const platformLabel = post.platform === 'x' ? '𝕏 X' : post.platform === 'instagram' ? '📷 Instagram' : post.platform === 'tiktok' ? '🎵 TikTok' : '▶️ YouTube Shorts'

  return (
    <div className="p-6 max-w-4xl mx-auto">
      {toast && (
        <div className="fixed top-4 right-4 bg-gray-900 text-white px-4 py-2 rounded-lg shadow-lg z-50 text-sm">{toast}</div>
      )}

      {/* ヘッダー */}
      <div className="flex items-center gap-3 mb-5">
        <button onClick={() => router.back()} className="text-gray-400 hover:text-gray-600">←</button>
        <div className="flex-1">
          <div className="flex items-center gap-2 flex-wrap">
            <span className="font-semibold text-gray-700">{platformLabel}</span>
            <span className={`text-xs px-2 py-0.5 rounded font-medium ${STATUS_COLORS[post.status]}`}>
              {STATUS_LABELS[post.status]}
            </span>
            {post.ng_check_passed === false && (
              <span className="text-xs bg-red-100 text-red-600 px-2 py-0.5 rounded">⚠️ NG表現あり</span>
            )}
            {post.ng_check_passed === true && (
              <span className="text-xs bg-green-100 text-green-600 px-2 py-0.5 rounded">✅ NG表現なし</span>
            )}
          </div>
          <p className="text-xs text-gray-400 mt-0.5">
            作成: {new Date(post.created_at).toLocaleString('ja-JP')}
          </p>
        </div>
      </div>

      {/* アクションボタン */}
      <div className="flex flex-wrap gap-2 mb-5">
        <button onClick={copyText} className="text-xs border px-3 py-2 rounded hover:bg-gray-50">
          📋 テキストコピー
        </button>
        <button onClick={handleNgCheck} disabled={actionLoading === 'ng'} className="text-xs border px-3 py-2 rounded hover:bg-gray-50 disabled:opacity-50">
          {actionLoading === 'ng' ? '...' : '🔍 NG再チェック'}
        </button>
        {post.status === 'pending_review' && (
          <>
            <button onClick={handleApprove} disabled={actionLoading === 'approve'} className="text-xs bg-blue-600 text-white px-3 py-2 rounded hover:bg-blue-700 disabled:opacity-50">
              {actionLoading === 'approve' ? '...' : '✅ 承認する'}
            </button>
            <button onClick={() => setShowRejectInput(!showRejectInput)} className="text-xs bg-orange-100 text-orange-700 px-3 py-2 rounded hover:bg-orange-200">
              🔄 差し戻し
            </button>
          </>
        )}
        {post.status === 'approved' && (
          <button onClick={handlePublish} disabled={actionLoading === 'publish'} className="text-xs bg-green-600 text-white px-3 py-2 rounded hover:bg-green-700 disabled:opacity-50">
            {actionLoading === 'publish' ? '投稿中...' : '🚀 投稿する'}
          </button>
        )}
        {post.external_post_url && (
          <a href={post.external_post_url} target="_blank" rel="noopener noreferrer"
            className="text-xs bg-gray-800 text-white px-3 py-2 rounded hover:bg-gray-900">
            🔗 投稿を確認
          </a>
        )}
        {!editing && post.status !== 'published' && (
          <button onClick={() => setEditing(true)} className="text-xs border px-3 py-2 rounded hover:bg-gray-50">
            ✏️ 編集
          </button>
        )}
      </div>

      {/* 差し戻し理由 */}
      {showRejectInput && (
        <div className="bg-orange-50 border border-orange-200 rounded-xl p-4 mb-4">
          <p className="text-sm font-medium text-orange-800 mb-2">差し戻し理由（任意）</p>
          <input
            type="text"
            value={rejectReason}
            onChange={e => setRejectReason(e.target.value)}
            placeholder="例：NG表現が含まれています"
            className="w-full border rounded p-2 text-sm mb-2 focus:outline-none focus:ring-2 focus:ring-orange-300"
          />
          <button onClick={handleReject} disabled={actionLoading === 'reject'} className="text-sm bg-orange-600 text-white px-4 py-1.5 rounded hover:bg-orange-700 disabled:opacity-50">
            {actionLoading === 'reject' ? '...' : '差し戻す'}
          </button>
        </div>
      )}

      {/* NG表現詳細 */}
      {post.ng_check_details?.found?.length > 0 && (
        <div className="bg-red-50 border border-red-200 rounded-xl p-4 mb-4">
          <p className="text-sm font-semibold text-red-700 mb-2">⚠️ NG表現が検出されました</p>
          {post.ng_check_details.found.map((item: any, i: number) => (
            <div key={i} className="text-xs mb-1">
              <span className="text-red-600 font-medium">「{item.expression}」</span>
              {item.suggestion && <span className="text-gray-600 ml-1">→ 代替：「{item.suggestion}」</span>}
            </div>
          ))}
        </div>
      )}

      {/* タブ */}
      <div className="flex border-b mb-5 gap-1">
        {[['content', '📄 本文'], ['assets', '🖼️ 素材'], ['analytics', '📈 分析']].map(([key, label]) => (
          <button
            key={key}
            onClick={() => setTab(key as any)}
            className={`px-4 py-2 text-sm font-medium border-b-2 transition-colors ${
              tab === key ? 'border-pink-600 text-pink-600' : 'border-transparent text-gray-500 hover:text-gray-700'
            }`}
          >
            {label}
          </button>
        ))}
      </div>

      {/* ── 本文タブ ── */}
      {tab === 'content' && (
        <div className="bg-white rounded-xl border p-5 shadow-sm">
          {editing ? (
            <div className="space-y-4">
              <div>
                <label className="block text-xs font-semibold text-gray-600 mb-1">タイトル</label>
                <input type="text" value={editData.title} onChange={e => setEditData({...editData, title: e.target.value})}
                  className="w-full border rounded-lg p-2 text-sm focus:outline-none focus:ring-2 focus:ring-pink-300" />
              </div>
              <div>
                <label className="block text-xs font-semibold text-gray-600 mb-1">本文</label>
                <textarea value={editData.body} onChange={e => setEditData({...editData, body: e.target.value})}
                  className="w-full border rounded-lg p-2 text-sm resize-none focus:outline-none focus:ring-2 focus:ring-pink-300" rows={6} />
                <p className="text-xs text-gray-400 text-right mt-0.5">{editData.body?.length || 0}文字</p>
              </div>
              <div>
                <label className="block text-xs font-semibold text-gray-600 mb-1">CTA（行動喚起）</label>
                <input type="text" value={editData.cta} onChange={e => setEditData({...editData, cta: e.target.value})}
                  className="w-full border rounded-lg p-2 text-sm focus:outline-none focus:ring-2 focus:ring-pink-300" />
              </div>
              <div>
                <label className="block text-xs font-semibold text-gray-600 mb-1">ハッシュタグ（スペース区切り、#なし可）</label>
                <input type="text" value={editData.hashtags} onChange={e => setEditData({...editData, hashtags: e.target.value})}
                  placeholder="VTuber VTuber活動 VTuberコンサル"
                  className="w-full border rounded-lg p-2 text-sm focus:outline-none focus:ring-2 focus:ring-pink-300" />
              </div>
              <div>
                <label className="block text-xs font-semibold text-gray-600 mb-1">メモ</label>
                <textarea value={editData.memo} onChange={e => setEditData({...editData, memo: e.target.value})}
                  className="w-full border rounded-lg p-2 text-sm resize-none focus:outline-none focus:ring-2 focus:ring-pink-300" rows={2} />
              </div>
              <div className="flex gap-2">
                <button onClick={handleSave} disabled={saving}
                  className="bg-pink-600 text-white px-4 py-2 rounded-lg text-sm disabled:opacity-50">
                  {saving ? '保存中...' : '保存する'}
                </button>
                <button onClick={() => setEditing(false)} className="border px-4 py-2 rounded-lg text-sm hover:bg-gray-50">
                  キャンセル
                </button>
              </div>
            </div>
          ) : (
            <div className="space-y-3">
              {post.title && <h2 className="font-bold text-gray-800 text-lg">{post.title}</h2>}
              <p className="text-gray-700 whitespace-pre-wrap text-sm leading-relaxed">
                {post.body || post.caption || '（本文なし）'}
              </p>
              {post.cta && (
                <div className="border-l-4 border-pink-400 pl-3 text-sm text-gray-600">
                  🔗 {post.cta}
                </div>
              )}
              {post.hashtags?.length > 0 && (
                <p className="text-sm text-blue-500">
                  {post.hashtags.map((h: string) => `#${h}`).join(' ')}
                </p>
              )}
              {post.memo && (
                <div className="bg-gray-50 rounded-lg p-3 text-xs text-gray-500">
                  📝 {post.memo}
                </div>
              )}
              <div className="text-xs text-gray-400 pt-2 border-t grid grid-cols-2 gap-1">
                <span>ターゲット: {post.target_segment}</span>
                <span>目的: {post.goal}</span>
                <span>トーン: {post.tone}</span>
              </div>
            </div>
          )}
        </div>
      )}

      {/* ── 素材タブ ── */}
      {tab === 'assets' && (
        <div className="space-y-4">
          {/* 素材生成 */}
          <div className="bg-white rounded-xl border p-5 shadow-sm">
            <h3 className="font-semibold text-gray-700 mb-3 text-sm">素材を生成する</h3>
            <div className="flex flex-wrap gap-3 mb-3">
              <div>
                <label className="block text-xs text-gray-500 mb-1">素材タイプ</label>
                <select value={genAssetType} onChange={e => setGenAssetType(e.target.value as any)}
                  className="border rounded p-1.5 text-sm focus:outline-none">
                  <option value="image_prompt">🎨 画像プロンプト</option>
                  <option value="video_script">🎬 動画台本</option>
                </select>
              </div>
              {genAssetType === 'video_script' && (
                <div>
                  <label className="block text-xs text-gray-500 mb-1">尺</label>
                  <select value={genDuration} onChange={e => setGenDuration(e.target.value)}
                    className="border rounded p-1.5 text-sm focus:outline-none">
                    <option value="15s">15秒</option>
                    <option value="30s">30秒</option>
                    <option value="60s">60秒</option>
                  </select>
                </div>
              )}
              <div className="flex items-end">
                <button onClick={handleGenerateAsset} disabled={genLoading}
                  className="bg-blue-600 text-white px-4 py-1.5 rounded text-sm disabled:opacity-50 hover:bg-blue-700">
                  {genLoading ? '生成中...' : 'AIで生成'}
                </button>
              </div>
            </div>
          </div>

          {/* 素材一覧 */}
          {assets.length === 0 ? (
            <div className="bg-white rounded-xl border p-8 text-center text-gray-400">
              <p className="text-2xl mb-2">🖼️</p>
              <p>素材がありません。上から生成してください。</p>
            </div>
          ) : (
            assets.map(asset => (
              <div key={asset.id} className="bg-white rounded-xl border p-4 shadow-sm">
                <div className="flex items-center gap-2 mb-2">
                  <span className="text-xs bg-blue-100 text-blue-700 px-2 py-0.5 rounded">
                    {asset.asset_type === 'image_prompt' ? '🎨 画像プロンプト' : asset.asset_type === 'video_script' ? '🎬 動画台本' : asset.asset_type}
                  </span>
                  <span className="text-xs text-gray-400">{new Date(asset.created_at).toLocaleDateString('ja-JP')}</span>
                </div>
                {asset.prompt && (
                  <div className="mb-2">
                    <p className="text-xs font-semibold text-gray-600 mb-1">プロンプト（英語）：</p>
                    <p className="text-sm text-gray-700 bg-gray-50 rounded p-2 font-mono text-xs">{asset.prompt}</p>
                  </div>
                )}
                {asset.content && (
                  <div>
                    <p className="text-xs font-semibold text-gray-600 mb-1">
                      {asset.asset_type === 'image_prompt' ? 'ネガティブプロンプト：' : '台本：'}
                    </p>
                    <p className="text-sm text-gray-700 whitespace-pre-wrap">{asset.content}</p>
                  </div>
                )}
                <button
                  onClick={() => navigator.clipboard.writeText(asset.prompt || asset.content || '').then(() => showToast('📋 コピーしました'))}
                  className="mt-2 text-xs border px-2 py-1 rounded hover:bg-gray-50"
                >
                  📋 コピー
                </button>
              </div>
            ))
          )}
        </div>
      )}

      {/* ── 分析タブ ── */}
      {tab === 'analytics' && (
        <div className="space-y-4">
          <div className="bg-white rounded-xl border p-5 shadow-sm">
            <h3 className="font-semibold text-gray-700 mb-4 text-sm">📊 数値を入力する（手動またはAPI）</h3>
            <div className="grid grid-cols-2 sm:grid-cols-3 gap-3 mb-4">
              {[
                ['impressions', 'インプレッション'],
                ['likes', 'いいね'],
                ['comments', 'コメント'],
                ['shares', 'シェア・RT'],
                ['saves', '保存'],
                ['profile_clicks', 'プロフクリック'],
                ['url_clicks', 'URLクリック'],
                ['leads', '無料相談申込'],
                ['conversions', '成約数'],
              ].map(([key, label]) => (
                <div key={key}>
                  <label className="block text-xs text-gray-500 mb-0.5">{label}</label>
                  <input
                    type="number"
                    value={analyticsForm[key] ?? ''}
                    onChange={e => setAnalyticsForm({...analyticsForm, [key]: e.target.value})}
                    className="w-full border rounded p-2 text-sm focus:outline-none focus:ring-2 focus:ring-pink-300"
                    placeholder="0"
                    min={0}
                  />
                </div>
              ))}
            </div>
            <div className="mb-4">
              <label className="block text-xs text-gray-500 mb-0.5">メモ</label>
              <textarea
                value={analyticsForm.memo ?? ''}
                onChange={e => setAnalyticsForm({...analyticsForm, memo: e.target.value})}
                className="w-full border rounded p-2 text-sm focus:outline-none focus:ring-2 focus:ring-pink-300"
                rows={2}
              />
            </div>
            <button onClick={handleSaveAnalytics} disabled={savingAnalytics}
              className="bg-pink-600 text-white px-5 py-2 rounded-lg text-sm disabled:opacity-50 hover:bg-pink-700">
              {savingAnalytics ? '保存・AI分析中...' : '💾 保存してAI改善提案を生成'}
            </button>
          </div>

          {/* AI分析結果 */}
          {analytics?.ai_analysis && (
            <div className="bg-gradient-to-br from-purple-50 to-pink-50 rounded-xl border border-purple-100 p-5 shadow-sm">
              <h3 className="font-semibold text-purple-800 mb-3 text-sm">🤖 AI改善提案</h3>
              <p className="text-sm text-gray-700 whitespace-pre-wrap leading-relaxed">{analytics.ai_analysis}</p>
            </div>
          )}
        </div>
      )}
    </div>
  )
}
