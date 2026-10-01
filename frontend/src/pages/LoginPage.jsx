import { useState } from "react";
import { Link, Navigate, useLocation, useNavigate } from "react-router-dom";
import { useAuth } from "../auth/AuthContext";
import { getApiErrorMessage } from "../api/client";

export default function LoginPage() {
  const { login, isAuthenticated, sessionExpiredMessage, clearSessionExpiredMessage } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();

  const [form, setForm] = useState({ email: "", password: "" });
  const [error, setError] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [showPassword, setShowPassword] = useState(false);

  if (isAuthenticated) {
    return <Navigate to="/" replace />;
  }

  function updateField(e) {
    const { name, value } = e.target;
    setForm((c) => ({ ...c, [name]: value }));
  }

  async function handleSubmit(e) {
    e.preventDefault();
    setError("");
    clearSessionExpiredMessage();
    setSubmitting(true);
    try {
      await login({ email: form.email.trim(), password: form.password });
      const destination = location.state?.from || "/";
      navigate(destination, { replace: true });
    } catch (err) {
      setError(getApiErrorMessage(err, "Could not sign in. Please check your credentials."));
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <main className="min-h-screen w-full bg-[#F7F6F2] flex items-center justify-center p-4 sm:p-6 lg:p-0">
      <div className="w-full max-w-6xl min-h-[640px] bg-white rounded-3xl border border-slate-200 shadow-xl overflow-hidden grid lg:grid-cols-12 my-auto">
        
        {/* ── Left Column: Form Panel ── */}
        <div className="lg:col-span-6 p-8 sm:p-12 flex flex-col justify-between">
          <div>
            {/* Brand Header */}
            <div className="flex items-center gap-3 mb-8">
              <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-teal-700 text-white shadow-sm">
                <svg className="h-5 w-5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2} strokeLinecap="round" strokeLinejoin="round">
                  <path d="M12 3v17M4 7h16M4 7l-2 6h6L6 7M20 7l-2 6h6L20 7M9 20h6" />
                </svg>
              </div>
              <div>
                <span className="text-lg font-bold text-slate-900 font-serif-title tracking-tight">
                  Nyaya AI
                </span>
                <p className="text-[11px] font-semibold text-teal-700 uppercase tracking-wider">
                  Indian Legal Information Workspace
                </p>
              </div>
            </div>

            {/* Form Title */}
            <div className="mb-7">
              <h1 className="text-2xl sm:text-3xl font-bold text-slate-900 font-serif-title tracking-tight">
                Sign in to your account
              </h1>
              <p className="mt-2 text-sm text-slate-600">
                Access your citation-grounded legal assistant and document workspace.
              </p>
            </div>

            {/* Form */}
            <form className="space-y-5" onSubmit={handleSubmit} noValidate>
              {/* Email Input */}
              <div>
                <label htmlFor="email" className="block text-xs font-semibold uppercase tracking-wider text-slate-700 mb-1.5">
                  Email address
                </label>
                <input
                  id="email"
                  name="email"
                  type="email"
                  required
                  autoComplete="email"
                  value={form.email}
                  onChange={updateField}
                  className="form-input-legal min-h-[46px]"
                  placeholder="you@example.com"
                  aria-invalid={Boolean(error)}
                  aria-describedby={error ? "login-error" : undefined}
                />
              </div>

              {/* Password Input */}
              <div>
                <label htmlFor="password" className="block text-xs font-semibold uppercase tracking-wider text-slate-700 mb-1.5">
                  Password
                </label>
                <div className="relative">
                  <input
                    id="password"
                    name="password"
                    type={showPassword ? "text" : "password"}
                    required
                    autoComplete="current-password"
                    value={form.password}
                    onChange={updateField}
                    className="form-input-legal min-h-[46px] pr-10"
                    placeholder="Enter your password"
                    aria-invalid={Boolean(error)}
                    aria-describedby={error ? "login-error" : undefined}
                  />
                  <button
                    type="button"
                    onClick={() => setShowPassword((v) => !v)}
                    className="absolute right-2 top-1/2 -translate-y-1/2 text-slate-400 hover:text-teal-700 transition-colors p-2 min-h-[44px] min-w-[44px] flex items-center justify-center cursor-pointer"
                    aria-label={showPassword ? "Hide password" : "Show password"}
                  >
                    {showPassword ? (
                      <svg className="h-5 w-5" viewBox="0 0 20 20" fill="currentColor" aria-hidden="true">
                        <path fillRule="evenodd" d="M3.28 2.22a.75.75 0 00-1.06 1.06l14.5 14.5a.75.75 0 101.06-1.06l-1.745-1.745a10.029 10.029 0 003.3-4.38 1.651 1.651 0 000-1.185A10.004 10.004 0 009.999 3a9.956 9.956 0 00-4.744 1.194L3.28 2.22zM7.752 6.69l1.092 1.092a2.5 2.5 0 013.374 3.373l1.091 1.092a4 4 0 00-5.557-5.557z" clipRule="evenodd" />
                        <path d="M10.748 13.93l2.523 2.523a9.987 9.987 0 01-3.27.547c-4.258 0-7.894-2.66-9.337-6.41a1.651 1.651 0 010-1.186A10.007 10.007 0 012.839 6.02L6.07 9.252a4 4 0 004.678 4.678z" />
                      </svg>
                    ) : (
                      <svg className="h-5 w-5" viewBox="0 0 20 20" fill="currentColor" aria-hidden="true">
                        <path d="M10 12.5a2.5 2.5 0 100-5 2.5 2.5 0 000 5z" />
                        <path fillRule="evenodd" d="M.664 10.59a1.651 1.651 0 010-1.186A10.004 10.004 0 0110 3c4.257 0 7.893 2.66 9.336 6.41.147.381.146.804 0 1.186A10.004 10.004 0 0110 17c-4.257 0-7.893-2.66-9.336-6.41z" clipRule="evenodd" />
                      </svg>
                    )}
                  </button>
                </div>
              </div>

              {/* Session Expired Notice */}
              {sessionExpiredMessage && !error && (
                <div role="alert" className="rounded-xl border border-amber-300 bg-amber-50 px-4 py-3 text-xs font-semibold text-amber-900 flex items-start gap-2">
                  <svg className="h-4 w-4 flex-shrink-0 mt-0.5 text-amber-700" viewBox="0 0 20 20" fill="currentColor" aria-hidden="true">
                    <path fillRule="evenodd" d="M8.485 2.495c.673-1.167 2.357-1.167 3.03 0l6.28 10.875c.673 1.167-.17 2.625-1.516 2.625H3.72c-1.347 0-2.189-1.458-1.515-2.625L8.485 2.495zM10 5a.75.75 0 01.75.75v3.5a.75.75 0 01-1.5 0v-3.5A.75.75 0 0110 5zm0 9a1 1 0 100-2 1 1 0 000 2z" clipRule="evenodd" />
                  </svg>
                  {sessionExpiredMessage}
                </div>
              )}

              {/* Error Alert */}
              {error && (
                <div id="login-error" role="alert" className="rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-xs font-semibold text-red-800 flex items-start gap-2">
                  <svg className="h-4 w-4 flex-shrink-0 mt-0.5 text-red-600" viewBox="0 0 20 20" fill="currentColor" aria-hidden="true">
                    <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.28 7.22a.75.75 0 00-1.06 1.06L8.94 10l-1.72 1.72a.75.75 0 101.06 1.06L10 11.06l1.72 1.72a.75.75 0 101.06-1.06L11.06 10l1.72-1.72a.75.75 0 00-1.06-1.06L10 8.94 8.28 7.22z" clipRule="evenodd" />
                  </svg>
                  {error}
                </div>
              )}

              {/* Submit Button */}
              <button
                type="submit"
                disabled={submitting}
                className="btn-teal w-full py-3 text-sm font-semibold shadow-sm transition-all"
              >
                {submitting ? (
                  <>
                    <span className="h-4 w-4 rounded-full border-2 border-white border-t-transparent animate-spin-smooth" />
                    Signing in…
                  </>
                ) : (
                  "Sign in"
                )}
              </button>
            </form>
          </div>

          <p className="mt-8 text-center text-xs font-medium text-slate-600">
            New to Nyaya AI?{" "}
            <Link
              to="/register"
              className="font-bold text-teal-700 hover:text-teal-800 underline transition-colors"
            >
              Create an account
            </Link>
          </p>
        </div>

        {/* ── Right Column: Deep Navy Visual Panel ── */}
        <div className="hidden lg:col-span-6 bg-slate-900 text-white p-12 lg:flex flex-col justify-between relative overflow-hidden">
          {/* Background subtle SVG pattern */}
          <div className="absolute inset-0 opacity-10 pointer-events-none">
            <svg width="100%" height="100%" xmlns="http://www.w3.org/2000/svg">
              <defs>
                <pattern id="grid-pattern" width="40" height="40" patternUnits="userSpaceOnUse">
                  <path d="M 40 0 L 0 0 0 40" fill="none" stroke="#FFFFFF" strokeWidth="0.5" />
                </pattern>
              </defs>
              <rect width="100%" height="100%" fill="url(#grid-pattern)" />
            </svg>
          </div>

          <div className="relative z-10">
            <span className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-teal-900/60 border border-teal-700/60 text-teal-300 text-xs font-semibold">
              <span className="h-2 w-2 rounded-full bg-teal-400" />
              Verified Statutory Intelligence
            </span>
          </div>

          {/* Layered Document Composition */}
          <div className="relative z-10 my-auto py-8">
            <div className="relative mx-auto max-w-sm">
              {/* Back Card */}
              <div className="absolute inset-0 -rotate-6 rounded-2xl bg-slate-800/80 border border-slate-700/60 p-6 shadow-lg transform transition-transform" />
              {/* Middle Card */}
              <div className="absolute inset-0 rotate-3 rounded-2xl bg-teal-950/70 border border-teal-800/60 p-6 shadow-xl transform transition-transform" />
              {/* Front Card */}
              <div className="relative rounded-2xl bg-slate-850 border border-slate-700 p-7 shadow-2xl space-y-4">
                <div className="flex items-center justify-between border-b border-slate-700/80 pb-3">
                  <div className="flex items-center gap-2 text-xs font-mono text-teal-400">
                    <span className="h-2 w-2 rounded-full bg-teal-400" />
                    CASE_FILE_REF #2026-IN
                  </div>
                  <span className="text-[10px] uppercase font-bold text-slate-400">Verified</span>
                </div>
                <div className="space-y-2">
                  <div className="h-2.5 w-3/4 rounded bg-slate-700" />
                  <div className="h-2 w-full rounded bg-slate-800" />
                  <div className="h-2 w-5/6 rounded bg-slate-800" />
                </div>
                <div className="pt-2 flex items-center justify-between text-xs text-slate-300">
                  <span>Consumer Rights Act 2019</span>
                  <span className="text-teal-400 font-mono">SHA-256 ✓</span>
                </div>
              </div>
            </div>

            <div className="mt-10 text-center">
              <h2 className="text-2xl font-bold font-serif-title tracking-tight text-white">
                “Bring clarity to your legal work.”
              </h2>
              <p className="mt-3 text-xs text-slate-400 leading-5 max-w-sm mx-auto">
                Structured legal research, statutory grounding, evidence vaulting, and automated complaint drafting in one calm workspace.
              </p>
            </div>
          </div>

          <div className="relative z-10 flex items-center justify-between text-xs text-slate-400 border-t border-slate-800 pt-4">
            <span>Nyaya AI Legal Workspace</span>
            <span>Statutory Grounded RAG</span>
          </div>
        </div>

      </div>
    </main>
  );
}