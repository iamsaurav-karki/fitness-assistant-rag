import { StrictMode, useEffect, useRef, useState } from "react";
import { createRoot } from "react-dom/client";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import "./styles.css";

const API_URL = import.meta.env.VITE_API_URL || "http://localhost:8000";
const CHAT_ENDPOINT = API_URL.endsWith("/api") ? `${API_URL}/chat` : `${API_URL}/api/chat`;
const starterQuestions = [
  "What exercises target the chest?",
  "Give me a 3-day beginner workout.",
  "What does the dataset recommend for muscle recovery?",
];

function createChat() {
  return { id: crypto.randomUUID(), title: "New chat", messages: [], updatedAt: Date.now() };
}

function loadChats() {
  try {
    const saved = JSON.parse(localStorage.getItem("fitness-assistant-chats"));
    if (Array.isArray(saved) && saved.length) return saved;
  } catch {
    // Fall back to a clean local conversation when storage is unavailable.
  }
  return [createChat()];
}

function titleForQuestion(question) {
  return question.length > 32 ? `${question.slice(0, 32).trim()}...` : question;
}

function App() {
  const [question, setQuestion] = useState("");
  const [chats, setChats] = useState(loadChats);
  const [activeChatId, setActiveChatId] = useState(() => loadChats()[0].id);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [showLatest, setShowLatest] = useState(false);
  const conversationRef = useRef(null);
  const inputRef = useRef(null);
  const activeChat = chats.find((chat) => chat.id === activeChatId) || chats[0];
  const messages = activeChat?.messages || [];

  useEffect(() => { localStorage.setItem("fitness-assistant-chats", JSON.stringify(chats)); }, [chats]);

  function scrollToLatest(force = false) {
    const element = conversationRef.current;
    if (!element) return;
    const nearBottom = element.scrollHeight - element.scrollTop - element.clientHeight < 120;
    if (force || nearBottom) element.scrollTo({ top: element.scrollHeight, behavior: "smooth" });
    setShowLatest(false);
  }

  useEffect(() => { scrollToLatest(); }, [messages, loading]);

  async function submit(event, preset = question) {
    event?.preventDefault();
    const text = preset.trim();
    if (!text || loading) return;
    setQuestion("");
    if (inputRef.current) inputRef.current.style.height = "auto";
    setError("");
    const chatId = activeChat.id;
    setChats((current) => current.map((chat) => chat.id === chatId ? { ...chat, title: chat.messages.length ? chat.title : titleForQuestion(text), messages: [...chat.messages, { role: "user", text }], updatedAt: Date.now() } : chat));
    setLoading(true);
    try {
      const response = await fetch(CHAT_ENDPOINT, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ question: text }),
      });
      const payload = await response.json();
      if (!response.ok) throw new Error(payload.detail || "The assistant could not answer.");
      setChats((current) => current.map((chat) => chat.id === chatId ? { ...chat, messages: [...chat.messages, { role: "assistant", text: payload.answer, sources: payload.sources, question: text }], updatedAt: Date.now() } : chat));
    } catch (requestError) {
      setError(requestError.message);
    } finally {
      setLoading(false);
    }
  }

  async function copyAnswer(text) {
    await navigator.clipboard.writeText(text);
  }

  function resizeInput(event) {
    const element = event.currentTarget;
    element.style.height = "auto";
    element.style.height = `${Math.min(element.scrollHeight, 160)}px`;
    setQuestion(element.value);
  }

  function startNewChat() {
    const chat = createChat();
    setChats((current) => [chat, ...current]);
    setActiveChatId(chat.id);
    setQuestion("");
    setError("");
  }

  function removeChat(chatId) {
    const remaining = chats.filter((chat) => chat.id !== chatId);
    const nextChats = remaining.length ? remaining : [createChat()];
    setChats(nextChats);
    if (chatId === activeChatId) setActiveChatId(nextChats[0].id);
  }

  function renameChat(chat) {
    const title = window.prompt("Name this chat", chat.title);
    if (!title?.trim()) return;
    setChats((current) => current.map((item) => item.id === chat.id ? { ...item, title: title.trim() } : item));
  }

  return (
    <main className="app-shell">
      <aside className="sidebar">
        <div className="sidebar-brand"><span className="brand-mark">FA</span><strong>Fitness Assistant</strong></div>
        <button className="new-chat" onClick={startNewChat}><span>＋</span> New chat <kbd>⌘ K</kbd></button>
        <div className="chat-history"><p className="details-label">YOUR CHATS</p>{chats.map((chat) => <div className={`chat-item ${chat.id === activeChatId ? "active" : ""}`} key={chat.id}><button className="chat-select" onClick={() => { setActiveChatId(chat.id); setError(""); }}>{chat.title}</button><button className="chat-menu" onClick={() => renameChat(chat)} title="Rename chat">···</button><button className="chat-delete" onClick={() => removeChat(chat.id)} title="Delete chat">×</button></div>)}</div>
        <div className="sidebar-section"><p className="details-label">PROJECT</p><div className="project-card"><span className="project-dot" /><div><strong>Fitness Assistant</strong><small>RAG fitness knowledge base</small></div></div></div>
        <div className="sidebar-section"><p className="details-label">BUILT WITH</p><div className="tech-list"><span>React + Vite</span><span>FastAPI</span><span>Amazon Bedrock</span><span>RAG</span></div></div>
        <div className="sidebar-footer"><span className="signal"><i /> Knowledge base ready</span><button className="settings" title="Project settings">⚙</button></div>
      </aside>

      <section className="workspace" aria-label="Fitness assistant chat">
        <header className="topbar"><div className="mobile-brand"><span className="brand-mark">FA</span><strong>Fitness Assistant</strong></div><span className="status"><i /> Ready</span><span className="topbar-note">Answers grounded in your fitness library</span></header>
        <div className="conversation" ref={conversationRef} onScroll={(event) => { const element = event.currentTarget; setShowLatest(element.scrollHeight - element.scrollTop - element.clientHeight > 160); }}>
          {messages.length === 0 && <div className="empty-state"><span className="welcome-mark">✦</span><p className="eyebrow">FITNESS KNOWLEDGE BASE</p><h1>How can I help you<br /><em>train smarter?</em></h1><p className="empty-copy">Ask about workouts, exercises, nutrition, or recovery. I’ll find relevant guidance from the project knowledge base.</p><div className="suggestions">{starterQuestions.map((item) => <button key={item} onClick={() => submit(null, item)}>{item}<span>↗</span></button>)}</div></div>}
          {messages.map((message, index) => <article className={`message ${message.role}`} key={`${message.role}-${index}`}><div className="markdown"><ReactMarkdown remarkPlugins={[remarkGfm]}>{message.text}</ReactMarkdown></div>{message.role === "assistant" && <div className="message-actions"><button onClick={() => copyAnswer(message.text)} title="Copy answer">Copy</button><button onClick={() => submit(null, message.question)} disabled={loading} title="Regenerate answer">Regenerate</button></div>}</article>)}
          {loading && <div className="message assistant pending"><span className="dots">● ● ●</span> Searching the knowledge base</div>}
        </div>
        {error && <p className="error">{error}</p>}
        {showLatest && <button className="latest" onClick={() => scrollToLatest(true)}>↓ Latest response</button>}
        <form className="composer" onSubmit={submit}><button className="attach" type="button" title="Attach a file">＋</button><textarea ref={inputRef} rows="1" value={question} onChange={resizeInput} onKeyDown={(event) => { if (event.key === "Enter" && !event.shiftKey) { event.preventDefault(); submit(event); } }} placeholder="Ask about your next workout..." aria-label="Question" /><button className="send" type="submit" disabled={loading || !question.trim()} title="Send message">↑</button></form>
        <p className="composer-note">Fitness Assistant can make mistakes. Check important health decisions with a qualified professional.</p>
      </section>
    </main>
  );
}

createRoot(document.getElementById("root")).render(<StrictMode><App /></StrictMode>);