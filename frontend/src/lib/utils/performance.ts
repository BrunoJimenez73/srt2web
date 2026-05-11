/**
 * Utilidades de rendimiento y optimización
 */

/**
 * Debounce function para limitar la frecuencia de ejecución
 */
export function debounce<T extends (...args: unknown[]) => unknown>(
  func: T,
  wait: number,
): (...args: Parameters<T>) => void {
  let timeout: ReturnType<typeof setTimeout> | null = null;

  return (...args: Parameters<T>) => {
    if (timeout) clearTimeout(timeout);
    timeout = setTimeout(() => func(...args), wait);
  };
}

/**
 * Throttle function para limitar la frecuencia de ejecución
 */
export function throttle<T extends (...args: unknown[]) => unknown>(
  func: T,
  limit: number,
): (...args: Parameters<T>) => void {
  let inThrottle = false;

  return (...args: Parameters<T>) => {
    if (!inThrottle) {
      func(...args);
      inThrottle = true;
      setTimeout(() => (inThrottle = false), limit);
    }
  };
}

/**
 * Lazy load de imágenes con Intersection Observer
 */
export function lazyLoadImages(): void {
  const images = document.querySelectorAll("img[data-src]");

  if ("IntersectionObserver" in window) {
    const imageObserver = new IntersectionObserver((entries, observer) => {
      entries.forEach((entry) => {
        if (entry.isIntersecting) {
          const img = entry.target as HTMLImageElement;
          if (img.dataset.src) {
            img.src = img.dataset.src;
            img.removeAttribute("data-src");
            observer.unobserve(img);
          }
        }
      });
    });

    images.forEach((img) => imageObserver.observe(img));
  } else {
    // Fallback for older browsers
    images.forEach((img) => {
      const src = (img as HTMLImageElement).dataset.src;
      if (src) {
        (img as HTMLImageElement).src = src;
      }
    });
  }
}

/**
 * Request Idle Callback polyfill
 */
export function requestIdleCallbackPolyfill(
  callback: (deadline: {
    timeRemaining: () => number;
    didTimeout: boolean;
  }) => void,
  options?: { timeout: number },
): number {
  if ("requestIdleCallback" in window) {
    return window.requestIdleCallback(callback, options as IdleRequestOptions);
  }

  // Polyfill using globalThis to avoid type shadowing
  const start = Date.now();
  // Cast to number for browser compatibility (NodeJS.Timeout is not a number)
  return Number(
    globalThis.setTimeout(() => {
      callback({
        timeRemaining: () => Math.max(0, 50 - (Date.now() - start)),
        didTimeout: false,
      });
    }, 1),
  );
}

// Re-export with the original name for backward compatibility
export { requestIdleCallbackPolyfill as requestIdleCallback };

/**
 * Measure rendering performance
 */
export function measureRenderTime(callback: () => void): void {
  if ("PerformanceObserver" in window) {
    const observer = new PerformanceObserver((list) => {
      observer.disconnect();
    });

    try {
      observer.observe({ entryTypes: ["paint", "largest-contentful-paint"] });
    } catch (e) {
      // Performance Observer not supported for these entry types
    }
  }

  callback();
}

/**
 * Preload critical resources
 */
export function preloadResource(href: string, as: string): void {
  const link = document.createElement("link");
  link.rel = "preload";
  link.href = href;
  link.as = as;
  document.head.appendChild(link);
}

/**
 * DNS prefetch for external domains
 */
export function dnsPrefetch(domain: string): void {
  const link = document.createElement("link");
  link.rel = "dns-prefetch";
  link.href = domain;
  document.head.appendChild(link);
}

/**
 * Check if user prefers reduced motion
 */
export function prefersReducedMotion(): boolean {
  return window.matchMedia("(prefers-reduced-motion: reduce)").matches;
}

/**
 * Check if user prefers dark mode
 */
export function prefersDarkMode(): boolean {
  return window.matchMedia("(prefers-color-scheme: dark)").matches;
}

/**
 * Memory usage monitoring (Chrome only)
 */
export function getMemoryUsage(): { used: number; total: number } | null {
  if ("memory" in performance) {
    const mem = (
      performance as {
        memory: { usedJSHeapSize: number; totalJSHeapSize: number };
      }
    ).memory;
    return {
      used: mem.usedJSHeapSize,
      total: mem.totalJSHeapSize,
    };
  }
  return null;
}

/**
 * Log memory usage (for debugging)
 */
export function logMemoryUsage(): void {
  void getMemoryUsage();
}
