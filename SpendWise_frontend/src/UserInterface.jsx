// ─── NOTE: All original JSX structure and Tailwind classes preserved.
//   Changes:
//   1. Settings: email/password change flows + correct alert toggles (5 toggles w/ thresholds)
//   2. Add Expense: top-down dropdown w/ 2 children (manual add + CSV import/download)
//   3. History: custom date range picker added
//   4. Dashboard: CPI comparison graph (scrollable, multi-line, up to 5 categories)
//   5. Swipe gestures: Fixed horizontal overflow white-space bugs, protected bottom nav, smoothed animations, and expanded safe zones.

import {
  BarChart2,
  Bell,
  Bell as BellIcon,
  Bike,
  Briefcase,
  BusFront,
  CalendarDays,
  Car,
  Check,
  CheckCircle2,
  ChevronDown,
  ChevronLeft,
  ChevronRight,
  ChevronUp,
  Clock,
  Download, FileText,
  Film,
  Footprints,
  Heart,
  Info,
  LayoutDashboard,
  Leaf,
  Lightbulb,
  Lock, Mail,
  MessageCircle,
  Moon,
  PieChart as PieChartIcon,
  Plus,
  RefreshCcw,
  Settings,
  ShoppingCart,
  Sliders,
  Sparkles,
  Target,
  Train,
  TrendingDown, TrendingUp,
  Upload,
  User, Users,
  Utensils,
  Wallet,
  X,
  Zap
} from 'lucide-react'
import { createElement, useCallback, useEffect, useRef, useState } from 'react'
import {
  CartesianGrid,
  Cell,
  Line,
  LineChart,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis, YAxis
} from 'recharts'

// ─── Auth / token-refresh lock ────────────────────────────────────────────────
let isRefreshing = null

// ─── Category maps ─────────────────────────────────────────────────────────────
const BACKEND_TO_CAT = {
  'Food & Dining': 'food',
  'Transport':     'transport',
  'Utilities':     'utilities',
  'Entertainment': 'entertainment',
  'Shopping':      'shopping',
  'Healthcare':    'healthcare',
  'Other':         'others',
}
const CAT_TO_BACKEND = Object.fromEntries(
  Object.entries(BACKEND_TO_CAT).map(([k, v]) => [v, k])
)

function mapExpense(e) {
  const raw = e.DatePurchased ?? ''
  let dateLabel = raw
  try {
    dateLabel = new Date(raw + 'T00:00:00').toLocaleDateString('en-US', { month: 'short', day: 'numeric' })
  } catch { /* keep raw string */ }
  return {
    id:        e.Id,
    name:      e.ItemName,
    category:  BACKEND_TO_CAT[e.Type] ?? 'others',
    date:      dateLabel,
    amount:    e.AmountSpent,
    recurring: e.Recurring,
    _raw:      e,
  }
}

function transformForecastData(data) {
  if (!data || !data.historical || data.historical.length === 0) return []
  const hist = data.historical
  const fore = data.forecast ?? []
  return [
    ...hist.map(d => ({ week: d.month, actual: d.amount })),
    ...fore.map((d, i) => ({
      week:     d.month,
      actual:   i === 0 ? hist[hist.length - 1].amount : undefined,
      forecast: d.amount,
    })),
  ]
}

const TRANSPORT_UI_TO_BACKEND = { car: 'gasoline', public: 'bus', bike: 'bike', taxi: 'taxi' }

function cn(...classes) { return classes.filter(Boolean).join(' ') }

const CATEGORIES = [
  { id: 'food',          label: 'Food & Dining',  icon: Utensils,    color: '#f97316', bg: 'bg-orange-50',  text: 'text-orange-500' },
  { id: 'transport',     label: 'Transport',       icon: Car,         color: '#3b82f6', bg: 'bg-blue-50',    text: 'text-blue-500'   },
  { id: 'utilities',     label: 'Utilities',       icon: Zap,         color: '#eab308', bg: 'bg-yellow-50',  text: 'text-yellow-500' },
  { id: 'entertainment', label: 'Entertainment',   icon: Film,        color: '#8b5cf6', bg: 'bg-violet-50',  text: 'text-violet-500' },
  { id: 'shopping',      label: 'Shopping',        icon: ShoppingCart,color: '#ec4899', bg: 'bg-pink-50',    text: 'text-pink-500'   },
  { id: 'healthcare',    label: 'Healthcare',      icon: Heart,       color: '#ef4444', bg: 'bg-red-50',     text: 'text-red-500'    },
  { id: 'others',        label: 'Others',          icon: Briefcase,   color: '#94a3b8', bg: 'bg-slate-50',   text: 'text-slate-400'  },
]

// ─── Shared UI Primitives ─────────────────────────────────────────────────────
function Card({ children, className = '', ...props }) {
  return (
    <div className={cn('bg-card rounded-2xl border border-border shadow-sm', className)} {...props}>
      {children}
    </div>
  )
}

function SectionHeader({ icon: Icon, title, action }) {
  return (
    <div className="flex items-center justify-between mb-4">
      <div className="flex items-center gap-2">
        <div className="w-8 h-8 rounded-xl bg-accent flex items-center justify-center">
          {createElement(Icon, { className: 'w-4 h-4 text-primary' })}
        </div>
        <h2 className="text-sm font-semibold text-foreground">{title}</h2>
      </div>
      {action}
    </div>
  )
}

// ─── OTP Code Input (auto-advance digits) ─────────────────────────────────────
function OtpInput({ length = 6, value, onChange }) {
  const refs = useRef([])
  const digits = value.split('')

  function handleChange(i, e) {
    const ch = e.target.value.replace(/\D/g, '').slice(-1)
    const next = [...digits]
    next[i] = ch
    const str = next.join('')
    onChange(str)
    if (ch && i < length - 1) refs.current[i + 1]?.focus()
  }
  function handleKeyDown(i, e) {
    if (e.key === 'Backspace' && !digits[i] && i > 0) refs.current[i - 1]?.focus()
  }
  return (
    <div className="flex gap-2 justify-center">
      {Array.from({ length }).map((_, i) => (
        <input
          key={i}
          ref={element => { refs.current[i] = element }}
          type="text"
          inputMode="numeric"
          maxLength={1}
          value={digits[i] ?? ''}
          onChange={e => handleChange(i, e)}
          onKeyDown={e => handleKeyDown(i, e)}
          className="w-10 h-12 rounded-xl bg-muted border border-border text-center text-lg font-bold text-foreground focus:outline-none focus:ring-2 focus:ring-primary/30"
        />
      ))}
    </div>
  )
}

// ─── PAGE: DASHBOARD ──────────────────────────────────────────────────────────
function ForecastTooltip({ active, payload, label }) {
  if (!active || !payload || payload.length === 0) return null
  return (
    <div className="bg-card border border-border rounded-xl shadow-md px-3 py-2 text-xs">
      <p className="text-muted-foreground mb-1 font-medium">{label}</p>
      {payload.map((p) => (
        <p key={p.name} style={{ color: p.color }} className="font-semibold">
          {p.name === 'forecast' ? 'Forecast' : 'Actual'}: ${p.value}
        </p>
      ))}
    </div>
  )
}

function CpiTooltip({ active, payload, label }) {
  if (!active || !payload || !payload.length) return null
  return (
    <div className="bg-card border border-border rounded-xl shadow-md px-3 py-2 text-xs max-w-[180px]">
      <p className="text-muted-foreground mb-1 font-medium">{label}</p>
      {payload.map(p => (
        <p key={p.dataKey} style={{ color: p.color }} className="font-semibold truncate">
          {p.dataKey}: {p.value?.toFixed(2)}
        </p>
      ))}
    </div>
  )
}

function PieTooltip({ active, payload }) {
  if (!active || !payload || payload.length === 0) return null
  
  const data = payload[0].payload
  
  if (data.isEmpty) {
    return (
      <div className="bg-card border border-border rounded-xl shadow-md px-3 py-2 text-xs">
        <p className="font-medium text-muted-foreground">No spending yet</p>
      </div>
    )
  }

  const percent = data.percent ?? payload[0].percent ?? 0

  return (
    <div className="bg-card border border-border rounded-xl shadow-md px-3 py-2 text-xs">
      <p className="font-semibold text-foreground">{payload[0].name}</p>
      <p className="text-muted-foreground">${payload[0].value.toFixed(2)}</p>
      <p className="text-muted-foreground">{(percent * 100).toFixed(1)}%</p>
    </div>
  )
}

function SpendingPieCard({ pieData = [] }) {
  const isZero = pieData.length === 0

  const chartData = isZero
    ? [{ name: 'No spending yet', value: 1, color: '#f8fafc', isEmpty: true }]
    : pieData

  const legendData = isZero
    ? CATEGORIES.map(c => ({ name: c.label, value: 0, color: c.color }))
    : pieData

  return (
    <section aria-label="Spending by Category">
      <Card className="p-5">
        <SectionHeader icon={PieChartIcon} title="Monthly Costs by Category" />
        <div className="h-52 relative">
          
          {isZero && (
            <div className="absolute inset-0 flex flex-col items-center justify-center pointer-events-none animate-in fade-in duration-700">
              <p className="text-xl font-bold text-muted-foreground/30">0%</p>
            </div>
          )}
          
          <ResponsiveContainer width="100%" height="100%">
            <PieChart>
              <Pie 
                data={chartData} 
                cx="50%" 
                cy="50%" 
                innerRadius={52} 
                outerRadius={80}
                paddingAngle={isZero ? 0 : 3} 
                dataKey="value"
                stroke="none"
                isAnimationActive={true}
                animationBegin={0}
                animationDuration={800}
                animationEasing="ease-out"
              >
                {chartData.map((entry, i) => (
                  <Cell key={i} fill={entry.color} />
                ))}
              </Pie>
              <Tooltip content={<PieTooltip />} />
            </PieChart>
          </ResponsiveContainer>
        </div>
        
        <div className="grid grid-cols-2 gap-1.5 mt-2">
          {legendData.map((d) => (
            <div key={d.name} className="flex items-center gap-2">
              <span className="w-2.5 h-2.5 rounded-full shrink-0" style={{ background: d.color }} />
              <span className="text-xs text-muted-foreground truncate">{d.name}</span>
              <span className="text-xs font-medium text-foreground ml-auto">${(d.value || 0).toFixed(0)}</span>
            </div>
          ))}
        </div>
      </Card>
    </section>
  )
}

function MonthlySummaryCard({ totalCommitted = 0, paidExpenses = 0, limitAmount = 0, spentPct = 0, remaining = 0, realtimeSavings = 0, monthlyRecurring = 0, isIncomeFallback = false }) {
  const now = new Date()
  const monthLabel = now.toLocaleDateString('en-US', { month: 'long', year: 'numeric' })
  
  // Dynamically change the labels based on whether it's using Income or Budget
  const labelText = isIncomeFallback ? 'income' : 'budget'
  const labelTextCap = isIncomeFallback ? 'Income' : 'Budget'

  return (
    <section aria-label="This Month Summary">
      <div className="bg-primary rounded-2xl p-5 text-primary-foreground shadow-sm">
        <div className="flex items-center justify-between mb-5">
          <p className="text-sm font-medium text-primary-foreground/70 uppercase tracking-wider">This Month</p>
          <span className="flex items-center gap-1 text-xs font-semibold bg-white/15 rounded-full px-3 py-1">
            <TrendingDown className="w-3 h-3" />{monthLabel}
          </span>
        </div>
        <p className="text-xs text-primary-foreground/60 mb-0.5">Paid + recurring plan</p>
        <p className="text-4xl font-bold tracking-tight">${totalCommitted.toFixed(2)}</p>
        <p className="text-xs text-primary-foreground/60 mb-1">
          ${paidExpenses.toFixed(2)} paid + ${monthlyRecurring.toFixed(2)}/mo recurring
        </p>
        <p className="text-sm text-primary-foreground/60 mb-5">of ${limitAmount.toLocaleString()} {labelText}</p>
        <div className="mb-3">
          <div className="flex justify-between text-xs text-primary-foreground/70 mb-2">
            <span>{spentPct}% used</span>
            <span>${remaining.toFixed(0)} left</span>
          </div>
          <div className="h-2 bg-white/20 rounded-full overflow-hidden">
            <div className="h-full bg-white rounded-full transition-all duration-700"
              style={{ width: `${Math.min(spentPct, 100)}%` }}
              role="progressbar" aria-valuenow={spentPct} aria-valuemin={0} aria-valuemax={100} />
          </div>
        </div>
        <div className="grid grid-cols-2 gap-3 mt-4">
          <div className="bg-white/10 rounded-xl p-3">
            <p className="text-xs text-primary-foreground/60 mb-0.5">{labelTextCap}</p>
            <p className="text-base font-semibold">${limitAmount.toLocaleString()}</p>
          </div>
          
          {/* REPLACE the Remaining box with Realtime Savings */}
          <div className="bg-white/10 rounded-xl p-3">
            <p className="text-xs text-primary-foreground/60 mb-0.5">Realtime Savings</p>
            <p className="text-base font-semibold">${realtimeSavings.toFixed(2)}</p>
          </div>
          
        </div>
      </div>
    </section>
  )
}
function InflationInsightsCard({ pir = 0, cpi = 0, hasPersonalData = false }) {
  const diff = +(pir - cpi).toFixed(1)
  return (
    <section aria-label="Inflation Insights">
      <Card className="p-5">
        <SectionHeader
          icon={TrendingUp} title="Inflation Insights"
          action={<button aria-label="More info" className="text-muted-foreground"><Info className="w-4 h-4" /></button>}
        />
        <div className={cn('border rounded-xl p-3 mb-4', hasPersonalData ? 'bg-amber-50 border-amber-100' : 'bg-muted border-border')}>
          <p className={cn('text-xs leading-relaxed', hasPersonalData ? 'text-amber-700' : 'text-muted-foreground')}>
            {!hasPersonalData
              ? <>Your Personal Inflation Rate needs comparable recent spending history to calculate.</>
              : diff > 0
              ? <>Your personal spending is rising <span className="font-bold text-amber-800">{diff}% faster</span> than the national average.</>
              : diff < 0
              ? <>Your personal spending is rising <span className="font-bold text-green-700">{Math.abs(diff)}% slower</span> than the national average.</>
              : <>Your personal spending matches the national average.</>
            }
          </p>
        </div>
        <div className="grid grid-cols-2 gap-3">
          {[
            { label: 'Your PIR',    value: hasPersonalData ? pir : null, sub: hasPersonalData ? 'Personal Inflation Rate' : 'Not enough history', barColor: 'bg-amber-400' },
            { label: 'National CPI',value: cpi, sub: 'Consumer Price Index',    barColor: 'bg-primary'   },
          ].map(item => (
            <div key={item.label} className="bg-muted rounded-xl p-4">
              <p className="text-xs text-muted-foreground mb-1 font-medium">{item.label}</p>
              <p className="text-2xl font-bold text-foreground">
                {item.value === null ? '—' : item.value.toFixed(1)}
                {item.value !== null && <span className="text-sm font-medium text-muted-foreground">%</span>}
              </p>
              <p className="text-xs text-muted-foreground mt-1">{item.sub}</p>
              <div className="mt-2 h-1.5 bg-border rounded-full overflow-hidden">
                <div className={cn('h-full rounded-full', item.barColor)}
                  style={{ width: `${Math.min(((item.value ?? 0) / 10) * 100, 100)}%` }} />
              </div>
            </div>
          ))}
        </div>
      </Card>
    </section>
  )
}

