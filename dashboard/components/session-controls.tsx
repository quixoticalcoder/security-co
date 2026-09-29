'use client'
import { useEffect, useState } from 'react'
export function SessionControls() {
  const [role, setRole] = useState('')
  useEffect(()=>{fetch('/api/session').then(r=>r.ok?r.json():null).then(data=>setRole(data?.role || '')).catch(()=>{})},[])
  if (!role) return null
  return <div style={{display:'flex',justifyContent:'space-between',gap:16,padding:'8px 20px',fontSize:12,background:'#10192c',color:'#dce6ff'}}>
    <span>{role==='reviewer'?'Reviewer session · separate history · up to 10 scans / 24 hours':'Password workspace'}</span>
    <button onClick={async()=>{const r=await fetch('/api/session/logout',{method:'POST',headers:{'X-Security-Request':'1'}});if(r.ok)window.location.assign('/signin')}}>Sign out / change access</button>
  </div>
}
