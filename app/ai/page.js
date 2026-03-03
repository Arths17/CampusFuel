"use client";

import { useState, useEffect, useRef } from "react";
import { useRouter } from "next/navigation";
import CampusFuelNav from "../components/Navbar/CampusFuelNav";
import styles from "./ai.module.css";

// ═══════════════════════════════════════════════════════════════════
// HTTP REQUEST UTILITIES (communicates with main.py backend)
// ═══════════════════════════════════════════════════════════════════

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || '';
const DEFAULT_TIMEOUT = 30000; // 30 seconds
const STREAM_TIMEOUT = 120000; // 2 minutes

// Error classes
class APIError extends Error {
  constructor(message, statusCode = 500) {
    super(message);
    this.name = 'APIError';
    this.statusCode = statusCode;
  }
}

class AuthenticationError extends APIError {
  constructor(message = 'Authentication required') {
    super(message, 401);
    this.name = 'AuthenticationError';
  }
}

class NetworkError extends APIError {
  constructor(message) {
    super(message, 0);
    this.name = 'NetworkError';
  }
}

class TimeoutError extends APIError {
  constructor(message = 'Request timeout') {
    super(message, 408);
    this.name = 'TimeoutError';
  }
}

// Get auth token from localStorage or sessionStorage
function getAuthToken() {
  if (typeof window === 'undefined') return null;
  return localStorage.getItem('token') || sessionStorage.getItem('token');
}

// Fetch with timeout
async function fetchWithTimeout(url, options, timeout = DEFAULT_TIMEOUT) {
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), timeout);

  try {
    const response = await fetch(url, {
      ...options,
      signal: controller.signal,
    });
    clearTimeout(timeoutId);
    return response;
  } catch (error) {
    clearTimeout(timeoutId);
    if (error.name === 'AbortError') {
      throw new TimeoutError('Request timeout exceeded');
    }
    throw new NetworkError(`Network error: ${error.message}`);
  }
}

// Get user profile from main.py GET /api/me
async function getProfile() {
  const token = getAuthToken();
  if (!token) {
    throw new AuthenticationError('No authentication token');
  }

  try {
    const response = await fetchWithTimeout(`${API_BASE_URL}/api/me`, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${token}`,
        'ngrok-skip-browser-warning': 'true',
      },
    });

    const data = await response.json();

    if (!response.ok) {
      throw new APIError(data.error || 'Failed to load profile', response.status);
    }

    if (data.success === false) {
      throw new APIError(data.error || 'Failed to load profile', response.status);
    }

    return data;
  } catch (error) {
    if (error instanceof APIError) throw error;
    throw new NetworkError(`Failed to load profile: ${error.message}`);
  }
}

// Send chat message with streaming to main.py POST /api/chat
async function sendChatMessage(message, onChunk) {
  const token = getAuthToken();
  if (!token) {
    throw new AuthenticationError('No authentication token');
  }

  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), STREAM_TIMEOUT);

  try {
    const response = await fetch(`${API_BASE_URL}/api/chat`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${token}`,
        'ngrok-skip-browser-warning': 'true',
      },
      body: JSON.stringify({ message }),
      signal: controller.signal,
    });

    if (!response.ok) {
      clearTimeout(timeoutId);
      const errorData = await response.json().catch(() => ({}));
      throw new APIError(
        errorData.error || `Request failed: ${response.statusText}`,
        response.status
      );
    }

    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let fullText = '';

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      const chunk = decoder.decode(value, { stream: false });
      fullText += chunk;

      if (onChunk) {
        onChunk(chunk);
      }
    }

    clearTimeout(timeoutId);
    return fullText;
  } catch (error) {
    clearTimeout(timeoutId);
    if (error.name === 'AbortError') {
      throw new TimeoutError('Stream timeout exceeded');
    }
    if (error instanceof APIError) throw error;
    throw new NetworkError(`Chat failed: ${error.message}`);
  }
}

