/**
 * Event handlers module
 */

export function setupEventHandlers(): void {
  document.addEventListener('DOMContentLoaded', () => {
    console.log('SRT2Web loaded');
  });
}

export function showStopConfirmation(): boolean {
  return confirm('¿Estás seguro de que quieres detener el pipeline?');
}

export function setupPipelineHandlers(): void {
  const btnStop = document.getElementById('btn-stop');
  if (btnStop) {
    btnStop.addEventListener('click', () => {
      if (showStopConfirmation()) {
        console.log('Pipeline stopped by user');
      }
    });
  }
}