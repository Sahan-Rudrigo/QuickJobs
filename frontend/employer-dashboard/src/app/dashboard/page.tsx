'use client';

import '@/lib/amplify';
import { useEffect, useState } from 'react';
import { getCurrentUser, signOut, fetchUserAttributes } from 'aws-amplify/auth';
import { useRouter } from 'next/navigation';
import {
  LayoutDashboard, PlusCircle, Briefcase, Users, LogOut,
  Bell, Search, TrendingUp, MapPin, Clock, DollarSign,
  Calendar, Trash2, RefreshCw, ChevronRight, Menu, X,
} from 'lucide-react';
import {
  BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer,
  PieChart, Pie, Cell, Legend,
} from 'recharts';

type Job = {
  id: string; title: string; company: string; location: string;
  type: string; salary: string; description: string; skills: string;
  deadline: string; postedAt: string; applications: number;
  status: 'Active' | 'Closed';
};

const emptyForm = {
  title: '', company: '', location: '', type: 'Full-time',
  salary: '', description: '', skills: '', deadline: '',
};

const PIE_COLORS  = ['#2563EB', '#CECCC8'];
const TYPE_COLORS: Record<string, string> = {
  'Full-time': '#2563EB', 'Part-time': '#7C3AED',
  'Contract': '#D97706', 'Remote': '#16A34A', 'Internship': '#DB2777',
};

const card: React.CSSProperties = {
  background: 'var(--bg-elevated)',
  border: '1px solid var(--border-subtle)',
  borderRadius: '16px',
  boxShadow: 'var(--shadow-sm)',
};

