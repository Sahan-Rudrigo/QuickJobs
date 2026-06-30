'use client';

import '@/app/lib/amplify';
import { useEffect, useState } from 'react';
import { getCurrentUser, signOut, fetchAuthSession } from 'aws-amplify/auth';
import { useRouter } from 'next/navigation';
import {
  LayoutDashboard, Building2, Briefcase, Users, LogOut,
  CheckCircle, XCircle, Clock, ChevronRight, Menu, X,
  ShieldCheck, AlertCircle, RefreshCw, Search,
} from 'lucide-react';

type CompanyStatus = 'PENDING' | 'APPROVED' | 'REJECTED' | 'SUSPENDED';
type Company = { id: string; name: string; email: string; industry: string; registered_at: string; status: CompanyStatus; };
type Job     = { id: string; title: string; company_name: string; location: string; job_type: string; posted_at: string; status: 'Active' | 'Closed'; };
type User    = { phone: string; name: string; location: string; experience_level: string; skills: string[]; opt_in_status: boolean; created_at: string; };
type Stats   = { total_companies: number; pending_approvals: number; approved_companies: number; total_jobs: number; active_jobs: number; total_matches: number; };

const COMPANY_URL = process.env.NEXT_PUBLIC_COMPANY_SERVICE_URL || 'http://localhost:8003';
const USER_URL    = process.env.NEXT_PUBLIC_USER_SERVICE_URL    || 'http://localhost:8001';

const card: React.CSSProperties = {
  background: 'var(--bg-elevated)',
  border: '1px solid var(--border-subtle)',
  borderRadius: '16px',
  boxShadow: 'var(--shadow-sm)',
};

