import { useEffect, useState } from 'react';
import { api } from '../lib/api';
import { Bar, BigScore, Btn, Card, Chips, ErrorMsg, errText, PageTitle, Pill } from '../components/ui';

export default function Companies() {
  const [tab, setTab] = useState<'co' | 'jd' | 'live'>('co');
  const [m, setM] = useState<any[] | null>(null);
  const [note, setNote] = useState('');
  const [jd, setJd] = useState('');
  const [r, setR] = useState<any>(null);
  const [err, setErr] = useState('');
  const [liveRole, setLiveRole] = useState('Software Developer');
  const [liveLocation, setLiveLocation] = useState('India');
  const [liveWorkMode, setLiveWorkMode] = useState('all');
  const [liveJobs, setLiveJobs] = useState<any[] | null>(null);
  const [liveNotes, setLiveNotes] = useState<string[]>([]);
  const [liveDisclaimer, setLiveDisclaimer] = useState('');
  const [loadingLive, setLoadingLive] = useState(false);
  const searchLiveJobs = async () => { setErr(''); setLoadingLive(true); try { const data = (await api.get('/jobs/live', { params: { role: liveRole, location: liveLocation, limit: 30, work_mode: liveWorkMode } })).data; setLiveJobs(data.jobs || []); setLiveNotes(data.notes || []); setLiveDisclaimer(data.disclaimer || ''); } catch (e) { setErr(errText(e)); } finally { setLoadingLive(false); } };
  useEffect(() => { api.get('/companies/matches', { params: { top: 14 } }).then((x) => { setM(x.data.matches); setNote(x.data.note); }).catch((e) => setErr(errText(e))); }, []);
  const tone: any = { 'Strong fit': 'green', 'Good fit': 'cyan', Stretch: 'amber', 'Not yet': 'red' };
  return (
    <>
      <PageTitle title="Job Matching Agent" sub="Company/role matches from your skills, profile similarity, coding strength and CGPA, plus job-description matching." />
      <div className="flex gap-2 mb-5"><Btn variant={tab === 'co' ? 'primary' : 'ghost'} onClick={() => setTab('co')}>Company / role matches</Btn><Btn variant={tab === 'jd' ? 'primary' : 'ghost'} onClick={() => setTab('jd')}>Match a job description</Btn><Btn variant={tab === 'live' ? 'primary' : 'ghost'} onClick={() => setTab('live')}>Live job vacancies</Btn></div>
      <ErrorMsg msg={err} />
      {tab === 'co' && <>
        {!m && !err && <div className="text-slate-400">Matching…</div>}
        <div className="grid lg:grid-cols-2 gap-4">
          {m?.map((x) => (
            <Card key={x.company + x.role}>
              <div className="flex justify-between items-start"><div><b className="text-lg">{x.company}</b><div className="text-sm text-slate-400">{x.role} · {x.category}</div></div>
                <div className="text-right"><div className="text-3xl font-bold text-cyan-300">{x.match_score}%</div><Pill tone={tone[x.fit]}>{x.fit}</Pill></div></div>
              <div className="mt-4"><Bar value={x.breakdown.skills} label="Skills" /><Bar value={x.breakdown.dsa_fit} label="DSA fit" /><Bar value={x.breakdown.academics} label="Academics" /></div>
              {x.missing_skills.length > 0 && <div className="mt-2"><div className="text-xs text-slate-500 mb-2">Missing core skills</div><Chips tone="amber" items={x.missing_skills} /></div>}
              {x.how_to_improve.length > 0 && <ul className="list-disc pl-5 text-sm text-slate-300 mt-3">{x.how_to_improve.map((t: string) => <li key={t}>{t}</li>)}</ul>}
              <div className="text-xs text-slate-500 mt-3">Process: {x.selection_process}</div>
            </Card>))}
        </div>
        {note && <div className="text-xs text-slate-500 mt-4">{note}</div>}
      </>}
      {tab === 'live' && <>
        <Card className="mb-4">
          <div className="grid md:grid-cols-4 gap-3 items-end">
            <label className="text-sm text-slate-400">Target role<input className="mt-2 w-full" value={liveRole} onChange={(e) => setLiveRole(e.target.value)} placeholder="e.g. Python Developer" /></label>
            <label className="text-sm text-slate-400">Preferred location<input className="mt-2 w-full" value={liveLocation} onChange={(e) => setLiveLocation(e.target.value)} placeholder="e.g. Bengaluru, India" /></label>
            <label className="text-sm text-slate-400">Work arrangement<select className="mt-2 w-full" value={liveWorkMode} onChange={(e) => setLiveWorkMode(e.target.value)}><option value="all">All (Remote + Hybrid + Office)</option><option value="remote">Remote / Work from home</option><option value="hybrid">Hybrid</option><option value="onsite">Work from office</option></select></label>
            <Btn disabled={!liveRole.trim() || loadingLive} onClick={searchLiveJobs}>{loadingLive ? 'Searching…' : 'Find live jobs'}</Btn>
          </div>
          <p className="text-xs text-slate-500 mt-3">Searches free public job feeds, including India-specific remote, hybrid and office vacancies from JobsForce India. Company career-board feeds can vary by availability. Listings are ranked against your profile. AI explanations are optional; rule-based matching works without an API key.</p>
        </Card>
        {liveNotes.map((n) => <div key={n} className="text-xs text-amber-300 mb-2">{n}</div>)}
        {liveJobs && <>
          <div className="text-sm text-slate-400 mb-3">{liveJobs.length} real vacancies found · ranked by profile match</div>
          <div className="grid lg:grid-cols-2 gap-4">
            {liveJobs.map((job) => <Card key={job.id}>
              <div className="flex justify-between gap-3 items-start"><div><b className="text-lg">{job.title}</b><div className="text-sm text-slate-300">{job.company}</div><div className="text-xs text-slate-500 mt-1">{job.location} · {job.work_mode || (job.remote ? "Remote" : "Work arrangement not specified")} · {job.job_type}</div></div><div className="text-right"><div className="text-2xl font-bold text-cyan-300">{job.match_score}%</div><Pill tone={tone[job.fit]}>{job.fit}</Pill></div></div>
              {job.salary && <div className="text-sm text-emerald-300 mt-3">Salary: {job.salary}</div>}
              <div className="mt-3 text-sm"><b>Why recommended?</b><ul className="list-disc pl-5 mt-1 text-slate-300">{job.why_recommended.map((reason: string) => <li key={reason}>{reason}</li>)}</ul></div>
              {job.matched_skills?.length > 0 && <div className="mt-3"><div className="text-xs text-slate-500 mb-1">Matched skills</div><Chips tone="green" items={job.matched_skills} /></div>}
              {job.missing_skills?.length > 0 && <div className="mt-2"><div className="text-xs text-slate-500 mb-1">Skills to improve</div><Chips tone="amber" items={job.missing_skills} /></div>}
              <div className="flex justify-between items-center mt-4"><span className="text-xs text-slate-500">Source: {job.source}</span><a className="text-cyan-300 underline text-sm" href={job.application_url} target="_blank" rel="noreferrer">View original job ↗</a></div>
            </Card>)}
          </div>
          {liveJobs.length === 0 && <p className="text-slate-400">No vacancies found. Try a broader role or location.</p>}
          {liveDisclaimer && <p className="text-xs text-slate-500 mt-4">{liveDisclaimer}</p>}
        </>}
      </>}
      {tab === 'jd' && <Card>
        <textarea className="min-h-64" value={jd} onChange={(e) => setJd(e.target.value)} placeholder="Paste the job description…" />
        <div className="mt-4"><Btn disabled={jd.length < 20} onClick={async () => { setErr(''); try { setR((await api.post('/job/match', { job_description: jd })).data); } catch (e) { setErr(errText(e)); } }}>Match job</Btn></div>
        {r && <div className="mt-6 grid md:grid-cols-2 gap-5"><div><BigScore value={r.match_score} label="Match score" /><div className="mt-2"><Pill tone={tone[r.fit]}>{r.fit}</Pill></div>{r.note && <p className="text-sm text-amber-300 mt-3">{r.note}</p>}</div>
          <div><div className="text-sm text-slate-400 mb-2">You have</div><Chips tone="green" items={r.matched} /><div className="text-sm text-slate-400 mt-4 mb-2">Missing</div><Chips tone="amber" items={r.missing} />
            {r.advice.length > 0 && <ul className="list-disc pl-5 text-sm text-slate-300 mt-4">{r.advice.map((a: string) => <li key={a}>{a}</li>)}</ul>}</div></div>}
      </Card>}
    </>
  );
}
