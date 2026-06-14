'use client'
import { useState, useEffect } from 'react'
import { useParams } from 'next/navigation'
import { reviewApi } from '@/lib/api'

export default function ReviewPage() {
  const params = useParams()
  const videoId = params.videoId as string
  const [data, setData] = useState<any>(null)
  const [loading, setLoading] = useState(true)
  const [checklist, setChecklist] = useState({
    no_factual_errors: false,
    no_inappropriate_content: false,
    matches_character: false,
    video_coherent: false,
    voice_ok: false,
    subtitle_ok: false,
    revision_request: '',
    reviewer_notes: '',
  })
  const [revisionReason, setRevisionReason] = useState('')
  const [saving, setSaving] = useState(false)
  const [approving, setApproving] = useState(false)
  const [publishing, setPublishing] = useState(false)

  useEffect(() => {
    fetchReview()
  }, [videoId])

  const fetchReview = async () => {
    try {
      const res = await reviewApi.get(videoId)
      setData(res.data)
      if (res.data.checklist) {
        setChecklist({
          no_factual_errors: res.data.checklist.no_factual_errors || false,
          no_inappropriate_content: res.data.checklist.no_inappropriate_content || false,
          matches_character: res.data.checklist.matches_character || false,
          video_coherent: res.data.checklist.video_coherent || false,
          voice_ok: res.data.checklist.voice_ok || false,
          subtitle_ok: res.data.checklist.subtitle_ok || false,
          revision_request: res.data.checklist.revision_request || '',
          reviewer_notes: res.data.checklist.reviewer_notes || '',
        })
      }
    } catch (err) {
      console.error(err)
    } finally {
      setLoading(false)
    }
  }

  const handleSaveChecklist = async () => {
    setSaving(true)
    try {
      await reviewApi.updateChecklist(videoId, checklist)
      alert('チェックリストを保存しました')
    } catch (err: any) {
      alert(err.response?.data?.detail || 'エラーが発生しました')
    } finally {
      setSaving(false)
    }
  }

  const handleRegenerate = async () => {
    if (!revisionReason.trim()) {
      alert('修正依頼の内容を入力してください')
      return
    }
    if (!confirm('再生成を依頼しますか？現在の動画は上書きされます。')) return
    try {
      await reviewApi.requestRegenerate(videoId, revisionReason)
      alert('再生成を依頼しました')
    } catch (err: any) {
      alert(err.response?.data?.detail || 'エラーが発生しました')
    }
  }

  const handleApprove = async () => {
    if (!confirm('この動画を承認しますか？承認後は公開ボタンが有効になります。')) return
    setApproving(true)
    try {
      await reviewApi.approve(videoId)
      alert('承認しました。「公開」ボタンで公開できます。')
      fetchReview()
    } catch (err: any) {
      alert(err.response?.data?.detail || 'エラーが発生しました')
    } finally {
      setApproving(false)
    }
  }

  const handlePublish = async () => {
    if (!confirm('⚠️ この動画をYouTubeで公開しますか？\n公開すると誰でも視聴できるようになります。')) return
    if (!confirm('最終確認: YouTube公開を実行してよろしいですか？')) return
    setPublishing(true)
    try {
      await reviewApi.publish(videoId)
      alert('✅ YouTubeで公開しました！')
      fetchReview()
    } catch (err: any) {
      alert(err.response?.data?.detail || 'エラーが発生しました')
    } finally {
      setPublishing(false)
    }
  }

  const allChecked = Object.entries(checklist)
    .filter(([key]) => key !== 'revision_request' && key !== 'reviewer_notes')
    .every(([, val]) => val === true)

  if (loading) return <div className="p-8 text-gray-400">読み込み中...</div>
  if (!data) return <div className="p-8 text-red-500">動画が見つかりません</div>

  const { video, youtube_upload, approval } = data
  const isApproved = approval?.status === 'approved'
  const isPublished = youtube_upload?.privacy_status === 'public'

  return (
    <div className="p-8 max-w-5xl">
      <h1 className="text-2xl font-bold text-gray-900 mb-6">📋 動画レビュー</h1>

      {/* ステータスバナー */}
      {isPublished ? (
        <div className="bg-emerald-50 border border-emerald-200 rounded-xl p-4 mb-6">
          <p className="text-emerald-700 font-medium">✅ この動画は公開済みです</p>
          {youtube_upload?.youtube_url && (
            <a href={youtube_upload.youtube_url} target="_blank" rel="noopener noreferrer"
               className="text-sm text-emerald-600 hover:underline">
              YouTube で見る →
            </a>
          )}
        </div>
      ) : isApproved ? (
        <div className="bg-green-50 border border-green-200 rounded-xl p-4 mb-6">
          <p className="text-green-700 font-medium">✅ 承認済み - 公開ボタンが有効です</p>
        </div>
      ) : (
        <div className="bg-amber-50 border border-amber-200 rounded-xl p-4 mb-6">
          <p className="text-amber-700 font-medium">⏳ レビュー待ち - チェックリストを確認してください</p>
        </div>
      )}

      <div className="grid grid-cols-3 gap-6">
        {/* 左: 動画プレビュー */}
        <div className="col-span-2 space-y-4">
          {/* 動画プレビュー */}
          {video?.file_url ? (
            <div className="bg-black rounded-xl overflow-hidden">
              <video
                src={video.file_url}
                controls
                className="w-full aspect-video"
              />
            </div>
          ) : youtube_upload?.youtube_url ? (
            <div className="bg-gray-900 rounded-xl p-4 text-center">
              <a
                href={youtube_upload.youtube_url}
                target="_blank"
                rel="noopener noreferrer"
                className="text-white hover:text-blue-300"
              >
                🎥 YouTubeで確認する →
              </a>
            </div>
          ) : (
            <div className="bg-gray-200 rounded-xl aspect-video flex items-center justify-center">
              <span className="text-gray-400">動画プレビューなし</span>
            </div>
          )}

          {/* 動画情報 */}
          <div className="bg-white rounded-xl p-5 shadow-sm border border-gray-100">
            <h2 className="font-bold text-gray-800 text-lg mb-2">{video?.title}</h2>
            <pre className="text-xs text-gray-500 whitespace-pre-wrap leading-relaxed">
              {video?.description}
            </pre>
            {video?.tags?.length > 0 && (
              <div className="flex flex-wrap gap-1 mt-3">
                {video.tags.map((tag: string) => (
                  <span key={tag} className="bg-gray-100 text-gray-600 text-xs px-2 py-0.5 rounded">
                    #{tag}
                  </span>
                ))}
              </div>
            )}
          </div>

          {/* YouTube情報 */}
          {youtube_upload && (
            <div className="bg-white rounded-xl p-5 shadow-sm border border-gray-100">
              <h3 className="font-medium text-gray-700 mb-2">📺 YouTube情報</h3>
              <div className="space-y-1 text-sm text-gray-600">
                <p>動画ID: {youtube_upload.youtube_video_id || '未アップロード'}</p>
                <p>公開状態: {
                  youtube_upload.privacy_status === 'public' ? '🌍 公開' :
                  youtube_upload.privacy_status === 'unlisted' ? '🔒 限定公開' : '⏳ 未設定'
                }</p>
                {youtube_upload.youtube_url && (
                  <a href={youtube_upload.youtube_url} target="_blank" className="text-blue-500 hover:underline text-sm">
                    {youtube_upload.youtube_url}
                  </a>
                )}
              </div>
            </div>
          )}

          {/* 修正依頼 */}
          {!isPublished && (
            <div className="bg-white rounded-xl p-5 shadow-sm border border-gray-100">
              <h3 className="font-medium text-gray-700 mb-3">🔄 再生成依頼</h3>
              <textarea
                value={revisionReason}
                onChange={e => setRevisionReason(e.target.value)}
                rows={3}
                className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-orange-400"
                placeholder="修正したい点を入力してください"
              />
              <button
                onClick={handleRegenerate}
                className="mt-2 bg-orange-100 hover:bg-orange-200 text-orange-700 px-4 py-2 rounded-lg text-sm font-medium"
              >
                🔄 再生成を依頼する
              </button>
            </div>
          )}
        </div>

        {/* 右: チェックリスト */}
        <div className="space-y-4">
          <div className="bg-white rounded-xl p-5 shadow-sm border border-gray-100">
            <h3 className="font-medium text-gray-700 mb-4">✅ チェックリスト</h3>
            <div className="space-y-3">
              {[
                { key: 'no_factual_errors', label: '事実誤認がない' },
                { key: 'no_inappropriate_content', label: '不適切表現がない' },
                { key: 'matches_character', label: 'キャラクター設定に合っている' },
                { key: 'video_coherent', label: '動画として破綻していない' },
                { key: 'voice_ok', label: '音声が問題ない' },
                { key: 'subtitle_ok', label: '字幕が問題ない' },
              ].map(item => (
                <label key={item.key} className="flex items-center gap-3 cursor-pointer group">
                  <input
                    type="checkbox"
                    checked={(checklist as any)[item.key]}
                    onChange={e => setChecklist({ ...checklist, [item.key]: e.target.checked })}
                    disabled={isPublished}
                    className="w-4 h-4 rounded accent-purple-500"
                  />
                  <span className={`text-sm ${(checklist as any)[item.key] ? 'text-gray-800 line-through' : 'text-gray-600'}`}>
                    {item.label}
                  </span>
                </label>
              ))}
            </div>

            <textarea
              value={checklist.reviewer_notes}
              onChange={e => setChecklist({ ...checklist, reviewer_notes: e.target.value })}
              rows={3}
              disabled={isPublished}
              className="w-full mt-4 border border-gray-300 rounded-lg px-3 py-2 text-xs outline-none focus:ring-2 focus:ring-purple-400"
              placeholder="レビューメモ（任意）"
            />

            {!isPublished && (
              <button
                onClick={handleSaveChecklist}
                disabled={saving}
                className="w-full mt-3 bg-gray-100 hover:bg-gray-200 text-gray-700 py-2 rounded-lg text-sm"
              >
                {saving ? '保存中...' : '保存'}
              </button>
            )}
          </div>

          {/* 承認・公開ボタン */}
          {!isPublished && (
            <div className="space-y-3">
              {!isApproved && (
                <button
                  onClick={handleApprove}
                  disabled={approving || !allChecked}
                  className="w-full bg-green-600 hover:bg-green-700 disabled:opacity-50 disabled:cursor-not-allowed text-white py-3 rounded-xl text-sm font-bold"
                >
                  {approving ? '承認中...' : '✅ 承認する'}
                </button>
              )}

              {!allChecked && !isApproved && (
                <p className="text-xs text-gray-400 text-center">
                  すべての項目にチェックが必要です
                </p>
              )}

              {isApproved && !isPublished && (
                <button
                  onClick={handlePublish}
                  disabled={publishing}
                  className="w-full bg-red-600 hover:bg-red-700 disabled:opacity-50 text-white py-3 rounded-xl text-sm font-bold"
                >
                  {publishing ? '公開中...' : '🌍 YouTubeに公開する'}
                </button>
              )}

              {isApproved && (
                <p className="text-xs text-amber-600 text-center bg-amber-50 p-2 rounded">
                  ⚠️ 公開すると誰でも視聴できます
                </p>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
