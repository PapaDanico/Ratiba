import { Link } from "react-router-dom";
import { Button } from "@/components/ui/Button";

export function ErrorPage() {
  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-dn-steel-lt via-white to-dn-steel-lt px-4">
      <div className="text-center space-y-8 max-w-md">
        <div className="space-y-4">
          <h1 className="text-8xl font-bold text-dn-steel-deep">404</h1>
          <h2 className="text-3xl font-bold text-dn-dark">Page Not Found</h2>
          <p className="text-lg text-dn-muted leading-relaxed">
            Sorry, the page you&apos;re looking for doesn&apos;t exist. It might have been moved or
            deleted.
          </p>
        </div>

        <div className="flex flex-col sm:flex-row gap-4 justify-center pt-4">
          <Link to="/">
            <Button size="lg">Go Home</Button>
          </Link>
          <button
            onClick={() => window.history.back()}
            className="px-8 py-3 rounded-lg border-2 border-dn-steel text-dn-steel-deep font-medium hover:bg-dn-steel-deep hover:text-white transition-colors"
          >
            Go Back
          </button>
        </div>

        <div className="pt-8 border-t border-dn-steel-lt">
          <p className="text-sm text-dn-muted mb-4">Helpful links:</p>
          <ul className="space-y-2 text-sm">
            <li>
              <Link to="/" className="text-dn-steel-deep hover:underline">
                Landing Page
              </Link>
            </li>
            <li>
              <Link to="/login" className="text-dn-steel-deep hover:underline">
                Sign In
              </Link>
            </li>
            <li>
              <Link to="/privacy" className="text-dn-steel-deep hover:underline">
                Privacy Policy
              </Link>
            </li>
          </ul>
        </div>
      </div>
    </div>
  );
}
