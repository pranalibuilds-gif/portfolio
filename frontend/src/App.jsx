import { useCallback, useEffect, useMemo, useState } from 'react'
import { apiRequest, collectionUrl, itemPath, login, resultCount, tokenStore, ApiError } from './api'
import { resourceByKey, resources } from './resources'
import PublicPortfolio from './PublicPortfolio'

const pageSize = 20

function currentRoute() {
  return window.location.pathname.replace(/\/+$/, '') || '/'
}

function routeTo(path) {
  window.history.pushState({}, '', path)
  window.dispatchEvent(new PopStateEvent('popstate'))
}

function useRoute() {
  const [route, setRoute] = useState(currentRoute)
  useEffect(() => {
    const update = () => setRoute(currentRoute())
    window.addEventListener('popstate', update)
    return () => window.removeEventListener('popstate', update)
  }, [])
  return [route, routeTo]
}

function displayValue(value) {
  if (value === null || value === undefined || value === '') return '—'
  if (typeof value === 'boolean') return value ? 'Yes' : 'No'
  if (typeof value === 'object') {
    return value.name || value.title || value.label || value.original_filename || value.id || '—'
  }
  return String(value)
}

function errorText(error) {
  if (!(error instanceof ApiError)) return error?.message || 'Something went wrong.'
  const data = error.data
  if (data && typeof data === 'object' && !data.detail && !data.non_field_errors) {
    return Object.entries(data)
      .map(([field, messages]) => `${field.replaceAll('_', ' ')}: ${Array.isArray(messages) ? messages.join(' ') : messages}`)
      .join(' · ') || error.message
  }
  return error.message
}

function ErrorBanner({ children, onClose }) {
  if (!children) return null
  return (
    <div className="alert alert-error" role="alert">
      <span>{children}</span>
      {onClose && <button className="icon-button" type="button" aria-label="Dismiss error" onClick={onClose}>×</button>}
    </div>
  )
}

function Loading({ label = 'Loading content…' }) {
  return <div className="loading"><span className="spinner" />{label}</div>
}

function Login({ onLogin }) {
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)
  async function submit(event) {
    event.preventDefault()
    setError('')
    setBusy(true)
    try {
      await login(username, password)
      onLogin()
      routeTo('/cms/dashboard')
    } catch (reason) {
      setError(errorText(reason))
    } finally {
      setBusy(false)
    }
  }
  return (
    <main className="login-screen">
      <div className="login-panel">
        <div className="brand-mark">P</div>
        <p className="eyebrow">PORTFOLIO CONTENT STUDIO</p>
        <h1>Welcome back</h1>
        <p className="muted">Sign in with your CMS administrator account.</p>
        <ErrorBanner>{error}</ErrorBanner>
        <form className="form-stack login-form" onSubmit={submit}>
          <label className="field">
            <span>Username</span>
            <input autoComplete="username" autoFocus required value={username} onChange={(event) => setUsername(event.target.value)} />
          </label>
          <label className="field">
            <span>Password</span>
            <input type="password" autoComplete="current-password" required value={password} onChange={(event) => setPassword(event.target.value)} />
          </label>
          <button className="button button-primary button-full" disabled={busy}>{busy ? 'Signing in…' : 'Sign in'}</button>
        </form>
        <p className="login-footnote">Your session is stored only for this browser tab.</p>
      </div>
    </main>
  )
}

