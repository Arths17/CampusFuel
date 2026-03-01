"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import CampusFuelNav from "../components/Navbar/CampusFuelNav";
import Header from "../components/Header/Header";
import styles from "./nutrition.module.css";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || '';

export default function NutritionPage() {
  const router = useRouter();
  const [username, setUsername] = useState(null);
  const [dailyGoals, setDailyGoals] = useState({
    calories: 2400,
    protein_g: 108,
    carbs_g: 275,
    fat_g: 90,
    fiber_g: 38,
  });

  useEffect(() => {
    const token = localStorage.getItem("token") || sessionStorage.getItem("token");
    if (!token) { 
      router.push("/login"); 
      return; 
    }
    fetch(`${API_BASE_URL}/api/me`, {
      headers: { "Authorization": `Bearer ${token}`, "ngrok-skip-browser-warning": "true" },
    })
      .then((r) => r.json())
      .then((data) => {
        if (!data.success) {
          router.push("/login");
        } else {
          setUsername(data.username);
        }
      })
      .catch(() => router.push("/login"));
  }, [router]);

  return (
    <div className={styles.layout}>
      <div className={`${styles.orb} ${styles.orbGreen}`} />
      <div className={`${styles.orb} ${styles.orbGold}`} />
      
      <CampusFuelNav />
      <div className={styles.main}>
        <Header title="Nutrition Database" username={username || ""} />
        <div className={styles.content}>

          {/* Daily Goals Overview */}
          <div className={styles.goalsCard}>
            <h2 className={styles.goalsTitle}>📊 Your Daily Goals</h2>
            <div className={styles.goalsGrid}>
              <div className={styles.goalItem}>
                <span className={styles.goalIcon}>🔥</span>
                <span className={styles.goalLabel}>Calories</span>
                <span className={styles.goalValue}>{dailyGoals.calories} kcal</span>
              </div>
              <div className={styles.goalItem}>
                <span className={styles.goalIcon}>💪</span>
                <span className={styles.goalLabel}>Protein</span>
                <span className={styles.goalValue}>{dailyGoals.protein_g}g</span>
              </div>
              <div className={styles.goalItem}>
                <span className={styles.goalIcon}>🌾</span>
                <span className={styles.goalLabel}>Carbs</span>
                <span className={styles.goalValue}>{dailyGoals.carbs_g}g</span>
              </div>
              <div className={styles.goalItem}>
                <span className={styles.goalIcon}>🥑</span>
                <span className={styles.goalLabel}>Fat</span>
                <span className={styles.goalValue}>{dailyGoals.fat_g}g</span>
              </div>
              <div className={styles.goalItem}>
                <span className={styles.goalIcon}>🥦</span>
                <span className={styles.goalLabel}>Fiber</span>
                <span className={styles.goalValue}>{dailyGoals.fiber_g}g</span>
              </div>
            </div>
          </div>

          {/* Educational Tips */}
          <div className={styles.tipsCard}>
            <h3 className={styles.tipsTitle}>💡 Nutrition Tips</h3>
            <div className={styles.tipsList}>
              <div className={styles.tip}>
                <span className={styles.tipIcon}>🥛</span>
                <p className={styles.tipText}>Aim for 0.8-1g of protein per kg of body weight daily for maintenance.</p>
              </div>
              <div className={styles.tip}>
                <span className={styles.tipIcon}>🥦</span>
                <p className={styles.tipText}>Fill half your plate with vegetables for optimal fiber and micronutrient intake.</p>
              </div>
              <div className={styles.tip}>
                <span className={styles.tipIcon}>💧</span>
                <p className={styles.tipText}>Drink at least 8 glasses of water daily for proper hydration.</p>
              </div>
            </div>
          </div>

        </div>
      </div>
    </div>
  );
}
