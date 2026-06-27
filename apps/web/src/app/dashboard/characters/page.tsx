'use client'
import { useState, useEffect, useRef } from 'react'
import { characterApi, apiClient } from '@/lib/api'

// ── TTSプロバイダーごとの声の種類定義 ─────────────────────────
const TTS_VOICE_OPTIONS: Record<string, { label: string; options: { value: string; label: string; description?: string }[] }> = {
  mock: {
    label: 'モック（テスト用・音声なし）',
    options: [],
  },
  openai: {
    label: 'OpenAI TTS',
    options: [
      { value: 'alloy',   label: 'Alloy',   description: '中性的・バランスの良い声' },
      { value: 'echo',    label: 'Echo',    description: '男性的・落ち着いた声' },
      { value: 'fable',   label: 'Fable',   description: '英国風・温かみのある声' },
      { value: 'onyx',    label: 'Onyx',    description: '男性・深みのある低い声' },
      { value: 'nova',    label: 'Nova',    description: '女性的・明るく活発な声 ★人気' },
      { value: 'shimmer', label: 'Shimmer', description: '女性・柔らかく落ち着いた声' },
    ],
  },
  voicevox: {
    label: 'VOICEVOX（日本語特化・無料）',
    options: [
      { value: '1',  label: '四国めたん（あまあま）',    description: '女性・甘い声' },
      { value: '2',  label: '四国めたん（ノーマル）',    description: '女性・標準' },
      { value: '3',  label: 'ずんだもん（ノーマル）',    description: '女性・元気・人気 ★' },
      { value: '4',  label: 'ずんだもん（あまあま）',    description: '女性・甘い声' },
      { value: '8',  label: '春日部つむぎ',              description: '女性・元気なJK風' },
      { value: '10', label: '雨晴はう',                  description: '女性・優しい声' },
      { value: '11', label: '波音リツ',                  description: '女性・クール' },
      { value: '13', label: '青山龍星',                  description: '男性・低音' },
      { value: '14', label: '冥鳴ひまり',                description: '女性・神秘的' },
      { value: '16', label: 'WhiteCUL',                  description: '女性・可愛い' },
      { value: '20', label: '後鬼',                      description: '男性・渋い声' },
      { value: '23', label: '九州そら（ノーマル）',      description: '女性・爽やか' },
      { value: '29', label: '玄野武宏',                  description: '男性・爽やか' },
      { value: '52', label: 'No.7',                      description: '男性・若い声' },
    ],
  },
  elevenlabs: {
    label: 'ElevenLabs（高品質・英日対応）',
    options: [
      { value: 'Rachel',    label: 'Rachel',    description: '女性・落ち着いた声（英語）' },
      { value: 'Domi',      label: 'Domi',      description: '女性・自信に満ちた声（英語）' },
      { value: 'Bella',     label: 'Bella',     description: '女性・柔らかい声（英語）' },
      { value: 'Antoni',    label: 'Antoni',    description: '男性・温かみのある声（英語）' },
      { value: 'Josh',      label: 'Josh',      description: '男性・若い声（英語）' },
      { value: 'Arnold',    label: 'Arnold',    description: '男性・クリアな声（英語）' },
      { value: 'Adam',      label: 'Adam',      description: '男性・ディープな声（英語）' },
      { value: 'Sam',       label: 'Sam',       description: '男性・落ち着いた声（英語）' },
      { value: '__custom__', label: '✏️ カスタムVoice ID（直接入力）', description: 'ElevenLabsダッシュボードで取得したVoice ID' },
    ],
  },
}