function Sidebar({ route, navigate, onLogout, open, close }) {
  return (
    <>
      {open && <button aria-label="Close navigation" className="mobile-scrim" onClick={close} />}
      <aside className={`sidebar ${open ? 'sidebar-open' : ''}`}>
        <button className="brand" type="button" onClick={() => { navigate('/cms/dashboard'); close() }}>
          <span className="brand-mark">P</span>
          <span><strong>Studio</strong><small>Portfolio CMS</small></span>
        </button>
        <div className="nav-caption">WORKSPACE</div>
        <nav className="nav-list" aria-label="CMS navigation">
          <button className={`nav-item ${route === 'dashboard' ? 'active' : ''}`} onClick={() => { navigate('/cms/dashboard'); close() }}>
            <span className="nav-icon">⌂</span><span>Overview</span>
          </button>
          {resources.map((resource) => (
            <button key={resource.key} className={`nav-item ${route === resource.key ? 'active' : ''}`} onClick={() => { navigate(`/cms/${resource.key}`); close() }}>
              <span className="nav-icon">{resource.icon}</span><span>{resource.label}</span>
              {resource.key === 'contacts' && <span className="nav-dot" />}
            </button>
          ))}
        </nav>
        <div className="sidebar-bottom">
          <div className="workspace-badge"><span className="online-dot" />CMS API connected</div>
          <button className="nav-item logout-item" onClick={onLogout}><span className="nav-icon">↪</span><span>Sign out</span></button>
        </div>
      </aside>
    </>
  )
}

function Dashboard({ onOpen }) {
  const [counts, setCounts] = useState({})
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  useEffect(() => {
    let active = true
    Promise.all(resources.map(async (resource) => {
      try {
        const data = await apiRequest(collectionUrl(resource.key, { page_size: 1 }))
        return [resource.key, resultCount(data)]
      } catch (reason) {
        if (reason.status === 401 || reason.status === 403) throw reason
        return [resource.key, null]
      }
    })).then((entries) => {
      if (active) setCounts(Object.fromEntries(entries))
    }).catch((reason) => {
      if (active) setError(errorText(reason))
    }).finally(() => {
      if (active) setLoading(false)
    })
    return () => { active = false }
  }, [])
  const contentCount = resources.filter((resource) => resource.publishable).reduce((sum, resource) => sum + (counts[resource.key] || 0), 0)
  const tiles = [
    { label: 'Published content & drafts', value: contentCount, detail: 'Across your portfolio', icon: '◈' },
    { label: 'Media assets', value: counts.media ?? '—', detail: 'Images and documents', icon: '▣' },
    { label: 'Inbox messages', value: counts.contacts ?? '—', detail: 'Contact submissions', icon: '✉' },
    { label: 'Projects', value: counts.projects ?? '—', detail: 'Portfolio case studies', icon: '▧' },
  ]
  return (
    <>
      <PageHeading eyebrow="YOUR WORKSPACE" title="Overview" description="Manage your portfolio content, media, and messages from one place." />
      <ErrorBanner>{error}</ErrorBanner>
      <div className="stat-grid">
        {tiles.map((tile, index) => <div className="stat-card" key={tile.label}>
          <div className={`stat-icon stat-icon-${index}`}>{tile.icon}</div>
          <span className="stat-label">{tile.label}</span>
          <strong className="stat-value">{loading ? '—' : tile.value}</strong>
          <span className="stat-detail">{tile.detail}</span>
        </div>)}
      </div>
      <section className="panel dashboard-panel">
        <div className="panel-header">
          <div><p className="eyebrow">CONTENT COLLECTIONS</p><h2>Jump back in</h2></div>
          <span className="panel-note">{loading ? 'Updating counts…' : 'All your content, organized'}</span>
        </div>
        <div className="collection-grid">
          {resources.map((resource) => <button className="collection-card" key={resource.key} onClick={() => onOpen(`/cms/${resource.key}`)}>
            <span className="collection-icon">{resource.icon}</span>
            <span className="collection-copy"><strong>{resource.label}</strong><small>{counts[resource.key] ?? '—'} records</small></span>
            <span className="collection-arrow">↗</span>
          </button>)}
        </div>
      </section>
    </>
  )
}

function PageHeading({ eyebrow, title, description, action }) {
  return (
    <div className="page-heading">
      <div><p className="eyebrow">{eyebrow}</p><h1>{title}</h1><p className="page-description">{description}</p></div>
      {action}
    </div>
  )
}

