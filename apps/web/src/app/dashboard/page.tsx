'use client'
import { useState, useEffect } from 'react'
import { dashboardApi, youtubeApi, videoJobApi, analysisApi } from '@/lib/api'
import Link from 'next/link'

interface DashboardSummary {
  latest_metrics: {
    week_start_date: string | null
    week_end_date: string | null
    total_views: number
    total_impressions: number
    ctr: number
    avg_view_duration: number
    avg_view_percentage: number
    subscribers_gained: number
    subscribers_lost: number
    total_likes: number
    total_comments: number
    views_change_rate: number
    ctr_change_rate: number
  }
  ai_analysis: {
    summary: string | null
    improvement_points: string | null
    next_theme_suggestions: any[] | null
    analyzed_at: string | null
  } | null
  active_jobs: Array<{
    id: string
    status: string
    progress_percent: number
    current_step: string | null
    created_at: string | null
  }>
  stats: {
    waiting_review_count: number
    youtube_connected: boolean
    channel_title: string | null
  }
}

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

function MetricCard({ label, value, sub, change }: {
  label: string
  value: string | number
  sub?: string
  change?: number | null
}) {
  return (
    <div className="bg-white rounded-xl p-5 shadow-sm border border-gray-100">
      <p className="text-xs text-gray-500 mb-1">{label}</p>
      <p className="text-2xl font-bold text-gray-900">{value}</p>
      {sub && <p className="text-xs text-gray-400 mt-1">{sub}</p>}
      {change !== undefined && change !== null && (
        <p className={`text-xs mt-1 font-medium ${change >= 0 ? 'text-green-600' : 'text-red-600'}`}>
          {change >= 0 ? '▲' : '▼'} {Math.abs(change).toFixed(1)}%（前週比）
        </p>
      )}
    </div>
  )
}

function formatDuration(seconds: number): string {
  const min = Math.floor(seconds / 60)
  const sec = Math.floor(seconds % 60)
  return `${min}:${sec.toString().padStart(2, '0')}`
}