function SpendingForecastCard({ forecastChartData = [], projectedTotal = null }) {
  const hasData = forecastChartData.length > 0
  return (
    <section aria-label="Spending Forecast">
      <Card className="p-5">
        <SectionHeader icon={BarChart2} title="Spending Forecast"
          action={<span className="text-xs font-medium text-primary bg-accent px-2.5 py-1 rounded-full">6-month view</span>}
        />
        {hasData && projectedTotal != null && (
          <p className="text-xs text-muted-foreground mb-4 -mt-2">
            Projected end-of-month: <span className="font-semibold text-foreground">${projectedTotal.toFixed(0)}</span>
          </p>
        )}
        {hasData ? (
          <div className="h-44">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={forecastChartData} margin={{ top: 4, right: 8, left: -20, bottom: 0 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" vertical={false} />
                <XAxis dataKey="week" tick={{ fontSize: 11, fill: '#94a3b8' }} axisLine={false} tickLine={false} />
                <YAxis tick={{ fontSize: 11, fill: '#94a3b8' }} axisLine={false} tickLine={false} tickFormatter={v => `$${v}`} />
                <Tooltip content={<ForecastTooltip />} cursor={{ stroke: '#cbd5e1', strokeWidth: 1 }} />
                <Line type="monotone" dataKey="actual" stroke="oklch(0.55 0.18 248)" strokeWidth={2.5}
                  dot={{ r: 3.5, fill: 'oklch(0.55 0.18 248)', strokeWidth: 0 }} connectNulls={false} />
                <Line type="monotone" dataKey="forecast" stroke="oklch(0.55 0.18 248)" strokeWidth={2}
                  strokeDasharray="5 4" dot={{ r: 3, fill: 'white', stroke: 'oklch(0.55 0.18 248)', strokeWidth: 2 }}
                  connectNulls={false} />
              </LineChart>
            </ResponsiveContainer>
          </div>
        ) : (
          <div className="h-44 flex flex-col items-center justify-center text-center px-4">
            <p className="text-2xl mb-2">📈</p>
            <p className="text-sm font-semibold text-foreground mb-1">Not Enough Data Yet</p>
            <p className="text-xs text-muted-foreground leading-relaxed">
              Keep logging expenses — we need at least 3 months of history to build your forecast.
            </p>
          </div>
        )}
      </Card>
    </section>
  )
}

// ─── NEW: CPI Category Comparison Chart ───────────────────────────────────────
const CPI_LINE_COLORS = ['#3b82f6','#f97316','#8b5cf6','#10b981','#ec4899']

function readCpiPreferences() {
  let email = 'default'
  try { email = localStorage.getItem('user_email')?.trim().toLowerCase() || 'default' }
  catch { /* Use a shared fallback key if browser storage is unavailable. */ }
  const storageKey = `spendwise:cpi-comparison:${encodeURIComponent(email)}`
  try {
    const saved = JSON.parse(localStorage.getItem(storageKey) || 'null')
    const categories = Array.isArray(saved?.categories)
      ? [...new Set(saved.categories.filter(category => typeof category === 'string'))].slice(0, 5)
      : null
    const timeRange = [0, 12, 60, 120].includes(saved?.timeRange) ? saved.timeRange : 60
    return { storageKey, categories, timeRange }
  } catch {
    return { storageKey, categories: null, timeRange: 60 }
  }
}

function CPIComparisonCard({ fetchWithAuth }) {
  const [preferences] = useState(readCpiPreferences)
  const [categories,   setCategories]   = useState([])
  const [selected,     setSelected]     = useState(() => preferences.categories ?? [])
  const [chartData,    setChartData]    = useState([])
  const [loading,      setLoading]      = useState(false)
  const [searchTerm,   setSearchTerm]   = useState('')
  const [showPicker,   setShowPicker]   = useState(false)
  const [categoriesLoaded, setCategoriesLoaded] = useState(false)
  
  // NEW: Time range filter state (in months)
  const [timeRange,    setTimeRange]    = useState(preferences.timeRange) // Default to 5 Years
  const MAX_SELECT = 5

  useEffect(() => {
    if (!fetchWithAuth) return
    fetchWithAuth('/dashboard/cpi-categories')
      .then(r => {
        if (!r.ok) throw new Error('Failed to load CPI categories')
        return r.json()
      })
      .then(data => {
        if (!Array.isArray(data)) return
        setCategories(data)
        setSelected(current => {
          const restored = [...new Set(current.filter(category => data.includes(category)))].slice(0, MAX_SELECT)
          if (preferences.categories !== null) return restored
          const def = data.find(category => category === 'All Items')
          return def ? [def] : []
        })
        setCategoriesLoaded(true)
      })
      .catch(() => {})
  }, [fetchWithAuth, preferences])

  useEffect(() => {
    if (!categoriesLoaded) return
    try {
      localStorage.setItem(preferences.storageKey, JSON.stringify({ categories: selected, timeRange }))
    } catch { /* Keep the chart usable if browser storage is unavailable. */ }
  }, [categoriesLoaded, preferences.storageKey, selected, timeRange])

  useEffect(() => {
    if (!selected.length || !fetchWithAuth) return
    setLoading(true)
    const params = selected.map(c => `categories=${encodeURIComponent(c)}`).join('&')
    fetchWithAuth(`/dashboard/cpi-data?${params}`)
      .then(r => r.ok ? r.json() : null)
      .then(data => {
        if (data && Array.isArray(data)) setChartData(data)
      })
      .catch(() => {})
      .finally(() => setLoading(false))
  }, [fetchWithAuth, selected])

  function toggleCategory(cat) {
    setSelected(prev => {
      if (prev.includes(cat)) return prev.filter(c => c !== cat)
      if (prev.length >= MAX_SELECT) return prev
      return [...prev, cat]
    })
  }

  const filteredCategories = categories.filter(c =>
    c.toLowerCase().includes(searchTerm.toLowerCase())
  ).slice(0, 80)

  // NEW: Slice the data based on the selected time range
  const filteredData = chartData.slice(timeRange === 0 ? 0 : -timeRange)

  // NEW: Dynamically adjust point width so the line gradients look steep and readable
  let pointWidth = 8
  if (timeRange === 12) pointWidth = 30       // 1 Year: Spread out nicely
  else if (timeRange === 60) pointWidth = 12  // 5 Years: Fits on screen or small scroll
  else if (timeRange === 120) pointWidth = 8  // 10 Years: Moderate scroll
  
  const chartWidth = Math.max(340, (filteredData.length || 12) * pointWidth)

  return (
    <section aria-label="CPI Category Comparison">
      <Card className="p-5" data-no-swipe>
        <SectionHeader icon={TrendingUp} title="CPI Comparison"
          action={
            <button onClick={() => setShowPicker(p => !p)}
              className="text-xs font-medium text-primary bg-accent px-2.5 py-1 rounded-full flex items-center gap-1">
              <Sliders className="w-3 h-3" /> Select ({selected.length}/{MAX_SELECT})
            </button>
          }
        />

        {showPicker && (
          <div className="mb-4 border border-border rounded-2xl overflow-hidden">
            <div className="p-3 border-b border-border">
              <input
                type="text"
                placeholder="Search categories…"
                value={searchTerm}
                onChange={e => setSearchTerm(e.target.value)}
                className="w-full bg-muted rounded-xl px-3 py-2 text-xs text-foreground border border-border focus:outline-none focus:ring-2 focus:ring-primary/30 placeholder:text-muted-foreground"
              />
            </div>
            <div className="max-h-44 overflow-y-auto p-2 flex flex-wrap gap-1.5">
              {filteredCategories.map(cat => {
                const on = selected.includes(cat)
                const disabled = !on && selected.length >= MAX_SELECT
                return (
                  <button key={cat}
                    onClick={() => !disabled && toggleCategory(cat)}
                    className={cn(
                      'px-2.5 py-1 rounded-full text-xs font-medium border transition-colors',
                      on       ? 'bg-primary text-primary-foreground border-primary'
                               : disabled ? 'bg-muted text-muted-foreground/40 border-border cursor-not-allowed'
                               : 'bg-card text-muted-foreground border-border hover:bg-muted'
                    )}>
                    {cat}
                  </button>
                )
              })}
              {filteredCategories.length === 0 && (
                <p className="text-xs text-muted-foreground p-2">No categories match.</p>
              )}
            </div>
          </div>
        )}

        {selected.length > 0 && (
          <div className="flex flex-wrap gap-1.5 mb-4">
            {selected.map((cat, i) => (
              <span key={cat} className="flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-medium"
                style={{ background: CPI_LINE_COLORS[i] + '22', color: CPI_LINE_COLORS[i], border: `1px solid ${CPI_LINE_COLORS[i]}44` }}>
                {cat}
                <button onClick={() => toggleCategory(cat)} className="ml-0.5">
                  <X className="w-2.5 h-2.5" />
                </button>
              </span>
            ))}
          </div>
        )}

        {/* NEW: Time Range Selector */}
        {selected.length > 0 && chartData.length > 0 && !loading && (
          <div className="flex items-center justify-between mb-3">
            <div className="flex gap-1.5 bg-muted p-1 rounded-xl">
              {[
                { label: '1Y', val: 12 }, 
                { label: '5Y', val: 60 }, 
                { label: '10Y', val: 120 }, 
                { label: 'All', val: 0 }
              ].map(t => (
                <button key={t.label} onClick={() => setTimeRange(t.val)}
                  className={cn(
                    'px-2.5 py-1 rounded-lg text-[10px] font-semibold transition-colors',
                    timeRange === t.val ? 'bg-card text-foreground shadow-sm' : 'text-muted-foreground hover:text-foreground'
                  )}>
                  {t.label}
                </button>
              ))}
            </div>
            <p className="text-[10px] text-muted-foreground font-medium">Base: 2024=100</p>
          </div>
        )}

        {loading ? (
          <div className="h-44 flex items-center justify-center">
            <p className="text-xs text-muted-foreground">Loading CPI data…</p>
          </div>
        ) : selected.length === 0 ? (
          <div className="h-44 flex flex-col items-center justify-center text-center px-4">
            <p className="text-2xl mb-2">📊</p>
            <p className="text-sm font-semibold text-foreground mb-1">Select Categories</p>
            <p className="text-xs text-muted-foreground">Tap "Select" above to choose up to 5 CPI categories to compare.</p>
          </div>
        ) : chartData.length === 0 ? (
          <div className="h-44 flex items-center justify-center">
            <p className="text-xs text-muted-foreground">No CPI data available.</p>
          </div>
        ) : (
          <div className="overflow-x-auto -mx-1 no-scrollbar">
            <div style={{ width: chartWidth, minWidth: '100%' }}>
              <LineChart width={chartWidth} height={176} data={filteredData} margin={{ top: 4, right: 12, left: -16, bottom: 0 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" vertical={false} />
                <XAxis dataKey="month" tick={{ fontSize: 10, fill: '#94a3b8' }} axisLine={false} tickLine={false}
                  interval={Math.max(0, Math.floor(filteredData.length / 6) - 1)} />
                  
                {/* NEW: domain={['auto', 'auto']} prevents graph from starting at 0, revealing tiny gradients */}
                <YAxis domain={['auto', 'auto']} tick={{ fontSize: 10, fill: '#94a3b8' }} axisLine={false} tickLine={false} />
                
                <Tooltip content={<CpiTooltip />} cursor={{ stroke: '#cbd5e1', strokeWidth: 1 }} />
                {selected.map((cat, i) => (
                  <Line key={cat} type="monotone" dataKey={cat} stroke={CPI_LINE_COLORS[i]}
                    strokeWidth={2.5} dot={false} connectNulls={true} />
                ))}
              </LineChart>
            </div>
          </div>
        )}
      </Card>
    </section>
  )
}
function RecentTransactionsCard({ onNavigate, expenses = [] }) {
  const recent = expenses.filter(e => !e.recurring).slice(0, 4)
  return (
    <section aria-label="Recent Transactions">
      <Card className="overflow-hidden">
        <div className="flex items-center justify-between px-5 py-4 border-b border-border">
          <h2 className="text-sm font-semibold text-foreground">Recent Transactions</h2>
          <button onClick={() => onNavigate('history')}
            className="flex items-center gap-0.5 text-xs text-primary font-medium hover:underline">
            See all <ChevronRight className="w-3 h-3" />
          </button>
        </div>
        {recent.length === 0 ? (
          <p className="px-5 py-6 text-sm text-muted-foreground text-center">No transactions this month yet.</p>
        ) : (
          <ul>
            {recent.map((tx, idx) => {
              const cat = CATEGORIES.find(c => c.id === tx.category)
              const Icon = cat?.icon ?? Briefcase
              return (
                <li key={tx.id}>
                  <div className="flex items-center gap-3.5 px-5 py-4">
                    <div className={cn('w-10 h-10 rounded-xl flex items-center justify-center shrink-0', cat?.bg ?? 'bg-slate-50', cat?.text ?? 'text-slate-400')}>
                      <Icon className="w-4 h-4" />
                    </div>
                    <div className="flex-1 min-w-0">
                      <p className="text-sm font-medium text-foreground truncate">{tx.name}</p>
                      <p className="text-xs text-muted-foreground">{cat?.label} &middot; {tx.date}</p>
                    </div>
                    <span className="text-sm font-semibold text-foreground shrink-0">-${tx.amount.toFixed(2)}</span>
                  </div>
                  {idx < recent.length - 1 && <div className="h-px bg-border mx-5" />}
                </li>
              )
            })}
          </ul>
        )}
      </Card>
    </section>
  )
}

function DashboardPage({ onNavigate, fetchWithAuth, showToast, refreshKey }) {
  const [summary,   setSummary]   = useState(null)
  const [extras,    setExtras]    = useState({})
  const [expenses,  setExpenses]  = useState([])
  const [loading,   setLoading]   = useState(false)

  useEffect(() => {
    const load = async () => {
      setLoading(true)
      try {
        const [sumRes, infRes, foreRes, brkRes, expRes] = await Promise.all([
          fetchWithAuth('/dashboard/summary'),
          fetchWithAuth('/dashboard/inflation-rates'),
          fetchWithAuth('/dashboard/forecast'),
          fetchWithAuth('/dashboard/spending-breakdown'),
          fetchWithAuth('/categories/?period=this_month'),
        ])
        if (sumRes.ok) setSummary(await sumRes.json())
        setExtras({
          inflation: infRes.ok  ? await infRes.json().catch(() => null) : null,
          forecast:  foreRes.ok ? await foreRes.json().catch(() => null) : null,
          breakdown: brkRes.ok  ? await brkRes.json().catch(() => null) : null,
        })
        if (expRes.ok) {
          const raw = await expRes.json()
          if (Array.isArray(raw)) setExpenses(raw.flatMap(cat => (cat?.expenses ?? []).map(mapExpense)))
        }
      } catch (err) {
        showToast('Error loading dashboard: ' + err.message)
      } finally {
        setLoading(false)
      }
    }
    load()
  }, [fetchWithAuth, refreshKey, showToast])

  const totalSpent  = summary?.total_spent  ?? 0
  const totalBudget = summary?.total_budget ?? 0
  const monthlyIncome = summary?.monthly_income ?? 0 
  const monthlyRecurring = summary?.monthly_recurring ?? 0
  const totalCommitted = summary?.total_committed ?? totalSpent + monthlyRecurring

  const realtimeSavings = summary?.savings ?? 0

  // If budget is 0, fall back to showing income limits
  const isIncomeFallback = totalBudget === 0
  const limitAmount = isIncomeFallback ? monthlyIncome : totalBudget
  
  const spentPct    = limitAmount > 0 ? Math.round((totalCommitted / limitAmount) * 100) : 0
  const remaining   = limitAmount - totalCommitted

  const pieData = (() => {
    const bd = extras.breakdown
    if (!bd?.labels?.length) return []
    return bd.labels.map((label, i) => ({
      name:  label,
      value: bd.data[i] ?? 0,
      color: CATEGORIES.find(c => c.label === label)?.color ?? '#94a3b8',
    })).filter(d => d.value > 0)
  })()

  const pir = extras.inflation?.personal_inflation_rate ?? 0
  const cpi = extras.inflation?.national_inflation_rate ?? 0
  const hasPersonalInflationData = extras.inflation?.personal_inflation_available ?? false
  const forecastChartData  = transformForecastData(extras.forecast)
  const projectedTotal     = extras.forecast?.projected_total ?? null

  const emailName = (() => {
    const email = localStorage.getItem('user_email') ?? ''
    const name  = email.split('@')[0]
    return name ? name.charAt(0).toUpperCase() + name.slice(1) : ''
  })()
  const hour = new Date().getHours()
  const greeting = hour < 12 ? 'Good morning' : hour < 17 ? 'Good afternoon' : 'Good evening'

  return (
    <main className="max-w-md mx-auto pb-28">
      <div className="px-5 pt-4 pb-1">
        <p className="text-xs text-muted-foreground font-medium uppercase tracking-wider mb-0.5">Welcome back</p>
        <h1 className="text-xl font-bold text-foreground tracking-tight">
          {greeting}{emailName ? `, ${emailName}!` : '!'}
        </h1>
        {/* 2. Update the subtitle text to say "income" or "budget" */}
        <p className="text-sm text-muted-foreground mt-1">
          {loading ? 'Loading your dashboard…' : `Your expenses and recurring plan use ${spentPct}% of your monthly ${isIncomeFallback ? 'income' : 'budget'}.`}
        </p>
      </div>
      <div className="px-4 flex flex-col gap-4 pt-3">
        {/* 3. Pass the new limitAmount and fallback flag into the card */}
        {/* Pass the realtimeSavings prop into the card */}
        <MonthlySummaryCard 
           totalCommitted={totalCommitted}
           paidExpenses={totalSpent}
           limitAmount={limitAmount} 
           spentPct={spentPct} 
           remaining={remaining} 
           realtimeSavings={realtimeSavings} 
           monthlyRecurring={monthlyRecurring}
           isIncomeFallback={isIncomeFallback} 
        />
        <SpendingPieCard pieData={pieData} />
        <InflationInsightsCard pir={pir} cpi={cpi} hasPersonalData={hasPersonalInflationData} />
        <CPIComparisonCard fetchWithAuth={fetchWithAuth} />
        <SpendingForecastCard forecastChartData={forecastChartData} projectedTotal={projectedTotal} />
        <RecentTransactionsCard expenses={expenses} onNavigate={onNavigate} />
      </div>
    </main>
  )
}

// ─── PAGE: HISTORY ────────────────────────────────────────────────────────────
const PERIOD_OPTIONS = [
  { label: 'This Month', value: 'this_month' },
  { label: 'Custom',     value: 'custom'     },
]

function CategoryRow({ cat, expenses, onDelete, onEdit }) {
  const [open, setOpen] = useState(false)
  const total = expenses.reduce((s, e) => s + e.amount, 0)
  if (expenses.length === 0) return null
  const Icon = cat.icon
  return (
    <div className="border border-border rounded-2xl overflow-hidden">
      <button className="w-full flex items-center gap-3 px-4 py-3.5 bg-card hover:bg-muted/50 transition-colors"
        onClick={() => setOpen(o => !o)} aria-expanded={open}>
        <div className={cn('w-9 h-9 rounded-xl flex items-center justify-center shrink-0', cat.bg, cat.text)}>
          <Icon className="w-4 h-4" />
        </div>
        <div className="flex-1 text-left">
          <p className="text-sm font-medium text-foreground">{cat.label}</p>
          <p className="text-xs text-muted-foreground">{expenses.length} transaction{expenses.length !== 1 ? 's' : ''}</p>
        </div>
        <span className="text-sm font-semibold text-foreground mr-2">${total.toFixed(2)}</span>
        {open ? <ChevronUp className="w-4 h-4 text-muted-foreground" /> : <ChevronDown className="w-4 h-4 text-muted-foreground" />}
      </button>
      {open && (
        <div className="border-t border-border bg-muted/30">
          {expenses.map((tx, idx) => (
            <div key={tx.id}>
              <div className="flex items-center gap-3 px-4 py-3">
                <div className="flex-1">
                  <p className="text-sm text-foreground font-medium">{tx.name}</p>
                  <p className="text-xs text-muted-foreground">{tx.date}</p>
                </div>
                <span className="text-sm font-semibold text-foreground">-${tx.amount.toFixed(2)}</span>
                {onEdit   && <button onClick={() => onEdit(tx)}   className="ml-2 text-muted-foreground hover:text-foreground transition-colors"><Settings className="w-3.5 h-3.5" /></button>}
                {onDelete && <button onClick={() => onDelete(tx)} className="ml-1 text-muted-foreground hover:text-destructive transition-colors"><X className="w-3.5 h-3.5" /></button>}
              </div>
              {idx < expenses.length - 1 && <div className="h-px bg-border mx-4" />}
            </div>
          ))}
          <div className="px-4 py-2 border-t border-border flex justify-between">
            <span className="text-xs text-muted-foreground font-medium">Subtotal</span>
            <span className="text-xs font-bold text-foreground">${total.toFixed(2)}</span>
          </div>
        </div>
      )}
    </div>
  )
}

function HistoryPage({ fetchWithAuth, showToast, refreshKey }) {
  const [period,      setPeriod]      = useState('this_month')
  const [tab,         setTab]         = useState('expenses')
  const [expenses,    setExpenses]    = useState([])
  const [basketItems, setBasketItems] = useState([])
  const [loading,     setLoading]     = useState(false)
  const [customFrom,  setCustomFrom]  = useState('')
  const [customTo,    setCustomTo]    = useState('')
  const [appliedRange, setAppliedRange] = useState(null)
  const [showCustom,  setShowCustom]  = useState(false)

  const fetchExpenses = useCallback(async (p, from, to) => {
    setLoading(true)
    try {
      let url = `/categories/?period=${p}`
      if (p === 'custom' && from && to) {
        url = `/categories/?period=custom&from=${from}&to=${to}`
      }
      const res = await fetchWithAuth(url)
      if (res.ok) {
        const data = await res.json()
        if (Array.isArray(data)) {
          setExpenses(data.flatMap(cat => (cat?.expenses ?? []).map(mapExpense)))
        }
      } else {
        showToast('Failed to load expenses')
      }
    } catch (err) {
      showToast('Error: ' + err.message)
    } finally {
      setLoading(false)
    }
  }, [fetchWithAuth])

  const fetchBasket = useCallback(async () => {
    try {
      const res = await fetchWithAuth('/basket/')
      if (res.ok) {
        const data = await res.json()
        if (Array.isArray(data)) {
          setBasketItems(data.flatMap(s =>
            (s?.Basket ?? []).map(e => ({
              id:       e.Id,
              name:     e.ItemName,
              category: BACKEND_TO_CAT[e.Type] ?? 'others',
              date:     '',
              amount:   e.AmountSpent,
              recurring: true,
              _raw:     e,
            }))
          ))
        }
      }
    } catch { /* silent */ }
  }, [fetchWithAuth])

  const reloadCurrentExpenses = useCallback(() => {
    if (period === 'custom') {
      if (appliedRange) return fetchExpenses('custom', appliedRange.from, appliedRange.to)
      return Promise.resolve()
    }
    return fetchExpenses(period)
  }, [period, appliedRange, fetchExpenses])

  useEffect(() => {
    reloadCurrentExpenses()
    fetchBasket()
  }, [reloadCurrentExpenses, fetchBasket, refreshKey])

  const handleDeleteExpense = async (tx) => {
    if (!window.confirm('Delete this expense?')) return
    const res = await fetchWithAuth(`/categories/${tx.id}`, { method: 'DELETE' })
    if (res.ok || res.status === 204) { showToast('Deleted'); reloadCurrentExpenses() }
    else showToast('Delete failed')
  }

  const handleDeleteBasket = async (tx) => {
    if (!window.confirm('Delete this basket item?')) return
    const res = await fetchWithAuth('/basket/', {
      method: 'DELETE',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ BasketExpensesId: [tx.id] }),
    })
    if (res.ok || res.status === 204) { showToast('Deleted'); fetchBasket() }
    else showToast('Delete failed')
  }

  const totalPaidExpenses = expenses.reduce((s, e) => s + e.amount, 0)
  const totalMonthlyPlan  = basketItems.reduce((s, e) => s + e.amount, 0)

  function handlePeriodChange(val) {
    setPeriod(val)
    if (val === 'custom') {
      setShowCustom(true)
    } else {
      setShowCustom(false)
    }
  }

  function applyCustomRange() {
    if (!customFrom || !customTo) { showToast('Please select both dates'); return }
    if (customFrom > customTo) { showToast('Start date must be before end date'); return }
    setAppliedRange({ from: customFrom, to: customTo })
    setShowCustom(false)
  }

  return (
    <main className="max-w-md mx-auto pb-28">
      <div className="px-5 pt-5 pb-3">
        <h1 className="text-xl font-bold text-foreground">History</h1>
        <p className="text-sm text-muted-foreground mt-0.5">Track your spending over time.</p>
      </div>

      <div className="px-4 mb-4" data-no-swipe>
        <div className="flex gap-2 overflow-x-auto pb-1 no-scrollbar">
          {PERIOD_OPTIONS.map(p => (
            <button key={p.value} onClick={() => handlePeriodChange(p.value)}
              className={cn(
                'shrink-0 px-3.5 py-1.5 rounded-full text-xs font-medium transition-colors',
                period === p.value
                  ? 'bg-primary text-primary-foreground'
                  : 'bg-card border border-border text-muted-foreground hover:bg-muted'
              )}>
              {p.label}
            </button>
          ))}
        </div>
      </div>

      {(showCustom || period === 'custom') && (
        <div className="px-4 mb-4">
          <Card className="p-4">
            <p className="text-xs font-semibold text-muted-foreground uppercase tracking-wider mb-3">Custom Date Range</p>
            <div className="flex gap-3 mb-3">
              <div className="flex-1">
                <label className="text-xs text-muted-foreground mb-1 block">From</label>
                <input type="date" value={customFrom} onChange={e => setCustomFrom(e.target.value)}
                  className="w-full bg-muted rounded-xl px-3 py-2 text-sm text-foreground border border-border focus:outline-none focus:ring-2 focus:ring-primary/30" />
              </div>
              <div className="flex-1">
                <label className="text-xs text-muted-foreground mb-1 block">To</label>
                <input type="date" value={customTo} onChange={e => setCustomTo(e.target.value)}
                  className="w-full bg-muted rounded-xl px-3 py-2 text-sm text-foreground border border-border focus:outline-none focus:ring-2 focus:ring-primary/30" />
              </div>
            </div>
            <button onClick={applyCustomRange}
              className="w-full bg-primary text-primary-foreground rounded-xl py-2 text-xs font-semibold hover:opacity-90 transition-opacity">
              Apply Range
            </button>
          </Card>
        </div>
      )}

      <div className="px-4 mb-4 grid grid-cols-2 gap-3">
        <Card className="p-3.5">
          <p className="text-xs text-muted-foreground mb-0.5">Paid expenses</p>
          <p className="text-lg font-bold text-foreground">${totalPaidExpenses.toFixed(2)}</p>
        </Card>
        <Card className="p-3.5">
          <p className="text-xs text-muted-foreground mb-0.5">Monthly plan</p>
          <p className="text-lg font-bold text-foreground">${totalMonthlyPlan.toFixed(2)}</p>
        </Card>
      </div>

      <div className="px-4 mb-4">
        <div className="flex bg-muted rounded-xl p-1 gap-1">
          {[
            { key: 'expenses', label: 'Expenses', icon: CalendarDays },
            { key: 'basket',   label: 'Basket',   icon: RefreshCcw   },
          ].map(t => {
            const Icon = t.icon
            return (
              <button key={t.key} onClick={() => setTab(t.key)}
                className={cn(
                  'flex-1 flex items-center justify-center gap-1.5 py-2 rounded-lg text-xs font-medium transition-colors',
                  tab === t.key ? 'bg-card text-foreground shadow-sm' : 'text-muted-foreground hover:text-foreground'
                )}>
                <Icon className="w-3.5 h-3.5" />{t.label}
              </button>
            )
          })}
        </div>
      </div>

      {loading && <p className="px-5 text-sm text-muted-foreground text-center py-8">Loading…</p>}

      {!loading && (
        <div className="px-4 flex flex-col gap-3">
          {tab === 'expenses' ? (
            <>
              <p className="text-xs text-muted-foreground font-medium uppercase tracking-wider px-1">
                By Category — {period === 'custom' && customFrom && customTo
                  ? `${customFrom} → ${customTo}`
                  : PERIOD_OPTIONS.find(p => p.value === period)?.label}
              </p>
              {CATEGORIES.map(cat => {
                const catExpenses = expenses.filter(e => e.category === cat.id)
                return (
                  <CategoryRow key={cat.id} cat={cat} expenses={catExpenses}
                    onDelete={handleDeleteExpense} onEdit={null} />
                )
              })}
              {expenses.length === 0 && (
                <p className="text-sm text-muted-foreground text-center py-8">No expenses for this period.</p>
              )}
            </>
          ) : (
            <>
              <p className="text-xs text-muted-foreground font-medium uppercase tracking-wider px-1">
                Recurring Items
              </p>
              <Card className="overflow-hidden">
                <div className="px-5 py-3.5 bg-accent border-b border-border flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <RefreshCcw className="w-4 h-4 text-primary" />
                    <span className="text-sm font-semibold text-foreground">Monthly plan total</span>
                  </div>
                  <span className="text-sm font-bold text-primary">${totalMonthlyPlan.toFixed(2)}</span>
                </div>
                {basketItems.length === 0
                  ? <p className="px-5 py-6 text-sm text-muted-foreground text-center">No recurring items yet.</p>
                  : basketItems.map((tx, idx) => {
                    const cat = CATEGORIES.find(c => c.id === tx.category)
                    const Icon = cat?.icon ?? Briefcase
                    return (
                      <div key={tx.id}>
                        <div className="flex items-center gap-3.5 px-5 py-4">
                          <div className={cn('w-10 h-10 rounded-xl flex items-center justify-center shrink-0', cat?.bg ?? 'bg-slate-50', cat?.text ?? 'text-slate-400')}>
                            <Icon className="w-4 h-4" />
                          </div>
                          <div className="flex-1 min-w-0">
                            <p className="text-sm font-medium text-foreground">{tx.name}</p>
                            <p className="text-xs text-muted-foreground">{cat?.label} &middot; Monthly</p>
                          </div>
                          <div className="text-right shrink-0">
                            <p className="text-sm font-semibold text-foreground">${tx.amount.toFixed(2)}</p>
                            <p className="text-xs text-muted-foreground">/ mo</p>
                          </div>
                          <button onClick={() => handleDeleteBasket(tx)}
                            className="ml-2 text-muted-foreground hover:text-destructive transition-colors shrink-0">
                            <X className="w-3.5 h-3.5" />
                          </button>
                        </div>
                        {idx < basketItems.length - 1 && <div className="h-px bg-border mx-5" />}
                      </div>
                    )
                  })
                }
              </Card>
            </>
          )}
        </div>
      )}
    </main>
  )
}

// ─── PAGE: BUDGET ─────────────────────────────────────────────────────────────
const BGT_KEYS = {
  food: 'Food', 
  transport: 'Transport', 
  utilities: 'Utilities',
  entertainment: 'Entertainment', 
  shopping: 'Shopping', 
  healthcare: 'Healthcare', 
  others: 'Other'
}

const EMPTY_BUDGETS = {
  food: 0, transport: 0, utilities: 0, entertainment: 0,
  shopping: 0, healthcare: 0, others: 0,
}

function BudgetPage({ fetchWithAuth, showToast, refreshKey }) {
  const [mode,           setMode]           = useState('auto')
  const [budgets,        setBudgets]        = useState(EMPTY_BUDGETS)
  const [apiSuggestions, setApiSuggestions] = useState([])
  const [accepted,       setAccepted]       = useState({})
  const [dismissed,      setDismissed]      = useState({})
  const [saving,         setSaving]         = useState(false)
  const [expenses,       setExpenses]       = useState([])


  const [autoAvgs,       setAutoAvgs]       = useState({})
  const totalBudget = Object.values(budgets).reduce((s, v) => s + v, 0)

  useEffect(() => {
    const load = async () => {
      try {
        const [budRes, expRes] = await Promise.all([
          fetchWithAuth('/budget'),
          fetchWithAuth('/categories/?period=this_month'),
        ])
        if (budRes.ok) {
          const data = await budRes.json()
          if (data?.Settings) {
            setMode(data.Settings.AutoBudget ? 'auto' : 'manual')
            setBudgets({
              food:          data.Settings.Food          ?? 0,
              transport:     data.Settings.Transport     ?? 0,
              utilities:     data.Settings.Utilities     ?? 0,
              entertainment: data.Settings.Entertainment ?? 0,
              shopping:      data.Settings.Shopping      ?? 0,
              healthcare:    data.Settings.Healthcare    ?? 0,
              others:        data.Settings.Other         ?? 0,
            })
          }
          if (Array.isArray(data?.Suggestions)) {
            setApiSuggestions(data.Suggestions.map((s, i) => ({ ...s, id: `s_${i}` })))
          }
          // 3. Save the backend category averages to state
          if (data?.category_avgs) {
            setAutoAvgs(data.category_avgs)
          }
        }
        if (expRes.ok) {
          const raw = await expRes.json()
          if (Array.isArray(raw)) setExpenses(raw.flatMap(c => (c?.expenses ?? []).map(mapExpense)))
        }
      } catch { showToast('Error loading budget') }
    }
    load()
  }, [fetchWithAuth, refreshKey, showToast])

  const handleSave = async () => {
    setSaving(true)
    try {
      const payload = {
        AutoBudget: mode === 'auto',
        ...(mode === 'manual' ? {
          TotalBudget: totalBudget,
          CategoryBudgets: {
            Food:          budgets.food,
            Transport:     budgets.transport,
            Utilities:     budgets.utilities,
            Entertainment: budgets.entertainment,
            Shopping:      budgets.shopping,
            Healthcare:    budgets.healthcare,
            Other:         budgets.others,
          },
        } : {}),
      }
      const res = await fetchWithAuth('/budget/settings', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      })
      if (res.ok) showToast('Budget saved!')
      else {
        const d = await res.json().catch(() => ({}))
        showToast(d.detail || 'Error saving budget')
      }
    } catch { showToast('Error saving budget') }
    finally { setSaving(false) }
  }

  async function handleAccept(suggestion) { 
  // Update local UI using the suggestion ID
  setAccepted(a => ({ ...a, [suggestion.id]: true })); 
  
  try {
    await fetchWithAuth('/budget/suggestions/action', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        title: suggestion.title,
        category: suggestion.cat || 'Other', 
        action: 'accept'
      })
    });
  } catch {
    showToast("Failed to save goal.");
  }
}