function resourceLabel(resource, row) {
  return row?.name || row?.title || row?.person_name || row?.role || row?.institution || row?.label || row?.original_filename || row?.email || `${resource.singular} #${row?.id}`
}

function valueFor(row, key, lookup) {
  const value = row?.[key]
  if (value === undefined) return '—'
  if (key === 'status') return <span className={`status-pill status-${value}`}>{value}</span>
  if (typeof value === 'boolean') return <span className={`bool-pill ${value ? 'bool-yes' : ''}`}>{value ? 'Yes' : 'No'}</span>
  if (key === 'file_url' && value) {
    return row.kind === 'image'
      ? <a className="media-preview" href={value} target="_blank" rel="noreferrer"><img src={value} alt={row.alt_text || row.original_filename || 'Media preview'} /></a>
      : <a className="text-button" href={value} target="_blank" rel="noreferrer">Open document ↗</a>
  }
  if (value && typeof value === 'object') {
    const mediaUrl = value.file_url || value.file || value.url
    if (mediaUrl && typeof mediaUrl === 'string' && /\.(png|jpe?g|gif|webp|svg)(\?.*)?$/i.test(mediaUrl)) {
      return <span className="table-media"><img src={mediaUrl} alt="" />{displayValue(value)}</span>
    }
    return displayValue(value)
  }
  const references = lookup[key]
  if (references) return references.get(String(value)) || value
  if (key.endsWith('_at') && value) return new Date(value).toLocaleString()
  if (key === 'size_bytes' && value) return `${(value / 1024).toFixed(0)} KB`
  if (typeof value === 'string' && value.length > 72) return `${value.slice(0, 69)}…`
  return displayValue(value)
}

function useReferences(resource) {
  const [lookups, setLookups] = useState({})
  useEffect(() => {
    let active = true
    const endpoints = new Set(resource.fields.filter((item) => ['reference', 'multireference'].includes(item.type)).map((item) => item.endpoint))
    resource.fields.forEach((item) => {
      if (item.name === 'project' || item.name === 'media' || item.name === 'file' || item.name === 'cover_media' || item.name === 'avatar' || item.name === 'category') endpoints.add(item.endpoint)
    })
    Promise.all([...endpoints].filter(Boolean).map(async (endpoint) => {
      try {
        const data = await apiRequest(collectionUrl(endpoint, { page_size: 100 }))
        return [endpoint, data.results || data]
      } catch {
        return [endpoint, []]
      }
    })).then((entries) => {
      if (!active) return
      const next = {}
      entries.forEach(([endpoint, rows]) => {
        const map = new Map()
        rows.forEach((row) => {
          map.set(String(row.id), resourceLabel(resourceByKey[endpoint] || { singular: endpoint }, row))
        })
        next[endpoint] = { rows, map }
      })
      setLookups(next)
    })
    return () => { active = false }
  }, [resource])
  const valueLookup = useMemo(() => {
    const byField = {}
    resource.fields.forEach((item) => {
      const endpoint = item.endpoint
      if (endpoint && lookups[endpoint]) byField[item.name] = lookups[endpoint].map
    })
    return byField
  }, [lookups, resource])
  return { lookups, valueLookup }
}

