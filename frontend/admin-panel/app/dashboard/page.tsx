'use client';

import '@/app/lib/amplify';
import { useEffect, useState } from 'react';
import { getCurrentUser, signOut } from 'aws-amplify/auth';
import { useRouter } from 'next/navigation';
import {
  LayoutDashboard, Building2, Briefcase, Users, LogOut,
  CheckCircle, XCircle, Clock, ChevronRight, ChevronsLeft,
  ChevronsRight, ShieldCheck, AlertCircle,
} from 'lucide-react';

// ── Types ────────────────────────────────────────────────────────────

type CompanyStatus = 'PENDING' | 'APPROVED' | 'REJECTED' | 'SUSPENDED';
type Company = {
  id: string; name: string; email: string; industry: string;
  registeredAt: string; status: CompanyStatus;
};
type Job = {
  id: string; title: string; company: string; location: string;
  type: string; postedAt: string; status: 'Active' | 'Closed';
};
type User = {
  phone: string; name: string; location: string;
  experience: string; skills: string[]; optIn: boolean; joinedAt: string;
};

// ── Stub data ────────────────────────────────────────────────────────

const STUB_COMPANIES: Company[] = [
  { id: 'c1', name: 'TechCorp Lanka',     email: 'hr@techcorp.lk',    industry: 'Software',    registeredAt: '2026-06-15', status: 'PENDING'  },
  { id: 'c2', name: 'MediHealth Pvt Ltd', email: 'jobs@medihealth.lk', industry: 'Healthcare',  registeredAt: '2026-06-14', status: 'PENDING'  },
  { id: 'c3', name: 'BuildRight Ltd',     email: 'hr@buildright.lk',  industry: 'Engineering', registeredAt: '2026-06-10', status: 'APPROVED' },
  { id: 'c4', name: 'EduFirst Academy',   email: 'jobs@edufirst.lk',  industry: 'Education',   registeredAt: '2026-06-08', status: 'APPROVED' },
];

const STUB_JOBS: Job[] = [
  { id: 'j1', title: 'Senior Python Developer',  company: 'TechCorp Lanka',     location: 'Colombo',  type: 'Full-time',  postedAt: '2026-06-17', status: 'Active' },
  { id: 'j2', title: 'Registered Nurse',         company: 'MediHealth Pvt Ltd', location: 'Kandy',    type: 'Full-time',  postedAt: '2026-06-16', status: 'Active' },
  { id: 'j3', title: 'Civil Engineer',           company: 'BuildRight Ltd',     location: 'Galle',    type: 'Contract',   postedAt: '2026-06-12', status: 'Active' },
  { id: 'j4', title: 'Primary School Teacher',   company: 'EduFirst Academy',   location: 'Colombo',  type: 'Full-time',  postedAt: '2026-06-09', status: 'Closed' },
];

const STUB_USERS: User[] = [
  { phone: '94771234567', name: 'Kasun Perera',  location: 'Colombo', experience: 'mid',    skills: ['Python', 'React'],       optIn: true,  joinedAt: '2026-06-16' },
  { phone: '94779876543', name: 'Nimali Silva',  location: 'Kandy',   experience: 'junior', skills: ['Nursing', 'First Aid'],  optIn: true,  joinedAt: '2026-06-15' },
  { phone: '94772345678', name: 'Ashan Fernando',location: 'Galle',   experience: 'senior', skills: ['Civil Eng', 'AutoCAD'], optIn: false, joinedAt: '2026-06-13' },
];

// ── Component ─────────────────────────────────────────────────────────

