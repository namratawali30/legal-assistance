import { useState } from "react";
import { getApiErrorMessage } from "../../api/client";

const CATEGORIES = [
  { value: "consumer_rights",    label: "Consumer Rights",    emoji: "🛒" },
  { value: "labour_rights",      label: "Labour Rights",      emoji: "⚖️" },
  { value: "womens_safety",      label: "Women's Safety",     emoji: "🛡️" },
  { value: "educational_rights", label: "Educational Rights", emoji: "🎓" },
  { value: "anti_ragging",       label: "Anti-Ragging",       emoji: "🚫" },
];

function SectionCard({ title, icon, children }) {
  return (
    <div className="card-legal overflow-hidden">
      <div className="flex items-center gap-2.5 border-b border-slate-100 px-5 py-3.5 bg-slate-50/70">
        <span className="text-base">{icon}</span>
        <h3 className="text-sm font-semibold text-slate-800 font-serif-title">{title}</h3>
      </div>
      <div className="p-5 space-y-4">{children}</div>
    </div>
  );
}

function Field({ id, label, required, children, hint }) {
  return (
    <div>
      <label htmlFor={id} className="block text-xs font-semibold uppercase tracking-wider text-slate-700 mb-1.5">
        {label}
        {required && <span className="ml-1 text-red-600" aria-hidden="true">*</span>}
      </label>
      {children}
      {hint && <p className="mt-1.5 text-xs text-slate-500">{hint}</p>}
    </div>
  );
}

function Input({ id, value, onChange, disabled, placeholder, type = "text", maxLength }) {
  return (
    <input
      id={id}
      type={type}
      value={value ?? ""}
      onChange={(e) => onChange(e.target.value)}
      disabled={disabled}
      placeholder={placeholder}
      maxLength={maxLength}
      className="form-input-legal min-h-[44px]"
    />
  );
}

function Textarea({ id, value, onChange, disabled, placeholder, rows = 4, maxLength }) {
  return (
    <textarea
      id={id}
      value={value ?? ""}
      onChange={(e) => onChange(e.target.value)}
      disabled={disabled}
      placeholder={placeholder}
      rows={rows}
      maxLength={maxLength}
      className="form-input-legal min-h-[44px] resize-none"
    />
  );
}

function Select({ id, value, onChange, disabled, options }) {
  return (
    <select
      id={id}
      value={value ?? ""}
      onChange={(e) => onChange(e.target.value)}
      disabled={disabled}
      className="form-input-legal min-h-[44px] bg-white"
    >
      <option value="">Select a legal category</option>
      {options.map((opt) => (
        <option key={opt.value} value={opt.value}>
          {opt.emoji} {opt.label}
        </option>
      ))}
    </select>
  );
}

