'use client';

import '@/lib/amplify';
import { useState, useEffect } from 'react';
import { signIn, confirmSignIn } from 'aws-amplify/auth';
import { useRouter } from 'next/navigation';

const jobFields = [
  { field: 'Civil Engineering',     icon: '🏗️', desc: 'Build the infrastructure of tomorrow',   gradient: 'from-slate-700 to-slate-600'   },
  { field: 'Healthcare & Medicine', icon: '🏥', desc: 'Caring for communities every day',        gradient: 'from-teal-700 to-teal-600'     },
  { field: 'Education & Teaching',  icon: '📚', desc: 'Shaping the next generation',             gradient: 'from-amber-700 to-amber-600'   },
  { field: 'Software Engineering',  icon: '💻', desc: 'Building digital solutions worldwide',   gradient: 'from-blue-700 to-blue-600'     },
  { field: 'Architecture & Design', icon: '🏛️', desc: 'Designing spaces that inspire people',   gradient: 'from-stone-700 to-stone-600'   },
  { field: 'Legal & Law',           icon: '⚖️', desc: 'Upholding justice and civil rights',     gradient: 'from-yellow-800 to-yellow-700' },
  { field: 'Nursing & Allied Health',icon:'🩺', desc: 'On the frontlines of patient care',      gradient: 'from-rose-700 to-rose-600'     },
  { field: 'Marketing & Branding',  icon: '📣', desc: 'Creating brands that stand out',         gradient: 'from-purple-700 to-purple-600' },
  { field: 'Accounting & Finance',  icon: '💼', desc: 'Managing the numbers that matter',       gradient: 'from-green-800 to-green-700'   },
  { field: 'Hospitality & Tourism', icon: '🏨', desc: 'Creating unforgettable experiences',     gradient: 'from-orange-700 to-orange-600' },
];

const floatingCards = [
  { title: 'Civil Engineer',      icon: '🏗️', delay: '0s',   duration: '9s',  left: '5%'  },
  { title: 'Doctor',              icon: '🩺', delay: '2s',   duration: '12s', left: '52%' },
  { title: 'Teacher',             icon: '📚', delay: '4s',   duration: '10s', left: '26%' },
  { title: 'Chef',                icon: '👨‍🍳', delay: '1s',   duration: '13s', left: '70%' },
  { title: 'Software Engineer',   icon: '💻', delay: '3s',   duration: '8s',  left: '40%' },
  { title: 'Architect',           icon: '🏛️', delay: '5.5s', duration: '11s', left: '15%' },
  { title: 'Accountant',          icon: '💼', delay: '1.5s', duration: '14s', left: '62%' },
  { title: 'Nurse',               icon: '💊', delay: '6s',   duration: '9s',  left: '80%' },
  { title: 'Electrician',         icon: '⚡', delay: '0.5s', duration: '10s', left: '33%' },
  { title: 'Lawyer',              icon: '⚖️', delay: '7s',   duration: '11s', left: '74%' },
  { title: 'Graphic Designer',    icon: '🎨', delay: '2.5s', duration: '12s', left: '88%' },
  { title: 'Marketing Manager',   icon: '📣', delay: '4.5s', duration: '9s',  left: '48%' },
];