export default function AdminDashboard() {
  const router  = useRouter();
  const [adminEmail, setAdminEmail] = useState('');
  const [view, setView]             = useState('Overview');
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const [companies, setCompanies]   = useState<Company[]>(STUB_COMPANIES);

  useEffect(() => {
    getCurrentUser()
      .then((u) => setAdminEmail(u.username))
      .catch(() => router.push('/login'));
  }, [router]);

  const pending  = companies.filter((c) => c.status === 'PENDING');
  const approved = companies.filter((c) => c.status === 'APPROVED');

  const approve = (id: string) =>
    setCompanies((prev) => prev.map((c) => c.id === id ? { ...c, status: 'APPROVED' } : c));
  const reject  = (id: string) =>
    setCompanies((prev) => prev.map((c) => c.id === id ? { ...c, status: 'REJECTED' } : c));

  const navItems = [
    { name: 'Overview',          icon: <LayoutDashboard size={18} /> },
    { name: 'Company Approvals', icon: <Building2 size={18} />,       badge: pending.length },
    { name: 'Job Listings',      icon: <Briefcase size={18} />        },
    { name: 'User Management',   icon: <Users size={18} />            },
  ];

  return (
    <div className="flex h-screen bg-slate-100 overflow-hidden">

      {/* ── Sidebar ── */}
      <aside className={`${sidebarOpen ? 'w-60' : 'w-16'} bg-slate-950 flex flex-col transition-all duration-300 shrink-0`}>
        <div className="p-4 flex items-center gap-3 border-b border-slate-800 overflow-hidden">
          <div className="w-9 h-9 bg-indigo-600 rounded-xl flex items-center justify-center shrink-0">
            <ShieldCheck size={18} className="text-white" />
          </div>
          {sidebarOpen && <span className="text-white font-bold text-base whitespace-nowrap">QJ Admin</span>}
        </div>

        {sidebarOpen && (
          <div className="px-4 py-2.5 border-b border-slate-800">
            <p className="text-slate-500 text-xs font-semibold uppercase tracking-widest">Admin Portal</p>
          </div>
        )}

        <nav className="flex-1 p-3 space-y-1">
          {navItems.map((item) => (
            <button key={item.name} onClick={() => setView(item.name)}
              className={`w-full flex items-center gap-3 px-3 py-2.5 rounded-xl text-sm font-medium transition-all ${
                view === item.name
                  ? 'bg-indigo-600 text-white shadow-md'
                  : 'text-slate-400 hover:bg-slate-800 hover:text-white'
              }`}>
              <span className="shrink-0">{item.icon}</span>
              {sidebarOpen && <span className="whitespace-nowrap flex-1 text-left">{item.name}</span>}
              {sidebarOpen && item.badge ? (
                <span className="bg-red-500 text-white text-xs px-2 py-0.5 rounded-full">{item.badge}</span>
              ) : null}
            </button>
          ))}
        </nav>

        <div className="p-3 border-t border-slate-800 space-y-1">
          {sidebarOpen && (
            <div className="px-3 py-2 mb-1">
              <p className="text-white text-xs font-semibold truncate">{adminEmail}</p>
              <p className="text-slate-500 text-xs">Administrator</p>
            </div>
          )}
          <button onClick={() => setSidebarOpen(!sidebarOpen)}
            className="w-full flex items-center gap-3 px-3 py-2 rounded-xl text-slate-500 hover:bg-slate-800 hover:text-white text-sm transition-all">
            {sidebarOpen ? <ChevronsLeft size={18} /> : <ChevronsRight size={18} />}
            {sidebarOpen && <span>Collapse</span>}
          </button>
          <button onClick={async () => { await signOut(); router.push('/login'); }}
            className="w-full flex items-center gap-3 px-3 py-2 rounded-xl text-red-500 hover:bg-red-950 text-sm transition-all">
            <LogOut size={18} className="shrink-0" />
            {sidebarOpen && <span>Sign Out</span>}
          </button>
        </div>
      </aside>

      {/* ── Main ── */}
      <div className="flex-1 flex flex-col overflow-hidden">

        {/* Header */}
        <header className="bg-white border-b border-gray-200 px-6 py-3.5 flex items-center gap-2 shadow-sm">
          <h1 className="text-base font-semibold text-gray-800">{view}</h1>
          <ChevronRight size={14} className="text-gray-400" />
          {pending.length > 0 && (
            <span className="ml-auto flex items-center gap-1.5 bg-amber-50 border border-amber-200 text-amber-700 text-xs font-medium px-3 py-1.5 rounded-xl">
              <AlertCircle size={13} />
              {pending.length} company approval{pending.length !== 1 ? 's' : ''} pending
            </span>
          )}
        </header>

        {/* Content */}
        <main className="flex-1 overflow-y-auto p-6">

          {/* ── OVERVIEW ── */}
          {view === 'Overview' && (
            <div className="space-y-6">
              <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
                {[
                  { label: 'Pending Approvals', value: pending.length,    color: 'text-amber-600',  bg: 'bg-amber-50',  icon: <Clock size={20} />       },
                  { label: 'Approved Companies', value: approved.length,   color: 'text-green-600',  bg: 'bg-green-50',  icon: <Building2 size={20} />   },
                  { label: 'Active Jobs',         value: STUB_JOBS.filter(j => j.status === 'Active').length, color: 'text-blue-600', bg: 'bg-blue-50', icon: <Briefcase size={20} /> },
                  { label: 'Registered Users',    value: STUB_USERS.length, color: 'text-indigo-600', bg: 'bg-indigo-50', icon: <Users size={20} />       },
                ].map((s) => (
                  <div key={s.label} className="bg-white rounded-2xl p-5 shadow-sm border border-gray-100">
                    <div className="flex items-center justify-between mb-3">
                      <p className="text-xs text-gray-500 font-medium uppercase tracking-wide">{s.label}</p>
                      <div className={`w-9 h-9 ${s.bg} ${s.color} rounded-xl flex items-center justify-center`}>{s.icon}</div>
                    </div>
                    <p className="text-4xl font-bold text-gray-800">{s.value}</p>
                  </div>
                ))}
              </div>

              {/* Pending companies quick view */}
              {pending.length > 0 && (
                <div className="bg-white rounded-2xl shadow-sm border border-gray-100 p-6">
                  <div className="flex items-center justify-between mb-4">
                    <h3 className="font-semibold text-gray-800">Pending Company Approvals</h3>
                    <button onClick={() => setView('Company Approvals')} className="text-sm text-indigo-600 hover:text-indigo-700 font-medium flex items-center gap-1">
                      View all <ChevronRight size={14} />
                    </button>
                  </div>
                  <div className="space-y-3">
                    {pending.slice(0, 3).map((c) => (
                      <PendingRow key={c.id} company={c} onApprove={approve} onReject={reject} />
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}

          {/* ── COMPANY APPROVALS ── */}
          {view === 'Company Approvals' && (
            <div className="space-y-4">
              {pending.length === 0 ? (
                <div className="bg-white rounded-2xl shadow-sm border border-gray-100 p-14 text-center">
                  <CheckCircle size={36} className="text-green-400 mx-auto mb-3" />
                  <p className="text-gray-600 font-medium">All companies reviewed</p>
                  <p className="text-gray-400 text-sm">No pending approvals at this time.</p>
                </div>
              ) : (
                pending.map((c) => (
                  <div key={c.id} className="bg-white rounded-2xl shadow-sm border border-gray-100 p-5">
                    <div className="flex items-start justify-between gap-4">
                      <div>
                        <div className="flex items-center gap-2 mb-1">
                          <h3 className="font-bold text-gray-800">{c.name}</h3>
                          <StatusBadge status={c.status} />
                        </div>
                        <p className="text-sm text-gray-500">{c.email}</p>
                        <p className="text-xs text-gray-400 mt-1">Industry: {c.industry} · Registered: {c.registeredAt}</p>
                      </div>
                      <div className="flex gap-2 shrink-0">
                        <button onClick={() => approve(c.id)}
                          className="flex items-center gap-1.5 text-sm px-4 py-2 rounded-xl font-medium bg-green-100 text-green-700 hover:bg-green-200 transition-colors">
                          <CheckCircle size={14} /> Approve
                        </button>
                        <button onClick={() => reject(c.id)}
                          className="flex items-center gap-1.5 text-sm px-4 py-2 rounded-xl font-medium bg-red-100 text-red-600 hover:bg-red-200 transition-colors">
                          <XCircle size={14} /> Reject
                        </button>
                      </div>
                    </div>
                  </div>
                ))
              )}

              {/* Reviewed companies */}
              {companies.filter(c => c.status !== 'PENDING').length > 0 && (
                <div>
                  <p className="text-xs text-gray-400 uppercase tracking-widest font-semibold mb-3 px-1">Reviewed</p>
                  {companies.filter(c => c.status !== 'PENDING').map((c) => (
                    <div key={c.id} className="bg-white rounded-2xl shadow-sm border border-gray-100 p-5 mb-3 flex items-center justify-between">
                      <div>
                        <p className="font-semibold text-gray-800">{c.name}</p>
                        <p className="text-sm text-gray-500">{c.email} · {c.industry}</p>
                      </div>
                      <StatusBadge status={c.status} />
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}

          {/* ── JOB LISTINGS ── */}
          {view === 'Job Listings' && (
            <div className="space-y-3">
              {STUB_JOBS.map((job) => (
                <div key={job.id} className="bg-white rounded-2xl shadow-sm border border-gray-100 p-5 flex items-center justify-between gap-4">
                  <div>
                    <div className="flex items-center gap-2 mb-0.5">
                      <p className="font-semibold text-gray-800">{job.title}</p>
                      <span className={`text-xs px-2.5 py-0.5 rounded-full font-medium ${job.status === 'Active' ? 'bg-green-100 text-green-700' : 'bg-gray-100 text-gray-500'}`}>
                        {job.status}
                      </span>
                    </div>
                    <p className="text-sm text-gray-500">{job.company} · {job.location} · {job.type}</p>
                    <p className="text-xs text-gray-400 mt-0.5">Posted {job.postedAt}</p>
                  </div>
                  <span className="text-xs bg-blue-50 text-blue-600 px-3 py-1.5 rounded-xl font-medium shrink-0">{job.type}</span>
                </div>
              ))}
            </div>
          )}

          {/* ── USER MANAGEMENT ── */}
          {view === 'User Management' && (
            <div className="space-y-3">
              {STUB_USERS.map((user) => (
                <div key={user.phone} className="bg-white rounded-2xl shadow-sm border border-gray-100 p-5">
                  <div className="flex items-start justify-between gap-4">
                    <div>
                      <div className="flex items-center gap-2 mb-1">
                        <p className="font-semibold text-gray-800">{user.name}</p>
                        <span className={`text-xs px-2.5 py-0.5 rounded-full font-medium ${user.optIn ? 'bg-green-100 text-green-700' : 'bg-gray-100 text-gray-500'}`}>
                          {user.optIn ? 'Opted In' : 'Opted Out'}
                        </span>
                      </div>
                      <p className="text-sm text-gray-500">{user.phone} · {user.location} · {user.experience}</p>
                      <div className="flex flex-wrap gap-1.5 mt-2">
                        {user.skills.map((s) => (
                          <span key={s} className="bg-slate-100 text-slate-600 text-xs px-2.5 py-0.5 rounded-full">{s}</span>
                        ))}
                      </div>
                    </div>
                    <p className="text-xs text-gray-400 shrink-0">Joined {user.joinedAt}</p>
                  </div>
                </div>
              ))}
            </div>
          )}

        </main>
      </div>
    </div>
  );
}

// ── Sub-components ────────────────────────────────────────────────────

function StatusBadge({ status }: { status: CompanyStatus }) {
  const map: Record<CompanyStatus, string> = {
    PENDING:   'bg-amber-100 text-amber-700',
    APPROVED:  'bg-green-100 text-green-700',
    REJECTED:  'bg-red-100 text-red-600',
    SUSPENDED: 'bg-gray-100 text-gray-500',
  };
  return (
    <span className={`text-xs px-2.5 py-0.5 rounded-full font-medium ${map[status]}`}>{status}</span>
  );
}

function PendingRow({ company, onApprove, onReject }: {
  company: Company;
  onApprove: (id: string) => void;
  onReject: (id: string) => void;
}) {
  return (
    <div className="flex items-center justify-between gap-4 py-3 border-b border-gray-100 last:border-0">
      <div>
        <p className="font-medium text-gray-800 text-sm">{company.name}</p>
        <p className="text-xs text-gray-400">{company.industry} · {company.registeredAt}</p>
      </div>
      <div className="flex gap-2 shrink-0">
        <button onClick={() => onApprove(company.id)}
          className="text-xs px-3 py-1.5 rounded-lg bg-green-100 text-green-700 hover:bg-green-200 font-medium transition-colors">
          Approve
        </button>
        <button onClick={() => onReject(company.id)}
          className="text-xs px-3 py-1.5 rounded-lg bg-red-100 text-red-600 hover:bg-red-200 font-medium transition-colors">
          Reject
        </button>
      </div>
    </div>
  );
}
