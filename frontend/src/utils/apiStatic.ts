/** 将后端静态路径（如 /static/announcements/xxx.png）转为完整 URL */
export function resolveApiStaticUrl(path: string | null | undefined): string {
  if (!path) return ''
  if (/^https?:\/\//i.test(path)) return path
  const base = import.meta.env.VITE_API_BASE_URL || ''
  const origin = base.replace(/\/?api\/v1\/?$/i, '').replace(/\/$/, '')
  const p = path.startsWith('/') ? path : `/${path}`
  return `${origin}${p}`
}
