/**
 * Clock utility - Centralized time display updates
 * Elimina intervalos duplicados de actualización del reloj
 */

let clockInterval: ReturnType<typeof setInterval> | null = null;
let initialized = false;

export function startClockUpdates(): void {
  if (initialized) return;
  initialized = true;

  updateClock(); // Update immediately

  clockInterval = setInterval(() => {
    updateClock();
  }, 1000);
}

export function stopClockUpdates(): void {
  if (clockInterval) {
    clearInterval(clockInterval);
    clockInterval = null;
  }
  initialized = false;
}

function updateClock(): void {
  const clock = document.getElementById("live-clock");
  if (clock) {
    clock.textContent = new Date().toLocaleTimeString("en-US", {
      hour12: false,
    });
  }
}

// Alias for compatibility
export const startClock = startClockUpdates;
export const stopClock = stopClockUpdates;
