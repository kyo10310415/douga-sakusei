'use client'
import { useState, useEffect } from 'react'
import { analysisApi } from '@/lib/api'

export default function AnalysisPage() {
  const [reports, setReports] = useState<any[]>([])
  const [loading, setLoading] = useState(true)
  const [selectedReport, setSelectedReport] = useState<any | null>(null)
  const [running, setRunning] = useState(false)

  useEffect(() => {
    fetchReports()
  }, [])

  const fetchReports = async () => {
    try {
      const res = await analysisApi.getReports()
      setReports(res.data)
      if (res.data.length > 0) setSelectedReport(res.data[0])
    } catch (err) {
      console.error(err)
    } finally {
      setLoading(false)
    }
  }

  const handleRunAnalysis = async () => {
    setRunning(true)
    try {
      await analysisApi.run()
      alert('AI分析ジョブを開始しました。完了後に結果が表示されます。')
      setTimeout(fetchReports, 3000)
    } catch (err: any) {
      alert(err.response?.data?.detail || 'エラーが発生しました')
    } finally {
      setRunning(false)
    }
  }

  if (loading) return <div className="p-8 text-gray-400">読み込み中...</div>

  return (
    <div className="p-8">
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold text-gray-900">🤖 AI分析レポート</h1>
        <button
          onClick={handleRunAnalysis}
          disabled={running}
          className="bg-purple-600 hover:bg-purple-700 disabled:opacity-50 text-white px-4 py-2 rounded-lg text-sm font-medium"
        >
          {running ? '分析実行中...' : '🤖 分析を実行'}
        </button>
      </div>

      {reports.length === 0 ? (
        <div className="text-center py-16 bg-white rounded-xl border border-gray-100">
          <div className="text-5xl mb-4">🤖</div>
          <p className="text-gray-500">分析レポートがありません</p>
          <p className="text-sm text-gray-400 mt-2">YouTube連携後に分析を実行してください</p>
        </div>
      ) : (
        <div className="flex gap-6">
          {/* レポートリスト */}
          <div className="w-64 flex-shrink-0">
            <div className="bg-white rounded-xl shadow-sm border border-gray-100 overflow-hidden">
              {reports.map(report => (
                <button
                  key={report.id}
                  onClick={() => setSelectedReport(report)}
                  className={`w-full text-left px-4 py-3 border-b border-gray-50 hover:bg-gray-50 ${
                    selectedReport?.id === report.id ? 'bg-purple-50 border-l-2 border-l-purple-500' : ''
                  }`}
                >
                  <p className="text-xs font-medium text-gray-700">
                    {report.analyzed_at ? new Date(report.analyzed_at).toLocaleDateString('ja-JP') : '未分析'}
                  </p>
                  <p className="text-xs text-gray-400 mt-0.5">
                    {report.status === 'completed' ? '✅ 完了' :
                     report.status === 'running' ? '🔄 実行中' :
                     report.status === 'failed' ? '❌ 失敗' : '⏳ 待機中'}
                  </p>
                </button>
              ))}
            </div>
          </div>

          {/* レポート詳細 */}
          {selectedReport && (
            <div className="flex-1 space-y-4">
              <div className="bg-white rounded-xl p-6 shadow-sm border border-gray-100">
                <h2 className="font-bold text-gray-800 mb-3">📝 分析サマリー</h2>
                <p className="text-sm text-gray-600 leading-relaxed">
                  {selectedReport.summary || '分析データがありません'}
                </p>
              </div>

              <div className="grid grid-cols-2 gap-4">
                {[
                  { key: 'trending_video_patterns', icon: '🔥', title: '伸びた動画の共通点' },
                  { key: 'declining_video_patterns', icon: '📉', title: '伸びなかった動画の共通点' },
                  { key: 'high_ctr_title_patterns', icon: '🎯', title: 'CTRが高いタイトル傾向' },
                  { key: 'high_retention_patterns', icon: '⏱', title: '視聴維持率が高い構成' },
                  { key: 'drop_off_factors', icon: '⚠️', title: '離脱が起きやすい要素' },
                  { key: 'improvement_points', icon: '💡', title: '次回改善ポイント' },
                ].map(item => (
                  <div key={item.key} className="bg-white rounded-xl p-5 shadow-sm border border-gray-100">
                    <h3 className="font-medium text-gray-700 mb-2 flex items-center gap-2">
                      <span>{item.icon}</span>
                      <span className="text-sm">{item.title}</span>
                    </h3>
                    <p className="text-xs text-gray-600 leading-relaxed">
                      {selectedReport[item.key] || '-'}
                    </p>
                  </div>
                ))}
              </div>

              {/* 次回テーマ候補 */}
              {selectedReport.next_theme_suggestions?.length > 0 && (
                <div className="bg-white rounded-xl p-6 shadow-sm border border-gray-100">
                  <h2 className="font-bold text-gray-800 mb-3">🎯 次回テーマ候補</h2>
                  <div className="space-y-3">
                    {selectedReport.next_theme_suggestions.map((theme: any, i: number) => (
                      <div key={i} className="flex items-start gap-3 p-3 bg-purple-50 rounded-lg">
                        <span className="font-bold text-purple-700">{i + 1}</span>
                        <div>
                          <p className="text-sm font-medium text-gray-800">{theme.title}</p>
                          <p className="text-xs text-gray-500 mt-1">{theme.reason}</p>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* タイトル候補 */}
              {selectedReport.next_title_suggestions?.length > 0 && (
                <div className="bg-white rounded-xl p-6 shadow-sm border border-gray-100">
                  <h2 className="font-bold text-gray-800 mb-3">📌 次回タイトル候補</h2>
                  <div className="space-y-2">
                    {selectedReport.next_title_suggestions.map((title: string, i: number) => (
                      <div key={i} className="flex items-center gap-2 p-2 bg-gray-50 rounded">
                        <span className="text-xs text-gray-400 w-4">{i + 1}</span>
                        <p className="text-sm text-gray-700">{title}</p>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* 台本方針 */}
              {selectedReport.next_script_policy && (
                <div className="bg-white rounded-xl p-6 shadow-sm border border-gray-100">
                  <h2 className="font-bold text-gray-800 mb-3">📖 次回台本方針</h2>
                  <p className="text-sm text-gray-600 leading-relaxed">
                    {selectedReport.next_script_policy}
                  </p>
                </div>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  )
}