function ResourceList({ resource, onOpen }) {
  const [rows, setRows] = useState([])
  const [count, setCount] = useState(0)
  const [page, setPage] = useState(1)
  const [searchDraft, setSearchDraft] = useState('')
  const [search, setSearch] = useState('')
  const [filter, setFilter] = useState('')
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [actionBusy, setActionBusy] = useState(null)
  const { valueLookup } = useReferences(resource)
  const load = useCallback(async () => {
    const params = { page, page_size: pageSize, search }
    if (resource.publishable || resource.filterStatus) params.status = filter
    if (resource.key === 'media') params.kind = filter
    if (resource.key === 'projects' && filter) params.featured = filter
    try {
      const data = await apiRequest(collectionUrl(resource.key, params))
      setError('')
      setRows(data.results || data)
      setCount(resultCount(data))
    } catch (reason) {
      setError(errorText(reason))
    } finally {
      setLoading(false)
    }
  }, [resource, page, search, filter])
  useEffect(() => {
    const request = window.setTimeout(load, 0)
    return () => window.clearTimeout(request)
  }, [load])
  useEffect(() => {
    const refresh = () => { setLoading(true); load() }
    window.addEventListener('cms-refresh', refresh)
    return () => window.removeEventListener('cms-refresh', refresh)
  }, [load])

  const filterOptions = resource.key === 'media'
    ? [['', 'All media'], ['image', 'Images'], ['document', 'Documents']]
    : resource.key === 'contacts'
      ? [['', 'All statuses'], ['new', 'New'], ['read', 'Read'], ['replied', 'Replied'], ['archived', 'Archived']]
      : resource.key === 'projects'
        ? [['', 'All projects'], ['true', 'Featured'], ['false', 'Not featured']]
        : resource.publishable
          ? [['', 'All statuses'], ['draft', 'Draft'], ['published', 'Published']]
          : []
  const columns = resource.columns
  const canCreate = resource.canCreate !== false
  const previous = page > 1
  const next = page * pageSize < count
  async function changePublication(row, action) {
    setActionBusy(row.id)
    setError('')
    try {
      await apiRequest(itemPath(resource.key, row.id, action), { method: 'POST' })
      setLoading(true)
      await load()
    } catch (reason) {
      setError(errorText(reason))
    } finally {
      setActionBusy(null)
    }
  }
  return (
    <>
      <PageHeading
        eyebrow="CONTENT COLLECTION"
        title={resource.label}
        description={resource.key === 'contacts' ? 'Review incoming messages and keep your inbox up to date.' : `Create, organize, and manage your ${resource.label.toLowerCase()}.`}
        action={canCreate && <button className="button button-primary" onClick={() => onOpen({ mode: 'create', resource })}><span>＋</span> New {resource.singular}</button>}
      />
      <section className="panel list-panel">
        <div className="list-toolbar">
          <form className="search-form" onSubmit={(event) => {
            event.preventDefault()
            const query = searchDraft.trim()
            if (search === query && page === 1) { load(); return }
            setLoading(true); setPage(1); setSearch(query)
          }}>
            <span className="search-icon">⌕</span>
            <input aria-label={`Search ${resource.label}`} placeholder={`Search ${resource.label.toLowerCase()}…`} value={searchDraft} onChange={(event) => setSearchDraft(event.target.value)} />
            <button className="button button-quiet" type="submit">Search</button>
          </form>
          <div className="toolbar-right">
            {filterOptions.length > 0 && <select aria-label="Filter content" className="filter-select" value={filter} onChange={(event) => { setLoading(true); setPage(1); setFilter(event.target.value) }}>
              {filterOptions.map(([value, label]) => <option key={value} value={value}>{label}</option>)}
            </select>}
            <span className="result-count">{count} {count === 1 ? 'record' : 'records'}</span>
          </div>
        </div>
        <ErrorBanner>{error}</ErrorBanner>
        {loading ? <Loading label={`Loading ${resource.label.toLowerCase()}…`} /> : rows.length === 0 ? (
          <div className="empty-state"><span className="empty-icon">{resource.icon}</span><h3>{search || filter ? 'No matching records' : `No ${resource.label.toLowerCase()} yet`}</h3><p>{search || filter ? 'Try changing your search or filter.' : `Add your first ${resource.singular.toLowerCase()} to get started.`}</p>{canCreate && !search && !filter && <button className="button button-primary" onClick={() => onOpen({ mode: 'create', resource })}>Create {resource.singular}</button>}</div>
        ) : (
          <div className="table-wrap"><table className="data-table">
            <thead><tr>{columns.map((column) => <th key={column}>{column.replaceAll('_', ' ')}</th>)}{resource.publishable && <th>Status</th>}<th className="actions-head">Actions</th></tr></thead>
            <tbody>{rows.map((row) => <tr key={row.id}>
              {columns.map((column) => <td key={column} className={column === 'message' ? 'message-cell' : ''}>{valueFor(row, column, valueLookup)}</td>)}
              {resource.publishable && <td><span className={`status-pill status-${row.status}`}>{row.status || 'draft'}</span></td>}
              <td><div className="row-actions">
                {resource.key === 'contacts' && <button className="text-button" onClick={() => onOpen({ mode: 'edit', resource, row })}>Open</button>}
                {resource.key !== 'contacts' && <button className="text-button" onClick={() => onOpen({ mode: 'edit', resource, row })}>Edit</button>}
                {resource.publishable && <button className="text-button" onClick={() => onOpen({ mode: 'preview', resource, row })}>Preview</button>}
                {resource.publishable && <button className="text-button publish-text" disabled={actionBusy === row.id} onClick={() => changePublication(row, row.status === 'published' ? 'unpublish' : 'publish')}>{actionBusy === row.id ? 'Saving…' : row.status === 'published' ? 'Unpublish' : 'Publish'}</button>}
                {resource.canDelete !== false && <button className="text-button danger-text" onClick={() => onOpen({ mode: 'delete', resource, row })}>Delete</button>}
              </div></td>
            </tr>)}</tbody>
          </table></div>
        )}
        <div className="pagination">
          <span>Showing {count === 0 ? 0 : (page - 1) * pageSize + 1}–{Math.min(page * pageSize, count)} of {count}</span>
          <div><button className="button button-quiet" disabled={!previous || loading} onClick={() => { setLoading(true); setPage((value) => value - 1) }}>← Previous</button><span className="page-number">Page {page}</span><button className="button button-quiet" disabled={!next || loading} onClick={() => { setLoading(true); setPage((value) => value + 1) }}>Next →</button></div>
        </div>
      </section>
    </>
  )
}