export default function AdminDashboard() {
  const router = useRouter();
  const [adminEmail, setAdminEmail]   = useState('');
  const [view, setView]               = useState('Overview');
  const [sidebarOpen, setSidebarOpen] = useState(true);

  const [companies, setCompanies] = useState<Company[]>([]);
  const [jobs, setJobs]           = useState<Job[]>([]);
  const [users, setUsers]         = useState<User[]>([]);
  const [stats, setStats]         = useState<Stats | null>(null);
  const [loading, setLoading]     = useState(true);
  const [error, setError]         = useState('');

  const [companySearch, setCompanySearch] = useState('');
  const [jobSearch, setJobSearch]         = useState('');
  const [userSearch, setUserSearch]       = useState('');
  const [companyPage, setCompanyPage]     = useState(1);
  const [jobPage, setJobPage]             = useState(1);
  const [userPage, setUserPage]           = useState(1);
  const PAGE_SIZE = 10;

  useEffect(() => {
    async function init() {
      try {
        // Auth check
        const u = await getCurrentUser();
        setAdminEmail(u.username);

        // Cognito group check
        const session = await fetchAuthSession();
        const groups = (session.tokens?.accessToken?.payload['cognito:groups'] as string[]) || [];
        if (!groups.includes('quickjobs-admins')) {
          router.push('/login');
          return;
        }

        await loadAll();
      } catch {
        router.push('/login');
      }
    }
    init();
  }, [router]);

  async function getAuthHeaders(): Promise<HeadersInit> {
    try {
      const session = await fetchAuthSession();
      const token = session.tokens?.accessToken?.toString();
      if (token) return { Authorization: `Bearer ${token}` };
    } catch {}
    return {};
  }

  async function loadAll() {
    setLoading(true);
    setError('');
    try {
      const headers = await getAuthHeaders();
      const [cRes, jRes, uRes, sRes] = await Promise.all([
        fetch(`${COMPANY_URL}/admin/companies`, { headers }),
        fetch(`${COMPANY_URL}/admin/jobs`,      { headers }),
        fetch(`${USER_URL}/users?limit=100`),
        fetch(`${COMPANY_URL}/admin/stats`,     { headers }),
      ]);
      if (cRes.ok) setCompanies(await cRes.json());
      else setError(`Failed to load companies (${cRes.status}). Check that the company service is running.`);
      if (jRes.ok) setJobs(await jRes.json());
      if (uRes.ok) setUsers(await uRes.json());
      if (sRes.ok) setStats(await sRes.json());
    } catch (e) {
      setError('Could not reach backend services. Make sure they are running.');
    } finally {
      setLoading(false);
    }
  }

  async function activate(id: string) {
    const headers = await getAuthHeaders();
    const res = await fetch(`${COMPANY_URL}/admin/companies/${id}/activate`, { method: 'PATCH', headers });
    if (res.ok) {
      const updated: Company = await res.json();
      setCompanies(prev => prev.map(c => c.id === id ? updated : c));
      setStats(s => s ? { ...s, pending_approvals: Math.max(0, s.pending_approvals - 1), approved_companies: s.approved_companies + 1 } : s);
    }
  }

  async function approve(id: string) {
    const headers = await getAuthHeaders();
    const res = await fetch(`${COMPANY_URL}/admin/companies/${id}/approve`, { method: 'PATCH', headers });
    if (res.ok) {
      const updated: Company = await res.json();
      setCompanies(prev => prev.map(c => c.id === id ? updated : c));
      setStats(s => s ? { ...s, pending_approvals: s.pending_approvals - 1, approved_companies: s.approved_companies + 1 } : s);
    }
  }

  async function reject(id: string) {
    const headers = await getAuthHeaders();
    const res = await fetch(`${COMPANY_URL}/admin/companies/${id}/reject`, { method: 'PATCH', headers });
    if (res.ok) {
      const updated: Company = await res.json();
      setCompanies(prev => prev.map(c => c.id === id ? updated : c));
      setStats(s => s ? { ...s, pending_approvals: Math.max(0, s.pending_approvals - 1) } : s);
    }
  }

  async function suspend(id: string) {
    const headers = await getAuthHeaders();
    const res = await fetch(`${COMPANY_URL}/admin/companies/${id}/suspend`, { method: 'PATCH', headers });
    if (res.ok) {
      const updated: Company = await res.json();
      setCompanies(prev => prev.map(c => c.id === id ? updated : c));
    }
  }

  const pending  = companies.filter(c => c.status === 'PENDING');
  const approved = companies.filter(c => c.status === 'APPROVED');

  const filteredPending = pending.filter(c =>
    !companySearch ||
    c.name.toLowerCase().includes(companySearch.toLowerCase()) ||
    c.email.toLowerCase().includes(companySearch.toLowerCase()) ||
    (c.industry || '').toLowerCase().includes(companySearch.toLowerCase())
  );
  const filteredReviewed = companies.filter(c => c.status !== 'PENDING').filter(c =>
    !companySearch ||
    c.name.toLowerCase().includes(companySearch.toLowerCase()) ||
    c.email.toLowerCase().includes(companySearch.toLowerCase())
  );
  const filteredJobs = jobs.filter(j =>
    !jobSearch ||
    j.title.toLowerCase().includes(jobSearch.toLowerCase()) ||
    j.company_name.toLowerCase().includes(jobSearch.toLowerCase()) ||
    (j.location || '').toLowerCase().includes(jobSearch.toLowerCase())
  );
  const filteredUsers = users.filter(u =>
    !userSearch ||
    (u.name || '').toLowerCase().includes(userSearch.toLowerCase()) ||
    u.phone.includes(userSearch) ||
    (u.location || '').toLowerCase().includes(userSearch.toLowerCase()) ||
    (u.skills || []).some(s => s.toLowerCase().includes(userSearch.toLowerCase()))
  );

  const pendingPages   = Math.max(1, Math.ceil(filteredPending.length / PAGE_SIZE));
  const reviewedPages  = Math.max(1, Math.ceil(filteredReviewed.length / PAGE_SIZE));
  const jobPages       = Math.max(1, Math.ceil(filteredJobs.length / PAGE_SIZE));
  const userPages      = Math.max(1, Math.ceil(filteredUsers.length / PAGE_SIZE));

  const pagedPending   = filteredPending.slice((companyPage - 1) * PAGE_SIZE, companyPage * PAGE_SIZE);
  const pagedReviewed  = filteredReviewed.slice((companyPage - 1) * PAGE_SIZE, companyPage * PAGE_SIZE);
  const pagedJobs      = filteredJobs.slice((jobPage - 1) * PAGE_SIZE, jobPage * PAGE_SIZE);
  const pagedUsers     = filteredUsers.slice((userPage - 1) * PAGE_SIZE, userPage * PAGE_SIZE);

  const navItems = [
    { name: 'Overview',          icon: <LayoutDashboard size={16} />               },
    { name: 'Company Approvals', icon: <Building2 size={16} />, badge: pending.length },
    { name: 'Job Listings',      icon: <Briefcase size={16} />                     },
    { name: 'User Management',   icon: <Users size={16} />                         },
  ];

  return (
    <div className="flex h-screen overflow-hidden" style={{ background: 'var(--bg-base)' }}>

      {/* ── Sidebar ── */}
      <aside className="flex flex-col shrink-0 transition-all duration-200"
        style={{ width: sidebarOpen ? '224px' : '64px', background: 'var(--bg-elevated)', borderRight: '1px solid var(--border-subtle)' }}>

        <div className="flex items-center gap-3 overflow-hidden"
          style={{ padding: '20px 16px', borderBottom: '1px solid var(--border-subtle)', height: '64px' }}>
          <div className="shrink-0 w-8 h-8 rounded-xl flex items-center justify-center" style={{ background: 'var(--accent-1)' }}>
            <ShieldCheck size={15} className="text-white" />
          </div>
          {sidebarOpen && (
            <div>
              <p className="font-semibold text-sm leading-none" style={{ color: 'var(--text-primary)', letterSpacing: '-0.01em' }}>QJ Admin</p>
              <p className="text-xs mt-0.5" style={{ color: 'var(--text-tertiary)' }}>Operations</p>
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
                {sidebarOpen && item.badge ? (
                  <span className="text-xs font-medium px-2 py-0.5 rounded-full text-white" style={{ background: 'var(--accent-danger)' }}>{item.badge}</span>
                ) : null}
              </button>
            );
          })}
        </nav>

        <div className="p-2 space-y-0.5" style={{ borderTop: '1px solid var(--border-subtle)' }}>
          {sidebarOpen && (
            <div className="px-3 py-2.5 mb-1">
              <p className="text-xs font-medium truncate" style={{ color: 'var(--text-primary)' }}>{adminEmail}</p>
              <p className="text-xs" style={{ color: 'var(--text-tertiary)' }}>Administrator</p>
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

        <header className="flex items-center gap-3 shrink-0"
          style={{ height: '64px', padding: '0 24px', background: 'var(--bg-elevated)', borderBottom: '1px solid var(--border-subtle)' }}>
          <h1 className="text-sm font-semibold" style={{ color: 'var(--text-primary)' }}>{view}</h1>
          <ChevronRight size={13} style={{ color: 'var(--text-tertiary)' }} />
          {pending.length > 0 && (
            <div className="ml-auto flex items-center gap-1.5 text-xs font-medium animate-toast"
              style={{ padding: '6px 12px', background: '#FFFBEB', border: '1px solid #FDE68A', borderRadius: '8px', color: '#92400E' }}>
              <AlertCircle size={13} />
              {pending.length} approval{pending.length !== 1 ? 's' : ''} pending
            </div>
          )}
          <button onClick={loadAll}
            className="ml-auto flex items-center gap-1.5 text-xs"
            style={{ color: 'var(--text-tertiary)', padding: '6px 10px', borderRadius: '8px', background: 'var(--bg-sunken)' }}>
            <RefreshCw size={12} className={loading ? 'animate-spin' : ''} />
            {loading ? 'Loading…' : 'Refresh'}
          </button>
        </header>

        <main className="flex-1 overflow-y-auto" style={{ padding: '32px' }}>

          {error && (
            <div className="flex items-center gap-2 mb-6 text-sm"
              style={{ padding: '12px 16px', background: '#FEF2F2', border: '1px solid #FECACA', borderRadius: '10px', color: '#B91C1C' }}>
              <AlertCircle size={15} /> {error}
            </div>
          )}

          {/* ── OVERVIEW ── */}
          {view === 'Overview' && (
            <div className="space-y-6 max-w-[1280px]">
              <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
                {[
                  { label: 'Pending Approvals',  value: stats?.pending_approvals  ?? pending.length,                              accent: 'var(--accent-warn)', soft: '#FFFBEB', icon: <Clock size={18} />       },
                  { label: 'Approved Companies', value: stats?.approved_companies ?? approved.length,                             accent: 'var(--accent-2)',    soft: '#F0FDF4', icon: <Building2 size={18} />   },
                  { label: 'Active Jobs',         value: stats?.active_jobs        ?? jobs.filter(j => j.status === 'Active').length, accent: 'var(--accent-1)', soft: 'var(--accent-1-soft)', icon: <Briefcase size={18} /> },
                  { label: 'Registered Users',    value: stats?.total_matches      ?? users.length,                               accent: '#7C3AED',            soft: '#F5F3FF', icon: <Users size={18} />       },
                ].map((s, i) => (
                  <div key={s.label} className="animate-reveal-up" style={{ ...card, padding: '24px', animationDelay: `${i * 60}ms`, opacity: 0 }}>
                    <div className="flex items-center justify-between mb-4">
                      <p className="text-xs font-medium uppercase tracking-[0.06em]" style={{ color: 'var(--text-secondary)' }}>{s.label}</p>
                      <div className="w-8 h-8 rounded-xl flex items-center justify-center" style={{ background: s.soft, color: s.accent }}>{s.icon}</div>
                    </div>
                    <p className="font-bold" style={{ fontSize: '36px', color: 'var(--text-primary)', letterSpacing: '-0.02em', lineHeight: 1 }}>
                      {loading ? '–' : s.value}
                    </p>
                  </div>
                ))}
              </div>

              {pending.length > 0 && (
                <div style={{ ...card, padding: '32px' }}>
                  <div className="flex items-center justify-between mb-6">
                    <div>
                      <p className="font-semibold" style={{ color: 'var(--text-primary)', fontSize: '15px' }}>Pending Approvals</p>
                      <p className="text-xs mt-0.5" style={{ color: 'var(--text-secondary)' }}>{pending.length} company{pending.length !== 1 ? 'ies' : ''} awaiting review</p>
                    </div>
                    <button onClick={() => setView('Company Approvals')} className="flex items-center gap-1 text-xs font-medium" style={{ color: 'var(--accent-1)' }}>
                      View all <ChevronRight size={13} />
                    </button>
                  </div>
                  <div className="space-y-0" style={{ borderTop: '1px solid var(--border-subtle)' }}>
                    {pending.slice(0, 3).map(c => (
                      <PendingRow key={c.id} company={c} onApprove={approve} onReject={reject} />
                    ))}
                  </div>
                </div>
              )}

              <div style={{ ...card, padding: '32px' }}>
                <div className="flex items-center justify-between mb-6">
                  <p className="font-semibold" style={{ color: 'var(--text-primary)', fontSize: '15px' }}>Recent Job Listings</p>
                  <button onClick={() => setView('Job Listings')} className="flex items-center gap-1 text-xs font-medium" style={{ color: 'var(--accent-1)' }}>
                    View all <ChevronRight size={13} />
                  </button>
                </div>
                <div style={{ borderTop: '1px solid var(--border-subtle)' }}>
                  {jobs.slice(0, 3).map(job => (
                    <div key={job.id} className="flex items-center justify-between py-4" style={{ borderBottom: '1px solid var(--border-subtle)' }}>
                      <div>
                        <p className="text-sm font-medium" style={{ color: 'var(--text-primary)' }}>{job.title}</p>
                        <p className="text-xs mt-0.5" style={{ color: 'var(--text-secondary)' }}>{job.company_name} · {job.location}</p>
                      </div>
                      <StatusBadge status={job.status} />
                    </div>
                  ))}
                  {jobs.length === 0 && !loading && (
                    <p className="text-sm text-center py-8" style={{ color: 'var(--text-tertiary)' }}>No jobs posted yet.</p>
                  )}
                </div>
              </div>
            </div>
          )}

          {/* ── COMPANY APPROVALS ── */}
          {view === 'Company Approvals' && (
            <div className="space-y-4 max-w-[1280px]">
              {/* Search */}
              <div className="flex items-center gap-2 rounded-xl"
                style={{ background: 'var(--bg-elevated)', border: '1px solid var(--border-subtle)', padding: '10px 16px' }}>
                <Search size={14} style={{ color: 'var(--text-tertiary)', flexShrink: 0 }} />
                <input className="flex-1 bg-transparent text-sm outline-none" placeholder="Search by name, email or industry…"
                  style={{ color: 'var(--text-primary)' }}
                  value={companySearch} onChange={e => { setCompanySearch(e.target.value); setCompanyPage(1); }} />
              </div>

              {filteredPending.length === 0 && pending.length === 0 ? (
                <div style={{ ...card, padding: '64px', textAlign: 'center' }}>
                  <div className="w-12 h-12 rounded-2xl flex items-center justify-center mx-auto mb-4" style={{ background: '#F0FDF4' }}>
                    <CheckCircle size={22} style={{ color: '#16A34A' }} />
                  </div>
                  <p className="font-medium mb-1" style={{ color: 'var(--text-primary)' }}>All caught up</p>
                  <p className="text-sm" style={{ color: 'var(--text-secondary)' }}>No pending approvals at this time.</p>
                </div>
              ) : filteredPending.length > 0 ? (
                <div style={{ ...card }}>
                  <div style={{ padding: '24px 32px', borderBottom: '1px solid var(--border-subtle)' }}>
                    <p className="font-semibold" style={{ color: 'var(--text-primary)', fontSize: '15px' }}>Awaiting Review</p>
                    <p className="text-xs mt-0.5" style={{ color: 'var(--text-secondary)' }}>{filteredPending.length} registration{filteredPending.length !== 1 ? 's' : ''}</p>
                  </div>
                  <div style={{ padding: '0 32px' }}>
                    {pagedPending.map(c => (
                      <div key={c.id} className="flex items-center justify-between gap-6 py-5" style={{ borderBottom: '1px solid var(--border-subtle)' }}>
                        <div>
                          <div className="flex items-center gap-2.5 mb-1">
                            <p className="font-medium text-sm" style={{ color: 'var(--text-primary)' }}>{c.name}</p>
                            <CompanyBadge status={c.status} />
                          </div>
                          <p className="text-xs" style={{ color: 'var(--text-secondary)' }}>{c.email} · {c.industry || 'N/A'} · Registered {new Date(c.registered_at).toLocaleDateString()}</p>
                        </div>
                        <div className="flex gap-2 shrink-0">
                          <button onClick={() => activate(c.id)} className="flex items-center gap-1.5 text-xs font-medium transition-all"
                            style={{ padding: '7px 14px', background: '#EFF6FF', borderRadius: '8px', color: '#1D4ED8' }}
                            title="Approve and grant login access via Cognito group">
                            <CheckCircle size={13} />Activate &amp; Approve
                          </button>
                          <button onClick={() => approve(c.id)} className="flex items-center gap-1.5 text-xs font-medium transition-all"
                            style={{ padding: '7px 14px', background: '#F0FDF4', borderRadius: '8px', color: '#15803D' }}
                            title="Approve without Cognito group (for admin-created accounts)">
                            <CheckCircle size={13} />Approve
                          </button>
                          <button onClick={() => reject(c.id)} className="flex items-center gap-1.5 text-xs font-medium transition-all"
                            style={{ padding: '7px 14px', background: '#FEF2F2', borderRadius: '8px', color: 'var(--accent-danger)' }}>
                            <XCircle size={13} />Reject
                          </button>
                        </div>
                      </div>
                    ))}
                  </div>
                  {pendingPages > 1 && (
                    <div style={{ padding: '16px 32px' }}>
                      <Paginator page={companyPage} total={pendingPages} onChange={setCompanyPage} />
                    </div>
                  )}
                </div>
              ) : null}

              {filteredReviewed.length > 0 && (
                <div style={{ ...card }}>
                  <div style={{ padding: '24px 32px', borderBottom: '1px solid var(--border-subtle)' }}>
                    <p className="font-semibold" style={{ color: 'var(--text-primary)', fontSize: '15px' }}>Reviewed</p>
                    <p className="text-xs mt-0.5" style={{ color: 'var(--text-secondary)' }}>{filteredReviewed.length} companies</p>
                  </div>
                  <div style={{ padding: '0 32px' }}>
                    {pagedReviewed.map(c => (
                      <div key={c.id} className="flex items-center justify-between py-4 gap-4" style={{ borderBottom: '1px solid var(--border-subtle)' }}>
                        <div className="flex-1 min-w-0">
                          <p className="text-sm font-medium" style={{ color: 'var(--text-primary)' }}>{c.name}</p>
                          <p className="text-xs mt-0.5" style={{ color: 'var(--text-secondary)' }}>{c.email} · {c.industry || 'N/A'}</p>
                        </div>
                        <div className="flex items-center gap-2 shrink-0">
                          <CompanyBadge status={c.status} />
                          {c.status === 'APPROVED' && (
                            <button onClick={() => suspend(c.id)} className="text-xs font-medium transition-all"
                              style={{ padding: '5px 10px', background: 'var(--bg-sunken)', borderRadius: '6px', color: 'var(--text-secondary)' }}>
                              Suspend
                            </button>
                          )}
                          {c.status === 'SUSPENDED' && (
                            <button onClick={() => approve(c.id)} className="text-xs font-medium transition-all"
                              style={{ padding: '5px 10px', background: '#F0FDF4', borderRadius: '6px', color: '#15803D' }}>
                              Reinstate
                            </button>
                          )}
                        </div>
                      </div>
                    ))}
                  </div>
                  {reviewedPages > 1 && (
                    <div style={{ padding: '16px 32px' }}>
                      <Paginator page={companyPage} total={reviewedPages} onChange={setCompanyPage} />
                    </div>
                  )}
                </div>
              )}
            </div>
          )}

          {/* ── JOB LISTINGS ── */}
          {view === 'Job Listings' && (
            <div className="space-y-3 max-w-[1280px]">
              <div className="flex items-start justify-between mb-2">
                <div>
                  <h2 className="font-semibold mb-1" style={{ fontSize: '20px', color: 'var(--text-primary)', letterSpacing: '-0.01em' }}>Job Listings</h2>
                  <p className="text-sm" style={{ color: 'var(--text-secondary)' }}>{filteredJobs.length} of {jobs.length} listings</p>
                </div>
              </div>
              <div className="flex items-center gap-2 rounded-xl mb-2"
                style={{ background: 'var(--bg-elevated)', border: '1px solid var(--border-subtle)', padding: '10px 16px' }}>
                <Search size={14} style={{ color: 'var(--text-tertiary)', flexShrink: 0 }} />
                <input className="flex-1 bg-transparent text-sm outline-none" placeholder="Search by title, company or location…"
                  style={{ color: 'var(--text-primary)' }}
                  value={jobSearch} onChange={e => { setJobSearch(e.target.value); setJobPage(1); }} />
              </div>
              {filteredJobs.length === 0 && !loading && (
                <div style={{ ...card, padding: '64px', textAlign: 'center' }}>
                  <p className="text-sm" style={{ color: 'var(--text-tertiary)' }}>{jobSearch ? 'No jobs match your search.' : 'No jobs posted yet.'}</p>
                </div>
              )}
              {pagedJobs.map(job => (
                <div key={job.id} className="flex items-center justify-between gap-6" style={{ ...card, padding: '20px 28px' }}>
                  <div>
                    <div className="flex items-center gap-2.5 mb-1">
                      <p className="font-medium text-sm" style={{ color: 'var(--text-primary)' }}>{job.title}</p>
                      <StatusBadge status={job.status} />
                    </div>
                    <p className="text-xs" style={{ color: 'var(--text-secondary)' }}>
                      {job.company_name} · {job.location} · {job.job_type} · Posted {new Date(job.posted_at).toLocaleDateString()}
                    </p>
                  </div>
                  <span className="text-xs font-medium px-3 py-1.5 rounded-lg shrink-0"
                    style={{ background: 'var(--bg-sunken)', color: 'var(--text-secondary)' }}>{job.job_type}</span>
                </div>
              ))}
              {jobPages > 1 && <Paginator page={jobPage} total={jobPages} onChange={setJobPage} />}
            </div>
          )}

          {/* ── USER MANAGEMENT ── */}
          {view === 'User Management' && (
            <div className="space-y-3 max-w-[1280px]">
              <div className="flex items-start justify-between mb-2">
                <div>
                  <h2 className="font-semibold mb-1" style={{ fontSize: '20px', color: 'var(--text-primary)', letterSpacing: '-0.01em' }}>User Management</h2>
                  <p className="text-sm" style={{ color: 'var(--text-secondary)' }}>{filteredUsers.length} of {users.length} registered job seekers</p>
                </div>
              </div>
              <div className="flex items-center gap-2 rounded-xl mb-2"
                style={{ background: 'var(--bg-elevated)', border: '1px solid var(--border-subtle)', padding: '10px 16px' }}>
                <Search size={14} style={{ color: 'var(--text-tertiary)', flexShrink: 0 }} />
                <input className="flex-1 bg-transparent text-sm outline-none" placeholder="Search by name, phone, location or skill…"
                  style={{ color: 'var(--text-primary)' }}
                  value={userSearch} onChange={e => { setUserSearch(e.target.value); setUserPage(1); }} />
              </div>
              {filteredUsers.length === 0 && !loading && (
                <div style={{ ...card, padding: '64px', textAlign: 'center' }}>
                  <p className="text-sm" style={{ color: 'var(--text-tertiary)' }}>{userSearch ? 'No users match your search.' : 'No users registered yet.'}</p>
                </div>
              )}
              {pagedUsers.map(user => (
                <div key={user.phone} style={{ ...card, padding: '24px 28px' }}>
                  <div className="flex items-start justify-between gap-4">
                    <div>
                      <div className="flex items-center gap-2.5 mb-1">
                        <p className="font-medium text-sm" style={{ color: 'var(--text-primary)' }}>{user.name || user.phone}</p>
                        <span className="text-xs font-medium px-2.5 py-0.5 rounded-md"
                          style={user.opt_in_status
                            ? { background: '#F0FDF4', color: '#15803D' }
                            : { background: 'var(--bg-sunken)', color: 'var(--text-tertiary)' }}>
                          {user.opt_in_status ? 'Opted In' : 'Opted Out'}
                        </span>
                      </div>
                      <p className="text-xs mb-3" style={{ color: 'var(--text-secondary)' }}>
                        {user.phone} · {user.location || '–'} · {user.experience_level || '–'}
                      </p>
                      <div className="flex flex-wrap gap-1.5">
                        {(user.skills || []).map(s => (
                          <span key={s} className="text-xs font-medium px-2.5 py-0.5 rounded-md"
                            style={{ background: 'var(--bg-sunken)', color: 'var(--text-secondary)' }}>{s}</span>
                        ))}
                      </div>
                    </div>
                    <p className="text-xs shrink-0" style={{ color: 'var(--text-tertiary)' }}>
                      Joined {user.created_at ? new Date(user.created_at).toLocaleDateString() : '–'}
                    </p>
                  </div>
                </div>
              ))}
              {userPages > 1 && <Paginator page={userPage} total={userPages} onChange={setUserPage} />}
            </div>
          )}

        </main>
      </div>
    </div>
  );
}

