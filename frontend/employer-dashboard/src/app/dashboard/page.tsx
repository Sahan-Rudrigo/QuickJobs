'use client';

import '@/lib/amplify';
import { useEffect, useState } from 'react';
import { getCurrentUser, signOut, fetchUserAttributes, fetchAuthSession } from 'aws-amplify/auth';
import { useRouter } from 'next/navigation';
import {
  LayoutDashboard, PlusCircle, Briefcase, Users, LogOut,
  Bell, Search, TrendingUp, MapPin, Clock, DollarSign,
  Calendar, Trash2, RefreshCw, ChevronRight, Menu, X,
  AlertCircle, CheckCircle, Download,
} from 'lucide-react';
import {
  BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer,
  PieChart, Pie, Cell, Legend,
} from 'recharts';

const COMPANY_URL  = process.env.NEXT_PUBLIC_COMPANY_SERVICE_URL || 'http://localhost:8003';
const FILE_URL     = process.env.NEXT_PUBLIC_FILE_SERVICE_URL    || 'http://localhost:8002';

type Job = {
  id: string; company_id: string; company_name: string; title: string;
  location: string; job_type: string; salary: string; description: string;
  skills: string[]; deadline: string; posted_at: string;
  applications: number; status: 'Active' | 'Closed';
};

type Candidate = {
  phone: string; name: string | null; skills: string[];
  experience_level: string | null; location: string | null; cv_s3_key: string | null;
};

type Company = { id: string; name: string; email: string; status: string; };

