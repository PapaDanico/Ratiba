/**
 * localStorage that never throws. Access to Web Storage raises a SecurityError
 * when storage is partitioned/blocked — e.g. the app running in a cross-site
 * iframe with third-party storage denied (the Claude Code web preview). Reading
 * it during render would crash the page to blank, so these helpers degrade to
 * a no-op / fallback instead.
 */
export const safeStorage = {
  get(key: string): string | null {
    try {
      return localStorage.getItem(key);
    } catch {
      return null;
    }
  },
  set(key: string, value: string): void {
    try {
      localStorage.setItem(key, value);
    } catch {
      /* storage blocked — ignore */
    }
  },
  remove(key: string): void {
    try {
      localStorage.removeItem(key);
    } catch {
      /* storage blocked — ignore */
    }
  },
};