export default function DashboardPage() {
  const router = useRouter();
  const [userEmail, setUserEmail]     = useState('');
  const [companyName, setCompanyName] = useState('');
  const [view, setView]               = useState('Overview');
  const [jobs, setJobs]               = useState<Job[]>([]);
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const [form, setForm]               = useState(emptyForm);
  const [posting, setPosting]         = useState(false);
  const [postSuccess, setPostSuccess] = useState(false);

  useEffect(() => {
    getCurrentUser()
      .then(async u => {
        setUserEmail(u.username);
        const attrs = await fetchUserAttributes();
        setCompanyName(attrs.name || u.username.split('@')[0]);
      })
      .catch(() => router.push('/login'));
    const saved = localStorage.getItem('quickjobs_jobs');
    if (saved) setJobs(JSON.parse(saved));
  }, [router]);

  const saveJobs = (updated: Job[]) => {
    setJobs(updated);
    localStorage.setItem('quickjobs_jobs', JSON.stringify(updated));
  };

  const handlePost = async (e: React.FormEvent) => {
    e.preventDefault();
    setPosting(true);
    await new Promise(r => setTimeout(r, 700));
    saveJobs([{ id: Date.now().toString(), ...form, postedAt: new Date().toISOString(), applications: 0, status: 'Active' }, ...jobs]);
    setForm(emptyForm); setPosting(false); setPostSuccess(true);
    setTimeout(() => { setPostSuccess(false); setView('My Jobs'); }, 1500);
  };

  const toggleStatus = (id: string) =>
    saveJobs(jobs.map(j => j.id === id ? { ...j, status: j.status === 'Active' ? 'Closed' : 'Active' } : j));
  const deleteJob = (id: string) => saveJobs(jobs.filter(j => j.id !== id));

  const activeJobs = jobs.filter(j => j.status === 'Active').length;
  const totalApps  = jobs.reduce((s, j) => s + j.applications, 0);
  const jobsByType = ['Full-time', 'Part-time', 'Contract', 'Remote', 'Internship']
    .map(t => ({ name: t, Jobs: jobs.filter(j => j.type === t).length }))
    .filter(d => d.Jobs > 0);
  const pieData = [
    { name: 'Active', value: activeJobs },
    { name: 'Closed', value: jobs.length - activeJobs },
  ].filter(d => d.value > 0);

  const navItems = [
    { name: 'Overview',   icon: <LayoutDashboard size={16} /> },
    { name: 'Post a Job', icon: <PlusCircle size={16} />      },
    { name: 'My Jobs',    icon: <Briefcase size={16} />       },
    { name: 'Applicants', icon: <Users size={16} />           },
  ];

  return (
    <div className="flex h-screen overflow-hidden" style={{ background: 'var(--bg-base)' }}>

      {/* ── Sidebar ── */}
      <aside className="flex flex-col shrink-0 transition-all duration-200"
        style={{ width: sidebarOpen ? '224px' : '64px', background: 'var(--bg-elevated)', borderRight: '1px solid var(--border-subtle)' }}>

        <div className="flex items-center gap-3 overflow-hidden"
          style={{ padding: '20px 16px', borderBottom: '1px solid var(--border-subtle)', height: '64px' }}>
          <div className="shrink-0 w-8 h-8 rounded-xl flex items-center justify-center" style={{ background: 'var(--accent-1)' }}>
            <span className="text-white font-bold text-sm">Q</span>
          </div>
          {sidebarOpen && (
            <div>
              <p className="font-semibold text-sm leading-none" style={{ color: 'var(--text-primary)', letterSpacing: '-0.01em' }}>QuickJobs</p>
              <p className="text-xs mt-0.5" style={{ color: 'var(--text-tertiary)' }}>Employer Portal</p>
            </div>
          )}
        </div>

        <nav className="flex-1 p-2 space-y-0.5">
          {navItems.map(item => {
            const active = view === item.name;
            return (
              <button key={item.name} onClick={() => setView(item.name)}
                className="w-full flex items-center gap-3 transition-all"
                style={{
                  padding: '9px 12px', borderRadius: '10px',
                  background: active ? 'var(--accent-1-soft)' : 'transparent',
                  color: active ? 'var(--accent-1)' : 'var(--text-secondary)',
                  fontSize: '14px', fontWeight: active ? 500 : 400,
                }}>
                <span className="shrink-0">{item.icon}</span>
                {sidebarOpen && <span className="whitespace-nowrap flex-1 text-left">{item.name}</span>}
                {sidebarOpen && item.name === 'My Jobs' && jobs.length > 0 && (
                  <span className="text-xs font-medium px-2 py-0.5 rounded-full"
                    style={{ background: 'var(--bg-sunken)', color: 'var(--text-secondary)' }}>
                    {jobs.length}
                  </span>
                )}
              </button>
            );
          })}
        </nav>

        <div className="p-2 space-y-0.5" style={{ borderTop: '1px solid var(--border-subtle)' }}>
          {sidebarOpen && companyName && (
            <div className="flex items-center gap-2.5 px-3 py-2.5 mb-1">
              <div className="w-7 h-7 rounded-full flex items-center justify-center shrink-0"
                style={{ background: 'var(--accent-1-soft)' }}>
                <span className="text-xs font-semibold" style={{ color: 'var(--accent-1)' }}>{companyName[0]?.toUpperCase()}</span>
              </div>
              <div className="flex-1 min-w-0">
                <p className="text-xs font-medium truncate" style={{ color: 'var(--text-primary)' }}>{companyName}</p>
                <p className="text-xs truncate" style={{ color: 'var(--text-tertiary)' }}>{userEmail}</p>
              </div>
            </div>
          )}
          <button onClick={() => setSidebarOpen(v => !v)}
            className="w-full flex items-center gap-3 transition-all"
            style={{ padding: '9px 12px', borderRadius: '10px', color: 'var(--text-tertiary)', fontSize: '14px' }}>
            {sidebarOpen ? <X size={16} /> : <Menu size={16} />}
            {sidebarOpen && <span>Collapse</span>}
          </button>
          <button onClick={async () => { await signOut(); router.push('/login'); }}
            className="w-full flex items-center gap-3 transition-all"
            style={{ padding: '9px 12px', borderRadius: '10px', color: 'var(--accent-danger)', fontSize: '14px' }}>
            <LogOut size={16} className="shrink-0" />
            {sidebarOpen && <span>Sign Out</span>}
          </button>
        </div>
      </aside>

      {/* ── Main ── */}
      <div className="flex-1 flex flex-col overflow-hidden">

        {/* Header */}
        <header className="flex items-center gap-4 shrink-0"
          style={{ height: '64px', padding: '0 24px', background: 'var(--bg-elevated)', borderBottom: '1px solid var(--border-subtle)' }}>
          <div className="flex items-center gap-2">
            <h1 className="text-sm font-semibold" style={{ color: 'var(--text-primary)' }}>{view}</h1>
            <ChevronRight size={13} style={{ color: 'var(--text-tertiary)' }} />
          </div>
          <div className="flex-1 overflow-hidden rounded-xl hidden lg:block"
            style={{ background: 'var(--bg-sunken)', padding: '6px 12px', maxWidth: '480px' }}>
            <div className="flex animate-marquee whitespace-nowrap">
              {[0, 1].map(i => (
                <span key={i} className="text-xs inline-flex items-center gap-2.5 pr-10" style={{ color: 'var(--text-secondary)' }}>
                  <span className="font-medium" style={{ color: 'var(--text-primary)' }}>{companyName || 'QuickJobs'}</span>
                  <span style={{ color: 'var(--text-tertiary)' }}>▸</span>
                  <span>{jobs.length} Jobs Posted</span>
                  <span style={{ color: 'var(--text-tertiary)' }}>▸</span>
                  <span>{activeJobs} Active</span>
                  <span style={{ color: 'var(--text-tertiary)' }}>▸</span>
                  <span>{totalApps} Applications</span>
                  <span style={{ color: 'var(--text-tertiary)' }}>▸</span>
                </span>
              ))}
            </div>
          </div>
          <div className="ml-auto flex items-center gap-2">
            <div className="hidden md:flex items-center gap-2 rounded-xl"
              style={{ background: 'var(--bg-sunken)', padding: '8px 12px' }}>
              <Search size={13} style={{ color: 'var(--text-tertiary)' }} />
              <input className="bg-transparent text-sm outline-none w-24" placeholder="Search…" style={{ color: 'var(--text-primary)' }} />
            </div>
            <button className="relative w-9 h-9 flex items-center justify-center rounded-xl" style={{ color: 'var(--text-secondary)' }}>
              <Bell size={17} />
              <span className="absolute top-2 right-2 w-1.5 h-1.5 rounded-full" style={{ background: 'var(--accent-1)' }} />
            </button>
          </div>
        </header>

        {/* Content */}
        <main className="flex-1 overflow-y-auto" style={{ padding: '32px' }}>

          {/* ── OVERVIEW ── */}
          {view === 'Overview' && (
            <div className="space-y-6 max-w-[1280px]">
              <div className="rounded-2xl p-8 flex items-center justify-between"
                style={{ background: 'var(--accent-1)', boxShadow: '0 4px 24px rgba(37,99,235,0.25)' }}>
                <div>
                  <p className="text-blue-200 text-xs font-medium uppercase tracking-[0.08em] mb-2">Welcome back</p>
                  <h2 className="text-white text-xl font-semibold mb-1.5" style={{ letterSpacing: '-0.01em' }}>
                    {companyName || userEmail.split('@')[0]}
                  </h2>
                  <p className="text-blue-200 text-sm">
                    {jobs.length === 0
                      ? 'Post your first job listing to start finding candidates.'
                      : `${activeJobs} active listing${activeJobs !== 1 ? 's' : ''} · ${totalApps} application${totalApps !== 1 ? 's' : ''}`}
                  </p>
                </div>
                <button onClick={() => setView('Post a Job')}
                  className="hidden md:flex items-center gap-2 font-medium text-sm text-white"
                  style={{ padding: '10px 20px', background: 'rgba(255,255,255,0.15)', border: '1px solid rgba(255,255,255,0.25)', borderRadius: '10px', backdropFilter: 'blur(8px)' }}>
                  <PlusCircle size={15} /> Post a Job
                </button>
              </div>

              <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
                {[
                  { label: 'Jobs Posted',      value: jobs.length, icon: <Briefcase size={18} />,  accent: 'var(--accent-1)', soft: 'var(--accent-1-soft)' },
                  { label: 'Active Listings',  value: activeJobs,  icon: <TrendingUp size={18} />, accent: '#16A34A',         soft: '#F0FDF4' },
                  { label: 'Applications',     value: totalApps,   icon: <Users size={18} />,      accent: '#7C3AED',         soft: '#F5F3FF' },
                  { label: 'WhatsApp Matches', value: totalApps,   icon: <Bell size={18} />,       accent: '#D97706',         soft: '#FFFBEB' },
                ].map((s, i) => (
                  <div key={s.label} className="animate-reveal-up" style={{ ...card, padding: '24px', animationDelay: `${i * 60}ms`, opacity: 0 }}>
                    <div className="flex items-center justify-between mb-4">
                      <p className="text-xs font-medium uppercase tracking-[0.06em]" style={{ color: 'var(--text-secondary)' }}>{s.label}</p>
                      <div className="w-8 h-8 rounded-xl flex items-center justify-center" style={{ background: s.soft, color: s.accent }}>{s.icon}</div>
                    </div>
                    <p className="font-bold" style={{ fontSize: '36px', color: 'var(--text-primary)', letterSpacing: '-0.02em', lineHeight: 1 }}>{s.value}</p>
                  </div>
                ))}
              </div>

              <div className="grid lg:grid-cols-2 gap-4">
                <div style={{ ...card, padding: '32px' }}>
                  <p className="font-semibold mb-0.5" style={{ color: 'var(--text-primary)', fontSize: '15px' }}>Jobs by Type</p>
                  <p className="text-xs mb-6" style={{ color: 'var(--text-secondary)' }}>Distribution of your posted listings</p>
                  {jobsByType.length === 0
                    ? <EmptyChart icon={<Briefcase size={28} />} text="Post jobs to see analytics" />
                    : (
                      <ResponsiveContainer width="100%" height={180}>
                        <BarChart data={jobsByType}>
                          <XAxis dataKey="name" tick={{ fontSize: 11, fill: 'var(--text-secondary)' }} />
                          <YAxis allowDecimals={false} tick={{ fontSize: 11, fill: 'var(--text-secondary)' }} />
                          <Tooltip contentStyle={{ borderRadius: '10px', border: '1px solid var(--border-subtle)', fontSize: '13px' }} />
                          <Bar dataKey="Jobs" radius={[6, 6, 0, 0]}>
                            {jobsByType.map((e, i) => <Cell key={i} fill={TYPE_COLORS[e.name] || 'var(--accent-1)'} />)}
                          </Bar>
                        </BarChart>
                      </ResponsiveContainer>
                    )}
                </div>
                <div style={{ ...card, padding: '32px' }}>
                  <p className="font-semibold mb-0.5" style={{ color: 'var(--text-primary)', fontSize: '15px' }}>Listing Status</p>
                  <p className="text-xs mb-6" style={{ color: 'var(--text-secondary)' }}>Active vs closed job listings</p>
                  {pieData.length === 0
                    ? <EmptyChart icon={<TrendingUp size={28} />} text="No listings yet" />
                    : (
                      <ResponsiveContainer width="100%" height={180}>
                        <PieChart>
                          <Pie data={pieData} cx="50%" cy="50%" innerRadius={50} outerRadius={75} paddingAngle={4} dataKey="value">
                            {pieData.map((_, i) => <Cell key={i} fill={PIE_COLORS[i]} />)}
                          </Pie>
                          <Legend iconType="circle" iconSize={8} wrapperStyle={{ fontSize: '12px' }} />
                          <Tooltip contentStyle={{ borderRadius: '10px', border: '1px solid var(--border-subtle)', fontSize: '13px' }} />
                        </PieChart>
                      </ResponsiveContainer>
                    )}
                </div>
              </div>

              <div style={{ ...card, padding: '32px' }}>
                <div className="flex items-center justify-between mb-6">
                  <p className="font-semibold" style={{ color: 'var(--text-primary)', fontSize: '15px' }}>Recent Listings</p>
                  <button onClick={() => setView('My Jobs')} className="flex items-center gap-1 text-xs font-medium" style={{ color: 'var(--accent-1)' }}>
                    View all <ChevronRight size={13} />
                  </button>
                </div>
                {jobs.length === 0 ? (
                  <div className="text-center py-12">
                    <div className="w-12 h-12 rounded-2xl flex items-center justify-center mx-auto mb-4" style={{ background: 'var(--bg-sunken)' }}>
                      <Briefcase size={20} style={{ color: 'var(--text-tertiary)' }} />
                    </div>
                    <p className="font-medium mb-1" style={{ color: 'var(--text-primary)', fontSize: '15px' }}>No jobs posted yet</p>
                    <p className="text-sm mb-5" style={{ color: 'var(--text-secondary)' }}>Post your first listing to get started</p>
                    <button onClick={() => setView('Post a Job')} className="text-white text-sm font-medium"
                      style={{ padding: '9px 20px', background: 'var(--accent-1)', borderRadius: '10px' }}>
                      Post a Job
                    </button>
                  </div>
                ) : (
                  <div style={{ borderTop: '1px solid var(--border-subtle)' }}>
                    {jobs.slice(0, 4).map(job => (
                      <div key={job.id} className="flex items-center gap-4 py-4" style={{ borderBottom: '1px solid var(--border-subtle)' }}>
                        <div className="w-9 h-9 rounded-xl flex items-center justify-center shrink-0" style={{ background: 'var(--bg-sunken)' }}>
                          <Briefcase size={15} style={{ color: 'var(--text-secondary)' }} />
                        </div>
                        <div className="flex-1 min-w-0">
                          <p className="font-medium text-sm truncate" style={{ color: 'var(--text-primary)' }}>{job.title}</p>
                          <p className="text-xs" style={{ color: 'var(--text-secondary)' }}>{job.company} · {job.location}</p>
                        </div>
                        <JobStatusBadge status={job.status} />
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </div>
          )}

          {/* ── POST A JOB ── */}
          {view === 'Post a Job' && (
            <div className="max-w-2xl">
              <div className="mb-8">
                <h2 className="font-semibold mb-1" style={{ fontSize: '20px', color: 'var(--text-primary)', letterSpacing: '-0.01em' }}>Post a Job</h2>
                <p className="text-sm" style={{ color: 'var(--text-secondary)' }}>Fill in the details to create a new listing.</p>
              </div>
              {postSuccess && (
                <div className="flex items-center gap-3 mb-6 animate-toast"
                  style={{ padding: '14px 16px', background: '#F0FDF4', border: '1px solid #BBF7D0', borderRadius: '12px' }}>
                  <p className="text-sm font-medium" style={{ color: '#15803D' }}>✓ Job posted! Redirecting…</p>
                </div>
              )}
              <form onSubmit={handlePost} style={{ ...card }}>
                <div style={{ padding: '24px 32px', borderBottom: '1px solid var(--border-subtle)' }}>
                  <p className="font-semibold" style={{ color: 'var(--text-primary)', fontSize: '15px' }}>New Listing</p>
                  <p className="text-xs mt-0.5" style={{ color: 'var(--text-secondary)' }}>Fields marked * are required</p>
                </div>
                <div style={{ padding: '32px', display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '20px' }}>
                  <div style={{ gridColumn: '1 / -1' }}>
                    <FormField label="Job Title *" value={form.title} onChange={v => setForm({ ...form, title: v })} placeholder="e.g. Senior Software Engineer" required />
                  </div>
                  <FormField label="Company Name *" value={form.company} onChange={v => setForm({ ...form, company: v })} placeholder="e.g. ABC Technologies" required />
                  <FormField label="Location *" value={form.location} onChange={v => setForm({ ...form, location: v })} placeholder="e.g. Colombo" required icon={<MapPin size={13} />} />
                  <div>
                    <label className="block text-sm font-medium mb-1.5" style={{ color: 'var(--text-primary)' }}>Job Type *</label>
                    <div className="relative">
                      <Clock size={13} className="absolute left-3 top-1/2 -translate-y-1/2" style={{ color: 'var(--text-tertiary)' }} />
                      <select value={form.type} onChange={e => setForm({ ...form, type: e.target.value })} className="w-full text-sm"
                        style={{ padding: '11px 16px 11px 36px', background: 'var(--bg-sunken)', border: '1px solid transparent', borderRadius: '10px', color: 'var(--text-primary)', outline: 'none', appearance: 'none' }}>
                        {['Full-time', 'Part-time', 'Contract', 'Remote', 'Internship'].map(t => <option key={t}>{t}</option>)}
                      </select>
                    </div>
                  </div>
                  <FormField label="Salary Range" value={form.salary} onChange={v => setForm({ ...form, salary: v })} placeholder="e.g. LKR 80,000–120,000" icon={<DollarSign size={13} />} />
                  <FormField label="Deadline" type="date" value={form.deadline} onChange={v => setForm({ ...form, deadline: v })} icon={<Calendar size={13} />} />
                  <div style={{ gridColumn: '1 / -1' }}>
                    <FormField label="Required Skills" value={form.skills} onChange={v => setForm({ ...form, skills: v })} placeholder="e.g. Python, React, SQL (comma separated)" />
                  </div>
                  <div style={{ gridColumn: '1 / -1' }}>
                    <label className="block text-sm font-medium mb-1.5" style={{ color: 'var(--text-primary)' }}>Job Description *</label>
                    <textarea value={form.description} onChange={e => setForm({ ...form, description: e.target.value })} required rows={5}
                      className="w-full text-sm resize-none"
                      style={{ padding: '11px 16px', background: 'var(--bg-sunken)', border: '1px solid transparent', borderRadius: '10px', color: 'var(--text-primary)', outline: 'none' }}
                      placeholder="Describe the role, responsibilities, and requirements…" />
                  </div>
                </div>
                <div className="flex gap-3" style={{ padding: '0 32px 32px' }}>
                  <button type="submit" disabled={posting} className="flex-1 text-white text-sm font-medium flex items-center justify-center gap-2"
                    style={{ padding: '12px', background: 'var(--accent-1)', borderRadius: '10px', opacity: posting ? 0.7 : 1 }}>
                    {posting
                      ? <><svg className="animate-spin w-4 h-4" fill="none" viewBox="0 0 24 24"><circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" /><path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" /></svg>Posting…</>
                      : <><PlusCircle size={15} />Post Job</>}
                  </button>
                  <button type="button" onClick={() => setForm(emptyForm)} className="text-sm font-medium"
                    style={{ padding: '12px 20px', background: 'var(--bg-sunken)', borderRadius: '10px', color: 'var(--text-secondary)' }}>
                    Clear
                  </button>
                </div>
              </form>
            </div>
          )}

          {/* ── MY JOBS ── */}
          {view === 'My Jobs' && (
            <div className="max-w-[1280px]">
              <div className="flex items-center justify-between mb-6">
                <div>
                  <h2 className="font-semibold mb-0.5" style={{ fontSize: '20px', color: 'var(--text-primary)', letterSpacing: '-0.01em' }}>My Jobs</h2>
                  <p className="text-sm" style={{ color: 'var(--text-secondary)' }}>{jobs.length} listing{jobs.length !== 1 ? 's' : ''}</p>
                </div>
                <button onClick={() => setView('Post a Job')} className="flex items-center gap-2 text-white text-sm font-medium"
                  style={{ padding: '9px 18px', background: 'var(--accent-1)', borderRadius: '10px' }}>
                  <PlusCircle size={15} />Post New Job
                </button>
              </div>
              {jobs.length === 0 ? (
                <div style={{ ...card, padding: '64px', textAlign: 'center' }}>
                  <div className="w-12 h-12 rounded-2xl flex items-center justify-center mx-auto mb-4" style={{ background: 'var(--bg-sunken)' }}>
                    <Briefcase size={20} style={{ color: 'var(--text-tertiary)' }} />
                  </div>
                  <p className="font-medium mb-4" style={{ color: 'var(--text-primary)' }}>No jobs posted yet</p>
                  <button onClick={() => setView('Post a Job')} className="text-white text-sm font-medium"
                    style={{ padding: '9px 20px', background: 'var(--accent-1)', borderRadius: '10px' }}>Post a Job</button>
                </div>
              ) : (
                <div className="space-y-3">
                  {jobs.map(job => (
                    <div key={job.id} style={{ ...card, padding: '24px' }}>
                      <div className="flex items-start justify-between gap-6">
                        <div className="flex-1 min-w-0">
                          <div className="flex items-center gap-2.5 mb-1 flex-wrap">
                            <h3 className="font-semibold" style={{ color: 'var(--text-primary)', fontSize: '15px' }}>{job.title}</h3>
                            <JobStatusBadge status={job.status} />
                            <span className="text-xs font-medium px-2.5 py-0.5 rounded-md"
                              style={{ background: 'var(--bg-sunken)', color: 'var(--text-secondary)' }}>{job.type}</span>
                          </div>
                          <p className="text-sm flex items-center gap-1.5 mb-3" style={{ color: 'var(--text-secondary)' }}>
                            <MapPin size={12} />{job.company} · {job.location}
                          </p>
                          {job.skills && (
                            <div className="flex flex-wrap gap-1.5 mb-3">
                              {job.skills.split(',').map(s => (
                                <span key={s} className="text-xs font-medium px-2.5 py-0.5 rounded-md"
                                  style={{ background: 'var(--bg-sunken)', color: 'var(--text-secondary)' }}>{s.trim()}</span>
                              ))}
                            </div>
                          )}
                          <div className="flex flex-wrap gap-4 text-xs" style={{ color: 'var(--text-tertiary)' }}>
                            <span className="flex items-center gap-1"><Calendar size={11} />{new Date(job.postedAt).toLocaleDateString()}</span>
                            {job.deadline && <span className="flex items-center gap-1"><Clock size={11} />Deadline: {new Date(job.deadline).toLocaleDateString()}</span>}
                            {job.salary && <span className="flex items-center gap-1"><DollarSign size={11} />{job.salary}</span>}
                          </div>
                        </div>
                        <div className="text-center shrink-0 rounded-2xl px-6 py-4" style={{ background: 'var(--bg-sunken)' }}>
                          <p className="font-bold" style={{ fontSize: '28px', color: 'var(--text-primary)', letterSpacing: '-0.02em' }}>{job.applications}</p>
                          <p className="text-xs font-medium mt-0.5" style={{ color: 'var(--text-secondary)' }}>Applicants</p>
                        </div>
                      </div>
                      {job.description && (
                        <p className="text-sm mt-4 pt-4 line-clamp-2" style={{ color: 'var(--text-secondary)', borderTop: '1px solid var(--border-subtle)' }}>{job.description}</p>
                      )}
                      <div className="flex gap-2 mt-4 pt-4" style={{ borderTop: '1px solid var(--border-subtle)' }}>
                        <button onClick={() => toggleStatus(job.id)} className="flex items-center gap-1.5 text-sm font-medium"
                          style={{ padding: '7px 14px', borderRadius: '8px', background: 'var(--bg-sunken)', color: 'var(--text-secondary)' }}>
                          <RefreshCw size={13} />{job.status === 'Active' ? 'Close Listing' : 'Reopen'}
                        </button>
                        <button onClick={() => deleteJob(job.id)} className="flex items-center gap-1.5 text-sm font-medium"
                          style={{ padding: '7px 14px', borderRadius: '8px', background: '#FEF2F2', color: 'var(--accent-danger)' }}>
                          <Trash2 size={13} />Delete
                        </button>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}

          {/* ── APPLICANTS ── */}
          {view === 'Applicants' && (
            <div className="max-w-2xl">
              <div className="mb-8">
                <h2 className="font-semibold mb-1" style={{ fontSize: '20px', color: 'var(--text-primary)', letterSpacing: '-0.01em' }}>Applicants</h2>
                <p className="text-sm" style={{ color: 'var(--text-secondary)' }}>Candidates matched to your listings via AI.</p>
              </div>
              <div style={{ ...card, padding: '64px', textAlign: 'center' }}>
                <div className="w-14 h-14 rounded-2xl flex items-center justify-center mx-auto mb-5"
                  style={{ background: 'var(--accent-1-soft)' }}>
                  <Users size={24} style={{ color: 'var(--accent-1)' }} />
                </div>
                <p className="font-semibold mb-2" style={{ color: 'var(--text-primary)', fontSize: '16px' }}>Coming in Phase 2</p>
                <p className="text-sm max-w-xs mx-auto" style={{ color: 'var(--text-secondary)', lineHeight: '1.6' }}>
                  WhatsApp-matched candidates will appear here with full profiles, skill scores, and CV details.
                </p>
                <div className="grid grid-cols-3 gap-3 mt-8">
                  {['Profile View', 'Skills Match', 'WhatsApp Contact'].map(f => (
                    <div key={f} className="rounded-xl p-4" style={{ background: 'var(--bg-sunken)' }}>
                      <p className="text-xs font-medium" style={{ color: 'var(--text-secondary)' }}>{f}</p>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          )}

        </main>
      </div>
    </div>
  );
}

function JobStatusBadge({ status }: { status: 'Active' | 'Closed' }) {
  return (
    <span className="text-xs font-medium px-2.5 py-0.5 rounded-md"
      style={status === 'Active'
        ? { background: '#F0FDF4', color: '#15803D' }
        : { background: 'var(--bg-sunken)', color: 'var(--text-secondary)' }}>
      {status}
    </span>
  );
}

function FormField({ label, value, onChange, placeholder, type = 'text', required, icon }: {
  label: string; value: string; onChange: (v: string) => void;
  placeholder?: string; type?: string; required?: boolean; icon?: React.ReactNode;
}) {
  return (
    <div>
      <label className="block text-sm font-medium mb-1.5" style={{ color: 'var(--text-primary)' }}>{label}</label>
      <div className="relative">
        {icon && <div className="absolute left-3 top-1/2 -translate-y-1/2" style={{ color: 'var(--text-tertiary)' }}>{icon}</div>}
        <input type={type} value={value} onChange={e => onChange(e.target.value)} required={required} placeholder={placeholder}
          className="w-full text-sm"
          style={{ padding: '11px 16px', paddingLeft: icon ? '36px' : '16px', background: 'var(--bg-sunken)', border: '1px solid transparent', borderRadius: '10px', color: 'var(--text-primary)', outline: 'none' }}
          onFocus={e => { e.target.style.borderColor = 'var(--accent-1)'; e.target.style.boxShadow = '0 0 0 3px rgba(37,99,235,0.12)'; }}
          onBlur={e => { e.target.style.borderColor = 'transparent'; e.target.style.boxShadow = 'none'; }} />
      </div>
    </div>
  );
}

function EmptyChart({ icon, text }: { icon: React.ReactNode; text: string }) {
  return (
    <div className="h-40 flex flex-col items-center justify-center" style={{ color: 'var(--text-tertiary)' }}>
      <div className="mb-2 opacity-40">{icon}</div>
      <p className="text-sm">{text}</p>
    </div>
  );
}
