'use client'
import { useState, useEffect } from 'react'
import { characterApi } from '@/lib/api'
import Link from 'next/link'

export default function CharactersPage() {
  const [characters, setCharacters] = useState<any[]>([])
  const [loading, setLoading] = useState(true)
  const [showForm, setShowForm] = useState(false)
  const [editingId, setEditingId] = useState<string | null>(null)
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
    try {
      if (editingId) {
        await characterApi.update(editingId, form)
        alert('キャラクターを更新しました')
      } else {
        await characterApi.create(form)
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
        tts_provider: c.tts_provider || 'mock',
        voice_type: c.voice_type || '',
        speech_rate: c.speech_rate || 1.0,
        pitch: c.pitch || 0.0,
        emotion_strength: c.emotion_strength || 0.7,
        is_default: c.is_default || false,
      })
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
              {/* キャラクター画像プレビュー */}
              <div className="bg-gradient-to-br from-purple-100 to-pink-100 h-32 flex items-center justify-center">
                {char.images?.standing?.url ? (
                  <img
                    src={char.images.standing.url}
                    alt={char.name}
                    className="h-full object-contain"
                  />
                ) : (
                  <span className="text-5xl">🎭</span>
                )}
              </div>

              <div className="p-5">
                <div className="flex items-center justify-between mb-2">
                  <h3 className="font-bold text-gray-900 text-lg">{char.name}</h3>
                  {char.is_default && (
                    <span className="bg-purple-100 text-purple-700 text-xs px-2 py-0.5 rounded-full font-medium">
                      デフォルト
                    </span>
                  )}
                </div>
                <div className="space-y-1 text-sm text-gray-500">
                  {char.age_setting && <p>年齢: {char.age_setting}</p>}
                  <p>一人称: {char.first_person} / 視聴者: {char.viewer_address}</p>
                  <p>TTS: {char.tts_provider}</p>
                  <p>話速: {char.speech_rate}x / ピッチ: {char.pitch}</p>
                </div>

                {/* 表情差分チェック */}
                <div className="mt-3 flex gap-1">
                  {['profile', 'standing', 'expression_normal', 'expression_smile', 'expression_surprise', 'expression_troubled', 'expression_serious'].map(imgType => (
                    <label
                      key={imgType}
                      className={`w-6 h-6 rounded cursor-pointer flex items-center justify-center text-xs ${
                        char.images?.[imgType] ? 'bg-green-200 text-green-700' : 'bg-gray-100 text-gray-400'
                      }`}
                      title={imgType}
                    >
                      {char.images?.[imgType] ? '✓' : '×'}
                      <input
                        type="file"
                        accept="image/*"
                        className="hidden"
                        onChange={e => {
                          const file = e.target.files?.[0]
                          if (file) handleImageUpload(char.id, imgType, file)
                        }}
                      />
                    </label>
                  ))}
                </div>
                <p className="text-xs text-gray-400 mt-1">画像クリックでアップロード</p>

                <div className="mt-4 flex gap-2">
                  <button
                    onClick={() => handleEdit(char.id)}
                    className="flex-1 bg-gray-100 hover:bg-gray-200 text-gray-700 py-2 rounded-lg text-xs font-medium"
                  >
                    編集
                  </button>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* キャラクター作成・編集フォーム */}
      {showForm && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-2xl w-full max-w-2xl max-h-[90vh] overflow-y-auto">
            <div className="p-6 border-b border-gray-100">
              <div className="flex items-center justify-between">
                <h2 className="text-lg font-bold text-gray-900">
                  {editingId ? 'キャラクター編集' : 'キャラクター作成'}
                </h2>
                <button
                  onClick={() => setShowForm(false)}
                  className="text-gray-400 hover:text-gray-700 text-xl"
                >
                  ×
                </button>
              </div>
            </div>

            <form onSubmit={handleSubmit} className="p-6 space-y-5">
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">キャラクター名 *</label>
                  <input
                    required
                    value={form.name}
                    onChange={e => setForm({ ...form, name: e.target.value })}
                    className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-purple-500 outline-none"
                    placeholder="例: AIちゃん"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">年齢設定</label>
                  <input
                    value={form.age_setting}
                    onChange={e => setForm({ ...form, age_setting: e.target.value })}
                    className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-purple-500 outline-none"
                    placeholder="例: 17歳"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">一人称</label>
                  <input
                    value={form.first_person}
                    onChange={e => setForm({ ...form, first_person: e.target.value })}
                    className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-purple-500 outline-none"
                    placeholder="わたし / あたし / 私"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">視聴者の呼び方</label>
                  <input
                    value={form.viewer_address}
                    onChange={e => setForm({ ...form, viewer_address: e.target.value })}
                    className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-purple-500 outline-none"
                    placeholder="みんな / みなさん"
                  />
                </div>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">性格</label>
                <textarea
                  value={form.personality}
                  onChange={e => setForm({ ...form, personality: e.target.value })}
                  rows={2}
                  className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-purple-500 outline-none"
                  placeholder="例: 明るくて元気！好奇心旺盛で新しいことが大好き。"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">口調</label>
                <textarea
                  value={form.tone}
                  onChange={e => setForm({ ...form, tone: e.target.value })}
                  rows={2}
                  className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-purple-500 outline-none"
                  placeholder="例: フレンドリーでカジュアル。語尾に「ね」や「よ」を使う。"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">話し方のサンプル</label>
                <textarea
                  value={form.speech_samples}
                  onChange={e => setForm({ ...form, speech_samples: e.target.value })}
                  rows={3}
                  className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-purple-500 outline-none"
                  placeholder="例: 「ねえみんな！今日も元気？わたしはめちゃくちゃ元気だよ！」"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">NG表現</label>
                <textarea
                  value={form.ng_expressions}
                  onChange={e => setForm({ ...form, ng_expressions: e.target.value })}
                  rows={2}
                  className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-purple-500 outline-none"
                  placeholder="例: 暴言・差別表現・特定の政治的発言"
                />
              </div>

              {/* 音声設定 */}
              <div className="border-t border-gray-100 pt-5">
                <h3 className="font-medium text-gray-700 mb-3">🎵 音声設定</h3>
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">TTSプロバイダー</label>
                    <select
                      value={form.tts_provider}
                      onChange={e => setForm({ ...form, tts_provider: e.target.value })}
                      className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-purple-500 outline-none"
                    >
                      <option value="mock">モック（無音）</option>
                      <option value="openai">OpenAI TTS</option>
                      <option value="elevenlabs">ElevenLabs</option>
                      <option value="voicevox">VOICEVOX</option>
                    </select>
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">声の種類/ID</label>
                    <input
                      value={form.voice_type}
                      onChange={e => setForm({ ...form, voice_type: e.target.value })}
                      className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-purple-500 outline-none"
                      placeholder="例: nova (OpenAI) / 1 (VOICEVOX)"
                    />
                  </div>
                </div>
                <div className="grid grid-cols-3 gap-4 mt-3">
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">
                      話速: {form.speech_rate}x
                    </label>
                    <input
                      type="range" min="0.5" max="2.0" step="0.1"
                      value={form.speech_rate}
                      onChange={e => setForm({ ...form, speech_rate: parseFloat(e.target.value) })}
                      className="w-full"
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">
                      ピッチ: {form.pitch}
                    </label>
                    <input
                      type="range" min="-1.0" max="1.0" step="0.1"
                      value={form.pitch}
                      onChange={e => setForm({ ...form, pitch: parseFloat(e.target.value) })}
                      className="w-full"
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">
                      感情強度: {form.emotion_strength}
                    </label>
                    <input
                      type="range" min="0.0" max="1.0" step="0.1"
                      value={form.emotion_strength}
                      onChange={e => setForm({ ...form, emotion_strength: parseFloat(e.target.value) })}
                      className="w-full"
                    />
                  </div>
                </div>
              </div>

              <div className="flex items-center gap-2">
                <input
                  type="checkbox"
                  id="is_default"
                  checked={form.is_default}
                  onChange={e => setForm({ ...form, is_default: e.target.checked })}
                  className="rounded"
                />
                <label htmlFor="is_default" className="text-sm text-gray-700">デフォルトキャラクターとして設定</label>
              </div>

              <div className="flex gap-3 pt-4 border-t border-gray-100">
                <button
                  type="button"
                  onClick={() => setShowForm(false)}
                  className="flex-1 border border-gray-300 text-gray-700 py-2.5 rounded-lg text-sm font-medium hover:bg-gray-50"
                >
                  キャンセル
                </button>
                <button
                  type="submit"
                  className="flex-1 bg-purple-600 hover:bg-purple-700 text-white py-2.5 rounded-lg text-sm font-medium"
                >
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
