'use client';

import '@/lib/amplify';
import { useState, useEffect } from 'react';
import { signIn, confirmSignIn, resetPassword, confirmResetPassword } from 'aws-amplify/auth';
import { useRouter } from 'next/navigation';
import { Eye, EyeOff, AlertCircle } from 'lucide-react';

const jobFields = [
  { field: 'Software Engineering',    icon: '💻', desc: 'Building digital solutions worldwide',  gradient: 'from-blue-600 to-blue-500'     },
  { field: 'Civil Engineering',       icon: '🏗️', desc: 'Build the infrastructure of tomorrow',  gradient: 'from-slate-600 to-slate-500'   },
  { field: 'Healthcare & Medicine',   icon: '🏥', desc: 'Caring for communities every day',       gradient: 'from-teal-600 to-teal-500'     },
  { field: 'Education & Teaching',    icon: '📚', desc: 'Shaping the next generation',            gradient: 'from-amber-600 to-amber-500'   },
  { field: 'Architecture & Design',   icon: '🏛️', desc: 'Designing spaces that inspire people',  gradient: 'from-stone-600 to-stone-500'   },
  { field: 'Legal & Law',             icon: '⚖️', desc: 'Upholding justice and civil rights',    gradient: 'from-yellow-700 to-yellow-600' },
  { field: 'Nursing & Allied Health', icon: '🩺', desc: 'On the frontlines of patient care',     gradient: 'from-rose-600 to-rose-500'     },
  { field: 'Marketing & Branding',    icon: '📣', desc: 'Creating brands that stand out',        gradient: 'from-purple-600 to-purple-500' },
  { field: 'Accounting & Finance',    icon: '💼', desc: 'Managing the numbers that matter',      gradient: 'from-green-700 to-green-600'   },
  { field: 'Hospitality & Tourism',   icon: '🏨', desc: 'Creating unforgettable experiences',    gradient: 'from-orange-600 to-orange-500' },
];

const floatingCards = [
  { title: 'Civil Engineer',    icon: '🏗️', delay: '0s',   duration: '9s',  left: '5%'  },
  { title: 'Doctor',            icon: '🩺', delay: '2s',   duration: '12s', left: '52%' },
  { title: 'Teacher',           icon: '📚', delay: '4s',   duration: '10s', left: '26%' },
  { title: 'Software Engineer', icon: '💻', delay: '3s',   duration: '8s',  left: '40%' },
  { title: 'Architect',         icon: '🏛️', delay: '5.5s', duration: '11s', left: '15%' },
  { title: 'Accountant',        icon: '💼', delay: '1.5s', duration: '14s', left: '62%' },
  { title: 'Nurse',             icon: '💊', delay: '6s',   duration: '9s',  left: '80%' },
  { title: 'Lawyer',            icon: '⚖️', delay: '7s',   duration: '11s', left: '74%' },
  { title: 'Graphic Designer',  icon: '🎨', delay: '2.5s', duration: '12s', left: '88%' },
];