export default function LoginPage() {
  const router = useRouter();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const [showPassword, setShowPassword] = useState(false);
  const [newPassword, setNewPassword] = useState('');
  const [companyName, setCompanyName] = useState('');
  const [requiresNewPassword, setRequiresNewPassword] = useState(false);
  const [fieldIndex, setFieldIndex] = useState(0);

  useEffect(() => {
    const interval = setInterval(() => {
      setFieldIndex((prev) => (prev + 1) % jobFields.length);
    }, 5500);
    return () => clearInterval(interval);
  }, []);

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError('');
    try {
      const result = await signIn({ username: email, password });
      if (result.nextStep?.signInStep === 'CONFIRM_SIGN_IN_WITH_NEW_PASSWORD_REQUIRED') {
        setRequiresNewPassword(true);
      } else {
        router.push('/dashboard');
      }
    } catch (err: any) {
      setError(err.message || 'Login failed. Please check your credentials.');
    } finally {
      setLoading(false);
    }
  };

  const handleNewPassword = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError('');
    try {
      await confirmSignIn({
        challengeResponse: newPassword,
        options: { userAttributes: { name: companyName } },
      });
      router.push('/dashboard');
    } catch (err: any) {
      setError(err.message || 'Failed to set new password.');
    } finally {
      setLoading(false);
    }
  };

  const current = jobFields[fieldIndex];

  return (
    <main className="min-h-screen flex">

      {/* ── Left Panel ── */}
      <div className="hidden lg:flex lg:w-1/2 relative gradient-animated flex-col justify-between p-12 overflow-hidden">

        {/* Floating job cards */}
        {floatingCards.map((card, i) => (
          <div key={i} className="absolute bottom-0 animate-float-up pointer-events-none"
            style={{ left: card.left, animationDuration: card.duration, animationDelay: card.delay }}>
            <div className="bg-white/15 backdrop-blur-md border border-white/25 rounded-2xl px-4 py-2.5 flex items-center gap-2.5 shadow-lg">
              <span className="text-xl">{card.icon}</span>
              <span className="text-white text-xs font-semibold whitespace-nowrap">{card.title}</span>
            </div>
          </div>
        ))}

        {/* Logo */}
        <div className="relative z-10 animate-fade-left">
          <div className="flex items-center gap-3 mb-1">
            <div className="w-11 h-11 bg-white rounded-2xl flex items-center justify-center shadow-xl">
              <span className="text-blue-700 font-black text-xl">Q</span>
            </div>
            <span className="text-white font-bold text-2xl tracking-tight">QuickJobs</span>
          </div>
          <p className="text-blue-200 text-sm ml-14">Employer Portal</p>
        </div>

        {/* Cycling field showcase */}
        <div className="relative z-10 flex flex-col items-center">
          <p className="text-blue-200 text-xs font-semibold uppercase tracking-widest mb-4">Hiring Across All Industries</p>
          <div key={fieldIndex} className="w-full animate-slide-right">
            <div className={`bg-gradient-to-br ${current.gradient} rounded-3xl p-8 text-center shadow-2xl border border-white/10`}>
              <div className="text-6xl mb-4">{current.icon}</div>
              <h3 className="text-white text-xl font-bold mb-2">{current.field}</h3>
              <p className="text-white/70 text-sm">{current.desc}</p>
              <div className="flex justify-center gap-2 mt-5">
                {jobFields.map((_, i) => (
                  <div key={i} className={`h-1.5 rounded-full transition-all duration-300 ${i === fieldIndex ? 'w-6 bg-white' : 'w-1.5 bg-white/30'}`} />
                ))}
              </div>
            </div>
          </div>
        </div>

        {/* Stats */}
        <div className="relative z-10 grid grid-cols-3 gap-3 animate-fade-in-up" style={{ animationDelay: '0.8s', opacity: 0 }}>
          {[
            { value: '10K+', label: 'Job Seekers' },
            { value: '500+', label: 'Companies'   },
            { value: '95%',  label: 'Match Rate'  },
          ].map((stat) => (
            <div key={stat.label} className="bg-white/10 backdrop-blur-sm rounded-2xl p-4 text-center border border-white/15">
              <p className="text-white font-bold text-2xl">{stat.value}</p>
              <p className="text-blue-300 text-xs mt-1">{stat.label}</p>
            </div>
          ))}
        </div>
      </div>

      {/* ── Right Panel ── */}
      <div className="w-full lg:w-1/2 flex items-center justify-center bg-gray-50 p-8">
        <div className="w-full max-w-md">

          <div className="lg:hidden flex items-center gap-2 mb-10 justify-center">
            <div className="w-9 h-9 bg-blue-600 rounded-xl flex items-center justify-center">
              <span className="text-white font-black">Q</span>
            </div>
            <span className="text-blue-700 font-bold text-xl">QuickJobs</span>
          </div>

          <div className="animate-fade-right" style={{ animationDelay: '0.2s', opacity: 0 }}>
            <h1 className="text-3xl font-bold text-gray-900 mb-1">
              {requiresNewPassword ? 'Set New Password' : 'Welcome back'}
            </h1>
            <p className="text-gray-500 mb-8 text-sm">
              {requiresNewPassword
                ? 'Set a permanent password to secure your account.'
                : 'Sign in to your employer account to continue'}
            </p>
          </div>

          {requiresNewPassword ? (
            <form onSubmit={handleNewPassword} className="space-y-5 animate-fade-in-up" style={{ animationDelay: '0.3s', opacity: 0 }}>
              <InputField label="Company Name" value={companyName} onChange={setCompanyName} placeholder="e.g. ABC Technologies" />
              <InputField label="New Password" type="password" value={newPassword} onChange={setNewPassword} placeholder="Minimum 8 characters" minLength={8} />
              {error && <ErrorBox message={error} />}
              <SubmitButton loading={loading} label="Set Password & Continue" />
            </form>
          ) : (
            <form onSubmit={handleLogin} className="space-y-5 animate-fade-in-up" style={{ animationDelay: '0.3s', opacity: 0 }}>
              <InputField label="Email address" type="email" value={email} onChange={setEmail} placeholder="you@company.com" />

              <div>
                <div className="flex justify-between items-center mb-2">
                  <label className="block text-sm font-semibold text-gray-700">Password</label>
                  <button type="button" className="text-xs text-blue-600 hover:text-blue-700 font-medium">Forgot password?</button>
                </div>
                <div className="relative">
                  <input
                    type={showPassword ? 'text' : 'password'}
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    required
                    className="w-full border-2 border-gray-200 rounded-xl px-4 py-3 text-gray-900 text-sm font-medium focus:outline-none focus:border-blue-500 bg-white shadow-sm placeholder:text-gray-400 transition-colors pr-12"
                    placeholder="Enter your password"
                  />
                  <button type="button" onClick={() => setShowPassword(!showPassword)}
                    className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-700 transition-colors">
                    {showPassword ? (
                      <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13.875 18.825A10.05 10.05 0 0112 19c-4.478 0-8.268-2.943-9.543-7a9.97 9.97 0 011.563-3.029m5.858.908a3 3 0 114.243 4.243M9.88 9.88l-3.29-3.29m7.532 7.532l3.29 3.29M3 3l3.59 3.59m0 0A9.953 9.953 0 0112 5c4.478 0 8.268 2.943 9.543 7a10.025 10.025 0 01-4.132 4.411m0 0L21 21" />
                      </svg>
                    ) : (
                      <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" />
                      </svg>
                    )}
                  </button>
                </div>
              </div>

              {error && <ErrorBox message={error} />}
              <SubmitButton loading={loading} label="Sign In" />

              <div className="flex items-center gap-3 my-2">
                <div className="flex-1 h-px bg-gray-200" />
                <span className="text-xs text-gray-400">Secured by AWS Cognito</span>
                <div className="flex-1 h-px bg-gray-200" />
              </div>
            </form>
          )}

          {!requiresNewPassword && (
            <p className="text-center text-xs text-gray-400 mt-4">
              Don&apos;t have an account?{' '}
              <span className="text-blue-600 font-semibold">Contact your administrator</span>
            </p>
          )}
        </div>
      </div>
    </main>
  );
}

