'use client'
import { useState, useEffect } from 'react'
import { videoJobApi } from '@/lib/api'
import Link from 'next/link'
import { useSearchParams } from 'next/navigation'

const statusLabels: Record<string, string> = {
  pending: '待機中',
  analyzing: '分析中',
  planning: '企画生成中',
  scripting: '台本生成中',
  generating_voice: '音声生成中',
  generating_assets: '素材生成中',
  rendering: 'レンダリング中',
  uploading: 'アップロード中',
  waiting_review: 'レビュー待ち',
  approved: '承認済み',
  published: '公開済み',
  failed: '失敗',
}

const statusColors: Record<string, string> = {
  pending: 'bg-gray-100 text-gray-700',
  analyzing: 'bg-blue-100 text-blue-700',
  planning: 'bg-indigo-100 text-indigo-700',
  scripting: 'bg-purple-100 text-purple-700',
  generating_voice: 'bg-pink-100 text-pink-700',
  generating_assets: 'bg-yellow-100 text-yellow-700',
  rendering: 'bg-orange-100 text-orange-700',
  uploading: 'bg-cyan-100 text-cyan-700',
  waiting_review: 'bg-amber-100 text-amber-700',
  approved: 'bg-green-100 text-green-700',
  published: 'bg-emerald-100 text-emerald-700',
  failed: 'bg-red-100 text-red-700',
}

