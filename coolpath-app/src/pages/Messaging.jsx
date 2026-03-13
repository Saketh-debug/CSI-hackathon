import { useState, useRef } from 'react'
import Navbar from '../components/Navbar'
import Footer from '../components/Footer'

const API_BASE = ''

export default function Messaging() {
  // --- Section 1 State ---
  const [singlePhone, setSinglePhone] = useState('')
  const [singleMessage, setSingleMessage] = useState('')
  const [singleStatus, setSingleStatus] = useState('idle') // idle, loading, success, error
  const [singleError, setSingleError] = useState('')

  // --- Section 2 State ---
  const [bulkPhones, setBulkPhones] = useState([])
  const [bulkInput, setBulkInput] = useState('')
  const [bulkMessage, setBulkMessage] = useState('')
  const [bulkStatus, setBulkStatus] = useState('idle')
  const [bulkError, setBulkError] = useState('')

  // --- Section 3 State ---
  const [csvFile, setCsvFile] = useState(null)
  const [csvMessage, setCsvMessage] = useState('')
  const [csvStatus, setCsvStatus] = useState('idle')
  const [csvError, setCsvError] = useState('')
  const fileInputRef = useRef(null)

  // --- Follow-Up Weather Helper ---
  const sendWeatherFollowUp = async (phone) => {
    try {
      // 1. Fetch current weather for Madhapur
      const forecastRes = await fetch(`${API_BASE}/api/forecast`)
      if (!forecastRes.ok) return // Silently fail follow-up

      const data = await forecastRes.json()
      if (!data || !data.current_temp) return

      // 2. Format localized safety message
      const temp = data.current_temp
      const desc = data.weather_description || ''

      let safetyAdvice = `Current weather in Madhapur is ${temp}°C ${desc ? '(' + desc + ')' : ''}. `
      if (temp >= 40) {
        safetyAdvice += 'DANGER: It is too hot to go out. Please stay indoors and stay hydrated.'
      } else if (temp >= 35) {
        safetyAdvice += 'Caution: It is getting hot. Please take precautions if you must go outside.'
      } else {
        safetyAdvice += 'The temperature is currently safe, but remain hydrated.'
      }

      // 3. Dispatch follow-up WhatsApp message
      await fetch(`${API_BASE}/api/messaging/single`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ phone, message: safetyAdvice })
      })
    } catch (err) {
      console.error('Failed to send weather follow-up:', err)
    }
  }

  const handleSendSingle = async () => {
    if (!singlePhone || !singleMessage) return
    setSingleStatus('loading')
    setSingleError('')
    try {
      const res = await fetch(`${API_BASE}/api/messaging/single`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ phone: singlePhone, message: singleMessage })
      })
      if (!res.ok) {
        throw new Error('Failed to send message')
      }
      setSingleStatus('weather') // Intermediate status
      setSinglePhone('')
      setSingleMessage('')

      // Dispatch weather follow up
      await sendWeatherFollowUp(singlePhone)

      setSingleStatus('success')
      setTimeout(() => setSingleStatus('idle'), 3000)
    } catch (err) {
      console.error(err)
      setSingleStatus('error')
      setSingleError(err.message || 'Error sending message')
    }
  }

  const handleAddPhone = (e) => {
    if (e.key === 'Enter' && bulkInput.trim()) {
      e.preventDefault()
      const newPhone = bulkInput.trim()
      if (!bulkPhones.includes(newPhone)) {
        setBulkPhones([...bulkPhones, newPhone])
      }
      setBulkInput('')
    }
  }

  const handleRemovePhone = (phone) => {
    setBulkPhones(bulkPhones.filter(p => p !== phone))
  }

  const handleSendBulk = async () => {
    if (bulkPhones.length === 0 || !bulkMessage) return
    setBulkStatus('loading')
    setBulkError('')
    try {
      const res = await fetch(`${API_BASE}/api/messaging/bulk`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ phones: bulkPhones, message: bulkMessage })
      })
      if (!res.ok) throw new Error('Failed to send bulk messages')

      setBulkStatus('weather') // Intermediate UI state

      // Dispatch weather follow-up to all successful recipients
      // Since Section 2 iterates synchronously across phones in backend, 
      // we fire these off in parallel after the main job
      await Promise.all(bulkPhones.map(phone => sendWeatherFollowUp(phone)))

      setBulkStatus('success')
      setBulkPhones([])
      setBulkMessage('')
      setTimeout(() => setBulkStatus('idle'), 4000)
    } catch (err) {
      console.error(err)
      setBulkStatus('error')
      setBulkError(err.message || 'Error sending bulk messages')
    }
  }

  const handleFileChange = (e) => {
    if (e.target.files && e.target.files[0]) {
      setCsvFile(e.target.files[0])
    }
  }

  const handleSendCsv = async () => {
    if (!csvFile || !csvMessage) return
    setCsvStatus('loading')
    setCsvError('')

    try {
      const text = await csvFile.text()
      const lines = text.split('\n').map(l => l.trim()).filter(Boolean)

      if (lines.length < 2) {
        throw new Error('CSV file appears empty or missing headers')
      }

      // Assume first row is header
      const headers = lines[0].split(',').map(h => h.trim().toLowerCase())
      const phoneIdx = headers.findIndex(h => h.includes('phone') || h.includes('number'))

      if (phoneIdx === -1) {
        throw new Error('CSV must contain a column named "Phone" or "Number"')
      }

      const promises = []
      for (let i = 1; i < lines.length; i++) {
        const cols = lines[i].split(',').map(c => c.trim())
        const phone = cols[phoneIdx]
        if (!phone) continue

        // Personalize message
        let personalizedMsg = csvMessage
        headers.forEach((headerName, idx) => {
          const regex = new RegExp(`{{${headerName}}}`, 'gi')
          personalizedMsg = personalizedMsg.replace(regex, cols[idx] || '')
        })

        promises.push(
          fetch(`${API_BASE}/api/messaging/single`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ phone, message: personalizedMsg })
          }).then(async res => {
            if (!res.ok) {
              const err = await res.json()
              throw new Error(err.detail || `Failed for ${phone}`)
            }
          })
        )
      }

      await Promise.all(promises)
      setCsvStatus('weather')

      // Dispatch weather follow-ups for all extracted numbers after main dispatches
      const validPhones = lines.slice(1)
        .map(l => l.split(',')[phoneIdx]?.trim())
        .filter(Boolean)
      await Promise.all(validPhones.map(phone => sendWeatherFollowUp(phone)))

      setCsvStatus('success')
      setCsvFile(null)
      setCsvMessage('')
      if (fileInputRef.current) fileInputRef.current.value = ''
      setTimeout(() => setCsvStatus('idle'), 4000)

    } catch (err) {
      console.error(err)
      setCsvStatus('error')
      setCsvError(err.message || 'Error processing CSV')
    }
  }

  return (
    <div className="relative flex min-h-screen w-full flex-col overflow-x-hidden bg-background-light text-slate-900">
      <div className="layout-container flex h-full grow flex-col">
        {/* Standardized Navigation */}
        <Navbar />

        <main className="flex-1 max-w-6xl mx-auto w-full px-6 py-10 flex flex-col gap-12">
          {/* Header Section */}
          <section className="flex flex-col gap-6">
            <div className="flex flex-col gap-1">
              <h1 className="text-3xl font-bold tracking-tight text-slate-900">Thermal Messaging</h1>
              <p className="text-slate-500">Configure and broadcast emergency thermal alerts to onsite personnel.</p>
            </div>
            <div className="flex border-b border-slate-200 gap-8">
              <a className="flex items-center gap-2 border-b-2 border-primary text-primary pb-3 pt-2 font-semibold text-sm transition-all" href="#single">
                <span className="material-symbols-outlined text-sm">person</span> Single Alert
              </a>
              <a className="flex items-center gap-2 border-b-2 border-transparent text-slate-500 pb-3 pt-2 font-semibold text-sm hover:text-primary transition-all" href="#bulk">
                <span className="material-symbols-outlined text-sm">group</span> Bulk Send
              </a>
              <a className="flex items-center gap-2 border-b-2 border-transparent text-slate-500 pb-3 pt-2 font-semibold text-sm hover:text-primary transition-all" href="#csv">
                <span className="material-symbols-outlined text-sm">upload_file</span> CSV Broadcast
              </a>
            </div>
          </section>

          {/* Section 1 & Live Status */}
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-8" id="single">
            <div className="lg:col-span-2 flex flex-col gap-6 glass p-8 rounded-xl shadow-sm border-slate-200/50">
              <div className="flex items-center justify-between">
                <h2 className="text-xl font-bold flex items-center gap-2 text-slate-800">
                  <span className="material-symbols-outlined text-primary">campaign</span>
                  Section 1: Single Thermal Alert
                </h2>
                <span className="text-[10px] font-bold uppercase tracking-widest text-slate-400 bg-slate-100 px-2 py-1 rounded">Individual Response</span>
              </div>
              <div className="grid grid-cols-1 gap-6">
                <div className="flex flex-col gap-2">
                  <label className="text-sm font-semibold text-slate-700">Recipient Phone Number</label>
                  <input
                    className="w-full rounded-lg border border-slate-200 bg-white p-4 focus:ring-2 focus:ring-primary/20 focus:border-primary outline-none transition-all placeholder:text-slate-400"
                    placeholder="+1 (555) 000-0000"
                    type="tel"
                    value={singlePhone}
                    onChange={(e) => setSinglePhone(e.target.value)}
                  />
                </div>
                <div className="flex flex-col gap-2 w-full">
                  <label className="text-sm font-semibold text-slate-700">Alert Message</label>
                  <textarea
                    className="w-full rounded-lg border border-slate-200 bg-white p-4 focus:ring-2 focus:ring-primary/20 focus:border-primary outline-none transition-all resize-none placeholder:text-slate-400"
                    placeholder="Enter emergency thermal instructions..."
                    rows="4"
                    value={singleMessage}
                    onChange={(e) => setSingleMessage(e.target.value)}
                  ></textarea>
                </div>

                {singleStatus === 'error' && (
                  <div className="p-3 bg-rose-50 text-rose-600 text-sm font-semibold rounded-lg border border-rose-200">
                    <span className="material-symbols-outlined text-sm align-middle mr-2">error</span>
                    {singleError}
                  </div>
                )}
                {singleStatus === 'success' && (
                  <div className="p-3 bg-emerald-50 text-emerald-600 text-sm font-semibold rounded-lg border border-emerald-200">
                    <span className="material-symbols-outlined text-sm align-middle mr-2">check_circle</span>
                    Message sent successfully via Twilio WhatsApp!
                  </div>
                )}

                <button
                  onClick={handleSendSingle}
                  disabled={singleStatus === 'loading' || singleStatus === 'weather' || !singlePhone || !singleMessage}
                  className="bg-primary hover:bg-primary/90 text-white font-bold py-4 px-6 rounded-lg transition-all flex items-center justify-center gap-2 shadow-lg shadow-primary/20 disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  {(singleStatus === 'loading' || singleStatus === 'weather') ? (
                    <span className="material-symbols-outlined animate-spin">sync</span>
                  ) : (
                    <span className="material-symbols-outlined">send</span>
                  )}
                  {singleStatus === 'loading' ? 'Sending...' : singleStatus === 'weather' ? 'Sending weather alert...' : 'Send Single Alert'}
                </button>
              </div>
            </div>

            {/* Live Status Sidebar */}

          </div>

          {/* Section 2 */}
          <div className="flex flex-col gap-6 glass p-8 rounded-xl border-slate-200/50 shadow-sm" id="bulk">
            <div className="flex items-center justify-between border-b border-slate-100 pb-4">
              <h2 className="text-xl font-bold flex items-center gap-2 text-slate-800">
                <span className="material-symbols-outlined text-primary">groups</span>
                Section 2: Bulk Thermal Dispatch
              </h2>
              <div className="flex items-center gap-2 px-3 py-1 rounded-full bg-primary/10 border border-primary/20 text-primary text-xs font-bold">
                RECIPIENTS: <span className="recipient-count">{bulkPhones.length}</span>
              </div>
            </div>
            <div className="flex flex-col gap-6">
              <div className="flex flex-col gap-3">
                <label className="text-sm font-semibold text-slate-700">Add Recipients</label>
                <div className="flex flex-wrap gap-2 p-3 rounded-lg border border-slate-200 bg-white">
                  {bulkPhones.map((phone, idx) => (
                    <div key={idx} className="flex items-center gap-2 bg-slate-100 text-slate-700 px-3 py-1 rounded-full text-xs font-semibold border border-slate-200">
                      {phone}
                      <span
                        onClick={() => handleRemovePhone(phone)}
                        className="material-symbols-outlined text-[14px] cursor-pointer hover:text-rose-500"
                      >close</span>
                    </div>
                  ))}
                  <input
                    className="bg-transparent border-none focus:ring-0 text-sm py-1 flex-1 min-w-[150px] placeholder:text-slate-400 outline-none"
                    placeholder="Type number (with +) and hit enter..."
                    type="text"
                    value={bulkInput}
                    onChange={(e) => setBulkInput(e.target.value)}
                    onKeyDown={handleAddPhone}
                  />
                </div>
              </div>
              <div className="flex flex-col gap-2">
                <label className="text-sm font-semibold text-slate-700">Broadcast Message</label>
                <textarea
                  className="w-full rounded-lg border border-slate-200 bg-white p-4 focus:ring-2 focus:ring-primary/20 focus:border-primary outline-none transition-all resize-none placeholder:text-slate-400"
                  placeholder="Alert message for all recipients..."
                  rows="3"
                  value={bulkMessage}
                  onChange={(e) => setBulkMessage(e.target.value)}
                ></textarea>
              </div>

              {bulkStatus === 'error' && (
                <div className="p-3 bg-rose-50 text-rose-600 text-sm font-semibold rounded-lg border border-rose-200">
                  <span className="material-symbols-outlined text-sm align-middle mr-2">error</span>
                  {bulkError}
                </div>
              )}
              {bulkStatus === 'success' && (
                <div className="p-3 bg-emerald-50 text-emerald-600 text-sm font-semibold rounded-lg border border-emerald-200">
                  <span className="material-symbols-outlined text-sm align-middle mr-2">check_circle</span>
                  Bulk messages enqueued successfully!
                </div>
              )}

              <div className="flex flex-col sm:flex-row gap-3 pt-2">
                <button
                  onClick={handleSendBulk}
                  disabled={bulkStatus === 'loading' || bulkStatus === 'weather' || bulkPhones.length === 0 || !bulkMessage}
                  className="flex-1 bg-primary hover:bg-primary/90 text-white font-bold py-3.5 px-6 rounded-lg transition-all flex items-center justify-center gap-2 shadow-lg shadow-primary/20 disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  {(bulkStatus === 'loading' || bulkStatus === 'weather') ? (
                    <span className="material-symbols-outlined animate-spin">sync</span>
                  ) : (
                    <span className="material-symbols-outlined">send_and_archive</span>
                  )}
                  {bulkStatus === 'loading' ? 'Sending...' : bulkStatus === 'weather' ? 'Sending weather alert...' : 'Send to All'}
                </button>
                <button
                  onClick={() => setBulkPhones([])}
                  className="bg-white hover:bg-rose-50 text-slate-600 hover:text-rose-600 font-bold py-3.5 px-6 rounded-lg transition-all flex items-center justify-center gap-2 border border-slate-200 hover:border-rose-200"
                >
                  <span className="material-symbols-outlined">delete_sweep</span>
                  Clear List
                </button>
              </div>
            </div>
          </div>

          {/* Section 3 */}
          <div className="flex flex-col gap-6 glass p-8 rounded-xl border-slate-200/50 shadow-sm" id="csv">
            <h2 className="text-xl font-bold flex items-center gap-2 text-slate-800">
              <span className="material-symbols-outlined text-primary">csv</span>
              Section 3: CSV Broadcast
            </h2>
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
              <div className="flex flex-col gap-4">
                <input
                  type="file"
                  accept=".csv"
                  className="hidden"
                  ref={fileInputRef}
                  onChange={handleFileChange}
                />
                <div
                  onClick={() => fileInputRef.current?.click()}
                  className={`w-full h-full min-h-[220px] border-2 border-dashed rounded-xl bg-slate-50/50 flex flex-col items-center justify-center p-6 text-center group transition-all cursor-pointer ${csvFile ? 'border-primary bg-primary/5' : 'border-slate-300 hover:border-primary/50 hover:bg-primary/5'}`}
                >
                  <div className="size-16 bg-white shadow-sm border border-slate-100 rounded-full flex items-center justify-center mb-4 group-hover:scale-110 transition-transform">
                    <span className={`material-symbols-outlined text-3xl ${csvFile ? 'text-primary' : 'text-slate-400 group-hover:text-primary'}`}>
                      {csvFile ? 'task' : 'cloud_upload'}
                    </span>
                  </div>
                  <p className="text-sm font-bold text-slate-700">
                    {csvFile ? csvFile.name : (
                      <>Drop CSV file here or <span className="text-primary underline">browse</span></>
                    )}
                  </p>
                  <p className="text-[11px] text-slate-500 mt-2 font-medium">
                    {csvFile ? `Size: ${(csvFile.size / 1024).toFixed(1)} KB` : 'Max file size 10MB (Columns: Phone, Name, Dept)'}
                  </p>
                </div>
              </div>
              <div className="flex flex-col gap-4">
                <div className="flex flex-col gap-2">
                  <label className="text-sm font-semibold text-slate-700">Custom Template Message</label>
                  <textarea
                    className="w-full rounded-lg border border-slate-200 bg-white p-4 focus:ring-2 focus:ring-primary/20 focus:border-primary outline-none transition-all resize-none placeholder:text-slate-400 text-sm"
                    placeholder="Use tags like {{name}} to personalize your alert..."
                    rows="5"
                    value={csvMessage}
                    onChange={(e) => setCsvMessage(e.target.value)}
                  ></textarea>
                </div>

                {csvStatus === 'error' && (
                  <div className="p-3 bg-rose-50 text-rose-600 text-sm font-semibold rounded-lg border border-rose-200">
                    <span className="material-symbols-outlined text-sm align-middle mr-2">error</span>
                    {csvError}
                  </div>
                )}
                {csvStatus === 'success' && (
                  <div className="p-3 bg-emerald-50 text-emerald-600 text-sm font-semibold rounded-lg border border-emerald-200">
                    <span className="material-symbols-outlined text-sm align-middle mr-2">check_circle</span>
                    CSV template broadcast completed successfully!
                  </div>
                )}

                <button
                  onClick={handleSendCsv}
                  disabled={csvStatus === 'loading' || csvStatus === 'weather' || !csvFile || !csvMessage}
                  className="w-full bg-secondary hover:bg-secondary/90 text-white font-bold py-4 px-6 rounded-lg transition-all flex items-center justify-center gap-2 shadow-lg shadow-secondary/20 disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  {(csvStatus === 'loading' || csvStatus === 'weather') ? (
                    <span className="material-symbols-outlined animate-spin">sync</span>
                  ) : (
                    <span className="material-symbols-outlined">broadcast_on_personal</span>
                  )}
                  {csvStatus === 'loading' ? 'Processing...' : csvStatus === 'weather' ? 'Sending weather alert...' : 'Send CSV Broadcast'}
                </button>
              </div>
            </div>
          </div>
        </main>

        <Footer />
      </div>
    </div>
  )
}