async function handleDismiss(suggestion) { 
  // Update local UI using the suggestion ID
  setDismissed(d => ({ ...d, [suggestion.id]: true })); 
  
  try {
    await fetchWithAuth('/budget/suggestions/action', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        title: suggestion.title,
        category: suggestion.cat || 'Other',
        action: 'dismiss' 
      })
    });
  } catch {
    console.error("Failed to save dismissal status.");
  }
}

  const visibleSuggestions = apiSuggestions.filter(s => !dismissed[s.id])

  return (
    <main className="max-w-md mx-auto pb-28">
      <div className="px-5 pt-5 pb-3">
        <h1 className="text-xl font-bold text-foreground">Budget</h1>
        <p className="text-sm text-muted-foreground mt-0.5">Set and manage your monthly limits.</p>
      </div>

      <div className="px-4 mb-4">
        <div className="flex bg-muted rounded-xl p-1 gap-1">
          {[{ key: 'manual', label: 'Manual', icon: Sliders }, { key: 'auto', label: 'Auto', icon: Sparkles }].map(m => {
            const Icon = m.icon
            return (
              <button key={m.key} onClick={() => setMode(m.key)}
                className={cn(
                  'flex-1 flex items-center justify-center gap-1.5 py-2.5 rounded-lg text-xs font-medium transition-colors',
                  mode === m.key ? 'bg-card text-foreground shadow-sm' : 'text-muted-foreground hover:text-foreground'
                )}>
                <Icon className="w-3.5 h-3.5" />{m.label}
              </button>
            )
          })}
        </div>
      </div>

      <div className="px-4 mb-4">
        <div className="bg-primary rounded-2xl px-5 py-4 text-primary-foreground flex items-center justify-between">
          <div>
            <p className="text-xs text-primary-foreground/70 mb-0.5">Total Budget Set</p>
            <p className="text-2xl font-bold">${totalBudget.toLocaleString()}</p>
          </div>
          <Target className="w-8 h-8 text-primary-foreground/40" />
        </div>
      </div>

      {mode === 'manual' ? (
        <div className="px-4 flex flex-col gap-3 mb-6">
          <p className="text-xs text-muted-foreground font-medium uppercase tracking-wider px-1">Per Category Budget</p>
          {CATEGORIES.map(cat => {
            const val   = budgets[cat.id] ?? 0
            const spent = expenses.filter(e => e.category === cat.id).reduce((s, e) => s + e.amount, 0)
            const pct   = val > 0 ? Math.min(Math.round((spent / val) * 100), 100) : 0
            const over  = spent > val && val > 0
            const Icon  = cat.icon
            return (
              <Card key={cat.id} className="p-4">
                <div className="flex items-center gap-3 mb-3">
                  <div className={cn('w-8 h-8 rounded-xl flex items-center justify-center shrink-0', cat.bg, cat.text)}>
                    <Icon className="w-3.5 h-3.5" />
                  </div>
                  <span className="text-sm font-medium text-foreground flex-1">{cat.label}</span>
                  {over && <span className="text-xs text-red-500 font-medium">Over budget</span>}
                </div>
                <div className="flex items-center gap-3 mb-2">
                  <span className="text-xs text-muted-foreground w-12">$</span>
                  <input type="number" value={val} min={0} step={10}
                    onChange={e => setBudgets(b => ({ ...b, [cat.id]: Number(e.target.value) }))}
                    className="flex-1 text-sm font-semibold bg-muted rounded-xl px-3 py-1.5 border border-border focus:outline-none focus:ring-2 focus:ring-primary/30 text-foreground" />
                  <span className="text-xs text-muted-foreground w-16 text-right">spent ${spent.toFixed(0)}</span>
                </div>
                {val > 0 && (
                  <div className="h-1.5 bg-border rounded-full overflow-hidden">
                    <div className={cn('h-full rounded-full transition-all duration-500', over ? 'bg-red-400' : 'bg-primary')}
                      style={{ width: `${pct}%` }} />
                  </div>
                )}
              </Card>
            )
          })}
          <button onClick={handleSave} disabled={saving}
            className="w-full bg-primary text-primary-foreground rounded-2xl py-3 text-sm font-semibold hover:opacity-90 transition-opacity disabled:opacity-50 mt-2">
            {saving ? 'Saving…' : 'Save Budget'}
          </button>
        </div>
      ) : expenses.length === 0 ? (
        <div className="px-4 mb-6">
          <Card className="p-5">
            <div className="flex items-center gap-3 mb-3">
              <div className="w-10 h-10 rounded-2xl bg-accent flex items-center justify-center">
                <Sparkles className="w-5 h-5 text-primary" />
              </div>
              <div>
                <p className="text-sm font-semibold text-foreground">Auto Budget</p>
                <p className="text-xs text-muted-foreground">Based on your spending history</p>
              </div>
            </div>
            <div className="bg-muted rounded-xl p-4 text-center">
              <p className="text-sm font-medium text-foreground mb-1">No spending history yet</p>
              <p className="text-xs text-muted-foreground leading-relaxed">
                Start logging your expenses. Once you have at least one month of data, auto budget will calculate your limits automatically.
              </p>
            </div>
          </Card>
        </div>
      ) : (
        <div className="px-4 mb-6">
          <Card className="p-5">
            <div className="flex items-center gap-3 mb-4">
              <div className="w-10 h-10 rounded-2xl bg-accent flex items-center justify-center">
                <Sparkles className="w-5 h-5 text-primary" />
              </div>
              <div>
                <p className="text-sm font-semibold text-foreground">Auto Budget</p>
                <p className="text-xs text-muted-foreground">Based on your spending history</p>
              </div>
            </div>
            <div className="flex flex-col gap-2">
              {CATEGORIES.map(cat => {
                const suggested = autoAvgs[BGT_KEYS[cat.id]] ?? 0
                
                // Hide if there's no data for this category
                if (suggested <= 0) return null
                
                const Icon = cat.icon
                return (
                  <div key={cat.id} className="flex items-center gap-3 py-2 border-b border-border last:border-0">
                    <div className={cn('w-7 h-7 rounded-lg flex items-center justify-center shrink-0', cat.bg, cat.text)}>
                      <Icon className="w-3.5 h-3.5" />
                    </div>
                    <span className="text-sm text-foreground flex-1">{cat.label}</span>
                    <span className="text-sm font-semibold text-foreground">${suggested}</span>
                  </div>
                )
              })}
            </div>
            <button onClick={async () => {
              setSaving(true)
              try {
                const res = await fetchWithAuth('/budget/settings', {
                  method: 'POST',
                  headers: { 'Content-Type': 'application/json' },
                  body: JSON.stringify({ AutoBudget: true }),
                })
                if (res.ok) {
                  const data = await res.json()
                  showToast('Auto budget applied!')
                  setBudgets({
                    food:          data.Food          ?? 0,
                    transport:     data.Transport     ?? 0,
                    utilities:     data.Utilities     ?? 0,
                    entertainment: data.Entertainment ?? 0,
                    shopping:      data.Shopping      ?? 0,
                    healthcare:    data.Healthcare    ?? 0,
                    others:        data.Other         ?? 0,
                  })
                  setMode('auto')
                } else {
                  const d = await res.json().catch(() => ({}))
                  showToast(d.detail || 'Error saving budget')
                }
              } catch { showToast('Error saving budget') }
              finally { setSaving(false) }
            }}
              disabled={saving}
              className="mt-4 w-full bg-primary text-primary-foreground rounded-xl py-2.5 text-sm font-semibold hover:opacity-90 transition-opacity disabled:opacity-50">
              {saving ? 'Applying…' : 'Apply Auto Budget'}
            </button>
          </Card>
        </div>
      )}

      {visibleSuggestions.length > 0 && (
        <div className="px-4 flex flex-col gap-3">
          <div className="flex items-center gap-2 px-1">
            <Lightbulb className="w-4 h-4 text-amber-500" />
            <p className="text-xs text-muted-foreground font-medium uppercase tracking-wider">Budget Suggestions</p>
          </div>
          {visibleSuggestions.map(s => {
            const isAccepted = accepted[s.id]
            return (
              <Card key={s.id} className={cn('p-4', isAccepted && 'border-green-200 bg-green-50')}>
                <div className="flex items-start gap-3">
                  <div className="w-9 h-9 rounded-xl flex items-center justify-center shrink-0 mt-0.5 bg-amber-50 text-amber-500">
                    <Lightbulb className="w-4 h-4" />
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-semibold text-foreground">{s.title}</p>
                    <p className="text-xs text-muted-foreground mt-0.5 leading-relaxed">{s.description}</p>
                    <p className="text-xs font-medium text-green-600 mt-1">Save ~${(s.savings ?? 0).toFixed(0)}/mo</p>
                  </div>
                </div>
                {!isAccepted ? (
                  <div className="flex gap-2 mt-3">
                    <button onClick={() => handleAccept(s)}
                      className="flex-1 flex items-center justify-center gap-1.5 bg-primary text-primary-foreground text-xs font-semibold py-2 rounded-xl hover:opacity-90 transition-opacity">
                      <Check className="w-3.5 h-3.5" /> Accept
                    </button>
                    <button onClick={() => handleDismiss(s)}
                      className="flex-1 flex items-center justify-center gap-1.5 bg-muted text-muted-foreground text-xs font-medium py-2 rounded-xl hover:bg-border transition-colors">
                      <X className="w-3.5 h-3.5" /> Dismiss
                    </button>
                  </div>
                ) : (
                  <div className="mt-3 flex items-center gap-1.5 text-xs text-green-600 font-medium">
                    <CheckCircle2 className="w-3.5 h-3.5" /> Accepted — we&apos;ll help you stay on track
                  </div>
                )}
              </Card>
            )
          })}
        </div>
      )}
    </main>
  )
}

