import { NextRequest, NextResponse } from 'next/server'
import { createHash, timingSafeEqual } from 'node:crypto'

export function proxy(request: NextRequest) {
  if (process.env.HOSTED_LITE !== 'true') return NextResponse.next()
  if (request.nextUrl.pathname === '/api/health') return NextResponse.next()
  const password = process.env.SECURITY_CO_ACCESS_PASSWORD
  if (!password) return new NextResponse('Set SECURITY_CO_ACCESS_PASSWORD in your host environment.', {status:503})
  const header = request.headers.get('authorization') || ''
  const decoded = header.startsWith('Basic ') ? Buffer.from(header.slice(6), 'base64').toString() : ''
  const expected = createHash('sha256').update(`reviewer:${password}`).digest()
  const actual = createHash('sha256').update(decoded).digest()
  if (timingSafeEqual(expected, actual)) return NextResponse.next()
  return new NextResponse('Sign in to Security Co using the reviewer account.', {
    status:401, headers:{'WWW-Authenticate':'Basic realm="Security Co", charset="UTF-8"', 'Cache-Control':'no-store'},
  })
}
