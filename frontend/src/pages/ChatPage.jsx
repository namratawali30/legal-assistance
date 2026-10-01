import {
  useEffect,
  useRef,
  useState,
} from "react";

import {
  createChat,
  deleteChat,
  getChat,
  listChats,
  retryChatMessage,
  sendChatMessage,
  updateChat,
} from "../api/chats";

import { getApiErrorMessage } from "../api/client";
import { fetchSessionReadiness } from "../api/readiness";
import { fetchSessionActionPlan } from "../api/actionPlan";
import { fetchSessionLawyerHandoff } from "../api/lawyerHandoff";

import CaseReadinessModal from "../components/CaseReadinessModal";
import ActionPlanModal from "../components/ActionPlanModal";
import SourceDetailsModal from "../components/SourceDetailsModal";
import LawyerHandoffModal from "../components/LawyerHandoffModal";

const CATEGORIES = [
  { value: "consumer_rights", label: "Consumer Rights" },
  { value: "labour_rights", label: "Labour Rights" },
  { value: "womens_safety", label: "Women's Safety" },
  { value: "educational_rights", label: "Educational Rights" },
  { value: "anti_ragging", label: "Anti-Ragging" },
];

const SUGGESTED_PROMPTS = [
  {
    category: "consumer_rights",
    text: "I bought a defective product and the seller refuses to repair or refund.",
  },
  {
    category: "labour_rights",
    text: "My employer hasn't paid my salary for 2 months without notice.",
  },
  {
    category: "womens_safety",
    text: "What steps can I take regarding workplace harassment under POSH Act?",
  },
  {
    category: "anti_ragging",
    text: "What remedies exist if a student faces ragging on campus?",
  },
];

function categoryLabel(value) {
  return CATEGORIES.find((c) => c.value === value)?.label || value;
}

