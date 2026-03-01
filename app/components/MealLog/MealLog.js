"use client";

import { useApp } from "../../context/AppContext";
import styles from "./MealLog.module.css";

const mealTypeColors = {
  Breakfast: "#145A32",
  Lunch: "#C99B4C",
  Snack: "#5b8dee",
  Dinner: "#e05a5a",
};

const mealTypeIcons = {
  Breakfast: "🍳",
  Lunch: "🥗",
  Snack: "🍫",
  Dinner: "🍝",
};

export default function MealLog() {
  const { todayMeals, mealsLoading } = useApp();

  const getMealName = (meal) => {
    if (meal.items && meal.items.length > 0) {
      if (meal.items.length === 1) {
        return meal.items[0].name;
      }
      return `${meal.items[0].name} +${meal.items.length - 1} more`;
    }
    return meal.type;
  };

  return (
    <div className={styles.container}>
      <div className={styles.header}>
        <h2 className={styles.title}>Today&apos;s Meal Log</h2>
        <a href="/meals?add=true" className={styles.addBtn}>+ Add Meal</a>
      </div>
      <div className={styles.list}>
        {mealsLoading ? (
          <div className={styles.loading}>Loading meals...</div>
        ) : todayMeals.length === 0 ? (
          <div className={styles.emptyState}>No meals logged today</div>
        ) : (
          todayMeals.map((meal) => (
            <div key={meal.id || meal.timestamp} className={styles.row}>
              <div className={styles.iconCol}>
                <span className={styles.icon}>{mealTypeIcons[meal.type] || "🍽️"}</span>
              </div>
              <div className={styles.info}>
                <span className={styles.mealName}>{getMealName(meal)}</span>
                <span className={styles.meta}>
                  <span
                    className={styles.badge}
                    style={{ background: mealTypeColors[meal.type] + "22", color: mealTypeColors[meal.type] }}
                  >
                    {meal.type}
                  </span>
                  <span className={styles.time}>{meal.time}</span>
                </span>
              </div>
              <div className={styles.macros}>
                <span className={styles.macro}>
                  <span className={styles.macroLabel}>Protein</span>
                  <span className={styles.macroVal}>{meal.total?.protein || 0}g</span>
                </span>
                <span className={styles.macro}>
                  <span className={styles.macroLabel}>Carbs</span>
                  <span className={styles.macroVal}>{meal.total?.carbs || 0}g</span>
                </span>
                <span className={styles.macro}>
                  <span className={styles.macroLabel}>Fat</span>
                  <span className={styles.macroVal}>{meal.total?.fat || 0}g</span>
                </span>
              </div>
              <div className={styles.calories}>
                <span className={styles.calVal}>{meal.total?.calories || 0}</span>
                <span className={styles.calLabel}>kcal</span>
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  );
}
