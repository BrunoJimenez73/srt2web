export interface UIConfig {
  darkMode: boolean;
  showLogs: boolean;
  refreshInterval: number;
}

export function toggleDarkMode(): void {
  console.log('Toggle dark mode');
}

export function showLogs(visible: boolean): void {
  console.log('Show logs:', visible);
}

export function setRefreshInterval(ms: number): void {
  console.log('Refresh interval:', ms);
}