export default function CharactersPage() {
  const [characters, setCharacters] = useState<any[]>([])
  const [loading, setLoading] = useState(true)
  const [showForm, setShowForm] = useState(false)
  const [editingId, setEditingId] = useState<string | null>(null)
  const [customVoiceId, setCustomVoiceId] = useState('')

  // ── サンプル音声プレビュー用 state ──
  const [previewLoading, setPreviewLoading] = useState(false)
  const [previewError, setPreviewError] = useState('')
  const [previewText, setPreviewText] = useState('こんにちは！わたしはAIキャラクターです。この声でよろしければ保存してください。')
  const [isPlaying, setIsPlaying] = useState(false)
  const audioRef = useRef<HTMLAudioElement | null>(null)
  const [form, setForm] = useState({
    name: '',
    age_setting: '',
    personality: '',
    tone: '',
    first_person: 'わたし',
    viewer_address: 'みなさん',
    specialty_genres: [] as string[],
    weak_genres: [] as string[],
    character_description: '',
    ng_expressions: '',
    speech_samples: '',
    tts_provider: 'mock',
    voice_type: '',
    speech_rate: 1.0,
    pitch: 0.0,
    emotion_strength: 0.7,
    is_default: false,
  })

  // プロバイダーが変わったらvoice_typeをリセット＆プレビューをクリア
  const handleProviderChange = (provider: string) => {
    const firstOption = TTS_VOICE_OPTIONS[provider]?.options[0]?.value ?? ''
    setForm(prev => ({ ...prev, tts_provider: provider, voice_type: firstOption }))
    setCustomVoiceId('')
    stopPreview()
    setPreviewError('')
  }

  // ── サンプル音声再生 ─────────────────────────────────
  const stopPreview = () => {
    if (audioRef.current) {
      // AudioContext 方式の停止（gsStop関数が設定されている場合）
      const ref = audioRef.current as any
      if (typeof ref.gsStop === 'function') {
        try { ref.gsStop() } catch (_) {}
      } else if (typeof ref.pause === 'function') {
        // フォールバック：従来のHTMLAudioElement
        ref.pause()
        ref.src = ''
      }
      audioRef.current = null
    }
    setIsPlaying(false)
  }

  const handlePreview = async () => {
    // 再生中なら停止
    if (isPlaying) { stopPreview(); return }

    // VOICEVOX はローカルサーバー必須のためクラウド環境では使用不可
    if (form.tts_provider === 'voicevox') {
      setPreviewError('VOICEVOXはローカル環境専用です。クラウド（Render等）では利用できません。ローカルで VOICEVOX を起動してから開発環境でお試しください。')
      return
    }

    const voiceType = form.tts_provider === 'elevenlabs' && form.voice_type === '__custom__'
      ? customVoiceId
      : form.voice_type

    setPreviewLoading(true)
    setPreviewError('')

    // デバッグ: ボタン押下とリクエスト情報をコンソールに出力
    console.log('[TTS Preview] リクエスト開始', {
      provider: form.tts_provider,
      voice_type: voiceType,
      apiBase: apiClient.defaults.baseURL,
      fullUrl: (apiClient.defaults.baseURL || '') + '/characters/tts-preview',
    })

    try {
      const res = await apiClient.post(
        '/characters/tts-preview',
        {
          provider: form.tts_provider,
          voice_type: voiceType || undefined,
          speech_rate: form.speech_rate,
          pitch: form.pitch,
          emotion_strength: form.emotion_strength,
          text: previewText,
        },
        { responseType: 'blob' }
      )

      console.log('[TTS Preview] レスポンス受信', { status: res.status, contentType: res.headers['content-type'] })

      // ── AudioContext を使った確実な再生 ─────────────────
      // HTMLAudioElement + ObjectURL はブラウザのAutoplay制限や
      // Content-Security-Policyに引っかかる場合がある。
      // ArrayBuffer → AudioContext.decodeAudioData() → 再生 の方が確実。
      const rawBlob: Blob = res.data

      console.log('[TTS Preview] Blob情報', {
        rawSize: rawBlob.size,
        rawType: rawBlob.type,
      })

      if (rawBlob.size === 0) {
        setPreviewError('音声データが空です。APIキーや設定を確認してください。')
        return
      }

      // Blob → ArrayBuffer に変換
      const arrayBuffer = await rawBlob.arrayBuffer()

      // AudioContext を生成（既存があれば再利用）
      const AudioCtx = window.AudioContext || (window as any).webkitAudioContext
      const audioCtx = new AudioCtx()

      console.log('[TTS Preview] AudioContext状態', { state: audioCtx.state })

      // suspended（Autoplay制限）なら resume する
      if (audioCtx.state === 'suspended') {
        await audioCtx.resume()
        console.log('[TTS Preview] AudioContext resume完了', { state: audioCtx.state })
      }

      let audioBuffer: AudioBuffer
      try {
        audioBuffer = await audioCtx.decodeAudioData(arrayBuffer)
        console.log('[TTS Preview] デコード成功', {
          duration: audioBuffer.duration,
          sampleRate: audioBuffer.sampleRate,
          numberOfChannels: audioBuffer.numberOfChannels,
        })
      } catch (decodeErr: any) {
        console.error('[TTS Preview] デコード失敗', decodeErr)
        setPreviewError(`音声のデコードに失敗しました: ${decodeErr?.message || decodeErr}`)
        audioCtx.close()
        return
      }

      // 既存の再生を停止
      if (audioRef.current) {
        (audioRef.current as any).gsStop?.()
        audioRef.current = null
      }

      const source = audioCtx.createBufferSource()
      source.buffer = audioBuffer
      source.connect(audioCtx.destination)

      // AudioContext を安全にcloseするヘルパー（二重close防止）
      const safeClose = () => {
        if (audioCtx.state !== 'closed') {
          audioCtx.close().catch(() => {})
        }
      }

      source.onended = () => {
        console.log('[TTS Preview] 再生終了')
        setIsPlaying(false)
        safeClose()
        audioRef.current = null
      }

      source.start(0)
      console.log('[TTS Preview] source.start() 呼び出し完了')
      setIsPlaying(true)

      // 停止用の関数を audioRef に保持（safeClose を使うので二重close不要）
      ;(audioRef as any).current = {
        gsStop: () => {
          try { source.stop() } catch (_) {}
          safeClose()
        }
      }
    } catch (err: any) {
      // デバッグ: ステータス・URL・レスポンス内容をコンソールに出力
      const status = err.response?.status
      const reqUrl = err.config?.url || err.config?.baseURL + err.config?.url
      console.error('[TTS Preview Error]', {
        status,
        url: reqUrl,
        baseURL: err.config?.baseURL,
        data: err.response?.data,
      })

      const detail = err.response?.data
      let errorMsg = ''

      if (detail) {
        // blob レスポンスの場合は JSON をパース
        if (detail instanceof Blob) {
          const text = await detail.text()
          try {
            const json = JSON.parse(text)
            errorMsg = json.detail?.error || json.detail || text
          } catch {
            errorMsg = text
          }
        } else {
          errorMsg = detail.detail?.error || detail.detail || String(detail)
        }
      } else {
        errorMsg = '音声の生成に失敗しました'
      }

      // ステータスコードを表示に含める（診断用）
      setPreviewError(status ? `[HTTP ${status}] ${errorMsg}` : errorMsg)
    } finally {
      setPreviewLoading(false)
    }
  }

  // 実際に保存するvoice_typeを解決
  const resolvedVoiceType = (() => {
    if (form.tts_provider === 'elevenlabs' && form.voice_type === '__custom__') {
      return customVoiceId
    }
    return form.voice_type
  })()

  useEffect(() => {
    fetchCharacters()
  }, [])

  const fetchCharacters = async () => {
    try {
      const res = await characterApi.list()
      setCharacters(res.data)
    } catch (err) {
      console.error(err)
    } finally {
      setLoading(false)
    }
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    // ElevenLabs カスタムIDが空のまま保存しようとした場合は警告
    if (form.tts_provider === 'elevenlabs' && form.voice_type === '__custom__' && !customVoiceId.trim()) {
      alert('カスタムVoice IDを入力してください')
      return
    }
    try {
      const payload = { ...form, voice_type: resolvedVoiceType }
      if (editingId) {
        await characterApi.update(editingId, payload)
        alert('キャラクターを更新しました')
      } else {
        await characterApi.create(payload)
        alert('キャラクターを作成しました')
      }
      setShowForm(false)
      setEditingId(null)
      fetchCharacters()
    } catch (err: any) {
      alert(err.response?.data?.detail || 'エラーが発生しました')
    }
  }

  const handleEdit = async (id: string) => {
    try {
      const res = await characterApi.get(id)
      const c = res.data
      const provider = c.tts_provider || 'mock'
      const voiceOptions = TTS_VOICE_OPTIONS[provider]?.options ?? []
      const isCustom = provider === 'elevenlabs' && c.voice_type
        && !voiceOptions.some((o: any) => o.value === c.voice_type && o.value !== '__custom__')

      setForm({
        name: c.name || '',
        age_setting: c.age_setting || '',
        personality: c.personality || '',
        tone: c.tone || '',
        first_person: c.first_person || 'わたし',
        viewer_address: c.viewer_address || 'みなさん',
        specialty_genres: c.specialty_genres || [],
        weak_genres: c.weak_genres || [],
        character_description: c.character_description || '',
        ng_expressions: c.ng_expressions || '',
        speech_samples: c.speech_samples || '',
        tts_provider: provider,
        voice_type: isCustom ? '__custom__' : (c.voice_type || voiceOptions[0]?.value || ''),
        speech_rate: c.speech_rate ?? 1.0,
        pitch: c.pitch ?? 0.0,
        emotion_strength: c.emotion_strength ?? 0.7,
        is_default: c.is_default || false,
      })
      if (isCustom) setCustomVoiceId(c.voice_type || '')
      else setCustomVoiceId('')
      setEditingId(id)
      setShowForm(true)
    } catch (err) {
      console.error(err)
    }
  }

  const handleImageUpload = async (charId: string, imageType: string, file: File) => {
    try {
      await characterApi.uploadImage(charId, imageType, file)
      alert(`${imageType} 画像をアップロードしました`)
      fetchCharacters()
    } catch (err: any) {
      alert(err.response?.data?.detail || 'エラーが発生しました')
    }
  }

  // 現在のプロバイダーの声オプション
  const currentVoiceOptions = TTS_VOICE_OPTIONS[form.tts_provider]?.options ?? []
  const selectedVoiceInfo = currentVoiceOptions.find(o => o.value === form.voice_type)

  if (loading) return <div className="p-8 text-gray-400">読み込み中...</div>

  return (
    <div className="p-8">
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold text-gray-900">🎭 キャラクター設定</h1>
        <button
          onClick={() => { setShowForm(true); setEditingId(null) }}
          className="bg-purple-600 hover:bg-purple-700 text-white px-4 py-2 rounded-lg text-sm font-medium"
        >
          ＋ 新規作成
        </button>
      </div>

      {/* キャラクター一覧 */}
      {characters.length === 0 ? (
        <div className="text-center py-16 text-gray-400">
          <div className="text-5xl mb-4">🎭</div>
          <p>キャラクターがいません</p>
          <p className="text-sm mt-2">キャラクターを作成してください</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-6 mb-8">
          {characters.map(char => (
            <div key={char.id} className="bg-white rounded-xl shadow-sm border border-gray-100 overflow-hidden">
              <div className="bg-gradient-to-br from-purple-100 to-pink-100 h-32 flex items-center justify-center">
                {char.images?.standing?.url ? (
                  <img src={char.images.standing.url} alt={char.name} className="h-full object-contain" />
                ) : (
                  <span className="text-5xl">🎭</span>
                )}
              </div>
              <div className="p-5">
                <div className="flex items-center justify-between mb-2">
                  <h3 className="font-bold text-gray-900 text-lg">{char.name}</h3>
                  {char.is_default && (
                    <span className="bg-purple-100 text-purple-700 text-xs px-2 py-0.5 rounded-full font-medium">デフォルト</span>
                  )}
                </div>
                <div className="space-y-1 text-sm text-gray-500">
                  {char.age_setting && <p>年齢: {char.age_setting}</p>}
                  <p>一人称: {char.first_person} / 視聴者: {char.viewer_address}</p>
                  {/* 音声設定を分かりやすく表示 */}
                  <div className="bg-purple-50 rounded-lg px-3 py-2 mt-2">
                    <p className="text-xs font-semibold text-purple-700 mb-1">🎵 音声設定</p>
                    <p className="text-xs">
                      <span className="font-medium">TTS:</span>{' '}
                      {char.tts_provider === 'mock' && 'モック（無音）'}
                      {char.tts_provider === 'openai' && 'OpenAI TTS'}
                      {char.tts_provider === 'voicevox' && 'VOICEVOX'}
                      {char.tts_provider === 'elevenlabs' && 'ElevenLabs'}
                    </p>
                    {char.voice_type && (
                      <p className="text-xs">
                        <span className="font-medium">声:</span>{' '}
                        {TTS_VOICE_OPTIONS[char.tts_provider]?.options.find(o => o.value === char.voice_type)?.label || char.voice_type}
                      </p>
                    )}
                    <p className="text-xs">話速: {char.speech_rate}x / ピッチ: {char.pitch}</p>
                  </div>
                </div>
                <div className="mt-3 flex gap-1">
                  {['profile', 'standing', 'expression_normal', 'expression_smile', 'expression_surprise', 'expression_troubled', 'expression_serious'].map(imgType => (
                    <label key={imgType}
                      className={`w-6 h-6 rounded cursor-pointer flex items-center justify-center text-xs ${char.images?.[imgType] ? 'bg-green-200 text-green-700' : 'bg-gray-100 text-gray-400'}`}
                      title={imgType}
                    >
                      {char.images?.[imgType] ? '✓' : '×'}
                      <input type="file" accept="image/*" className="hidden"
                        onChange={e => { const file = e.target.files?.[0]; if (file) handleImageUpload(char.id, imgType, file) }} />
                    </label>
                  ))}
                </div>
                <p className="text-xs text-gray-400 mt-1">画像クリックでアップロード</p>
                <div className="mt-4 flex gap-2">
                  <button onClick={() => handleEdit(char.id)}
                    className="flex-1 bg-gray-100 hover:bg-gray-200 text-gray-700 py-2 rounded-lg text-xs font-medium">
                    編集
                  </button>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* 作成・編集フォーム */}
      {showForm && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-2xl w-full max-w-2xl max-h-[90vh] overflow-y-auto">
            <div className="p-6 border-b border-gray-100">
              <div className="flex items-center justify-between">
                <h2 className="text-lg font-bold text-gray-900">
                  {editingId ? 'キャラクター編集' : 'キャラクター作成'}
                </h2>
                <button onClick={() => setShowForm(false)} className="text-gray-400 hover:text-gray-700 text-xl">×</button>
              </div>
            </div>

            <form onSubmit={handleSubmit} className="p-6 space-y-5">
              {/* 基本情報 */}
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">キャラクター名 *</label>
                  <input required value={form.name} onChange={e => setForm({ ...form, name: e.target.value })}
                    className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-purple-500 outline-none"
                    placeholder="例: AIちゃん" />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">年齢設定</label>
                  <input value={form.age_setting} onChange={e => setForm({ ...form, age_setting: e.target.value })}
                    className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-purple-500 outline-none"
                    placeholder="例: 17歳" />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">一人称</label>
                  <input value={form.first_person} onChange={e => setForm({ ...form, first_person: e.target.value })}
                    className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-purple-500 outline-none"
                    placeholder="わたし / あたし / 私" />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">視聴者の呼び方</label>
                  <input value={form.viewer_address} onChange={e => setForm({ ...form, viewer_address: e.target.value })}
                    className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-purple-500 outline-none"
                    placeholder="みんな / みなさん" />
                </div>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">性格</label>
                <textarea value={form.personality} onChange={e => setForm({ ...form, personality: e.target.value })}
                  rows={2} className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-purple-500 outline-none"
                  placeholder="例: 明るくて元気！好奇心旺盛で新しいことが大好き。" />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">口調</label>
                <textarea value={form.tone} onChange={e => setForm({ ...form, tone: e.target.value })}
                  rows={2} className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-purple-500 outline-none"
                  placeholder="例: フレンドリーでカジュアル。語尾に「ね」や「よ」を使う。" />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">話し方のサンプル</label>
                <textarea value={form.speech_samples} onChange={e => setForm({ ...form, speech_samples: e.target.value })}
                  rows={3} className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-purple-500 outline-none"
                  placeholder="例: 「ねえみんな！今日も元気？わたしはめちゃくちゃ元気だよ！」" />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">NG表現</label>
                <textarea value={form.ng_expressions} onChange={e => setForm({ ...form, ng_expressions: e.target.value })}
                  rows={2} className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-purple-500 outline-none"
                  placeholder="例: 暴言・差別表現・特定の政治的発言" />
              </div>

              {/* ───── 音声設定（改修部分） ───── */}
              <div className="border-t border-gray-100 pt-5">
                <h3 className="font-semibold text-gray-800 mb-1">🎵 音声設定</h3>
                <p className="text-xs text-gray-400 mb-4">
                  TTSプロバイダーを選ぶと、使用できる「声の種類」が自動的に切り替わります
                </p>

                {/* STEP 1: プロバイダー選択 */}
                <div className="mb-4">
                  <label className="block text-sm font-semibold text-gray-700 mb-2">
                    STEP 1 — TTSプロバイダーを選ぶ
                  </label>
                  <div className="grid grid-cols-2 gap-2">
                    {Object.entries(TTS_VOICE_OPTIONS).map(([key, info]) => (
                      <button
                        key={key}
                        type="button"
                        onClick={() => handleProviderChange(key)}
                        className={`text-left px-3 py-2.5 rounded-lg border text-sm transition-colors ${
                          form.tts_provider === key
                            ? 'bg-purple-600 text-white border-purple-600'
                            : 'bg-white text-gray-700 border-gray-200 hover:border-purple-300'
                        }`}
                      >
                        <span className="font-medium flex items-center gap-1">
                          {key === 'mock' && '🔇 モック'}
                          {key === 'openai' && '🤖 OpenAI TTS'}
                          {key === 'voicevox' && '🎌 VOICEVOX'}
                          {key === 'elevenlabs' && '⚡ ElevenLabs'}
                          {/* VOICEVOXはローカル専用バッジ */}
                          {key === 'voicevox' && (
                            <span className="text-[10px] bg-yellow-400 text-yellow-900 font-bold px-1 py-0.5 rounded leading-none">
                              ローカル専用
                            </span>
                          )}
                        </span>
                        <span className={`block text-xs mt-0.5 ${form.tts_provider === key ? 'text-purple-100' : 'text-gray-400'}`}>
                          {key === 'mock' && '音声なし・開発用'}
                          {key === 'openai' && '6種類の声・英語得意'}
                          {key === 'voicevox' && 'ローカルVOICEVOX起動が必要'}
                          {key === 'elevenlabs' && '高品質・英日対応'}
                        </span>
                      </button>
                    ))}
                  </div>
                </div>

                {/* STEP 2: 声の種類選択（mock以外） */}
                {form.tts_provider !== 'mock' && currentVoiceOptions.length > 0 && (
                  <div className="mb-4">
                    <label className="block text-sm font-semibold text-gray-700 mb-2">
                      STEP 2 — 声の種類を選ぶ
                    </label>
                    <select
                      value={form.voice_type}
                      onChange={e => setForm({ ...form, voice_type: e.target.value })}
                      className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-purple-500 outline-none"
                    >
                      {currentVoiceOptions.map(opt => (
                        <option key={opt.value} value={opt.value}>
                          {opt.label}{opt.description ? ` — ${opt.description}` : ''}
                        </option>
                      ))}
                    </select>

                    {/* 選択中の声の説明バッジ */}
                    {selectedVoiceInfo && selectedVoiceInfo.value !== '__custom__' && (
                      <div className="mt-2 bg-purple-50 border border-purple-100 rounded-lg px-3 py-2 text-xs text-purple-800">
                        ✅ 選択中：<strong>{selectedVoiceInfo.label}</strong>
                        {selectedVoiceInfo.description && (
                          <span className="text-purple-600 ml-1">— {selectedVoiceInfo.description}</span>
                        )}
                        {/* VOICEVOXのキャラクターID表示 */}
                        {form.tts_provider === 'voicevox' && (
                          <span className="ml-2 text-gray-400">（スタイルID: {selectedVoiceInfo.value}）</span>
                        )}
                      </div>
                    )}

                    {/* ElevenLabs カスタムVoice ID入力欄 */}
                    {form.tts_provider === 'elevenlabs' && form.voice_type === '__custom__' && (
                      <div className="mt-3">
                        <label className="block text-xs font-medium text-gray-600 mb-1">
                          カスタムVoice ID（ElevenLabsダッシュボードから取得）
                        </label>
                        <input
                          type="text"
                          value={customVoiceId}
                          onChange={e => setCustomVoiceId(e.target.value)}
                          placeholder="例: 21m00Tcm4TlvDq8ikWAM"
                          className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-purple-500 outline-none font-mono"
                        />
                        <p className="text-xs text-gray-400 mt-1">
                          取得方法：
                          <a href="https://elevenlabs.io/voice-lab" target="_blank" rel="noopener noreferrer"
                            className="text-blue-500 hover:underline ml-1">
                            ElevenLabs Voice Lab
                          </a>
                          → 使いたい声 → 「View」→ Voice ID をコピー
                        </p>
                      </div>
                    )}
                  </div>
                )}

                {/* ── サンプル音声プレビュー ── */}
                {form.tts_provider !== 'mock' && (
                  <div className="mt-4 bg-purple-50 border border-purple-100 rounded-xl p-4">
                    <p className="text-xs font-semibold text-purple-700 mb-2">🎧 サンプル音声を聴く</p>

                    {/* サンプルテキスト編集 */}
                    <div className="mb-3">
                      <label className="block text-xs text-gray-500 mb-1">読み上げるテキスト（変更可）</label>
                      <input
                        type="text"
                        value={previewText}
                        onChange={e => setPreviewText(e.target.value)}
                        maxLength={100}
                        className="w-full border border-purple-200 rounded-lg px-3 py-1.5 text-sm focus:ring-2 focus:ring-purple-400 outline-none bg-white"
                      />
                      <p className="text-xs text-gray-400 text-right mt-0.5">{previewText.length}/100文字</p>
                    </div>

                    {/* 再生ボタン */}
                    <button
                      type="button"
                      onClick={handlePreview}
                      disabled={previewLoading || (form.tts_provider === 'elevenlabs' && form.voice_type === '__custom__' && !customVoiceId.trim())}
                      className={`flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-colors disabled:opacity-50 ${
                        isPlaying
                          ? 'bg-red-500 hover:bg-red-600 text-white'
                          : 'bg-purple-600 hover:bg-purple-700 text-white'
                      }`}
                    >
                      {previewLoading ? (
                        <><span className="animate-spin">⏳</span> 生成中...</>
                      ) : isPlaying ? (
                        <><span>⏹</span> 停止</>
                      ) : (
                        <><span>▶</span> 再生してみる</>
                      )}
                    </button>

                    {/* エラー表示 */}
                    {previewError && (
                      <div className="mt-2 bg-red-50 border border-red-200 rounded-lg px-3 py-2 text-xs text-red-700">
                        <p className="font-medium">⚠️ {previewError}</p>
                        {previewError.includes('405') && (
                          <p className="mt-0.5 text-red-500">→ バックエンドAPIのルート設定エラーです。最新のデプロイが完了しているか確認してください</p>
                        )}
                        {!previewError.includes('405') && form.tts_provider === 'openai' && (
                          <p className="mt-0.5 text-red-500">→ Render の環境変数に <code className="bg-red-100 px-1 rounded">OPENAI_API_KEY</code> を設定してください</p>
                        )}
                        {!previewError.includes('405') && form.tts_provider === 'elevenlabs' && (
                          <p className="mt-0.5 text-red-500">→ Render の環境変数に <code className="bg-red-100 px-1 rounded">TTS_API_KEY</code>（ElevenLabs APIキー）を設定してください</p>
                        )}
                        {!previewError.includes('405') && form.tts_provider === 'voicevox' && (
                          <p className="mt-0.5 text-red-500">→ VOICEVOX はローカル環境でのみ動作します（Render 本番環境では利用不可）</p>
                        )}
                      </div>
                    )}

                    {/* プロバイダー別の補足情報 */}
                    <p className="text-xs text-purple-500 mt-2">
                      {form.tts_provider === 'openai' && '💡 OpenAI TTS は英語が得意ですが日本語も対応しています'}
                      {form.tts_provider === 'elevenlabs' && '💡 ElevenLabs は高品質ですが1文字ごとにAPIクレジットを消費します'}
                      {form.tts_provider === 'voicevox' && '💡 VOICEVOX はローカル環境（PC上）でのみ再生できます'}
                    </p>
                  </div>
                )}

                {/* mock のサンプルは無音なので案内のみ */}
                {form.tts_provider === 'mock' && (
                  <div className="mt-4 bg-gray-50 border border-gray-200 rounded-xl p-4">
                    <p className="text-xs text-gray-500">
                      🔇 モックは音声なし（無音）です。動画生成ジョブのテスト実行には使えますが、実際の音声は生成されません。
                      本番運用には <strong>OpenAI TTS</strong>（英語・日本語）または <strong>VOICEVOX</strong>（日本語専用・無料）をお選びください。
                    </p>
                  </div>
                )}

                {/* mock選択時のガイド */}
                {form.tts_provider === 'mock' && (
                  <div className="mb-4 bg-gray-50 border border-gray-200 rounded-lg px-3 py-2 text-xs text-gray-500">
                    🔇 モックでは音声は生成されません。動作テスト用として使用してください。
                    本番運用には OpenAI TTS / VOICEVOX / ElevenLabs のいずれかを選んでください。
                  </div>
                )}

                {/* STEP 3: 音声パラメータ */}
                <div>
                  <label className="block text-sm font-semibold text-gray-700 mb-2">
                    STEP 3 — 音声パラメータを調整する（任意）
                  </label>
                  <div className="grid grid-cols-3 gap-4">
                    <div>
                      <label className="block text-xs font-medium text-gray-600 mb-1">
                        話速: <span className="font-bold text-purple-700">{form.speech_rate}x</span>
                      </label>
                      <input type="range" min="0.5" max="2.0" step="0.1"
                        value={form.speech_rate}
                        onChange={e => setForm({ ...form, speech_rate: parseFloat(e.target.value) })}
                        className="w-full accent-purple-600" />
                      <div className="flex justify-between text-xs text-gray-400 mt-0.5">
                        <span>0.5x</span><span>1.0x</span><span>2.0x</span>
                      </div>
                    </div>
                    <div>
                      <label className="block text-xs font-medium text-gray-600 mb-1">
                        ピッチ: <span className="font-bold text-purple-700">{form.pitch > 0 ? '+' : ''}{form.pitch}</span>
                      </label>
                      <input type="range" min="-1.0" max="1.0" step="0.1"
                        value={form.pitch}
                        onChange={e => setForm({ ...form, pitch: parseFloat(e.target.value) })}
                        className="w-full accent-purple-600" />
                      <div className="flex justify-between text-xs text-gray-400 mt-0.5">
                        <span>低い</span><span>標準</span><span>高い</span>
                      </div>
                    </div>
                    <div>
                      <label className="block text-xs font-medium text-gray-600 mb-1">
                        感情強度: <span className="font-bold text-purple-700">{form.emotion_strength}</span>
                      </label>
                      <input type="range" min="0.0" max="1.0" step="0.1"
                        value={form.emotion_strength}
                        onChange={e => setForm({ ...form, emotion_strength: parseFloat(e.target.value) })}
                        className="w-full accent-purple-600" />
                      <div className="flex justify-between text-xs text-gray-400 mt-0.5">
                        <span>弱め</span><span>普通</span><span>強め</span>
                      </div>
                    </div>
                  </div>
                </div>
              </div>

              <div className="flex items-center gap-2">
                <input type="checkbox" id="is_default" checked={form.is_default}
                  onChange={e => setForm({ ...form, is_default: e.target.checked })} className="rounded" />
                <label htmlFor="is_default" className="text-sm text-gray-700">デフォルトキャラクターとして設定</label>
              </div>

              <div className="flex gap-3 pt-4 border-t border-gray-100">
                <button type="button" onClick={() => setShowForm(false)}
                  className="flex-1 border border-gray-300 text-gray-700 py-2.5 rounded-lg text-sm font-medium hover:bg-gray-50">
                  キャンセル
                </button>
                <button type="submit"
                  className="flex-1 bg-purple-600 hover:bg-purple-700 text-white py-2.5 rounded-lg text-sm font-medium">
                  {editingId ? '更新する' : '作成する'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  )
}
