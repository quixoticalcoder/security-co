import { NextRequest, NextResponse } from 'next/server'
import { createHmac, timingSafeEqual } from 'node:crypto'

function validSession(value: string): boolean {
  try {
    const secret = process.env.SECURITY_CO_ACCESS_PASSWORD
    if (!secret) return false
    const [body, signature, extra] = value.split('.')
    if (!body || !signature || extra) return false
    const expected = createHmac('sha256', secret).update(body).digest('hex')
    if (signature.length !== expected.length || !timingSafeEqual(Buffer.from(signature), Buffer.from(expected))) return false
    const session = JSON.parse(Buffer.from(body, 'base64url').toString())
    return session.exp > Date.now() / 1000 && ((session.role === 'owner' && session.id === 'owner') || (session.role === 'reviewer' && /^[a-f0-9]{32}$/.test(session.id)))
  } catch { return false }
}

export function proxy(request: NextRequest) {
  if (process.env.HOSTED_LITE !== 'true') return NextResponse.next()
  const path = request.nextUrl.pathname
  const publicPath = path === '/signin' || path.startsWith('/_next/') || /^\/(icon[^/]*|apple-icon\.png|favicon\.ico)$/.test(path) || ['/api/health', '/api/session/login', '/api/session/reviewer', '/api/session/logout'].includes(path)
  if (publicPath) return NextResponse.next()
  if (validSession(request.cookies.get('security_session')?.value || '')) {
    const result = NextResponse.next()
    result.headers.set('Cache-Control', 'no-store')
    return result
  }
  if (path.startsWith('/api/')) return NextResponse.json({detail:'Your session expired. Sign in or start a reviewer session.'}, {status:401})
  return NextResponse.redirect(new URL('/signin', request.url))
}
