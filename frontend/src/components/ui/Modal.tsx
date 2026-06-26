import { useEffect, useRef, type ReactNode } from "react";
import { Card, CardBody, CardHeader, CardTitle } from "@/components/ui/Card";

const FOCUSABLE =
  "a[href],button:not([disabled]),input:not([disabled]),select:not([disabled])," +
  'textarea:not([disabled]),[tabindex]:not([tabindex="-1"])';

/**
 * Accessible modal dialog: focus is moved in on open and restored on close,
 * Tab is trapped within, Escape and backdrop-click close it. Renders inside a
 * Card so call sites only supply a title and body.
 */
export function Modal({
  title,
  onClose,
  children,
  testId,
  maxWidth = "max-w-md",
  disableEscape = false,
}: {
  title: string;
  onClose: () => void;
  children: ReactNode;
  testId?: string;
  maxWidth?: string;
  disableEscape?: boolean;
}) {
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const previouslyFocused = document.activeElement as HTMLElement | null;
    const node = ref.current;
    const focusable = () => (node ? Array.from(node.querySelectorAll<HTMLElement>(FOCUSABLE)) : []);

    (focusable()[0] ?? node)?.focus();

    function onKey(e: KeyboardEvent) {
      if (e.key === "Escape") {
        if (!disableEscape) {
          e.stopPropagation();
          onClose();
        }
        return;
      }
      if (e.key === "Tab") {
        const f = focusable();
        if (f.length === 0) {
          e.preventDefault();
          return;
        }
        const first = f[0];
        const last = f[f.length - 1];
        if (e.shiftKey && document.activeElement === first) {
          e.preventDefault();
          last?.focus();
        } else if (!e.shiftKey && document.activeElement === last) {
          e.preventDefault();
          first?.focus();
        }
      }
    }

    document.addEventListener("keydown", onKey, true);
    return () => {
      document.removeEventListener("keydown", onKey, true);
      previouslyFocused?.focus?.();
    };
  }, [onClose, disableEscape]);

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-dn-dark/40 p-4"
      onMouseDown={(e) => {
        if (e.target === e.currentTarget) onClose();
      }}
    >
      <div
        ref={ref}
        role="dialog"
        aria-modal="true"
        aria-label={title}
        tabIndex={-1}
        data-testid={testId}
        className={`w-full ${maxWidth} outline-none`}
      >
        <Card>
          <CardHeader>
            <CardTitle>{title}</CardTitle>
          </CardHeader>
          <CardBody>{children}</CardBody>
        </Card>
      </div>
    </div>
  );
}
