'use client'
import { useState } from 'react'

export default function SignIn() {
  const [password, setPassword] = useState('')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  async function enter(role: 'login' | 'reviewer') {
    setBusy(true); setError('')
    try {
      const response = await fetch(`/api/session/${role}`, {method:'POST', headers:{'Content-Type':'application/json','X-Security-Request':'1'}, body:JSON.stringify(role === 'login' ? {password} : {})})
      const result = await response.json()
      if (!response.ok) throw new Error(result.detail || 'Unable to start your session.')
      window.location.assign('/')
    } catch (err) { setError(err instanceof Error ? err.message : 'Unable to connect. Please try again.') }
    finally { setBusy(false) }
  }
  return <main style={{minHeight:'90vh',display:'grid',placeItems:'center',background:'#080f1e',padding:24,color:'#e6edfa'}}>
    <section style={{maxWidth:480,width:'100%',background:'#111c31',padding:36,borderRadius:20,border:'1px solid #26354d'}}>
      <p style={{color:'#72afff',fontSize:12,letterSpacing:2}}>SECURITY CO</p>
      <h1 style={{fontSize:30,fontWeight:650,margin:'16px 0'}}>Your investigation workspace</h1>
      <p style={{color:'#aebdd3',lineHeight:1.6,marginBottom:24}}>Analyze suspicious links and emails, inspect evidence, and export investigation reports.</p>
      <form onSubmit={e=>{e.preventDefault();void enter('login')}}>
        <label htmlFor="password" style={{display:'block',marginBottom:8}}>Workspace password</label>
        <input id="password" type="password" autoComplete="current-password" required value={password} onChange={e=>setPassword(e.target.value)} style={{width:'100%',padding:12,borderRadius:8,border:'1px solid #465974',background:'#080f1e',color:'white'}} />
        <button disabled={busy} style={{width:'100%',background:'#5c9fff',color:'#071225',borderRadius:8,padding:12,marginTop:12,fontWeight:650}}>{busy?'Connecting…':'Sign in'}</button>
      </form>
      <div style={{borderTop:'1px solid #2c3d56',marginTop:28,paddingTop:24}}>
        <h2 style={{fontSize:19,fontWeight:600}}>Evaluator or reviewer?</h2>
        <p style={{fontSize:14,lineHeight:1.6,color:'#aebdd3',margin:'12px 0'}}>Try the same live link and email investigations, evidence views, history, and report downloads. No password needed.</p>
        <button disabled={busy} onClick={()=>void enter('reviewer')} style={{width:'100%',background:'#d3e5ff',color:'#071225',borderRadius:8,padding:13,fontWeight:650}}>Try the live reviewer demo →</button>
        <p style={{fontSize:12,lineHeight:1.6,color:'#aebdd3',marginTop:14}}>Separate history for your 24-hour session. Up to 10 scans, subject to the shared free allowance. History may reset on server restart. The free edition’s existing feature limits apply.</p>
      </div>
      {error && <p role="alert" style={{marginTop:16,color:'#ffb9b9'}}>{error}</p>}
    </section>
  </main>
}
