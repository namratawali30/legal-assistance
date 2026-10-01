import { useState } from "react";
import { Link, Navigate, useNavigate } from "react-router-dom";
import { registerAccount } from "../api/auth";
import { getApiErrorMessage } from "../api/client";
import { useAuth } from "../auth/AuthContext";

export default function RegisterPage() {
  const { isAuthenticated } = useAuth();
  const navigate = useNavigate();

  const [form, setForm] = useState({
    fullName: "",
    email: "",
    password: "",
    confirmPassword: "",
  });
  const [error, setError] = useState("");
  const [submitting, setSubmitting] = useState(false);

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

    if (form.password !== form.confirmPassword) {
      setError("The passwords do not match.");
      return;
    }
    if (form.password.length < 8) {
      setError("Password must be at least 8 characters.");
      return;
    }

    setSubmitting(true);
    try {
      await registerAccount({
        fullName: form.fullName.trim(),
        email: form.email.trim(),
        password: form.password,
      });
      navigate("/login", { replace: true, state: { registered: true } });
    } catch (requestError) {
      setError(getApiErrorMessage(requestError, "Could not create the account."));
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <main className="min-h-screen w-full bg-[#F7F6F2] flex items-center justify-center p-4 sm:p-6 lg:p-0">
      <div className="w-full max-w-6xl min-h-[660px] bg-white rounded-3xl border border-slate-200 shadow-xl overflow-hidden grid lg:grid-cols-12 my-auto">
        
        {/* ── Left Column: Form Panel ── */}
        <div className="lg:col-span-6 p-8 sm:p-12 flex flex-col justify-between">
          <div>
            {/* Brand Header */}
            <div className="flex items-center gap-3 mb-6">
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
            <div className="mb-6">
              <h1 className="text-2xl sm:text-3xl font-bold text-slate-900 font-serif-title tracking-tight">
                Create your account
              </h1>
              <p className="mt-1.5 text-sm text-slate-600">
                Your chats, evidence vault, and formal complaints are securely linked to your account.
              </p>
            </div>

            {/* Form */}
            <form className="space-y-4" onSubmit={handleSubmit} noValidate>
              {/* Full Name */}
              <div>
                <label htmlFor="fullName" className="block text-xs font-semibold uppercase tracking-wider text-slate-700 mb-1">
                  Full name
                </label>
                <input
                  id="fullName"
                  name="fullName"
                  type="text"
                  required
                  autoComplete="name"
                  value={form.fullName}
                  onChange={updateField}
                  className="form-input-legal min-h-[44px]"
                  placeholder="Priya Sharma"
                  aria-invalid={Boolean(error)}
                  aria-describedby={error ? "register-error" : undefined}
                />
              </div>

              {/* Email Address */}
              <div>
                <label htmlFor="email" className="block text-xs font-semibold uppercase tracking-wider text-slate-700 mb-1">
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
                  className="form-input-legal min-h-[44px]"
                  placeholder="you@example.com"
                  aria-invalid={Boolean(error)}
                  aria-describedby={error ? "register-error" : undefined}
                />
              </div>

              {/* Password */}
              <div>
                <label htmlFor="password" className="block text-xs font-semibold uppercase tracking-wider text-slate-700 mb-1">
                  Password <span className="text-slate-400 font-normal lowercase">(min 8 chars)</span>
                </label>
                <input
                  id="password"
                  name="password"
                  type="password"
                  required
                  autoComplete="new-password"
                  value={form.password}
                  onChange={updateField}
                  className="form-input-legal min-h-[44px]"
                  placeholder="Create a strong password"
                  aria-invalid={Boolean(error)}
                  aria-describedby={error ? "register-error" : undefined}
                />
              </div>

              {/* Confirm Password */}
              <div>
                <label htmlFor="confirmPassword" className="block text-xs font-semibold uppercase tracking-wider text-slate-700 mb-1">
                  Confirm password
                </label>
                <input
                  id="confirmPassword"
                  name="confirmPassword"
                  type="password"
                  required
                  autoComplete="new-password"
                  value={form.confirmPassword}
                  onChange={updateField}
                  className="form-input-legal min-h-[44px]"
                  placeholder="Repeat your password"
                  aria-invalid={Boolean(error)}
                  aria-describedby={error ? "register-error" : undefined}
                />
              </div>

              {/* Error Alert */}
              {error && (
                <div id="register-error" role="alert" className="rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-xs font-semibold text-red-800 flex items-start gap-2">
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
                className="btn-teal w-full py-3 text-sm font-semibold shadow-sm mt-2 transition-all"
              >
                {submitting ? (
                  <>
                    <span className="h-4 w-4 rounded-full border-2 border-white border-t-transparent animate-spin-smooth" />
                    Creating account…
                  </>
                ) : (
                  "Create account"
                )}
              </button>
            </form>
          </div>

          <p className="mt-6 text-center text-xs font-medium text-slate-600">
            Already registered?{" "}
            <Link
              to="/login"
              className="font-bold text-teal-700 hover:text-teal-800 underline transition-colors"
            >
              Sign in
            </Link>
          </p>
        </div>

        {/* ── Right Column: Deep Navy Visual Panel ── */}
        <div className="hidden lg:col-span-6 bg-slate-900 text-white p-12 lg:flex flex-col justify-between relative overflow-hidden">
          {/* Background subtle SVG pattern */}
          <div className="absolute inset-0 opacity-10 pointer-events-none">
            <svg width="100%" height="100%" xmlns="http://www.w3.org/2000/svg">
              <defs>
                <pattern id="grid-pattern-reg" width="40" height="40" patternUnits="userSpaceOnUse">
                  <path d="M 40 0 L 0 0 0 40" fill="none" stroke="#FFFFFF" strokeWidth="0.5" />
                </pattern>
              </defs>
              <rect width="100%" height="100%" fill="url(#grid-pattern-reg)" />
            </svg>
          </div>

          <div className="relative z-10">
            <span className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-teal-900/60 border border-teal-700/60 text-teal-300 text-xs font-semibold">
              <span className="h-2 w-2 rounded-full bg-teal-400" />
              Private & Encrypted Workspace
            </span>
          </div>

          {/* Layered Document Composition Variation */}
          <div className="relative z-10 my-auto py-8">
            <div className="relative mx-auto max-w-sm">
              {/* Back Card */}
              <div className="absolute inset-0 rotate-6 rounded-2xl bg-teal-950/80 border border-teal-800/60 p-6 shadow-lg transform transition-transform" />
              {/* Middle Card */}
              <div className="absolute inset-0 -rotate-3 rounded-2xl bg-slate-800/70 border border-slate-700/60 p-6 shadow-xl transform transition-transform" />
              {/* Front Card */}
              <div className="relative rounded-2xl bg-slate-850 border border-slate-700 p-7 shadow-2xl space-y-4">
                <div className="flex items-center justify-between border-b border-slate-700/80 pb-3">
                  <div className="flex items-center gap-2 text-xs font-mono text-teal-400">
                    <span className="h-2 w-2 rounded-full bg-teal-400" />
                    ACCOUNT_REGISTERED #NYAYA
                  </div>
                  <span className="text-[10px] uppercase font-bold text-slate-400">Grounded</span>
                </div>
                <div className="space-y-2">
                  <div className="h-2.5 w-2/3 rounded bg-slate-700" />
                  <div className="h-2 w-full rounded bg-slate-800" />
                  <div className="h-2 w-4/5 rounded bg-slate-800" />
                </div>
                <div className="pt-2 flex items-center justify-between text-xs text-slate-300">
                  <span>SHA-256 Fingerprint Vault</span>
                  <span className="text-teal-400 font-mono">Protected ✓</span>
                </div>
              </div>
            </div>

            <div className="mt-10 text-center">
              <h2 className="text-2xl font-bold font-serif-title tracking-tight text-white">
                “Complex information becomes clear.”
              </h2>
              <p className="mt-3 text-xs text-slate-400 leading-5 max-w-sm mx-auto">
                Grounded statutory explanations, organized case evidence, and clean complaint exporting built for clarity and speed.
              </p>
            </div>
          </div>

          <div className="relative z-10 flex items-center justify-between text-xs text-slate-400 border-t border-slate-800 pt-4">
            <span>Nyaya AI Legal Workspace</span>
            <span>Indian Law Grounded</span>
          </div>
        </div>

      </div>
    </main>
  );
}