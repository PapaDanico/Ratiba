import { Link } from "react-router-dom";
import { LegalShell, Section } from "./LegalShell";

export function TermsPage() {
  return (
    <LegalShell title="Terms of Use" updated="28 May 2026">
      <Section heading="1. Acceptance of these terms">
        <p>
          These Terms of Use (“Terms”) govern your access to and use of Ratiba, a crew-rostering
          platform operated by DN Consultancy (“we”, “us”, “our”). By creating an account, creating
          a demo workspace, or otherwise using Ratiba, you agree to these Terms and to our{" "}
          <Link to="/privacy" className="underline">
            Privacy Policy
          </Link>
          . If you are using Ratiba on behalf of an organisation, you confirm you are authorised to
          bind that organisation.
        </p>
      </Section>

      <Section heading="2. The service">
        <p>
          Ratiba provides tools for building flight routings, generating and publishing crew
          rosters, tracking training and currencies, managing crew documents, and producing
          compliance and payroll exports aligned to the KCAA Flight Duty Time Scheme (CAA-AC-OPS033)
          and ICAO Annex 6. Features may change, and some environments are provided for{" "}
          <strong>demonstration and evaluation</strong> only.
        </p>
      </Section>

      <Section heading="3. Accounts and demo workspaces">
        <p>
          You are responsible for the accuracy of registration details, for keeping your credentials
          confidential, and for all activity under your account. Demo and evaluation workspaces are
          provided “as is”; their data may be reset, suspended, or deleted at any time without
          notice, and should not be relied upon for live operations.
        </p>
      </Section>

      <Section heading="4. Acceptable use">
        <p>You agree not to:</p>
        <ul className="list-disc list-inside space-y-1">
          <li>upload personal data without a lawful basis or required consents;</li>
          <li>attempt to access data belonging to other Operators or users;</li>
          <li>probe, scan, or disrupt the security or integrity of the service;</li>
          <li>use the service unlawfully or in breach of aviation or data-protection law; or</li>
          <li>reverse engineer or resell the service without our written permission.</li>
        </ul>
      </Section>

      <Section heading="5. Your data and your responsibilities">
        <p>
          Where you (or your Operator) upload crew or other personal data, you act as the data
          controller for that data. You are responsible for ensuring you have a lawful basis and any
          necessary consents to provide that data to Ratiba and to have it processed as described in
          the Privacy Policy, including for sensitive personal data such as medical and immigration
          documents. We process such data as your processor on your instructions.
        </p>
      </Section>

      <Section heading="6. Compliance disclaimer">
        <p>
          Ratiba is a decision-support tool that assists with Flight Time Limitation (FTL) checks
          under the KCAA Flight Duty Time Scheme (CAA-AC-OPS033), record-keeping, and audit
          preparation. It does <strong>not</strong> replace the AOC holder’s legal responsibilities.
          The Operator and its accountable managers remain solely responsible for regulatory
          compliance, the legality of published rosters, and operational safety decisions. Always
          verify outputs against your approved Operations Manual and applicable regulations.
        </p>
      </Section>

      <Section heading="7. Intellectual property">
        <p>
          Ratiba, including its software, design, and branding, is owned by DN Consultancy and its
          licensors. These Terms grant you a limited, non-exclusive, non-transferable right to use
          the service; no other rights are granted. Data you upload remains yours.
        </p>
      </Section>

      <Section heading="8. Availability and warranties">
        <p>
          We aim to keep Ratiba available and reliable but do not guarantee uninterrupted or
          error-free operation. To the maximum extent permitted by law, the service is provided “as
          is” and “as available”, without warranties of any kind, express or implied. Evaluation
          environments carry no service-level commitment.
        </p>
      </Section>

      <Section heading="9. Limitation of liability">
        <p>
          To the maximum extent permitted by applicable law, DN Consultancy shall not be liable for
          indirect, incidental, special, or consequential losses, or for loss of profits, data, or
          goodwill, arising from use of the service. Nothing in these Terms excludes liability that
          cannot lawfully be excluded.
        </p>
      </Section>

      <Section heading="10. Indemnity">
        <p>
          You agree to indemnify DN Consultancy against claims arising from your unlawful use of the
          service or from your provision of personal data without a lawful basis or required
          consents.
        </p>
      </Section>

      <Section heading="11. Suspension and termination">
        <p>
          We may suspend or terminate access for breach of these Terms, for security or legal
          reasons, or for non-payment under any separate commercial agreement. You may stop using
          the service at any time. On termination, we handle residual data in line with the Privacy
          Policy.
        </p>
      </Section>

      <Section heading="12. Governing law and jurisdiction">
        <p>
          These Terms are governed by the laws of the Republic of Kenya, and the courts of Kenya
          shall have jurisdiction, without prejudice to any mandatory rights you have under
          applicable law.
        </p>
      </Section>

      <Section heading="13. Changes to these terms">
        <p>
          We may update these Terms from time to time. Continued use after changes take effect
          constitutes acceptance. The “Last updated” date above reflects the current version.
        </p>
      </Section>

      <Section heading="14. Contact">
        <p>
          DN Consultancy — Ratiba. Email: <strong>[legal@dnconsultancy.co.ke]</strong>. Postal
          address: <strong>[address to be inserted]</strong>.
        </p>
      </Section>
    </LegalShell>
  );
}
