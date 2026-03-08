import { Outlet } from 'react-router-dom'

/**
 * Dashboard layout wrapper: sidebar + main content area.
 */
export default function DashboardLayout({ title = 'SmartRiver Dashboard' }) {
  return (
    <div className="min-h-screen flex bg-slate-50">
      <aside className="w-60 bg-white border-r border-slate-200 p-4">
        <h2 className="font-semibold text-cyan-700">{title}</h2>
        <nav className="mt-4 space-y-1 text-sm text-slate-600">
          <a href="/dashboard" className="block py-1 hover:text-cyan-600">Overview</a>
          <a href="/river-health" className="block py-1 hover:text-cyan-600">River Health</a>
          <a href="/forecast" className="block py-1 hover:text-cyan-600">Forecast</a>
          <a href="/alerts" className="block py-1 hover:text-cyan-600">Alerts</a>
        </nav>
      </aside>
      <main className="flex-1 p-6 overflow-auto">
        <Outlet />
      </main>
    </div>
  )
}