function CollapsibleSources({ sources, onSelectSource }) {
  const [expanded, setExpanded] = useState(false);
  const visibleSources = sources.slice(0, 5);

  if (!sources || sources.length === 0) return null;

  return (
    <div className="mt-3 pt-3 border-t border-slate-100">
      <button
        type="button"
        onClick={() => setExpanded(!expanded)}
        className="flex items-center gap-2 text-xs font-semibold text-teal-700 hover:text-teal-800 transition-colors cursor-pointer"
      >
        <span>📜 Sources used ({sources.length})</span>
        <span className="text-[11px] text-teal-600 font-normal ml-auto">
          {expanded ? "▲ Hide" : "▼ View sources"}
        </span>
      </button>

      {expanded && (
        <div className="mt-2.5 space-y-2">
          {visibleSources.map((source, idx) => (
            <div
              key={source.citation_id || idx}
              onClick={() => onSelectSource?.(source)}
              className="flex items-center justify-between rounded-xl border border-slate-200 bg-slate-50 p-2.5 text-xs cursor-pointer hover:border-teal-400 hover:bg-teal-50/50 transition-all shadow-2xs"
            >
              <div className="flex items-center gap-2 min-w-0">
                <span className="rounded bg-teal-700 px-1.5 py-0.5 text-[10px] font-bold text-white flex-shrink-0">
                  {source.citation_id || `SOURCE_${idx + 1}`}
                </span>
                <span className="font-semibold text-slate-800 truncate">
                  {source.title || "Legal Source"}
                </span>
                {source.provision_number && (
                  <span className="text-slate-500 truncate hidden sm:inline">
                    — {source.provision_type ? `${source.provision_type} ` : "Section "}{source.provision_number}
                  </span>
                )}
              </div>
              <span className="text-[11px] font-semibold text-teal-700 ml-2 flex-shrink-0">
                View →
              </span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

function Message({ message, onRetry, retrying, onSelectOption, onSelectSource }) {
  const assistant = message.role === "assistant";
  const isClarification = message.message_type === "clarification";

  return (
    <div className={assistant ? "flex justify-start" : "flex justify-end"}>
      <div
        className={[
          "max-w-2xl rounded-2xl px-5 py-4 text-slate-900 transition-all text-sm leading-6",
          assistant
            ? isClarification
              ? "border border-amber-300 bg-amber-50/90 shadow-sm"
              : "border border-slate-200 bg-white shadow-sm"
            : "bg-teal-700 text-white shadow-sm",
        ].join(" ")}
      >
        {assistant && message.category_notice && (
          <div className="mb-3 flex items-center gap-2 rounded-xl border border-teal-200 bg-teal-50/90 px-3 py-2 text-xs font-semibold text-teal-900">
            <svg className="h-4 w-4 text-teal-700 flex-shrink-0" viewBox="0 0 20 20" fill="currentColor">
              <path fillRule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a.75.75 0 000 1.5h.253a.25.25 0 01.244.304l-.459 2.066A1.75 1.75 0 0010.747 15H11a.75.75 0 000-1.5h-.253a.25.25 0 01-.244-.304l.459-2.066A1.75 1.75 0 009.253 9H9z" clipRule="evenodd" />
            </svg>
            {message.category_notice}
          </div>
        )}

        {assistant && isClarification && (
          <div className="mb-2 flex items-center gap-1.5 text-xs font-bold text-amber-900">
            <svg className="h-4 w-4 text-amber-700 flex-shrink-0" viewBox="0 0 20 20" fill="currentColor">
              <path fillRule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a.75.75 0 000 1.5h.253a.25.25 0 01.244.304l-.459 2.066A1.75 1.75 0 0010.747 15H11a.75.75 0 000-1.5h-.253a.25.25 0 01-.244-.304l.459-2.066A1.75 1.75 0 009.253 9H9z" clipRule="evenodd" />
            </svg>
            Follow-Up Fact Clarification Needed
          </div>
        )}

        <div className="whitespace-pre-wrap text-sm leading-6">
          {message.content}
        </div>

        {assistant && message.suggested_options && message.suggested_options.length > 0 && (
          <div className="mt-3.5 flex flex-wrap gap-2">
            {message.suggested_options.map((option, idx) => (
              <button
                key={idx}
                type="button"
                onClick={() => onSelectOption?.(option)}
                className="rounded-xl border border-amber-300 bg-white px-3 py-1.5 text-xs font-semibold text-amber-900 hover:bg-amber-100 transition-all cursor-pointer"
              >
                {option}
              </button>
            ))}
          </div>
        )}

        {assistant && message.sources && message.sources.length > 0 && (
          <CollapsibleSources sources={message.sources} onSelectSource={onSelectSource} />
        )}

        {assistant && message.status === "failed" && (
          <button
            type="button"
            disabled={retrying}
            onClick={() => onRetry(message.id)}
            className="mt-3 rounded-xl border border-red-200 bg-red-50 px-3 py-1.5 text-xs font-bold text-red-700 hover:bg-red-100 disabled:opacity-50 transition-colors cursor-pointer"
          >
            {retrying ? "Retrying..." : "Retry response"}
          </button>
        )}
      </div>
    </div>
  );
}

export default function ChatPage() {
  const [chats, setChats] = useState([]);
  const [selectedChat, setSelectedChat] = useState(null);
  const [loading, setLoading] = useState(true);
  const [loadingChat, setLoadingChat] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [retryingMessageId, setRetryingMessageId] = useState(null);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");
  const [showNewChat, setShowNewChat] = useState(false);
  const [newChat, setNewChat] = useState({
    title: "",
    category: "consumer_rights",
  });

  const [readinessModalOpen, setReadinessModalOpen] = useState(false);
  const [readinessData, setReadinessData] = useState(null);
  const [loadingReadiness, setLoadingReadiness] = useState(false);
  const [readinessError, setReadinessError] = useState("");

  const [actionPlanModalOpen, setActionPlanModalOpen] = useState(false);
  const [actionPlanData, setActionPlanData] = useState(null);
  const [loadingActionPlan, setLoadingActionPlan] = useState(false);
  const [actionPlanError, setActionPlanError] = useState("");

  const [handoffModalOpen, setHandoffModalOpen] = useState(false);
  const [handoffData, setHandoffData] = useState(null);
  const [loadingHandoff, setLoadingHandoff] = useState(false);
  const [handoffError, setHandoffError] = useState("");

  const [selectedSource, setSelectedSource] = useState(null);
  const [answerMode, setAnswerMode] = useState("simple");

  const bottomRef = useRef(null);

  useEffect(() => {
    loadChats();
  }, []);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [selectedChat?.messages, submitting]);

  async function loadChats() {
    setLoading(true);
    setError("");
    try {
      const data = await listChats();
      setChats(data);
    } catch (requestError) {
      setError(getApiErrorMessage(requestError, "Could not load chats."));
    } finally {
      setLoading(false);
    }
  }

  async function openChat(chatId) {
    setLoadingChat(true);
    setError("");
    try {
      const data = await getChat(chatId);
      setSelectedChat(data);
      setAnswerMode(data.answer_mode || "simple");
    } catch (requestError) {
      setError(getApiErrorMessage(requestError, "Could not load this chat."));
    } finally {
      setLoadingChat(false);
    }
  }

  async function handleToggleAnswerMode(newMode) {
    setAnswerMode(newMode);
    if (selectedChat) {
      try {
        await updateChat(selectedChat.id, { answer_mode: newMode });
        setSelectedChat((prev) => (prev ? { ...prev, answer_mode: newMode } : null));
      } catch (err) {
        console.error("Could not update answer mode:", err);
      }
    }
  }

  async function handleOpenHandoff() {
    if (!selectedChat) return;
    setHandoffModalOpen(true);
    setLoadingHandoff(true);
    setHandoffError("");
    try {
      const data = await fetchSessionLawyerHandoff(selectedChat.id);
      setHandoffData(data);
    } catch (err) {
      setHandoffError(getApiErrorMessage(err, "Could not generate lawyer handoff pack."));
    } finally {
      setLoadingHandoff(false);
    }
  }

  async function handleOpenReadiness() {
    if (!selectedChat) return;
    setReadinessModalOpen(true);
    setLoadingReadiness(true);
    setReadinessError("");
    try {
      const data = await fetchSessionReadiness(selectedChat.id);
      setReadinessData(data);
    } catch (err) {
      setReadinessError(getApiErrorMessage(err, "Could not load case readiness assessment."));
    } finally {
      setLoadingReadiness(false);
    }
  }

  async function handleOpenActionPlan() {
    if (!selectedChat) return;
    setActionPlanModalOpen(true);
    setLoadingActionPlan(true);
    setActionPlanError("");
    try {
      const data = await fetchSessionActionPlan(selectedChat.id);
      setActionPlanData(data);
    } catch (err) {
      setActionPlanError(getApiErrorMessage(err, "Could not generate action plan."));
    } finally {
      setLoadingActionPlan(false);
    }
  }

  async function handleCreateChat(event) {
    event.preventDefault();
    setError("");

    try {
      const created = await createChat({
        title: newChat.title.trim(),
        category: newChat.category,
      });

      setChats((current) => [created, ...current]);
      setNewChat({ title: "", category: "consumer_rights" });
      setShowNewChat(false);
      await openChat(created.id);
    } catch (requestError) {
      setError(getApiErrorMessage(requestError, "Could not create chat."));
    }
  }

  async function handleSend(event) {
    event.preventDefault();
    const content = message.trim();

    if (!content || !selectedChat || submitting) {
      return;
    }

    setMessage("");
    setSubmitting(true);
    setError("");

    const optimisticMessage = {
      id: `local-${Date.now()}`,
      session_id: selectedChat.id,
      role: "user",
      content,
      sources: [],
      status: "completed",
      created_at: new Date().toISOString(),
    };

    setSelectedChat((current) => ({
      ...current,
      messages: [...(current.messages || []), optimisticMessage],
    }));

    try {
      const result = await sendChatMessage(selectedChat.id, content, answerMode);

      setSelectedChat((current) => ({
        ...current,
        messages: [
          ...(current.messages || []).filter((item) => item.id !== optimisticMessage.id),
          result.user_message,
          result.assistant_message,
        ],
      }));

      await loadChats();
    } catch (requestError) {
      setSelectedChat((current) => ({
        ...current,
        messages: (current.messages || []).filter((item) => item.id !== optimisticMessage.id),
      }));

      setMessage(content);
      setError(getApiErrorMessage(requestError, "Could not send your question."));
    } finally {
      setSubmitting(false);
    }
  }

  async function handleRetry(messageId) {
    if (!selectedChat) return;
    setRetryingMessageId(messageId);
    setError("");

    try {
      const updated = await retryChatMessage(selectedChat.id, messageId);

      setSelectedChat((current) => ({
        ...current,
        messages: current.messages.map((item) => (item.id === messageId ? updated : item)),
      }));
    } catch (requestError) {
      setError(getApiErrorMessage(requestError, "Could not retry this response."));
    } finally {
      setRetryingMessageId(null);
    }
  }

  async function handleDeleteChat() {
    if (!selectedChat) return;
    const confirmed = window.confirm("Delete this chat and its message history?");
    if (!confirmed) return;

    try {
      await deleteChat(selectedChat.id);
      setChats((current) => current.filter((chat) => chat.id !== selectedChat.id));
      setSelectedChat(null);
    } catch (requestError) {
      setError(getApiErrorMessage(requestError, "Could not delete chat."));
    }
  }

  const [mobileChatsOpen, setMobileChatsOpen] = useState(false);
  const [mobileActionsOpen, setMobileActionsOpen] = useState(false);

  return (
    <div className="flex min-h-[calc(100vh-73px)] lg:min-h-screen">
      {/* Desktop Sidebar */}
      <section aria-label="Legal Chat History" className="hidden w-72 shrink-0 border-r border-slate-200 bg-white md:block">
        <div className="border-b border-slate-200 p-4 bg-slate-50/50">
          <button
            type="button"
            onClick={() => setShowNewChat(true)}
            className="btn-teal w-full py-2.5 text-sm font-semibold shadow-xs min-h-[44px]"
          >
            + New legal chat
          </button>
        </div>

        <div className="space-y-1 p-3 overflow-y-auto max-h-[calc(100vh-140px)]">
          {loading ? (
            <p className="p-3 text-xs text-slate-500 font-medium">Loading chats...</p>
          ) : chats.length === 0 ? (
            <p className="p-3 text-xs leading-5 text-slate-500">
              No active chats. Click + New legal chat to start asking questions.
            </p>
          ) : (
            chats.map((chat) => (
              <button
                key={chat.id}
                type="button"
                onClick={() => openChat(chat.id)}
                className={[
                  "w-full rounded-xl p-3 text-left transition focus:outline-none focus:ring-2 focus:ring-teal-400 min-h-[44px] cursor-pointer",
                  selectedChat?.id === chat.id
                    ? "bg-teal-50 border border-teal-200 shadow-2xs font-semibold"
                    : "hover:bg-slate-50 border border-transparent",
                ].join(" ")}
              >
                <div className="truncate text-sm text-slate-900 font-medium">
                  {chat.title}
                </div>
                <div className="mt-0.5 text-xs text-teal-700 font-medium">
                  {categoryLabel(chat.category)}
                </div>
              </button>
            ))
          )}
        </div>
      </section>

      {/* Mobile Chat Sessions Drawer Overlay */}
      {mobileChatsOpen && (
        <div className="fixed inset-0 z-50 md:hidden" aria-modal="true" role="dialog" aria-label="Chat Sessions">
          <div className="absolute inset-0 bg-slate-950/60 backdrop-blur-xs" onClick={() => setMobileChatsOpen(false)} />
          <div className="absolute inset-y-0 left-0 w-80 max-w-[85vw] bg-white shadow-2xl p-4 flex flex-col animate-slide-left">
            <div className="flex items-center justify-between border-b border-slate-100 pb-3 mb-3">
              <h3 className="text-base font-bold text-slate-900 font-serif-title">Legal Chats</h3>
              <button
                type="button"
                onClick={() => setMobileChatsOpen(false)}
                className="rounded-lg p-2 text-slate-400 hover:bg-slate-100 min-h-[44px] min-w-[44px] flex items-center justify-center cursor-pointer"
                aria-label="Close chat list"
              >
                ✕
              </button>
            </div>
            <button
              type="button"
              onClick={() => {
                setMobileChatsOpen(false);
                setShowNewChat(true);
              }}
              className="btn-teal w-full py-2.5 text-sm font-semibold mb-3 min-h-[44px]"
            >
              + New legal chat
            </button>
            <div className="flex-1 overflow-y-auto space-y-1">
              {chats.map((chat) => (
                <button
                  key={chat.id}
                  type="button"
                  onClick={() => {
                    openChat(chat.id);
                    setMobileChatsOpen(false);
                  }}
                  className={[
                    "w-full rounded-xl p-3 text-left transition min-h-[44px]",
                    selectedChat?.id === chat.id
                      ? "bg-teal-50 border border-teal-200"
                      : "hover:bg-slate-50 border border-transparent",
                  ].join(" ")}
                >
                  <div className="truncate text-sm font-medium text-slate-900">
                    {chat.title}
                  </div>
                  <div className="mt-0.5 text-xs text-teal-700 font-medium">
                    {categoryLabel(chat.category)}
                  </div>
                </button>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* Main Chat Area */}
      <section className="flex min-w-0 flex-1 flex-col bg-[#F7F6F2]">
        <header className="flex flex-wrap items-center justify-between border-b border-slate-200 bg-white px-4 py-3 sm:px-6 gap-3 shadow-2xs">
          <div className="min-w-0 flex-1">
            <div className="flex items-center gap-2">
              <button
                type="button"
                onClick={() => setMobileChatsOpen(true)}
                className="rounded-lg border border-slate-300 p-2 text-xs font-semibold text-slate-700 md:hidden min-h-[44px] min-w-[44px] flex items-center justify-center cursor-pointer"
                aria-label="Open chat history"
              >
                💬 Chats
              </button>
              <h1 className="truncate text-base sm:text-lg font-bold text-slate-900 font-serif-title">
                {selectedChat ? selectedChat.title : "Legal Chat Workspace"}
              </h1>
            </div>
            <p className="mt-0.5 text-xs text-teal-700 font-medium truncate">
              {selectedChat
                ? `Category: ${categoryLabel(selectedChat.category)}`
                : "Citation-Grounded Indian Legal Assistance"}
            </p>
          </div>

          <div className="flex items-center gap-2">
            <button
              type="button"
              onClick={() => setShowNewChat(true)}
              className="btn-outline-legal text-xs py-2 px-3 md:hidden min-h-[44px]"
            >
              + New
            </button>

            {selectedChat && (
              <div className="flex items-center gap-2">
                {/* Answer Mode Toggle */}
                <div className="flex items-center gap-0.5 bg-slate-100 p-1 rounded-xl border border-slate-200 text-xs font-semibold text-slate-600">
                  <span className="px-1.5 text-slate-500 font-normal hidden sm:inline">Mode:</span>
                  <button
                    type="button"
                    title="Short, practical guidance"
                    onClick={() => handleToggleAnswerMode("simple")}
                    className={`px-2.5 py-1 rounded-lg transition-all cursor-pointer min-h-[34px] ${
                      answerMode === "simple"
                        ? "bg-white text-teal-800 shadow-2xs font-bold"
                        : "text-slate-600 hover:text-slate-900"
                    }`}
                  >
                    Simple
                  </button>
                  <button
                    type="button"
                    title="Detailed statutory breakdown"
                    onClick={() => handleToggleAnswerMode("detailed")}
                    className={`px-2.5 py-1 rounded-lg transition-all cursor-pointer min-h-[34px] ${
                      answerMode === "detailed"
                        ? "bg-white text-teal-800 shadow-2xs font-bold"
                        : "text-slate-600 hover:text-slate-900"
                    }`}
                  >
                    Detailed
                  </button>
                </div>

                {/* Desktop Secondary Actions Group */}
                <div className="hidden md:flex items-center gap-2">
                  <button
                    type="button"
                    onClick={handleOpenHandoff}
                    className="btn-outline-legal py-2 px-3 text-xs font-semibold min-h-[44px]"
                  >
                    💼 Lawyer Handoff
                  </button>
                  <button
                    type="button"
                    onClick={handleOpenActionPlan}
                    className="btn-outline-legal py-2 px-3 text-xs font-semibold min-h-[44px]"
                  >
                    🎯 Action Plan
                  </button>
                  <button
                    type="button"
                    onClick={handleOpenReadiness}
                    className="btn-outline-legal py-2 px-3 text-xs font-semibold min-h-[44px]"
                  >
                    📋 Case Readiness
                  </button>
                  <button
                    type="button"
                    onClick={handleDeleteChat}
                    className="btn-danger-legal py-2 px-3 text-xs font-semibold min-h-[44px]"
                  >
                    Delete
                  </button>
                </div>

                {/* Mobile Actions Dropdown */}
                <div className="relative md:hidden">
                  <button
                    type="button"
                    onClick={() => setMobileActionsOpen(!mobileActionsOpen)}
                    className="btn-teal py-2 px-3 text-xs font-semibold min-h-[44px] flex items-center gap-1 shadow-2xs"
                    aria-expanded={mobileActionsOpen}
                    aria-label="More actions"
                  >
                    Actions ▼
                  </button>
                  {mobileActionsOpen && (
                    <div
                      className="absolute right-0 top-12 z-30 w-52 rounded-2xl bg-white p-2 shadow-xl border border-slate-200 space-y-1 animate-fade-in"
                      onClick={() => setMobileActionsOpen(false)}
                    >
                      <button
                        type="button"
                        onClick={handleOpenHandoff}
                        className="w-full text-left rounded-xl px-3 py-2 text-xs font-semibold text-slate-800 hover:bg-slate-50 flex items-center gap-2 cursor-pointer"
                      >
                        💼 Lawyer Handoff
                      </button>
                      <button
                        type="button"
                        onClick={handleOpenActionPlan}
                        className="w-full text-left rounded-xl px-3 py-2 text-xs font-semibold text-slate-800 hover:bg-slate-50 flex items-center gap-2 cursor-pointer"
                      >
                        🎯 Action Plan
                      </button>
                      <button
                        type="button"
                        onClick={handleOpenReadiness}
                        className="w-full text-left rounded-xl px-3 py-2 text-xs font-semibold text-slate-800 hover:bg-slate-50 flex items-center gap-2 cursor-pointer"
                      >
                        📋 Case Readiness
                      </button>
                      <div className="border-t border-slate-100 my-1" />
                      <button
                        type="button"
                        onClick={handleDeleteChat}
                        className="w-full text-left rounded-xl px-3 py-2 text-xs font-semibold text-red-600 hover:bg-red-50 flex items-center gap-2 cursor-pointer"
                      >
                        🗑 Delete Chat
                      </button>
                    </div>
                  )}
                </div>
              </div>
            )}
          </div>
        </header>

        {error && (
          <div role="alert" className="border-b border-red-200 bg-red-50 px-5 py-3 text-sm font-semibold text-red-800">
            {error}
          </div>
        )}

        {!selectedChat ? (
          <div className="flex flex-1 items-center justify-center p-6 sm:p-8">
            <div className="max-w-xl text-center animate-fade-in">
              <div className="inline-flex h-12 w-12 items-center justify-center rounded-2xl bg-teal-50 text-teal-700 text-2xl border border-teal-200 mb-4 shadow-2xs">
                ⚖️
              </div>

              <h2 className="text-2xl font-bold font-serif-title text-slate-900">
                What would you like to understand?
              </h2>

              <p className="mt-2 text-sm leading-6 text-slate-600">
                Nyaya AI supplies statutory explanation grounded in verified Indian laws. Select a category below or create a custom legal chat.
              </p>

              {/* Suggested Prompts Cards Grid */}
              <div className="mt-6 grid gap-3 sm:grid-cols-2 text-left">
                {SUGGESTED_PROMPTS.map((prompt, idx) => (
                  <button
                    key={idx}
                    type="button"
                    onClick={() => {
                      setNewChat({
                        title: prompt.text.slice(0, 40) + "...",
                        category: prompt.category,
                      });
                      setShowNewChat(true);
                    }}
                    className="card-legal p-3.5 hover:border-teal-600/60 cursor-pointer"
                  >
                    <span className="text-[10px] font-bold text-teal-700 uppercase tracking-wider">
                      {categoryLabel(prompt.category)}
                    </span>
                    <p className="text-xs font-medium text-slate-800 mt-1 line-clamp-2">
                      "{prompt.text}"
                    </p>
                  </button>
                ))}
              </div>

              <button
                type="button"
                onClick={() => setShowNewChat(true)}
                className="mt-6 btn-teal py-2.5 px-6 text-sm shadow-xs"
              >
                Start a legal chat
              </button>
            </div>
          </div>
        ) : loadingChat ? (
          <div className="flex flex-1 items-center justify-center text-sm font-medium text-slate-500">
            Loading conversation history...
          </div>
        ) : (
          <>
            <div className="flex-1 overflow-y-auto px-4 py-6 sm:px-8">
              <div className="mx-auto max-w-3xl space-y-5">
                {selectedChat.messages?.length === 0 && (
                  <div className="py-12 text-center animate-fade-in">
                    <h3 className="text-lg font-bold font-serif-title text-slate-900">
                      Start your legal conversation
                    </h3>
                    <p className="mx-auto mt-2 max-w-md text-xs leading-5 text-slate-600">
                      Describe your situation clearly. Nyaya AI will analyze key legal elements, ask necessary clarification questions, and supply citation-backed statutory answers.
                    </p>
                  </div>
                )}

                {selectedChat.messages?.map((item) => (
                  <Message
                    key={item.id}
                    message={item}
                    onRetry={handleRetry}
                    retrying={retryingMessageId === item.id}
                    onSelectOption={(opt) => setMessage(opt)}
                    onSelectSource={(src) => setSelectedSource(src)}
                  />
                ))}

                {submitting && (
                  <div className="flex justify-start">
                    <div className="rounded-2xl border border-teal-200 bg-teal-50 px-4 py-3 text-xs font-medium text-teal-900 shadow-2xs flex items-center gap-2">
                      <span className="h-3.5 w-3.5 rounded-full border-2 border-teal-700 border-t-transparent animate-spin-smooth" />
                      Retrieving verified legal statutes & drafting answer...
                    </div>
                  </div>
                )}

                <div ref={bottomRef} />
              </div>
            </div>

            {/* Composer */}
            <div className="border-t border-slate-200 bg-white p-4 shadow-sm">
              <form onSubmit={handleSend} className="mx-auto flex max-w-3xl gap-3 items-end">
                <div className="flex-1">
                  <label htmlFor="chat-composer-input" className="sr-only">
                    Ask a legal-information question
                  </label>
                  <textarea
                    id="chat-composer-input"
                    rows={2}
                    maxLength={10000}
                    value={message}
                    disabled={submitting}
                    onChange={(event) => setMessage(event.target.value)}
                    placeholder="Ask a legal-information question..."
                    className="form-input-legal min-h-[56px] resize-none rounded-xl"
                  />
                </div>

                <button
                  type="submit"
                  aria-label="Send legal question"
                  disabled={submitting || !message.trim()}
                  className="btn-teal py-3 px-5 text-sm font-semibold min-h-[44px] min-w-[44px] shadow-2xs"
                >
                  Send
                </button>
              </form>

              <p className="mx-auto mt-2 max-w-3xl text-[11px] text-slate-500">
                Statutory legal information grounding — not guaranteed legal advice or representation.
              </p>
            </div>
          </>
        )}
      </section>

      {/* New Chat Modal */}
      {showNewChat && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/60 p-4 backdrop-blur-xs animate-fade-in"
          onClick={() => setShowNewChat(false)}
        >
          <form
            role="dialog"
            aria-modal="true"
            aria-labelledby="new-chat-title"
            onClick={(e) => e.stopPropagation()}
            onSubmit={handleCreateChat}
            className="w-full max-w-md rounded-2xl bg-white p-6 shadow-2xl border border-slate-200 outline-none"
          >
            <h3 id="new-chat-title" className="text-xl font-bold font-serif-title text-slate-900">
              New legal chat
            </h3>

            <p className="mt-1.5 text-xs text-slate-600">
              Select the Indian statutory category that best matches your query.
            </p>

            <div className="mt-5">
              <label htmlFor="new-chat-title-input" className="mb-1 block text-xs font-semibold text-slate-700">
                Chat title
              </label>

              <input
                id="new-chat-title-input"
                required
                minLength={1}
                maxLength={150}
                value={newChat.title}
                onChange={(event) =>
                  setNewChat((current) => ({
                    ...current,
                    title: event.target.value,
                  }))
                }
                placeholder="e.g. Defective product refund query"
                className="form-input-legal min-h-[44px]"
              />
            </div>

            <div className="mt-4">
              <label htmlFor="new-chat-category-select" className="mb-1 block text-xs font-semibold text-slate-700">
                Legal category
              </label>

              <select
                id="new-chat-category-select"
                value={newChat.category}
                onChange={(event) =>
                  setNewChat((current) => ({
                    ...current,
                    category: event.target.value,
                  }))
                }
                className="form-input-legal min-h-[44px] bg-white"
              >
                {CATEGORIES.map((category) => (
                  <option key={category.value} value={category.value}>
                    {category.label}
                  </option>
                ))}
              </select>
            </div>

            <div className="mt-6 flex justify-end gap-3">
              <button
                type="button"
                onClick={() => setShowNewChat(false)}
                className="btn-outline-legal py-2 px-4 text-xs font-semibold min-h-[44px]"
              >
                Cancel
              </button>

              <button
                type="submit"
                className="btn-teal py-2 px-4 text-xs font-semibold shadow-2xs min-h-[44px]"
              >
                Create chat
              </button>
            </div>
          </form>
        </div>
      )}

      {/* Modals */}
      <CaseReadinessModal
        isOpen={readinessModalOpen}
        onClose={() => setReadinessModalOpen(false)}
        readiness={readinessData}
        loading={loadingReadiness}
        error={readinessError}
      />

      <ActionPlanModal
        isOpen={actionPlanModalOpen}
        onClose={() => setActionPlanModalOpen(false)}
        plan={actionPlanData}
        loading={loadingActionPlan}
        error={actionPlanError}
      />

      <LawyerHandoffModal
        isOpen={handoffModalOpen}
        onClose={() => setHandoffModalOpen(false)}
        handoff={handoffData}
        loading={loadingHandoff}
        error={handoffError}
        sessionId={selectedChat?.id}
      />

      <SourceDetailsModal
        isOpen={!!selectedSource}
        onClose={() => setSelectedSource(null)}
        source={selectedSource}
      />
    </div>
  );
}