// 零依赖 Markdown → 安全 HTML 渲染器
// 先对原始文本做 HTML 转义防 XSS，再逐步应用 markdown 语法转换。
// 支持：标题、加粗、斜体、标红(==红字==)、列表、图片、链接、行内代码、引用、分割线。

function escapeHtml(s: string): string {
  return s
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;')
}

// 仅允许 http/https/相对路径，阻止 javascript: 等危险协议
function safeUrl(url: string): string {
  const u = url.trim()
  if (/^(https?:)?\/\//i.test(u) || u.startsWith('/') || u.startsWith('./') || u.startsWith('../') || u.startsWith('#')) {
    return u
  }
  if (/^data:image\//i.test(u)) return u
  return ''
}

function inline(text: string): string {
  let s = escapeHtml(text)
  // 图片 ![alt](url)
  s = s.replace(/!\[([^\]]*)\]\(([^)\s]+)\)/g, (_m, alt, url) => {
    const safe = safeUrl(url)
    if (!safe) return ''
    return `<img src="${safe}" alt="${alt}" />`
  })
  // 链接 [text](url)
  s = s.replace(/\[([^\]]+)\]\(([^)\s]+)\)/g, (_m, label, url) => {
    const safe = safeUrl(url)
    if (!safe) return label
    return `<a href="${safe}" target="_blank" rel="noopener noreferrer">${label}</a>`
  })
  // 行内代码 `code`
  s = s.replace(/`([^`]+)`/g, '<code>$1</code>')
  // 加粗 **text**
  s = s.replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>')
  // 标红 ==text==
  s = s.replace(/==([^=]+)==/g, '<mark>$1</mark>')
  // 斜体 *text*
  s = s.replace(/(^|[^*])\*([^*]+)\*/g, '$1<em>$2</em>')
  return s
}

export function renderMarkdown(src: string): string {
  if (!src) return ''
  const lines = src.replace(/\r\n/g, '\n').split('\n')
  const html: string[] = []
  let listType: 'ul' | 'ol' | null = null
  let paraBuf: string[] = []

  function flushPara() {
    if (paraBuf.length) {
      html.push(`<p>${inline(paraBuf.join(' '))}</p>`)
      paraBuf = []
    }
  }
  function closeList() {
    if (listType) {
      html.push(`</${listType}>`)
      listType = null
    }
  }

  for (const raw of lines) {
    const line = raw.trimEnd()

    if (!line.trim()) {
      flushPara()
      closeList()
      continue
    }

    // 分割线
    if (/^(-{3,}|\*{3,}|_{3,})$/.test(line.trim())) {
      flushPara(); closeList()
      html.push('<hr />')
      continue
    }

    // 标题
    const h = /^(#{1,6})\s+(.*)$/.exec(line)
    if (h) {
      flushPara(); closeList()
      const level = h[1].length
      html.push(`<h${level}>${inline(h[2])}</h${level}>`)
      continue
    }

    // 引用
    const q = /^>\s?(.*)$/.exec(line)
    if (q) {
      flushPara(); closeList()
      html.push(`<blockquote>${inline(q[1])}</blockquote>`)
      continue
    }

    // 无序列表
    const ul = /^[-*+]\s+(.*)$/.exec(line.trim())
    if (ul) {
      flushPara()
      if (listType !== 'ul') { closeList(); html.push('<ul>'); listType = 'ul' }
      html.push(`<li>${inline(ul[1])}</li>`)
      continue
    }

    // 有序列表
    const ol = /^\d+\.\s+(.*)$/.exec(line.trim())
    if (ol) {
      flushPara()
      if (listType !== 'ol') { closeList(); html.push('<ol>'); listType = 'ol' }
      html.push(`<li>${inline(ol[1])}</li>`)
      continue
    }

    // 普通段落（累积，空行才结束）
    closeList()
    paraBuf.push(line.trim())
  }

  flushPara()
  closeList()
  return html.join('\n')
}