// ─── PAGE: SETTINGS ───────────────────────────────────────────────────────────
function SettingRow({ icon: Icon, label, sub, children, onClick }) {
  const inner = (
    <div className={cn(
      'flex items-center gap-3 py-3.5 border-b border-border last:border-0',
      onClick && 'cursor-pointer hover:bg-muted/40 -mx-5 px-5 rounded-xl transition-colors'
    )} onClick={onClick}>
      <div className="w-8 h-8 rounded-xl bg-accent flex items-center justify-center shrink-0">
        {createElement(Icon, { className: 'w-4 h-4 text-primary' })}
      </div>
      <div className="flex-1 min-w-0">
        <p className="text-sm font-medium text-foreground">{label}</p>
        {sub && <p className="text-xs text-muted-foreground">{sub}</p>}
      </div>
      {children}
      {onClick && !children && <ChevronRight className="w-4 h-4 text-muted-foreground shrink-0" />}
    </div>
  )
  return inner
}

function Toggle({ on, onChange }) {
  return (
    <button role="switch" aria-checked={on} onClick={() => onChange(!on)}
      className={cn('w-10 h-6 rounded-full relative transition-colors shrink-0', on ? 'bg-primary' : 'bg-border')}>
      <span className={cn('absolute top-1 w-4 h-4 rounded-full bg-white shadow transition-all', on ? 'left-5' : 'left-1')} />
    </button>
  )
}

const ALERT_CONFIG = [
  {
    id: 'PriceIncreaseAlerts',
    label: 'Price Increase Alert',
    description: 'Alert when market prices for your basket categories rise too much',
    thresholdKey: 'PriceThreshold',
    thresholdLabel: 'Price increase threshold (%)',
    hasThreshold: true,
  },
  {
    id: 'BudgetThresholdAlerts',
    label: 'Budget Threshold Alert',
    description: 'Alert when you have crossed a set % of your budget',
    thresholdKey: 'BudgetThreshold',
    thresholdLabel: 'Budget usage threshold (%)',
    hasThreshold: true,
  },
  {
    id: 'PaceAlerts',
    label: 'Spending Pace Alert',
    description: 'Alert when you are spending faster than your prorated income',
    hasThreshold: false,
  },
  {
    id: 'AnomalyAlerts',
    label: 'Anomaly Alert',
    description: 'Alert when a single expense is unusually large',
    thresholdKey: 'AnomalyThreshold',
    thresholdLabel: 'Anomaly threshold (% of budget/income)',
    hasThreshold: true,
  },
  {
    id: 'InflationBeaterAlerts',
    label: 'Inflation Beater Insight',
    description: 'Get insights on whether you are beating or lagging national inflation',
    hasThreshold: false,
  },
]

