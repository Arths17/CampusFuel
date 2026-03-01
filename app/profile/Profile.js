"use client";

import React, { useState, useEffect } from "react";
import Link from "next/link";
import styles from "./Profile.module.css";
import { useApp } from "../context/AppContext";

const SELECT_OPTIONS = {
  gender: ["Male", "Female", "Non-binary", "Prefer not to say"],
  goal: ["Fat loss", "Muscle gain", "Maintenance", "General health"],
  diet_type: ["Omnivore", "Vegetarian", "Vegan", "Halal", "Kosher", "Other"],
  budget: ["Low", "Medium", "Flexible"],
  cooking_access: ["Dorm microwave", "Shared kitchen", "Full kitchen", "None"],
};

function avatarUrl(name, username) {
  const initials = (name || username || "?").slice(0, 2).toUpperCase();
  return `https://ui-avatars.com/api/?name=${encodeURIComponent(initials)}&background=16a34a&color=fff&size=128&bold=true`;
}

function Profile() {
  const { user, userProfile, refreshUser } = useApp();

  const [fields, setFields] = useState({
    name: "",
    age: "",
    gender: "",
    height: "",
    weight: "",
    goal: "",
    diet_type: "",
    allergies: "",
    budget: "",
    cooking_access: "",
    cultural_prefs: "",
    extra: "",
  });
  const [saving, setSaving] = useState(false);
  const [status, setStatus] = useState(null); // { ok: bool, msg: string }

  // Populate fields whenever profile data loads
  useEffect(() => {
    if (!userProfile) return;
    setFields((prev) => ({
      ...prev,
      name: userProfile.name ?? prev.name,
      age: userProfile.age != null ? String(userProfile.age) : prev.age,
      gender: userProfile.gender ?? prev.gender,
      height: userProfile.height ?? prev.height,
      weight: userProfile.weight ?? prev.weight,
      goal: userProfile.goal ?? prev.goal,
      diet_type: userProfile.diet_type ?? prev.diet_type,
      allergies: userProfile.allergies ?? prev.allergies,
      budget: userProfile.budget ?? prev.budget,
      cooking_access: userProfile.cooking_access ?? prev.cooking_access,
      cultural_prefs: userProfile.cultural_prefs ?? prev.cultural_prefs,
      extra: userProfile.extra ?? prev.extra,
    }));
  }, [userProfile]);

  const set = (key) => (e) =>
    setFields((prev) => ({ ...prev, [key]: e.target.value }));

  const handleSubmit = async (e) => {
    e.preventDefault();
    setStatus(null);
    setSaving(true);
    try {
      const token =
        localStorage.getItem("token") || sessionStorage.getItem("token");
      const response = await fetch("/api/profile", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
          "ngrok-skip-browser-warning": "true",
        },
        body: JSON.stringify(fields),
      });
      const data = await response.json().catch(() => ({}));
      if (response.ok && data.success !== false) {
        localStorage.setItem("campusfuel_profile", JSON.stringify(fields));
        try { await refreshUser(); } catch (_) {}
        setStatus({ ok: true, msg: "Profile saved!" });
      } else {
        setStatus({ ok: false, msg: data.error || "Failed to save profile." });
      }
    } catch (err) {
      setStatus({ ok: false, msg: "Network error — please try again." });
    } finally {
      setSaving(false);
    }
  };

  const displayName = fields.name || user?.username || "";
  const username = user?.username || "";

  return (
    <div className={styles.pageWrapper}>
      <div className={styles.card}>
        {/* Header */}
        <div className={styles.header}>
          <div className={styles.avatarWrapper}>
            <img
              src={avatarUrl(displayName, username)}
              alt="Avatar"
              className={styles.avatar}
            />
          </div>
          <div>
            <h1 className={styles.title}>{displayName || "Your Profile"}</h1>
            <p className={styles.subtitle}>@{username}</p>
          </div>
        </div>

        <form className={styles.form} onSubmit={handleSubmit}>
          {/* Basic */}
          <p className={styles.sectionLabel}>Basic info</p>

          <label className={styles.label}>
            Display name
            <input
              className={styles.input}
              value={fields.name}
              onChange={set("name")}
              placeholder="e.g. Jordan"
            />
          </label>

          <label className={styles.label}>
            Username
            <input
              className={`${styles.input} ${styles.readOnly}`}
              value={username}
              readOnly
            />
          </label>

          <div className={styles.row}>
            <label className={styles.label}>
              Age
              <input
                className={styles.input}
                value={fields.age}
                onChange={set("age")}
                placeholder="e.g. 20"
                inputMode="numeric"
              />
            </label>
            <label className={styles.label}>
              Gender
              <select
                className={styles.input}
                value={fields.gender}
                onChange={set("gender")}
              >
                <option value="">— select —</option>
                {SELECT_OPTIONS.gender.map((o) => (
                  <option key={o} value={o.toLowerCase()}>{o}</option>
                ))}
              </select>
            </label>
          </div>

          <div className={styles.row}>
            <label className={styles.label}>
              Height
              <input
                className={styles.input}
                value={fields.height}
                onChange={set("height")}
                placeholder={"e.g. 5'10\""}
              />
            </label>
            <label className={styles.label}>
              Weight
              <input
                className={styles.input}
                value={fields.weight}
                onChange={set("weight")}
                placeholder="e.g. 160 lbs"
              />
            </label>
          </div>

          {/* Diet & goals */}
          <p className={styles.sectionLabel}>Diet &amp; goals</p>

          <div className={styles.row}>
            <label className={styles.label}>
              Body goal
              <select
                className={styles.input}
                value={fields.goal}
                onChange={set("goal")}
              >
                <option value="">— select —</option>
                {SELECT_OPTIONS.goal.map((o) => (
                  <option key={o} value={o.toLowerCase()}>{o}</option>
                ))}
              </select>
            </label>
            <label className={styles.label}>
              Diet type
              <select
                className={styles.input}
                value={fields.diet_type}
                onChange={set("diet_type")}
              >
                <option value="">— select —</option>
                {SELECT_OPTIONS.diet_type.map((o) => (
                  <option key={o} value={o.toLowerCase()}>{o}</option>
                ))}
              </select>
            </label>
          </div>

          <div className={styles.row}>
            <label className={styles.label}>
              Budget
              <select
                className={styles.input}
                value={fields.budget}
                onChange={set("budget")}
              >
                <option value="">— select —</option>
                {SELECT_OPTIONS.budget.map((o) => (
                  <option key={o} value={o.toLowerCase()}>{o}</option>
                ))}
              </select>
            </label>
            <label className={styles.label}>
              Cooking access
              <select
                className={styles.input}
                value={fields.cooking_access}
                onChange={set("cooking_access")}
              >
                <option value="">— select —</option>
                {SELECT_OPTIONS.cooking_access.map((o) => (
                  <option key={o} value={o.toLowerCase()}>{o}</option>
                ))}
              </select>
            </label>
          </div>

          <label className={styles.label}>
            Allergies / intolerances
            <input
              className={styles.input}
              value={fields.allergies}
              onChange={set("allergies")}
              placeholder="e.g. peanuts, gluten — or 'none'"
            />
          </label>

          <label className={styles.label}>
            Cultural food preferences
            <input
              className={styles.input}
              value={fields.cultural_prefs}
              onChange={set("cultural_prefs")}
              placeholder="e.g. South Asian — or 'none'"
            />
          </label>

          <label className={styles.label}>
            Anything else
            <textarea
              className={styles.input}
              value={fields.extra}
              onChange={set("extra")}
              placeholder="Health conditions, habits, concerns — or 'none'"
              rows={3}
            />
          </label>

          {status && (
            <p className={status.ok ? styles.msgOk : styles.msgErr}>
              {status.msg}
            </p>
          )}

          <button type="submit" className={styles.button} disabled={saving}>
            {saving ? "Saving…" : "Save changes"}
          </button>

          <Link href="/survey" className={styles.surveyLink}>
            Edit full survey →
          </Link>
        </form>
      </div>
    </div>
  );
}

export default Profile;
