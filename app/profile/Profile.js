// pages/Profile.js  OR  components/Profile/Profile.js
"use client";

import React, { useState } from "react";
import styles from "./Profile.module.css";

function Profile() {
  const [name, setName] = useState("Jane Doe");
  const [username, setUsername] = useState("janedoe123");
  const [email, setEmail] = useState("jane@example.com");
  const [password, setPassword] = useState("********");
  const [imageUrl, setImageUrl] = useState(
    "https://avatars.dicebear.com/api/initials/JD.svg"
  );

  const handleSubmit = (e) => {
    e.preventDefault();
    // TODO: save profile changes
    console.log("Saving profile:", {
      name,
      username,
      email,
      password,
      imageUrl,
    });
  };

  return (
    <div className={styles.pageWrapper}>
      <div className={styles.card}>
        <div className={styles.header}>
          <div className={styles.avatarWrapper}>
            <img src={imageUrl} alt="Profile" className={styles.avatar} />
          </div>
          <div>
            <h1 className={styles.title}>{name}</h1>
            <p className={styles.subtitle}>@{username}</p>
          </div>
        </div>

        <form className={styles.form} onSubmit={handleSubmit}>
          <label className={styles.label}>
            Full name
            <input
              className={styles.input}
              value={name}
              onChange={(e) => setName(e.target.value)}
            />
          </label>

          <label className={styles.label}>
            Username
            <input
              className={styles.input}
              value={username}
              onChange={(e) => setUsername(e.target.value)}
            />
          </label>

          <label className={styles.label}>
            Email
            <input
              type="email"
              className={styles.input}
              value={email}
              onChange={(e) => setEmail(e.target.value)}
            />
          </label>

          <label className={styles.label}>
            Password
            <input
              type="password"
              className={styles.input}
              value={password}
              onChange={(e) => setPassword(e.target.value)}
            />
          </label>

          <label className={styles.label}>
            Profile image URL
            <input
              className={styles.input}
              value={imageUrl}
              onChange={(e) => setImageUrl(e.target.value)}
            />
          </label>

          <button type="submit" className={styles.button}>
            Save changes
          </button>
        </form>
      </div>
    </div>
  );
}

export default Profile;
