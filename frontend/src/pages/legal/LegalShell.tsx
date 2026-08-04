import { Link } from "react-router-dom";
import type { ReactNode } from "react";

/** Public, unauthenticated chrome for the legal notices. */
export function LegalShell({
  title,
  updated,
  children,
}: {
  title: string;
  updated: string;
  children: ReactNode;
}) {
  return (
    <main className="min-h-screen bg-dn-fog">
      <header className="bg-dn-dark">
        <div className="mx-auto max-w-3xl px-6 py-4 flex items-center justify-between">
          <span className="font-display text-2xl text-dn-amber tracking-wide">Ratiba</span>
          <Link to="/login" className="text-sm text-dn-amber/70 hover:text-dn-amber underline">
            Back to sign in
          </Link>
        </div>
        <div className="tribal-stripe" />
      </header>

      <div className="mx-auto max-w-3xl px-6 py-10">
        <div className="mb-6 rounded-md border border-dn-amber/40 bg-dn-amber/5 p-3 text-xs text-dn-muted">
          <strong className="text-dn-dark">Draft for review.</strong> These notices are templates
          aligned to the Kenya Data Protection Act, 2019 and its Regulations. Have them reviewed by
          qualified legal counsel and complete the bracketed details before relying on them in
          production.
        </div>

        <h1 className="font-display text-4xl text-dn-dark">{title}</h1>
        <p className="mt-1 text-sm text-dn-muted">Last updated: {updated}</p>

        <div className="mt-8 space-y-7 text-sm text-dn-dark leading-relaxed">{children}</div>

        <footer className="mt-12 border-t border-dn-navy-lt pt-4 text-xs text-dn-muted">
          DN Consultancy · Ratiba ·{" "}
          <Link to="/privacy" className="underline">
            Privacy Policy
          </Link>{" "}
          ·{" "}
          <Link to="/terms" className="underline">
            Terms of Use
          </Link>
        </footer>
      </div>
    </main>
  );
}

export function Section({ heading, children }: { heading: string; children: ReactNode }) {
  return (
    <section>
      <h2 className="font-display text-xl text-dn-dark mb-2">{heading}</h2>
      <div className="space-y-2">{children}</div>
    </section>
  );
}