// ── Sub-components ────────────────────────────────────────────────────

function Paginator({ page, total, onChange }: { page: number; total: number; onChange: (p: number) => void }) {
  return (
    <div className="flex items-center justify-between pt-2">
      <button disabled={page === 1} onClick={() => onChange(page - 1)}
        className="text-xs font-medium px-3 py-1.5 rounded-lg transition-all"
        style={{ background: page === 1 ? 'transparent' : 'var(--bg-sunken)', color: page === 1 ? 'var(--text-tertiary)' : 'var(--text-secondary)', cursor: page === 1 ? 'default' : 'pointer' }}>
        ← Previous
      </button>
      <span className="text-xs" style={{ color: 'var(--text-tertiary)' }}>Page {page} of {total}</span>
      <button disabled={page === total} onClick={() => onChange(page + 1)}
        className="text-xs font-medium px-3 py-1.5 rounded-lg transition-all"
        style={{ background: page === total ? 'transparent' : 'var(--bg-sunken)', color: page === total ? 'var(--text-tertiary)' : 'var(--text-secondary)', cursor: page === total ? 'default' : 'pointer' }}>
        Next →
      </button>
    </div>
  );
}

function CompanyBadge({ status }: { status: CompanyStatus }) {
  const styles: Record<CompanyStatus, React.CSSProperties> = {
    PENDING:   { background: '#FFFBEB', color: '#92400E' },
    APPROVED:  { background: '#F0FDF4', color: '#15803D' },
    REJECTED:  { background: '#FEF2F2', color: '#B91C1C' },
    SUSPENDED: { background: 'var(--bg-sunken)', color: 'var(--text-tertiary)' },
  };
  return <span className="text-xs font-medium px-2.5 py-0.5 rounded-md" style={styles[status]}>{status}</span>;
}

