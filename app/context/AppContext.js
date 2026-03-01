"use client";

import { createContext, useContext, useState, useEffect } from "react";
import { useRouter, usePathname } from "next/navigation";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || '';

const AppContext = createContext();

async function parseApiResponse(response, fallbackMessage) {
  const rawText = await response.text();
  let data = null;

  try {
    data = rawText ? JSON.parse(rawText) : {};
  } catch {
    data = null;
  }

  const explicitError =
    data?.error ||
    data?.detail ||
    data?.message ||
    data?.error_code;

  if (!response.ok || data?.success === false) {
    const fallback = `${fallbackMessage} (${response.status})`;
    const nonJsonHint = !data && rawText ? ` ${rawText.slice(0, 120)}` : "";
    return {
      ok: false,
      error: explicitError || `${fallback}${nonJsonHint}`,
      data: data || {},
    };
  }

  return { ok: true, data: data || {} };
}

function getLastNDates(n) {
  const dates = [];
  for (let i = n - 1; i >= 0; i--) {
    const date = new Date();
    date.setDate(date.getDate() - i);
    dates.push(date.toISOString().split("T")[0]);
  }
  return dates;
}

function deriveWeeklyMeals(meals) {
  const dates = getLastNDates(7);
  return dates.map((date) => {
    const dayMeals = meals.filter((meal) => meal.date === date);
    const totals = dayMeals.reduce(
      (acc, meal) => ({
        calories: acc.calories + (meal.total?.calories || 0),
        protein: acc.protein + (meal.total?.protein || 0),
        carbs: acc.carbs + (meal.total?.carbs || 0),
        fat: acc.fat + (meal.total?.fat || 0),
      }),
      { calories: 0, protein: 0, carbs: 0, fat: 0 }
    );
    return { date, ...totals };
  });
}

function deriveTodayMeals(meals) {
  const today = new Date().toISOString().split("T")[0];
  return meals.filter((meal) => meal.date === today);
}

function deriveActivityMetrics(meals) {
  const byDate = meals.reduce((acc, meal) => {
    if (!meal?.date) return acc;
    if (!acc[meal.date]) acc[meal.date] = [];
    acc[meal.date].push(meal);
    return acc;
  }, {});

  const datesLogged = Object.keys(byDate).sort();
  const firstLoggedDate = datesLogged[0] || null;
  const totalMeals = meals.length;
  const loggedDays = datesLogged.length;

  let currentStreak = 0;
  const cursor = new Date();
  const todayKey = cursor.toISOString().split("T")[0];
  // If no meals today yet, start counting from yesterday so the streak isn't reset
  if (!byDate[todayKey] || byDate[todayKey].length === 0) {
    cursor.setDate(cursor.getDate() - 1);
  }
  while (true) {
    const key = cursor.toISOString().split("T")[0];
    if (byDate[key] && byDate[key].length > 0) {
      currentStreak += 1;
      cursor.setDate(cursor.getDate() - 1);
    } else {
      break;
    }
  }

  const weeklyTotals = deriveWeeklyMeals(meals);
  const proteinGoalDays = weeklyTotals.filter((d) => d.protein >= 108).length;
  const calorieGoalDays = weeklyTotals.filter((d) => d.calories >= 1800 && d.calories <= 2400).length;
  // Exclude today from perfectWeek if no meals have been logged today yet
  const today = new Date().toISOString().split("T")[0];
  const relevantDays = weeklyTotals.filter((d) => d.date < today || (byDate[d.date] && byDate[d.date].length > 0));
  const perfectWeek = relevantDays.length >= 6 && relevantDays.every((d) => d.calories > 0);

  const achievements = [
    {
      id: 1,
      icon: "🔥",
      title: "7 Day Streak",
      description: "Logged meals for 7 days in a row",
      unlocked: currentStreak >= 7,
    },
    {
      id: 2,
      icon: "💪",
      title: "Protein Goal",
      description: "Hit protein goal 3+ days this week",
      unlocked: proteinGoalDays >= 3,
    },
    {
      id: 3,
      icon: "🥗",
      title: "Healthy Week",
      description: "Stayed in calorie range for 4+ days",
      unlocked: calorieGoalDays >= 4,
    },
    {
      id: 4,
      icon: "🏁",
      title: "First Meal Logged",
      description: "Logged your first meal",
      unlocked: totalMeals >= 1,
    },
    {
      id: 5,
      icon: "🗓️",
      title: "Consistent Logger",
      description: "Logged meals on 14 different days",
      unlocked: loggedDays >= 14,
    },
    {
      id: 6,
      icon: "🌟",
      title: "Perfect Week",
      description: "Logged meals every day this week",
      unlocked: perfectWeek,
    },
  ];

  const milestones = [];
  if (firstLoggedDate) {
    milestones.push({ date: firstLoggedDate, title: "Started using CampusFuel", type: "start" });
  }
  if (totalMeals >= 1) {
    const firstMeal = meals
      .slice()
      .sort((a, b) => new Date(a.timestamp || 0) - new Date(b.timestamp || 0))[0];
    if (firstMeal?.date) {
      milestones.push({ date: firstMeal.date, title: "Logged first meal", type: "meal" });
    }
  }
  if (currentStreak >= 7) {
    milestones.push({ date: new Date().toISOString().split("T")[0], title: "Reached 7-day streak", type: "streak" });
  }
  if (proteinGoalDays >= 3) {
    milestones.push({ date: new Date().toISOString().split("T")[0], title: "Hit protein target 3+ days", type: "protein" });
  }

  const sortedMilestones = milestones
    .filter((m) => m.date)
    .sort((a, b) => new Date(b.date) - new Date(a.date));

  return {
    totalMeals,
    loggedDays,
    currentStreak,
    achievements,
    milestones: sortedMilestones,
  };
}