export default function LoginPage() {
  const router = useRouter();
  const [email, setEmail]                             = useState('');
  const [password, setPassword]                       = useState('');
  const [showPassword, setShowPassword]               = useState(false);
  const [newPassword, setNewPassword]                 = useState('');
  const [companyName, setCompanyName]                 = useState('');
  const [requiresNewPassword, setRequiresNewPassword] = useState(false);
  const [forgotMode, setForgotMode]                   = useState(false);
  const [resetCodeSent, setResetCodeSent]             = useState(false);
  const [resetCode, setResetCode]                     = useState('');
  const [newPasswordReset, setNewPasswordReset]       = useState('');
  const [error, setError]                             = useState('');
  const [loading, setLoading]                         = useState(false);
  const [fieldIndex, setFieldIndex]                   = useState(0);

  useEffect(() => {
    const id = setInterval(() => setFieldIndex(i => (i + 1) % jobFields.length), 5500);
    return () => clearInterval(id);
  }, []);

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true); setError('');
    try {
      const result = await signIn({ username: email, password });
      if (result.nextStep?.signInStep === 'CONFIRM_SIGN_IN_WITH_NEW_PASSWORD_REQUIRED') {
        setRequiresNewPassword(true);
      } else {
        router.push('/dashboard');
      }
    } catch (err: any) {
      setError(err.message || 'Login failed. Please check your credentials.');
    } finally { setLoading(false); }
  };

  const handleNewPassword = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true); setError('');
    try {
      await confirmSignIn({ challengeResponse: newPassword, options: { userAttributes: { name: companyName } } });
      router.push('/dashboard');
    } catch (err: any) {
      setError(err.message || 'Failed to set new password.');
    } finally { setLoading(false); }
  };

  const handleForgotRequest = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true); setError('');
    try {
      await resetPassword({ username: email });
      setResetCodeSent(true);
    } catch (err: any) {
      setError(err.message || 'Could not send reset code.');
    } finally { setLoading(false); }
  };

  const handleForgotConfirm = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true); setError('');
    try {
      await confirmResetPassword({ username: email, confirmationCode: resetCode, newPassword: newPasswordReset });
      setForgotMode(false); setResetCodeSent(false);
      setError('');
    } catch (err: any) {
      setError(err.message || 'Could not reset password.');
    } finally { setLoading(false); }
  };

  const current = jobFields[fieldIndex];

  return (
    <main className="min-h-screen flex">

      {/* ── Left panel — animated gradient (signature) ── */}
      <div className="hidden lg:flex lg:w-1/2 relative gradient-animated flex-col justify-between overflow-hidden"
        style={{ padding: '48px' }}>

        {floatingCards.map((card, i) => (
          <div key={i} className="absolute bottom-0 animate-float-up pointer-events-none"
            style={{ left: card.left, animationDuration: card.duration, animationDelay: card.delay }}>
            <div className="bg-white/10 backdrop-blur-md border border-white/20 rounded-2xl px-4 py-2.5 flex items-center gap-2.5">
              <span className="text-xl">{card.icon}</span>
              <span className="text-white text-xs font-medium whitespace-nowrap">{card.title}</span>
            </div>
          </div>
        ))}

        {/* Logo */}
        <div className="relative z-10 animate-reveal-right">
          <div className="flex items-center gap-3 mb-1">
            <div className="w-10 h-10 bg-white rounded-2xl flex items-center justify-center shadow-lg">
              <span className="text-blue-700 font-bold text-lg">Q</span>
            </div>
            <span className="text-white font-semibold text-xl tracking-tight">QuickJobs</span>
          </div>
          <p className="text-blue-200/80 text-sm ml-[52px]">Employer Portal</p>
        </div>

        {/* Cycling field card */}
        <div className="relative z-10 flex flex-col items-center">
          <p className="text-blue-200/60 text-xs font-medium uppercase tracking-[0.12em] mb-6">Hiring Across All Industries</p>
          <div key={fieldIndex} className="w-full animate-reveal-right">
            <div className={`bg-gradient-to-br ${current.gradient} rounded-2xl p-10 text-center shadow-xl border border-white/10`}>
              <div className="text-5xl mb-5">{current.icon}</div>
              <h3 className="text-white text-lg font-semibold mb-2 tracking-tight">{current.field}</h3>
              <p className="text-white/60 text-sm">{current.desc}</p>
              <div className="flex justify-center gap-1.5 mt-6">
                {jobFields.map((_, i) => (
                  <div key={i} className={`h-1 rounded-full transition-all duration-300 ${i === fieldIndex ? 'w-6 bg-white' : 'w-1.5 bg-white/25'}`} />
                ))}
              </div>
            </div>
          </div>
        </div>

        {/* Stats */}
        <div className="relative z-10 grid grid-cols-3 gap-3 animate-reveal-up" style={{ animationDelay: '0.4s', opacity: 0 }}>
          {[{ value: '10K+', label: 'Job Seekers' }, { value: '500+', label: 'Companies' }, { value: '95%', label: 'Match Rate' }].map(s => (
            <div key={s.label} className="bg-white/8 rounded-2xl p-4 text-center border border-white/10">
              <p className="text-white font-bold text-2xl tracking-tight">{s.value}</p>
              <p className="text-blue-200/70 text-xs mt-1">{s.label}</p>
            </div>
          ))}
        </div>
      </div>

      {/* ── Right panel — warm form ── */}
      <div className="w-full lg:w-1/2 flex items-center justify-center p-8"
        style={{ background: 'var(--bg-base)' }}>
        <div className="w-full max-w-[400px]">

          {/* Mobile logo */}
          <div className="lg:hidden flex items-center gap-2.5 mb-10 justify-center">
            <div className="w-9 h-9 rounded-xl flex items-center justify-center" style={{ background: 'var(--accent-1)' }}>
              <span className="text-white font-bold text-sm">Q</span>
            </div>
            <span className="font-semibold text-lg tracking-tight" style={{ color: 'var(--text-primary)' }}>QuickJobs</span>
          </div>

          <div className="mb-8 animate-reveal-up">
            <h1 className="font-semibold mb-1.5"
              style={{ fontSize: '24px', letterSpacing: '-0.01em', color: 'var(--text-primary)' }}>
              {requiresNewPassword ? 'Set your password' : 'Welcome back'}
            </h1>
            <p className="text-sm" style={{ color: 'var(--text-secondary)' }}>
              {requiresNewPassword
                ? 'Create a permanent password to secure your account.'
                : 'Sign in to your employer account to continue.'}
            </p>
          </div>

          {requiresNewPassword ? (
            <form onSubmit={handleNewPassword} className="space-y-4 animate-reveal-up" style={{ animationDelay: '0.1s', opacity: 0 }}>
              <Field label="Company Name" value={companyName} onChange={setCompanyName} placeholder="e.g. ABC Technologies" />
              <Field label="New Password" type={showPassword ? 'text' : 'password'} value={newPassword} onChange={setNewPassword}
                placeholder="Minimum 8 characters" minLength={8}
                suffix={<EyeToggle show={showPassword} onToggle={() => setShowPassword(v => !v)} />} />
              {error && <ErrorBox message={error} />}
              <SubmitBtn loading={loading} label="Set Password & Continue" />
            </form>
          ) : forgotMode ? (
            <div className="animate-reveal-up" style={{ animationDelay: '0.1s', opacity: 0 }}>
              {!resetCodeSent ? (
                <form onSubmit={handleForgotRequest} className="space-y-4">
                  <p className="text-sm mb-4" style={{ color: 'var(--text-secondary)' }}>Enter your email to receive a reset code.</p>
                  <Field label="Email address" type="email" value={email} onChange={setEmail} placeholder="you@company.com" />
                  {error && <ErrorBox message={error} />}
                  <SubmitBtn loading={loading} label="Send Reset Code" />
                  <button type="button" onClick={() => { setForgotMode(false); setError(''); }} className="w-full text-sm mt-2" style={{ color: 'var(--text-secondary)' }}>← Back to Sign In</button>
                </form>
              ) : (
                <form onSubmit={handleForgotConfirm} className="space-y-4">
                  <p className="text-sm mb-4" style={{ color: 'var(--text-secondary)' }}>Check your email for the reset code.</p>
                  <Field label="Reset Code" value={resetCode} onChange={setResetCode} placeholder="6-digit code" />
                  <Field label="New Password" type={showPassword ? 'text' : 'password'} value={newPasswordReset} onChange={setNewPasswordReset}
                    placeholder="Minimum 8 characters" minLength={8}
                    suffix={<EyeToggle show={showPassword} onToggle={() => setShowPassword(v => !v)} />} />
                  {error && <ErrorBox message={error} />}
                  <SubmitBtn loading={loading} label="Reset Password" />
                  <button type="button" onClick={() => { setForgotMode(false); setResetCodeSent(false); setError(''); }} className="w-full text-sm mt-2" style={{ color: 'var(--text-secondary)' }}>← Back to Sign In</button>
                </form>
              )}
            </div>
          ) : (
            <form onSubmit={handleLogin} className="space-y-4 animate-reveal-up" style={{ animationDelay: '0.1s', opacity: 0 }}>
              <Field label="Email address" type="email" value={email} onChange={setEmail} placeholder="you@company.com" />
              <Field label="Password" type={showPassword ? 'text' : 'password'} value={password} onChange={setPassword}
                placeholder="Enter your password"
                suffix={<EyeToggle show={showPassword} onToggle={() => setShowPassword(v => !v)} />}
                action={<button type="button" onClick={() => { setForgotMode(true); setError(''); }} className="text-xs font-medium" style={{ color: 'var(--accent-1)' }}>Forgot password?</button>} />
              {error && <ErrorBox message={error} />}
              <SubmitBtn loading={loading} label="Sign In" />
            </form>
          )}

          <div className="flex items-center gap-3 mt-6">
            <div className="flex-1 h-px" style={{ background: 'var(--border-subtle)' }} />
            <span className="text-xs" style={{ color: 'var(--text-tertiary)' }}>Secured by AWS Cognito</span>
            <div className="flex-1 h-px" style={{ background: 'var(--border-subtle)' }} />
          </div>

          {!requiresNewPassword && !forgotMode && (
            <p className="text-center text-xs mt-4" style={{ color: 'var(--text-tertiary)' }}>
              No account?{' '}
              <a href="/register" className="font-medium" style={{ color: 'var(--accent-1)' }}>Register your company</a>
            </p>
          )}
        </div>
      </div>
    </main>
  );
}

