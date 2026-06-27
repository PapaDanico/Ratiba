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
              <DnLogo />
              <span className="text-lg font-semibold text-dn-dark">Ratiba</span>
            </div>
            <div className="flex gap-3">
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

      {/* Hero Section */}
      <section className="pt-32 pb-20 px-4 sm:px-6 lg:px-8 max-w-7xl mx-auto">
        <div className="grid lg:grid-cols-2 gap-12 items-center">
          {/* Left Content */}
          <div className="space-y-8">
            <div className="space-y-4">
              <h1 className="text-5xl sm:text-6xl font-bold text-dn-dark leading-tight">
                Modern Crew
                <br />
                <span className="bg-gradient-to-r from-dn-steel to-dn-steel-lt bg-clip-text text-transparent">
                  Rostering
                </span>
              </h1>
              <p className="text-xl text-dn-muted leading-relaxed max-w-md">
                Intelligent flight crew scheduling that respects regulations, optimizes costs, and
                keeps your team happy.
              </p>
            </div>

            <div className="flex flex-col sm:flex-row gap-4">
              <Link to="/login" className="flex-1 sm:flex-none">
                <Button size="lg" className="w-full sm:w-auto">
                  Start for free
                </Button>
              </Link>
              <button className="px-8 py-3 rounded-lg border-2 border-dn-steel text-dn-steel font-medium hover:bg-dn-steel hover:text-white transition-colors">
                Watch demo
              </button>
            </div>

            <div className="flex items-center gap-8 pt-8 border-t border-dn-steel-lt">
              <div>
                <div className="text-3xl font-bold text-dn-dark">500K+</div>
                <p className="text-sm text-dn-muted">Crew hours scheduled</p>
              </div>
              <div>
                <div className="text-3xl font-bold text-dn-dark">98%</div>
                <p className="text-sm text-dn-muted">FTL compliance</p>
              </div>
              <div>
                <div className="text-3xl font-bold text-dn-dark">15+</div>
                <p className="text-sm text-dn-muted">Airlines using</p>
              </div>
            </div>
          </div>

          {/* Right Visual */}
          <div className="hidden lg:block">
            <div className="relative">
              <div className="absolute inset-0 bg-gradient-to-r from-dn-steel-lt to-transparent rounded-3xl blur-3xl opacity-20"></div>
              <div className="relative bg-white rounded-2xl shadow-2xl p-8 border border-dn-steel-lt">
                <div className="space-y-4">
                  {/* Mock Dashboard Card */}
                  <div className="bg-gradient-to-r from-dn-steel-lt to-dn-steel-lt/50 rounded-lg p-4">
                    <div className="h-3 bg-white/20 rounded w-24 mb-3"></div>
                    <div className="grid grid-cols-2 gap-3">
                      <div className="h-8 bg-white/10 rounded"></div>
                      <div className="h-8 bg-white/10 rounded"></div>
                      <div className="h-8 bg-white/10 rounded"></div>
                      <div className="h-8 bg-white/10 rounded"></div>
                    </div>
                  </div>
                  <div className="space-y-2">
                    <div className="h-2 bg-dn-steel-lt rounded w-full"></div>
                    <div className="h-2 bg-dn-steel-lt rounded w-5/6"></div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Features Section */}
      <section className="py-20 px-4 sm:px-6 lg:px-8 bg-white">
        <div className="max-w-7xl mx-auto">
          <div className="text-center mb-16">
            <h2 className="text-4xl font-bold text-dn-dark mb-4">
              Powerful features for modern operations
            </h2>
            <p className="text-xl text-dn-muted">
              Everything you need to manage crew, respect regulations, and optimize scheduling
            </p>
          </div>

          <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-8">
            {features.map((feature, idx) => (
              <div
                key={idx}
                className="group p-8 rounded-xl border border-dn-steel-lt hover:border-dn-steel hover:shadow-lg transition-all"
              >
                <div className="text-3xl mb-4">{feature.icon}</div>
                <h3 className="text-lg font-semibold text-dn-dark mb-2">{feature.title}</h3>
                <p className="text-dn-muted text-sm leading-relaxed">{feature.description}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Benefits Section */}
      <section className="py-20 px-4 sm:px-6 lg:px-8">
        <div className="max-w-7xl mx-auto">
          <div className="grid lg:grid-cols-2 gap-12 items-center">
            <div className="space-y-8">
              <h2 className="text-4xl font-bold text-dn-dark">Why teams choose Ratiba</h2>
              {benefits.map((benefit, idx) => (
                <div key={idx} className="flex gap-4">
                  <div className="flex-shrink-0 w-8 h-8 rounded-full bg-dn-steel/10 flex items-center justify-center text-dn-steel font-bold">
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
                  <div className="text-sm font-mono text-dn-steel">FTL Compliance Rate</div>
                  <div className="text-2xl font-bold text-dn-dark">98.7%</div>
                </div>
                <div className="bg-white rounded-lg p-4 border-l-4 border-dn-steel">
                  <div className="text-sm font-mono text-dn-steel">Avg. Scheduling Time</div>
                  <div className="text-2xl font-bold text-dn-dark">2 minutes</div>
                </div>
                <div className="bg-white rounded-lg p-4 border-l-4 border-dn-steel">
                  <div className="text-sm font-mono text-dn-steel">Crew Satisfaction</div>
                  <div className="text-2xl font-bold text-dn-dark">9.2/10</div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* CTA Section */}
      <section className="py-20 px-4 sm:px-6 lg:px-8 bg-gradient-to-r from-dn-steel to-dn-steel-lt">
        <div className="max-w-4xl mx-auto text-center space-y-8">
          <h2 className="text-4xl font-bold text-white">Ready to transform your scheduling?</h2>
          <p className="text-lg text-white/80">
            Join hundreds of operators already using Ratiba to schedule smarter
          </p>
          <Link to="/login">
            <Button size="lg" className="bg-white text-dn-steel hover:bg-gray-100">
              Get started now
            </Button>
          </Link>
        </div>
      </section>

      {/* Footer */}
      <footer className="border-t border-dn-steel-lt bg-white/50 backdrop-blur">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
          <div className="grid md:grid-cols-4 gap-8 mb-8">
            <div>
              <h3 className="font-semibold text-dn-dark mb-4">Product</h3>
              <ul className="space-y-2 text-sm text-dn-muted">
                <li>
                  <a href="#" className="hover:text-dn-steel">
                    Features
                  </a>
                </li>
                <li>
                  <a href="#" className="hover:text-dn-steel">
                    Pricing
                  </a>
                </li>
                <li>
                  <a href="#" className="hover:text-dn-steel">
                    Security
                  </a>
                </li>
              </ul>
            </div>
            <div>
              <h3 className="font-semibold text-dn-dark mb-4">Company</h3>
              <ul className="space-y-2 text-sm text-dn-muted">
                <li>
                  <a href="#" className="hover:text-dn-steel">
                    About
                  </a>
                </li>
                <li>
                  <a href="#" className="hover:text-dn-steel">
                    Blog
                  </a>
                </li>
                <li>
                  <a href="#" className="hover:text-dn-steel">
                    Careers
                  </a>
                </li>
              </ul>
            </div>
            <div>
              <h3 className="font-semibold text-dn-dark mb-4">Resources</h3>
              <ul className="space-y-2 text-sm text-dn-muted">
                <li>
                  <Link to="/privacy" className="hover:text-dn-steel">
                    Privacy
                  </Link>
                </li>
                <li>
                  <Link to="/terms" className="hover:text-dn-steel">
                    Terms
                  </Link>
                </li>
                <li>
                  <a href="#" className="hover:text-dn-steel">
                    Contact
                  </a>
                </li>
              </ul>
            </div>
            <div>
              <h3 className="font-semibold text-dn-dark mb-4">Legal</h3>
              <ul className="space-y-2 text-sm text-dn-muted">
                <li>
                  <a href="#" className="hover:text-dn-steel">
                    KCAA Compliance
                  </a>
                </li>
                <li>
                  <a href="#" className="hover:text-dn-steel">
                    FTL Rules
                  </a>
                </li>
                <li>
                  <a href="#" className="hover:text-dn-steel">
                    Support
                  </a>
                </li>
              </ul>
            </div>
          </div>
          <div className="border-t border-dn-steel-lt pt-8 flex flex-col sm:flex-row justify-between items-center text-sm text-dn-muted">
            <div>© 2026 Ratiba. All rights reserved.</div>
            <div className="flex gap-6 mt-4 sm:mt-0">
              <a href="#" className="hover:text-dn-steel">
                Twitter
              </a>
              <a href="#" className="hover:text-dn-steel">
                GitHub
              </a>
              <a href="#" className="hover:text-dn-steel">
                LinkedIn
              </a>
            </div>
          </div>
        </div>
      </footer>
    </div>
  );
}

const features = [
  {
    icon: "📅",
    title: "Smart Scheduling",
    description:
      "AI-powered roster optimization respecting all FTL regulations and crew preferences",
  },
  {
    icon: "✈️",
    title: "FTL Compliance",
    description: "Automatic validation against KCAA rules ensures 100% regulatory adherence",
  },
  {
    icon: "👥",
    title: "Crew Management",
    description: "Centralized crew database with type ratings, currencies, and certifications",
  },
  {
    icon: "📊",
    title: "Real-time Analytics",
    description: "Detailed dashboards showing utilization, costs, and compliance metrics",
  },
  {
    icon: "🔄",
    title: "Drag-and-drop Editor",
    description: "Intuitive interface to amend rosters with instant FTL re-validation",
  },
  {
    icon: "📱",
    title: "Crew App",
    description: "Mobile app for crew to view schedules, request leave, and swap duties",
  },
];

const benefits = [
  {
    title: "Save 15+ hours per week",
    description: "Automate scheduling that previously took manual effort",
  },
  {
    title: "Reduce compliance violations",
    description: "Real-time FTL checking prevents costly breaches",
  },
  {
    title: "Improve crew satisfaction",
    description: "Fair, transparent scheduling builds crew morale",
  },
  {
    title: "Cut scheduling costs",
    description: "Optimized rosters reduce overtime and positioning flights",
  },
];
