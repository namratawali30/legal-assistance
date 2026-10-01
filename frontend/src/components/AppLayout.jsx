import { useState } from "react";
import { NavLink, Outlet } from "react-router-dom";
import { useAuth } from "../auth/AuthContext";
import { useFocusTrap } from "../hooks/useFocusTrap";

// ─────────────────────────────────────────────
// Icon components (inline SVG — no extra deps)
// ─────────────────────────────────────────────

function IconGrid(props) {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.75} strokeLinecap="round" strokeLinejoin="round" {...props}>
      <rect x="3" y="3" width="7" height="7" rx="1.5" />
      <rect x="14" y="3" width="7" height="7" rx="1.5" />
      <rect x="3" y="14" width="7" height="7" rx="1.5" />
      <rect x="14" y="14" width="7" height="7" rx="1.5" />
    </svg>
  );
}

function IconChat(props) {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.75} strokeLinecap="round" strokeLinejoin="round" {...props}>
      <path d="M21 15a2 2 0 01-2 2H7l-4 4V5a2 2 0 012-2h14a2 2 0 012 2z" />
    </svg>
  );
}

function IconDocument(props) {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.75} strokeLinecap="round" strokeLinejoin="round" {...props}>
      <path d="M14 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V8z" />
      <path d="M14 2v6h6M16 13H8M16 17H8M10 9H8" />
    </svg>
  );
}

function IconShield(props) {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.75} strokeLinecap="round" strokeLinejoin="round" {...props}>
      <path d="M12 2l7 3v5c0 5-3.5 9.74-7 11C8.5 19.74 5 15 5 10V5l7-3z" />
    </svg>
  );
}

function IconLogout(props) {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.75} strokeLinecap="round" strokeLinejoin="round" {...props}>
      <path d="M9 21H5a2 2 0 01-2-2V5a2 2 0 012-2h4M16 17l5-5-5-5M21 12H9" />
    </svg>
  );
}

function IconMenu(props) {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2} strokeLinecap="round" strokeLinejoin="round" {...props}>
      <path d="M4 6h16M4 12h16M4 18h16" />
    </svg>
  );
}

function IconClose(props) {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2} strokeLinecap="round" strokeLinejoin="round" {...props}>
      <path d="M18 6L6 18M6 6l12 12" />
    </svg>
  );
}

function IconScalesOfJustice(props) {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.75} strokeLinecap="round" strokeLinejoin="round" {...props}>
      <path d="M12 3v17M4 7h16M4 7l-2 6h6L6 7M20 7l-2 6h6L20 7M9 20h6" />
    </svg>
  );
}

// ─────────────────────────────────────────────
// Nav items config
// ─────────────────────────────────────────────

const NAV_ITEMS = [
  { to: "/",          end: true,  label: "Dashboard",     Icon: IconGrid     },
  { to: "/cases",     end: false, label: "Cases & Matters", Icon: IconScalesOfJustice },
  { to: "/chat",      end: false, label: "Legal Chat",    Icon: IconChat     },
  { to: "/complaints",end: false, label: "Complaints",    Icon: IconDocument },
  { to: "/evidence",  end: false, label: "Evidence Vault",Icon: IconShield   },
];

// ─────────────────────────────────────────────
// Sidebar content
// ─────────────────────────────────────────────

function SidebarContent({ user, logout, onNavClick }) {
  return (
    <div className="flex h-full flex-col justify-between bg-slate-900 text-slate-100">
      <div>
        {/* Brand Header */}
        <div className="px-5 pt-6 pb-5 border-b border-slate-800">
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-teal-700 text-white shadow-sm flex-shrink-0">
              <IconScalesOfJustice className="h-5 w-5 text-white" aria-hidden="true" />
            </div>
            <div className="min-w-0">
              <p className="text-base font-bold text-white tracking-tight font-serif-title">
                Nyaya AI
              </p>
              <p className="text-xs text-teal-400 font-medium truncate">Legal Workspace</p>
            </div>
          </div>
        </div>

        {/* Navigation */}
        <nav aria-label="Main Navigation" className="px-3 py-5 space-y-1">
          <p className="px-3 mb-2 text-[11px] font-bold uppercase tracking-wider text-slate-400">
            Workspace Navigation
          </p>
          {NAV_ITEMS.map(({ to, end, label, Icon }) => (
            <NavLink
              key={to}
              to={to}
              end={end}
              onClick={onNavClick}
              className={({ isActive }) =>
                [
                  "flex items-center gap-3 rounded-xl px-3.5 py-2.5 text-sm font-medium transition-colors focus:outline-none focus:ring-2 focus:ring-teal-400 min-h-[44px]",
                  isActive
                    ? "bg-slate-800 text-white font-semibold border-l-4 border-teal-500"
                    : "text-slate-300 hover:text-white hover:bg-slate-800/60",
                ].join(" ")
              }
            >
              {({ isActive }) => (
                <>
                  <span
                    className={[
                      "flex h-7 w-7 items-center justify-center rounded-lg flex-shrink-0 transition-colors",
                      isActive ? "text-teal-400" : "text-slate-400",
                    ].join(" ")}
                  >
                    <Icon className="h-4.5 w-4.5" aria-hidden="true" />
                  </span>
                  <span>{label}</span>
                </>
              )}
            </NavLink>
          ))}
        </nav>
      </div>

      <div>
        {/* Grounding Badge */}
        <div className="mx-3.5 mb-4 p-3 rounded-xl bg-slate-850 border border-slate-800 text-xs text-slate-300 leading-5">
          <div className="flex items-center gap-1.5 font-semibold text-teal-400 mb-1">
            <svg className="h-3.5 w-3.5" viewBox="0 0 20 20" fill="currentColor">
              <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.857-9.809a.75.75 0 00-1.214-.882l-3.483 4.79-1.88-1.88a.75.75 0 10-1.06 1.061l2.5 2.5a.75.75 0 001.137-.089l4-5.5z" clipRule="evenodd" />
            </svg>
            Statutory RAG Grounded
          </div>
          Grounded in verified Indian law statutes and evidence fingerprints.
        </div>

        {/* User profile & logout */}
        <div className="border-t border-slate-800 px-3.5 py-4">
          <div className="flex items-center gap-3 px-2 mb-3">
            <div
              className="flex h-8 w-8 items-center justify-center rounded-full bg-teal-800 text-white font-bold text-xs shadow-sm flex-shrink-0"
              aria-hidden="true"
            >
              {user?.full_name?.[0]?.toUpperCase() || "U"}
            </div>
            <div className="min-w-0">
              <p className="truncate text-sm font-semibold text-white">{user?.full_name}</p>
              <p className="truncate text-xs text-slate-400">{user?.email}</p>
            </div>
          </div>

          <button
            type="button"
            onClick={logout}
            className="flex items-center gap-3 w-full rounded-xl px-3.5 py-2.5 text-sm font-medium text-red-400 hover:text-red-300 hover:bg-red-500/10 transition-colors min-h-[44px] cursor-pointer focus:outline-none focus:ring-2 focus:ring-red-400"
            aria-label="Sign out of account"
          >
            <IconLogout className="h-4 w-4" aria-hidden="true" />
            <span>Sign out</span>
          </button>
        </div>
      </div>
    </div>
  );
}

