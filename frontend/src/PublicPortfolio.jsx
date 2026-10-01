import { useEffect, useState } from 'react'
import { apiRequest } from './api'
import './PublicPortfolio.css'

function useApi(path, optional = false) {
  const [state, setState] = useState({ path, data: null, loading: true, error: '', attempt: 0 })

  useEffect(() => {
    let active = true
    apiRequest(path)
      .then((response) => {
        if (active) setState({ path, data: response, loading: false, error: '', attempt: state.attempt })
      })
      .catch((reason) => {
        if (!active) return
        if (optional && reason.status === 404) {
          setState({ path, data: null, loading: false, error: '', attempt: state.attempt })
          return
        }
        setState({
          path,
          data: null,
          loading: false,
          error: reason.message || 'Unable to load this content.',
          attempt: state.attempt,
        })
      })
    return () => { active = false }
  }, [path, optional, state.attempt])

  function retry() {
    setState((current) => ({ ...current, attempt: current.attempt + 1 }))
  }
  return state.path === path
    ? { ...state, retry }
    : { path, data: null, loading: true, error: '', attempt: state.attempt, retry }
}

function rows(response) {
  if (Array.isArray(response)) return response
  return response?.results || []
}

function PublicLink({ to, navigate, children, className, onClick, ...props }) {
  return (
    <a
      href={to}
      className={className}
      onClick={(event) => {
        onClick?.(event)
        if (event.defaultPrevented) return
        if (event.button !== 0 || event.metaKey || event.ctrlKey || event.shiftKey || event.altKey || props.target === '_blank') return
        event.preventDefault()
        navigate(to)
        if (to.includes('#')) {
          const targetId = to.split('#')[1]
          window.setTimeout(() => document.getElementById(targetId)?.scrollIntoView(), 0)
        } else {
          window.scrollTo({ top: 0, behavior: 'auto' })
        }
      }}
      {...props}
    >
      {children}
    </a>
  )
}

function dateLabel(value) {
  if (!value) return ''
  return new Date(`${value.slice(0, 10)}T00:00:00`).toLocaleDateString(undefined, { month: 'short', year: 'numeric' })
}

function period(start, end, current) {
  return [dateLabel(start), current ? 'Present' : dateLabel(end)].filter(Boolean).join(' — ')
}

function Image({ media, alt, className = '' }) {
  if (!media?.file_url) return null
  return <img className={className} src={media.file_url} alt={alt || media.alt_text || ''} loading="lazy" />
}

function Recoverable({ error, retry }) {
  if (!error) return null
  return (
    <div className="portfolio-alert" role="alert">
      <p>{error}</p>
      <button type="button" onClick={retry}>Try again</button>
    </div>
  )
}

function CollectionState({ loading, error, empty, onRetry }) {
  if (loading) return <p className="portfolio-state" role="status">Loading content…</p>
  if (error) return <Recoverable error={error} retry={onRetry} />
  if (empty) return <p className="portfolio-state">{empty}</p>
  return null
}

function SectionHeading({ eyebrow, title, link, navigate }) {
  return (
    <div className="section-heading">
      <div><p className="section-eyebrow">{eyebrow}</p><h2>{title}</h2></div>
      {link && <PublicLink className="text-link" to={link.to} navigate={navigate}>{link.label}<span aria-hidden="true"> ↗</span></PublicLink>}
    </div>
  )
}

function ProjectCard({ project, navigate }) {
  return (
    <article className="project-card">
      <PublicLink className="project-image" to={`/projects/${project.slug}`} navigate={navigate} aria-label={`View ${project.title}`}>
        <Image media={project.cover_media} alt={project.cover_media?.alt_text || project.title} />
        {!project.cover_media?.file_url && <span className="image-placeholder" aria-hidden="true">↗</span>}
      </PublicLink>
      <div className="project-copy">
        <p className="card-meta">{project.role || 'Selected work'}{project.completed_on ? ` · ${dateLabel(project.completed_on)}` : ''}</p>
        <h3><PublicLink to={`/projects/${project.slug}`} navigate={navigate}>{project.title}</PublicLink></h3>
        {project.summary && <p>{project.summary}</p>}
        {project.skills?.length > 0 && <ul className="tag-list" aria-label="Project skills">{project.skills.slice(0, 4).map((skill) => <li key={skill.id}>{skill.name}</li>)}</ul>}
      </div>
    </article>
  )
}