function SettingsPage({ fetchWithAuth, showToast, onLogout, isDarkMode, setIsDarkMode }) {
  const [income,    setIncome]    = useState('0')
  const [household, setHousehold] = useState('1')
  const [transport, setTransport] = useState([])
  const [alertToggles, setAlertToggles] = useState({
    PriceIncreaseAlerts:   true,
    BudgetThresholdAlerts: true,
    PaceAlerts:            true,
    AnomalyAlerts:         true,
    InflationBeaterAlerts: true,
  })
  const [thresholds, setThresholds] = useState({
    PriceThreshold:   10,
    BudgetThreshold:  80,
    AnomalyThreshold: 25,
  })
  const [saved,    setSaved]    = useState(false)

  const [emailModal,  setEmailModal]  = useState(false)
  const [emailStep,   setEmailStep]   = useState(1)
  const [emailPw,     setEmailPw]     = useState('')
  const [newEmail,    setNewEmail]    = useState('')
  const [emailCode,   setEmailCode]   = useState('')
  const [emailLoading,setEmailLoading]= useState(false)

  const [pwModal,  setPwModal]  = useState(false)
  const [curPw,    setCurPw]    = useState('')
  const [newPw,    setNewPw]    = useState('')
  const [rePw,     setRePw]     = useState('')
  const [pwLoading,setPwLoading]= useState(false)

  const [tgModal,   setTgModal]   = useState(false)
  const [tgCode,    setTgCode]    = useState('')
  const [tgLoading, setTgLoading] = useState(false)

  const [deleteModal,   setDeleteModal]   = useState(false)
  const [deletePw,      setDeletePw]      = useState('')
  const [deleteSure,    setDeleteSure]    = useState(false)
  const [deleteData,    setDeleteData]    = useState(false)
  const [deleteLoading, setDeleteLoading] = useState(false)

  // for linking of tg to app
  const [isTgLinked, setIsTgLinked] = useState(false)

  useEffect(() => {
    const load = async () => {
      try {
        const res = await fetchWithAuth('/settings/')
        if (res.ok) {
          const d = await res.json()
          setIncome(String(d.MonthlyIncome ?? 0))
          setHousehold(String(d.HouseholdSize ?? 1))
          setTransport(d.TransportationTypes ?? [])
          setAlertToggles({
            PriceIncreaseAlerts:   !!d.PriceIncreaseAlerts,
            BudgetThresholdAlerts: !!d.BudgetThresholdAlerts,
            PaceAlerts:            !!d.PaceAlerts,
            AnomalyAlerts:         !!d.AnomalyAlerts,
            InflationBeaterAlerts: !!d.InflationBeaterAlerts,
          })
          setThresholds({
            PriceThreshold:   d.PriceThreshold   ?? 10,
            BudgetThreshold:  d.BudgetThreshold  ?? 80,
            AnomalyThreshold: d.AnomalyThreshold ?? 25,
          })
        }
        const tgRes = await fetchWithAuth('/bot/status')
        if (tgRes.ok) {
          const tgData = await tgRes.json()
          setIsTgLinked(tgData.IsLinked)
        }
      } catch { /* silent */ }
    }
    load()
  }, [])

  const TRANSPORT_OPTIONS = [
    { key: 'gasoline',     label: 'Gasoline Vehicle', icon: Car },
    { key: 'hybrid',       label: 'Hybrid Vehicle',   icon: Leaf },
    { key: 'electric',     label: 'Electric Vehicle', icon: Zap },
    { key: 'bus',          label: 'Bus',              icon: BusFront },
    { key: 'train',        label: 'Train',            icon: Train },
    { key: 'walking',      label: 'Walk',             icon: Footprints },
    { key: 'bike',         label: 'Bike',             icon: Bike },
    { key: 'taxi',         label: 'Taxi',             icon: Car },
    { key: 'private_hire', label: 'Private Hire',     icon: Car },
  ]
  function toggleTransport(key) {
    setTransport(t => t.includes(key) ? t.filter(k => k !== key) : [...t, key])
  }

  async function handleSave() {
    const payload = {
      MonthlyIncome:        parseFloat(income)      || 0,
      HouseholdSize:        parseInt(household, 10) || 1,
      TransportationTypes:  transport,
      ...alertToggles,
      ...thresholds,
    }
    try {
      const res = await fetchWithAuth('/settings/update', {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      })
      if (res.ok) {
        setSaved(true)
        showToast('Settings saved!')
        setTimeout(() => setSaved(false), 2000)
      } else {
        const d = await res.json().catch(() => ({}))
        showToast(d.detail || 'Failed to save settings')
      }
    } catch { showToast('Error saving settings') }
  }

  async function handleRequestEmailChange() {
    if (!emailPw || !newEmail) { showToast('Please fill in all fields'); return }
    setEmailLoading(true)
    try {
      const res = await fetchWithAuth('/users/request-email-change', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ Password: emailPw, NewEmail: newEmail }),
      })
      const d = await res.json().catch(() => ({}))
      if (res.ok) {
        setEmailStep(2)
        setEmailCode('')
        showToast('Verification code sent to your new email!')
      } else {
        showToast(d.detail || 'Request failed. Check your password.')
      }
    } catch { showToast('Error sending request') }
    finally { setEmailLoading(false) }
  }

  async function handleConfirmEmailChange() {
    if (emailCode.length < 6) { showToast('Please enter the full 6-digit code'); return }
    setEmailLoading(true)
    try {
      const res = await fetchWithAuth('/users/confirm-email-change', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ VerificationCode: emailCode }),
      })
      const d = await res.json().catch(() => ({}))
      if (res.ok) {
        localStorage.setItem('user_email', newEmail)
        setEmailModal(false)
        setEmailStep(1)
        setEmailPw(''); setNewEmail(''); setEmailCode('')
        showToast('Email updated successfully!')
      } else {
        showToast(d.detail || 'Invalid code. Please try again.')
      }
    } catch { showToast('Error confirming change') }
    finally { setEmailLoading(false) }
  }

  async function handleChangePassword() {
    if (!curPw || !newPw || !rePw) { showToast('Please fill in all fields'); return }
    if (newPw !== rePw) { showToast('New passwords do not match'); return }
    setPwLoading(true)
    
    try {
      const res = await fetchWithAuth('/users/change-password', {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ CurrentPassword: curPw, Password: newPw, RePassword: rePw }),
      })
      
      const d = await res.json().catch(() => ({}))
      
      if (res.ok) {
        setPwModal(false)
        setCurPw(''); setNewPw(''); setRePw('')
        showToast('Password changed successfully!')
      } else {
        if (Array.isArray(d.detail)) {
          const validationMessages = [...new Set(d.detail
            .map(error => error?.msg?.replace(/^Value error,\s*/i, '').trim())
            .filter(Boolean))]
          showToast(validationMessages.length
            ? `New password not accepted: ${validationMessages.join('. ')}. Try a different password.`
            : 'New password is invalid. Please try a different password.')
        } else {
          showToast(d.detail || 'Failed to change password.')
        }
      }
    } catch { 
      showToast('Error changing password') 
    } finally { 
      setPwLoading(false) 
    }
  }

  async function handleGenerateTgCode() {
    setTgLoading(true)
    try {
      const res = await fetchWithAuth('/bot/generate-link-code', { method: 'POST' })
      if (res.ok) {
        const data = await res.json()
        setTgCode(data.LinkCode)
        showToast('Link code generated successfully!')
      } else {
        showToast('Failed to generate Telegram code.')
      }
    } catch {
      showToast('Error generating code.')
    } finally {
      setTgLoading(false)
    }
  }

  async function handleOpenTgModal() {
    setTgModal(true)
    setTgCode('')
    try {
      const res = await fetchWithAuth('/bot/status')
      if (res.ok) {
        const data = await res.json()
        setIsTgLinked(data.IsLinked)
      }
    } catch { /* Keep the last known status if it cannot be refreshed. */ }
  }

  async function handleUnlinkTg() {
    if (!window.confirm('Are you sure you want to unlink your Telegram account?')) return
    
    setTgLoading(true)
    try {
      const res = await fetchWithAuth('/bot/unlink-app', { method: 'POST' })
      if (res.ok) {
        setIsTgLinked(false)
        setTgModal(false)
        showToast('Telegram unlinked successfully!')
      } else {
        showToast('Failed to unlink Telegram.')
      }
    } catch {
      showToast('Error unlinking account.')
    } finally {
      setTgLoading(false)
    }
  }

  async function handleDeleteAccount() {
    if (!deletePw) { showToast('Please enter your password.'); return }
    if (!deleteSure || !deleteData) { showToast('Please check both boxes to confirm.'); return }
    
    setDeleteLoading(true)
    try {
      const res = await fetchWithAuth('/users/delete', {
        method: 'DELETE',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ 
          Password: deletePw, 
          IsSure: deleteSure, 
          DataDelete: deleteData 
        }),
      })
      
      if (res.ok || res.status === 204) {
        setDeleteModal(false)
        showToast('Account permanently deleted.')
        onLogout() // Instantly log them out and clear local storage
      } else {
        const d = await res.json().catch(() => ({}))
        showToast(d.detail || 'Failed to delete account. Check your password.')
      }
    } catch { 
      showToast('Error deleting account') 
    } finally { 
      setDeleteLoading(false) 
    }
  }

  const email = localStorage.getItem('user_email') ?? '—'
  const inputCls = 'w-full bg-muted rounded-xl px-4 py-3 text-sm text-foreground border border-border focus:outline-none focus:ring-2 focus:ring-primary/30 placeholder:text-muted-foreground'
  const btnCls   = 'w-full bg-primary text-primary-foreground rounded-2xl py-3 text-sm font-semibold hover:opacity-90 transition-opacity disabled:opacity-50'

  return (
    <main className="max-w-md mx-auto pb-28">
      <div className="px-5 pt-5 pb-3">
        <h1 className="text-xl font-bold text-foreground">Settings</h1>
        <p className="text-sm text-muted-foreground mt-0.5">Manage your profile and preferences.</p>
      </div>

      

      <div className="px-4 flex flex-col gap-4">
        <Card className="px-5 py-1">
          <p className="text-xs font-semibold text-muted-foreground uppercase tracking-wider pt-4 pb-2">Profile</p>
          
          <SettingRow icon={Moon} label="Dark Mode" sub="Toggle application theme">
            <Toggle on={isDarkMode} onChange={setIsDarkMode} />
          </SettingRow>

          <SettingRow icon={Mail} label="Email" sub={email}
            onClick={() => { setEmailModal(true); setEmailStep(1); setEmailPw(''); setNewEmail(''); setEmailCode('') }} />
          <SettingRow icon={Lock} label="Password" sub="Change your account password"
            onClick={() => { setPwModal(true); setCurPw(''); setNewPw(''); setRePw('') }} />
          
          <SettingRow icon={MessageCircle} label="Telegram Bot" sub="Link your account to Telegram"
            onClick={handleOpenTgModal} />

          <SettingRow icon={X} label="Delete Account" sub="Permanently erase your data">
            <button 
              onClick={() => { 
                setDeleteModal(true); setDeletePw(''); setDeleteSure(false); setDeleteData(false); 
              }} 
              className="text-xs text-destructive font-medium bg-destructive/10 px-3 py-1.5 rounded-lg hover:bg-destructive/20 transition-colors"
            >
              Delete
            </button>
          </SettingRow>

          <SettingRow icon={User} label="Sign Out" sub="Sign out of your account">
            <button onClick={onLogout} className="text-xs text-muted-foreground font-medium">Sign Out</button>
          </SettingRow>
          <div className="pb-2" />
        </Card>

        <Card className="px-5 py-1">
          <p className="text-xs font-semibold text-muted-foreground uppercase tracking-wider pt-4 pb-2">Setup Details</p>

          <SettingRow icon={Briefcase} label="Monthly Income" sub="Your take-home income">
            <div className="flex items-center gap-1 bg-muted rounded-xl px-3 py-1.5">
              <span className="text-xs text-muted-foreground">$</span>
              <input type="number" value={income} onChange={e => setIncome(e.target.value)}
                className="w-16 bg-transparent text-sm font-semibold text-foreground focus:outline-none text-right" />
            </div>
          </SettingRow>

          <SettingRow icon={Users} label="Household Size" sub="Number of people">
            <div className="flex items-center gap-2">
              <button onClick={() => setHousehold(h => String(Math.max(1, Number(h) - 1)))}
                className="w-7 h-7 rounded-lg bg-muted flex items-center justify-center text-foreground hover:bg-border transition-colors text-sm font-bold">-</button>
              <span className="text-sm font-semibold text-foreground w-4 text-center">{household}</span>
              <button onClick={() => setHousehold(h => String(Number(h) + 1))}
                className="w-7 h-7 rounded-lg bg-muted flex items-center justify-center text-foreground hover:bg-border transition-colors text-sm font-bold">+</button>
            </div>
          </SettingRow>

          <div className="py-3 border-b border-border">
            <div className="flex items-center gap-3 mb-3">
              <div className="w-8 h-8 rounded-xl bg-accent flex items-center justify-center shrink-0">
                <Train className="w-4 h-4 text-primary" />
              </div>
              <p className="text-sm font-medium text-foreground">Transport Modes</p>
            </div>
            <div className="flex flex-wrap gap-2 pl-11">
              {TRANSPORT_OPTIONS.map(t => {
                const Icon = t.icon
                const on = transport.includes(t.key)
                return (
                  <button key={t.key} onClick={() => toggleTransport(t.key)}
                    className={cn(
                      'flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs font-medium border transition-colors',
                      on ? 'bg-primary text-primary-foreground border-primary' : 'bg-card text-muted-foreground border-border hover:bg-muted'
                    )}>
                    <Icon className="w-3 h-3" />{t.label}
                  </button>
                )
              })}
            </div>
          </div>
          <div className="pb-2" />
        </Card>

        <Card className="px-5 py-1">
          <p className="text-xs font-semibold text-muted-foreground uppercase tracking-wider pt-4 pb-2">Alert Configuration</p>
          {ALERT_CONFIG.map(a => (
            <div key={a.id}>
              <SettingRow icon={BellIcon} label={a.label} sub={a.description}>
                <Toggle on={alertToggles[a.id]} onChange={v => setAlertToggles(al => ({ ...al, [a.id]: v }))} />
              </SettingRow>
              {a.hasThreshold && alertToggles[a.id] && (
                <div className="py-3 pl-11 border-b border-border -mt-1 mb-1">
                  <p className="text-xs text-muted-foreground mb-2">{a.thresholdLabel}</p>
                  <div className="flex items-center gap-2">
                    <input type="number" min={1} max={100}
                      value={thresholds[a.thresholdKey]}
                      onChange={e => setThresholds(t => ({ ...t, [a.thresholdKey]: Number(e.target.value) }))}
                      className="w-20 bg-muted rounded-xl px-3 py-1.5 text-sm font-semibold text-foreground border border-border focus:outline-none focus:ring-2 focus:ring-primary/30 text-center" />
                    <span className="text-xs text-muted-foreground">%</span>
                  </div>
                </div>
              )}
            </div>
          ))}
          <div className="pb-2" />
        </Card>

        <button onClick={handleSave}
          className={cn(
            'w-full py-3 rounded-2xl text-sm font-semibold transition-all',
            saved ? 'bg-green-500 text-white' : 'bg-primary text-primary-foreground hover:opacity-90'
          )}>
          {saved ? 'Saved!' : 'Save Changes'}
        </button>
      </div> 

      {tgModal && (
        <div className="fixed inset-0 z-50 flex items-start justify-center overflow-y-auto bg-black/40 backdrop-blur-sm px-5 py-8">
          <div className="w-full max-w-sm max-h-[calc(100dvh-4rem)] overflow-y-auto bg-card rounded-2xl p-6 shadow-xl">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-base font-bold text-foreground">Telegram Bot</h2>
              <button onClick={() => setTgModal(false)} className="w-8 h-8 rounded-xl bg-muted flex items-center justify-center">
                <X className="w-4 h-4" />
              </button>
            </div>
            
            {/* If Already Linked -> Show Unlink UI */}
            {isTgLinked ? (
              <div className="flex flex-col items-center gap-4 animate-in zoom-in-95 duration-200 py-2">
                <div className="w-16 h-16 rounded-full bg-green-100 flex items-center justify-center mb-2">
                  <CheckCircle2 className="w-8 h-8 text-green-600" />
                </div>
                <p className="text-sm font-semibold text-foreground text-center">Account Linked</p>
                <p className="text-xs text-muted-foreground text-center leading-relaxed px-2">
                  Your SpendWise account is actively connected to the Telegram bot.
                </p>
                <button onClick={handleUnlinkTg} disabled={tgLoading} 
                  className="w-full bg-destructive/10 text-destructive border border-destructive/20 rounded-2xl py-3 text-sm font-semibold hover:bg-destructive/20 transition-colors disabled:opacity-50 mt-2">
                  {tgLoading ? 'Unlinking...' : 'Unlink Account'}
                </button>
              </div>
            ) : (
              /* If NOT Linked -> Show Generate Code UI (Your existing code) */
              <>
                <p className="text-sm text-muted-foreground mb-5 leading-relaxed">
                  Generate a unique code and send it to our Telegram bot to securely link your SpendWise account.
                </p>

                {tgCode ? (
                  <div className="flex flex-col items-center gap-4 animate-in zoom-in-95 duration-200">
                    <div className="bg-muted px-6 py-5 rounded-2xl border border-border w-full text-center shadow-inner">
                      <span className="text-3xl font-bold tracking-[0.25em] text-foreground font-mono">{tgCode}</span>
                    </div>
                    <p className="text-xs text-muted-foreground text-center px-2">
                      This code expires in 10 minutes. Message it to <span className="font-semibold text-foreground">@SpendWiseBot</span> on Telegram to complete the setup.
                    </p>
                    <button onClick={() => setTgModal(false)} className="w-full text-xs text-muted-foreground text-center mt-2 hover:text-foreground">
                      Close
                    </button>
                  </div>
                ) : (
                  <button onClick={handleGenerateTgCode} disabled={tgLoading} className={btnCls}>
                    {tgLoading ? 'Generating...' : 'Generate Link Code'}
                  </button>
                )}
              </>
            )}
          </div>
        </div>
      )}

      {emailModal && (
        <div className="fixed inset-0 z-50 flex items-start justify-center overflow-y-auto bg-black/40 backdrop-blur-sm px-5 py-8">
          <div className="w-full max-w-sm max-h-[calc(100dvh-4rem)] overflow-y-auto bg-card rounded-2xl p-6 shadow-xl">
            {emailStep === 1 ? (
              <>
                <div className="flex items-center justify-between mb-4">
                  <h2 className="text-base font-bold text-foreground">Change Email</h2>
                  <button onClick={() => setEmailModal(false)} className="w-8 h-8 rounded-xl bg-muted flex items-center justify-center"><X className="w-4 h-4" /></button>
                </div>
                <p className="text-xs text-muted-foreground mb-4 leading-relaxed">
                  For security, please verify your current password before changing your email.
                </p>
                <div className="flex flex-col gap-3">
                  <input type="password" placeholder="Current password" value={emailPw}
                    onChange={e => setEmailPw(e.target.value)} className={inputCls} />
                  <input type="email" placeholder="New email address" value={newEmail}
                    onChange={e => setNewEmail(e.target.value)} className={inputCls} />
                </div>
                <button onClick={handleRequestEmailChange} disabled={emailLoading} className={cn(btnCls, 'mt-4')}>
                  {emailLoading ? 'Sending…' : 'Send Verification Code'}
                </button>
              </>
            ) : (
              <>
                <div className="flex items-center justify-between mb-4">
                  <h2 className="text-base font-bold text-foreground">Enter Code</h2>
                  <button onClick={() => { setEmailModal(false); setEmailStep(1) }} className="w-8 h-8 rounded-xl bg-muted flex items-center justify-center"><X className="w-4 h-4" /></button>
                </div>
                <p className="text-sm text-muted-foreground mb-5 leading-relaxed">
                  We sent a 6-digit verification code to <strong>{newEmail}</strong>. Enter it below.
                </p>
                <OtpInput length={6} value={emailCode} onChange={setEmailCode} />
                <button onClick={handleConfirmEmailChange} disabled={emailLoading || emailCode.length < 6}
                  className={cn(btnCls, 'mt-5')}>
                  {emailLoading ? 'Confirming…' : 'Confirm Email Change'}
                </button>
                <button onClick={() => setEmailStep(1)} className="w-full text-xs text-muted-foreground text-center mt-3">
                  ← Back
                </button>
              </>
            )}
          </div>
        </div>
      )}

      {pwModal && (
        <div className="fixed inset-0 z-50 flex items-start justify-center overflow-y-auto bg-black/40 backdrop-blur-sm px-5 py-8">
          <div className="w-full max-w-sm max-h-[calc(100dvh-4rem)] overflow-y-auto bg-card rounded-2xl p-6 shadow-xl">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-base font-bold text-foreground">Change Password</h2>
              <button onClick={() => setPwModal(false)} className="w-8 h-8 rounded-xl bg-muted flex items-center justify-center"><X className="w-4 h-4" /></button>
            </div>
            <div className="flex flex-col gap-3">
              <input type="password" placeholder="Current password" value={curPw}
                onChange={e => setCurPw(e.target.value)} className={inputCls} />
              <input type="password" placeholder="New password" value={newPw}
                onChange={e => setNewPw(e.target.value)} className={inputCls} />
              <input type="password" placeholder="Confirm new password" value={rePw}
                onChange={e => setRePw(e.target.value)} className={inputCls} />
              <p className="text-xs text-muted-foreground leading-relaxed">
                Password must be 8–100 characters, with an uppercase letter, a number, and a special character.
              </p>
            </div>
            <button onClick={handleChangePassword} disabled={pwLoading}
              className={cn(btnCls, 'mt-4')}>
              {pwLoading ? 'Changing…' : 'Change Password'}
            </button>
          </div>
        </div>
      )}

      {deleteModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm px-5">
          <div className="w-full max-w-sm bg-card rounded-2xl p-6 shadow-xl border border-destructive/20 -mt-300">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-base font-bold text-destructive flex items-center gap-2">
                <X className="w-5 h-5" /> Delete Account
              </h2>
              <button onClick={() => setDeleteModal(false)} className="w-8 h-8 rounded-xl bg-muted flex items-center justify-center"><X className="w-4 h-4" /></button>
            </div>
            
            <div className="bg-destructive/10 rounded-xl p-4 mb-4">
              <p className="text-xs text-destructive font-medium leading-relaxed">
                Warning: This action is permanent. All your financial history, budgets, and settings will be wiped immediately. We are not responsible for the loss of this data.
              </p>
            </div>

            <div className="flex flex-col gap-4 mb-5">
              <input type="password" placeholder="Verify your password" value={deletePw}
                onChange={e => setDeletePw(e.target.value)} className={inputCls} />
              
              <label className="flex items-start gap-3 cursor-pointer mt-1">
                <input type="checkbox" checked={deleteSure} onChange={e => setDeleteSure(e.target.checked)}
                  className="mt-0.5 w-4 h-4 accent-destructive" />
                <span className="text-xs text-muted-foreground leading-relaxed">
                  I am sure I want to delete my account and understand this cannot be undone.
                </span>
              </label>

              <label className="flex items-start gap-3 cursor-pointer">
                <input type="checkbox" checked={deleteData} onChange={e => setDeleteData(e.target.checked)}
                  className="mt-0.5 w-4 h-4 accent-destructive" />
                <span className="text-xs text-muted-foreground leading-relaxed">
                  I agree that SpendWise will permanently delete all my data and is not responsible for it.
                </span>
              </label>
            </div>

            <button onClick={handleDeleteAccount} disabled={deleteLoading || !deleteSure || !deleteData}
              className={cn(btnCls, 'bg-destructive text-destructive-foreground hover:bg-destructive/90')}>
              {deleteLoading ? 'Deleting…' : 'Permanently Delete Account'}
            </button>
            <button onClick={() => setDeleteModal(false)} className="w-full text-xs text-muted-foreground text-center mt-4 hover:text-foreground">
              Cancel
            </button>
          </div>
        </div>
      )}
    </main>
  )
}