function fieldInitial(field, row) {
  let value = row?.[field.name]
  if (field.name === 'gallery_media_ids') value = row?.gallery_media?.map((item) => item.media?.id).filter(Boolean) || []
  if (value && typeof value === 'object' && !Array.isArray(value)) value = value.id ?? ''
  if (field.type === 'multireference') return Array.isArray(value) ? value.map(String) : []
  if (field.type === 'checkbox') return Boolean(value)
  if (value === null || value === undefined) return ''
  return value
}

function Editor({ selection, onClose, onSaved }) {
  const { resource, row, mode } = selection
  const [values, setValues] = useState(() => Object.fromEntries(resource.fields.map((item) => [item.name, fieldInitial(item, row)])))
  const [errors, setErrors] = useState('')
  const [busy, setBusy] = useState(false)
  const [options, setOptions] = useState({})
  const [upload, setUpload] = useState(null)
  const isEdit = mode === 'edit'
  useEffect(() => {
    let active = true
    const endpoints = [...new Set(resource.fields.filter((item) => ['reference', 'multireference'].includes(item.type)).map((item) => item.endpoint).filter(Boolean))]
    Promise.all(endpoints.map(async (endpoint) => {
      try {
        const data = await apiRequest(collectionUrl(endpoint, { page_size: 100 }))
        return [endpoint, data.results || data]
      } catch (reason) {
        return [endpoint, { error: errorText(reason) }]
      }
    })).then((entries) => {
      if (active) setOptions(Object.fromEntries(entries))
    })
    return () => { active = false }
  }, [resource])

  if (mode === 'preview') return <Preview resource={resource} row={row} onClose={onClose} />
  if (mode === 'delete') return <div className="modal-backdrop" role="presentation" onMouseDown={(event) => event.target === event.currentTarget && onClose()}>
    <section className="modal-card confirm-modal" role="dialog" aria-modal="true" aria-labelledby="delete-title">
      <button className="modal-close" onClick={onClose} aria-label="Close">×</button>
      <span className="confirm-icon">!</span><p className="eyebrow">REMOVE RECORD</p><h2 id="delete-title">Delete {resource.singular.toLowerCase()}?</h2>
      <p className="muted">This action can’t be undone. The record “{resourceLabel(resource, row)}” will be removed.</p>
      <ErrorBanner>{errors}</ErrorBanner>
      <div className="modal-actions"><button className="button button-secondary" onClick={onClose}>Cancel</button><button className="button button-danger" disabled={busy} onClick={async () => {
        setBusy(true); setErrors('')
        try { await apiRequest(itemPath(resource.key, row.id), { method: 'DELETE' }); onSaved() } catch (reason) { setErrors(errorText(reason)); setBusy(false) }
      }}>{busy ? 'Deleting…' : 'Delete record'}</button></div>
    </section>
  </div>

  const contact = resource.key === 'contacts'
  const visibleFields = contact ? resource.fields : resource.fields
  async function submit(event) {
    event.preventDefault()
    setErrors('')
    setBusy(true)
    const payload = {}
    visibleFields.forEach((item) => {
      const value = values[item.name]
      if (item.type === 'file') return
      if (item.type === 'checkbox') payload[item.name] = Boolean(value)
      else if (item.type === 'number') payload[item.name] = value === '' ? item.name === 'proficiency' ? null : 0 : Number(value)
      else if (item.type === 'date') payload[item.name] = value === '' ? null : value
      else if (['reference', 'multireference'].includes(item.type)) {
        payload[item.name] = item.type === 'multireference'
          ? (value || []).map(Number)
          : value === '' ? null : Number(value)
      } else payload[item.name] = value ?? ''
    })
    let body = JSON.stringify(payload)
    const selectedUpload = resource.key === 'media' ? (upload || null) : null
    if (selectedUpload) {
      const form = new FormData()
      Object.entries(payload).forEach(([key, value]) => form.append(key, value === null ? '' : value))
      form.append('upload', selectedUpload)
      body = form
    }
    try {
      const path = isEdit ? itemPath(resource.key, row.id) : `/cms/${resource.key}/`
      await apiRequest(path, { method: isEdit ? 'PATCH' : 'POST', body })
      onSaved()
    } catch (reason) {
      setErrors(errorText(reason))
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="modal-backdrop" role="presentation" onMouseDown={(event) => event.target === event.currentTarget && onClose()}>
      <section className="modal-card editor-modal" role="dialog" aria-modal="true" aria-labelledby="editor-title">
        <div className="modal-header"><div><p className="eyebrow">{contact ? 'INBOX MESSAGE' : isEdit ? 'EDIT CONTENT' : 'NEW CONTENT'}</p><h2 id="editor-title">{contact ? 'Message details' : `${isEdit ? 'Edit' : 'Create'} ${resource.singular}`}</h2></div><button className="modal-close" onClick={onClose} aria-label="Close">×</button></div>
        {contact && <div className="message-detail">
          <div className="contact-detail-head"><div className="avatar-circle">{row.name?.slice(0, 1)?.toUpperCase() || '?'}</div><div><strong>{row.name}</strong><a href={`mailto:${row.email}`}>{row.email}</a></div><time>{row.received_at ? new Date(row.received_at).toLocaleString() : ''}</time></div>
          <h3>{row.subject || 'No subject'}</h3><p>{row.message}</p>
        </div>}
        <ErrorBanner>{errors}</ErrorBanner>
        <form className="form-stack" onSubmit={submit}>
          <div className="form-grid">
            {visibleFields.map((item) => {
              const value = values[item.name]
              const hidden = item.name === 'ended_on' && values.is_current
              if (hidden) return null
              if (item.type === 'checkbox') return <label className="checkbox-field" key={item.name}><input type="checkbox" checked={Boolean(value)} onChange={(event) => setValues({ ...values, [item.name]: event.target.checked })} /><span>{item.label}</span></label>
              if (item.type === 'reference' || item.type === 'multireference') {
                const fieldOptions = options[item.endpoint]
                if (fieldOptions?.error) return <div className="field-warning" key={item.name}><span>{item.label}</span><p>{fieldOptions.error}</p></div>
                const available = (fieldOptions || []).filter((option) => !item.kind || option.kind === item.kind)
                return <label className={`field ${item.type === 'multireference' ? 'field-wide' : ''}`} key={item.name}>
                  <span>{item.label}{item.required && <i> *</i>}</span>
                  <select required={item.required && !isEdit} multiple={item.type === 'multireference'} value={item.type === 'multireference' ? (value || []) : value} onChange={(event) => setValues({ ...values, [item.name]: item.type === 'multireference' ? [...event.target.selectedOptions].map((option) => option.value) : event.target.value })}>
                    {item.type !== 'multireference' && <option value="">No selection</option>}
                    {available.map((option) => <option key={option.id} value={option.id}>{resourceLabel(resourceByKey[item.endpoint] || { singular: item.endpoint }, option)}</option>)}
                  </select>
                  {item.type === 'multireference' && <small>Hold Ctrl (Windows) or Command (Mac) to select multiple.</small>}
                </label>
              }
              if (item.type === 'select') return <label className="field" key={item.name}><span>{item.label}{item.required && <i> *</i>}</span><select required={item.required} value={value ?? ''} onChange={(event) => setValues({ ...values, [item.name]: event.target.value })}><option value="">Choose {item.label.toLowerCase()}…</option>{item.options.map((option) => <option value={option} key={option}>{option[0].toUpperCase() + option.slice(1)}</option>)}</select></label>
              if (item.type === 'file') return <label className="field field-wide" key={item.name}><span>{item.label}{item.required && !isEdit && <i> *</i>}</span><input type="file" required={item.required && !isEdit} accept={item.accept?.[values.kind]} onChange={(event) => {
                const selected = event.target.files?.[0] || null
                if (selected && selected.size > item.maxSizeBytes) {
                  setUpload(null)
                  setErrors('Files must be 10 MB or smaller.')
                  event.target.value = ''
                  return
                }
                setErrors('')
                setUpload(selected)
              }} /><small>Allowed: PNG, JPEG, GIF, WebP images or PDF documents. Maximum size: 10 MB.</small>{upload && <small>Selected: {upload.name} · {(upload.size / 1024).toFixed(0)} KB</small>}</label>
              const Control = item.type === 'textarea' ? 'textarea' : 'input'
              return <label className={`field ${item.type === 'textarea' ? 'field-wide' : ''}`} key={item.name}><span>{item.label}{item.required && <i> *</i>}</span><Control type={item.type === 'textarea' ? undefined : item.type} rows={item.rows || (item.type === 'textarea' ? 4 : undefined)} required={item.required} maxLength={item.maxLength} min={item.min} max={item.max} value={value} onChange={(event) => setValues({ ...values, [item.name]: event.target.value })} /></label>
            })}
          </div>
          <div className="modal-actions"><button type="button" className="button button-secondary" onClick={onClose}>Cancel</button><button className="button button-primary" disabled={busy}>{busy ? 'Saving…' : contact ? 'Update status' : isEdit ? 'Save changes' : `Create ${resource.singular}`}</button></div>
        </form>
      </section>
    </div>
  )
}

function Preview({ resource, row, onClose }) {
  const [data, setData] = useState(null)
  const [error, setError] = useState('')
  useEffect(() => {
    let active = true
    apiRequest(itemPath(resource.key, row.id, 'preview')).then((result) => { if (active) setData(result) }).catch((reason) => { if (active) setError(errorText(reason)) })
    return () => { active = false }
  }, [resource, row.id])
  return <div className="modal-backdrop" role="presentation" onMouseDown={(event) => event.target === event.currentTarget && onClose()}>
    <section className="modal-card preview-modal" role="dialog" aria-modal="true" aria-labelledby="preview-title">
      <div className="modal-header"><div><p className="eyebrow">PROTECTED PREVIEW · {row.status || 'draft'}</p><h2 id="preview-title">{resourceLabel(resource, row)}</h2></div><button className="modal-close" onClick={onClose} aria-label="Close">×</button></div>
      <p className="muted">This preview is visible to authenticated CMS administrators only and does not change publication status.</p>
      <ErrorBanner>{error}</ErrorBanner>
      {data ? <div className="preview-data">{Object.entries(data).filter(([key]) => !['created_by', 'updated_by'].includes(key)).map(([key, value]) => <div className="preview-row" key={key}><strong>{key.replaceAll('_', ' ')}</strong><span>{typeof value === 'object' ? JSON.stringify(value, null, 2) : displayValue(value)}</span></div>)}</div> : !error && <Loading label="Loading secure preview…" />}
      <div className="modal-actions"><button className="button button-secondary" onClick={onClose}>Close preview</button></div>
    </section>
  </div>
}

function App() {
  const [route, navigate] = useRoute()
  const [loggedIn, setLoggedIn] = useState(Boolean(tokenStore.access && tokenStore.refresh))
  const [sidebarOpen, setSidebarOpen] = useState(false)
  const [selection, setSelection] = useState(null)
  useEffect(() => {
    const expire = () => {
      tokenStore.clear()
      setLoggedIn(false)
      setSelection(null)
    }
    window.addEventListener('cms-auth-expired', expire)
    return () => window.removeEventListener('cms-auth-expired', expire)
  }, [])
  useEffect(() => {
    if (route === '/cms' && loggedIn) navigate('/cms/dashboard')
    if (route.startsWith('/cms/') && !loggedIn) navigate('/login')
    if (loggedIn && route === '/login') navigate('/cms/dashboard')
  }, [loggedIn, route, navigate])
  function logout() {
    tokenStore.clear()
    setLoggedIn(false)
    setSelection(null)
    navigate('/login')
  }
  if (route === '/login') return <Login onLogin={() => setLoggedIn(true)} />
  if (!route.startsWith('/cms')) return <PublicPortfolio route={route} navigate={navigate} />
  if (!loggedIn) return <Login onLogin={() => setLoggedIn(true)} />
  const cmsRoute = route === '/cms/dashboard' || route === '/cms' ? 'dashboard' : route.split('/')[2]
  const resource = resourceByKey[cmsRoute]
  return (
    <div className="app-shell min-h-screen bg-slate-50 text-slate-900">
      <Sidebar route={cmsRoute} navigate={navigate} onLogout={logout} open={sidebarOpen} close={() => setSidebarOpen(false)} />
      <main className="main-area">
        <header className="topbar"><button className="mobile-menu" onClick={() => setSidebarOpen(true)} aria-label="Open navigation">☰</button><div className="breadcrumb"><span>Portfolio CMS</span><b>/</b><strong>{resource?.label || 'Overview'}</strong></div><div className="topbar-right"><span className="admin-avatar">A</span><span className="admin-label">Administrator</span></div></header>
        <div className="content-area">
          {cmsRoute === 'dashboard' && <Dashboard onOpen={navigate} />}
          {resource && <ResourceList key={resource.key} resource={resource} onOpen={setSelection} />}
          {!resource && cmsRoute !== 'dashboard' && <div className="empty-state"><h2>Page not found</h2><button className="button button-primary" onClick={() => navigate('/cms/dashboard')}>Back to overview</button></div>}
        </div>
      </main>
      {selection && <Editor selection={selection} onClose={() => setSelection(null)} onSaved={() => { setSelection(null); window.dispatchEvent(new Event('cms-refresh')) }} />}
    </div>
  )
}

export default App
