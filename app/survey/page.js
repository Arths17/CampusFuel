"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import styles from "./survey.module.css";
import { useApp } from "../context/AppContext";

const STEPS = [
  {
    key: "name",
    emoji: "👋",
    question: "What's your name?",
    type: "text",
    placeholder: "e.g. Jordan",
  },
  {
    key: "age",
    emoji: "🎂",
    question: "How old are you?",
    type: "text",
    placeholder: "e.g. 20",
  },
  {
    key: "gender",
    emoji: "⚧",
    question: "What's your gender?",
    type: "select",
    options: ["Male", "Female", "Non-binary", "Prefer not to say"],
  },
  {
    key: "height",
    emoji: "📏",
    question: "What's your height?",
    type: "text",
    placeholder: "e.g. 5'10\" or 178cm",
  },
  {
    key: "weight",
    emoji: "⚖️",
    question: "What's your weight?",
    type: "text",
    placeholder: "e.g. 160 lbs or 73 kg",
  },
  {
    key: "goal",
    emoji: "🎯",
    question: "What's your body goal?",
    type: "select",
    options: ["Fat loss", "Muscle gain", "Maintenance", "General health"],
  },
  {
    key: "diet_type",
    emoji: "🥗",
    question: "What's your diet type?",
    type: "select",
    options: ["Omnivore", "Vegetarian", "Vegan", "Halal", "Kosher", "Other"],
  },
  {
    key: "allergies",
    emoji: "⚠️",
    question: "Any food allergies or intolerances?",
    type: "text",
    placeholder: "e.g. peanuts, gluten — or 'none'",
  },
  {
    key: "budget",
    emoji: "💰",
    question: "What's your food budget level?",
    type: "select",
    options: ["Low", "Medium", "Flexible"],
  },
  {
    key: "cooking_access",
    emoji: "🍳",
    question: "What cooking access do you have?",
    type: "select",
    options: ["Dorm microwave", "Shared kitchen", "Full kitchen", "None"],
  },
  {
    key: "cultural_prefs",
    emoji: "🌍",
    question: "Any cultural food preferences?",
    type: "text",
    placeholder: "e.g. South Asian, Mediterranean — or 'none'",
  },
  {
    key: "class_schedule",
    emoji: "📅",
    question: "What's your class schedule?",
    type: "classpicker",
    times: ["6am","7am","8am","9am","10am","11am","12pm","1pm","2pm","3pm","4pm","5pm","6pm","7pm","8pm","9pm"],
  },
  {
    key: "sleep_schedule",
    emoji: "😴",
    question: "When do you sleep and how long?",
    type: "sleeppicker",
    bedTimes: ["8pm","9pm","10pm","11pm","12am","1am","2am","3am"],
    sleepDurations: ["4 hrs","5 hrs","6 hrs","7 hrs","8 hrs","9 hrs","10 hrs"],
  },
  {
    key: "workout_times",
    emoji: "🏋️",
    question: "When do you work out?",
    type: "workoutpicker",
  },
  {
    key: "stress_level",
    emoji: "😰",
    question: "What's your stress level right now?",
    type: "slider",
    min: 1,
    max: 10,
    labels: ["1 – Totally chill", "10 – Overwhelmed"],
  },
  {
    key: "energy_level",
    emoji: "⚡",
    question: "What's your energy level right now?",
    type: "slider",
    min: 1,
    max: 10,
    labels: ["1 – Exhausted", "10 – Energized"],
  },
  {
    key: "sleep_quality",
    emoji: "🌙",
    question: "How's your sleep quality been lately?",
    type: "select",
    options: ["Poor", "Okay", "Good"],
  },
  {
    key: "mood",
    emoji: "💭",
    question: "How's your mood today?",
    type: "select",
    options: ["Low", "Neutral", "Good"],
  },
  {
    key: "extra",
    emoji: "📝",
    question: "Anything else we should know?",
    type: "textarea",
    placeholder: "Health conditions, habits, concerns — or 'none'",
  },
];

const DAYS = ["Mon","Tue","Wed","Thu","Fri","Sat","Sun"];
const WORKOUT_SLOTS = ["Morning","Afternoon","Evening","Night","I don't work out"];
const NUMERIC_ONLY_KEYS = new Set(["age"]);