// ─── HEADER ───────────────────────────────────────────────────────────────────
const PAGE_TITLES = {
  dashboard: 'Dashboard', history: 'History', add: 'Add Expense', budget: 'Budget', settings: 'Settings',
}

function AppHeader({ page, onNotif, hasAlerts = false }) {
  return (
    <header className="sticky top-0 z-50 bg-card/90 backdrop-blur-sm border-b border-border">
      <div className="flex items-center justify-between px-5 py-4 max-w-md mx-auto">
        <div className="flex items-center gap-2.5">
          <div className="w-8 h-8 rounded-xl bg-primary flex items-center justify-center">
            <Wallet className="w-4 h-4 text-primary-foreground" />
          </div>
          <span className="text-lg font-semibold tracking-tight text-foreground">
            {PAGE_TITLES[page] ?? 'SpendWise'}
          </span>
        </div>
        <button aria-label="Notifications"
          className="relative w-9 h-9 rounded-xl bg-muted flex items-center justify-center text-muted-foreground hover:bg-accent transition-colors"
          onClick={onNotif}>
          <Bell className="w-4 h-4" />
          {hasAlerts && <span className="absolute top-1.5 right-1.5 w-2 h-2 rounded-full bg-primary" />}
        </button>
      </div>
    </header>
  )
}