export default function ComplaintEditor({
  complaint,
  onSave,
  onCancel,
  isCreating = false,
  saveHandler,
}) {
  const isFinalized = complaint?.status === "finalized";
  const isReadOnly  = isFinalized;

  const [fields, setFields] = useState({
    title:               complaint?.title               ?? "",
    category:            complaint?.category            ?? "",
    complainant_name:    complaint?.complainant_name    ?? "",
    complainant_address: complaint?.complainant_address ?? "",
    complainant_contact: complaint?.complainant_contact ?? "",
    respondent_name:     complaint?.respondent_name     ?? "",
    respondent_address:  complaint?.respondent_address  ?? "",
    incident_date:       complaint?.incident_date       ?? "",
    incident_location:   complaint?.incident_location   ?? "",
    facts:               complaint?.facts               ?? "",
    relief_requested:    complaint?.relief_requested    ?? "",
  });

  const [saving, setSaving] = useState(false);
  const [error,  setError]  = useState(null);
  const [dirty,  setDirty]  = useState(false);

  function update(key, value) {
    setFields((prev) => ({ ...prev, [key]: value }));
    setDirty(true);
    setError(null);
  }

  async function handleSubmit(e) {
    e.preventDefault();
    if (isReadOnly) return;

    if (!fields.title.trim()) {
      setError("Title is required."); return;
    }
    if (!fields.category) {
      setError("Please select a legal category."); return;
    }
    if (!fields.complainant_name.trim()) {
      setError("Complainant name is required."); return;
    }
    if (!fields.respondent_name.trim()) {
      setError("Respondent name is required."); return;
    }
    if (fields.facts.trim().length < 20) {
      setError("Facts description must be at least 20 characters."); return;
    }

    setSaving(true);
    setError(null);

    try {
      const result = await saveHandler({
        title:               fields.title.trim(),
        category:            fields.category,
        complainant_name:    fields.complainant_name.trim(),
        complainant_address: fields.complainant_address.trim() || null,
        complainant_contact: fields.complainant_contact.trim() || null,
        respondent_name:     fields.respondent_name.trim(),
        respondent_address:  fields.respondent_address.trim() || null,
        incident_date:       fields.incident_date || null,
        incident_location:   fields.incident_location.trim() || null,
        facts:               fields.facts.trim(),
        relief_requested:    fields.relief_requested.trim() || null,
      });

      setDirty(false);
      onSave(result);
    } catch (err) {
      setError(getApiErrorMessage(err, "Could not save complaint."));
    } finally {
      setSaving(false);
    }
  }

  return (
    <form onSubmit={handleSubmit} noValidate>
      <div className="space-y-4">

        {/* ── Identification ── */}
        <SectionCard title="Complaint identification" icon="📋">
          <Field id="field-title" label="Title" required>
            <Input
              id="field-title"
              value={fields.title}
              onChange={(v) => update("title", v)}
              disabled={isReadOnly || saving}
              placeholder="Brief description of your complaint"
              maxLength={200}
            />
          </Field>

          <Field id="field-category" label="Legal category" required>
            <Select
              id="field-category"
              value={fields.category}
              onChange={(v) => update("category", v)}
              disabled={isReadOnly || saving || !isCreating}
              options={CATEGORIES}
            />
            {!isCreating && (
              <p className="mt-1.5 text-xs text-slate-400">
                Category cannot be changed after creation.
              </p>
            )}
          </Field>
        </SectionCard>

        {/* ── Complainant ── */}
        <SectionCard title="Complainant (you)" icon="👤">
          <Field id="field-complainant-name" label="Full name" required>
            <Input
              id="field-complainant-name"
              value={fields.complainant_name}
              onChange={(v) => update("complainant_name", v)}
              disabled={isReadOnly || saving}
              placeholder="Your full legal name"
              maxLength={150}
            />
          </Field>

          <Field id="field-complainant-address" label="Address">
            <Textarea
              id="field-complainant-address"
              value={fields.complainant_address}
              onChange={(v) => update("complainant_address", v)}
              disabled={isReadOnly || saving}
              placeholder="Your postal address"
              rows={2}
              maxLength={1000}
            />
          </Field>

          <Field id="field-complainant-contact" label="Contact" hint="Phone number or email">
            <Input
              id="field-complainant-contact"
              value={fields.complainant_contact}
              onChange={(v) => update("complainant_contact", v)}
              disabled={isReadOnly || saving}
              placeholder="e.g. +91 9876543210"
              maxLength={100}
            />
          </Field>
        </SectionCard>

        {/* ── Respondent ── */}
        <SectionCard title="Respondent (party against whom complaint is made)" icon="🏢">
          <Field id="field-respondent-name" label="Name" required>
            <Input
              id="field-respondent-name"
              value={fields.respondent_name}
              onChange={(v) => update("respondent_name", v)}
              disabled={isReadOnly || saving}
              placeholder="Individual or organisation name"
              maxLength={200}
            />
          </Field>

          <Field id="field-respondent-address" label="Address">
            <Textarea
              id="field-respondent-address"
              value={fields.respondent_address}
              onChange={(v) => update("respondent_address", v)}
              disabled={isReadOnly || saving}
              placeholder="Respondent's address"
              rows={2}
              maxLength={1000}
            />
          </Field>
        </SectionCard>

        {/* ── Incident details ── */}
        <SectionCard title="Incident details" icon="📅">
          <div className="grid gap-4 sm:grid-cols-2">
            <Field id="field-incident-date" label="Incident date">
              <Input
                id="field-incident-date"
                type="date"
                value={fields.incident_date}
                onChange={(v) => update("incident_date", v)}
                disabled={isReadOnly || saving}
              />
            </Field>

            <Field id="field-incident-location" label="Location">
              <Input
                id="field-incident-location"
                value={fields.incident_location}
                onChange={(v) => update("incident_location", v)}
                disabled={isReadOnly || saving}
                placeholder="City, state, or address"
                maxLength={500}
              />
            </Field>
          </div>

          <Field
            id="field-facts"
            label="Facts"
            required
            hint="Describe what happened clearly and chronologically. Include key dates, amounts, and actions taken."
          >
            <Textarea
              id="field-facts"
              value={fields.facts}
              onChange={(v) => update("facts", v)}
              disabled={isReadOnly || saving}
              placeholder="Describe the events in detail — include names, dates, amounts, and any steps already taken…"
              rows={7}
              maxLength={15000}
            />
            <div className="flex justify-end mt-1">
              <span
                className={`text-xs ${
                  fields.facts.length > 14000 ? "text-red-500" : "text-slate-400"
                }`}
              >
                {fields.facts.length.toLocaleString()} / 15,000
              </span>
            </div>
          </Field>

          <Field
            id="field-relief"
            label="Relief requested"
            hint="What outcome are you seeking? (e.g. refund, compensation, action against respondent)"
          >
            <Textarea
              id="field-relief"
              value={fields.relief_requested}
              onChange={(v) => update("relief_requested", v)}
              disabled={isReadOnly || saving}
              placeholder="Describe the relief or remedy you are seeking…"
              rows={3}
              maxLength={5000}
            />
          </Field>
        </SectionCard>

        {/* Error Alert */}
        {error && (
          <div
            role="alert"
            className="flex items-start gap-2.5 rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm font-semibold text-red-800"
          >
            <svg className="h-4 w-4 flex-shrink-0 mt-0.5 text-red-600" viewBox="0 0 20 20" fill="currentColor">
              <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.28 7.22a.75.75 0 00-1.06 1.06L8.94 10l-1.72 1.72a.75.75 0 101.06 1.06L10 11.06l1.72 1.72a.75.75 0 101.06-1.06L11.06 10l1.72-1.72a.75.75 0 00-1.06-1.06L10 8.94 6.28 5.22z" clipRule="evenodd" />
            </svg>
            {error}
          </div>
        )}

        {/* Actions */}
        {!isReadOnly && (
          <div className="flex items-center gap-3 pt-2">
            <button
              type="submit"
              disabled={saving || (!isCreating && !dirty)}
              className="btn-teal shadow-2xs py-2.5 px-5"
              id="complaint-save-btn"
            >
              {saving ? (
                <>
                  <span className="h-3.5 w-3.5 rounded-full border-2 border-white border-t-transparent animate-spin-smooth" />
                  Saving…
                </>
              ) : isCreating ? (
                "Create complaint"
              ) : (
                "Save changes"
              )}
            </button>

            {isCreating && onCancel && (
              <button
                type="button"
                onClick={onCancel}
                disabled={saving}
                className="btn-outline-legal py-2.5 px-5"
              >
                Cancel
              </button>
            )}
          </div>
        )}

        {/* Finalized notice */}
        {isReadOnly && (
          <div className="flex items-center gap-3 rounded-xl border border-teal-200 bg-teal-50 px-4 py-3.5 text-xs text-teal-900">
            <svg className="h-4 w-4 flex-shrink-0 text-teal-700" viewBox="0 0 20 20" fill="currentColor">
              <path fillRule="evenodd" d="M10 1a4.5 4.5 0 00-4.5 4.5V9H5a2 2 0 00-2 2v6a2 2 0 002 2h10a2 2 0 002-2v-6a2 2 0 00-2-2h-.5V5.5A4.5 4.5 0 0010 1zm3 8V5.5a3 3 0 10-6 0V9h6z" clipRule="evenodd" />
            </svg>
            <div>
              <p className="font-bold">Complaint finalized</p>
              <p className="text-slate-700 mt-0.5">
                This complaint is locked and cannot be edited. Export as PDF or DOCX using the header controls.
              </p>
            </div>
          </div>
        )}
      </div>
    </form>
  );
}