const emptyForm = {
  title: '', location: '', job_type: 'Full-time',
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

  const [userEmail, setUserEmail]       = useState('');
  const [pendingApproval, setPendingApproval] = useState(false);
  const [company, setCompany]           = useState<Company | null>(null);
  const [view, setView]                 = useState('Overview');
  const [jobs, setJobs]                 = useState<Job[]>([]);
  const [sidebarOpen, setSidebarOpen]   = useState(true);
  const [form, setForm]                 = useState(emptyForm);
  const [posting, setPosting]           = useState(false);
  const [postSuccess, setPostSuccess]   = useState(false);
  const [postError, setPostError]       = useState('');
  const [initLoading, setInitLoading]   = useState(true);
  const [jobsLoading, setJobsLoading]   = useState(false);

  const [jobSearch, setJobSearch] = useState('');

  // Applicants tab state
  const [selectedJobId, setSelectedJobId]   = useState('');
  const [candidates, setCandidates]         = useState<Candidate[]>([]);
  const [candidatesLoading, setCandidatesLoading] = useState(false);

  useEffect(() => {
    async function init() {
      // Auth check — redirect to login only if not authenticated or wrong group
      let u, session;
      try {
        u = await getCurrentUser();
        session = await fetchAuthSession();
      } catch {
        router.push('/login');
        return;
      }

      setUserEmail(u.username);

      const groups = (session.tokens?.accessToken?.payload['cognito:groups'] as string[]) || [];
      if (!groups.includes('quickjobs-employers')) {
        setUserEmail(u.username);
        setPendingApproval(true);
        setInitLoading(false);
        return;
      }

      // Company lookup — network errors here should not log the user out
      try {
        const attrs = await fetchUserAttributes();
        const sub         = session.tokens?.accessToken?.payload['sub'] as string || u.username;
        const email       = attrs.email || u.username;
        const companyName = attrs.name || email.split('@')[0];

        let co: Company | null = null;
        const byUser = await fetch(`${COMPANY_URL}/companies/by-user/${sub}`);
        if (byUser.ok) {
          co = await byUser.json();
        } else {
          const created = await fetch(`${COMPANY_URL}/companies`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ name: companyName, email: email, cognito_user_id: sub }),
          });
          if (created.ok) co = await created.json();
        }

        if (co) {
          setCompany(co);
          await loadJobs(co.id);
        }
      } catch {
        // Company service unavailable — still show dashboard, just without company data
      } finally {
        setInitLoading(false);
      }
    }
    init();
  }, [router]);

  async function loadJobs(companyId: string) {
    setJobsLoading(true);
    try {
      const res = await fetch(`${COMPANY_URL}/companies/${companyId}/jobs`);
      if (res.ok) setJobs(await res.json());
    } finally {
      setJobsLoading(false);
    }
  }

  const handlePost = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!company) {
      setPostError('Company profile not loaded. Please refresh the page.');
      return;
    }
    if (company.status !== 'APPROVED') {
      setPostError('Your account is pending admin approval. You can post jobs once approved.');
      return;
    }
    setPosting(true);
    setPostError('');
    try {
      const res = await fetch(`${COMPANY_URL}/companies/${company.id}/jobs`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          title:       form.title,
          location:    form.location,
          job_type:    form.job_type,
          salary:      form.salary,
          description: form.description,
          skills:      form.skills ? form.skills.split(',').map(s => s.trim()).filter(Boolean) : [],
          deadline:    form.deadline || null,
        }),
      });
      if (res.ok) {
        const newJob: Job = await res.json();
        setJobs(prev => [newJob, ...prev]);
        setForm(emptyForm);
        setPostSuccess(true);
        setTimeout(() => { setPostSuccess(false); setView('My Jobs'); }, 1500);
      } else {
        const err = await res.json().catch(() => ({}));
        setPostError(err.detail || `Failed to post job (${res.status}). Please try again.`);
      }
    } catch {
      setPostError('Could not reach the server. Check that the company service is running.');
    } finally {
      setPosting(false);
    }
  };

  const toggleStatus = async (jobId: string) => {
    const res = await fetch(`${COMPANY_URL}/jobs/${jobId}/status`, { method: 'PATCH' });
    if (res.ok) {
      const updated: Job = await res.json();
      setJobs(prev => prev.map(j => j.id === jobId ? updated : j));
    }
  };

  const deleteJob = async (jobId: string) => {
    const res = await fetch(`${COMPANY_URL}/jobs/${jobId}`, { method: 'DELETE' });
    if (res.ok) setJobs(prev => prev.filter(j => j.id !== jobId));
  };

  const loadCandidates = async (jobId: string) => {
    setSelectedJobId(jobId);
    setCandidatesLoading(true);
    setCandidates([]);
    try {
      const res = await fetch(`${COMPANY_URL}/jobs/${jobId}/matches`);
      if (res.ok) {
        const data = await res.json();
        setCandidates(data.candidates || []);
      }
    } finally {
      setCandidatesLoading(false);
    }
  };

  const filteredJobs = jobs.filter(j =>
    !jobSearch ||
    j.title.toLowerCase().includes(jobSearch.toLowerCase()) ||
    (j.location || '').toLowerCase().includes(jobSearch.toLowerCase()) ||
    (j.skills || []).some(s => s.toLowerCase().includes(jobSearch.toLowerCase()))
  );
  const activeJobs  = jobs.filter(j => j.status === 'Active').length;
  const totalApps   = jobs.reduce((s, j) => s + j.applications, 0);
  const jobsByType  = ['Full-time', 'Part-time', 'Contract', 'Remote', 'Internship']
    .map(t => ({ name: t, Jobs: jobs.filter(j => j.job_type === t).length }))
    .filter(d => d.Jobs > 0);
  const pieData = [
    { name: 'Active', value: activeJobs },
    { name: 'Closed', value: jobs.length - activeJobs },
  ].filter(d => d.value > 0);

  const companyName = company?.name || userEmail.split('@')[0];

  const navItems = [
    { name: 'Overview',   icon: <LayoutDashboard size={16} /> },
    { name: 'Post a Job', icon: <PlusCircle size={16} />      },
    { name: 'My Jobs',    icon: <Briefcase size={16} />       },
    { name: 'Applicants', icon: <Users size={16} />           },
  ];

  if (initLoading) {
    return (
      <div className="flex h-screen items-center justify-center" style={{ background: 'var(--bg-base)' }}>
        <div className="text-center">
          <div className="w-8 h-8 mx-auto mb-3 rounded-xl flex items-center justify-center" style={{ background: 'var(--accent-1)' }}>
            <span className="text-white font-bold text-sm">Q</span>
          </div>
          <p className="text-sm" style={{ color: 'var(--text-secondary)' }}>Loading your dashboard…</p>
        </div>
      </div>
    );
  }

  if (pendingApproval) {
    return (
      <div className="flex h-screen items-center justify-center p-6" style={{ background: 'var(--bg-base)' }}>
        <div className="w-full max-w-[440px] text-center">
          <div className="w-16 h-16 rounded-2xl flex items-center justify-center mx-auto mb-6" style={{ background: '#FFFBEB' }}>
            <Clock size={30} style={{ color: '#D97706' }} />
          </div>
          <h1 className="font-semibold mb-2" style={{ fontSize: '22px', color: 'var(--text-primary)', letterSpacing: '-0.01em' }}>
            Pending Admin Approval
          </h1>
          <p className="text-sm mb-2" style={{ color: 'var(--text-secondary)', lineHeight: '1.6' }}>
            Your account (<strong>{userEmail}</strong>) is awaiting approval.
          </p>
          <p className="text-sm mb-8" style={{ color: 'var(--text-tertiary)', lineHeight: '1.6' }}>
            An admin needs to activate your account before you can access the dashboard. You'll be able to log in once approved.
          </p>
          <button
            onClick={async () => { const { signOut } = await import('aws-amplify/auth'); await signOut(); router.push('/login'); }}
            className="text-sm font-medium"
            style={{ padding: '10px 24px', background: 'var(--bg-elevated)', border: '1px solid var(--border-subtle)', borderRadius: '10px', color: 'var(--text-secondary)' }}>
            Sign Out
          </button>
        </div>
      </div>
    );
  }

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
              <div className="w-7 h-7 rounded-full flex items-center justify-center shrink-0" style={{ background: 'var(--accent-1-soft)' }}>
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

        <header className="flex items-center gap-4 shrink-0"
          style={{ height: '64px', padding: '0 24px', background: 'var(--bg-elevated)', borderBottom: '1px solid var(--border-subtle)' }}>
          <div className="flex items-center gap-2">
            <h1 className="text-sm font-semibold" style={{ color: 'var(--text-primary)' }}>{view}</h1>
            <ChevronRight size={13} style={{ color: 'var(--text-tertiary)' }} />
          </div>

          {/* Company status banner */}
          {company && company.status === 'PENDING' && (
            <div className="flex items-center gap-1.5 text-xs font-medium"
              style={{ padding: '5px 10px', background: '#FFFBEB', border: '1px solid #FDE68A', borderRadius: '8px', color: '#92400E' }}>
              <AlertCircle size={12} /> Account pending admin approval
            </div>
          )}
          {company && company.status === 'REJECTED' && (
            <div className="flex items-center gap-1.5 text-xs font-medium"
              style={{ padding: '5px 10px', background: '#FEF2F2', border: '1px solid #FECACA', borderRadius: '8px', color: '#B91C1C' }}>
              <AlertCircle size={12} /> Account rejected — contact admin
            </div>
          )}

          <div className="ml-auto flex items-center gap-2">
            <div className="hidden md:flex items-center gap-2 rounded-xl"
              style={{ background: 'var(--bg-sunken)', padding: '8px 12px' }}>
              <Search size={13} style={{ color: 'var(--text-tertiary)' }} />
              <input className="bg-transparent text-sm outline-none w-24" placeholder="Search jobs…" style={{ color: 'var(--text-primary)' }}
                value={jobSearch} onChange={e => setJobSearch(e.target.value)} />
            </div>
            <button className="relative w-9 h-9 flex items-center justify-center rounded-xl" style={{ color: 'var(--text-secondary)' }}>
              <Bell size={17} />
              {totalApps > 0 && <span className="absolute top-2 right-2 w-1.5 h-1.5 rounded-full" style={{ background: 'var(--accent-1)' }} />}
            </button>
          </div>
        </header>

        <main className="flex-1 overflow-y-auto" style={{ padding: '32px' }}>

          {/* ── OVERVIEW ── */}
          {view === 'Overview' && (
            <div className="space-y-6 max-w-[1280px]">
              <div className="rounded-2xl p-8 flex items-center justify-between"
                style={{ background: 'var(--accent-1)', boxShadow: '0 4px 24px rgba(37,99,235,0.25)' }}>
                <div>
                  <p className="text-blue-200 text-xs font-medium uppercase tracking-[0.08em] mb-2">Welcome back</p>
                  <h2 className="text-white text-xl font-semibold mb-1.5" style={{ letterSpacing: '-0.01em' }}>{companyName}</h2>
                  <p className="text-blue-200 text-sm">
                    {jobs.length === 0
                      ? 'Post your first job listing to start finding candidates.'
                      : `${activeJobs} active listing${activeJobs !== 1 ? 's' : ''} · ${totalApps} match${totalApps !== 1 ? 'es' : ''}`}
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
                  { label: 'Jobs Posted',      value: jobs.length,  icon: <Briefcase size={18} />,  accent: 'var(--accent-1)', soft: 'var(--accent-1-soft)' },
                  { label: 'Active Listings',  value: activeJobs,   icon: <TrendingUp size={18} />, accent: '#16A34A',         soft: '#F0FDF4' },
                  { label: 'WhatsApp Matches', value: totalApps,    icon: <Users size={18} />,      accent: '#7C3AED',         soft: '#F5F3FF' },
                  { label: 'Notifications Sent', value: totalApps,  icon: <Bell size={18} />,       accent: '#D97706',         soft: '#FFFBEB' },
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
                          <p className="text-xs" style={{ color: 'var(--text-secondary)' }}>{job.location} · {job.applications} match{job.applications !== 1 ? 'es' : ''}</p>
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
                <p className="text-sm" style={{ color: 'var(--text-secondary)' }}>Fill in the details. Our AI will automatically match candidates on WhatsApp.</p>
              </div>
              {postSuccess && (
                <div className="flex items-center gap-3 mb-6 animate-toast"
                  style={{ padding: '14px 16px', background: '#F0FDF4', border: '1px solid #BBF7D0', borderRadius: '12px' }}>
                  <CheckCircle size={16} style={{ color: '#16A34A' }} />
                  <p className="text-sm font-medium" style={{ color: '#15803D' }}>Job posted! Matching candidates…</p>
                </div>
              )}
              {postError && (
                <div className="flex items-center gap-3 mb-6"
                  style={{ padding: '14px 16px', background: '#FEF2F2', border: '1px solid #FECACA', borderRadius: '12px' }}>
                  <AlertCircle size={16} style={{ color: '#DC2626' }} />
                  <p className="text-sm font-medium" style={{ color: '#B91C1C' }}>{postError}</p>
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
                  <FormField label="Location *" value={form.location} onChange={v => setForm({ ...form, location: v })} placeholder="e.g. Colombo" required icon={<MapPin size={13} />} />
                  <div>
                    <label className="block text-sm font-medium mb-1.5" style={{ color: 'var(--text-primary)' }}>Job Type *</label>
                    <div className="relative">
                      <Clock size={13} className="absolute left-3 top-1/2 -translate-y-1/2" style={{ color: 'var(--text-tertiary)' }} />
                      <select value={form.job_type} onChange={e => setForm({ ...form, job_type: e.target.value })} className="w-full text-sm"
                        style={{ padding: '11px 16px 11px 36px', background: 'var(--bg-sunken)', border: '1px solid transparent', borderRadius: '10px', color: 'var(--text-primary)', outline: 'none', appearance: 'none' }}>
                        {['Full-time', 'Part-time', 'Contract', 'Remote', 'Internship'].map(t => <option key={t}>{t}</option>)}
                      </select>
                    </div>
                  </div>
                  <FormField label="Salary Range" value={form.salary} onChange={v => setForm({ ...form, salary: v })} placeholder="e.g. LKR 80,000–120,000" icon={<DollarSign size={13} />} />
                  <FormField label="Deadline" type="date" value={form.deadline} onChange={v => setForm({ ...form, deadline: v })} icon={<Calendar size={13} />} />
                  <div style={{ gridColumn: '1 / -1' }}>
                    <FormField label="Required Skills (comma separated)" value={form.skills} onChange={v => setForm({ ...form, skills: v })} placeholder="e.g. Python, React, SQL" />
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
                  <p className="text-sm" style={{ color: 'var(--text-secondary)' }}>
                    {filteredJobs.length}{jobSearch ? ` of ${jobs.length}` : ''} listing{filteredJobs.length !== 1 ? 's' : ''}
                    {jobSearch && <button onClick={() => setJobSearch('')} className="ml-2 text-xs" style={{ color: 'var(--accent-1)' }}>Clear</button>}
                  </p>
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
              ) : filteredJobs.length === 0 ? (
                <div style={{ ...card, padding: '64px', textAlign: 'center' }}>
                  <p className="text-sm" style={{ color: 'var(--text-tertiary)' }}>No jobs match your search.</p>
                </div>
              ) : (
                <div className="space-y-3">
                  {filteredJobs.map(job => (
                    <div key={job.id} style={{ ...card, padding: '24px' }}>
                      <div className="flex items-start justify-between gap-6">
                        <div className="flex-1 min-w-0">
                          <div className="flex items-center gap-2.5 mb-1 flex-wrap">
                            <h3 className="font-semibold" style={{ color: 'var(--text-primary)', fontSize: '15px' }}>{job.title}</h3>
                            <JobStatusBadge status={job.status} />
                            <span className="text-xs font-medium px-2.5 py-0.5 rounded-md"
                              style={{ background: 'var(--bg-sunken)', color: 'var(--text-secondary)' }}>{job.job_type}</span>
                          </div>
                          <p className="text-sm flex items-center gap-1.5 mb-3" style={{ color: 'var(--text-secondary)' }}>
                            <MapPin size={12} />{job.company_name} · {job.location}
                          </p>
                          {job.skills && job.skills.length > 0 && (
                            <div className="flex flex-wrap gap-1.5 mb-3">
                              {job.skills.map(s => (
                                <span key={s} className="text-xs font-medium px-2.5 py-0.5 rounded-md"
                                  style={{ background: 'var(--bg-sunken)', color: 'var(--text-secondary)' }}>{s}</span>
                              ))}
                            </div>
                          )}
                          <div className="flex flex-wrap gap-4 text-xs" style={{ color: 'var(--text-tertiary)' }}>
                            <span className="flex items-center gap-1"><Calendar size={11} />{new Date(job.posted_at).toLocaleDateString()}</span>
                            {job.deadline && <span className="flex items-center gap-1"><Clock size={11} />Deadline: {new Date(job.deadline).toLocaleDateString()}</span>}
                            {job.salary && <span className="flex items-center gap-1"><DollarSign size={11} />{job.salary}</span>}
                          </div>
                        </div>
                        <div className="text-center shrink-0 rounded-2xl px-6 py-4 cursor-pointer"
                          style={{ background: 'var(--bg-sunken)' }}
                          onClick={() => { setView('Applicants'); loadCandidates(job.id); }}>
                          <p className="font-bold" style={{ fontSize: '28px', color: 'var(--text-primary)', letterSpacing: '-0.02em' }}>{job.applications}</p>
                          <p className="text-xs font-medium mt-0.5" style={{ color: 'var(--accent-1)' }}>View Matches</p>
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
            <div className="max-w-[1280px]">
              <div className="mb-6">
                <h2 className="font-semibold mb-1" style={{ fontSize: '20px', color: 'var(--text-primary)', letterSpacing: '-0.01em' }}>Matched Candidates</h2>
                <p className="text-sm" style={{ color: 'var(--text-secondary)' }}>AI-matched job seekers notified via WhatsApp</p>
              </div>

              {/* Job selector */}
              {jobs.length > 0 && (
                <div className="mb-6" style={{ ...card, padding: '20px 24px' }}>
                  <label className="block text-xs font-medium mb-2" style={{ color: 'var(--text-secondary)' }}>Select a job to view its matches</label>
                  <select
                    value={selectedJobId}
                    onChange={e => loadCandidates(e.target.value)}
                    className="w-full text-sm"
                    style={{ padding: '10px 14px', background: 'var(--bg-sunken)', border: '1px solid transparent', borderRadius: '10px', color: 'var(--text-primary)', outline: 'none' }}>
                    <option value="">— Choose a job —</option>
                    {jobs.map(j => (
                      <option key={j.id} value={j.id}>{j.title} ({j.applications} match{j.applications !== 1 ? 'es' : ''})</option>
                    ))}
                  </select>
                </div>
              )}

              {candidatesLoading && (
                <div className="text-center py-12" style={{ color: 'var(--text-tertiary)', fontSize: '14px' }}>
                  Loading candidates…
                </div>
              )}

              {!candidatesLoading && selectedJobId && candidates.length === 0 && (
                <div style={{ ...card, padding: '64px', textAlign: 'center' }}>
                  <div className="w-12 h-12 rounded-2xl flex items-center justify-center mx-auto mb-4" style={{ background: 'var(--bg-sunken)' }}>
                    <Users size={20} style={{ color: 'var(--text-tertiary)' }} />
                  </div>
                  <p className="font-medium mb-1" style={{ color: 'var(--text-primary)' }}>No matches yet</p>
                  <p className="text-sm" style={{ color: 'var(--text-secondary)' }}>Candidates are matched when the job is posted. Try updating the skills or description.</p>
                </div>
              )}

              {!candidatesLoading && !selectedJobId && jobs.length === 0 && (
                <div style={{ ...card, padding: '64px', textAlign: 'center' }}>
                  <div className="w-12 h-12 rounded-2xl flex items-center justify-center mx-auto mb-4" style={{ background: 'var(--accent-1-soft)' }}>
                    <Users size={24} style={{ color: 'var(--accent-1)' }} />
                  </div>
                  <p className="font-semibold mb-2" style={{ color: 'var(--text-primary)', fontSize: '16px' }}>No jobs posted yet</p>
                  <p className="text-sm max-w-xs mx-auto" style={{ color: 'var(--text-secondary)', lineHeight: '1.6' }}>
                    Post a job to see AI-matched candidates with their profiles and CV details.
                  </p>
                </div>
              )}

              {!candidatesLoading && candidates.length > 0 && (
                <div className="space-y-3">
                  {candidates.map(c => (
                    <div key={c.phone} style={{ ...card, padding: '24px 28px' }}>
                      <div className="flex items-start justify-between gap-4">
                        <div className="flex-1">
                          <div className="flex items-center gap-2.5 mb-1">
                            <div className="w-8 h-8 rounded-full flex items-center justify-center shrink-0"
                              style={{ background: 'var(--accent-1-soft)' }}>
                              <span className="text-xs font-semibold" style={{ color: 'var(--accent-1)' }}>
                                {(c.name || c.phone)[0]?.toUpperCase()}
                              </span>
                            </div>
                            <div>
                              <p className="font-medium text-sm" style={{ color: 'var(--text-primary)' }}>{c.name || c.phone}</p>
                              {c.name && <p className="text-xs" style={{ color: 'var(--text-tertiary)' }}>{c.phone}</p>}
                            </div>
                          </div>
                          <p className="text-xs mt-2 mb-3" style={{ color: 'var(--text-secondary)' }}>
                            {[c.experience_level, c.location].filter(Boolean).join(' · ')}
                          </p>
                          {c.skills && c.skills.length > 0 && (
                            <div className="flex flex-wrap gap-1.5">
                              {c.skills.map(s => (
                                <span key={s} className="text-xs font-medium px-2.5 py-0.5 rounded-md"
                                  style={{ background: 'var(--bg-sunken)', color: 'var(--text-secondary)' }}>{s}</span>
                              ))}
                            </div>
                          )}
                        </div>
                        <div className="flex items-center gap-2 shrink-0">
                          <span className="text-xs font-medium px-2.5 py-1 rounded-lg"
                            style={{ background: '#F0FDF4', color: '#15803D' }}>Matched</span>
                          {c.cv_s3_key && (
                            <button
                              onClick={async () => {
                                const res = await fetch(`${FILE_URL}/cv/${c.phone}/latest/download`);
                                if (res.ok) {
                                  const data = await res.json();
                                  window.open(data.download_url, '_blank');
                                }
                              }}
                              className="flex items-center gap-1 text-xs font-medium"
                              style={{ padding: '6px 10px', background: 'var(--bg-sunken)', borderRadius: '8px', color: 'var(--text-secondary)' }}>
                              <Download size={12} />CV
                            </button>
                          )}
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              )}
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
