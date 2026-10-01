import React, { useState, useEffect } from "react";
import { fetchCases, createCase, recordCaseSubmission, addCaseReminder } from "../api/cases";

export default function CasesPage() {
  const [cases, setCases] = useState([]);
  const [selectedCase, setSelectedCase] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [showIntakeModal, setShowIntakeModal] = useState(false);
  const [showSubmissionModal, setShowSubmissionModal] = useState(false);
  const [showReminderModal, setShowReminderModal] = useState(false);

  // Form states
  const [newTitle, setNewTitle] = useState("");
  const [complainantName, setComplainantName] = useState("");
  const [oppositeParty, setOppositeParty] = useState("");
  const [incidentDate, setIncidentDate] = useState("");
  const [location, setLocation] = useState("");
  const [amount, setAmount] = useState("");
  const [desiredOutcome, setDesiredOutcome] = useState("");

  // Submission state
  const [authorityName, setAuthorityName] = useState("");
  const [submissionDate, setSubmissionDate] = useState("");
  const [refNumber, setRefNumber] = useState("");
  const [subNotes, setSubNotes] = useState("");

  // Reminder state
  const [reminderTitle, setReminderTitle] = useState("");
  const [dueDate, setDueDate] = useState("");

  useEffect(() => {
    loadCases();
  }, []);

  async function loadCases() {
    setLoading(true);
    try {
      const data = await fetchCases();
      setCases(data);
      if (data.length > 0 && !selectedCase) {
        setSelectedCase(data[0]);
      }
    } catch (err) {
      setError("Failed to load cases.");
    } finally {
      setLoading(false);
    }
  }

  async function handleCreateCase(e) {
    e.preventDefault();
    try {
      const payload = {
        title: newTitle || "New Consumer Matter",
        category: "consumer_rights",
        intake_facts: {
          complainant_name: complainantName,
          opposite_party_name: oppositeParty,
          incident_date: incidentDate,
          incident_location: location,
          transaction_amount: parseFloat(amount) || 0,
          desired_outcome: desiredOutcome,
        },
      };
      const created = await createCase(payload);
      setCases([created, ...cases]);
      setSelectedCase(created);
      setShowIntakeModal(false);
      resetIntakeForm();
    } catch (err) {
      alert("Error creating case intake.");
    }
  }

  async function handleRecordSubmission(e) {
    e.preventDefault();
    if (!selectedCase) return;
    try {
      const payload = {
        authority_name: authorityName,
        submission_date: submissionDate,
        reference_number: refNumber,
        notes: subNotes,
        acknowledged_by_user: true,
      };
      const updated = await recordCaseSubmission(selectedCase.id, payload);
      setSelectedCase(updated);
      setCases(cases.map(c => c.id === updated.id ? updated : c));
      setShowSubmissionModal(false);
    } catch (err) {
      alert("Failed to record submission acknowledgment.");
    }
  }

  async function handleAddReminder(e) {
    e.preventDefault();
    if (!selectedCase) return;
    try {
      const payload = {
        title: reminderTitle,
        due_date: dueDate,
        status: "pending",
      };
      const updated = await addCaseReminder(selectedCase.id, payload);
      setSelectedCase(updated);
      setShowReminderModal(false);
    } catch (err) {
      alert("Failed to add reminder.");
    }
  }

  function resetIntakeForm() {
    setNewTitle("");
    setComplainantName("");
    setOppositeParty("");
    setIncidentDate("");
    setLocation("");
    setAmount("");
    setDesiredOutcome("");
  }

  if (loading) return <div className="p-8 text-center text-gray-600">Loading Case Workspace...</div>;

  return (
    <div className="max-w-7xl mx-auto p-6 space-y-6">
      <div className="flex justify-between items-center bg-white p-6 rounded-xl shadow-sm border border-gray-100">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Case & Matter Workspace</h1>
          <p className="text-sm text-gray-500">Guided consumer complaint preparation, evidence linkage, and filing tracking</p>
        </div>
        <button
          onClick={() => setShowIntakeModal(true)}
          className="px-4 py-2 bg-indigo-600 hover:bg-indigo-700 text-white font-medium rounded-lg shadow-sm transition"
        >
          + New Guided Case Intake
        </button>
      </div>

      {cases.length === 0 ? (
        <div className="bg-white p-12 text-center rounded-xl border border-dashed border-gray-300">
          <h3 className="text-lg font-semibold text-gray-700">No active cases found</h3>
          <p className="text-sm text-gray-500 mt-1">Start by launching a guided intake to structure your facts and evidence.</p>
          <button
            onClick={() => setShowIntakeModal(true)}
            className="mt-4 px-5 py-2.5 bg-indigo-600 text-white rounded-lg font-medium shadow"
          >
            Create Your First Case
          </button>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          {/* Cases List Sidebar */}
          <div className="bg-white p-4 rounded-xl border border-gray-200 shadow-sm space-y-3">
            <h2 className="text-base font-semibold text-gray-800 px-2">Your Matters</h2>
            <div className="space-y-2">
              {cases.map((c) => (
                <div
                  key={c.id}
                  onClick={() => setSelectedCase(c)}
                  className={`p-3.5 rounded-lg cursor-pointer transition border ${
                    selectedCase?.id === c.id
                      ? "border-indigo-500 bg-indigo-50/50"
                      : "border-gray-100 hover:bg-gray-50"
                  }`}
                >
                  <div className="font-semibold text-gray-900 text-sm">{c.title}</div>
                  <div className="flex justify-between items-center mt-2 text-xs text-gray-500">
                    <span className="capitalize px-2 py-0.5 bg-gray-100 rounded text-gray-700">{c.status}</span>
                    <span>{new Date(c.updated_at).toLocaleDateString()}</span>
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Case Detail Workspace */}
          {selectedCase && (
            <div className="md:col-span-2 space-y-6">
              <div className="bg-white p-6 rounded-xl border border-gray-200 shadow-sm space-y-4">
                <div className="flex justify-between items-start border-b pb-4">
                  <div>
                    <h2 className="text-xl font-bold text-gray-900">{selectedCase.title}</h2>
                    <span className="inline-block mt-1 px-2.5 py-0.5 bg-indigo-100 text-indigo-800 text-xs font-semibold rounded-full uppercase">
                      {selectedCase.category.replace("_", " ")}
                    </span>
                  </div>
                  <div className="space-x-2">
                    <button
                      onClick={() => setShowSubmissionModal(true)}
                      className="px-3 py-1.5 text-xs bg-emerald-600 hover:bg-emerald-700 text-white font-medium rounded shadow-sm"
                    >
                      Record Filing Acknowledgment
                    </button>
                    <button
                      onClick={() => setShowReminderModal(true)}
                      className="px-3 py-1.5 text-xs bg-gray-800 hover:bg-gray-900 text-white font-medium rounded shadow-sm"
                    >
                      + Add Follow-up
                    </button>
                  </div>
                </div>

                {/* Intake Facts Grid */}
                <div>
                  <h3 className="text-sm font-semibold text-gray-800 mb-2">Structured Intake Facts</h3>
                  <div className="grid grid-cols-2 gap-4 bg-gray-50 p-4 rounded-lg text-sm">
                    <div><span className="font-medium text-gray-500">Complainant:</span> {selectedCase.intake_facts?.complainant_name || "N/A"}</div>
                    <div><span className="font-medium text-gray-500">Opposite Party:</span> {selectedCase.intake_facts?.opposite_party_name || "N/A"}</div>
                    <div><span className="font-medium text-gray-500">Incident Date:</span> {selectedCase.intake_facts?.incident_date || "N/A"}</div>
                    <div><span className="font-medium text-gray-500">Location:</span> {selectedCase.intake_facts?.incident_location || "N/A"}</div>
                    <div><span className="font-medium text-gray-500">Amount Involved:</span> ₹{selectedCase.intake_facts?.transaction_amount || "0"}</div>
                    <div><span className="font-medium text-gray-500">Desired Relief:</span> {selectedCase.intake_facts?.desired_outcome || "N/A"}</div>
                  </div>
                </div>

                {/* Submission Record Status */}
                {selectedCase.submission_record ? (
                  <div className="bg-emerald-50 border border-emerald-200 p-4 rounded-lg text-sm text-emerald-900">
                    <div className="font-bold text-emerald-800">Recorded Submission Acknowledgment</div>
                    <div className="mt-1">Authority: {selectedCase.submission_record.authority_name}</div>
                    <div>Date: {selectedCase.submission_record.submission_date} | Reference No: {selectedCase.submission_record.reference_number || "N/A"}</div>
                  </div>
                ) : (
                  <div className="bg-amber-50 border border-amber-200 p-3 rounded-lg text-xs text-amber-800">
                    Status: Finalized in application, pending user submission to authority.
                  </div>
                )}

                {/* Reminders List */}
                <div>
                  <h3 className="text-sm font-semibold text-gray-800 mb-2">Follow-up Reminders</h3>
                  {selectedCase.reminders?.length === 0 ? (
                    <p className="text-xs text-gray-500 italic">No follow-up reminders added.</p>
                  ) : (
                    <ul className="space-y-2 text-sm">
                      {selectedCase.reminders?.map((r, idx) => (
                        <li key={idx} className="flex justify-between bg-white border p-2.5 rounded shadow-xs">
                          <span className="font-medium text-gray-800">{r.title}</span>
                          <span className="text-xs text-indigo-600 font-semibold">Due: {r.due_date}</span>
                        </li>
                      ))}
                    </ul>
                  )}
                </div>
              </div>
            </div>
          )}
        </div>
      )}

      {/* Intake Modal */}
      {showIntakeModal && (
        <div className="fixed inset-0 bg-black/40 flex items-center justify-center p-4 z-50">
          <form onSubmit={handleCreateCase} className="bg-white rounded-xl max-w-lg w-full p-6 space-y-4 shadow-xl">
            <h3 className="text-lg font-bold text-gray-900">Guided Consumer Intake</h3>
            <div>
              <label className="text-xs font-semibold text-gray-700">Case Title</label>
              <input type="text" required value={newTitle} onChange={e=>setNewTitle(e.target.value)} className="w-full mt-1 p-2 border rounded text-sm" placeholder="e.g. Defective Laptop Complaint" />
            </div>
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="text-xs font-semibold text-gray-700">Complainant Name</label>
                <input type="text" value={complainantName} onChange={e=>setComplainantName(e.target.value)} className="w-full mt-1 p-2 border rounded text-sm" />
              </div>
              <div>
                <label className="text-xs font-semibold text-gray-700">Opposite Party</label>
                <input type="text" value={oppositeParty} onChange={e=>setOppositeParty(e.target.value)} className="w-full mt-1 p-2 border rounded text-sm" />
              </div>
            </div>
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="text-xs font-semibold text-gray-700">Incident Date</label>
                <input type="date" value={incidentDate} onChange={e=>setIncidentDate(e.target.value)} className="w-full mt-1 p-2 border rounded text-sm" />
              </div>
              <div>
                <label className="text-xs font-semibold text-gray-700">Amount (₹)</label>
                <input type="number" value={amount} onChange={e=>setAmount(e.target.value)} className="w-full mt-1 p-2 border rounded text-sm" />
              </div>
            </div>
            <div>
              <label className="text-xs font-semibold text-gray-700">Desired Outcome / Relief</label>
              <textarea value={desiredOutcome} onChange={e=>setDesiredOutcome(e.target.value)} className="w-full mt-1 p-2 border rounded text-sm" rows={2} placeholder="Full refund, replacement, or compensation..." />
            </div>
            <div className="flex justify-end space-x-2 pt-2">
              <button type="button" onClick={() => setShowIntakeModal(false)} className="px-4 py-2 border rounded text-sm text-gray-600">Cancel</button>
              <button type="submit" className="px-4 py-2 bg-indigo-600 text-white rounded text-sm font-medium">Save Case</button>
            </div>
          </form>
        </div>
      )}

      {/* Submission Modal */}
      {showSubmissionModal && (
        <div className="fixed inset-0 bg-black/40 flex items-center justify-center p-4 z-50">
          <form onSubmit={handleRecordSubmission} className="bg-white rounded-xl max-w-md w-full p-6 space-y-4 shadow-xl">
            <h3 className="text-lg font-bold text-gray-900">Record Official Submission Acknowledgment</h3>
            <div>
              <label className="text-xs font-semibold text-gray-700">Authority Name</label>
              <input type="text" required value={authorityName} onChange={e=>setAuthorityName(e.target.value)} className="w-full mt-1 p-2 border rounded text-sm" placeholder="e.g. District Commission, Bengaluru" />
            </div>
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="text-xs font-semibold text-gray-700">Submission Date</label>
                <input type="date" required value={submissionDate} onChange={e=>setSubmissionDate(e.target.value)} className="w-full mt-1 p-2 border rounded text-sm" />
              </div>
              <div>
                <label className="text-xs font-semibold text-gray-700">Reference / Diary No.</label>
                <input type="text" value={refNumber} onChange={e=>setRefNumber(e.target.value)} className="w-full mt-1 p-2 border rounded text-sm" />
              </div>
            </div>
            <div className="flex justify-end space-x-2 pt-2">
              <button type="button" onClick={() => setShowSubmissionModal(false)} className="px-4 py-2 border rounded text-sm text-gray-600">Cancel</button>
              <button type="submit" className="px-4 py-2 bg-emerald-600 text-white rounded text-sm font-medium">Record Submission</button>
            </div>
          </form>
        </div>
      )}
    </div>
  );
}
