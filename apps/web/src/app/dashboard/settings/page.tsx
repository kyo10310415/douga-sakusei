'use client'
import { useState, useEffect, useCallback } from 'react'
import { useSearchParams } from 'next/navigation'
import { settingsApi, youtubeApi } from '@/lib/api'
import { useAuth } from '@/hooks/useAuth'

const DAY_OPTIONS = [
  { value: 0, label: '日曜日' },
  { value: 1, label: '月曜日' },
  { value: 2, label: '火曜日' },
  { value: 3, label: '水曜日' },
  { value: 4, label: '木曜日' },
  { value: 5, label: '金曜日' },
  { value: 6, label: '土曜日' },
]

type YouTubeAccount = {
  id: string
  channel_id: string
  channel_title: string
  channel_thumbnail_url: string | null
  subscriber_count: number | null
  video_count: number | null
  view_count: number | null
  last_synced_at: string | null
  has_refresh_token: boolean
}

export default function SettingsPage() {
  const { user } = useAuth()
  const isAdmin = user?.is_admin ?? false
  const searchParams = useSearchParams()
  const [scheduler, setScheduler] = useState({ day_of_week: 1, hour: 9, minute: 0, enabled: true })
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [connectingYouTube, setConnectingYouTube] = useState(false)
  const [disconnecting, setDisconnecting] = useState<string | null>(null)
  const [accounts, setAccounts] = useState<YouTubeAccount[]>([])
  const [accountsLoading, setAccountsLoading] = useState(true)
  const [toast, setToast] = useState<{ type: 'success' | 'error'; msg: string } | null>(null)

  const showToast = (type: 'success' | 'error', msg: string) => {
    setToast({ type, msg })
    setTimeout(() => setToast(null), 5000)
  }

  const fetchAccounts = useCallback(async () => {
    setAccountsLoading(true)
    try {
      const res = await youtubeApi.getAccounts()
      setAccounts(res.data)
    } catch {
      // 未設定の場合は空配列のまま
    } finally {
      setAccountsLoading(false)
    }
  }, [])

  useEffect(() => {
    settingsApi.getScheduler()
      .then(res => setScheduler(res.data))
      .catch(err => {
        // 管理者権限エラー(403)は無視してデフォルト値のまま表示
        if (err.response?.status !== 403) {
          console.error('scheduler fetch error:', err)
        }
      })
      .finally(() => setLoading(false))
    fetchAccounts()
  }, [fetchAccounts])

  // コールバック結果をURLパラメータから受け取る
  useEffect(() => {
    const youtube = searchParams.get('youtube')
    if (youtube === 'success') {
      showToast('success', 'YouTubeアカウントの連携が完了しました！')
      fetchAccounts()
      // URLをクリーンアップ
      window.history.replaceState({}, '', '/dashboard/settings')
    } else if (youtube === 'error') {
      const reason = searchParams.get('reason') || '不明なエラー'
      showToast('error', `YouTube連携に失敗しました: ${reason}`)
      window.history.replaceState({}, '', '/dashboard/settings')
    }
  }, [searchParams, fetchAccounts])

  const handleSaveScheduler = async () => {
    setSaving(true)
    try {
      await settingsApi.updateScheduler(scheduler)
      showToast('success', 'スケジューラー設定を保存しました')
    } catch (err: any) {
      showToast('error', err.response?.data?.detail || 'エラーが発生しました')
    } finally {
      setSaving(false)
    }
  }

  const handleConnectYouTube = async () => {
    setConnectingYouTube(true)
    try {
      const res = await youtubeApi.startOAuth()
      // 同じタブでリダイレクト（OAuth callbackがダッシュボードに戻る）
      window.location.href = res.data.authorization_url
    } catch (err: any) {
      showToast('error', err.response?.data?.detail || 'YouTube連携エラー: サーバーのOAuth設定を確認してください')
      setConnectingYouTube(false)
    }
  }

  const handleDisconnect = async (accountId: string, channelTitle: string) => {
    if (!confirm(`「${channelTitle}」との連携を切断しますか？`)) return
    setDisconnecting(accountId)
    try {
      await youtubeApi.disconnectAccount(accountId)
      showToast('success', `「${channelTitle}」の連携を切断しました`)
      fetchAccounts()
    } catch (err: any) {
      showToast('error', err.response?.data?.detail || '切断に失敗しました')
    } finally {
      setDisconnecting(null)
    }
  }

  const formatCount = (n: number | null) => {
    if (n == null) return '—'
    if (n >= 10000) return `${(n / 10000).toFixed(1)}万`
    return n.toLocaleString()
  }

  if (loading) return <div className="p-8 text-gray-400">読み込み中...</div>

  return (
    <div className="p-8 max-w-2xl">
      <h1 className="text-2xl font-bold text-gray-900 mb-6">⚙️ システム設定</h1>

      {/* トースト通知 */}
      {toast && (
        <div className={`fixed top-6 right-6 z-50 px-5 py-3 rounded-xl shadow-lg text-white text-sm font-medium transition-all
          ${toast.type === 'success' ? 'bg-green-500' : 'bg-red-500'}`}>
          {toast.type === 'success' ? '✅ ' : '❌ '}{toast.msg}
        </div>
      )}

      {/* YouTube連携セクション */}
      <div className="bg-white rounded-xl p-6 shadow-sm border border-gray-100 mb-6">
        <h2 className="font-bold text-gray-800 mb-4 flex items-center gap-2 text-lg">
          <span>📺</span> YouTube連携
        </h2>

        {/* 連携済みアカウント一覧 */}
        {accountsLoading ? (
          <div className="text-sm text-gray-400 py-4 text-center">アカウント確認中...</div>
        ) : accounts.length > 0 ? (
          <div className="space-y-3 mb-5">
            {accounts.map(account => (
              <div key={account.id}
                className="flex items-center gap-4 bg-green-50 border border-green-200 rounded-xl p-4">
                {account.channel_thumbnail_url ? (
                  <img
                    src={account.channel_thumbnail_url}
                    alt={account.channel_title}
                    className="w-12 h-12 rounded-full border-2 border-green-300"
                  />
                ) : (
                  <div className="w-12 h-12 rounded-full bg-green-200 flex items-center justify-center text-green-700 font-bold text-lg">
                    {account.channel_title?.[0] ?? 'Y'}
                  </div>
                )}
                <div className="flex-1 min-w-0">
                  <p className="font-semibold text-gray-800 truncate">{account.channel_title}</p>
                  <div className="flex gap-3 mt-1 text-xs text-gray-500">
                    <span>👥 {formatCount(account.subscriber_count)}</span>
                    <span>🎬 {formatCount(account.video_count)}本</span>
                    <span>👁 {formatCount(account.view_count)}</span>
                  </div>
                  {account.last_synced_at && (
                    <p className="text-xs text-gray-400 mt-1">
                      最終同期: {new Date(account.last_synced_at).toLocaleString('ja-JP')}
                    </p>
                  )}
                  {!account.has_refresh_token && (
                    <p className="text-xs text-amber-600 mt-1">⚠️ リフレッシュトークンなし（再連携を推奨）</p>
                  )}
                </div>
                <div className="flex flex-col gap-2">
                  <span className="text-xs bg-green-100 text-green-700 px-2 py-1 rounded-full font-medium text-center">
                    ✓ 連携中
                  </span>
                  <button
                    onClick={() => handleDisconnect(account.id, account.channel_title)}
                    disabled={disconnecting === account.id}
                    className="text-xs text-red-500 hover:text-red-700 disabled:opacity-50 underline"
                  >
                    {disconnecting === account.id ? '切断中...' : '切断'}
                  </button>
                </div>
              </div>
            ))}
          </div>
        ) : (
          <div className="bg-gray-50 rounded-xl p-5 mb-5 text-center">
            <p className="text-gray-500 text-sm mb-1">YouTubeアカウントが連携されていません</p>
            <p className="text-gray-400 text-xs">連携するとチャンネルデータの取得・動画アップロードが可能になります</p>
          </div>
        )}

        {/* 連携ボタン */}
        <button
          onClick={handleConnectYouTube}
          disabled={connectingYouTube}
          className="w-full flex items-center justify-center gap-2 bg-red-600 hover:bg-red-700 disabled:opacity-50 disabled:cursor-wait text-white px-5 py-3 rounded-xl text-sm font-semibold transition-colors"
        >
          {connectingYouTube ? (
            <>
              <svg className="animate-spin h-4 w-4" viewBox="0 0 24 24" fill="none">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"/>
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8z"/>
              </svg>
              Googleアカウント選択画面へ移動中...
            </>
          ) : accounts.length > 0 ? (
            '🔗 別のYouTubeアカウントを追加連携'
          ) : (
            '🔗 YouTubeアカウントを連携する'
          )}
        </button>

        <p className="text-xs text-gray-400 mt-3">
          ※ RenderダッシュボードでYOUTUBE_CLIENT_IDとYOUTUBE_CLIENT_SECRETの設定が必要です
        </p>
      </div>

      {/* スケジューラー設定 */}
      <div className="bg-white rounded-xl p-6 shadow-sm border border-gray-100 mb-6">
        <h2 className="font-bold text-gray-800 mb-4 flex items-center gap-2 text-lg">
          <span>⏰</span> 週次ジョブスケジューラー
          {!isAdmin && <span className="text-xs text-gray-400 font-normal ml-1">（閲覧のみ）</span>}
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
              onChange={e => isAdmin && setScheduler({ ...scheduler, enabled: e.target.checked })}
              disabled={!isAdmin}
              className="w-4 h-4 rounded accent-purple-500 disabled:opacity-50"
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
                disabled={!scheduler.enabled || !isAdmin}
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
                disabled={!scheduler.enabled || !isAdmin}
                className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-purple-400 disabled:opacity-50"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">分 (0-59)</label>
              <input
                type="number" min="0" max="59"
                value={scheduler.minute}
                onChange={e => setScheduler({ ...scheduler, minute: parseInt(e.target.value) })}
                disabled={!scheduler.enabled || !isAdmin}
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

        {isAdmin ? (
          <button
            onClick={handleSaveScheduler}
            disabled={saving}
            className="mt-4 bg-purple-600 hover:bg-purple-700 disabled:opacity-50 text-white px-4 py-2 rounded-lg text-sm font-medium"
          >
            {saving ? '保存中...' : '設定を保存'}
          </button>
        ) : (
          <p className="mt-4 text-xs text-amber-600 bg-amber-50 px-3 py-2 rounded-lg">
            ⚠️ スケジューラー設定の変更は管理者アカウントのみ可能です
          </p>
        )}
      </div>

      {/* 自動化フロー説明 */}
      <div className="bg-white rounded-xl p-6 shadow-sm border border-gray-100">
        <h2 className="font-bold text-gray-800 mb-4 text-lg">🔄 自動化フロー</h2>
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
            { step: 9, label: '人間によるレビュー待ち', desc: 'ダッシュボードで通知・承認後に公開' },
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