export default function JobsPage() {
  const [jobs, setJobs] = useState<any[]>([])
  const [loading, setLoading] = useState(true)
  const [filter, setFilter] = useState<string>('')
  const searchParams = useSearchParams()

  useEffect(() => {
    const statusParam = searchParams.get('status') || ''
    setFilter(statusParam)
  }, [searchParams])

  useEffect(() => {
    videoJobApi.list(50, filter || undefined)
      .then(res => setJobs(res.data))
      .catch(console.error)
      .finally(() => setLoading(false))
  }, [filter])

  const handleRetry = async (jobId: string) => {
    try {
      await videoJobApi.retry(jobId)
      alert('再実行を開始しました')
      location.reload()
    } catch (err: any) {
      alert(err.response?.data?.detail || 'エラーが発生しました')
    }
  }

  const handleCancel = async (jobId: string) => {
    if (!confirm('このジョブをキャンセルしますか？')) return
    try {
      await videoJobApi.cancel(jobId)
      location.reload()
    } catch (err: any) {
      alert(err.response?.data?.detail || 'エラーが発生しました')
    }
  }

  return (
    <div className="p-8">
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold text-gray-900">🎬 動画生成ジョブ</h1>
        <Link
          href="/dashboard"
          className="bg-green-600 hover:bg-green-700 text-white px-4 py-2 rounded-lg text-sm font-medium"
          onClick={async (e) => {
            e.preventDefault()
            try {
              await videoJobApi.create({})
              alert('動画生成ジョブを開始しました')
              location.reload()
            } catch (err: any) {
              alert(err.response?.data?.detail || 'エラーが発生しました')
            }
          }}
        >
          ＋ 新しいジョブを作成
        </Link>
      </div>

      {/* ステータスフィルター */}
      <div className="flex gap-2 mb-6 flex-wrap">
        <button
          onClick={() => setFilter('')}
          className={`px-3 py-1.5 rounded-full text-xs font-medium border ${
            filter === '' ? 'bg-gray-800 text-white border-gray-800' : 'bg-white text-gray-600 border-gray-200 hover:border-gray-400'
          }`}
        >
          すべて
        </button>
        {Object.entries(statusLabels).map(([key, label]) => (
          <button
            key={key}
            onClick={() => setFilter(key)}
            className={`px-3 py-1.5 rounded-full text-xs font-medium border ${
              filter === key
                ? 'bg-gray-800 text-white border-gray-800'
                : 'bg-white text-gray-600 border-gray-200 hover:border-gray-400'
            }`}
          >
            {label}
          </button>
        ))}
      </div>

      {loading ? (
        <div className="space-y-3">
          {[...Array(5)].map((_, i) => (
            <div key={i} className="h-24 bg-gray-200 rounded-xl animate-pulse"></div>
          ))}
        </div>
      ) : jobs.length === 0 ? (
        <div className="text-center py-16 text-gray-400">
          <div className="text-5xl mb-4">🎬</div>
          <p>ジョブがありません</p>
          <p className="text-sm mt-2">ダッシュボードから動画生成を開始してください</p>
        </div>
      ) : (
        <div className="space-y-4">
          {jobs.map(job => (
            <div key={job.id} className="bg-white rounded-xl p-5 shadow-sm border border-gray-100">
              <div className="flex items-start justify-between gap-4">
                <div className="flex-1">
                  <div className="flex items-center gap-3 mb-3">
                    <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${statusColors[job.status] || 'bg-gray-100 text-gray-700'}`}>
                      {statusLabels[job.status] || job.status}
                    </span>
                    {job.current_step && (
                      <span className="text-xs text-gray-500">{job.current_step}</span>
                    )}
                    <span className="text-xs text-gray-400">ID: {job.id.slice(0, 8)}...</span>
                  </div>

                  {/* プログレスバー */}
                  <div className="w-full bg-gray-200 rounded-full h-2 mb-2">
                    <div
                      className={`h-2 rounded-full transition-all ${
                        job.status === 'failed' ? 'bg-red-500' :
                        job.status === 'published' ? 'bg-emerald-500' : 'bg-purple-500'
                      }`}
                      style={{ width: `${job.progress_percent}%` }}
                    ></div>
                  </div>
                  <p className="text-xs text-gray-400">{job.progress_percent}% 完了</p>

                  {/* エラー表示 */}
                  {job.error_message && (
                    <div className="mt-3 bg-red-50 border border-red-200 rounded p-3">
                      <p className="text-xs text-red-700 font-medium">エラー:</p>
                      <p className="text-xs text-red-600 mt-1">{job.error_message}</p>
                    </div>
                  )}

                  {/* 動画URLと日時 */}
                  <div className="flex items-center gap-4 mt-3 text-xs text-gray-400">
                    {job.created_at && (
                      <span>作成: {new Date(job.created_at).toLocaleString('ja-JP')}</span>
                    )}
                    {job.completed_at && (
                      <span>完了: {new Date(job.completed_at).toLocaleString('ja-JP')}</span>
                    )}
                    {job.retry_count > 0 && (
                      <span className="text-yellow-600">リトライ: {job.retry_count}/{job.max_retries}</span>
                    )}
                  </div>
                </div>

                {/* アクションボタン */}
                <div className="flex flex-col gap-2">
                  <Link
                    href={`/dashboard/jobs/${job.id}`}
                    className="bg-gray-100 hover:bg-gray-200 text-gray-700 px-3 py-1.5 rounded-lg text-xs font-medium text-center"
                  >
                    詳細
                  </Link>

                  {job.status === 'waiting_review' && (
                    <Link
                      href={`/dashboard/review/${job.id}`}
                      className="bg-amber-500 hover:bg-amber-600 text-white px-3 py-1.5 rounded-lg text-xs font-medium text-center"
                    >
                      レビュー
                    </Link>
                  )}

                  {job.status === 'failed' && job.retry_count < job.max_retries && (
                    <button
                      onClick={() => handleRetry(job.id)}
                      className="bg-blue-500 hover:bg-blue-600 text-white px-3 py-1.5 rounded-lg text-xs font-medium"
                    >
                      再実行
                    </button>
                  )}

                  {!['published', 'approved', 'waiting_review'].includes(job.status) && (
                    <button
                      onClick={() => handleCancel(job.id)}
                      className="bg-red-100 hover:bg-red-200 text-red-700 px-3 py-1.5 rounded-lg text-xs font-medium"
                    >
                      キャンセル
                    </button>
                  )}
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