function StatusBadge({ status }: { status: 'Active' | 'Closed' }) {
  return (
    <span className="text-xs font-medium px-2.5 py-0.5 rounded-md"
      style={status === 'Active' ? { background: '#F0FDF4', color: '#15803D' } : { background: 'var(--bg-sunken)', color: 'var(--text-secondary)' }}>
      {status}
    </span>
  );
}

function PendingRow({ company, onApprove, onReject }: {
  company: Company; onApprove: (id: string) => void; onReject: (id: string) => void;
}) {
  return (
    <div className="flex items-center justify-between gap-4 py-4" style={{ borderBottom: '1px solid var(--border-subtle)' }}>
      <div>
        <p className="text-sm font-medium" style={{ color: 'var(--text-primary)' }}>{company.name}</p>
        <p className="text-xs mt-0.5" style={{ color: 'var(--text-secondary)' }}>{company.industry || 'N/A'} · {new Date(company.registered_at).toLocaleDateString()}</p>
      </div>
      <div className="flex gap-2 shrink-0">
        <button onClick={() => onApprove(company.id)} className="text-xs font-medium transition-all"
          style={{ padding: '6px 12px', background: '#F0FDF4', borderRadius: '8px', color: '#15803D' }}>Approve</button>
        <button onClick={() => onReject(company.id)} className="text-xs font-medium transition-all"
          style={{ padding: '6px 12px', background: '#FEF2F2', borderRadius: '8px', color: 'var(--accent-danger)' }}>Reject</button>
      </div>
    </div>
  );
}
