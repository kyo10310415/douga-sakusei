'use client'
import { useState, useEffect } from 'react'
import { youtubeApi } from '@/lib/api'
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip,
  ResponsiveContainer, BarChart, Bar, Legend
} from 'recharts'

export default function WeeklyDataPage() {
  const [metrics, setMetrics] = useState<any[]>([])
  const [videos, setVideos] = useState<any[]>([])
  const [loading, setLoading] = useState(true)
  const [activeTab, setActiveTab] = useState<'overview' | 'videos'>('overview')

  useEffect(() => {
    Promise.all([
      youtubeApi.getWeeklyMetrics(12),
      youtubeApi.getVideos(20),
    ]).then(([m, v]) => {
      setMetrics(m.data.reverse())
      setVideos(v.data)
    }).catch(console.error).finally(() => setLoading(false))
  }, [])

  const chartData = metrics.map(m => ({
    week: m.week_start_date ? m.week_start_date.slice(5) : '',
    再生数: m.total_views,
    CTR: m.ctr ? parseFloat(m.ctr.toFixed(2)) : 0,
    登録者増加: m.subscribers_gained || 0,
    高評価: m.total_likes || 0,
  }))

  const sortedByViews = [...videos].sort((a, b) => (b.views || 0) - (a.views || 0))
  const topVideos = sortedByViews.slice(0, 5)
  const bottomVideos = sortedByViews.slice(-5).reverse()

  if (loading) return <div className="p-8 text-gray-400">読み込み中...</div>

  return (
    <div className="p-8">
      <h1 className="text-2xl font-bold text-gray-900 mb-6">📅 週次データ</h1>

      {metrics.length === 0 ? (
        <div className="text-center py-16 bg-white rounded-xl border border-gray-100">
          <div className="text-5xl mb-4">📊</div>
          <p className="text-gray-500">週次データがありません</p>
          <p className="text-sm text-gray-400 mt-2">YouTube連携後、データ取得を実行してください</p>
        </div>
      ) : (
        <>
          {/* タブ */}
          <div className="flex gap-2 mb-6">
            {(['overview', 'videos'] as const).map(tab => (
              <button
                key={tab}
                onClick={() => setActiveTab(tab)}
                className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
                  activeTab === tab
                    ? 'bg-blue-600 text-white'
                    : 'bg-white text-gray-600 hover:bg-gray-50 border border-gray-200'
                }`}
              >
                {tab === 'overview' ? '週次推移' : '動画別分析'}
              </button>
            ))}
          </div>

          {activeTab === 'overview' && (
            <div className="space-y-6">
              {/* 再生数推移 */}
              <div className="bg-white rounded-xl p-6 shadow-sm border border-gray-100">
                <h2 className="font-semibold text-gray-700 mb-4">再生数 週次推移</h2>
                <ResponsiveContainer width="100%" height={250}>
                  <LineChart data={chartData}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
                    <XAxis dataKey="week" tick={{ fontSize: 12 }} />
                    <YAxis tick={{ fontSize: 12 }} />
                    <Tooltip />
                    <Line type="monotone" dataKey="再生数" stroke="#7c3aed" strokeWidth={2} dot={false} />
                  </LineChart>
                </ResponsiveContainer>
              </div>

              {/* CTR推移 */}
              <div className="bg-white rounded-xl p-6 shadow-sm border border-gray-100">
                <h2 className="font-semibold text-gray-700 mb-4">CTR推移 (%)</h2>
                <ResponsiveContainer width="100%" height={200}>
                  <LineChart data={chartData}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
                    <XAxis dataKey="week" tick={{ fontSize: 12 }} />
                    <YAxis tick={{ fontSize: 12 }} />
                    <Tooltip />
                    <Line type="monotone" dataKey="CTR" stroke="#ec4899" strokeWidth={2} dot={false} />
                  </LineChart>
                </ResponsiveContainer>
              </div>

              {/* 登録者増加 */}
              <div className="bg-white rounded-xl p-6 shadow-sm border border-gray-100">
                <h2 className="font-semibold text-gray-700 mb-4">登録者増加 推移</h2>
                <ResponsiveContainer width="100%" height={200}>
                  <BarChart data={chartData}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
                    <XAxis dataKey="week" tick={{ fontSize: 12 }} />
                    <YAxis tick={{ fontSize: 12 }} />
                    <Tooltip />
                    <Bar dataKey="登録者増加" fill="#10b981" />
                  </BarChart>
                </ResponsiveContainer>
              </div>

              {/* データテーブル */}
              <div className="bg-white rounded-xl shadow-sm border border-gray-100 overflow-hidden">
                <table className="w-full text-sm">
                  <thead className="bg-gray-50">
                    <tr>
                      <th className="px-4 py-3 text-left text-gray-600">期間</th>
                      <th className="px-4 py-3 text-right text-gray-600">再生数</th>
                      <th className="px-4 py-3 text-right text-gray-600">CTR</th>
                      <th className="px-4 py-3 text-right text-gray-600">登録者増</th>
                      <th className="px-4 py-3 text-right text-gray-600">前週比</th>
                    </tr>
                  </thead>
                  <tbody>
                    {[...metrics].reverse().map(m => (
                      <tr key={m.id} className="border-t border-gray-50 hover:bg-gray-50">
                        <td className="px-4 py-3 text-gray-700">{m.week_start_date} 〜 {m.week_end_date}</td>
                        <td className="px-4 py-3 text-right text-gray-700">{m.total_views?.toLocaleString()}</td>
                        <td className="px-4 py-3 text-right text-gray-700">{m.ctr ? `${m.ctr.toFixed(2)}%` : '-'}</td>
                        <td className="px-4 py-3 text-right text-gray-700">+{m.subscribers_gained || 0}</td>
                        <td className={`px-4 py-3 text-right font-medium ${
                          (m.views_change_rate || 0) >= 0 ? 'text-green-600' : 'text-red-600'
                        }`}>
                          {m.views_change_rate !== null ? `${m.views_change_rate >= 0 ? '+' : ''}${m.views_change_rate?.toFixed(1)}%` : '-'}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}

          {activeTab === 'videos' && (
            <div className="space-y-6">
              {/* 伸びた動画 */}
              <div className="bg-white rounded-xl p-6 shadow-sm border border-gray-100">
                <h2 className="font-semibold text-gray-700 mb-4">🔥 伸びた動画 TOP5</h2>
                <div className="space-y-3">
                  {topVideos.map((v, i) => (
                    <div key={v.id} className="flex items-start gap-3 p-3 rounded-lg hover:bg-gray-50">
                      <span className="font-bold text-gray-400 text-sm w-5">{i + 1}</span>
                      {v.thumbnail_url && (
                        <img src={v.thumbnail_url} alt="" className="w-24 h-14 object-cover rounded" />
                      )}
                      <div className="flex-1">
                        <p className="text-sm font-medium text-gray-800 line-clamp-2">{v.title}</p>
                        <div className="flex gap-3 mt-1 text-xs text-gray-500">
                          <span>👁 {v.views?.toLocaleString()}</span>
                          <span>CTR: {v.ctr ? `${v.ctr.toFixed(1)}%` : '-'}</span>
                          <span>👍 {v.likes}</span>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              </div>

              {/* 伸びなかった動画 */}
              <div className="bg-white rounded-xl p-6 shadow-sm border border-gray-100">
                <h2 className="font-semibold text-gray-700 mb-4">📉 伸びなかった動画</h2>
                <div className="space-y-3">
                  {bottomVideos.map((v, i) => (
                    <div key={v.id} className="flex items-start gap-3 p-3 rounded-lg hover:bg-gray-50">
                      <span className="font-bold text-gray-400 text-sm w-5">{i + 1}</span>
                      {v.thumbnail_url && (
                        <img src={v.thumbnail_url} alt="" className="w-24 h-14 object-cover rounded" />
                      )}
                      <div className="flex-1">
                        <p className="text-sm font-medium text-gray-800 line-clamp-2">{v.title}</p>
                        <div className="flex gap-3 mt-1 text-xs text-gray-500">
                          <span>👁 {v.views?.toLocaleString()}</span>
                          <span>CTR: {v.ctr ? `${v.ctr.toFixed(1)}%` : '-'}</span>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          )}
        </>
      )}
    </div>
  )
}