// ─────────────────────────────────────────────
// AppLayout Component
// ─────────────────────────────────────────────

export default function AppLayout() {
  const { user, logout } = useAuth();
  const [mobileOpen, setMobileOpen] = useState(false);
  const drawerRef = useFocusTrap(mobileOpen, () => setMobileOpen(false));

  return (
    <div className="min-h-screen bg-[#F7F6F2] lg:flex">
      {/* Skip Link for Keyboard Accessibility */}
      <a href="#main-content" className="skip-link">
        Skip to main content
      </a>

      {/* ── Desktop sidebar ── */}
      <aside
        aria-label="Sidebar Navigation"
        className="hidden lg:fixed lg:inset-y-0 lg:flex lg:flex-col border-r border-slate-800 shadow-md z-30"
        style={{ width: "var(--sidebar-width)" }}
      >
        <SidebarContent user={user} logout={logout} />
      </aside>

      {/* ── Mobile top bar ── */}
      <header className="bg-slate-900 text-white sticky top-0 z-40 flex items-center justify-between px-4 py-3 lg:hidden border-b border-slate-800 shadow-sm">
        <div className="flex items-center gap-2.5">
          <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-teal-700 text-white">
            <IconScalesOfJustice className="h-4.5 w-4.5" aria-hidden="true" />
          </div>
          <span className="text-base font-bold text-white font-serif-title tracking-tight">
            Nyaya AI
          </span>
        </div>
        <button
          type="button"
          onClick={() => setMobileOpen(true)}
          className="rounded-lg p-2 text-slate-300 hover:text-white hover:bg-slate-800 transition-colors min-h-[44px] min-w-[44px] flex items-center justify-center"
          aria-label="Open main menu"
          aria-expanded={mobileOpen}
          aria-controls="mobile-navigation-drawer"
        >
          <IconMenu className="h-6 w-6" aria-hidden="true" />
        </button>
      </header>

      {/* ── Mobile drawer overlay ── */}
      {mobileOpen && (
        <div
          id="mobile-navigation-drawer"
          className="fixed inset-0 z-50 lg:hidden"
          aria-modal="true"
          role="dialog"
          aria-label="Mobile Navigation Menu"
        >
          {/* Backdrop */}
          <div
            className="absolute inset-0 bg-slate-950/70 backdrop-blur-xs animate-fade-in"
            onClick={() => setMobileOpen(false)}
          />
          {/* Drawer */}
          <div
            ref={drawerRef}
            tabIndex={-1}
            className="absolute inset-y-0 left-0 animate-slide-left outline-none shadow-2xl bg-slate-900"
            style={{ width: "var(--sidebar-width)" }}
          >
            <div className="flex items-center justify-between px-5 pt-5 pb-4 border-b border-slate-800">
              <span className="text-base font-bold text-white font-serif-title">
                Nyaya AI
              </span>
              <button
                type="button"
                onClick={() => setMobileOpen(false)}
                className="rounded-lg p-2 text-slate-400 hover:text-white hover:bg-slate-800 min-h-[44px] min-w-[44px] flex items-center justify-center"
                aria-label="Close navigation menu"
              >
                <IconClose className="h-5 w-5" aria-hidden="true" />
              </button>
            </div>
            <SidebarContent
              user={user}
              logout={logout}
              onNavClick={() => setMobileOpen(false)}
            />
          </div>
        </div>
      )}

      {/* ── Main content ── */}
      <main
        id="main-content"
        tabIndex={-1}
        className="min-w-0 flex-1 lg:ml-[var(--sidebar-width)] outline-none bg-[#F7F6F2]"
      >
        <Outlet />
      </main>
    </div>
  );
}