export function AppProvider({ children }) {
  const router = useRouter();
  const pathname = usePathname();
  
  const [user, setUser] = useState(null);
  const [userProfile, setUserProfile] = useState(null);
  const [allMeals, setAllMeals] = useState([]);
  const [todayMeals, setTodayMeals] = useState([]);
  const [weeklyMeals, setWeeklyMeals] = useState([]);
  const [waterIntake, setWaterIntakeState] = useState(0);
  const [workouts, setWorkouts] = useState([]);
  const [workoutsLoading, setWorkoutsLoading] = useState(false);
  const [activityMetrics, setActivityMetrics] = useState({
    totalMeals: 0,
    loggedDays: 0,
    currentStreak: 0,
    achievements: [],
    milestones: [],
  });
  const [loading, setLoading] = useState(true);
  const [mealsLoading, setMealsLoading] = useState(false);

  const syncMealState = (meals) => {
    const normalizedMeals = (meals || [])
      .map((meal) => ({
        ...meal,
        id: meal.id || meal.timestamp,
      }))
      .sort((a, b) => new Date(b.timestamp || 0) - new Date(a.timestamp || 0));

    setAllMeals(normalizedMeals);
    setTodayMeals(deriveTodayMeals(normalizedMeals));
    setWeeklyMeals(deriveWeeklyMeals(normalizedMeals));
    setActivityMetrics(deriveActivityMetrics(normalizedMeals));
  };

  // Initialize auth and fetch user data
  useEffect(() => {
    const publicPaths = ["/", "/login", "/signup", "/survey"];
    if (publicPaths.includes(pathname)) {
      setLoading(false);
      return;
    }

    setLoading(true);
    fetchUserData();
  }, [pathname, router]);

  const fetchUserData = async (token) => {
    const resolvedToken = token || localStorage.getItem("token") || sessionStorage.getItem("token");
    if (!resolvedToken) {
      router.push("/login");
      setLoading(false);
      return;
    }
    try {
      const response = await fetch(`${API_BASE_URL}/api/me`, {
        headers: {
          "Authorization": `Bearer ${resolvedToken}`,
          "ngrok-skip-browser-warning": "true"
        }
      });
      const data = await response.json();
      
      if (!data.success) {
        localStorage.removeItem("token");
        sessionStorage.removeItem("token");
        setUser(null);
        setUserProfile(null);
        router.push("/login");
        return;
      }

      setUser({
        username: data.username,
        token: resolvedToken
      });
      setUserProfile(data.profile || {});
      
      await Promise.all([
        refreshMealData(resolvedToken),
        fetchWaterIntake(resolvedToken),
        fetchWorkouts(resolvedToken),
      ]);
    } catch (error) {
      console.error("Failed to fetch user data:", error);
      localStorage.removeItem("token");
      sessionStorage.removeItem("token");
      setUser(null);
      setUserProfile(null);
      router.push("/login");
    } finally {
      setLoading(false);
    }
  };

  const refreshMealData = async (token) => {
    const userToken = token || user?.token;
    if (!userToken) return;

    setMealsLoading(true);
    try {
      const response = await fetch(`${API_BASE_URL}/api/meals`, {
        headers: {
          "Authorization": `Bearer ${userToken}`,
          "ngrok-skip-browser-warning": "true"
        }
      });
      const parsed = await parseApiResponse(response, "Failed to load meals");

      if (parsed.ok && parsed.data?.success !== false) {
        const serverMeals = parsed.data?.meals || [];
        syncMealState(serverMeals);
      }
      // On error, silently preserve existing meal state rather than wiping it
    } catch (error) {
      console.error("Failed to refresh meals:", error);
      // Don't wipe existing meals on network/parse errors
    } finally {
      setMealsLoading(false);
    }
  };

  const fetchTodayMeals = async (token) => {
    await refreshMealData(token);
  };

  const fetchMealsByDate = async (date) => {
    return allMeals.filter((meal) => meal.date === date);
  };

  const fetchWeeklyMeals = async () => {
    await refreshMealData();
  };

  const fetchWaterIntake = async (token) => {
    const userToken = token || user?.token;
    if (!userToken) return;

    const date = new Date().toISOString().split("T")[0];
    try {
      const response = await fetch(`${API_BASE_URL}/api/water?date=${date}`, {
        headers: {
          "Authorization": `Bearer ${userToken}`,
          "ngrok-skip-browser-warning": "true"
        }
      });
      const parsed = await parseApiResponse(response, "Failed to load water intake");
      if (parsed.ok && parsed.data?.success !== false) {
        setWaterIntakeState(Number(parsed.data?.glasses || 0));
        return;
      }
      setWaterIntakeState(0);
    } catch {
      setWaterIntakeState(0);
    }
  };

  const saveWaterIntake = async (glasses) => {
    const token = user?.token;
    if (!token) return { success: false, error: "Not authenticated" };

    const date = new Date().toISOString().split("T")[0];
    try {
      const response = await fetch(`${API_BASE_URL}/api/water`, {
        method: "POST",
        headers: {
          "Authorization": `Bearer ${token}`,
          "Content-Type": "application/json",
          "ngrok-skip-browser-warning": "true"
        },
        body: JSON.stringify({ date, glasses })
      });
      const parsed = await parseApiResponse(response, "Failed to save water intake");
      if (parsed.ok && parsed.data?.success !== false) {
        setWaterIntakeState(Number(parsed.data?.glasses ?? glasses ?? 0));
        return { success: true };
      }
      return { success: false, error: parsed.error || "Failed to save water intake" };
    } catch (error) {
      return { success: false, error: error.message || "Failed to save water intake" };
    }
  };

  const fetchWorkouts = async (token) => {
    const userToken = token || user?.token;
    if (!userToken) return;

    setWorkoutsLoading(true);
    try {
      const response = await fetch(`${API_BASE_URL}/api/workouts`, {
        headers: {
          "Authorization": `Bearer ${userToken}`,
          "ngrok-skip-browser-warning": "true"
        }
      });
      const parsed = await parseApiResponse(response, "Failed to load workouts");
      if (parsed.ok && parsed.data?.success !== false) {
        setWorkouts(parsed.data?.workouts || []);
      } else {
        setWorkouts([]);
      }
    } catch {
      setWorkouts([]);
    } finally {
      setWorkoutsLoading(false);
    }
  };

  const addWorkout = async (workoutData) => {
    const token = user?.token;
    if (!token) return { success: false, error: "Not authenticated" };

    try {
      const response = await fetch(`${API_BASE_URL}/api/workouts`, {
        method: "POST",
        headers: {
          "Authorization": `Bearer ${token}`,
          "Content-Type": "application/json",
          "ngrok-skip-browser-warning": "true"
        },
        body: JSON.stringify(workoutData)
      });
      const parsed = await parseApiResponse(response, "Failed to save workout");
      if (parsed.ok && parsed.data?.success !== false) {
        await fetchWorkouts(token);
        return { success: true };
      }
      return { success: false, error: parsed.error || "Failed to save workout" };
    } catch (error) {
      return { success: false, error: error.message || "Failed to save workout" };
    }
  };

  const deleteWorkout = async (workoutId) => {
    const token = user?.token;
    if (!token) return { success: false, error: "Not authenticated" };

    try {
      const response = await fetch(`${API_BASE_URL}/api/workouts/${encodeURIComponent(workoutId)}`, {
        method: "DELETE",
        headers: {
          "Authorization": `Bearer ${token}`,
          "ngrok-skip-browser-warning": "true"
        }
      });
      const parsed = await parseApiResponse(response, "Failed to delete workout");
      if (parsed.ok && parsed.data?.success !== false) {
        await fetchWorkouts(token);
        return { success: true };
      }
      return { success: false, error: parsed.error || "Failed to delete workout" };
    } catch (error) {
      return { success: false, error: error.message || "Failed to delete workout" };
    }
  };

  const addMeal = async (mealData) => {
    const token = user?.token;
    if (!token) return { success: false, error: "Not authenticated" };

    // Optimistic update: add meal to local state immediately
    const optimisticMeal = {
      ...mealData,
      id: mealData.id || mealData.timestamp,
    };
    const previousMeals = allMeals;
    syncMealState([optimisticMeal, ...allMeals]);

    try {
      const response = await fetch(`${API_BASE_URL}/api/meals`, {
        method: 'POST',
        headers: {
          "Authorization": `Bearer ${token}`,
          "Content-Type": "application/json",
          "ngrok-skip-browser-warning": "true"
        },
        body: JSON.stringify(mealData)
      });
      const parsed = await parseApiResponse(response, "Failed to save meal");
      
      if (parsed.ok && parsed.data?.success !== false) {
        // Sync with server to get authoritative data (non-blocking, errors don't wipe state)
        refreshMealData(token).catch(() => {});
        return { success: true };
      }
      // Rollback optimistic update on failure
      syncMealState(previousMeals);
      return { success: false, error: parsed.error || "Failed to save meal" };
    } catch (error) {
      console.error("Failed to add meal:", error);
      // Rollback optimistic update on exception
      syncMealState(previousMeals);
      return { success: false, error: error.message };
    }
  };

  const updateMeal = async (mealId, mealData) => {
    const token = user?.token;
    if (!token) return { success: false, error: "Not authenticated" };

    try {
      const response = await fetch(`${API_BASE_URL}/api/meals/${encodeURIComponent(mealId)}`, {
        method: "PUT",
        headers: {
          "Authorization": `Bearer ${token}`,
          "Content-Type": "application/json",
          "ngrok-skip-browser-warning": "true"
        },
        body: JSON.stringify(mealData)
      });
      const parsed = await parseApiResponse(response, "Failed to update meal");

      if (parsed.ok && parsed.data?.success !== false) {
        await refreshMealData(token);
        return { success: true };
      }
      return { success: false, error: parsed.error || "Failed to update meal" };
    } catch (error) {
      console.error("Failed to update meal:", error);
      return { success: false, error: error.message };
    }
  };

  const deleteMeal = async (mealId) => {
    const token = user?.token;
    if (!token) return { success: false, error: "Not authenticated" };

    try {
      const response = await fetch(`${API_BASE_URL}/api/meals/${encodeURIComponent(mealId)}`, {
        method: 'DELETE',
        headers: {
          "Authorization": `Bearer ${token}`,
          "ngrok-skip-browser-warning": "true"
        }
      });
      const parsed = await parseApiResponse(response, "Failed to delete meal");
      
      if (parsed.ok && parsed.data?.success !== false) {
        await refreshMealData(token);
        return { success: true };
      }
      return { success: false, error: parsed.error || "Failed to delete meal" };
    } catch (error) {
      console.error("Failed to delete meal:", error);
      return { success: false, error: error.message };
    }
  };

  const logout = () => {
    localStorage.removeItem("token");
    sessionStorage.removeItem("token");
    setUser(null);
    setUserProfile(null);
    setAllMeals([]);
    setTodayMeals([]);
    setWeeklyMeals([]);
    setWaterIntakeState(0);
    setWorkouts([]);
    setActivityMetrics({
      totalMeals: 0,
      loggedDays: 0,
      currentStreak: 0,
      achievements: [],
      milestones: [],
    });
    router.push("/login");
  };

  const value = {
    user,
    userProfile,
    allMeals,
    todayMeals,
    weeklyMeals,
    activityMetrics,
    waterIntake,
    workouts,
    workoutsLoading,
    loading,
    mealsLoading,
    refreshMealData,
    fetchTodayMeals,
    fetchMealsByDate,
    fetchWeeklyMeals,
    fetchWaterIntake,
    saveWaterIntake,
    fetchWorkouts,
    addWorkout,
    deleteWorkout,
    addMeal,
    updateMeal,
    deleteMeal,
    logout,
    refreshUser: fetchUserData
  };

  return <AppContext.Provider value={value}>{children}</AppContext.Provider>;
}

export function useApp() {
  const context = useContext(AppContext);
  if (context === undefined) {
    throw new Error("useApp must be used within an AppProvider");
  }
  return context;
}
