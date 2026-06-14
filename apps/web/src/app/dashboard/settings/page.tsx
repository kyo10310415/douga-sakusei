'use client'
import { useState, useEffect } from 'react'
import { settingsApi, youtubeApi } from '@/lib/api'

const DAY_OPTIONS = [
  { value: 0, label: '日曜日' },
  { value: 1, label: '月曜日' },
  { value: 2, label: '火曜日' },
  { value: 3, label: '水曜日' },
  { value: 4, label: '木曜日' },
  { value: 5, label: '金曜日' },
  { value: 6, label: '土曜日' },
]

export default function SettingsPage() {
  const [scheduler, setScheduler] = useState({
    day_of_week: 1,
    hour: 9,
    minute: 0,
    enabled: true,
  })
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [oauthUrl, setOauthUrl] = useState('')
  const [connectingYouTube, setConnectingYouTube] = useState(false)

  useEffect(() => {
    settingsApi.getScheduler()
      .then(res => setScheduler(res.data))
      .catch(console.error)
      .finally(() => setLoading(false))
  }, [])

  const handleSaveScheduler = async () => {
    setSaving(true)
    try {
      await settingsApi.updateScheduler(scheduler)
      alert('スケジューラー設定を保存しました')
    } catch (err: any) {
      alert(err.response?.data?.detail || 'エラーが発生しました')
    } finally {
      setSaving(false)
    }
  }

  const handleConnectYouTube = async () => {
    setConnectingYouTube(true)
    try {
      const res = await youtubeApi.startOAuth()
      window.open(res.data.authorization_url, '_blank')
    } catch (err: any) {
      alert(err.response?.data?.detail || 'YouTube連携エラー: OAuth設定を確認してください')
    } finally {
      setConnectingYouTube(false)
    }
  }

  if (loading) return <div className="p-8 text-gray-400">読み込み中...</div>

  return (
    <div className="p-8 max-w-2xl">
      <h1 className="text-2xl font-bold text-gray-900 mb-6">⚙️ システム設定</h1>

      {/* YouTube連携 */}
      <div className="bg-white rounded-xl p-6 shadow-sm border border-gray-100 mb-6">
        <h2 className="font-bold text-gray-800 mb-4 flex items-center gap-2">
          <span>📺</span> YouTube連携
        </h2>
        <p className="text-sm text-gray-500 mb-4">
          YouTubeチャンネルとの連携設定です。.envファイルにYOUTUBE_CLIENT_IDとYOUTUBE_CLIENT_SECRETを設定してください。
        </p>
        <div className="bg-gray-50 rounded-lg p-4 mb-4">
          <p className="text-xs font-medium text-gray-600 mb-2">必要な.env設定:</p>
          <code className="text-xs text-gray-500 block">
            YOUTUBE_CLIENT_ID=your-client-id<br />
            YOUTUBE_CLIENT_SECRET=your-client-secret<br />
            YOUTUBE_REDIRECT_URI=http://localhost:8000/api/youtube/oauth/callback
          </code>
        </div>
        <button
          onClick={handleConnectYouTube}
          disabled={connectingYouTube}
          className="bg-red-600 hover:bg-red-700 disabled:opacity-50 text-white px-4 py-2 rounded-lg text-sm font-medium"
        >
          {connectingYouTube ? '接続中...' : '🔗 YouTube連携を開始'}
        </button>
      </div>

      {/* スケジューラー設定 */}
      <div className="bg-white rounded-xl p-6 shadow-sm border border-gray-100 mb-6">
        <h2 className="font-bold text-gray-800 mb-4 flex items-center gap-2">
          <span>⏰</span> 週次ジョブスケジューラー
        </h2>
        <p className="text-sm text-gray-500 mb-4">
          毎週自動で「YouTube取得→AI分析→動画生成→限定公開アップロード」を実行する時刻を設定します。
        </p>

        <div className="space-y-4">
          <div className="flex items-center gap-3">
            <input
              type="checkbox"
              id="scheduler_enabled"
              checked={scheduler.enabled}
              onChange={e => setScheduler({ ...scheduler, enabled: e.target.checked })}
              className="w-4 h-4 rounded accent-purple-500"
            />
            <label htmlFor="scheduler_enabled" className="text-sm font-medium text-gray-700">
              自動実行を有効にする
            </label>
          </div>

          <div className="grid grid-cols-3 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">曜日</label>
              <select
                value={scheduler.day_of_week}
                onChange={e => setScheduler({ ...scheduler, day_of_week: parseInt(e.target.value) })}
                disabled={!scheduler.enabled}
                className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-purple-400 disabled:opacity-50"
              >
                {DAY_OPTIONS.map(opt => (
                  <option key={opt.value} value={opt.value}>{opt.label}</option>
                ))}
              </select>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">時 (0-23)</label>
              <input
                type="number" min="0" max="23"
                value={scheduler.hour}
                onChange={e => setScheduler({ ...scheduler, hour: parseInt(e.target.value) })}
                disabled={!scheduler.enabled}
                className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-purple-400 disabled:opacity-50"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">分 (0-59)</label>
              <input
                type="number" min="0" max="59"
                value={scheduler.minute}
                onChange={e => setScheduler({ ...scheduler, minute: parseInt(e.target.value) })}
                disabled={!scheduler.enabled}
                className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-purple-400 disabled:opacity-50"
              />
            </div>
          </div>

          {scheduler.enabled && (
            <p className="text-sm text-gray-500 bg-blue-50 p-3 rounded-lg">
              毎週 {DAY_OPTIONS.find(d => d.value === scheduler.day_of_week)?.label} の {scheduler.hour}:{String(scheduler.minute).padStart(2, '0')} に実行されます
            </p>
          )}
        </div>

        <button
          onClick={handleSaveScheduler}
          disabled={saving}
          className="mt-4 bg-purple-600 hover:bg-purple-700 disabled:opacity-50 text-white px-4 py-2 rounded-lg text-sm font-medium"
        >
          {saving ? '保存中...' : '設定を保存'}
        </button>
      </div>

      {/* ジョブフロー説明 */}
      <div className="bg-white rounded-xl p-6 shadow-sm border border-gray-100">
        <h2 className="font-bold text-gray-800 mb-4">🔄 自動化フロー</h2>
        <div className="space-y-2">
          {[
            { step: 1, label: 'YouTube週次データ取得', desc: 'Analytics APIで視聴データを取得' },
            { step: 2, label: 'AI分析', desc: 'OpenAI APIでトレンド分析・改善点抽出' },
            { step: 3, label: '次回企画生成', desc: 'AI分析結果をもとに動画企画を生成' },
            { step: 4, label: '台本生成', desc: 'キャラクター設定・テーマ設定に基づく台本' },
            { step: 5, label: '音声生成', desc: 'TTSで各セクションの音声を生成' },
            { step: 6, label: '素材生成', desc: '背景・挿入画像などの素材を生成' },
            { step: 7, label: '動画レンダリング', desc: 'FFmpegでシーンを合成・動画化' },
            { step: 8, label: 'YouTube限定公開アップロード', desc: '必ずunlistedでアップロード（auto-publicは禁止）' },
            { step: 9, label: '人間によるレビュー待ち', desc: 'ダッシュボードで通知' },
          ].map(item => (
            <div key={item.step} className="flex items-start gap-3">
              <span className="w-6 h-6 bg-purple-100 text-purple-700 rounded-full flex items-center justify-center text-xs font-bold flex-shrink-0">
                {item.step}
              </span>
              <div>
                <p className="text-sm font-medium text-gray-700">{item.label}</p>
                <p className="text-xs text-gray-400">{item.desc}</p>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}