// ─── ADD EXPENSE — top-down dropdown with 2 children ─────────────────────────
function AddExpenseDropdown({ onClose, fetchWithAuth, showToast, onSuccess }) {
  const [panel, setPanel] = useState(null)

  const [name,      setName]      = useState('')
  const [amount,    setAmount]    = useState('')
  const [category,  setCategory]  = useState('food')
  const [date,      setDate]      = useState(new Date().toISOString().split('T')[0])
  const note = ''
  const [recurring, setRecurring] = useState(false)
  const [saving,    setSaving]    = useState(false)

  const [csvFile,      setCsvFile]      = useState(null)
  const [uploading,    setUploading]    = useState(false)
  const [uploadResult, setUploadResult] = useState(null)

  const handleAdd = async () => {
    if (!name.trim()) { showToast('Item name is required'); return }
    const amt = parseFloat(amount)
    if (!amt || amt <= 0) { showToast('Amount must be greater than 0'); return }
    setSaving(true)
    try {
      const res = await fetchWithAuth('/expenses/', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          Type:          CAT_TO_BACKEND[category] ?? 'Other',
          ItemName:      name.trim(),
          AmountSpent:   amt,
          DatePurchased: date,
          Note:          note || null,
          Recurring:     recurring,
        }),
      })
      if (res.ok) {
        showToast('Expense added!')
        onSuccess?.()
        onClose()
      } else {
        const d = await res.json().catch(() => ({}))
        showToast(d.detail || 'Failed to add expense')
      }
    } catch (err) { showToast('Error: ' + err.message) }
    finally { setSaving(false) }
  }

  async function downloadTemplate(type) {
    try {
      const res = await fetchWithAuth(`/import/template?template_type=${type}`)
      if (!res.ok) { showToast('Download failed'); return }
      const blob = await res.blob()
      const url  = URL.createObjectURL(blob)
      const a    = document.createElement('a')
      a.href     = url
      a.download = type === 'monthly' ? 'SpendWise_Monthly_Categories.csv' : 'SpendWise_Individual_Items.csv'
      a.click()
      URL.revokeObjectURL(url)
    } catch { showToast('Download failed') }
  }

  async function handleUpload() {
    if (!csvFile) { showToast('Please select a CSV file'); return }
    setUploading(true)
    setUploadResult(null)
    try {
      const formData = new FormData()
      formData.append('file', csvFile)
      const res  = await fetchWithAuth('/import/upload-csv', { method: 'POST', body: formData })
      const data = await res.json().catch(() => ({}))
      if (res.ok) {
        setUploadResult({ success: true, rows: data.rows_processed, errors: data.errors ?? [] })
        if (data.rows_processed > 0) onSuccess?.()
      } else {
        setUploadResult({ success: false, errors: [data.detail ?? 'Upload failed'] })
      }
    } catch (err) {
      setUploadResult({ success: false, errors: [err.message] })
    } finally {
      setUploading(false)
    }
  }

  return (
    <div className="fixed inset-0 z-50 bg-black/10 backdrop-blur-[1px]" onClick={onClose}>
      <div className="absolute bottom-24 left-0 right-0 max-w-md mx-auto" onClick={e => e.stopPropagation()}>
        {!panel && (
          <div className="px-4 pb-2 flex gap-3 animate-in slide-in-from-bottom duration-200">
            <button
              onClick={() => setPanel('manual')}
              className="flex-1 bg-card border border-border rounded-2xl p-5 flex flex-col items-center gap-2 shadow-xl hover:border-primary transition-colors focus:outline-none">
              <div className="w-12 h-12 rounded-2xl bg-primary flex items-center justify-center">
                <Plus className="w-6 h-6 text-primary-foreground" />
              </div>
              <p className="text-sm font-semibold text-foreground mt-1">Add Expense</p>
              <p className="text-[10px] text-muted-foreground text-center">Manually log a new expense</p>
            </button>
            <button
              onClick={() => setPanel('csv')}
              className="flex-1 bg-card border border-border rounded-2xl p-5 flex flex-col items-center gap-2 shadow-xl hover:border-primary transition-colors focus:outline-none">
              <div className="w-12 h-12 rounded-2xl bg-accent flex items-center justify-center">
                <FileText className="w-6 h-6 text-primary" />
              </div>
              <p className="text-sm font-semibold text-foreground mt-1">Import / Export</p>
              <p className="text-[10px] text-muted-foreground text-center">Download templates or upload CSV</p>
            </button>
          </div>
        )}

        {panel === 'manual' && (
          <div className="mx-4 mt-2 bg-card rounded-2xl p-5 shadow-xl border border-border animate-in slide-in-from-top duration-200">
            <div className="flex items-center justify-between mb-4">
              <button onClick={() => setPanel(null)} className="text-muted-foreground hover:text-foreground">
                <ChevronLeft className="w-5 h-5" />
              </button>
              <h2 className="text-sm font-bold text-foreground">Add Expense</h2>
              <button onClick={onClose} className="w-8 h-8 rounded-xl bg-muted flex items-center justify-center text-muted-foreground hover:bg-border transition-colors">
                <X className="w-4 h-4" />
              </button>
            </div>

            <div className="flex flex-col gap-3 max-h-[70vh] overflow-y-auto">
              <div>
                <label className="text-xs font-medium text-muted-foreground mb-1.5 block">Description</label>
                <input type="text" placeholder="e.g. Lunch at cafe" value={name} onChange={e => setName(e.target.value)}
                  className="w-full bg-muted rounded-xl px-4 py-2.5 text-sm text-foreground border border-border focus:outline-none focus:ring-2 focus:ring-primary/30" />
              </div>
              <div>
                <label className="text-xs font-medium text-muted-foreground mb-1.5 block">Amount (S$)</label>
                <input type="number" placeholder="0.00" value={amount} onChange={e => setAmount(e.target.value)}
                  className="w-full bg-muted rounded-xl px-4 py-2.5 text-sm text-foreground border border-border focus:outline-none focus:ring-2 focus:ring-primary/30" />
              </div>
              <div>
                <label className="text-xs font-medium text-muted-foreground mb-1.5 block">Date</label>
                <input type="date" value={date} onChange={e => setDate(e.target.value)}
                  className="w-full bg-muted rounded-xl px-4 py-2.5 text-sm text-foreground border border-border focus:outline-none focus:ring-2 focus:ring-primary/30" />
              </div>
              <div>
                <label className="text-xs font-medium text-muted-foreground mb-1.5 block">Category</label>
                <div className="flex flex-wrap gap-2">
                  {CATEGORIES.map(cat => {
                    const Icon = cat.icon
                    const active = category === cat.id
                    return (
                      <button key={cat.id} onClick={() => setCategory(cat.id)}
                        className={cn(
                          'flex items-center gap-1.5 px-2.5 py-1.5 rounded-full text-xs font-medium border transition-colors',
                          active ? 'bg-primary text-primary-foreground border-primary' : 'bg-card text-muted-foreground border-border hover:bg-muted'
                        )}>
                        <Icon className="w-3 h-3" />{cat.label}
                      </button>
                    )
                  })}
                </div>
              </div>
              <div className="flex items-center justify-between py-2 border-t border-border">
                <div>
                  <p className="text-sm font-medium text-foreground">Recurring</p>
                  <p className="text-xs text-muted-foreground">Add to basket as a monthly item</p>
                </div>
                <Toggle on={recurring} onChange={setRecurring} />
              </div>
              <button onClick={handleAdd} disabled={saving}
                className="w-full bg-primary text-primary-foreground rounded-2xl py-3 text-sm font-semibold hover:opacity-90 transition-opacity disabled:opacity-50">
                {saving ? 'Adding…' : 'Add Expense'}
              </button>
            </div>
          </div>
        )}

        {panel === 'csv' && (
          <div className="mx-4 mb-2 bg-card rounded-2xl p-5 shadow-xl border border-border animate-in slide-in-from-bottom duration-200">
            <div className="flex items-center justify-between mb-4">
              <button onClick={() => setPanel(null)} className="text-muted-foreground hover:text-foreground">
                <ChevronLeft className="w-5 h-5" />
              </button>
              <h2 className="text-sm font-bold text-foreground">Import / Export</h2>
              <button onClick={onClose} className="w-8 h-8 rounded-xl bg-muted flex items-center justify-center text-muted-foreground hover:bg-border transition-colors">
                <X className="w-4 h-4" />
              </button>
            </div>

            <div className="flex flex-col gap-4 max-h-[70vh] overflow-y-auto">
              <div>
                <p className="text-xs font-semibold text-muted-foreground uppercase tracking-wider mb-2">Download Templates</p>
                <div className="flex flex-col gap-2">
                  <button onClick={() => downloadTemplate('monthly')}
                    className="flex items-center gap-3 p-3 rounded-xl border border-border bg-muted/40 hover:bg-muted transition-colors text-left">
                    <div className="w-8 h-8 rounded-lg bg-blue-50 flex items-center justify-center shrink-0">
                      <Download className="w-4 h-4 text-blue-500" />
                    </div>
                    <div className="flex-1 min-w-0">
                      <p className="text-xs font-semibold text-foreground">Monthly Categories CSV</p>
                      <p className="text-[10px] text-muted-foreground leading-relaxed">Import aggregated monthly spending totals by category (e.g. past data). Best for bulk historical entry.</p>
                    </div>
                  </button>
                  <button onClick={() => downloadTemplate('detailed')}
                    className="flex items-center gap-3 p-3 rounded-xl border border-border bg-muted/40 hover:bg-muted transition-colors text-left">
                    <div className="w-8 h-8 rounded-lg bg-violet-50 flex items-center justify-center shrink-0">
                      <Download className="w-4 h-4 text-violet-500" />
                    </div>
                    <div className="flex-1 min-w-0">
                      <p className="text-xs font-semibold text-foreground">Detailed Item CSV</p>
                      <p className="text-[10px] text-muted-foreground leading-relaxed">Import individual expense line items with date, name, amount and category. Use for itemised imports.</p>
                    </div>
                  </button>
                </div>
              </div>

              <div>
                <p className="text-xs font-semibold text-muted-foreground uppercase tracking-wider mb-2">Upload CSV</p>
                <div className="border-2 border-dashed border-border rounded-xl p-4 text-center">
                  <Upload className="w-6 h-6 text-muted-foreground mx-auto mb-2" />
                  <p className="text-xs text-muted-foreground mb-2">Fill in a downloaded template and upload it here</p>
                  <input type="file" accept=".csv" id="csv-upload" className="hidden"
                    onChange={e => { setCsvFile(e.target.files[0]); setUploadResult(null) }} />
                  <label htmlFor="csv-upload"
                    className="inline-block px-4 py-1.5 bg-muted rounded-xl text-xs font-medium text-foreground border border-border cursor-pointer hover:bg-border transition-colors">
                    {csvFile ? csvFile.name : 'Choose file'}
                  </label>
                </div>

                {csvFile && !uploadResult && (
                  <button onClick={handleUpload} disabled={uploading}
                    className="w-full mt-3 bg-primary text-primary-foreground rounded-2xl py-2.5 text-xs font-semibold hover:opacity-90 transition-opacity disabled:opacity-50">
                    {uploading ? 'Uploading…' : 'Upload & Import'}
                  </button>
                )}

                {uploadResult && (
                  <div className={cn('mt-3 p-3 rounded-xl text-xs', uploadResult.success ? 'bg-green-50 border border-green-200' : 'bg-red-50 border border-red-200')}>
                    {uploadResult.success ? (
                      <p className="text-green-700 font-semibold mb-1">✓ Imported {uploadResult.rows} row{uploadResult.rows !== 1 ? 's' : ''} successfully!</p>
                    ) : (
                      <p className="text-red-700 font-semibold mb-1">Import failed</p>
                    )}
                    {uploadResult.errors?.length > 0 && (
                      <div className="mt-1 max-h-28 overflow-y-auto">
                        {uploadResult.errors.map((e, i) => (
                          <p key={i} className="text-red-600">{e}</p>
                        ))}
                      </div>
                    )}
                  </div>
                )}
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}

// ─── BOTTOM NAV ───────────────────────────────────────────────────────────────
const NAV_ITEMS = [
  { key: 'dashboard', label: 'Home',    icon: LayoutDashboard },
  { key: 'history',   label: 'History', icon: Clock           },
  { key: 'add',       label: 'Add',     icon: Plus, highlight: true },
  { key: 'budget',    label: 'Budget',  icon: PieChartIcon    },
  { key: 'settings',  label: 'Settings',icon: Settings        },
]

function BottomNav({ active, onNavigate }) {
  return (
    <nav aria-label="Main navigation" className="fixed bottom-0 left-0 right-0 z-50 bg-card/95 backdrop-blur-sm border-t border-border">
      <ul className="flex items-center justify-around px-2 py-2 max-w-md mx-auto">
        {NAV_ITEMS.map(item => {
          const Icon = item.icon
          const isActive = active === item.key
          return (
            <li key={item.key}>
              <button aria-label={item.label} aria-current={isActive && !item.highlight ? 'page' : undefined}
                onClick={() => onNavigate(item.key)}
                className={cn(
                  'flex flex-col items-center gap-1 px-3 py-1.5 rounded-xl transition-all duration-150',
                  item.highlight
                    ? 'bg-primary text-primary-foreground shadow-md -translate-y-2 w-12 h-12 !rounded-2xl !gap-0 !p-0 items-center justify-center'
                    : isActive ? 'text-primary' : 'text-muted-foreground hover:text-foreground'
                )}>
                <Icon className="w-5 h-5" />
                {!item.highlight && (
                  <span className={cn('text-[10px] font-medium', isActive ? 'text-primary' : 'text-muted-foreground')}>
                    {item.label}
                  </span>
                )}
              </button>
            </li>
          )
        })}
      </ul>
    </nav>
  )
}

// ─── ALERTS SIDE-SHEET ────────────────────────────────────────────────────────
function AlertsSheet({ onClose, fetchWithAuth, onAlertsChange }) {
  const [alerts,  setAlerts]  = useState([])
  const [loading, setLoading] = useState(false)
  const [pendingAlertId, setPendingAlertId] = useState(null)
  const [deleteError, setDeleteError] = useState('')
  const swipeStartRef = useRef(null)

  useEffect(() => {
    const load = async () => {
      setLoading(true)
      try {
        const res = await fetchWithAuth('/alerts/')
        if (res.ok) setAlerts(await res.json())
      } catch { /* silent */ }
      finally { setLoading(false) }
    }
    load()
  }, [])

  const markRead = async (id) => {
    if (!id || pendingAlertId !== null) return
    setPendingAlertId(id)
    setDeleteError('')
    try {
      const res = await fetchWithAuth(`/alerts/${id}/read`, { method: 'PUT' })
      if (!res.ok) {
        setDeleteError('Could not remove this alert. Please try again.')
        return
      }

      const remainingAlerts = alerts.filter(a => a.Id !== id)
      setAlerts(remainingAlerts)
      onAlertsChange?.(remainingAlerts.length > 0)
    } catch {
      setDeleteError('Could not remove this alert. Please try again.')
    } finally {
      setPendingAlertId(null)
    }
  }

  const alertColor = (type) => {
    if (!type) return 'border-l-primary bg-accent'
    const t = type.toLowerCase()
    if (t.includes('budget') || t.includes('limit')) return 'border-l-yellow-400 bg-yellow-50'
    if (t.includes('overspend') || t.includes('danger')) return 'border-l-red-400 bg-red-50'
    if (t.includes('saving') || t.includes('success')) return 'border-l-green-400 bg-green-50'
    return 'border-l-primary bg-accent'
  }

  return (
    <div className="fixed inset-0 z-50 flex" data-no-swipe onClick={onClose}>
      <div className="flex-1" />
      <div className="w-full max-w-sm bg-card h-full shadow-2xl flex flex-col" onClick={e => e.stopPropagation()}>
        <div className="flex items-center justify-between px-5 py-4 border-b border-border">
          <h2 className="text-base font-bold text-foreground">Notifications</h2>
          <button onClick={onClose} className="w-8 h-8 rounded-xl bg-muted flex items-center justify-center"><X className="w-4 h-4" /></button>
        </div>
        <div className="flex-1 overflow-y-auto p-4 flex flex-col gap-3">
          {loading && <p className="text-sm text-muted-foreground text-center py-8">Loading…</p>}
          {deleteError && <p role="alert" className="text-sm text-destructive text-center">{deleteError}</p>}
          {!loading && alerts.length === 0 && <p className="text-sm text-muted-foreground text-center py-8">No alerts yet.</p>}
          {alerts.map((a, index) => (
            <div key={a.Id ?? index}
              className={cn('border-l-4 rounded-r-xl p-3 text-sm touch-pan-y', alertColor(a.AlertType))}
              onTouchStart={e => {
                const touch = e.touches[0]
                swipeStartRef.current = { id: a.Id, x: touch.clientX, y: touch.clientY }
              }}
              onTouchEnd={e => {
                const start = swipeStartRef.current
                swipeStartRef.current = null
                if (!start || start.id !== a.Id) return
                const touch = e.changedTouches[0]
                const deltaX = touch.clientX - start.x
                const deltaY = touch.clientY - start.y
                if (Math.abs(deltaX) >= 70 && Math.abs(deltaX) > Math.abs(deltaY) * 1.25) {
                  markRead(a.Id)
                }
              }}>
              <p className="font-semibold text-foreground text-xs mb-0.5">{a.Title ?? a.AlertType ?? 'Alert'}</p>
              <p className="text-muted-foreground leading-relaxed">{a.Message}</p>
              <div className="mt-2 flex items-center justify-between gap-3">
                <p className="text-[10px] text-muted-foreground">Swipe away or dismiss below</p>
                <button
                  type="button"
                  disabled={pendingAlertId !== null}
                  onClick={() => markRead(a.Id)}
                  className="text-[10px] font-semibold text-primary disabled:opacity-50"
                >
                  {pendingAlertId === a.Id ? 'Removing…' : 'Mark as read'}
                </button>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}

// ─── PAGE: SETUP ─────────────────────────────────────────────────────────────
function SetupPage({ fetchWithAuth, showToast, onComplete }) {
  const [income, setIncome] = useState('')
  const [household, setHousehold] = useState('1')
  const [transport, setTransport] = useState([])
  const [saving, setSaving] = useState(false)

  const TRANSPORT_OPTIONS = [
    { key: 'gasoline',     label: 'Gasoline Vehicle', icon: Car },
    { key: 'hybrid',       label: 'Hybrid Vehicle',   icon: Leaf },
    { key: 'electric',     label: 'Electric Vehicle', icon: Zap },
    { key: 'bus',          label: 'Bus',              icon: BusFront },
    { key: 'train',        label: 'Train',            icon: Train },
    { key: 'walking',      label: 'Walk',             icon: Footprints },
    { key: 'bike',         label: 'Bike',             icon: Bike },
    { key: 'taxi',         label: 'Taxi',             icon: Car },
    { key: 'private_hire', label: 'Private Hire',     icon: Car },
  ]

  function toggleTransport(key) {
    setTransport(t => t.includes(key) ? t.filter(k => k !== key) : [...t, key])
  }

  async function handleSetup() {
    const numIncome = parseFloat(income)
    if (isNaN(numIncome) || numIncome < 0) { showToast('Valid monthly income is required'); return }

    setSaving(true)
    try {
      const payload = {
        MonthlyIncome: numIncome,
        HouseholdSize: parseInt(household, 10) || 1,
        TransportationTypes: transport
      }
      const res = await fetchWithAuth('/settings/setup', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      })
      if (res.ok) {
        showToast('Setup complete!')
        onComplete()
      } else {
        const d = await res.json().catch(() => ({}))
        showToast(d.detail || 'Setup failed')
      }
    } catch {
      showToast('Error saving setup')
    } finally {
      setSaving(false)
    }
  }

  return (
    <main className="max-w-md mx-auto pt-16 px-5 flex flex-col min-h-screen pb-10 animate-in fade-in duration-500">
      <div className="mb-8 flex flex-col items-center gap-3">
        <div className="w-14 h-14 rounded-2xl bg-primary flex items-center justify-center shadow-lg">
          <Wallet className="w-7 h-7 text-primary-foreground" />
        </div>
        <div className="text-center">
          <h1 className="text-2xl font-bold text-foreground tracking-tight">Welcome to SpendWise</h1>
          <p className="text-sm text-muted-foreground mt-1">Let's get your account set up</p>
        </div>
      </div>

      <Card className="p-6 flex flex-col gap-6 shadow-sm border border-border">
        <div>
          <label className="text-xs font-semibold text-muted-foreground uppercase tracking-wider mb-2 block">Monthly Income</label>
          <div className="flex items-center gap-2 bg-muted rounded-xl px-4 py-3.5 border border-border focus-within:ring-2 focus-within:ring-primary/30 transition-all">
            <span className="text-sm text-muted-foreground">$</span>
            <input type="number" placeholder="e.g. 4000" value={income} onChange={e => setIncome(e.target.value)}
              className="w-full bg-transparent text-sm font-semibold text-foreground focus:outline-none" />
          </div>
        </div>

        <div>
          <label className="text-xs font-semibold text-muted-foreground uppercase tracking-wider mb-2 block">Household Size</label>
          <div className="flex items-center gap-3 bg-muted rounded-xl p-2 border border-border w-fit">
            <button onClick={() => setHousehold(h => String(Math.max(1, Number(h) - 1)))}
              className="w-9 h-9 rounded-lg bg-card flex items-center justify-center text-foreground shadow-sm hover:border-primary border border-transparent transition-colors text-sm font-bold">-</button>
            <span className="text-sm font-semibold text-foreground w-6 text-center">{household}</span>
            <button onClick={() => setHousehold(h => String(Number(h) + 1))}
              className="w-9 h-9 rounded-lg bg-card flex items-center justify-center text-foreground shadow-sm hover:border-primary border border-transparent transition-colors text-sm font-bold">+</button>
          </div>
        </div>

        <div>
          <label className="text-xs font-semibold text-muted-foreground uppercase tracking-wider mb-2 block">Primary Transport</label>
          <div className="flex flex-wrap gap-2">
            {TRANSPORT_OPTIONS.map(t => {
              const Icon = t.icon
              const on = transport.includes(t.key)
              return (
                <button key={t.key} onClick={() => toggleTransport(t.key)}
                  className={`flex items-center gap-1.5 px-3 py-2 rounded-xl text-xs font-medium border transition-all ${on ? 'bg-primary text-primary-foreground border-primary shadow-sm' : 'bg-card text-muted-foreground border-border hover:bg-muted'}`}>
                  <Icon className="w-3.5 h-3.5" />{t.label}
                </button>
              )
            })}
          </div>
        </div>

        <button onClick={handleSetup} disabled={saving}
          className="w-full bg-primary text-primary-foreground rounded-2xl py-3.5 text-sm font-bold hover:opacity-90 transition-opacity disabled:opacity-50 mt-2 shadow-md">
          {saving ? 'Saving Profile...' : 'Complete Setup'}
        </button>
      </Card>
    </main>
  )
}

// ─── ROOT ─────────────────────────────────────────────────────────────────────
const SWIPE_PAGES = ['dashboard', 'history', 'budget', 'settings']

export default function Dashboard() {
  const [token,      setToken]      = useState(localStorage.getItem('access_token') || '')
  const [page,       setPage]       = useState('dashboard')
  const [dataRefreshKey, setDataRefreshKey] = useState(0)
  const [showAdd,    setShowAdd]    = useState(false)
  const [showAlerts, setShowAlerts] = useState(false)
  const [hasAlerts,  setHasAlerts]  = useState(false)
  const [toast,      setToast]      = useState(null)
  const [hasUnsavedSettings, setHasUnsavedSettings] = useState(false)
  const [isCheckingSetup, setIsCheckingSetup] = useState(!!token)

  const [isDarkMode, setIsDarkMode] = useState(() => {
    return localStorage.getItem('theme') === 'dark' ||
      (!('theme' in localStorage) && window.matchMedia('(prefers-color-scheme: dark)').matches)
  })

  useEffect(() => {
    const root = window.document.documentElement
    if (isDarkMode) {
      root.classList.add('dark')
      localStorage.setItem('theme', 'dark')
    } else {
      root.classList.remove('dark')
      localStorage.setItem('theme', 'light')
    }
  }, [isDarkMode])

  const touchStartX = useRef(null)
  const touchStartY = useRef(null)
  const touchInsideScrollable = useRef(false)

  const [slideClass, setSlideClass] = useState('page-fade-in')

  const showToast = useCallback((msg) => {
    setToast(msg)
    setTimeout(() => setToast(null), 3000)
  }, [])

  const refreshData = useCallback(() => {
    setDataRefreshKey(key => key + 1)
  }, [])

  const clearTokens = useCallback(() => {
    localStorage.removeItem('access_token')
    localStorage.removeItem('refresh_token')
    localStorage.removeItem('user_id')
    localStorage.removeItem('user_email')
    setToken('')
  }, [])

  const refreshAccessToken = useCallback(async () => {
    const refreshToken = localStorage.getItem('refresh_token')
    if (!refreshToken) return null
    try {
      const res = await fetch('/authentication/refresh', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(refreshToken),
      })
      if (!res.ok) return null
      const data = await res.json()
      if (!data?.AccessToken) return null
      localStorage.setItem('access_token', data.AccessToken)
      setToken(data.AccessToken)
      return data.AccessToken
    } catch {
      return null
    }
  }, [])

  const handleSessionExpired = useCallback(async () => {
    const access = localStorage.getItem('access_token') || token
    if (access) {
      try {
        await fetch('/authentication/logout', {
          method: 'POST',
          headers: { Authorization: `Bearer ${access}` },
        })
      } catch { }
    }
    clearTokens()
    showToast('Session expired or account suspended. Please sign in again.')
  }, [token, clearTokens, showToast])

  const fetchWithAuth = useCallback(async (url, options = {}) => {
    const access = localStorage.getItem('access_token') || token
    const headers = { ...(options.headers || {}), Authorization: `Bearer ${access}` }
    let res = await fetch(url, { ...options, headers })

    if (res.status === 403) {
      handleSessionExpired()
      return res
    }

    if (res.status === 401) {
      if (!isRefreshing) isRefreshing = refreshAccessToken()
      const newAccess = await isRefreshing
      isRefreshing = null
      if (!newAccess) { handleSessionExpired(); return res }
      const retryHeaders = { ...(options.headers || {}), Authorization: `Bearer ${newAccess}` }
      res = await fetch(url, { ...options, headers: retryHeaders })
    }
    return res
  }, [token, refreshAccessToken, handleSessionExpired])

  const handleLogout = useCallback(async () => {
    try { await fetchWithAuth('/authentication/logout', { method: 'POST' }) } catch { }
    clearTokens()
    showToast('Logged out')
  }, [fetchWithAuth, clearTokens, showToast])

  function tryNavigate(targetPage) {
    if (page === 'settings' && hasUnsavedSettings && targetPage !== 'settings') {
      if (!window.confirm('You have unsaved settings. Discard changes?')) return false
      setHasUnsavedSettings(false)
    }
    return true
  }

  useEffect(() => {
    if (!token) {
      setIsCheckingSetup(false)
      return
    }
    fetchWithAuth('/settings/')
      .then(r => r.ok ? r.json() : null)
      .then(data => {
        if (data && data.SetupCompleted === false) {
          setPage('setup')
        }
      })
      .finally(() => setIsCheckingSetup(false))
  }, [token])

  useEffect(() => {
    if (!token) return
    fetchWithAuth('/alerts/')
      .then(r => r.ok ? r.json() : [])
      .then(data => setHasAlerts(Array.isArray(data) && data.length > 0))
      .catch(() => {})
  }, [page])

  function handleNavigate(key) {
    if (key === 'add') { setShowAdd(true); return }
    const fromIdx = SWIPE_PAGES.indexOf(page)
    const toIdx   = SWIPE_PAGES.indexOf(key)
    if (fromIdx !== -1 && toIdx !== -1 && fromIdx !== toIdx) {
      setSlideClass(toIdx > fromIdx ? 'page-enter-from-right' : 'page-enter-from-left')
    } else {
      setSlideClass('page-fade-in')
    }
    if (tryNavigate(key)) {
      if (key === 'settings') window.scrollTo(0, 0)
      setPage(key)
    }
  }

  function handleTouchStart(e) {
    touchStartX.current = e.touches[0].clientX
    touchStartY.current = e.touches[0].clientY
    touchInsideScrollable.current = !!e.target.closest('[data-no-swipe]')
  }

  function handleTouchEnd(e) {
    if (page === 'setup') return
    if (touchStartX.current === null) return

    if (touchInsideScrollable.current) {
      touchStartX.current = null
      touchStartY.current = null
      touchInsideScrollable.current = false
      return
    }

    const dx = e.changedTouches[0].clientX - touchStartX.current
    const dy = e.changedTouches[0].clientY - touchStartY.current

    touchStartX.current = null
    touchStartY.current = null
    touchInsideScrollable.current = false

    if (Math.abs(dx) < 60 || Math.abs(dx) < Math.abs(dy) * 1.5) return

    const idx = SWIPE_PAGES.indexOf(page)
    if (idx === -1) return

    if (dx < 0 && idx < SWIPE_PAGES.length - 1) {
      const target = SWIPE_PAGES[idx + 1]
      if (tryNavigate(target)) {
        setSlideClass('page-enter-from-right')
        setPage(target)
      }
    } else if (dx > 0 && idx > 0) {
      const target = SWIPE_PAGES[idx - 1]
      if (tryNavigate(target)) {
        setSlideClass('page-enter-from-left')
        setPage(target)
      }
    }
  }

  if (!token) {
    return (
      <LoginPage
        onLoginSuccess={(accessToken, refreshToken, email, isSetupComplete) => {
          localStorage.setItem('access_token', accessToken)
          localStorage.setItem('refresh_token', refreshToken)
          if (email) localStorage.setItem('user_email', email)
          setToken(accessToken)
          setPage(isSetupComplete ? 'dashboard' : 'setup')
        }}
      />
    )
  }

  if (isCheckingSetup) {
    return (
      <div className="min-h-screen bg-background flex flex-col items-center justify-center">
        <div className="animate-pulse flex flex-col items-center gap-3">
          <div className="w-12 h-12 rounded-2xl bg-primary/20 flex items-center justify-center">
            <Wallet className="w-6 h-6 text-primary" />
          </div>
          <p className="text-sm font-medium text-muted-foreground">Loading SpendWise...</p>
        </div>
      </div>
    )
  }

  const isSetup = page === 'setup'

  return (
    <div className="min-h-[100dvh] w-full max-w-[100vw] overflow-x-hidden bg-background flex flex-col relative" onTouchStart={handleTouchStart} onTouchEnd={handleTouchEnd}>
      <style>{`
        @keyframes _swPageRight {
          from { transform: translateX(30px); opacity: 0; }
          to   { transform: translateX(0);    opacity: 1; }
        }
        @keyframes _swPageLeft {
          from { transform: translateX(-30px); opacity: 0; }
          to   { transform: translateX(0);    opacity: 1; }
        }
        @keyframes _swFade {
          from { opacity: 0; }
          to   { opacity: 1; }
        }
        .page-enter-from-right { animation: _swPageRight 250ms cubic-bezier(0.25, 0.46, 0.45, 0.94) both; }
        .page-enter-from-left  { animation: _swPageLeft  250ms cubic-bezier(0.25, 0.46, 0.45, 0.94) both; }
        .page-fade-in          { animation: _swFade      200ms ease-out both; }
      `}</style>

      {!isSetup && <AppHeader page={page} onNotif={() => setShowAlerts(true)} hasAlerts={hasAlerts} />}

      <div key={page} className={cn("flex-1 w-full", slideClass)}>
        {page === 'setup'     && <SetupPage fetchWithAuth={fetchWithAuth} showToast={showToast} onComplete={() => setPage('dashboard')} />}
        {page === 'dashboard' && <DashboardPage onNavigate={handleNavigate} fetchWithAuth={fetchWithAuth} showToast={showToast} refreshKey={dataRefreshKey} />}
        {page === 'history'   && <HistoryPage   fetchWithAuth={fetchWithAuth} showToast={showToast} refreshKey={dataRefreshKey} />}
        {page === 'budget'    && <BudgetPage    fetchWithAuth={fetchWithAuth} showToast={showToast} refreshKey={dataRefreshKey} />}
        {page === 'settings'  && (
          <SettingsPage
            fetchWithAuth={fetchWithAuth}
            showToast={showToast}
            onLogout={handleLogout}
            setHasUnsavedSettings={setHasUnsavedSettings}
            isDarkMode={isDarkMode}
            setIsDarkMode={setIsDarkMode}
          />
        )}
      </div>

      {!isSetup && <BottomNav active={page} onNavigate={handleNavigate} />}

      {showAdd && (
        <AddExpenseDropdown
          onClose={() => setShowAdd(false)}
          fetchWithAuth={fetchWithAuth}
          showToast={showToast}
          onSuccess={refreshData}
        />
      )}

      {showAlerts && (
        <AlertsSheet onClose={() => setShowAlerts(false)} fetchWithAuth={fetchWithAuth} onAlertsChange={setHasAlerts} />
      )}

      {toast && (
        <div className="fixed bottom-24 left-1/2 -translate-x-1/2 bg-foreground text-background px-4 py-2.5 rounded-xl text-sm font-medium text-center leading-relaxed z-50 shadow-lg pointer-events-none"
          style={{ width: 'max-content', maxWidth: 'calc(100vw - 2rem)', maxHeight: '30vh', overflowY: 'auto', overflowWrap: 'anywhere' }}>
          {toast}
        </div>
      )}
    </div>
  )
}

// ─── LOGIN PAGE ───────────────────────────────────────────────────────────────
function LoginPage({ onLoginSuccess }) {
  const [tab,           setTab]           = useState('login')
  const [email,         setEmail]         = useState('')
  const [password,      setPassword]      = useState('')
  const [pwErrors,      setPwErrors]      = useState([])
  const [termsAccepted, setTermsAccepted] = useState(false)
  const [loading,       setLoading]       = useState(false)
  const [toast,         setToast]         = useState(null)

  const [verifyModal, setVerifyModal] = useState({ show: false, email: '' })
  const [verifyCode,  setVerifyCode]  = useState('')

  const [forgotStep, setForgotStep] = useState(0)
  const [forgotForm, setForgotForm] = useState({ email: '', code: '', newPw: '', rePw: '' })

  const [showTerms, setShowTerms] = useState(false)

  const showMsg = (msg) => { setToast(msg); setTimeout(() => setToast(null), 3500) }

  const validatePassword = (pw) => {
    const p = pw || ''
    return [
      { text: 'At least 8 characters.', met: p.length >= 8 && p.length <= 100 },
      { text: 'At least one uppercase letter.', met: /[A-Z]/.test(p) },
      { text: 'At least one number.', met: /[0-9]/.test(p) },
      { text: 'At least one special character.', met: /[!@#$%^&*(),.?":{}|<>+]/.test(p) }
    ]
  }
  const handleLogin = async () => {
    setLoading(true)
    try {
      const form = new FormData()
      form.append('username', email.trim())
      form.append('password', password)
      const res  = await fetch('/authentication/login', { method: 'POST', body: form })
      const data = await res.json().catch(() => ({}))
      
      if (res.ok) {
        let isSetupComplete = true
        try {
          const sRes = await fetch('/settings/', { headers: { Authorization: `Bearer ${data.AccessToken}` } })
          if (sRes.ok) {
            const sData = await sRes.json()
            isSetupComplete = sData.SetupCompleted ?? false
          }
        } catch { /* Keep the default setup state if the profile check fails. */ }

        onLoginSuccess(data.AccessToken, data.RefreshToken, email.trim(), isSetupComplete)
      } else {
        showMsg(data.detail || 'Login failed')
      }
    } catch (err) { showMsg('Error: ' + err.message) }
    finally { setLoading(false) }
  }

  const handleRegister = async () => {
    if (!termsAccepted) { showMsg('You must accept the Terms & Conditions.'); return }
    const reqs = validatePassword(password)
    setPwErrors(reqs)
    if (reqs.some(r => !r.met)) return
    setLoading(true)
    try {
      const res  = await fetch('/users/register', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ Email: email.trim(), Password: password }),
      })
      const data = await res.json().catch(() => ({}))
      if (res.ok) {
        setPwErrors([])
        setVerifyModal({ show: true, email: email.trim() })
        showMsg('Account created! Check your email for the verification code.')
      } else {
        showMsg(data.detail || 'Registration failed')
      }
    } catch (err) { showMsg('Error: ' + err.message) }
    finally { setLoading(false) }
  }

  const handleVerify = async () => {
    setLoading(true)
    try {
      const res  = await fetch('/users/verify-email', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ Email: verifyModal.email, VerificationCode: verifyCode }),
      })
      const data = await res.json().catch(() => ({}))
      if (res.ok) {
        setVerifyModal({ show: false, email: '' })
        setVerifyCode('')
        setTab('login')
        showMsg('Email verified! You can now sign in.')
      } else {
        showMsg(data.detail || 'Verification failed')
      }
    } catch (err) { showMsg('Error: ' + err.message) }
    finally { setLoading(false) }
  }

  const handleForgotRequest = async () => {
    setLoading(true)
    try {
      const res  = await fetch('/users/forgot-password', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ Email: forgotForm.email }),
      })
      const data = await res.json().catch(() => ({}))
      if (res.ok) { setForgotStep(2); showMsg('Reset code sent to your email.') }
      else showMsg(data.detail || 'Failed to send reset code')
    } catch (err) { showMsg('Error: ' + err.message) }
    finally { setLoading(false) }
  }

  const handleForgotReset = async () => {
    if (forgotForm.newPw !== forgotForm.rePw) { showMsg('Passwords do not match.'); return }
    const reqs = validatePassword(forgotForm.newPw)
    const unmet = reqs.filter(r => !r.met)
    if (unmet.length) { showMsg(unmet[0].text); return }
    setLoading(true)
    try {
      const res  = await fetch('/users/reset-password', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          Email: forgotForm.email,
          ResetCode: forgotForm.code,
          NewPassword: forgotForm.newPw,
          ReNewPassword: forgotForm.rePw,
        }),
      })
      const data = await res.json().catch(() => ({}))
      if (res.ok) { setForgotStep(0); setTab('login'); showMsg('Password reset! Please sign in.') }
      else showMsg(data.detail || 'Reset failed')
    } catch (err) { showMsg('Error: ' + err.message) }
    finally { setLoading(false) }
  }

  const inputCls = 'w-full bg-muted rounded-xl px-4 py-3 text-sm text-foreground border border-border focus:outline-none focus:ring-2 focus:ring-primary/30 placeholder:text-muted-foreground'
  const btnCls   = 'w-full bg-primary text-primary-foreground rounded-2xl py-3 text-sm font-semibold hover:opacity-90 transition-opacity disabled:opacity-50'

  return (
    <div className="min-h-[100dvh] bg-background flex flex-col items-center justify-center px-5">
      <div className="mb-8 flex flex-col items-center gap-3">
        <div className="w-14 h-14 rounded-2xl bg-primary flex items-center justify-center shadow-lg">
          <Wallet className="w-7 h-7 text-primary-foreground" />
        </div>
        <div className="text-center">
          <h1 className="text-2xl font-bold text-foreground tracking-tight">SpendWise</h1>
          <p className="text-sm text-muted-foreground mt-0.5">Your personal finance companion</p>
        </div>
      </div>

      <div className="w-full max-w-sm">
        <div className="flex bg-muted rounded-xl p-1 gap-1 mb-6">
          {[{ key: 'login', label: 'Sign In' }, { key: 'register', label: 'Sign Up' }].map(t => (
            <button key={t.key} onClick={() => { setTab(t.key); setPwErrors([]) }}
              className={cn(
                'flex-1 py-2 rounded-lg text-sm font-medium transition-colors',
                tab === t.key ? 'bg-card text-foreground shadow-sm' : 'text-muted-foreground hover:text-foreground'
              )}>
              {t.label}
            </button>
          ))}
        </div>

        <div className="flex flex-col gap-3">
          <input type="email" placeholder="Email address" value={email} onChange={e => setEmail(e.target.value)} className={inputCls} />
          <input type="password" placeholder="Password" value={password}
            onChange={e => { setPassword(e.target.value); if (tab === 'register') setPwErrors(validatePassword(e.target.value)) }}
            className={inputCls} />

          {tab === 'register' && pwErrors.length > 0 && (
            <div className="bg-muted/50 border border-border rounded-xl px-4 py-3 flex flex-col gap-1">
              {pwErrors.map((req, i) => (
                <p key={i} className={cn("text-xs transition-colors", req.met ? "text-green-600" : "text-destructive")}>
                  {req.text}
                </p>
              ))}
            </div>
          )}

          {tab === 'register' && (
            <label className="flex items-start gap-2.5 cursor-pointer">
              <input type="checkbox" checked={termsAccepted} onChange={e => setTermsAccepted(e.target.checked)}
                className="mt-0.5 w-4 h-4 accent-primary" />
              <span className="text-xs text-muted-foreground leading-relaxed">
                I agree to the{' '}
                <button onClick={() => setShowTerms(true)} className="text-primary underline font-medium">
                  Terms and Conditions
                </button>
              </span>
            </label>
          )}

          <button onClick={tab === 'login' ? handleLogin : handleRegister} disabled={loading} className={cn(btnCls, 'mt-1')}>
            {loading ? 'Please wait…' : tab === 'login' ? 'Sign In' : 'Create Account'}
          </button>

          {tab === 'login' && (
            <button onClick={() => setForgotStep(1)} className="text-xs text-primary text-center font-medium mt-1">
              Forgot password?
            </button>
          )}
        </div>
      </div>

      {toast && (
        <div className="fixed bottom-10 left-1/2 -translate-x-1/2 bg-foreground text-background px-4 py-2.5 rounded-xl text-sm font-medium z-50 shadow-lg">
          {toast}
        </div>
      )}

      {verifyModal.show && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-sm px-5">
          <div className="w-full max-w-sm bg-card rounded-2xl p-6 shadow-xl">
            <h2 className="text-base font-bold text-foreground mb-1">Verify Your Email</h2>
            <p className="text-sm text-muted-foreground mb-5">
              We sent a 6-digit code to <strong>{verifyModal.email}</strong>.
            </p>
            <OtpInput length={6} value={verifyCode} onChange={setVerifyCode} />
            <button onClick={handleVerify} disabled={loading} className={cn(btnCls, 'mt-4')}>
              {loading ? 'Verifying…' : 'Verify Account'}
            </button>
            <button onClick={() => setVerifyModal({ show: false, email: '' })}
              className="w-full text-xs text-muted-foreground text-center mt-3">Cancel</button>
          </div>
        </div>
      )}

      {forgotStep === 1 && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-sm px-5">
          <div className="w-full max-w-sm bg-card rounded-2xl p-6 shadow-xl">
            <h2 className="text-base font-bold text-foreground mb-1">Reset Password</h2>
            <p className="text-sm text-muted-foreground mb-4">Enter your account email and we'll send a reset code.</p>
            <input type="email" placeholder="Email address" value={forgotForm.email}
              onChange={e => setForgotForm(f => ({ ...f, email: e.target.value }))}
              className={cn(inputCls, 'mb-3')} />
            <button onClick={handleForgotRequest} disabled={loading} className={btnCls}>
              {loading ? 'Sending…' : 'Send Reset Code'}
            </button>
            <button onClick={() => setForgotStep(0)} className="w-full text-xs text-muted-foreground text-center mt-3">Cancel</button>
          </div>
        </div>
      )}

      {forgotStep === 2 && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-sm px-5">
          <div className="w-full max-w-sm bg-card rounded-2xl p-6 shadow-xl">
            <h2 className="text-base font-bold text-foreground mb-4">Enter New Password</h2>
            <div className="flex flex-col gap-3">
              <input type="text" placeholder="6-digit code" maxLength={6} value={forgotForm.code}
                onChange={e => setForgotForm(f => ({ ...f, code: e.target.value }))}
                className={cn(inputCls, 'text-center tracking-[0.3em] font-bold')} />
              <input type="password" placeholder="New password" value={forgotForm.newPw}
                onChange={e => setForgotForm(f => ({ ...f, newPw: e.target.value }))} className={inputCls} />
              <input type="password" placeholder="Confirm new password" value={forgotForm.rePw}
                onChange={e => setForgotForm(f => ({ ...f, rePw: e.target.value }))} className={inputCls} />
            </div>
            <button onClick={handleForgotReset} disabled={loading} className={cn(btnCls, 'mt-4')}>
              {loading ? 'Resetting…' : 'Reset Password'}
            </button>
            <button onClick={() => setForgotStep(0)} className="w-full text-xs text-muted-foreground text-center mt-3">Cancel</button>
          </div>
        </div>
      )}

      {showTerms && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-sm px-5">
          <div className="w-full max-w-sm bg-card rounded-2xl p-6 shadow-xl max-h-[80vh] overflow-y-auto">
            <h2 className="text-base font-bold text-foreground mb-3">Terms and Conditions</h2>
            <div className="text-sm text-muted-foreground leading-relaxed flex flex-col gap-3">
              <p>Welcome to SpendWise!</p>
              <p>By registering, you agree to provide accurate information and understand that this app is for personal finance tracking purposes only. We are not responsible for financial decisions made based on this app's calculations.</p>
              <p>Your data is stored securely. We will not sell your personal data to third parties.</p>
              <p>Please use this application responsibly.</p>
            </div>
            <button onClick={() => { setTermsAccepted(true); setShowTerms(false) }} className={cn(btnCls, 'mt-5')}>I Agree</button>
          </div>
        </div>
      )}
    </div>
  )
}
