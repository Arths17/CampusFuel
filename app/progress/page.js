"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { useApp } from "../context/AppContext";
import CampusFuelNav from "../components/Navbar/CampusFuelNav";
import Header from "../components/Header/Header";
import styles from "./progress.module.css";

const WORKOUT_TYPES = [
  "Strength Training", "Cardio", "HIIT", "Yoga", "Pilates",
  "Running", "Cycling", "Swimming", "Basketball", "Soccer",
  "Tennis", "Hiking", "Stretching", "Other",
];

export default function ProgressPage() {
  const router = useRouter();
  const { user, userProfile, weeklyMeals, mealsLoading, fetchWeeklyMeals, activityMetrics, workouts, fetchWorkouts, addWorkout, deleteWorkout } = useApp();
  const [timeRange, setTimeRange] = useState("week");
  const [showWorkoutModal, setShowWorkoutModal] = useState(false);
  const [workoutSaving, setWorkoutSaving] = useState(false);
  const [newWorkout, setNewWorkout] = useState({
    type: "Strength Training",
    duration: "",
    notes: "",
    date: new Date().toISOString().split("T")[0],
  });

  useEffect(() => {
    // Fetch weekly meals data when component mounts
    if (user) {
      fetchWeeklyMeals();
      fetchWorkouts();
    }
  }, [user]);

  // Transform weeklyMeals data to include day names
  const weeklyData = weeklyMeals.map((dayData) => {
    const date = new Date(dayData.date);
    const dayNames = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"];
    const workoutCount = workouts.filter((workout) => workout.date === dayData.date).length;
    return {
      day: dayNames[date.getDay()],
      calories: dayData.calories,
      protein: dayData.protein,
      workouts: workoutCount
    };
  });

  const maxCalories = weeklyData.length > 0 ? Math.max(...weeklyData.map(d => d.calories)) : 0;
  const maxProtein = weeklyData.length > 0 ? Math.max(...weeklyData.map(d => d.protein)) : 0;
  const avgCalories = weeklyData.length > 0 ? Math.round(weeklyData.reduce((sum, d) => sum + d.calories, 0) / weeklyData.length) : 0;
  const avgProtein = weeklyData.length > 0 ? Math.round(weeklyData.reduce((sum, d) => sum + d.protein, 0) / weeklyData.length) : 0;
  const totalWorkouts = weeklyData.reduce((sum, d) => sum + d.workouts, 0);
  const achievements = activityMetrics.achievements || [];
  const profileMilestone = userProfile && Object.keys(userProfile).length > 0
    ? [{ date: new Date().toISOString().split("T")[0], title: "Completed survey profile", type: "profile" }]
    : [];
  const milestones = [...profileMilestone, ...(activityMetrics.milestones || [])]
    .sort((a, b) => new Date(b.date) - new Date(a.date));
  const engagementScore = Math.min(
    100,
    Math.round((activityMetrics.loggedDays || 0) * 4 + (activityMetrics.currentStreak || 0) * 8)
  );

  const handleSaveWorkout = async () => {
    if (!newWorkout.type || !newWorkout.duration) return;
    setWorkoutSaving(true);
    const result = await addWorkout({
      ...newWorkout,
      duration: parseInt(newWorkout.duration) || 0,
      timestamp: new Date().toISOString(),
    });
    setWorkoutSaving(false);
    if (result?.success !== false) {
      setShowWorkoutModal(false);
      setNewWorkout({ type: "Strength Training", duration: "", notes: "", date: new Date().toISOString().split("T")[0] });
    }
  };

  return (
    <div className={styles.layout}>
      <div className={`${styles.orb} ${styles.orbGreen}`} />
      <div className={`${styles.orb} ${styles.orbGold}`} />
      
      <CampusFuelNav />
      <div className={styles.main}>
        <Header title="Progress & Analytics" username={user?.username || ""} />
        <div className={styles.content}>

          {/* Log Workout button */}
          <div className={styles.workoutActionRow}>
            <button className={styles.logWorkoutBtn} onClick={() => setShowWorkoutModal(true)}>
              + Log Workout
            </button>
          </div>

          {/* Summary Stats */}
          <div className={styles.summaryGrid}>
            {mealsLoading ? (
              Array.from({ length: 4 }).map((_, idx) => <div key={idx} className={styles.statSkeleton} />)
            ) : (
              <>
            <div className={styles.statCard}>
              <span className={styles.statIcon}>📅</span>
              <div className={styles.statInfo}>
                <p className={styles.statLabel}>Current Streak</p>
                <p className={styles.statValue}>{activityMetrics.currentStreak || 0} days</p>
              </div>
            </div>
            <div className={styles.statCard}>
              <span className={styles.statIcon}>🔥</span>
              <div className={styles.statInfo}>
                <p className={styles.statLabel}>Avg. Calories</p>
                <p className={styles.statValue}>{avgCalories} kcal</p>
              </div>
            </div>
            <div className={styles.statCard}>
              <span className={styles.statIcon}>💪</span>
              <div className={styles.statInfo}>
                <p className={styles.statLabel}>Avg. Protein</p>
                <p className={styles.statValue}>{avgProtein}g</p>
              </div>
            </div>
            <div className={styles.statCard}>
              <span className={styles.statIcon}>🏋️</span>
              <div className={styles.statInfo}>
                <p className={styles.statLabel}>Workouts</p>
                <p className={styles.statValue}>{totalWorkouts} this week</p>
              </div>
            </div>
              </>
            )}
          </div>

          {/* Charts Section */}
          <div className={styles.chartsSection}>
            <div className={styles.chartCard}>
              <div className={styles.chartHeader}>
                <h2 className={styles.chartTitle}>📊 Calorie Trends</h2>
                <div className={styles.timeRangeButtons}>
                  <button 
                    className={`${styles.timeButton} ${timeRange === "week" ? styles.active : ""}`}
                    onClick={() => setTimeRange("week")}
                  >
                    Week
                  </button>
                  <button 
                    className={`${styles.timeButton} ${timeRange === "month" ? styles.active : ""}`}
                    onClick={() => setTimeRange("month")}
                  >
                    Month
                  </button>
                  <button 
                    className={`${styles.timeButton} ${timeRange === "year" ? styles.active : ""}`}
                    onClick={() => setTimeRange("year")}
                  >
                    Year
                  </button>
                </div>
              </div>
              <div className={styles.chart}>
                {mealsLoading ? (
                  Array.from({ length: 7 }).map((_, idx) => (
                    <div key={idx} className={styles.barGroup}>
                      <div className={styles.barContainer}><div className={styles.barSkeleton} /></div>
                      <span className={styles.barLabel}>•</span>
                    </div>
                  ))
                ) : weeklyData.length === 0 ? (
                  <div className={styles.chartNote}>No meal data available yet. Start logging meals!</div>
                ) : (
                  weeklyData.map((data, idx) => (
                    <div key={idx} className={styles.barGroup}>
                      <div className={styles.barContainer}>
                        <div 
                          className={styles.bar}
                          style={{ height: `${maxCalories > 0 ? (data.calories / maxCalories) * 100 : 0}%` }}
                          title={`${data.calories} kcal`}
                        />
                      </div>
                      <span className={styles.barLabel}>{data.day}</span>
                    </div>
                  ))
                )}
              </div>
              <p className={styles.chartNote}>Goal: 2400 kcal/day</p>
            </div>

            <div className={styles.chartCard}>
              <h2 className={styles.chartTitle}>💪 Protein Intake</h2>
              <div className={styles.chart}>
                {mealsLoading ? (
                  Array.from({ length: 7 }).map((_, idx) => (
                    <div key={idx} className={styles.barGroup}>
                      <div className={styles.barContainer}><div className={styles.barSkeleton} /></div>
                      <span className={styles.barLabel}>•</span>
                    </div>
                  ))
                ) : weeklyData.length === 0 ? (
                  <div className={styles.chartNote}>No meal data available yet. Start logging meals!</div>
                ) : (
                  weeklyData.map((data, idx) => (
                    <div key={idx} className={styles.barGroup}>
                      <div className={styles.barContainer}>
                        <div 
                          className={`${styles.bar} ${styles.barProtein}`}
                          style={{ height: `${maxProtein > 0 ? (data.protein / maxProtein) * 100 : 0}%` }}
                          title={`${data.protein}g`}
                        />
                      </div>
                      <span className={styles.barLabel}>{data.day}</span>
                    </div>
                  ))
                )}
              </div>
              <p className={styles.chartNote}>Goal: 108g/day</p>
            </div>
          </div>

          {/* Achievements */}
          <div className={styles.achievementsCard}>
            <h2 className={styles.achievementsTitle}>🏆 Achievements</h2>
            <div className={styles.achievementsGrid}>
              {achievements.map((achievement) => (
                <div 
                  key={achievement.id} 
                  className={`${styles.achievement} ${achievement.unlocked ? styles.unlocked : styles.locked}`}
                >
                  <div className={styles.achievementIcon}>{achievement.icon}</div>
                  <div className={styles.achievementInfo}>
                    <h3 className={styles.achievementTitle}>{achievement.title}</h3>
                    <p className={styles.achievementDesc}>{achievement.description}</p>
                  </div>
                  {achievement.unlocked && <span className={styles.unlockedBadge}>✓</span>}
                </div>
              ))}
            </div>
          </div>

          {/* Timeline */}
          <div className={styles.timelineCard}>
            <h2 className={styles.timelineTitle}>📜 Your Journey</h2>
            <div className={styles.timeline}>
              {milestones.length === 0 ? (
                <div className={styles.timelineItem}>
                  <div className={styles.timelineDot} />
                  <div className={styles.timelineContent}>
                    <p className={styles.timelineDate}>No milestones yet</p>
                    <p className={styles.timelineText}>Log your first meal to start your journey timeline.</p>
                  </div>
                </div>
              ) : milestones.map((milestone, idx) => (
                <div key={idx} className={styles.timelineItem}>
                  <div className={styles.timelineDot} />
                  <div className={styles.timelineContent}>
                    <p className={styles.timelineDate}>{milestone.date}</p>
                    <p className={styles.timelineText}>{milestone.title}</p>
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Engagement Health */}
          <div className={styles.engagementCard}>
            <h2 className={styles.engagementTitle}>💚 Engagement Health</h2>
            <p className={styles.engagementDesc}>
              You&apos;re doing great! Your consistent logging and engagement show strong commitment.
            </p>
            <div className={styles.engagementMeter}>
              <div className={styles.meterBar}>
                <div className={styles.meterFill} style={{ width: `${engagementScore}%` }} />
              </div>
              <p className={styles.meterLabel}>{engagementScore}% Engagement Score</p>
            </div>
            <div className={styles.engagementTips}>
              <div className={styles.engagementTip}>
                <span className={styles.tipIcon}>✅</span>
                <span className={styles.tipText}>Regular meal logging</span>
              </div>
              <div className={styles.engagementTip}>
                <span className={styles.tipIcon}>✅</span>
                <span className={styles.tipText}>Active AI coach usage</span>
              </div>
              <div className={styles.engagementTip}>
                <span className={styles.tipIcon}>⚠️</span>
                <span className={styles.tipText}>Try adding more workout tracking</span>
              </div>
            </div>
          </div>

          {/* Workout Log */}
          <div className={styles.workoutCard}>
            <h2 className={styles.workoutCardTitle}>🏋️ Workout Log</h2>
            {workouts.length === 0 ? (
              <p className={styles.workoutEmpty}>No workouts logged yet. Hit &quot;Log Workout&quot; to get started!</p>
            ) : (
              <div className={styles.workoutList}>
                {workouts.slice(0, 10).map((w, i) => (
                  <div key={w.id || i} className={styles.workoutRow}>
                    <div className={styles.workoutRowLeft}>
                      <span className={styles.workoutType}>{w.type}</span>
                      {w.notes && <span className={styles.workoutNotes}>{w.notes}</span>}
                    </div>
                    <div className={styles.workoutRowRight}>
                      <span className={styles.workoutDuration}>⏱ {w.duration} min</span>
                      <span className={styles.workoutDate}>{w.date}</span>
                      <button
                        className={styles.workoutDeleteBtn}
                        onClick={() => deleteWorkout(w.id)}
                        title="Delete"
                      >✕</button>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>

        </div>
      </div>

      {/* Log Workout Modal */}
      {showWorkoutModal && (
        <div className={styles.modal} onClick={(e) => e.target === e.currentTarget && setShowWorkoutModal(false)}>
          <div className={styles.modalContent}>
            <button className={styles.modalClose} onClick={() => setShowWorkoutModal(false)}>×</button>
            <h2 className={styles.modalTitle}>🏋️ Log Workout</h2>

            <div className={styles.formGroup}>
              <label className={styles.formLabel}>Workout Type</label>
              <select
                className={styles.formSelect}
                value={newWorkout.type}
                onChange={(e) => setNewWorkout({ ...newWorkout, type: e.target.value })}
              >
                {WORKOUT_TYPES.map((t) => <option key={t} value={t}>{t}</option>)}
              </select>
            </div>

            <div className={styles.formGroup}>
              <label className={styles.formLabel}>Duration (minutes)</label>
              <input
                type="number"
                min="1"
                max="300"
                className={styles.formInput}
                placeholder="e.g. 45"
                value={newWorkout.duration}
                onChange={(e) => setNewWorkout({ ...newWorkout, duration: e.target.value })}
              />
            </div>

            <div className={styles.formGroup}>
              <label className={styles.formLabel}>Date</label>
              <input
                type="date"
                className={styles.formInput}
                value={newWorkout.date}
                onChange={(e) => setNewWorkout({ ...newWorkout, date: e.target.value })}
              />
            </div>

            <div className={styles.formGroup}>
              <label className={styles.formLabel}>Notes (optional)</label>
              <input
                type="text"
                className={styles.formInput}
                placeholder="e.g. felt strong today, new PR on bench"
                value={newWorkout.notes}
                onChange={(e) => setNewWorkout({ ...newWorkout, notes: e.target.value })}
              />
            </div>

            <div className={styles.modalActions}>
              <button className={styles.cancelButton} onClick={() => setShowWorkoutModal(false)}>Cancel</button>
              <button
                className={styles.saveButton}
                onClick={handleSaveWorkout}
                disabled={!newWorkout.type || !newWorkout.duration || workoutSaving}
              >
                {workoutSaving ? "Saving..." : "Save Workout"}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