// ═══════════════════════════════════════════════════════════════════
// MARKDOWN RENDERER
// ═══════════════════════════════════════════════════════════════════

function renderInline(text) {
  const regex = /(\*\*(.+?)\*\*|\*(.+?)\*|`(.+?)`)/g;
  const parts = [];
  let lastIndex = 0;
  let key = 0;
  let match;
  while ((match = regex.exec(text)) !== null) {
    if (match.index > lastIndex) parts.push(text.slice(lastIndex, match.index));
    if (match[2]) parts.push(<strong key={key++}>{match[2]}</strong>);
    else if (match[3]) parts.push(<em key={key++}>{match[3]}</em>);
    else if (match[4]) parts.push(<code key={key++} style={{ background: "rgba(0,0,0,0.07)", padding: "1px 5px", borderRadius: "4px", fontSize: "0.88em", fontFamily: "monospace" }}>{match[4]}</code>);
    lastIndex = match.index + match[0].length;
  }
  if (lastIndex < text.length) parts.push(text.slice(lastIndex));
  return parts.length > 0 ? parts : text;
}

function renderMarkdown(text) {
  if (!text) return null;
  const lines = text.split("\n");
  const elements = [];
  let listItems = [];
  let listType = null;
  function flushList() {
    if (!listItems.length) return;
    const Tag = listType === "ol" ? "ol" : "ul";
    elements.push(
      <Tag key={`list-${elements.length}`} style={{ paddingLeft: "1.4em", margin: "4px 0" }}>
        {listItems.map((item, i) => <li key={i} style={{ marginBottom: "2px" }}>{renderInline(item)}</li>)}
      </Tag>
    );
    listItems = [];
    listType = null;
  }
  lines.forEach((line, i) => {
    const h3 = line.match(/^###\s+(.+)$/);
    const h2 = line.match(/^##\s+(.+)$/);
    const h1 = line.match(/^#\s+(.+)$/);
    const ol = line.match(/^\d+\.\s+(.+)$/);
    const ul = line.match(/^[-*]\s+(.+)$/);
    if (h3) {
      flushList();
      elements.push(<strong key={i} style={{ display: "block", fontSize: "0.95em", color: "var(--green-dark,#0e3e23)", margin: "8px 0 4px" }}>{renderInline(h3[1])}</strong>);
    } else if (h2) {
      flushList();
      elements.push(<strong key={i} style={{ display: "block", fontSize: "1em", color: "var(--green-dark,#0e3e23)", margin: "10px 0 4px" }}>{renderInline(h2[1])}</strong>);
    } else if (h1) {
      flushList();
      elements.push(<strong key={i} style={{ display: "block", fontSize: "1.05em", color: "var(--green-dark,#0e3e23)", margin: "12px 0 6px" }}>{renderInline(h1[1])}</strong>);
    } else if (ol) {
      if (listType !== "ol") { flushList(); listType = "ol"; }
      listItems.push(ol[1]);
    } else if (ul) {
      if (listType !== "ul") { flushList(); listType = "ul"; }
      listItems.push(ul[1]);
    } else if (line.trim() === "") {
      flushList();
      if (elements.length > 0) elements.push(<br key={`br-${i}`} />);
    } else {
      flushList();
      elements.push(<p key={i} style={{ margin: "0 0 4px" }}>{renderInline(line)}</p>);
    }
  });
  flushList();
  return elements;
}

// ═══════════════════════════════════════════════════════════════════
// REACT COMPONENT
// ═══════════════════════════════════════════════════════════════════

export default function AIPage() {
  const router = useRouter();
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [profileReady, setProfileReady] = useState(false);
  const [profileName, setProfileName] = useState("");
  const [checkingProfile, setCheckingProfile] = useState(true);
  const [chatUser, setChatUser] = useState(null);
  const bottomRef = useRef(null);
  const inputRef = useRef(null);

  // Persist messages to localStorage per user
  const getChatKey = (username) => `cf-chat-${username || "anon"}`;

  const saveMessages = (msgs, username) => {
    try {
      // Keep last 100 messages to avoid bloating storage
      localStorage.setItem(getChatKey(username), JSON.stringify(msgs.slice(-100)));
    } catch { /* no-op */ }
  };

  const loadMessages = (username) => {
    try {
      const raw = localStorage.getItem(getChatKey(username));
      return raw ? JSON.parse(raw) : [];
    } catch { return []; }
  };

  // Auto-resize textarea
  useEffect(() => {
    const textarea = inputRef.current;
    if (textarea) {
      textarea.style.height = 'auto';
      textarea.style.height = Math.min(textarea.scrollHeight, 200) + 'px';
    }
  }, [input]);

  // Check for profile on mount - fetch from backend based on logged-in user
  useEffect(() => {
    async function loadProfile() {
      const token = getAuthToken();
      if (!token) {
        router.push("/login");
        return;
      }

      try {
        const data = await getProfile();

        if (!data.success) {
          router.push("/login");
          return;
        }

        // Check if user has a profile
        if (data.profile && Object.keys(data.profile).length > 0) {
          const uname = data.username || "";
          setProfileName(data.profile.name || uname);
          setChatUser(uname);
          setProfileReady(true);
          // Restore chat history
          const saved = loadMessages(uname);
          if (saved.length > 0) setMessages(saved);
          // Update localStorage as cache
          localStorage.setItem("campusfuel_profile", JSON.stringify(data.profile));
        } else {
          setProfileReady(false);
        }
      } catch (err) {
        console.error("Failed to load profile:", err);
        
        // Handle authentication errors
        if (err instanceof AuthenticationError) {
          router.push("/login");
          return;
        }
        
        setProfileReady(false);
      } finally {
        setCheckingProfile(false);
      }
    }

    loadProfile();
  }, [router]);

  // Auto-scroll to bottom on new messages
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
    // Persist chat history whenever messages change
    if (chatUser && messages.length > 0) {
      saveMessages(messages, chatUser);
    }
  }, [messages, chatUser]);

  async function sendMessage() {
    const text = input.trim();
    if (!text || loading) return;
    const userMsg = { role: "user", content: text };
    setMessages((prev) => [...prev, userMsg]);
    setInput("");
    setLoading(true);

    // Placeholder for streaming AI response
    const aiMsgIndex = messages.length + 1;
    setMessages((prev) => [...prev, { role: "ai", content: "" }]);

    try {
      // Stream chat response from main.py POST /api/chat
      await sendChatMessage(text, (chunk) => {
        // Update message with each streamed chunk
        setMessages((prev) => {
          const updated = [...prev];
          updated[updated.length - 1] = {
            role: "ai",
            content: updated[updated.length - 1].content + chunk,
          };
          return updated;
        });
      });
    } catch (err) {
      console.error("Chat error:", err);
      
      let errorMessage = "⚠️ Could not reach the AI server. Make sure the backend is running on port 8000.";
      
      if (err instanceof AuthenticationError) {
        errorMessage = "⚠️ Session expired. Please log in again.";
        setTimeout(() => router.push("/login"), 2000);
      } else if (err instanceof TimeoutError) {
        errorMessage = "⚠️ Request timeout. The AI is taking too long to respond. Please try again.";
      } else if (err instanceof NetworkError) {
        errorMessage = `⚠️ Network error: ${err.message}`;
      } else if (err instanceof APIError) {
        errorMessage = `⚠️ ${err.message}`;
      }
      
      setMessages((prev) => {
        const updated = [...prev];
        updated[updated.length - 1] = {
          role: "ai",
          content: errorMessage,
          error: true,
        };
        return updated;
      });
    } finally {
      setLoading(false);
      inputRef.current?.focus();
    }
  }

  function handleKeyDown(e) {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  }

  const SUGGESTED = [
    "Give me a meal plan for today",
    "What should I eat before a 3-hour study session?",
    "I'm on a tight budget — what's a high-protein cheap meal?",
    "I only slept 4 hours, what should I eat?",
    "Help me reduce stress with nutrition",
  ];

  if (checkingProfile) return null;

  // No profile → prompt survey
  if (!profileReady) {
    return (
      <div className={styles.layout}>
        {/* Ambient orbs */}
        <div className={`${styles.orb} ${styles.orbGreen}`} />
        <div className={`${styles.orb} ${styles.orbGold}`} />
        
        <CampusFuelNav />
        <div className={styles.main}>
          <div className={styles.gateWrap}>
            <div className={styles.gateCard}>
              <div className={styles.gateEmoji}>🤖</div>
              <h2 className={styles.gateTitle}>Meet Your AI Health Coach</h2>
              <p className={styles.gateSub}>
                Before we start, CampusFuel needs to learn about you — your goals,
                schedule, diet, and lifestyle — so it can give truly personalized advice.
              </p>
              <p className={styles.gateNote}>
                ⏱ Takes about <strong>2 minutes</strong>. You only do this once.
              </p>
              <button
                className={styles.gateBtn}
                onClick={() => router.push("/survey")}
              >
                Start My Health Profile →
              </button>
            </div>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className={styles.layout}>
      {/* Ambient orbs */}
      <div className={`${styles.orb} ${styles.orbGreen}`} />
      <div className={`${styles.orb} ${styles.orbGold}`} />
      
      <CampusFuelNav />
      <div className={styles.main}>
        {/* Header */}
        <div className={styles.header}>
          <div className={styles.headerLeft}>
            <span className={styles.aiAvatar}>🤖</span>
            <div>
              <h1 className={styles.headerTitle}>AI Health Coach</h1>
              <span className={styles.headerSub}>
                Personalized nutrition & wellness for {profileName || "you"}
              </span>
            </div>
          </div>
          <button
            className={styles.retakeBtn}
            onClick={() => router.push("/survey")}
            title="Update your health profile"
          >
            ✏️ Update Profile
          </button>
        </div>

        {/* Chat area */}
        <div className={styles.chatArea}>
          {messages.length === 0 && (
            <div className={styles.empty}>
              <div className={styles.emptyEmoji}>💬</div>
              <p className={styles.emptyText}>
                Ask anything about nutrition, energy, sleep, stress, or meal planning.
              </p>
              <div className={styles.suggestions}>
                {SUGGESTED.map((s) => (
                  <button
                    key={s}
                    className={styles.suggestion}
                    onClick={() => { setInput(s); inputRef.current?.focus(); }}
                  >
                    {s}
                  </button>
                ))}
              </div>
            </div>
          )}

          {messages.map((msg, i) => (
            <div
              key={i}
              className={`${styles.msgRow} ${msg.role === "user" ? styles.userRow : styles.aiRow}`}
            >
              {msg.role === "ai" && (
                <div className={styles.aiAvatarSmall}>🤖</div>
              )}
              <div
                className={`${styles.bubble} ${msg.role === "user" ? styles.userBubble : styles.aiBubble} ${msg.error ? styles.errorBubble : ""}`}
              >
                {msg.content
                  ? msg.role === "user"
                    ? msg.content
                    : renderMarkdown(msg.content)
                  : <span className={styles.typing}>●●●</span>}
              </div>
            </div>
          ))}
          <div ref={bottomRef} />
        </div>

        {/* Input area */}
        <div className={styles.inputArea}>
          <div className={styles.inputContainer}>
            <textarea
              ref={inputRef}
              className={styles.chatInput}
              placeholder="Ask your AI health coach anything..."
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              disabled={loading}
            />
            <button
              className={styles.sendBtn}
              onClick={sendMessage}
              disabled={loading || !input.trim()}
            >
              {loading ? "..." : "Send"}
            </button>
          </div>
        </div>  
        {/* Page Footer */}
        <footer className={styles.pageFooter}>
          <span>🌿 CampusFuel</span>
          <span>© 2026 · Built for students, by students.</span>
        </footer>
      </div>
    </div>
  );
}