import { Bell, BookOpenCheck, Menu, Search } from 'lucide-react'
import { navItems } from '../data/appData'

export function Shell({ activeSection, apiStatus, children }) {
  const statusTone = apiStatus === 'ok' ? 'bg-emerald-500' : apiStatus === 'offline' ? 'bg-red-500' : 'bg-amber-500'

  return (
    <div className="min-h-screen bg-slate-50 text-slate-950">
      <aside className="fixed inset-y-0 left-0 z-30 hidden w-72 border-r border-slate-200 bg-white lg:flex lg:flex-col">
        <div className="flex h-20 items-center gap-3 border-b border-slate-200 px-6">
          <div className="flex size-11 items-center justify-center rounded-lg bg-slate-950 text-white">
            <BookOpenCheck className="size-5" />
          </div>
          <div>
            <p className="text-xs font-semibold uppercase tracking-[0.18em] text-slate-500">Course Finder</p>
            <h1 className="text-lg font-semibold">AI Workbench</h1>
          </div>
        </div>

        <nav className="flex-1 space-y-1 px-4 py-6">
          {navItems.map((item) => {
            const Icon = item.icon
            const selected = item.label === activeSection
            return (
              <a
                key={item.label}
                href={`#${item.label.toLowerCase()}`}
                className={`flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium transition ${
                  selected ? 'bg-slate-950 text-white' : 'text-slate-600 hover:bg-slate-100 hover:text-slate-950'
                }`}
              >
                <Icon className="size-4" />
                {item.label}
              </a>
            )
          })}
        </nav>

        <div className="border-t border-slate-200 p-4">
          <div className="rounded-lg border border-slate-200 bg-slate-50 p-4">
            <p className="text-sm font-semibold">API status</p>
            <div className="mt-3 flex items-center justify-between">
              <span className="text-sm text-slate-600">{apiStatus}</span>
              <span className={`size-2.5 rounded-full ${statusTone}`} />
            </div>
          </div>
        </div>
      </aside>

      <div className="lg:pl-72">
        <header className="sticky top-0 z-20 border-b border-slate-200 bg-white/90 backdrop-blur">
          <div className="flex h-16 items-center justify-between gap-4 px-4 sm:px-6 lg:px-8">
            <div className="flex items-center gap-3">
              <button className="inline-flex size-10 items-center justify-center rounded-lg border border-slate-200 lg:hidden" type="button">
                <Menu className="size-5" />
              </button>
              <div>
                <p className="text-xs font-semibold uppercase tracking-[0.18em] text-slate-500">Enterprise learner intelligence</p>
                <h2 className="text-base font-semibold sm:text-lg">Personalized course discovery</h2>
              </div>
            </div>

            <div className="hidden items-center gap-3 md:flex">
              <div className="flex h-10 w-72 items-center gap-2 rounded-lg border border-slate-200 bg-slate-50 px-3 text-sm text-slate-500">
                <Search className="size-4" />
                Search learners, paths, courses
              </div>
              <button className="inline-flex size-10 items-center justify-center rounded-lg border border-slate-200 bg-white" type="button">
                <Bell className="size-4" />
              </button>
            </div>
          </div>
        </header>

        <main className="px-4 py-6 sm:px-6 lg:px-8">{children}</main>
      </div>
    </div>
  )
}