function BlogCard({ post, navigate }) {
  return (
    <article className="blog-card">
      <PublicLink className="blog-image" to={`/blog/${post.slug}`} navigate={navigate} aria-label={`Read ${post.title}`}>
        <Image media={post.cover_media} alt={post.cover_media?.alt_text || post.title} />
        {!post.cover_media?.file_url && <span className="image-placeholder" aria-hidden="true">✳</span>}
      </PublicLink>
      <div className="blog-copy">
        <time dateTime={post.published_at}>{dateLabel(post.published_at)}</time>
        <h3><PublicLink to={`/blog/${post.slug}`} navigate={navigate}>{post.title}</PublicLink></h3>
        {post.excerpt && <p>{post.excerpt}</p>}
        <PublicLink className="text-link" to={`/blog/${post.slug}`} navigate={navigate}>Read article <span aria-hidden="true">↗</span></PublicLink>
      </div>
    </article>
  )
}

function MarkdownBody({ value }) {
  const blocks = (value || '').split(/\n{2,}/).map((block) => block.trim()).filter(Boolean)
  return blocks.map((block, index) => {
    const lines = block.split('\n')
    const heading = lines[0].match(/^(#{1,4})\s+(.+)$/)
    if (heading) {
      const level = Math.min(heading[1].length + 1, 6)
      const Element = `h${level}`
      return <Element key={index}>{heading[2]}</Element>
    }
    if (lines.every((line) => /^[-*]\s+/.test(line))) {
      return <ul key={index}>{lines.map((line) => <li key={line}>{line.replace(/^[-*]\s+/, '')}</li>)}</ul>
    }
    if (lines.every((line) => /^\d+\.\s+/.test(line))) {
      return <ol key={index}>{lines.map((line) => <li key={line}>{line.replace(/^\d+\.\s+/, '')}</li>)}</ol>
    }
    if (lines[0].startsWith('> ')) return <blockquote key={index}>{lines.map((line) => line.replace(/^>\s?/, '')).join(' ')}</blockquote>
    return <p key={index}>{lines.join(' ')}</p>
  })
}

function DetailFailure({ error, retry, navigate }) {
  return (
    <main id="main-content" className="portfolio-main narrow-main">
      <p className="section-eyebrow">CONTENT UNAVAILABLE</p>
      <h1>We couldn’t load this page.</h1>
      <p className="detail-error">{error}</p>
      <button className="button-link" onClick={retry}>Try again</button>
      <PublicLink className="text-link back-link" to="/" navigate={navigate}>Back to home</PublicLink>
    </main>
  )
}

function Home({ navigate }) {
  const profile = useApi('/public/profile/', true)
  const categories = useApi('/public/skill-categories/?page_size=100')
  const projects = useApi('/public/projects/?ordering=-featured,-published_at&page_size=6')
  const experience = useApi('/public/experience/?ordering=-started_on&page_size=8')
  const education = useApi('/public/education/?ordering=-started_on&page_size=8')
  const services = useApi('/public/services/?page_size=8')
  const testimonials = useApi('/public/testimonials/?ordering=-featured&page_size=6')
  const posts = useApi('/public/blog/?ordering=-published_at&page_size=3')
  const socialLinks = useApi('/public/social-links/?page_size=30')
  const resume = useApi('/public/resume/?current=true&page_size=1')
  const person = profile.data
  const projectRows = rows(projects.data)
  const postRows = rows(posts.data)
  const socialRows = rows(socialLinks.data)
  const resumeFile = rows(resume.data)[0]?.file

  return (
    <>
      <main id="main-content">
        <section className="hero-section">
          <div className="hero-inner">
            <div className="hero-copy">
              <p className="section-eyebrow">{person?.location || 'PORTFOLIO'}</p>
              <h1>{person?.headline || (person ? person.name : 'Portfolio')}</h1>
              {person?.short_bio && <p className="hero-description">{person.short_bio}</p>}
              <div className="hero-actions">
                <a className="button-link" href="#projects">Explore my work <span aria-hidden="true">↘</span></a>
                <a className="subtle-link" href="#contact">Let’s talk</a>
                {resumeFile?.file_url && <a className="subtle-link" href={resumeFile.file_url} download>Download résumé <span aria-hidden="true">↓</span></a>}
              </div>
              <Recoverable error={profile.error} retry={profile.retry} />
              {!profile.loading && !profile.error && !person && <p className="profile-absent" role="status">Profile details are not published yet.</p>}
            </div>
            <div className="hero-art">
              <div className="hero-art-frame">
                {person?.avatar?.file_url
                  ? <Image media={person.avatar} alt={person.name || 'Profile portrait'} className="hero-portrait" />
                  : <div className="hero-monogram" aria-hidden="true">{person?.name?.slice(0, 1) || '✳'}</div>}
                <span className="art-caption">{person?.name || 'Portfolio'}</span>
              </div>
              <span className="art-orbit art-orbit-one" aria-hidden="true" />
              <span className="art-orbit art-orbit-two" aria-hidden="true" />
            </div>
          </div>
          <a className="scroll-note" href="#about">Scroll to explore <span aria-hidden="true">↓</span></a>
        </section>

        <section className="portfolio-section about-section" id="about">
          <div className="section-inner about-grid">
            <div><p className="section-eyebrow">A LITTLE ABOUT ME</p><h2>{person?.name || 'About'}</h2></div>
            <div className="about-copy">
              {profile.loading && <p className="portfolio-state" role="status">Loading profile…</p>}
              <Recoverable error={profile.error} retry={profile.retry} />
              {person?.biography
                ? <p>{person.biography}</p>
                : !profile.loading && !profile.error && <p className="portfolio-state">{person ? 'Biography has not been added yet.' : 'A published profile will appear here when available.'}</p>}
              {person?.email && <a className="text-link" href={`mailto:${person.email}`}>{person.email} <span aria-hidden="true">↗</span></a>}
            </div>
          </div>
        </section>

        <section className="portfolio-section soft-section" id="skills">
          <div className="section-inner">
            <SectionHeading eyebrow="WHAT I WORK WITH" title="Skills & tools" />
            <CollectionState loading={categories.loading} error={categories.error} empty={categories.data && rows(categories.data).length === 0 ? 'No published skills yet.' : ''} onRetry={categories.retry} />
            {!categories.loading && !categories.error && <div className="skill-grid">{rows(categories.data).map((category) => (
              <article className="skill-category" key={category.id}>
                <h3>{category.name}</h3>
                <ul>{category.skills.map((skill) => <li key={skill.id}><span>{skill.name}</span>{skill.proficiency != null && <span className="skill-level">{skill.proficiency}%</span>}</li>)}</ul>
              </article>
            ))}</div>}
          </div>
        </section>

        <section className="portfolio-section" id="projects">
          <div className="section-inner">
            <SectionHeading eyebrow="A FEW THINGS I’VE MADE" title="Selected projects" />
            <CollectionState loading={projects.loading} error={projects.error} empty={projects.data && projectRows.length === 0 ? 'No published projects yet.' : ''} onRetry={projects.retry} />
            {!projects.loading && !projects.error && <div className="project-grid">{projectRows.map((project) => <ProjectCard key={project.id} project={project} navigate={navigate} />)}</div>}
          </div>
        </section>

        <section className="portfolio-section soft-section" id="experience">
          <div className="section-inner">
            <SectionHeading eyebrow="THE JOURNEY SO FAR" title="Experience & education" />
            <div className="journey-grid">
              <div className="timeline-column">
                <h3 className="column-heading">Experience</h3>
                <CollectionState loading={experience.loading} error={experience.error} empty={experience.data && rows(experience.data).length === 0 ? 'No published experience yet.' : ''} onRetry={experience.retry} />
                {!experience.loading && !experience.error && <ol className="timeline">{rows(experience.data).map((item) => (
                  <li className="timeline-item" key={item.id}><span className="timeline-dot" aria-hidden="true" /><p className="timeline-date">{period(item.started_on, item.ended_on, item.is_current)}</p><h4>{item.role}</h4><p className="timeline-place">{item.organization}{item.location ? ` · ${item.location}` : ''}</p>{item.description && <p className="timeline-description">{item.description}</p>}</li>
                ))}</ol>}
              </div>
              <div className="timeline-column">
                <h3 className="column-heading">Education</h3>
                <CollectionState loading={education.loading} error={education.error} empty={education.data && rows(education.data).length === 0 ? 'No published education yet.' : ''} onRetry={education.retry} />
                {!education.loading && !education.error && <ol className="timeline">{rows(education.data).map((item) => (
                  <li className="timeline-item" key={item.id}><span className="timeline-dot" aria-hidden="true" /><p className="timeline-date">{period(item.started_on, item.ended_on, item.is_current)}</p><h4>{item.degree}{item.field_of_study ? ` · ${item.field_of_study}` : ''}</h4><p className="timeline-place">{item.institution}{item.location ? ` · ${item.location}` : ''}</p>{item.description && <p className="timeline-description">{item.description}</p>}</li>
                ))}</ol>}
              </div>
            </div>
          </div>
        </section>

        <section className="portfolio-section" id="services">
          <div className="section-inner">
            <SectionHeading eyebrow="HOW I CAN HELP" title="Services" />
            <CollectionState loading={services.loading} error={services.error} empty={services.data && rows(services.data).length === 0 ? 'No published services yet.' : ''} onRetry={services.retry} />
            {!services.loading && !services.error && <div className="service-grid">{rows(services.data).map((service, index) => <article className="service-card" key={service.id}><span className="service-number">{String(index + 1).padStart(2, '0')}</span><h3>{service.title}</h3><p>{service.description}</p></article>)}</div>}
          </div>
        </section>

        <section className="portfolio-section quote-section">
          <div className="section-inner">
            <SectionHeading eyebrow="KIND WORDS" title="What people say" />
            <CollectionState loading={testimonials.loading} error={testimonials.error} empty={testimonials.data && rows(testimonials.data).length === 0 ? 'No testimonials have been published yet.' : ''} onRetry={testimonials.retry} />
            {!testimonials.loading && !testimonials.error && <div className="testimonial-grid">{rows(testimonials.data).map((testimonial) => <figure className="testimonial-card" key={testimonial.id}><span className="quote-mark" aria-hidden="true">“</span><blockquote>{testimonial.quote}</blockquote><figcaption><Image media={testimonial.avatar} alt="" className="testimonial-avatar" /><span><strong>{testimonial.person_name}</strong><small>{[testimonial.person_title, testimonial.organization].filter(Boolean).join(' · ')}</small></span></figcaption></figure>)}</div>}
          </div>
        </section>

        <section className="portfolio-section soft-section" id="journal">
          <div className="section-inner">
            <SectionHeading eyebrow="NOTES & IDEAS" title="From the journal" link={{ to: '/blog', label: 'All articles' }} navigate={navigate} />
            <CollectionState loading={posts.loading} error={posts.error} empty={posts.data && postRows.length === 0 ? 'No published articles yet.' : ''} onRetry={posts.retry} />
            {!posts.loading && !posts.error && <div className="blog-grid">{postRows.map((post) => <BlogCard key={post.id} post={post} navigate={navigate} />)}</div>}
          </div>
        </section>

        <section className="contact-section" id="contact">
          <div className="section-inner contact-grid">
            <div><p className="section-eyebrow">HAVE A PROJECT IN MIND?</p><h2>Let’s make something meaningful.</h2><p>Have a question or an idea to explore? Send a note.</p>{person?.email && <a className="contact-email" href={`mailto:${person.email}`}>{person.email}</a>}</div>
            <ContactForm />
          </div>
        </section>
      </main>
      <footer className="portfolio-footer">
        <div className="section-inner footer-inner">
          <p>© {new Date().getFullYear()} {person?.name || 'Portfolio'}</p>
          <div className="footer-links">
            {socialLinks.loading && <span className="footer-note">Loading links…</span>}
            <Recoverable error={socialLinks.error} retry={socialLinks.retry} />
            {socialRows.map((social) => <a href={social.url} target="_blank" rel="noreferrer" key={social.id}>{social.label || social.platform}<span className="sr-only"> (opens in a new tab)</span></a>)}
            {resumeFile?.file_url && <a href={resumeFile.file_url} download>Résumé</a>}
            <PublicLink to="/login" navigate={navigate}>CMS sign in</PublicLink>
          </div>
        </div>
      </footer>
    </>
  )
}

function ContactForm() {
  const [form, setForm] = useState({ name: '', email: '', subject: '', message: '' })
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const [success, setSuccess] = useState('')

  async function submit(event) {
    event.preventDefault()
    setBusy(true)
    setError('')
    setSuccess('')
    try {
      const response = await apiRequest('/public/contact/', { method: 'POST', body: JSON.stringify(form) })
      setSuccess(response?.detail || 'Your message has been received.')
      setForm({ name: '', email: '', subject: '', message: '' })
    } catch (reason) {
      const data = reason.data
      const details = data && typeof data === 'object'
        ? Object.entries(data).map(([field, messages]) => `${field === 'non_field_errors' ? '' : `${field.replaceAll('_', ' ')}: `}${Array.isArray(messages) ? messages.join(' ') : messages}`).join(' · ')
        : ''
      setError(details || reason.message || 'Your message could not be sent. Please try again.')
    } finally {
      setBusy(false)
    }
  }

  return (
    <form className="contact-form" onSubmit={submit}>
      <div className="contact-form-grid">
        <label><span>Name</span><input required autoComplete="name" minLength={2} maxLength={120} value={form.name} onChange={(event) => setForm({ ...form, name: event.target.value })} /></label>
        <label><span>Email</span><input required type="email" autoComplete="email" maxLength={254} value={form.email} onChange={(event) => setForm({ ...form, email: event.target.value })} /></label>
        <label className="form-wide"><span>Subject <small>(optional)</small></span><input maxLength={200} value={form.subject} onChange={(event) => setForm({ ...form, subject: event.target.value })} /></label>
        <label className="form-wide"><span>Message</span><textarea required minLength={10} maxLength={10000} rows={5} value={form.message} onChange={(event) => setForm({ ...form, message: event.target.value })} /></label>
      </div>
      {error && <p className="form-feedback form-error" role="alert">{error}</p>}
      {success && <p className="form-feedback form-success" role="status">{success}</p>}
      <button className="button-link" type="submit" disabled={busy}>{busy ? 'Sending…' : 'Send message'} <span aria-hidden="true">↗</span></button>
    </form>
  )
}

function ProjectDetail({ slug, navigate }) {
  const detail = useApi(`/public/projects/${encodeURIComponent(slug)}/`)
  const project = detail.data
  if (detail.loading) return <main id="main-content" className="portfolio-main narrow-main"><p className="portfolio-state" role="status">Loading project…</p></main>
  if (detail.error) return <DetailFailure error={detail.error} retry={detail.retry} navigate={navigate} />
  return (
    <main id="main-content" className="portfolio-main detail-main">
      <PublicLink className="back-link text-link" to="/" navigate={navigate}>← Back to portfolio</PublicLink>
      <article>
        <header className="detail-header"><p className="section-eyebrow">{project.role || 'Project'}</p><h1>{project.title}</h1>{project.summary && <p className="detail-intro">{project.summary}</p>}<p className="detail-meta">{[project.started_on && dateLabel(project.started_on), project.completed_on && dateLabel(project.completed_on)].filter(Boolean).join(' — ')}</p></header>
        {project.cover_media?.file_url && <Image media={project.cover_media} alt={project.cover_media.alt_text || project.title} className="detail-cover" />}
        <div className="detail-body-grid">
          <div className="markdown-content"><MarkdownBody value={project.description} /></div>
          <aside className="detail-aside"><h2>Project details</h2>{project.skills?.length > 0 && <><h3>Skills</h3><ul className="tag-list">{project.skills.map((skill) => <li key={skill.id}>{skill.name}</li>)}</ul></>}{project.project_url && <a href={project.project_url} target="_blank" rel="noreferrer">Visit project <span aria-hidden="true">↗</span></a>}{project.source_url && <a href={project.source_url} target="_blank" rel="noreferrer">View source <span aria-hidden="true">↗</span></a>}</aside>
        </div>
        {project.gallery_media?.length > 0 && <section className="detail-gallery" aria-label="Project gallery">{project.gallery_media.map((item, index) => <figure key={`${item.media?.id}-${index}`}><Image media={item.media} alt={item.media?.alt_text || item.caption || `${project.title} gallery image ${index + 1}`} />{item.caption && <figcaption>{item.caption}</figcaption>}</figure>)}</section>}
      </article>
    </main>
  )
}

function BlogList({ navigate }) {
  const articles = useApi('/public/blog/?ordering=-published_at&page_size=100')
  const posts = rows(articles.data)
  return (
    <main id="main-content" className="portfolio-main blog-list-main">
      <p className="section-eyebrow">NOTES & IDEAS</p><h1>Journal</h1><p className="detail-intro">Articles and ideas.</p>
      <CollectionState loading={articles.loading} error={articles.error} empty={articles.data && posts.length === 0 ? 'No published articles yet.' : ''} onRetry={articles.retry} />
      {!articles.loading && !articles.error && <div className="blog-grid blog-list-grid">{posts.map((post) => <BlogCard key={post.id} post={post} navigate={navigate} />)}</div>}
    </main>
  )
}

function BlogDetail({ slug, navigate }) {
  const article = useApi(`/public/blog/${encodeURIComponent(slug)}/`)
  const post = article.data
  if (article.loading) return <main id="main-content" className="portfolio-main narrow-main"><p className="portfolio-state" role="status">Loading article…</p></main>
  if (article.error) return <DetailFailure error={article.error} retry={article.retry} navigate={navigate} />
  return (
    <main id="main-content" className="portfolio-main article-main">
      <PublicLink className="back-link text-link" to="/blog" navigate={navigate}>← All articles</PublicLink>
      <article>
        <header className="article-header"><p className="section-eyebrow">JOURNAL</p><h1>{post.title}</h1><time dateTime={post.published_at}>{dateLabel(post.published_at)}</time>{post.excerpt && <p className="detail-intro">{post.excerpt}</p>}</header>
        {post.cover_media?.file_url && <Image media={post.cover_media} alt={post.cover_media.alt_text || post.title} className="detail-cover" />}
        <div className="markdown-content article-content"><MarkdownBody value={post.body_markdown} /></div>
      </article>
    </main>
  )
}

export default function PublicPortfolio({ route, navigate }) {
  const [menuOpen, setMenuOpen] = useState(false)
  const isProjectDetail = route.startsWith('/projects/')
  const isBlogDetail = route.startsWith('/blog/') && route !== '/blog/'

  useEffect(() => {
    const title = route === '/blog' ? 'Journal' : isProjectDetail ? 'Project' : isBlogDetail ? 'Article' : 'Portfolio'
    document.title = `${title} · Portfolio`
  }, [route, isProjectDetail, isBlogDetail])

  return (
    <div className="portfolio-site">
      <a className="skip-link" href="#main-content">Skip to content</a>
      <header className="portfolio-header">
        <div className="header-inner">
          <PublicLink className="portfolio-brand" to="/" navigate={navigate}><span className="brand-sigil" aria-hidden="true">✳</span><span>Portfolio</span></PublicLink>
          <button className="nav-toggle" type="button" aria-expanded={menuOpen} aria-controls="portfolio-navigation" onClick={() => setMenuOpen(!menuOpen)}><span className="sr-only">{menuOpen ? 'Close navigation' : 'Open navigation'}</span><span aria-hidden="true">{menuOpen ? '×' : '☰'}</span></button>
          <nav className={`portfolio-nav ${menuOpen ? 'nav-open' : ''}`} id="portfolio-navigation" aria-label="Main navigation">
            <PublicLink to="/" navigate={navigate} onClick={() => setMenuOpen(false)}>Home</PublicLink>
            <PublicLink to="/#projects" navigate={navigate} onClick={() => setMenuOpen(false)}>Work</PublicLink>
            <PublicLink to="/#about" navigate={navigate} onClick={() => setMenuOpen(false)}>About</PublicLink>
            <PublicLink to="/#experience" navigate={navigate} onClick={() => setMenuOpen(false)}>Experience</PublicLink>
            <PublicLink to="/#journal" navigate={navigate} onClick={() => setMenuOpen(false)}>Journal</PublicLink>
            <PublicLink className="nav-contact" to="/#contact" navigate={navigate} onClick={() => setMenuOpen(false)}>Get in touch <span aria-hidden="true">↗</span></PublicLink>
          </nav>
        </div>
      </header>
      {route === '/' || route === '' ? <Home navigate={navigate} />
        : route === '/blog' || route === '/blog/' ? <BlogList navigate={navigate} />
          : isProjectDetail ? <ProjectDetail slug={decodeURIComponent(route.slice('/projects/'.length).replace(/\/$/, ''))} navigate={navigate} />
            : isBlogDetail ? <BlogDetail slug={decodeURIComponent(route.slice('/blog/'.length).replace(/\/$/, ''))} navigate={navigate} />
              : <main id="main-content" className="portfolio-main narrow-main"><p className="section-eyebrow">PAGE NOT FOUND</p><h1>This page isn’t here.</h1><PublicLink className="text-link" to="/" navigate={navigate}>Return to the portfolio</PublicLink></main>}
      {route !== '/' && route !== '' && <footer className="portfolio-footer"><div className="section-inner footer-inner"><p>Portfolio</p><PublicLink to="/" navigate={navigate}>Home</PublicLink><PublicLink to="/login" navigate={navigate}>CMS sign in</PublicLink></div></footer>}
    </div>
  )
}
