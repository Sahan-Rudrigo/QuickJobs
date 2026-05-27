'use client';

import '@/lib/amplify';
import { useEffect, useState } from 'react';
import { getCurrentUser, signOut, fetchUserAttributes } from 'aws-amplify/auth';
import { useRouter } from 'next/navigation';
import {
  LayoutDashboard, PlusCircle, Briefcase, Users, LogOut,
  ChevronsLeft, ChevronsRight, Bell, Search, TrendingUp,
  MapPin, Clock, DollarSign, Calendar, Trash2, RefreshCw, ChevronRight,
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

const PIE_COLORS = ['#3b82f6', '#94a3b8'];
const BAR_COLORS: Record<string, string> = {
  'Full-time': '#3b82f6', 'Part-time': '#8b5cf6',
  'Contract': '#f59e0b', 'Remote': '#10b981', 'Internship': '#ec4899',
};

export default function DashboardPage() {
  const router = useRouter();
  const [userEmail, setUserEmail] = useState('');
  const [companyName, setCompanyName] = useState('');
  const [view, setView] = useState('Overview');
  const [jobs, setJobs] = useState<Job[]>([]);
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const [form, setForm] = useState(emptyForm);
  const [posting, setPosting] = useState(false);
  const [postSuccess, setPostSuccess] = useState(false);

  useEffect(() => {
    getCurrentUser()
      .then(async (u) => {
        setUserEmail(u.username);
        const attrs = await fetchUserAttributes();
        setCompanyName(attrs.name || u.username.split('@')[0]);
      })
      .catch(() => router.push('/login'));
    const saved = localStorage.getItem('quickjobs_posted_jobs');
    if (saved) setJobs(JSON.parse(saved));
  }, [router]);

  const saveJobs = (updated: Job[]) => {
    setJobs(updated);
    localStorage.setItem('quickjobs_posted_jobs', JSON.stringify(updated));
  };

  const handlePost = async (e: React.FormEvent) => {
    e.preventDefault();
    setPosting(true);
    await new Promise((r) => setTimeout(r, 800));
    saveJobs([{ id: Date.now().toString(), ...form, postedAt: new Date().toISOString(), applications: 0, status: 'Active' }, ...jobs]);
    setForm(emptyForm);
    setPosting(false);
    setPostSuccess(true);
    setTimeout(() => { setPostSuccess(false); setView('My Jobs'); }, 1500);
  };

  const toggleStatus = (id: string) =>
    saveJobs(jobs.map((j) => j.id === id ? { ...j, status: j.status === 'Active' ? 'Closed' : 'Active' } : j));
  const deleteJob = (id: string) => saveJobs(jobs.filter((j) => j.id !== id));

  const activeJobs = jobs.filter((j) => j.status === 'Active').length;
  const totalApps = jobs.reduce((s, j) => s + j.applications, 0);

  const jobsByType = ['Full-time', 'Part-time', 'Contract', 'Remote', 'Internship']
    .map((t) => ({ name: t, Jobs: jobs.filter((j) => j.type === t).length }))
    .filter((d) => d.Jobs > 0);

  const pieData = [
    { name: 'Active', value: activeJobs },
    { name: 'Closed', value: jobs.length - activeJobs },
  ].filter((d) => d.value > 0);

  const navItems = [
    { name: 'Overview',    icon: <LayoutDashboard size={18} /> },
    { name: 'Post a Job',  icon: <PlusCircle size={18} />      },
    { name: 'My Jobs',     icon: <Briefcase size={18} />       },
    { name: 'Applicants',  icon: <Users size={18} />           },
  ];

  return (
    <div className="flex h-screen bg-slate-100 overflow-hidden">

      {/* ── Sidebar ── */}
      <aside className={`${sidebarOpen ? 'w-60' : 'w-16'} bg-gradient-to-b from-slate-900 to-blue-950 flex flex-col transition-all duration-300 flex-shrink-0`}>
        <div className="p-4 flex items-center gap-3 overflow-hidden border-b border-white/10">
          <div className="w-9 h-9 bg-blue-500 rounded-xl flex items-center justify-center flex-shrink-0 shadow-lg">
            <span className="text-white font-black text-sm">Q</span>
          </div>
          {sidebarOpen && <span className="text-white font-bold text-lg whitespace-nowrap tracking-tight">QuickJobs</span>}
        </div>

        {sidebarOpen && (
          <div className="px-4 py-3 border-b border-white/10">
            <p className="text-white/40 text-xs font-semibold uppercase tracking-widest">Employer Portal</p>
          </div>
        )}

        <nav className="flex-1 p-3 space-y-1">
          {navItems.map((item) => (
            <button key={item.name} onClick={() => setView(item.name)}
              className={`w-full flex items-center gap-3 px-3 py-2.5 rounded-xl text-sm font-medium transition-all ${
                view === item.name
                  ? 'bg-white text-blue-700 shadow-md'
                  : 'text-white/60 hover:bg-white/10 hover:text-white'
              }`}>
              <span className="flex-shrink-0">{item.icon}</span>
              {sidebarOpen && <span className="whitespace-nowrap">{item.name}</span>}
              {sidebarOpen && item.name === 'My Jobs' && jobs.length > 0 && (
                <span className="ml-auto bg-blue-500 text-white text-xs px-2 py-0.5 rounded-full">{jobs.length}</span>
              )}
            </button>
          ))}
        </nav>

        <div className="p-3 border-t border-white/10 space-y-1">
          {sidebarOpen && companyName && (
            <div className="flex items-center gap-2 px-3 py-2 mb-1">
              <div className="w-7 h-7 bg-blue-500 rounded-lg flex items-center justify-center flex-shrink-0">
                <span className="text-white font-bold text-xs">{companyName[0]?.toUpperCase()}</span>
              </div>
              <div className="flex-1 min-w-0">
                <p className="text-white text-xs font-semibold truncate">{companyName}</p>
                <p className="text-white/40 text-xs truncate">{userEmail}</p>
              </div>
            </div>
          )}
          <button onClick={() => setSidebarOpen(!sidebarOpen)}
            className="w-full flex items-center gap-3 px-3 py-2 rounded-xl text-white/50 hover:bg-white/10 hover:text-white text-sm transition-all">
            {sidebarOpen ? <ChevronsLeft size={18} /> : <ChevronsRight size={18} />}
            {sidebarOpen && <span>Collapse</span>}
          </button>
        </div>
      </aside>

      {/* ── Main ── */}
      <div className="flex-1 flex flex-col overflow-hidden">

        {/* Header */}
        <header className="bg-white border-b border-gray-200 px-6 py-3.5 flex items-center gap-4 flex-shrink-0 shadow-sm">

          {/* Left: page title */}
          <div className="flex items-center gap-2 flex-shrink-0">
            <h1 className="text-base font-semibold text-gray-800">{view}</h1>
            <ChevronRight size={14} className="text-gray-400" />
          </div>

          {/* Centre: scrolling ticker */}
          <div className="flex-1 overflow-hidden rounded-xl bg-gradient-to-r from-blue-50 to-indigo-50 border border-blue-100 py-1.5 px-3 hidden lg:block">
            <div className="flex animate-marquee whitespace-nowrap">
              {[0, 1].map((i) => (
                <span key={i} className="text-xs text-blue-700 font-medium inline-flex items-center gap-2.5 pr-10">
                  <span className="font-bold text-blue-800">{companyName || 'QuickJobs'}</span>
                  <span className="text-blue-300 font-bold">▸</span>
                  <span>{jobs.length} Job{jobs.length !== 1 ? 's' : ''} Posted</span>
                  <span className="text-blue-300 font-bold">▸</span>
                  <span>{activeJobs} Active Listing{activeJobs !== 1 ? 's' : ''}</span>
                  <span className="text-blue-300 font-bold">▸</span>
                  <span>{totalApps} Application{totalApps !== 1 ? 's' : ''} Received</span>
                  <span className="text-blue-300 font-bold">▸</span>
                  <span className="text-indigo-600 font-semibold">QuickJobs Employer Portal</span>
                  <span className="text-blue-300 font-bold">▸</span>
                </span>
              ))}
            </div>
          </div>

          {/* Right: actions */}
          <div className="flex items-center gap-3 flex-shrink-0">
            <div className="hidden md:flex items-center gap-2 bg-gray-100 rounded-xl px-3 py-2">
              <Search size={14} className="text-gray-400" />
              <input className="bg-transparent text-sm text-gray-600 outline-none placeholder:text-gray-400 w-28" placeholder="Search..." />
            </div>
            <button className="relative p-2 rounded-xl hover:bg-gray-100 transition-colors">
              <Bell size={18} className="text-gray-500" />
              <span className="absolute top-1.5 right-1.5 w-2 h-2 bg-blue-500 rounded-full" />
            </button>
            <div className="flex items-center gap-2 pl-2 border-l border-gray-200">
              <div className="w-8 h-8 bg-gradient-to-br from-blue-500 to-blue-700 rounded-full flex items-center justify-center shadow-sm flex-shrink-0">
                <span className="text-white font-bold text-xs">{(companyName || userEmail)[0]?.toUpperCase()}</span>
              </div>
              <div className="hidden sm:flex flex-col leading-tight">
                <span className="text-sm text-gray-800 font-semibold max-w-[120px] truncate">{companyName || '—'}</span>
                <span className="text-xs text-gray-400 max-w-[120px] truncate">{userEmail}</span>
              </div>
            </div>
            <button onClick={async () => { await signOut(); router.push('/login'); }}
              className="flex items-center gap-1.5 text-sm text-red-500 hover:text-red-700 px-3 py-1.5 rounded-xl hover:bg-red-50 transition-colors">
              <LogOut size={15} />
              <span className="hidden sm:block">Sign Out</span>
            </button>
          </div>
        </header>

        {/* Content */}
        <main className="flex-1 overflow-y-auto p-6">

          {/* ── OVERVIEW ── */}
          {view === 'Overview' && (
            <div className="space-y-6">

              {/* Welcome banner */}
              <div className="bg-gradient-to-r from-blue-600 to-indigo-700 rounded-2xl p-6 flex items-center justify-between shadow-lg">
                <div>
                  <h2 className="text-white text-xl font-bold mb-1">
                    Welcome back, {companyName || userEmail.split('@')[0]} 👋
                  </h2>
                  <p className="text-blue-100 text-sm">
                    {jobs.length === 0
                      ? "Post your first job listing to start finding candidates."
                      : `You have ${activeJobs} active listing${activeJobs !== 1 ? 's' : ''} and ${totalApps} application${totalApps !== 1 ? 's' : ''} so far.`}
                  </p>
                </div>
                <button onClick={() => setView('Post a Job')}
                  className="hidden md:flex items-center gap-2 bg-white text-blue-700 px-5 py-2.5 rounded-xl font-semibold text-sm hover:bg-blue-50 transition-colors shadow-md flex-shrink-0">
                  <PlusCircle size={16} />
                  Post a Job
                </button>
              </div>

              {/* Stat cards */}
              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
                {[
                  { label: 'Total Jobs Posted',   value: jobs.length, icon: <Briefcase size={20} />,   from: 'from-blue-500',   to: 'to-blue-600',   light: 'bg-blue-50 text-blue-600'   },
                  { label: 'Active Listings',      value: activeJobs,  icon: <TrendingUp size={20} />,  from: 'from-green-500',  to: 'to-green-600',  light: 'bg-green-50 text-green-600'  },
                  { label: 'Total Applications',   value: totalApps,   icon: <Users size={20} />,       from: 'from-purple-500', to: 'to-purple-600', light: 'bg-purple-50 text-purple-600' },
                  { label: 'WhatsApp Matches',     value: totalApps,   icon: <Bell size={20} />,        from: 'from-orange-400', to: 'to-orange-500', light: 'bg-orange-50 text-orange-500' },
                ].map((s, i) => (
                  <div key={s.label} className="bg-white rounded-2xl p-5 shadow-sm border border-gray-100 overflow-hidden relative animate-slide-card"
                    style={{ animationDelay: `${i * 0.08}s`, opacity: 0 }}>
                    <div className={`absolute top-0 left-0 right-0 h-1 bg-gradient-to-r ${s.from} ${s.to}`} />
                    <div className="flex items-center justify-between mb-4">
                      <p className="text-xs text-gray-500 font-medium uppercase tracking-wide">{s.label}</p>
                      <div className={`w-9 h-9 ${s.light} rounded-xl flex items-center justify-center`}>{s.icon}</div>
                    </div>
                    <p className="text-4xl font-bold text-gray-800">{s.value}</p>
                  </div>
                ))}
              </div>

              {/* Charts */}
              <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
                {/* Bar chart */}
                <div className="bg-white rounded-2xl p-6 shadow-sm border border-gray-100">
                  <h3 className="font-semibold text-gray-800 mb-1">Jobs by Type</h3>
                  <p className="text-xs text-gray-400 mb-5">Distribution of your posted job listings</p>
                  {jobsByType.length === 0 ? (
                    <div className="h-40 flex flex-col items-center justify-center text-gray-400">
                      <Briefcase size={32} className="mb-2 opacity-30" />
                      <p className="text-sm">Post jobs to see analytics</p>
                    </div>
                  ) : (
                    <ResponsiveContainer width="100%" height={180}>
                      <BarChart data={jobsByType}>
                        <XAxis dataKey="name" tick={{ fontSize: 11 }} />
                        <YAxis allowDecimals={false} tick={{ fontSize: 11 }} />
                        <Tooltip />
                        <Bar dataKey="Jobs" radius={[6, 6, 0, 0]}>
                          {jobsByType.map((entry, i) => (
                            <Cell key={i} fill={BAR_COLORS[entry.name] || '#3b82f6'} />
                          ))}
                        </Bar>
                      </BarChart>
                    </ResponsiveContainer>
                  )}
                </div>

                {/* Pie chart */}
                <div className="bg-white rounded-2xl p-6 shadow-sm border border-gray-100">
                  <h3 className="font-semibold text-gray-800 mb-1">Listing Status</h3>
                  <p className="text-xs text-gray-400 mb-5">Active vs closed job listings</p>
                  {pieData.length === 0 ? (
                    <div className="h-40 flex flex-col items-center justify-center text-gray-400">
                      <TrendingUp size={32} className="mb-2 opacity-30" />
                      <p className="text-sm">No listings yet</p>
                    </div>
                  ) : (
                    <ResponsiveContainer width="100%" height={180}>
                      <PieChart>
                        <Pie data={pieData} cx="50%" cy="50%" innerRadius={50} outerRadius={75}
                          paddingAngle={4} dataKey="value">
                          {pieData.map((_, i) => <Cell key={i} fill={PIE_COLORS[i]} />)}
                        </Pie>
                        <Legend />
                        <Tooltip />
                      </PieChart>
                    </ResponsiveContainer>
                  )}
                </div>
              </div>

              {/* Recent jobs */}
              <div className="bg-white rounded-2xl shadow-sm border border-gray-100 p-6">
                <div className="flex items-center justify-between mb-5">
                  <h3 className="font-semibold text-gray-800">Recent Listings</h3>
                  <button onClick={() => setView('My Jobs')} className="text-sm text-blue-600 hover:text-blue-700 font-medium flex items-center gap-1">
                    View all <ChevronRight size={14} />
                  </button>
                </div>
                {jobs.length === 0 ? (
                  <div className="text-center py-12">
                    <div className="w-14 h-14 bg-blue-50 rounded-2xl flex items-center justify-center mx-auto mb-3">
                      <Briefcase size={24} className="text-blue-400" />
                    </div>
                    <p className="text-gray-600 font-medium mb-1">No jobs posted yet</p>
                    <p className="text-gray-400 text-sm mb-4">Post your first listing to get started</p>
                    <button onClick={() => setView('Post a Job')} className="bg-blue-600 text-white px-5 py-2 rounded-xl text-sm font-medium hover:bg-blue-700">Post a Job</button>
                  </div>
                ) : (
                  <div className="divide-y divide-gray-100">
                    {jobs.slice(0, 4).map((job) => (
                      <div key={job.id} className="flex items-center gap-4 py-3.5 hover:bg-gray-50 rounded-xl px-2 -mx-2 transition-colors">
                        <div className="w-10 h-10 bg-blue-100 rounded-xl flex items-center justify-center flex-shrink-0">
                          <Briefcase size={16} className="text-blue-600" />
                        </div>
                        <div className="flex-1 min-w-0">
                          <p className="font-medium text-gray-800 text-sm truncate">{job.title}</p>
                          <p className="text-xs text-gray-500">{job.company} · {job.location}</p>
                        </div>
                        <div className="flex items-center gap-3 flex-shrink-0">
                          <span className="text-sm font-medium text-gray-700">{job.applications} applicants</span>
                          <span className={`text-xs px-2.5 py-1 rounded-full font-medium ${job.status === 'Active' ? 'bg-green-100 text-green-700' : 'bg-gray-100 text-gray-500'}`}>
                            {job.status}
                          </span>
                        </div>
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
              <p className="text-gray-500 text-sm mb-6">Fill in the details to create a new job listing.</p>
              {postSuccess && (
                <div className="bg-green-50 border border-green-200 rounded-2xl p-4 mb-6 flex items-center gap-3">
                  <div className="w-8 h-8 bg-green-100 rounded-xl flex items-center justify-center flex-shrink-0">
                    <svg className="w-4 h-4 text-green-600" fill="currentColor" viewBox="0 0 20 20">
                      <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
                    </svg>
                  </div>
                  <p className="text-green-700 font-medium text-sm">Job posted! Redirecting to My Jobs...</p>
                </div>
              )}
              <form onSubmit={handlePost} className="bg-white rounded-2xl shadow-sm border border-gray-100 overflow-hidden">
                <div className="bg-gradient-to-r from-blue-600 to-indigo-700 px-6 py-4">
                  <h3 className="text-white font-semibold">New Job Listing</h3>
                  <p className="text-blue-200 text-xs mt-0.5">Fill all required fields marked with *</p>
                </div>
                <div className="p-6 grid grid-cols-1 sm:grid-cols-2 gap-5">
                  <div className="sm:col-span-2">
                    <label className="block text-sm font-semibold text-gray-700 mb-1.5">Job Title *</label>
                    <input value={form.title} onChange={(e) => setForm({ ...form, title: e.target.value })} required
                      className="w-full border-2 border-gray-200 rounded-xl px-4 py-2.5 text-gray-900 text-sm focus:outline-none focus:border-blue-500 transition-colors placeholder:text-gray-400"
                      placeholder="e.g. Senior Software Engineer" />
                  </div>
                  <div>
                    <label className="block text-sm font-semibold text-gray-700 mb-1.5">Company Name *</label>
                    <input value={form.company} onChange={(e) => setForm({ ...form, company: e.target.value })} required
                      className="w-full border-2 border-gray-200 rounded-xl px-4 py-2.5 text-gray-900 text-sm focus:outline-none focus:border-blue-500 transition-colors placeholder:text-gray-400"
                      placeholder="e.g. ABC Technologies" />
                  </div>
                  <div>
                    <label className="block text-sm font-semibold text-gray-700 mb-1.5">Location *</label>
                    <div className="relative">
                      <MapPin size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
                      <input value={form.location} onChange={(e) => setForm({ ...form, location: e.target.value })} required
                        className="w-full border-2 border-gray-200 rounded-xl pl-9 pr-4 py-2.5 text-gray-900 text-sm focus:outline-none focus:border-blue-500 transition-colors placeholder:text-gray-400"
                        placeholder="e.g. Colombo, Sri Lanka" />
                    </div>
                  </div>
                  <div>
                    <label className="block text-sm font-semibold text-gray-700 mb-1.5">Job Type *</label>
                    <div className="relative">
                      <Clock size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
                      <select value={form.type} onChange={(e) => setForm({ ...form, type: e.target.value })}
                        className="w-full border-2 border-gray-200 rounded-xl pl-9 pr-4 py-2.5 text-gray-900 text-sm focus:outline-none focus:border-blue-500 bg-white transition-colors">
                        {['Full-time', 'Part-time', 'Contract', 'Remote', 'Internship'].map((t) => <option key={t}>{t}</option>)}
                      </select>
                    </div>
                  </div>
                  <div>
                    <label className="block text-sm font-semibold text-gray-700 mb-1.5">Salary Range</label>
                    <div className="relative">
                      <DollarSign size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
                      <input value={form.salary} onChange={(e) => setForm({ ...form, salary: e.target.value })}
                        className="w-full border-2 border-gray-200 rounded-xl pl-9 pr-4 py-2.5 text-gray-900 text-sm focus:outline-none focus:border-blue-500 transition-colors placeholder:text-gray-400"
                        placeholder="e.g. LKR 80,000 - 120,000" />
                    </div>
                  </div>
                  <div>
                    <label className="block text-sm font-semibold text-gray-700 mb-1.5">Deadline</label>
                    <div className="relative">
                      <Calendar size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
                      <input type="date" value={form.deadline} onChange={(e) => setForm({ ...form, deadline: e.target.value })}
                        className="w-full border-2 border-gray-200 rounded-xl pl-9 pr-4 py-2.5 text-gray-900 text-sm focus:outline-none focus:border-blue-500 transition-colors" />
                    </div>
                  </div>
                  <div className="sm:col-span-2">
                    <label className="block text-sm font-semibold text-gray-700 mb-1.5">Required Skills</label>
                    <input value={form.skills} onChange={(e) => setForm({ ...form, skills: e.target.value })}
                      className="w-full border-2 border-gray-200 rounded-xl px-4 py-2.5 text-gray-900 text-sm focus:outline-none focus:border-blue-500 transition-colors placeholder:text-gray-400"
                      placeholder="e.g. Python, React, SQL (comma separated)" />
                  </div>
                  <div className="sm:col-span-2">
                    <label className="block text-sm font-semibold text-gray-700 mb-1.5">Job Description *</label>
                    <textarea value={form.description} onChange={(e) => setForm({ ...form, description: e.target.value })} required rows={5}
                      className="w-full border-2 border-gray-200 rounded-xl px-4 py-2.5 text-gray-900 text-sm focus:outline-none focus:border-blue-500 resize-none transition-colors placeholder:text-gray-400"
                      placeholder="Describe the role, responsibilities, requirements and benefits..." />
                  </div>
                </div>
                <div className="px-6 pb-6 flex gap-3">
                  <button type="submit" disabled={posting}
                    className="flex-1 bg-blue-600 text-white py-3 rounded-xl font-semibold hover:bg-blue-700 transition-all disabled:opacity-50 flex items-center justify-center gap-2 shadow-md">
                    {posting ? (
                      <><svg className="animate-spin w-4 h-4" fill="none" viewBox="0 0 24 24"><circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" /><path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" /></svg>Posting...</>
                    ) : <><PlusCircle size={16} /> Post Job</>}
                  </button>
                  <button type="button" onClick={() => setForm(emptyForm)}
                    className="px-5 bg-gray-100 text-gray-600 py-3 rounded-xl font-medium hover:bg-gray-200 transition-colors">
                    Clear
                  </button>
                </div>
              </form>
            </div>
          )}

          {/* ── MY JOBS ── */}
          {view === 'My Jobs' && (
            <div>
              <div className="flex items-center justify-between mb-6">
                <p className="text-gray-500 text-sm">{jobs.length} job{jobs.length !== 1 ? 's' : ''} posted</p>
                <button onClick={() => setView('Post a Job')}
                  className="bg-blue-600 text-white px-4 py-2 rounded-xl text-sm font-semibold hover:bg-blue-700 flex items-center gap-2 shadow-sm">
                  <PlusCircle size={15} /> Post New Job
                </button>
              </div>
              {jobs.length === 0 ? (
                <div className="bg-white rounded-2xl shadow-sm border border-gray-100 p-14 text-center">
                  <div className="w-14 h-14 bg-blue-50 rounded-2xl flex items-center justify-center mx-auto mb-3">
                    <Briefcase size={24} className="text-blue-400" />
                  </div>
                  <p className="text-gray-600 font-medium mb-4">No jobs posted yet</p>
                  <button onClick={() => setView('Post a Job')} className="bg-blue-600 text-white px-6 py-2.5 rounded-xl text-sm font-semibold hover:bg-blue-700">Post a Job</button>
                </div>
              ) : (
                <div className="space-y-4">
                  {jobs.map((job) => (
                    <div key={job.id} className="bg-white rounded-2xl shadow-sm border border-gray-100 overflow-hidden">
                      <div className={`h-1 ${job.status === 'Active' ? 'bg-gradient-to-r from-green-400 to-green-500' : 'bg-gray-300'}`} />
                      <div className="p-5">
                        <div className="flex items-start justify-between gap-4">
                          <div className="flex-1 min-w-0">
                            <div className="flex items-center gap-2.5 mb-1 flex-wrap">
                              <h3 className="font-bold text-gray-800">{job.title}</h3>
                              <span className={`text-xs px-2.5 py-0.5 rounded-full font-semibold ${job.status === 'Active' ? 'bg-green-100 text-green-700' : 'bg-gray-100 text-gray-500'}`}>
                                {job.status}
                              </span>
                              <span className="text-xs px-2.5 py-0.5 rounded-full font-medium bg-blue-50 text-blue-700">{job.type}</span>
                            </div>
                            <p className="text-sm text-gray-500 mb-3 flex items-center gap-1.5">
                              <MapPin size={12} /> {job.company} · {job.location}
                            </p>
                            {job.skills && (
                              <div className="flex flex-wrap gap-1.5 mb-3">
                                {job.skills.split(',').map((s) => (
                                  <span key={s} className="bg-slate-100 text-slate-600 text-xs px-2.5 py-0.5 rounded-full">{s.trim()}</span>
                                ))}
                              </div>
                            )}
                            <div className="flex flex-wrap gap-4 text-xs text-gray-400">
                              <span className="flex items-center gap-1"><Calendar size={11} /> {new Date(job.postedAt).toLocaleDateString()}</span>
                              {job.deadline && <span className="flex items-center gap-1"><Clock size={11} /> Deadline: {new Date(job.deadline).toLocaleDateString()}</span>}
                              {job.salary && <span className="flex items-center gap-1"><DollarSign size={11} /> {job.salary}</span>}
                            </div>
                          </div>
                          <div className="text-center flex-shrink-0 bg-blue-50 rounded-2xl px-5 py-3">
                            <p className="text-3xl font-bold text-blue-700">{job.applications}</p>
                            <p className="text-xs text-blue-500 font-medium mt-0.5">Applicants</p>
                          </div>
                        </div>
                        {job.description && (
                          <p className="text-sm text-gray-500 mt-3 pt-3 border-t border-gray-100 line-clamp-2">{job.description}</p>
                        )}
                        <div className="flex gap-2 mt-4 pt-3 border-t border-gray-100">
                          <button onClick={() => toggleStatus(job.id)}
                            className={`flex items-center gap-1.5 text-sm px-4 py-1.5 rounded-xl font-medium transition-colors ${job.status === 'Active' ? 'bg-gray-100 text-gray-700 hover:bg-gray-200' : 'bg-green-100 text-green-700 hover:bg-green-200'}`}>
                            <RefreshCw size={13} />
                            {job.status === 'Active' ? 'Close Listing' : 'Reopen Listing'}
                          </button>
                          <button onClick={() => deleteJob(job.id)}
                            className="flex items-center gap-1.5 text-sm px-4 py-1.5 rounded-xl font-medium text-red-600 bg-red-50 hover:bg-red-100 transition-colors">
                            <Trash2 size={13} /> Delete
                          </button>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}

          {/* ── APPLICANTS ── */}
          {view === 'Applicants' && (
            <div className="bg-white rounded-2xl shadow-sm border border-gray-100 overflow-hidden">
              <div className="bg-gradient-to-r from-blue-600 to-indigo-700 px-6 py-8 text-center">
                <div className="w-16 h-16 bg-white/20 rounded-2xl flex items-center justify-center mx-auto mb-3">
                  <Users size={28} className="text-white" />
                </div>
                <h3 className="text-white font-bold text-lg mb-1">Applicants — Coming in Phase 2</h3>
                <p className="text-blue-200 text-sm max-w-sm mx-auto">
                  When the AI matching service is connected, WhatsApp-matched candidates will appear here with full profiles and CV details.
                </p>
              </div>
              <div className="p-8 grid grid-cols-3 gap-4 text-center">
                {['Profile View', 'Skills Match', 'WhatsApp Contact'].map((f) => (
                  <div key={f} className="bg-gray-50 rounded-xl p-4">
                    <p className="text-sm text-gray-500 font-medium">{f}</p>
                    <p className="text-xs text-gray-400 mt-1">Available in Phase 2</p>
                  </div>
                ))}
              </div>
            </div>
          )}

        </main>
      </div>
    </div>
  );
}