export default function SurveyPage() {
  const router = useRouter();
  const { userProfile, refreshUser } = useApp();
  const [step, setStep] = useState(0);
  const [answers, setAnswers] = useState({});
  const [current, setCurrent] = useState("");
  // daypicker state: array of selected day strings
  const [selectedDays, setSelectedDays] = useState([]);
  // sleeppicker state
  const [bedTime, setBedTime] = useState("");
  const [wakeTime, setWakeTime] = useState("");
  // workoutpicker state
  const [workoutDays, setWorkoutDays] = useState([]);
  const [workoutSlot, setWorkoutSlot] = useState("");
  // classpicker state
  const [classBlocks, setClassBlocks] = useState([]); // [{days:[], start:"", end:""}]
  const [blockDays, setBlockDays] = useState([]);
  const [blockStart, setBlockStart] = useState("");
  const [blockEnd, setBlockEnd] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  // Pre-populate answers from saved profile when profile data becomes available
  useEffect(() => {
    const savedProfile =
      userProfile && Object.keys(userProfile).length > 0
        ? userProfile
        : (() => {
            try {
              const cached = localStorage.getItem("campusfuel_profile");
              return cached ? JSON.parse(cached) : null;
            } catch { return null; }
          })();

    if (!savedProfile) return;

    const preloaded = {};
    STEPS.forEach((s) => {
      if (savedProfile[s.key] != null && savedProfile[s.key] !== "") {
        preloaded[s.key] = String(savedProfile[s.key]);
      }
    });
    if (Object.keys(preloaded).length === 0) return;

    setAnswers(preloaded);

    // Seed the UI state for step 0
    const first = STEPS[0];
    const firstVal = preloaded[first.key] || "";
    if (first.type === "classpicker") {
      if (firstVal) {
        const blocks = firstVal.split(" | ").map((b) => {
          const idx = b.lastIndexOf(" ");
          const [s2, e] = b.substring(idx + 1).split("–");
          return { days: b.substring(0, idx).split(", "), start: s2, end: e };
        });
        setClassBlocks(blocks);
      }
    } else if (first.type === "daypicker") {
      setSelectedDays(firstVal ? firstVal.split(", ") : []);
    } else if (first.type === "sleeppicker") {
      const m = firstVal.match(/sleep (.+) for (.+)/);
      setBedTime(m ? m[1] : "");
      setWakeTime(m ? m[2] : "");
    } else if (first.type === "workoutpicker") {
      if (firstVal === "none") {
        setWorkoutDays([]);
        setWorkoutSlot("i don't work out");
      } else {
        const parts = firstVal.split(" – ");
        setWorkoutDays(parts[0] ? parts[0].split(", ") : []);
        setWorkoutSlot(parts[1] || "");
      }
    } else {
      setCurrent(firstVal || (first.type === "slider" ? "5" : ""));
    }
  }, [userProfile]);

  const q = STEPS[step];
  const isLast = step === STEPS.length - 1;

  function handleTextInputChange(rawValue) {
    if (!NUMERIC_ONLY_KEYS.has(q.key)) {
      setCurrent(rawValue);
      if (error === "Please enter numbers only.") setError("");
      return;
    }

    if (/^\d*$/.test(rawValue)) {
      setCurrent(rawValue);
      if (error === "Please enter numbers only.") setError("");
    } else {
      setError("Please enter numbers only.");
    }
  }

  function handleNext() {
    // Serialize interactive pickers into a string value
    let val = current.trim();
    if (q.type === "classpicker") {
      val = classBlocks.length > 0
        ? classBlocks.map(b => `${b.days.join(", ")} ${b.start}–${b.end}`).join(" | ")
        : "";
    } else if (q.type === "daypicker") {
      val = selectedDays.length > 0 ? selectedDays.join(", ") : "";
    } else if (q.type === "sleeppicker") {
      val = bedTime && wakeTime ? `sleep ${bedTime} for ${wakeTime}` : "";
    } else if (q.type === "workoutpicker") {
      if (workoutSlot === "i don't work out") val = "none";
      else val = workoutDays.length > 0 && workoutSlot ? `${workoutDays.join(", ")} – ${workoutSlot}` : "";
    } else {
      val = current.trim() || (q.type === "slider" ? "5" : "");
    }
    if (!val) {
      setError("Please make a selection before continuing.");
      return;
    }

    if (NUMERIC_ONLY_KEYS.has(q.key) && !/^\d+$/.test(val)) {
      setError("Please enter numbers only.");
      return;
    }

    if (q.key === "age") {
      const ageNum = Number(val);
      if (Number.isNaN(ageNum) || ageNum < 10 || ageNum > 100) {
        setError("Please enter a valid age between 10 and 100.");
        return;
      }
    }

    setError("");
    // Don't lowercase classpicker (preserves day names like Mon, Tue)
    const updated = { ...answers, [q.key]: q.type === "classpicker" ? val : val.toLowerCase() };
    setAnswers(updated);

    if (isLast) {
      submitProfile(updated);
    } else {
      const nextKey = STEPS[step + 1].key;
      const nextType = STEPS[step + 1].type;
      const saved = updated[nextKey] || "";
      if (nextType === "classpicker") {
        if (saved) {
          const blocks = saved.split(" | ").map(b => {
            const i = b.lastIndexOf(" ");
            const [s, e] = b.substring(i + 1).split("–");
            return { days: b.substring(0, i).split(", "), start: s, end: e };
          });
          setClassBlocks(blocks);
        } else { setClassBlocks([]); }
        setBlockDays([]); setBlockStart(""); setBlockEnd("");
      } else if (nextType === "daypicker") {
        setSelectedDays(saved ? saved.split(", ") : []);
      } else if (nextType === "sleeppicker") {
        const m = saved.match(/sleep (.+) for (.+)/);
        setBedTime(m ? m[1] : ""); setWakeTime(m ? m[2] : "");
      } else if (nextType === "workoutpicker") {
        if (saved === "none") { setWorkoutDays([]); setWorkoutSlot("i don't work out"); }
        else {
          const parts = saved.split(" – ");
          setWorkoutDays(parts[0] ? parts[0].split(", ") : []);
          setWorkoutSlot(parts[1] || "");
        }
      } else {
        setCurrent(saved || (STEPS[step + 1].type === "slider" ? "5" : ""));
      }
      setStep((s) => s + 1);
    }
  }

  function handleBack() {
    setError("");
    const prevKey = STEPS[step - 1].key;
    const prevType = STEPS[step - 1].type;
    const saved = answers[prevKey] || "";
    if (prevType === "classpicker") {
      if (saved) {
        const blocks = saved.split(" | ").map(b => {
          const i = b.lastIndexOf(" ");
          const [s, e] = b.substring(i + 1).split("–");
          return { days: b.substring(0, i).split(", "), start: s, end: e };
        });
        setClassBlocks(blocks);
      } else { setClassBlocks([]); }
      setBlockDays([]); setBlockStart(""); setBlockEnd("");
    } else if (prevType === "daypicker") {
      setSelectedDays(saved ? saved.split(", ") : []);
    } else if (prevType === "sleeppicker") {
      const m = saved.match(/sleep (.+) for (.+)/);
      setBedTime(m ? m[1] : ""); setWakeTime(m ? m[2] : "");
    } else if (prevType === "workoutpicker") {
      if (saved === "none") { setWorkoutDays([]); setWorkoutSlot("i don't work out"); }
      else {
        const parts = saved.split(" – ");
        setWorkoutDays(parts[0] ? parts[0].split(", ") : []);
        setWorkoutSlot(parts[1] || "");
      }
    } else {
      setCurrent(saved || (prevType === "slider" ? "5" : ""));
    }
    setStep((s) => s - 1);
  }

  async function submitProfile(profile) {
    setLoading(true);
    try {
      const token = localStorage.getItem("token") || sessionStorage.getItem("token");
      if (!token) {
        router.push("/login");
        return;
      }
      
      const response = await fetch("/api/profile", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
          "ngrok-skip-browser-warning": "true",
        },
        body: JSON.stringify(profile),
      });

      if (response.ok) {
        // Save to localStorage as cache (will be user-specific via profile fetch)
        localStorage.setItem("campusfuel_profile", JSON.stringify(profile));
        // Refresh in-memory user profile so re-entering the survey shows saved data
        try { await refreshUser(); } catch (_) {}
        router.push("/dashboard");
      } else {
        // Get error details from response
        const errorData = await response.json().catch(() => ({ error: "Unknown error" }));
        console.error("Profile save failed:", response.status, errorData);
        throw new Error(errorData.error || `Failed to save profile (${response.status})`);
      }
    } catch (err) {
      console.error("Profile save error:", err);
      setError("Failed to save your profile. Please try again.");
      setLoading(false);
    }
  }

  const sliderVal = q.type === "slider" ? (current || "5") : "5";

  return (
    <div className={styles.page}>
      {/* Ambient orbs */}
      <div className={`${styles.orb} ${styles.orbGreen}`} />
      <div className={`${styles.orb} ${styles.orbGold}`} />
      
      {/* Header */}
      <div className={styles.topBar}>
        <Link href="/dashboard" className={styles.brand}>🌿 CampusFuel</Link>
        <span className={styles.stepCount}>{step + 1} / {STEPS.length}</span>
      </div>

      {/* Pill progress bar */}
      <div className={styles.pillBar}>
        {STEPS.map((_, i) => (
          <div
            key={i}
            className={`${styles.pill} ${i < step ? styles.pillDone : ""} ${i === step ? styles.pillActive : ""}`}
          />
        ))}
      </div>

      <div className={styles.card}>
        {/* Emoji + question */}
        <div className={styles.emoji}>{q.emoji}</div>
        <h2 className={styles.question}>{q.question}</h2>

        {/* Input */}
        <div className={styles.inputWrap}>

          {q.type === "text" && (
            <input
              key={q.key}
              type="text"
              className={styles.input}
              placeholder={q.placeholder}
              value={current}
              onChange={(e) => handleTextInputChange(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && handleNext()}
              inputMode={NUMERIC_ONLY_KEYS.has(q.key) ? "numeric" : undefined}
              pattern={NUMERIC_ONLY_KEYS.has(q.key) ? "[0-9]*" : undefined}
              autoFocus
            />
          )}

          {q.type === "textarea" && (
            <textarea
              key={q.key}
              className={styles.textarea}
              placeholder={q.placeholder}
              value={current}
              onChange={(e) => setCurrent(e.target.value)}
              rows={4}
              autoFocus
            />
          )}

          {q.type === "select" && (
            <div className={styles.options}>
              {q.options.map((opt) => (
                <button
                  key={opt}
                  className={`${styles.optBtn} ${current === opt.toLowerCase() ? styles.optActive : ""}`}
                  onClick={() => setCurrent(opt.toLowerCase())}
                  type="button"
                >
                  {opt}
                </button>
              ))}
            </div>
          )}

          {q.type === "slider" && (
            <div className={styles.sliderWrap}>
              <div className={styles.sliderLabels}>
                <span>{q.labels[0]}</span>
                <span>{q.labels[1]}</span>
              </div>
              <input
                type="range"
                min={q.min}
                max={q.max}
                value={sliderVal}
                onChange={(e) => setCurrent(e.target.value)}
                className={styles.slider}
              />
              <div className={styles.sliderVal}>{sliderVal} / {q.max}</div>
            </div>
          )}

          {q.type === "classpicker" && (
            <div className={styles.pickerWrap}>
              {/* Saved class blocks */}
              {classBlocks.length > 0 && (
                <div className={styles.classBlockList}>
                  {classBlocks.map((b, i) => (
                    <div key={i} className={styles.classBlock}>
                      <span>📅 {b.days.join(" · ")} &nbsp;·&nbsp; {b.start}–{b.end}</span>
                      <button type="button" className={styles.classBlockRemove}
                        onClick={() => setClassBlocks(prev => prev.filter((_, j) => j !== i))}>
                        ✕
                      </button>
                    </div>
                  ))}
                </div>
              )}

              {/* Builder */}
              <div className={styles.classBuilder}>
                <p className={styles.sleepLabel}>📆 Days</p>
                <div className={styles.dayRow}>
                  {DAYS.map((d) => (
                    <button key={d} type="button"
                      className={`${styles.dayBtn} ${blockDays.includes(d) ? styles.dayBtnOn : ""}`}
                      onClick={() => setBlockDays(prev =>
                        prev.includes(d) ? prev.filter(x => x !== d) : [...prev, d]
                      )}>
                      {d}
                    </button>
                  ))}
                </div>
                <div className={styles.sleepRow}>
                  <div className={styles.sleepGroup}>
                    <span className={styles.sleepLabel}>🕐 Start time</span>
                    <div className={styles.timeGrid}>
                      {q.times.map(t => (
                        <button key={t} type="button"
                          className={`${styles.timeBtn} ${blockStart === t ? styles.timeBtnOn : ""}`}
                          onClick={() => {
                            setBlockStart(t);
                            if (blockEnd && q.times.indexOf(t) >= q.times.indexOf(blockEnd)) setBlockEnd("");
                          }}>
                          {t}
                        </button>
                      ))}
                    </div>
                  </div>
                  <div className={styles.sleepDivider} />
                  <div className={styles.sleepGroup}>
                    <span className={styles.sleepLabel}>🕑 End time</span>
                    <div className={styles.timeGrid}>
                      {q.times
                        .filter(t => !blockStart || q.times.indexOf(t) > q.times.indexOf(blockStart))
                        .map(t => (
                          <button key={t} type="button"
                            className={`${styles.timeBtn} ${blockEnd === t ? styles.timeBtnOn : ""}`}
                            onClick={() => setBlockEnd(t)}>
                            {t}
                          </button>
                        ))}
                    </div>
                  </div>
                </div>
                <button
                  type="button"
                  className={styles.addClassBtn}
                  disabled={blockDays.length === 0 || !blockStart || !blockEnd}
                  onClick={() => {
                    setClassBlocks(prev => [...prev, { days: blockDays, start: blockStart, end: blockEnd }]);
                    setBlockDays([]); setBlockStart(""); setBlockEnd("");
                  }}>
                  + Add Class
                </button>
              </div>
            </div>
          )}

          {q.type === "sleeppicker" && (
            <div className={styles.pickerWrap}>
              <div className={styles.sleepRow}>
                <div className={styles.sleepGroup}>
                  <span className={styles.sleepLabel}>🌙 Bedtime</span>
                  <div className={styles.timeGrid}>
                    {q.bedTimes.map((t) => (
                      <button
                        key={t}
                        type="button"
                        className={`${styles.timeBtn} ${bedTime === t ? styles.timeBtnOn : ""}`}
                        onClick={() => setBedTime(t)}
                      >
                        {t}
                      </button>
                    ))}
                  </div>
                </div>
                <div className={styles.sleepDivider} />
                <div className={styles.sleepGroup}>
                  <span className={styles.sleepLabel}>⏰ How long?</span>
                  <div className={styles.timeGrid}>
                    {q.sleepDurations.map((d) => (
                      <button
                        key={d}
                        type="button"
                        className={`${styles.timeBtn} ${wakeTime === d ? styles.timeBtnOn : ""}`}
                        onClick={() => setWakeTime(d)}
                      >
                        {d}
                      </button>
                    ))}
                  </div>
                </div>
              </div>
              {bedTime && wakeTime && (
                <p className={styles.pickerSummary}>😴 {bedTime} · {wakeTime}</p>
              )}
            </div>
          )}

          {q.type === "workoutpicker" && (
            <div className={styles.pickerWrap}>
              <p className={styles.sleepLabel}>📆 Which days?</p>
              <div className={styles.dayRow}>
                {DAYS.map((d) => (
                  <button
                    key={d}
                    type="button"
                    className={`${styles.dayBtn} ${workoutDays.includes(d) ? styles.dayBtnOn : ""} ${workoutSlot === "i don't work out" ? styles.dayBtnDisabled : ""}`}
                    onClick={() => {
                      if (workoutSlot === "i don't work out") return;
                      setWorkoutDays((prev) =>
                        prev.includes(d) ? prev.filter((x) => x !== d) : [...prev, d]
                      );
                    }}
                  >
                    {d}
                  </button>
                ))}
              </div>
              <p className={styles.sleepLabel} style={{ marginTop: "18px" }}>⏰ What time?</p>
              <div className={styles.slotRow}>
                {WORKOUT_SLOTS.map((s) => (
                  <button
                    key={s}
                    type="button"
                    className={`${styles.slotBtn} ${workoutSlot === s.toLowerCase() ? styles.slotBtnOn : ""}`}
                    onClick={() => {
                      const val = s.toLowerCase();
                      setWorkoutSlot(val);
                      if (val === "i don't work out") setWorkoutDays([]);
                    }}
                  >
                    {s}
                  </button>
                ))}
              </div>
              {((workoutDays.length > 0 && workoutSlot && workoutSlot !== "i don't work out") || workoutSlot === "i don't work out") && (
                <p className={styles.pickerSummary}>
                  {workoutSlot === "i don't work out" ? "🛋️ No workouts" : `🏋️ ${workoutDays.join(" · ")} – ${workoutSlot}`}
                </p>
              )}
            </div>
          )}

        </div>

        {error && <p className={styles.error}>{error}</p>}

        {/* Navigation */}
        <div className={styles.nav}>
          {step > 0 && (
            <button className={styles.backBtn} onClick={handleBack} type="button">
              ← Back
            </button>
          )}
          <button
            className={styles.nextBtn}
            onClick={handleNext}
            disabled={loading}
            type="button"
          >
            {loading ? "Saving..." : isLast ? "Finish & Start AI Chat 🚀" : "Next →"}
          </button>
        </div>
      </div>

    </div>
  );
}
