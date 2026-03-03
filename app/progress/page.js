"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { useApp } from "../context/AppContext";
import CampusFuelNav from "../components/Navbar/CampusFuelNav";
import Header from "../components/Header/Header";
import styles from "./progress.module.css";
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
} from "recharts";

const WORKOUT_TYPES = [
  "Strength Training", "Cardio", "HIIT", "Yoga", "Pilates",
  "Running", "Cycling", "Swimming", "Basketball", "Soccer",
  "Tennis", "Hiking", "Stretching", "Other",
];

export default function ProgressPage() {
  const router = useRouter();
  const {
    user,
    userProfile,
    weeklyMeals,
    mealsLoading,
    fetchWeeklyMeals,
    activityMetrics,
    workouts,
    fetchWorkouts,
    addWorkout,
    deleteWorkout,
  } = useApp();

  const [timeRange, setTimeRange] = useState("week");
  const [showWorkoutModal, setShowWorkoutModal] = useState(false);
  const [workoutSaving, setWorkoutSaving] = useState(false);
  const [newWorkout, setNewWorkout] = useState({
    type: "Strength Training",
    duration: "",
    notes: "",
    date: new Date().toLocaleDateString("en-CA"),
  });

  useEffect(() => {
    if (user) {
      fetchWeeklyMeals();
      fetchWorkouts();
    }
  }, [user, fetchWeeklyMeals, fetchWorkouts]);

  const weeklyData = (weeklyMeals || []).map((dayData) => {
    const date = new Date(dayData.date);
    const dayNames = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"];
    const workoutCount = workouts.filter(
      (workout) => workout.date === dayData.date
    ).length;

    return {
      day: dayNames[date.getDay()],
      calories: dayData.calories,
      protein: dayData.protein,
      workouts: workoutCount,
    };
  });

  const avgCalories =
    weeklyData.length > 0
      ? Math.round(
          weeklyData.reduce((sum, d) => sum + d.calories, 0) /
            weeklyData.length
        )
      : 0;

  const avgProtein =
    weeklyData.length > 0
      ? Math.round(
          weeklyData.reduce((sum, d) => sum + d.protein, 0) /
            weeklyData.length
        )
      : 0;

  const totalWorkouts = weeklyData.reduce((sum, d) => sum + d.workouts, 0);

  const achievements = activityMetrics.achievements || [];

  const profileMilestone =
    userProfile && Object.keys(userProfile).length > 0
      ? [
          {
            date: new Date().toLocaleDateString("en-CA"),
            title: "Completed survey profile",
            type: "profile",
          },
        ]
      : [];

  const milestones = [
    ...profileMilestone,
    ...(activityMetrics.milestones || []),
  ].sort((a, b) => new Date(b.date) - new Date(a.date));

  const engagementScore = Math.min(
    100,
    Math.round(
      (activityMetrics.loggedDays || 0) * 4 +
        (activityMetrics.currentStreak || 0) * 8
    )
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
      setNewWorkout({
        type: "Strength Training",
        duration: "",
        notes: "",
        date: new Date().toLocaleDateString("en-CA"),
      });
    }
  };

  return (
    <div className={styles.layout}>
      <CampusFuelNav />
      <div className={styles.main}>
        <Header
          title="Progress & Analytics"
          username={user?.username || ""}
        />

        <div className={styles.content}>

          {/* Summary Stats */}
          <div className={styles.summaryGrid}>
            {mealsLoading ? (
              Array.from({ length: 4 }).map((_, idx) => (
                <div key={idx} className={styles.statSkeleton} />
              ))
            ) : (
              <>
                <div className={styles.statCard}>
                  <p>Current Streak</p>
                  <p>{activityMetrics.currentStreak || 0} days</p>
                </div>

                <div className={styles.statCard}>
                  <p>Avg Calories</p>
                  <p>{avgCalories} kcal</p>
                </div>

                <div className={styles.statCard}>
                  <p>Avg Protein</p>
                  <p>{avgProtein} g</p>
                </div>

                <div className={styles.statCard}>
                  <p>Workouts</p>
                  <p>{totalWorkouts} this week</p>
                </div>
              </>
            )}
          </div>

          {/* Charts */}
          <div className={styles.chartsSection}>
            <div className={styles.chartCard}>
              <h2>Calorie Trends</h2>

              <ResponsiveContainer width="100%" height={250}>
                <BarChart data={weeklyData}>
                  <XAxis dataKey="day" />
                  <YAxis />
                  <Tooltip />
                  <Bar dataKey="calories" />
                </BarChart>
              </ResponsiveContainer>
            </div>

            <div className={styles.chartCard}>
              <h2>Protein Intake</h2>

              <ResponsiveContainer width="100%" height={250}>
                <BarChart data={weeklyData}>
                  <XAxis dataKey="day" />
                  <YAxis />
                  <Tooltip />
                  <Bar dataKey="protein" />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </div>

          {/* Achievements */}
          <div className={styles.achievementsCard}>
            <h2>Achievements</h2>

            {achievements.map((achievement) => (
              <div key={achievement.id}>
                {achievement.icon} {achievement.title}
              </div>
            ))}
          </div>

          {/* Engagement */}
          <div className={styles.engagementCard}>
            <h2>Engagement Score</h2>
            <p>{engagementScore}%</p>
          </div>
        </div>
      </div>
    </div>
  );
}