function InputField({ label, value, onChange, placeholder, type = 'text', minLength }: {
  label: string; value: string; onChange: (v: string) => void;
  placeholder?: string; type?: string; minLength?: number;
}) {
  return (
    <div>
      <label className="block text-sm font-semibold text-gray-700 mb-2">{label}</label>
      <input type={type} value={value} onChange={(e) => onChange(e.target.value)}
        required minLength={minLength} placeholder={placeholder}
        className="w-full border-2 border-gray-200 rounded-xl px-4 py-3 text-gray-900 text-sm font-medium focus:outline-none focus:border-blue-500 bg-white shadow-sm placeholder:text-gray-400 transition-colors" />
    </div>
  );
}

function SubmitButton({ loading, label }: { loading: boolean; label: string }) {
  return (
    <button type="submit" disabled={loading}
      className="w-full bg-blue-600 text-white py-3 rounded-xl font-semibold hover:bg-blue-700 transition-all disabled:opacity-50 flex items-center justify-center gap-2 shadow-md hover:shadow-lg hover:shadow-blue-200 hover:-translate-y-0.5">
      {loading ? (
        <>
          <svg className="animate-spin w-4 h-4" fill="none" viewBox="0 0 24 24">
            <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
            <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
          </svg>
          Loading...
        </>
      ) : label}
    </button>
  );
}

function ErrorBox({ message }: { message: string }) {
  return (
    <div className="bg-red-50 border border-red-200 rounded-xl p-3 flex items-start gap-2">
      <svg className="w-4 h-4 text-red-500 mt-0.5 flex-shrink-0" fill="currentColor" viewBox="0 0 20 20">
        <path fillRule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7 4a1 1 0 11-2 0 1 1 0 012 0zm-1-9a1 1 0 00-1 1v4a1 1 0 102 0V6a1 1 0 00-1-1z" clipRule="evenodd" />
      </svg>
      <p className="text-red-600 text-sm">{message}</p>
    </div>
  );
}