function Field({ label, value, onChange, placeholder, type = 'text', minLength, suffix, action }: {
  label: string; value: string; onChange: (v: string) => void;
  placeholder?: string; type?: string; minLength?: number;
  suffix?: React.ReactNode; action?: React.ReactNode;
}) {
  return (
    <div>
      <div className="flex items-center justify-between mb-1.5">
        <label className="text-sm font-medium" style={{ color: 'var(--text-primary)', letterSpacing: '0.01em' }}>{label}</label>
        {action}
      </div>
      <div className="relative">
        <input type={type} value={value} onChange={e => onChange(e.target.value)} required
          minLength={minLength} placeholder={placeholder} className="w-full text-sm"
          style={{ padding: '11px 16px', paddingRight: suffix ? '44px' : '16px', background: 'var(--bg-sunken)', border: '1px solid transparent', borderRadius: '10px', color: 'var(--text-primary)', outline: 'none' }}
          onFocus={e => { e.target.style.borderColor = 'var(--accent-1)'; e.target.style.boxShadow = '0 0 0 3px rgba(37,99,235,0.12)'; }}
          onBlur={e => { e.target.style.borderColor = 'transparent'; e.target.style.boxShadow = 'none'; }} />
        {suffix && <div className="absolute right-3 top-1/2 -translate-y-1/2">{suffix}</div>}
      </div>
    </div>
  );
}

