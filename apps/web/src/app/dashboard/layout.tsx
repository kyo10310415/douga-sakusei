'use client'
import { useState, useEffect, ReactNode } from 'react'
import Link from 'next/link'
import { usePathname, useRouter } from 'next/navigation'
import { useAuth } from '@/hooks/useAuth'

const navItems = [
  { href: '/dashboard', label: 'ダッシュボード', icon: '📊' },
  { href: '/dashboard/weekly', label: '週次データ', icon: '📅' },
  { href: '/dashboard/jobs', label: '動画生成ジョブ', icon: '🎬' },
  { href: '/dashboard/characters', label: 'キャラクター設定', icon: '🎭' },
  { href: '/dashboard/themes', label: '動画テーマ設定', icon: '🎯' },
  { href: '/dashboard/analysis', label: 'AI分析', icon: '🤖' },
  { href: '/dashboard/settings', label: '設定', icon: '⚙️' },
]

const promoNavItems = [
  { href: '/dashboard/promo', label: '宣伝ダッシュボード', icon: '📣' },
  { href: '/dashboard/promo/generate', label: '投稿生成', icon: '✨' },
  { href: '/dashboard/promo/posts', label: '投稿管理', icon: '📝' },
  { href: '/dashboard/promo/assets', label: '素材管理', icon: '🖼️' },
  { href: '/dashboard/promo/analytics', label: '宣伝分析', icon: '📈' },
]

export default function DashboardLayout({ children }: { children: ReactNode }) {
  const { user, loading, logout } = useAuth()
  const router = useRouter()
  const pathname = usePathname()
  const [sidebarOpen, setSidebarOpen] = useState(true)

  useEffect(() => {
    if (!loading && !user) {
      router.push('/login')
    }
  }, [user, loading, router])

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50">
        <div className="text-center">
          <div className="text-4xl animate-pulse mb-4">🎭</div>
          <p className="text-gray-500">読み込み中...</p>
        </div>
      </div>
    )
  }

  if (!user) return null

  return (
    <div className="min-h-screen bg-gray-50 flex">
      {/* サイドバー */}
      <aside className={`${sidebarOpen ? 'w-64' : 'w-16'} bg-gray-900 text-white transition-all duration-200 flex flex-col`}>
        <div className="p-4 border-b border-gray-700 flex items-center justify-between">
          {sidebarOpen && (
            <div className="flex items-center gap-2">
              <span className="text-2xl">🎭</span>
              <span className="font-bold text-sm">VTuber Studio</span>
            </div>
          )}
          <button
            onClick={() => setSidebarOpen(!sidebarOpen)}
            className="text-gray-400 hover:text-white p-1 rounded"
          >
            {sidebarOpen ? '◀' : '▶'}
          </button>
        </div>

        <nav className="flex-1 py-4 overflow-y-auto">
          {navItems.map(item => (
            <Link
              key={item.href}
              href={item.href}
              className={`flex items-center gap-3 px-4 py-3 text-sm hover:bg-gray-700 transition-colors ${
                pathname === item.href || (item.href !== '/dashboard' && pathname.startsWith(item.href + '/'))
                  ? 'bg-purple-700 text-white' 
                  : 'text-gray-300'
              }`}
            >
              <span className="text-lg flex-shrink-0">{item.icon}</span>
              {sidebarOpen && <span>{item.label}</span>}
            </Link>
          ))}

          {/* コンサル宣伝セクション */}
          {sidebarOpen && (
            <div className="px-4 pt-4 pb-1">
              <span className="text-xs font-semibold text-gray-500 uppercase tracking-wider">
                コンサル宣伝
              </span>
            </div>
          )}
          {!sidebarOpen && (
            <div className="border-t border-gray-700 my-2" />
          )}
          {promoNavItems.map(item => (
            <Link
              key={item.href}
              href={item.href}
              className={`flex items-center gap-3 px-4 py-3 text-sm hover:bg-gray-700 transition-colors ${
                pathname === item.href || (item.href !== '/dashboard/promo' && pathname.startsWith(item.href + '/'))
                  ? 'bg-pink-700 text-white'
                  : 'text-gray-300'
              }`}
            >
              <span className="text-lg flex-shrink-0">{item.icon}</span>
              {sidebarOpen && <span>{item.label}</span>}
            </Link>
          ))}
        </nav>

        <div className="p-4 border-t border-gray-700">
          {sidebarOpen && (
            <div className="mb-2 text-xs text-gray-400">
              {user.username}
              {user.is_admin && <span className="ml-1 bg-purple-700 px-1 rounded">管理者</span>}
            </div>
          )}
          <button
            onClick={logout}
            className="flex items-center gap-2 text-gray-400 hover:text-white text-sm"
          >
            <span>🚪</span>
            {sidebarOpen && <span>ログアウト</span>}
          </button>
        </div>
      </aside>

      {/* メインコンテンツ */}
      <main className="flex-1 overflow-auto">
        {children}
      </main>
    </div>
  )
}
