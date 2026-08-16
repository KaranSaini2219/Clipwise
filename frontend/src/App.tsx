import { FormEvent, useRef, useState } from 'react'
import { ArrowUp, Bot, CheckCircle2, Clock3, Link, LoaderCircle, Play, RotateCcw, Send, Sparkles, Youtube } from 'lucide-react'
import { askVideo, processVideo, type ProcessResult, type Source } from './lib/api'

type Message = { role: 'user' | 'assistant'; body: string; sources?: Source[] }
const time = (seconds: number) => { const s = Math.round(seconds); const m = Math.floor(s / 60); return `${Math.floor(m / 60) ? `${Math.floor(m / 60)}:` : ''}${String(m % 60).padStart(Math.floor(m / 60) ? 2 : 1, '0')}:${String(s % 60).padStart(2, '0')}` }

function App() {
  const [url, setUrl] = useState('')
  const [result, setResult] = useState<ProcessResult | null>(null)
  const [error, setError] = useState('')
  const [processing, setProcessing] = useState(false)
  const [question, setQuestion] = useState('')
  const [asking, setAsking] = useState(false)
  const [messages, setMessages] = useState<Message[]>([])
  const chatEnd = useRef<HTMLDivElement>(null)

  async function onProcess(event: FormEvent) {
    event.preventDefault(); setError(''); setProcessing(true)
    try { const processed = await processVideo(url); setResult(processed); setMessages([]) }
    catch (e) { setError(e instanceof Error ? e.message : 'Unable to process this video.') }
    finally { setProcessing(false) }
  }
  async function onAsk(event: FormEvent) {
    event.preventDefault(); if (!result || !question.trim() || asking) return
    const text = question.trim(); setQuestion(''); setMessages(old => [...old, { role: 'user', body: text }]); setAsking(true)
    try { const response = await askVideo(result.video.video_id, text); setMessages(old => [...old, { role: 'assistant', body: response.answer, sources: response.sources }]) }
    catch (e) { setMessages(old => [...old, { role: 'assistant', body: e instanceof Error ? e.message : 'I could not answer that.' }]) }
    finally { setAsking(false); requestAnimationFrame(() => chatEnd.current?.scrollIntoView({ behavior: 'smooth' })) }
  }
  function reset() { setResult(null); setMessages([]); setUrl(''); setError('') }

  return <main className="min-h-screen text-slate-100 selection:bg-violet-400/30">
    <div className="aurora a1" /><div className="aurora a2" />
    <div className="relative mx-auto max-w-6xl px-5 pb-16 pt-7 sm:px-8">
      <header className="mb-16 flex items-center justify-between"><div className="flex items-center gap-3"><div className="grid h-10 w-10 place-items-center rounded-xl bg-violet-500 shadow-lg shadow-violet-500/25"><Sparkles size={19}/></div><span className="text-lg font-bold tracking-tight">clipwise</span></div>{result && <button onClick={reset} className="quiet-button"><RotateCcw size={15}/> New video</button>}</header>
      {!result ? <section className="mx-auto max-w-3xl pt-8 text-center">
        <div className="eyebrow"><Youtube size={14}/> TRANSCRIPT-POWERED VIDEO INTELLIGENCE</div>
        <h1 className="mt-6 font-display text-5xl font-semibold leading-[1.03] tracking-tight text-white sm:text-7xl">Your video,<br/><span className="text-gradient">finally searchable.</span></h1>
        <p className="mx-auto mt-6 max-w-xl text-base leading-7 text-slate-400 sm:text-lg">Paste a YouTube link. We turn its transcript into a focused summary and a conversation you can trust.</p>
        <form onSubmit={onProcess} className="input-shell mx-auto mt-10 flex max-w-2xl gap-2 p-2"><div className="flex min-w-0 flex-1 items-center gap-3 px-3"><Link className="shrink-0 text-violet-300" size={19}/><input value={url} onChange={e => setUrl(e.target.value)} placeholder="Paste a YouTube video URL" aria-label="YouTube video URL" /></div><button disabled={processing || !url.trim()} className="primary-button">{processing ? <><LoaderCircle className="animate-spin" size={17}/> Reading video</> : <><ArrowUp size={18}/> Analyze</>}</button></form>
        {error && <div className="error-box">{error}</div>}
        {processing && <div className="mt-8 flex justify-center gap-7 text-sm text-slate-400"><span className="flex items-center gap-2"><LoaderCircle className="animate-spin text-violet-400" size={15}/> Fetching captions</span><span className="hidden sm:inline">·</span><span>Building searchable context</span></div>}
        <div className="mt-16 grid grid-cols-1 gap-3 text-left sm:grid-cols-3"><Feature n="01" title="Transcript-native" copy="Answers stay grounded in the words actually said."/><Feature n="02" title="Source-aware" copy="Jump to the relevant moment with timestamp references."/><Feature n="03" title="Ask freely" copy="Follow up without reprocessing the video."/></div>
      </section> : <section className="grid gap-7 lg:grid-cols-[minmax(0,1fr)_330px]">
        <div className="min-w-0 space-y-6"><VideoCard result={result}/><Summary summary={result.summary}/><Chat videoId={result.video.video_id} messages={messages} question={question} setQuestion={setQuestion} asking={asking} onAsk={onAsk} chatEnd={chatEnd}/></div>
        <aside className="order-first lg:order-none"><div className="sticky top-7 rounded-2xl border border-white/8 bg-slate-900/50 p-5"><p className="text-xs font-semibold uppercase tracking-[.16em] text-slate-500">Video context</p><div className="mt-5 space-y-4 text-sm text-slate-300"><Meta icon={<Clock3 size={16}/>} label="Duration" value={time(result.video.duration_seconds)}/><Meta icon={<CheckCircle2 size={16}/>} label="Transcript" value={result.video.transcript_source}/><Meta icon={<Bot size={16}/>} label="Indexed" value={`${result.indexed_chunks} passages`}/></div><div className="mt-6 border-t border-white/8 pt-5"><p className="text-xs leading-5 text-slate-500">Every response is constrained to retrieved transcript passages.</p></div></div></aside>
      </section>}
    </div>
  </main>
}
function Feature({n,title,copy}:{n:string;title:string;copy:string}) { return <div className="feature"><span>{n}</span><h3>{title}</h3><p>{copy}</p></div> }
function Meta({icon,label,value}:{icon:React.ReactNode;label:string;value:string}) { return <div className="flex gap-3"><span className="text-violet-300">{icon}</span><div><p className="text-xs text-slate-500">{label}</p><p className="mt-0.5 font-medium">{value}</p></div></div> }
function VideoCard({result}:{result:ProcessResult}) { return <article className="video-card overflow-hidden rounded-2xl border border-white/10"><div className="relative h-44 sm:h-60"><img className="h-full w-full object-cover opacity-80" src={result.video.thumbnail_url} alt=""/><div className="absolute inset-0 bg-gradient-to-t from-[#11182b] via-[#11182b]/10 to-transparent"/><a href={result.video.url} target="_blank" rel="noreferrer" className="play-button"><Play size={18} fill="currentColor"/></a></div><div className="p-5 sm:p-6"><p className="mb-2 text-xs font-semibold uppercase tracking-[.15em] text-violet-300">Ready to explore</p><h2 className="font-display text-2xl font-semibold text-white sm:text-3xl">{result.video.title}</h2>{result.already_indexed && <p className="mt-3 text-sm text-emerald-300">Already indexed — your saved transcript is ready.</p>}</div></article> }
function Summary({summary}:{summary:string}) { return <article className="rounded-2xl border border-violet-400/15 bg-violet-500/[.07] p-6 sm:p-7"><div className="flex items-center gap-3"><div className="grid h-9 w-9 place-items-center rounded-lg bg-violet-500/20 text-violet-200"><Sparkles size={17}/></div><div><p className="text-sm font-semibold text-white">Video summary</p><p className="text-xs text-slate-500">Generated only from the transcript</p></div></div><div className="summary mt-5 whitespace-pre-wrap text-[15px] leading-7 text-slate-300">{summary}</div></article> }
function Chat({videoId,messages,question,setQuestion,asking,onAsk,chatEnd}:{videoId:string;messages:Message[];question:string;setQuestion:(s:string)=>void;asking:boolean;onAsk:(e:FormEvent)=>void;chatEnd:React.RefObject<HTMLDivElement|null>}) { const suggestions=['What are the main points?','What examples were given?','What is the key conclusion?']; return <section className="rounded-2xl border border-white/10 bg-slate-900/50"><div className="border-b border-white/8 px-6 py-5"><h2 className="font-semibold text-white">Ask about this video</h2><p className="mt-1 text-sm text-slate-500">Answers cite the moments used to answer you.</p></div><div className="min-h-[270px] space-y-5 p-5 sm:p-6">{messages.length === 0 && <div className="flex h-[220px] flex-col items-center justify-center text-center"><div className="grid h-11 w-11 place-items-center rounded-full bg-violet-500/15 text-violet-300"><Bot size={20}/></div><p className="mt-4 text-sm text-slate-400">Start with a question, or try one below.</p><div className="mt-4 flex flex-wrap justify-center gap-2">{suggestions.map(s=><button key={s} onClick={()=>setQuestion(s)} className="suggestion">{s}</button>)}</div></div>}{messages.map((message,i)=><div key={i} className={`message ${message.role}`}><div className="message-label">{message.role === 'user' ? 'You' : 'Clipwise'}</div><div className="whitespace-pre-wrap leading-7">{message.body}</div>{message.sources && <div className="mt-4 flex flex-wrap gap-2">{message.sources.map((source,j)=><a key={j} href={`https://www.youtube.com/watch?v=${videoId}&t=${Math.floor(source.start_seconds)}s`} target="_blank" rel="noreferrer" title={source.excerpt} className="source"><Clock3 size={12}/>{source.label}</a>)}</div>}</div>)}{asking && <div className="message assistant"><div className="message-label">Clipwise</div><LoaderCircle className="animate-spin text-violet-300" size={18}/></div>}<div ref={chatEnd}/></div><form onSubmit={onAsk} className="flex gap-2 border-t border-white/8 p-3"><input value={question} onChange={e=>setQuestion(e.target.value)} placeholder="Ask a question about the transcript…"/><button aria-label="Send question" disabled={!question.trim() || asking} className="send"><Send size={17}/></button></form></section> }
export default App
