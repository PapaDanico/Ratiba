import { createContext, useCallback, useContext, useState, type ReactNode } from "react";

type Tone = "success" | "error" | "info";
type Toast = { id: number; message: string; tone: Tone };
type ToastContextValue = { show: (message: string, tone?: Tone) => void };

const ToastContext = createContext<ToastContextValue | null>(null);

const TONE_CLASS: Record<Tone, string> = {
  success: "bg-dn-green text-white",
  error: "bg-dn-red text-white",
  info: "bg-dn-steel text-white",
};

/** App-wide transient feedback. Toasts auto-dismiss after 4s and are announced
 * via an aria-live region for screen readers. */
export function ToastProvider({ children }: { children: ReactNode }) {
  const [toasts, setToasts] = useState<Toast[]>([]);

  const show = useCallback((message: string, tone: Tone = "info") => {
    const id = Date.now() + Math.random();
    setToasts((prev) => [...prev, { id, message, tone }]);
    setTimeout(() => setToasts((prev) => prev.filter((t) => t.id !== id)), 4000);
  }, []);

  return (
    <ToastContext.Provider value={{ show }}>
      {children}
      <div
        className="fixed bottom-4 right-4 z-[60] flex flex-col gap-2"
        aria-live="polite"
        role="status"
      >
        {toasts.map((t) => (
          <div
            key={t.id}
            data-testid="toast"
            className={`rounded-md px-4 py-2 text-sm shadow-lg ${TONE_CLASS[t.tone]}`}
          >
            {t.message}
          </div>
        ))}
      </div>
    </ToastContext.Provider>
  );
}

// eslint-disable-next-line react-refresh/only-export-components
export function useToast(): ToastContextValue {
  const ctx = useContext(ToastContext);
  if (!ctx) throw new Error("useToast must be used inside <ToastProvider>");
  return ctx;
}
