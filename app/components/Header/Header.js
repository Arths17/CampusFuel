import Link from "next/link";
import styles from "./Header.module.css";

export default function Header({ title = "Dashboard", username = "" }) {
  const initials = username
    ? username.slice(0, 2).toUpperCase()
    : "?";
  const today = new Date().toLocaleDateString("en-US", {
    weekday: "long",
    year: "numeric",
    month: "long",
    day: "numeric",
  });

  return (
    <header className={styles.header}>
      <div className={styles.left}>
        <h1 className={styles.title}>{title}</h1>
        <p className={styles.date}>{today}</p>
      </div>
      <div className={styles.right}>
        <div className={styles.searchBar}>
          <span className={styles.searchIcon}>🔍</span>
          <input
            type="text"
            placeholder="Search foods..."
            className={styles.searchInput}
          />
        </div>
        <button className={styles.addBtn}>+ Log Meal</button>
        <Link href="/Profile Page" className={styles.avatarLink}>
          <div className={styles.avatar}>
            <span>{initials}</span>
          </div>
        </Link>
      </div>
    </header>
  );
}
