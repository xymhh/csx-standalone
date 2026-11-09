/**
 * 外链海报地址转换。
 *
 * 豆瓣与 Bangumi 的图床带 Referer 校验，浏览器直连会拿到 418/403 的占位模糊图，
 * 因此这些域名统一改走后端代理（服务端补 Referer），其余图床（TMDB 等）保持原样。
 */
const PROXIED_HOSTS = ['doubanio.com', 'bgm.tv', 'anilist.co']

export function posterSrc(url: string | null | undefined): string | undefined {
  if (!url) return undefined
  try {
    const parsed = new URL(url)
    if (parsed.protocol === 'https:' && PROXIED_HOSTS.some((host) => parsed.hostname.endsWith(host))) {
      return `/api/v1/media/poster?url=${encodeURIComponent(url)}`
    }
  } catch {
    // 非绝对 URL（相对路径或脏数据）直接交给浏览器处理
  }
  return url
}
