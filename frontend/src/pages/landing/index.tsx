import { Link } from "react-router-dom";
import { DnLogo } from "@/components/ui/DnLogo";
import { Button } from "@/components/ui/Button";

export function LandingPage() {
  return (
    <div className="min-h-screen bg-gradient-to-br from-dn-steel-lt via-white to-dn-steel-lt">
      {/* Navigation */}
      <nav className="fixed top-0 w-full bg-white/80 backdrop-blur-md border-b border-dn-steel-lt z-50">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center h-16">
            <div className="flex items-center gap-2">
              <DnLogo showText={false} width={28} />
              <span className="text-lg font-semibold text-dn-dark">Ratiba</span>
            </div>
            <div className="flex gap-3">
              <Link to="/crew/me" className="hidden sm:block">
                <Button variant="ghost" size="sm">
                  Crew access
                </Button>
              </Link>
              <Link to="/login">
                <Button variant="secondary" size="sm">
                  Sign in
                </Button>
              </Link>
              <Link to="/login">
                <Button size="sm">Get started</Button>
              </Link>
            </div>
          </div>
        </div>
      </nav>

      {/* Hero */}
      <section className="pt-32 pb-20 px-4 sm:px-6 lg:px-8 max-w-7xl mx-auto">
        <div className="grid lg:grid-cols-2 gap-12 items-center">
          <div className="space-y-8">
            <div className="space-y-4">
              <p className="inline-flex items-center gap-2 rounded-full border border-dn-steel-lt bg-white/70 px-4 py-1.5 text-xs font-medium text-dn-steel-deep">
                <span aria-hidden>✈️</span> Built for African aviation · KCAA FTL scheme
              </p>
              <h1 className="text-5xl sm:text-6xl font-bold text-dn-dark leading-tight">
                Crew rostering,
                <br />
                <span className="bg-gradient-to-r from-dn-steel to-dn-steel-lt bg-clip-text text-transparent">
                  compliance-first
                </span>
              </h1>
              <p className="text-xl text-dn-muted leading-relaxed max-w-md">
                Ratiba plans, publishes, and defends your crew roster: every duty checked against
                the full flight-time limitation scheme before it reaches a pilot&apos;s phone.
              </p>
            </div>

            <div className="flex flex-col sm:flex-row gap-4">
              <Link to="/login" className="flex-1 sm:flex-none">
                <Button size="lg" className="w-full sm:w-auto">
                  Operations sign-in
                </Button>
              </Link>
              <Link to="/crew/me" className="flex-1 sm:flex-none">
                <Button variant="secondary" size="lg" className="w-full sm:w-auto">
                  I&apos;m flight crew →
                </Button>
              </Link>
            </div>

            <div className="flex items-center gap-8 pt-8 border-t border-dn-steel-lt">
              <div>
                <div className="text-3xl font-bold text-dn-dark">15</div>
                <p className="text-sm text-dn-muted">FTL rules enforced on every publish</p>
              </div>
              <div>
                <div className="text-3xl font-bold text-dn-dark">SHA-256</div>
                <p className="text-sm text-dn-muted">Sealed, verifiable audit packs</p>
              </div>
              <div>
                <div className="text-3xl font-bold text-dn-dark">PWA</div>
                <p className="text-sm text-dn-muted">Installs on every crew phone</p>
              </div>
            </div>
          </div>

          {/* Right visual: stylised roster snapshot */}
          <div className="hidden lg:block">
            <div className="relative">
              <div className="absolute inset-0 bg-gradient-to-r from-dn-steel-lt to-transparent rounded-3xl blur-3xl opacity-20"></div>
              <div className="relative bg-white rounded-2xl shadow-2xl p-8 border border-dn-steel-lt">
                <div className="flex items-center justify-between mb-4">
                  <span className="text-sm font-semibold text-dn-dark">November roster</span>
                  <span className="rounded-full bg-emerald-50 px-3 py-1 text-xs font-medium text-emerald-700">
                    LEGAL · published
                  </span>
                </div>
                <div className="space-y-3">
                  {[
                    ["JW 512 · NBO–MGQ", "06:10Z", "Capt Achieng · FO Hassan"],
                    ["JW 513 · MGQ–NBO", "10:45Z", "Capt Achieng · FO Hassan"],
                    ["JW 630 · NBO–JUB", "13:20Z", "Capt Okello · FO Wanjiru"],
                  ].map(([flt, time, crew]) => (
                    <div
                      key={flt}
                      className="flex items-center justify-between rounded-lg border border-dn-steel-lt/70 bg-dn-fog/40 px-4 py-3"
                    >
                      <div>
                        <div className="text-sm font-mono font-medium text-dn-steel-deep">
                          {flt}
                        </div>
                        <div className="text-xs text-dn-muted">{crew}</div>
                      </div>
                      <span className="text-xs font-mono text-dn-muted">{time}</span>
                    </div>
                  ))}
                  <div className="flex items-center justify-between rounded-lg bg-dn-steel-lt/30 px-4 py-3 text-xs text-dn-steel-deep">
                    <span>FDP 11.4h of 13h · rest 14h · within limits</span>
                    <span aria-hidden>✓</span>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Role paths */}
      <section id="roles" className="py-20 px-4 sm:px-6 lg:px-8 bg-white">
        <div className="max-w-7xl mx-auto">
          <div className="text-center mb-16">
            <h2 className="text-4xl font-bold text-dn-dark mb-4">One platform, three doors</h2>
            <p className="text-xl text-dn-muted">
              Everyone gets exactly the surface they need — nothing more to learn, nothing to
              misconfigure.
            </p>
          </div>
          <div className="grid md:grid-cols-3 gap-8">
            {rolePaths.map((r) => (
              <div
                key={r.title}
                className="flex flex-col rounded-xl border border-dn-steel-lt p-8 hover:border-dn-steel hover:shadow-lg transition-all"
              >
                <div className="text-3xl mb-4" aria-hidden>
                  {r.icon}
                </div>
                <h3 className="text-lg font-semibold text-dn-dark mb-2">{r.title}</h3>
                <ul className="text-sm text-dn-muted leading-relaxed space-y-1.5 mb-6">
                  {r.points.map((p) => (
                    <li key={p} className="flex gap-2">
                      <span className="text-dn-steel-deep" aria-hidden>
                        ·
                      </span>
                      {p}
                    </li>
                  ))}
                </ul>
                <Link to={r.to} className="mt-auto">
                  <Button variant={r.primary ? "primary" : "secondary"} size="sm">
                    {r.cta}
                  </Button>
                </Link>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Features */}
      <section className="py-20 px-4 sm:px-6 lg:px-8">
        <div className="max-w-7xl mx-auto">
          <div className="text-center mb-16">
            <h2 className="text-4xl font-bold text-dn-dark mb-4">
              Everything an AOC needs to roster with confidence
            </h2>
            <p className="text-xl text-dn-muted">
              From first flight entry to the audit pack you hand the regulator.
            </p>
          </div>

          <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-8">
            {features.map((feature) => (
              <div
                key={feature.title}
                className="group p-8 rounded-xl border border-dn-steel-lt bg-white hover:border-dn-steel hover:shadow-lg transition-all"
              >
                <div className="text-3xl mb-4" aria-hidden>
                  {feature.icon}
                </div>
                <h3 className="text-lg font-semibold text-dn-dark mb-2">{feature.title}</h3>
                <p className="text-dn-muted text-sm leading-relaxed">{feature.description}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Why Ratiba */}
      <section className="py-20 px-4 sm:px-6 lg:px-8 bg-white">
        <div className="max-w-7xl mx-auto">
          <div className="grid lg:grid-cols-2 gap-12 items-center">
            <div className="space-y-8">
              <h2 className="text-4xl font-bold text-dn-dark">Why operators choose Ratiba</h2>
              {benefits.map((benefit) => (
                <div key={benefit.title} className="flex gap-4">
                  <div className="flex-shrink-0 w-8 h-8 rounded-full bg-dn-steel/10 flex items-center justify-center text-dn-steel-deep font-bold">
                    ✓
                  </div>
                  <div>
                    <h3 className="font-semibold text-dn-dark mb-1">{benefit.title}</h3>
                    <p className="text-dn-muted text-sm">{benefit.description}</p>
                  </div>
                </div>
              ))}
            </div>
            <div className="bg-gradient-to-br from-dn-steel-lt via-white to-dn-steel-lt rounded-2xl p-12 shadow-lg">
              <div className="space-y-4">
                <div className="bg-white rounded-lg p-4 border-l-4 border-dn-steel">
                  <div className="text-sm font-mono text-dn-steel-deep">Legality engine</div>
                  <div className="text-2xl font-bold text-dn-dark">KCAR-P8 FTL scheme</div>
                  <p className="text-xs text-dn-muted mt-1">
                    Daily, cumulative, and rest rules — with operator-approved variations.
                  </p>
                </div>
                <div className="bg-white rounded-lg p-4 border-l-4 border-dn-steel">
                  <div className="text-sm font-mono text-dn-steel-deep">Evidence</div>
                  <div className="text-2xl font-bold text-dn-dark">Tamper-evident PDFs</div>
                  <p className="text-xs text-dn-muted mt-1">
                    Roster cards and audit packs, hash-sealed and re-verifiable at any time.
                  </p>
                </div>
                <div className="bg-white rounded-lg p-4 border-l-4 border-dn-steel">
                  <div className="text-sm font-mono text-dn-steel-deep">Crew experience</div>
                  <div className="text-2xl font-bold text-dn-dark">Roster in the pocket</div>
                  <p className="text-xs text-dn-muted mt-1">
                    Pilots pair once with a code and always see today&apos;s duty, notices, and
                    expiries.
                  </p>
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* CTA */}
      <section className="py-20 px-4 sm:px-6 lg:px-8 bg-gradient-to-r from-dn-steel to-dn-steel-lt">
        <div className="max-w-4xl mx-auto text-center space-y-8">
          <h2 className="text-4xl font-bold text-white">See your operation in Ratiba today</h2>
          <p className="text-lg text-white/80">
            Create a private demo workspace pre-loaded with crew, aircraft, and flights — or sign in
            to your operator.
          </p>
          <div className="flex flex-col sm:flex-row justify-center gap-4">
            <Link to="/login">
              <Button size="lg" className="bg-white text-dn-steel-deep hover:bg-gray-100">
                Create a demo workspace
              </Button>
            </Link>
            <Link to="/crew/me">
              <Button
                size="lg"
                variant="ghost"
                className="border border-white/60 text-white hover:bg-white/10"
              >
                Flight crew access
              </Button>
            </Link>
          </div>
        </div>
      </section>

      {/* Footer */}
      <footer className="border-t border-dn-steel-lt bg-white/50 backdrop-blur">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
          <div className="grid md:grid-cols-3 gap-8 mb-8">
            <div>
              <h3 className="font-semibold text-dn-dark mb-4">Product</h3>
              <ul className="space-y-2 text-sm text-dn-muted">
                <li>
                  <a href="#roles" className="hover:text-dn-steel-deep">
                    Who it&apos;s for
                  </a>
                </li>
                <li>
                  <Link to="/login" className="hover:text-dn-steel-deep">
                    Operations sign-in
                  </Link>
                </li>
                <li>
                  <Link to="/crew/me" className="hover:text-dn-steel-deep">
                    Crew portal
                  </Link>
                </li>
              </ul>
            </div>
            <div>
              <h3 className="font-semibold text-dn-dark mb-4">Compliance</h3>
              <ul className="space-y-2 text-sm text-dn-muted">
                <li>KCAA Flight Duty Time Scheme</li>
                <li>ICAO Annex 6 aligned</li>
                <li>Operator FTL variations supported</li>
              </ul>
            </div>
            <div>
              <h3 className="font-semibold text-dn-dark mb-4">Legal</h3>
              <ul className="space-y-2 text-sm text-dn-muted">
                <li>
                  <Link to="/privacy" className="hover:text-dn-steel-deep">
                    Privacy Policy
                  </Link>
                </li>
                <li>
                  <Link to="/terms" className="hover:text-dn-steel-deep">
                    Terms of Use
                  </Link>
                </li>
              </ul>
            </div>
          </div>
          <div className="border-t border-dn-steel-lt pt-8 flex flex-col sm:flex-row justify-between items-center gap-2 text-sm text-dn-muted">
            <div>© 2026 Ratiba · A DN Consultancy platform</div>
            <div className="italic">Shaping Africa&apos;s Future, Together.</div>
          </div>
        </div>
      </footer>
    </div>
  );
}

const rolePaths = [
  {
    icon: "🛡️",
    title: "Administrator",
    points: [
      "Set up the operator: fleet, users, and roles",
      "Approve FTL variations against the baseline scheme",
      "Own settings, imports, and the audit trail",
    ],
    to: "/login",
    cta: "Admin sign-in",
    primary: false,
  },
  {
    icon: "🗓️",
    title: "Crewing officer",
    points: [
      "Auto-generate and publish legal rosters in minutes",
      "Handle leave, swaps, IROP recovery, and standby",
      "Issue pairing codes and monthly roster PDFs to crew",
    ],
    to: "/login",
    cta: "Operations sign-in",
    primary: true,
  },
  {
    icon: "🧑‍✈️",
    title: "Flight crew",
    points: [
      "Pair your phone once with a code — no password",
      "Today's duty, 14-day roster, and expiring currencies",
      "Acknowledge notices, request leave and swaps",
    ],
    to: "/crew/me",
    cta: "Enter pairing code",
    primary: false,
  },
];

const features = [
  {
    icon: "⚖️",
    title: "FTL legality engine",
    description:
      "Every duty is checked against the full KCAA flight-time limitation scheme — daily FDP, cumulative duty and block hours, and rest — before publishing.",
  },
  {
    icon: "⚡",
    title: "One-click roster generation",
    description:
      "Feed in your flights and Ratiba assigns qualified, current, legal crew across the horizon, flagging anything it can't cover.",
  },
  {
    icon: "📄",
    title: "Crew roster cards",
    description:
      "Calendar-style monthly PDFs per crew member, branded and ready to print or send — generated in seconds.",
  },
  {
    icon: "🔏",
    title: "Regulator-ready audit packs",
    description:
      "One click seals a period's duties, verdicts, and variations into a hash-verified PDF you can hand to an inspector.",
  },
  {
    icon: "🚨",
    title: "Compliance alerts",
    description:
      "Expiring licences, medicals, type ratings, and any non-legal duty surface on the dashboard before they become findings.",
  },
  {
    icon: "📱",
    title: "Pilot self-service",
    description:
      "Crew pair a device with a one-time code and see their roster, duty of the day, notices, and leave — on any phone.",
  },
];

const benefits = [
  {
    title: "Compliance you can prove",
    description:
      "Not just 'the roster looked legal' — every publish stores its verdicts, and audit packs make the evidence portable.",
  },
  {
    title: "Built for East African operations",
    description:
      "KCAA scheme as the baseline, ACMI postings, rotation tracking, and IROP recovery for the way the region actually flies.",
  },
  {
    title: "Hours back every week",
    description:
      "Auto-generation and instant legality re-checks replace the spreadsheet and the late-night phone calls.",
  },
  {
    title: "Crew who trust the plan",
    description:
      "Transparent rosters on every phone, acknowledged notices, and fair leave and swap handling build buy-in.",
  },
];