export default function DashboardPage() {
  const [summary, setSummary] = useState<DashboardSummary | null>(null)
  const [loading, setLoading] = useState(true)
  const [syncing, setSyncing] = useState(false)

  useEffect(() => {
    dashboardApi.getSummary()
      .then(res => setSummary(res.data))
      .catch(err => console.error(err))
      .finally(() => setLoading(false))
  }, [])

  const handleSync = async () => {
    setSyncing(true)
    try {
      await youtubeApi.syncWeekly()
      alert('週次データ取得ジョブを開始しました')
    } catch (err: any) {
      alert(err.response?.data?.detail || 'エラーが発生しました')
    } finally {
      setSyncing(false)
    }
  }

  const handleRunAnalysis = async () => {
    try {
      await analysisApi.run()
      alert('AI分析ジョブを開始しました')
    } catch (err: any) {
      alert(err.response?.data?.detail || 'エラーが発生しました')
    }
  }

  const handleStartGeneration = async () => {
    try {
      await videoJobApi.create({})
      alert('動画生成ジョブを開始しました')
    } catch (err: any) {
      alert(err.response?.data?.detail || 'エラーが発生しました')
    }
  }

  if (loading) {
    return (
      <div className="p-8">
        <div className="animate-pulse space-y-4">
          <div className="h-8 bg-gray-200 rounded w-1/3"></div>
          <div className="grid grid-cols-4 gap-4">
            {[...Array(8)].map((_, i) => (
              <div key={i} className="h-24 bg-gray-200 rounded-xl"></div>
            ))}
          </div>
        </div>
      </div>
    )
  }

  const metrics = summary?.latest_metrics

  return (
    <div className="p-8 space-y-8">
      {/* ヘッダー */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">ダッシュボード</h1>
          {metrics?.week_start_date && (
            <p className="text-sm text-gray-500 mt-1">
              集計期間: {metrics.week_start_date} 〜 {metrics.week_end_date}
            </p>
          )}
        </div>
        <div className="flex gap-3">
          {!summary?.stats.youtube_connected && (
            <Link
              href="/dashboard/settings"
              className="bg-yellow-500 hover:bg-yellow-600 text-white px-4 py-2 rounded-lg text-sm font-medium"
            >
              ⚠️ YouTube未連携
            </Link>
          )}
          <button
            onClick={handleSync}
            disabled={syncing}
            className="bg-blue-600 hover:bg-blue-700 disabled:opacity-50 text-white px-4 py-2 rounded-lg text-sm font-medium"
          >
            {syncing ? '取得中...' : '🔄 週次データ取得'}
          </button>
          <button
            onClick={handleRunAnalysis}
            className="bg-purple-600 hover:bg-purple-700 text-white px-4 py-2 rounded-lg text-sm font-medium"
          >
            🤖 AI分析実行
          </button>
          <button
            onClick={handleStartGeneration}
            className="bg-green-600 hover:bg-green-700 text-white px-4 py-2 rounded-lg text-sm font-medium"
          >
            🎬 動画生成開始
          </button>
        </div>
      </div>

      {/* レビュー待ちアラート */}
      {summary?.stats.waiting_review_count && summary.stats.waiting_review_count > 0 ? (
        <div className="bg-amber-50 border border-amber-200 rounded-xl p-4 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <span className="text-2xl">📋</span>
            <div>
              <p className="font-medium text-amber-800">
                {summary.stats.waiting_review_count}件の動画がレビュー待ちです
              </p>
              <p className="text-sm text-amber-600">確認後に公開承認をしてください</p>
            </div>
          </div>
          <Link
            href="/dashboard/jobs?status=waiting_review"
            className="bg-amber-500 hover:bg-amber-600 text-white px-4 py-2 rounded-lg text-sm font-medium"
          >
            レビューへ →
          </Link>
        </div>
      ) : null}

      {/* 週次メトリクス */}
      <section>
        <h2 className="text-lg font-semibold text-gray-700 mb-4">📈 最新週次指標</h2>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <MetricCard
            label="総再生数"
            value={metrics?.total_views?.toLocaleString() ?? '-'}
            change={metrics?.views_change_rate}
          />
          <MetricCard
            label="インプレッション"
            value={metrics?.total_impressions?.toLocaleString() ?? '-'}
          />
          <MetricCard
            label="CTR"
            value={metrics?.ctr ? `${metrics.ctr.toFixed(2)}%` : '-'}
            change={metrics?.ctr_change_rate}
          />
          <MetricCard
            label="平均視聴時間"
            value={metrics?.avg_view_duration ? formatDuration(metrics.avg_view_duration) : '-'}
          />
          <MetricCard
            label="視聴維持率"
            value={metrics?.avg_view_percentage ? `${metrics.avg_view_percentage.toFixed(1)}%` : '-'}
          />
          <MetricCard
            label="登録者増減"
            value={metrics?.subscribers_gained !== undefined ? `+${metrics.subscribers_gained}` : '-'}
            sub={metrics?.subscribers_lost ? `(減: ${metrics.subscribers_lost})` : undefined}
          />
          <MetricCard
            label="高評価数"
            value={metrics?.total_likes?.toLocaleString() ?? '-'}
          />
          <MetricCard
            label="コメント数"
            value={metrics?.total_comments?.toLocaleString() ?? '-'}
          />
        </div>
      </section>

      {/* AI分析サマリー */}
      {summary?.ai_analysis && (
        <section>
          <h2 className="text-lg font-semibold text-gray-700 mb-4">🤖 AI分析サマリー</h2>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="bg-white rounded-xl p-6 shadow-sm border border-gray-100">
              <h3 className="font-medium text-gray-700 mb-3">📝 今週のまとめ</h3>
              <p className="text-sm text-gray-600 leading-relaxed">
                {summary.ai_analysis.summary || '分析データがありません'}
              </p>
              {summary.ai_analysis.analyzed_at && (
                <p className="text-xs text-gray-400 mt-3">
                  分析日時: {new Date(summary.ai_analysis.analyzed_at).toLocaleString('ja-JP')}
                </p>
              )}
            </div>
            <div className="bg-white rounded-xl p-6 shadow-sm border border-gray-100">
              <h3 className="font-medium text-gray-700 mb-3">💡 次回動画への改善提案</h3>
              <p className="text-sm text-gray-600 leading-relaxed">
                {summary.ai_analysis.improvement_points || '改善提案がありません'}
              </p>
            </div>
          </div>

          {summary.ai_analysis.next_theme_suggestions && summary.ai_analysis.next_theme_suggestions.length > 0 && (
            <div className="bg-white rounded-xl p-6 shadow-sm border border-gray-100 mt-4">
              <h3 className="font-medium text-gray-700 mb-3">🎯 次回テーマ候補</h3>
              <div className="space-y-2">
                {summary.ai_analysis.next_theme_suggestions.slice(0, 3).map((theme: any, i: number) => (
                  <div key={i} className="flex items-start gap-3 p-3 bg-purple-50 rounded-lg">
                    <span className="text-purple-600 font-bold text-sm">{i + 1}</span>
                    <div>
                      <p className="text-sm font-medium text-gray-800">{theme.title}</p>
                      <p className="text-xs text-gray-500 mt-1">{theme.reason}</p>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </section>
      )}

      {/* 進行中のジョブ */}
      {summary?.active_jobs && summary.active_jobs.length > 0 && (
        <section>
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-lg font-semibold text-gray-700">🔄 進行中のジョブ</h2>
            <Link
              href="/dashboard/jobs"
              className="text-purple-600 hover:underline text-sm"
            >
              すべて見る →
            </Link>
          </div>
          <div className="space-y-3">
            {summary.active_jobs.map(job => (
              <div
                key={job.id}
                className="bg-white rounded-xl p-4 shadow-sm border border-gray-100 flex items-center gap-4"
              >
                <div className="flex-1">
                  <div className="flex items-center gap-2 mb-2">
                    <span className={`status-badge ${statusColors[job.status] || 'bg-gray-100 text-gray-700'}`}>
                      {statusLabels[job.status] || job.status}
                    </span>
                    <span className="text-xs text-gray-400">{job.current_step}</span>
                  </div>
                  <div className="w-full bg-gray-200 rounded-full h-2">
                    <div
                      className="bg-purple-500 h-2 rounded-full transition-all"
                      style={{ width: `${job.progress_percent}%` }}
                    ></div>
                  </div>
                  <p className="text-xs text-gray-400 mt-1">{job.progress_percent}%</p>
                </div>
                <Link
                  href={`/dashboard/jobs/${job.id}`}
                  className="text-gray-400 hover:text-gray-700"
                >
                  →
                </Link>
              </div>
            ))}
          </div>
        </section>
      )}

      {/* クイックリンク */}
      <section>
        <h2 className="text-lg font-semibold text-gray-700 mb-4">🚀 クイックアクション</h2>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          {[
            { href: '/dashboard/weekly', label: '週次データを見る', icon: '📅', color: 'bg-blue-50 hover:bg-blue-100 text-blue-700' },
            { href: '/dashboard/characters', label: 'キャラクター設定', icon: '🎭', color: 'bg-purple-50 hover:bg-purple-100 text-purple-700' },
            { href: '/dashboard/themes', label: 'テーマ設定', icon: '🎯', color: 'bg-green-50 hover:bg-green-100 text-green-700' },
            { href: '/dashboard/analysis', label: 'AI分析レポート', icon: '🤖', color: 'bg-pink-50 hover:bg-pink-100 text-pink-700' },
          ].map(item => (
            <Link
              key={item.href}
              href={item.href}
              className={`${item.color} rounded-xl p-4 flex items-center gap-3 transition-colors`}
            >
              <span className="text-2xl">{item.icon}</span>
              <span className="text-sm font-medium">{item.label}</span>
            </Link>
          ))}
        </div>
      </section>
    </div>
  )
}