function EyeToggle({ show, onToggle }: { show: boolean; onToggle: () => void }) {
  return (
    <button type="button" onClick={onToggle} style={{ color: 'var(--text-tertiary)' }}>
      {show ? <EyeOff size={16} /> : <Eye size={16} />}
    </button>
  );
}

function SubmitBtn({ loading, label }: { loading: boolean; label: string }) {
  return (
    <button type="submit" disabled={loading} className="w-full text-white text-sm font-medium flex items-center justify-center gap-2"
      style={{ padding: '12px 24px', background: 'var(--accent-1)', borderRadius: '10px', marginTop: '8px', opacity: loading ? 0.7 : 1, letterSpacing: '0.01em' }}>
      {loading
        ? <><svg className="animate-spin w-4 h-4" fill="none" viewBox="0 0 24 24"><circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" /><path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" /></svg>Loading...</>
        : label}
    </button>
  );
}

function ErrorBox({ message }: { message: string }) {
  return (
    <div className="flex items-start gap-2.5 animate-toast"
      style={{ padding: '12px 14px', background: '#FEF2F2', border: '1px solid #FECACA', borderRadius: '10px' }}>
      <AlertCircle size={15} style={{ color: 'var(--accent-danger)', marginTop: '1px', flexShrink: 0 }} />
      <p className="text-sm" style={{ color: '#B91C1C' }}>{message}</p>
    </div>
  );
}
