import { createContext, useCallback, useContext, useState, type ReactNode } from "react";

type Tone = "success" | "error" | "info";
type ToastAction = { label: string; onClick: () => void };
type Toast = { id: number; message: string; tone: Tone; action?: ToastAction };
type ToastContextValue = { show: (message: string, tone?: Tone, action?: ToastAction) => void };

const ToastContext = createContext<ToastContextValue | null>(null);

const TONE_CLASS: Record<Tone, string> = {
  success: "bg-dn-green text-white",
  error: "bg-dn-red text-white",
  info: "bg-dn-navy-deep text-white",
};

const TONE_ICON: Record<Tone, string> = {
  success: "✓",
  error: "✕",
  info: "ℹ",
};

/** App-wide transient feedback. Toasts auto-dismiss after 4s and are announced
 * via an aria-live region for screen readers. */
export function ToastProvider({ children }: { children: ReactNode }) {
  const [toasts, setToasts] = useState<Toast[]>([]);

  const dismiss = useCallback((id: number) => {
    setToasts((prev) => prev.filter((t) => t.id !== id));
  }, []);

  const show = useCallback(
    (message: string, tone: Tone = "info", action?: ToastAction) => {
      const id = Date.now() + Math.random();
      setToasts((prev) => [...prev, { id, message, tone, ...(action ? { action } : {}) }]);
      // Action toasts linger longer — the user needs time to change their mind.
      setTimeout(() => dismiss(id), action ? 7000 : 4000);
    },
    [dismiss],
  );

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
            className={`motion-toast-in flex items-center gap-2.5 rounded-dn-sm py-2.5 pl-3 pr-2 text-sm shadow-dn-lg ${TONE_CLASS[t.tone]}`}
          >
            <span aria-hidden className="grid h-5 w-5 place-items-center text-xs font-bold">
              {TONE_ICON[t.tone]}
            </span>
            <span className="pr-1">{t.message}</span>
            {t.action && (
              <button
                type="button"
                onClick={() => {
                  dismiss(t.id);
                  t.action?.onClick();
                }}
                className="rounded-sm border border-white/40 px-2 py-0.5 text-xs font-semibold uppercase tracking-wide transition-colors hover:bg-white/15"
                data-testid="toast-action"
              >
                {t.action.label}
              </button>
            )}
            <button
              type="button"
              onClick={() => dismiss(t.id)}
              aria-label="Dismiss notification"
              className="ml-auto grid h-6 w-6 place-items-center rounded-sm text-base leading-none text-white/70 transition-colors hover:bg-white/15 hover:text-white"
            >
              ✕
            </button>
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
