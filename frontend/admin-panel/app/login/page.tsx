'use client';

import '@/app/lib/amplify';
import { useState } from 'react';
import { signIn, confirmSignIn } from 'aws-amplify/auth';
import { useRouter } from 'next/navigation';
import { ShieldCheck, Eye, EyeOff, AlertCircle } from 'lucide-react';

export default function AdminLoginPage() {
  const router = useRouter();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [requiresNewPassword, setRequiresNewPassword] = useState(false);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

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
      await confirmSignIn({ challengeResponse: newPassword });
      router.push('/dashboard');
    } catch (err: any) {
      setError(err.message || 'Failed to set new password.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <main className="min-h-screen bg-slate-950 flex items-center justify-center p-4">

      {/* Background grid pattern */}
      <div className="absolute inset-0 bg-[linear-gradient(rgba(99,102,241,0.03)_1px,transparent_1px),linear-gradient(90deg,rgba(99,102,241,0.03)_1px,transparent_1px)] bg-[size:64px_64px]" />

      <div className="relative w-full max-w-md">

        {/* Card */}
        <div className="bg-slate-900 border border-slate-800 rounded-2xl p-8 shadow-2xl">

          {/* Header */}
          <div className="flex flex-col items-center mb-8">
            <div className="w-14 h-14 bg-indigo-600 rounded-2xl flex items-center justify-center mb-4 shadow-lg shadow-indigo-900/50">
              <ShieldCheck size={26} className="text-white" />
            </div>
            <h1 className="text-xl font-bold text-white">
              {requiresNewPassword ? 'Set New Password' : 'Admin Portal'}
            </h1>
            <p className="text-slate-400 text-sm mt-1">
              {requiresNewPassword
                ? 'Create a permanent password for your account'
                : 'QuickJobs internal administration'}
            </p>
          </div>

          {/* Form */}
          {requiresNewPassword ? (
            <form onSubmit={handleNewPassword} className="space-y-4">
              <Field
                label="New Password"
                type={showPassword ? 'text' : 'password'}
                value={newPassword}
                onChange={setNewPassword}
                placeholder="Minimum 8 characters"
                minLength={8}
                suffix={
                  <button type="button" onClick={() => setShowPassword(!showPassword)} className="text-slate-400 hover:text-slate-200">
                    {showPassword ? <EyeOff size={16} /> : <Eye size={16} />}
                  </button>
                }
              />
              {error && <ErrorBox message={error} />}
              <SubmitBtn loading={loading} label="Set Password & Continue" />
            </form>
          ) : (
            <form onSubmit={handleLogin} className="space-y-4">
              <Field
                label="Email address"
                type="email"
                value={email}
                onChange={setEmail}
                placeholder="admin@quickjobs.com"
              />
              <Field
                label="Password"
                type={showPassword ? 'text' : 'password'}
                value={password}
                onChange={setPassword}
                placeholder="Enter your password"
                suffix={
                  <button type="button" onClick={() => setShowPassword(!showPassword)} className="text-slate-400 hover:text-slate-200">
                    {showPassword ? <EyeOff size={16} /> : <Eye size={16} />}
                  </button>
                }
              />
              {error && <ErrorBox message={error} />}
              <SubmitBtn loading={loading} label="Sign In" />
            </form>
          )}

          {/* Footer */}
          <div className="flex items-center gap-3 mt-6">
            <div className="flex-1 h-px bg-slate-800" />
            <span className="text-xs text-slate-600">Secured by AWS Cognito</span>
            <div className="flex-1 h-px bg-slate-800" />
          </div>
        </div>

        <p className="text-center text-slate-600 text-xs mt-4">
          QuickJobs Admin — restricted access only
        </p>
      </div>
    </main>
  );
}

function Field({ label, value, onChange, placeholder, type = 'text', minLength, suffix }: {
  label: string; value: string; onChange: (v: string) => void;
  placeholder?: string; type?: string; minLength?: number;
  suffix?: React.ReactNode;
}) {
  return (
    <div>
      <label className="block text-sm font-medium text-slate-300 mb-1.5">{label}</label>
      <div className="relative">
        <input
          type={type} value={value} required minLength={minLength}
          onChange={(e) => onChange(e.target.value)} placeholder={placeholder}
          className="w-full bg-slate-800 border border-slate-700 rounded-xl px-4 py-2.5 text-white text-sm placeholder:text-slate-500 focus:outline-none focus:border-indigo-500 transition-colors pr-10"
        />
        {suffix && (
          <div className="absolute right-3 top-1/2 -translate-y-1/2">{suffix}</div>
        )}
      </div>
    </div>
  );
}

function SubmitBtn({ loading, label }: { loading: boolean; label: string }) {
  return (
    <button type="submit" disabled={loading}
      className="w-full bg-indigo-600 text-white py-2.5 rounded-xl font-semibold text-sm hover:bg-indigo-500 transition-colors disabled:opacity-50 flex items-center justify-center gap-2 mt-2">
      {loading ? (
        <><svg className="animate-spin w-4 h-4" fill="none" viewBox="0 0 24 24">
          <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
          <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
        </svg>Loading...</>
      ) : label}
    </button>
  );
}

function ErrorBox({ message }: { message: string }) {
  return (
    <div className="bg-red-950 border border-red-800 rounded-xl p-3 flex items-start gap-2">
      <AlertCircle size={15} className="text-red-400 mt-0.5 shrink-0" />
      <p className="text-red-300 text-sm">{message}</p>
    </div>
  );
}
