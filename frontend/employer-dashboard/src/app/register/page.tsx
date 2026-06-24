'use client';

import '@/lib/amplify';
import { useState } from 'react';
import { signUp, confirmSignUp } from 'aws-amplify/auth';
import { useRouter } from 'next/navigation';
import { Eye, EyeOff, AlertCircle, CheckCircle, Building2 } from 'lucide-react';

const COMPANY_URL = process.env.NEXT_PUBLIC_COMPANY_SERVICE_URL || 'http://localhost:8003';

type Step = 'form' | 'verify' | 'done';

export default function RegisterPage() {
  const router = useRouter();

  const [step, setStep]               = useState<Step>('form');
  const [companyName, setCompanyName] = useState('');
  const [email, setEmail]             = useState('');
  const [password, setPassword]       = useState('');
  const [showPass, setShowPass]       = useState(false);
  const [code, setCode]               = useState('');
  const [error, setError]             = useState('');
  const [loading, setLoading]         = useState(false);

  const handleSignUp = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true); setError('');
    try {
      await signUp({
        username: email,
        password,
        options: {
          userAttributes: { email, name: companyName },
        },
      });
      setStep('verify');
    } catch (err: any) {
      setError(err.message || 'Sign-up failed. Please try again.');
    } finally { setLoading(false); }
  };

  const handleConfirm = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true); setError('');
    try {
      await confirmSignUp({ username: email, confirmationCode: code });

      // Create pending company record
      await fetch(`${COMPANY_URL}/companies`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          name:             companyName,
          email:            email,
          cognito_user_id:  email,
        }),
      });

      setStep('done');
    } catch (err: any) {
      setError(err.message || 'Verification failed. Check your code and try again.');
    } finally { setLoading(false); }
  };

  return (
    <main className="min-h-screen flex items-center justify-center p-6" style={{ background: 'var(--bg-base)' }}>
      <div className="w-full max-w-[420px]">

        {/* Logo */}
        <div className="flex items-center gap-2.5 mb-10 justify-center">
          <div className="w-9 h-9 rounded-xl flex items-center justify-center" style={{ background: 'var(--accent-1)' }}>
            <span className="text-white font-bold text-sm">Q</span>
          </div>
          <span className="font-semibold text-lg tracking-tight" style={{ color: 'var(--text-primary)' }}>QuickJobs</span>
        </div>

        {step === 'form' && (
          <div className="animate-reveal-up">
            <h1 className="font-semibold mb-1.5"
              style={{ fontSize: '24px', letterSpacing: '-0.01em', color: 'var(--text-primary)' }}>
              Register your company
            </h1>
            <p className="text-sm mb-8" style={{ color: 'var(--text-secondary)' }}>
              Create an account to post jobs and find candidates via WhatsApp.
              Your account will be reviewed by an admin before you can post listings.
            </p>

            <form onSubmit={handleSignUp} className="space-y-4">
              <Field label="Company Name *" value={companyName} onChange={setCompanyName} placeholder="e.g. Acme Technologies" required />
              <Field label="Work Email *" type="email" value={email} onChange={setEmail} placeholder="you@company.com" required />
              <Field label="Password *" type={showPass ? 'text' : 'password'} value={password} onChange={setPassword}
                placeholder="Minimum 8 characters" required minLength={8}
                suffix={<EyeToggle show={showPass} onToggle={() => setShowPass(v => !v)} />} />
              {error && <ErrorBox message={error} />}
              <button type="submit" disabled={loading} className="w-full text-white text-sm font-medium flex items-center justify-center gap-2 mt-2"
                style={{ padding: '12px', background: 'var(--accent-1)', borderRadius: '10px', opacity: loading ? 0.7 : 1 }}>
                {loading ? <Spinner /> : 'Create Account'}
              </button>
            </form>

            <p className="text-center text-xs mt-6" style={{ color: 'var(--text-tertiary)' }}>
              Already have an account?{' '}
              <a href="/login" className="font-medium" style={{ color: 'var(--accent-1)' }}>Sign in</a>
            </p>
          </div>
        )}

        {step === 'verify' && (
          <div className="animate-reveal-up">
            <div className="w-12 h-12 rounded-2xl flex items-center justify-center mx-auto mb-6" style={{ background: 'var(--accent-1-soft)' }}>
              <Building2 size={22} style={{ color: 'var(--accent-1)' }} />
            </div>
            <h1 className="font-semibold mb-1.5 text-center"
              style={{ fontSize: '22px', letterSpacing: '-0.01em', color: 'var(--text-primary)' }}>
              Check your email
            </h1>
            <p className="text-sm mb-8 text-center" style={{ color: 'var(--text-secondary)' }}>
              We sent a verification code to <strong>{email}</strong>
            </p>

            <form onSubmit={handleConfirm} className="space-y-4">
              <Field label="Verification Code" value={code} onChange={setCode} placeholder="6-digit code" required />
              {error && <ErrorBox message={error} />}
              <button type="submit" disabled={loading} className="w-full text-white text-sm font-medium flex items-center justify-center gap-2"
                style={{ padding: '12px', background: 'var(--accent-1)', borderRadius: '10px', opacity: loading ? 0.7 : 1 }}>
                {loading ? <Spinner /> : 'Verify & Continue'}
              </button>
            </form>
          </div>
        )}

        {step === 'done' && (
          <div className="text-center animate-reveal-up">
            <div className="w-14 h-14 rounded-2xl flex items-center justify-center mx-auto mb-6" style={{ background: '#F0FDF4' }}>
              <CheckCircle size={28} style={{ color: '#16A34A' }} />
            </div>
            <h1 className="font-semibold mb-2" style={{ fontSize: '22px', color: 'var(--text-primary)', letterSpacing: '-0.01em' }}>
              You're registered!
            </h1>
            <p className="text-sm mb-2 mx-auto max-w-xs" style={{ color: 'var(--text-secondary)', lineHeight: '1.6' }}>
              Your company account has been created and is <strong>pending admin approval.</strong>
            </p>
            <p className="text-sm mb-8 mx-auto max-w-xs" style={{ color: 'var(--text-tertiary)', lineHeight: '1.6' }}>
              Once approved you'll be able to post jobs and receive AI-matched candidates.
              An admin will also activate your login access.
            </p>
            <button onClick={() => router.push('/login')} className="text-white text-sm font-medium"
              style={{ padding: '11px 24px', background: 'var(--accent-1)', borderRadius: '10px' }}>
              Go to Sign In
            </button>
          </div>
        )}
      </div>
    </main>
  );
}

function Field({ label, value, onChange, placeholder, type = 'text', required, minLength, suffix }: {
  label: string; value: string; onChange: (v: string) => void;
  placeholder?: string; type?: string; required?: boolean; minLength?: number; suffix?: React.ReactNode;
}) {
  return (
    <div>
      <label className="block text-sm font-medium mb-1.5" style={{ color: 'var(--text-primary)' }}>{label}</label>
      <div className="relative">
        <input type={type} value={value} onChange={e => onChange(e.target.value)} required={required} minLength={minLength}
          placeholder={placeholder} className="w-full text-sm"
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

function ErrorBox({ message }: { message: string }) {
  return (
    <div className="flex items-start gap-2.5"
      style={{ padding: '12px 14px', background: '#FEF2F2', border: '1px solid #FECACA', borderRadius: '10px' }}>
      <AlertCircle size={15} style={{ color: '#B91C1C', marginTop: '1px', flexShrink: 0 }} />
      <p className="text-sm" style={{ color: '#B91C1C' }}>{message}</p>
    </div>
  );
}

function Spinner() {
  return <svg className="animate-spin w-4 h-4" fill="none" viewBox="0 0 24 24"><circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" /><path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" /></svg>;
}
