'use client';

import '@/app/lib/amplify';
import { useState } from 'react';
import { signIn, confirmSignIn, resetPassword, confirmResetPassword } from 'aws-amplify/auth';
import { useRouter } from 'next/navigation';
import { ShieldCheck, Eye, EyeOff, AlertCircle } from 'lucide-react';

function getErrorMessage(err: unknown): string | undefined {
  return err instanceof Error ? err.message : undefined;
}

export default function AdminLoginPage() {
  const router = useRouter();
  const [email, setEmail]                             = useState('');
  const [password, setPassword]                       = useState('');
  const [newPassword, setNewPassword]                 = useState('');
  const [showPassword, setShowPassword]               = useState(false);
  const [requiresNewPassword, setRequiresNewPassword] = useState(false);
  const [forgotMode, setForgotMode]                   = useState(false);
  const [resetCodeSent, setResetCodeSent]             = useState(false);
  const [resetCode, setResetCode]                     = useState('');
  const [newPasswordReset, setNewPasswordReset]       = useState('');
  const [error, setError]                             = useState('');
  const [loading, setLoading]                         = useState(false);

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
    } catch (err) {
      setError(getErrorMessage(err) || 'Login failed. Please check your credentials.');
    } finally { setLoading(false); }
  };

  const handleNewPassword = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true); setError('');
    try {
      await confirmSignIn({ challengeResponse: newPassword });
      router.push('/dashboard');
    } catch (err) {
      setError(getErrorMessage(err) || 'Failed to set new password.');
    } finally { setLoading(false); }
  };

  const handleForgotRequest = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true); setError('');
    try {
      await resetPassword({ username: email });
      setResetCodeSent(true);
    } catch (err) {
      setError(getErrorMessage(err) || 'Could not send reset code.');
    } finally { setLoading(false); }
  };

  const handleForgotConfirm = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true); setError('');
    try {
      await confirmResetPassword({ username: email, confirmationCode: resetCode, newPassword: newPasswordReset });
      setForgotMode(false); setResetCodeSent(false); setError('');
    } catch (err) {
      setError(getErrorMessage(err) || 'Could not reset password.');
    } finally { setLoading(false); }
  };

  return (
    <main className="min-h-screen flex" style={{ background: 'var(--bg-base)' }}>

      {/* ── Left accent panel ── */}
      <div className="hidden lg:flex lg:w-[420px] shrink-0 flex-col justify-between relative overflow-hidden"
        style={{ background: 'var(--accent-1)', padding: '48px' }}>

        {/* Soft glow */}
        <div className="absolute inset-0 pointer-events-none" style={{
          background: 'radial-gradient(ellipse 80% 60% at 30% 20%, rgba(255,255,255,0.08), transparent 70%)',
        }} />

        {/* Grid overlay */}
        <div className="absolute inset-0 pointer-events-none" style={{
          backgroundImage: 'linear-gradient(rgba(255,255,255,0.04) 1px, transparent 1px), linear-gradient(90deg, rgba(255,255,255,0.04) 1px, transparent 1px)',
          backgroundSize: '48px 48px',
        }} />

        {/* Logo */}
        <div className="relative z-10">
          <div className="flex items-center gap-3 mb-1">
            <div className="w-10 h-10 bg-white/15 rounded-xl flex items-center justify-center border border-white/20">
              <ShieldCheck size={20} className="text-white" />
            </div>
            <span className="text-white font-semibold text-lg tracking-tight">QuickJobs Admin</span>
          </div>
          <p className="text-indigo-200/70 text-sm mt-1 ml-[52px]">Internal Operations Portal</p>
        </div>

        {/* Footer note */}
        <div className="relative z-10">
          <p className="text-indigo-200/40 text-xs">Restricted access — authorised personnel only</p>
        </div>
      </div>

      {/* ── Right form panel ── */}
      <div className="flex-1 flex items-center justify-center p-8">
        <div className="w-full max-w-[380px]">

          {/* Mobile logo */}
          <div className="lg:hidden flex items-center gap-2.5 mb-10 justify-center">
            <div className="w-9 h-9 rounded-xl flex items-center justify-center" style={{ background: 'var(--accent-1)' }}>
              <ShieldCheck size={16} className="text-white" />
            </div>
            <span className="font-semibold text-lg tracking-tight" style={{ color: 'var(--text-primary)' }}>QuickJobs Admin</span>
          </div>

          {/* Heading */}
          <div className="mb-8">
            <h1 className="font-semibold mb-1.5"
              style={{ fontSize: '22px', letterSpacing: '-0.01em', color: 'var(--text-primary)' }}>
              {requiresNewPassword ? 'Set your password' : 'Administrator sign in'}
            </h1>
            <p className="text-sm" style={{ color: 'var(--text-secondary)' }}>
              {requiresNewPassword
                ? 'Create a permanent password for your admin account.'
                : 'Sign in with your admin credentials to continue.'}
            </p>
          </div>

          {/* Form */}
          {requiresNewPassword ? (
            <form onSubmit={handleNewPassword} className="space-y-4">
              <Field label="New Password" type={showPassword ? 'text' : 'password'} value={newPassword} onChange={setNewPassword}
                placeholder="Minimum 8 characters" minLength={8}
                suffix={<EyeToggle show={showPassword} onToggle={() => setShowPassword(v => !v)} />} />
              {error && <ErrorBox message={error} />}
              <SubmitBtn loading={loading} label="Set Password & Continue" />
            </form>
          ) : forgotMode ? (
            <div>
              {!resetCodeSent ? (
                <form onSubmit={handleForgotRequest} className="space-y-4">
                  <p className="text-sm mb-2" style={{ color: 'var(--text-secondary)' }}>Enter your admin email to receive a reset code.</p>
                  <Field label="Email address" type="email" value={email} onChange={setEmail} placeholder="admin@quickjobs.com" />
                  {error && <ErrorBox message={error} />}
                  <SubmitBtn loading={loading} label="Send Reset Code" />
                  <button type="button" onClick={() => { setForgotMode(false); setError(''); }} className="w-full text-sm mt-2" style={{ color: 'var(--text-secondary)' }}>← Back</button>
                </form>
              ) : (
                <form onSubmit={handleForgotConfirm} className="space-y-4">
                  <p className="text-sm mb-2" style={{ color: 'var(--text-secondary)' }}>Check your email for the reset code.</p>
                  <Field label="Reset Code" value={resetCode} onChange={setResetCode} placeholder="6-digit code" />
                  <Field label="New Password" type={showPassword ? 'text' : 'password'} value={newPasswordReset} onChange={setNewPasswordReset}
                    placeholder="Minimum 8 characters" minLength={8}
                    suffix={<EyeToggle show={showPassword} onToggle={() => setShowPassword(v => !v)} />} />
                  {error && <ErrorBox message={error} />}
                  <SubmitBtn loading={loading} label="Reset Password" />
                  <button type="button" onClick={() => { setForgotMode(false); setResetCodeSent(false); setError(''); }} className="w-full text-sm mt-2" style={{ color: 'var(--text-secondary)' }}>← Back</button>
                </form>
              )}
            </div>
          ) : (
            <form onSubmit={handleLogin} className="space-y-4">
              <Field label="Email address" type="email" value={email} onChange={setEmail} placeholder="admin@quickjobs.com" />
              <div>
                <div className="flex items-center justify-between mb-1.5">
                  <label className="text-sm font-medium" style={{ color: 'var(--text-primary)', letterSpacing: '0.01em' }}>Password</label>
                  <button type="button" onClick={() => { setForgotMode(true); setError(''); }} className="text-xs font-medium" style={{ color: 'var(--accent-1)' }}>Forgot password?</button>
                </div>
                <div className="relative">
                  <input type={showPassword ? 'text' : 'password'} value={password} onChange={e => setPassword(e.target.value)} required
                    placeholder="Enter your password" className="w-full text-sm"
                    style={{ padding: '11px 16px', paddingRight: '44px', background: 'var(--bg-sunken)', border: '1px solid transparent', borderRadius: '10px', color: 'var(--text-primary)', outline: 'none' }}
                    onFocus={e => { e.target.style.borderColor = 'var(--accent-1)'; e.target.style.boxShadow = '0 0 0 3px rgba(79,70,229,0.12)'; }}
                    onBlur={e => { e.target.style.borderColor = 'transparent'; e.target.style.boxShadow = 'none'; }} />
                  <div className="absolute right-3 top-1/2 -translate-y-1/2"><EyeToggle show={showPassword} onToggle={() => setShowPassword(v => !v)} /></div>
                </div>
              </div>
              {error && <ErrorBox message={error} />}
              <SubmitBtn loading={loading} label="Sign In" />
            </form>
          )}

          {/* Divider */}
          <div className="flex items-center gap-3 mt-6">
            <div className="flex-1 h-px" style={{ background: 'var(--border-subtle)' }} />
            <span className="text-xs" style={{ color: 'var(--text-tertiary)' }}>Secured by AWS Cognito</span>
            <div className="flex-1 h-px" style={{ background: 'var(--border-subtle)' }} />
          </div>
        </div>
      </div>
    </main>
  );
}

function Field({ label, value, onChange, placeholder, type = 'text', minLength, suffix }: {
  label: string; value: string; onChange: (v: string) => void;
  placeholder?: string; type?: string; minLength?: number; suffix?: React.ReactNode;
}) {
  return (
    <div>
      <label className="block text-sm font-medium mb-1.5" style={{ color: 'var(--text-primary)', letterSpacing: '0.01em' }}>{label}</label>
      <div className="relative">
        <input type={type} value={value} onChange={e => onChange(e.target.value)} required minLength={minLength}
          placeholder={placeholder} className="w-full text-sm"
          style={{ padding: '11px 16px', paddingRight: suffix ? '44px' : '16px', background: 'var(--bg-sunken)', border: '1px solid transparent', borderRadius: '10px', color: 'var(--text-primary)', outline: 'none' }}
          onFocus={e => { e.target.style.borderColor = 'var(--accent-1)'; e.target.style.boxShadow = '0 0 0 3px rgba(79,70,229,0.12)'; }}
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
