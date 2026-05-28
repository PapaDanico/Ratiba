import { LegalShell, Section } from "./LegalShell";

export function PrivacyPage() {
  return (
    <LegalShell title="Privacy Policy" updated="28 May 2026">
      <Section heading="1. Introduction">
        <p>
          This Privacy Policy explains how Ratiba, a crew-rostering platform operated by DN
          Consultancy (“we”, “us”, “our”), collects, uses, discloses, and safeguards personal data.
          It is written to align with the Kenya <strong>Data Protection Act, No. 24 of 2019</strong>{" "}
          (the “Act”), the Data Protection (General) Regulations, 2021, and guidance issued by the
          Office of the Data Protection Commissioner (“ODPC”).
        </p>
        <p>
          By using Ratiba you acknowledge the practices described here. If you do not agree, please
          do not use the service.
        </p>
      </Section>

      <Section heading="2. Who is responsible for your data (controller and processor)">
        <p>
          Ratiba is provided to licensed Air Operator Certificate (AOC) holders (“Operators”). Where
          an Operator uploads or manages its crew members’ data, the{" "}
          <strong>Operator is the data controller</strong> and{" "}
          <strong>Ratiba (DN Consultancy) acts as a data processor</strong> processing that data on
          the Operator’s documented instructions.
        </p>
        <p>
          For account-holder and service-usage data (for example, a Crewing Officer’s login and
          activity logs), Ratiba acts as the data controller.
        </p>
        <p>
          Contact for data-protection matters: <strong>[privacy@dnconsultancy.co.ke]</strong>. Data
          Protection Officer / contact person: <strong>[name and contact to be inserted]</strong>.
          ODPC registration number: <strong>[registration number to be inserted]</strong>.
        </p>
      </Section>

      <Section heading="3. Personal data we collect">
        <p>Depending on how the service is used, we may process:</p>
        <ul className="list-disc list-inside space-y-1">
          <li>
            <strong>Account data:</strong> name, email address, role, and a securely hashed
            password.
          </li>
          <li>
            <strong>Crew data (provided by the Operator):</strong> names, employee number, date of
            birth, base station, contact details (email, phone), languages, and employment/contract
            type.
          </li>
          <li>
            <strong>Operational data:</strong> rosters, flight-duty periods, sectors, leave, swaps,
            type ratings, recurrent currencies, and flight/duty-hour records used for Flight Time
            Limitation (FTL) compliance.
          </li>
          <li>
            <strong>Sensitive personal data (Section 2 &amp; 44 of the Act):</strong> health-related
            information such as aviation medical certificate validity; religious-observance
            indicators used for fair rostering; and immigration documents (passport, visa, work
            permit). We process these only where necessary for aviation safety and regulatory
            compliance, and with appropriate safeguards.
          </li>
          <li>
            <strong>Technical data:</strong> log records, IP address, and usage events needed to
            operate, secure, and audit the service.
          </li>
        </ul>
      </Section>

      <Section heading="4. Why we process your data and our lawful basis (Section 30)">
        <ul className="list-disc list-inside space-y-1">
          <li>
            <strong>Performance of a contract</strong> — to provide rostering, scheduling, and
            related functionality to Operators and their authorised users.
          </li>
          <li>
            <strong>Compliance with a legal obligation</strong> — to maintain crew FTL, currency,
            and duty records required under the Kenya Civil Aviation Regulations (KCARs) 2025 Part 8
            and to support audit by the Kenya Civil Aviation Authority (KCAA).
          </li>
          <li>
            <strong>Consent</strong> — where required, in particular for certain sensitive personal
            data; consent may be withdrawn at any time without affecting prior lawful processing.
          </li>
          <li>
            <strong>Legitimate interests</strong> — to secure, maintain, and improve the service,
            provided these interests are not overridden by your rights and freedoms.
          </li>
        </ul>
      </Section>

      <Section heading="5. Data protection principles we apply (Section 25)">
        <p>
          We process personal data lawfully, fairly, and transparently; collect it for specified,
          explicit purposes; limit it to what is necessary (data minimisation); keep it accurate and
          up to date; retain it no longer than necessary; and protect it with appropriate technical
          and organisational measures. We remain accountable for these obligations.
        </p>
      </Section>

      <Section heading="6. Who we share data with">
        <p>We do not sell personal data. We may disclose it to:</p>
        <ul className="list-disc list-inside space-y-1">
          <li>the Operator that controls the relevant crew records;</li>
          <li>
            regulators such as the KCAA, and the ODPC, where required by law or for lawful
            compliance and audit;
          </li>
          <li>
            vetted service providers (for example, cloud hosting and infrastructure) acting as our
            sub-processors under written terms; and
          </li>
          <li>
            third parties where required by law, court order, or to protect rights, safety, and
            security.
          </li>
        </ul>
      </Section>

      <Section heading="7. Cross-border transfer of personal data (Sections 48–49)">
        <p>
          Ratiba is hosted on cloud infrastructure that may store or process data on servers located
          outside Kenya. Where personal data is transferred outside Kenya, we rely on appropriate
          safeguards — including contractual protections with our hosting provider and encryption in
          transit — and, where required, on your consent or another lawful transfer basis under the
          Act. <strong>[Confirm hosting region and transfer safeguards with counsel.]</strong>
        </p>
      </Section>

      <Section heading="8. How we protect your data">
        <ul className="list-disc list-inside space-y-1">
          <li>encryption of traffic in transit using TLS/HTTPS;</li>
          <li>passwords stored only as salted, hashed values — never in plain text;</li>
          <li>role-based access scoped so each Operator sees only its own data (multi-tenancy);</li>
          <li>
            an append-only, tamper-evident audit trail of changes to roster-relevant records; and
          </li>
          <li>regular review of access and security practices.</li>
        </ul>
        <p>
          No system is perfectly secure, but we take reasonable steps to protect personal data
          against unauthorised access, loss, or misuse.
        </p>
      </Section>

      <Section heading="9. How long we keep your data">
        <p>
          We retain personal data for as long as an account or Operator relationship is active, and
          thereafter only as needed to meet legal, regulatory, and aviation record-keeping
          obligations (for example, retention of crew duty and FTL records for the period required
          by applicable aviation rules). When data is no longer required it is deleted or
          anonymised. Demo/evaluation workspaces may be reset or removed without notice.
        </p>
      </Section>

      <Section heading="10. Your rights as a data subject (Section 26)">
        <p>Subject to the Act, you have the right to:</p>
        <ul className="list-disc list-inside space-y-1">
          <li>be informed of the use of your personal data;</li>
          <li>access the personal data we hold about you;</li>
          <li>request correction of inaccurate or incomplete data;</li>
          <li>request deletion or erasure where permitted;</li>
          <li>object to or request restriction of certain processing;</li>
          <li>data portability where applicable;</li>
          <li>withdraw consent where processing is based on consent; and</li>
          <li>lodge a complaint with the ODPC.</li>
        </ul>
        <p>
          Because Operators control their crew data, requests relating to crew records may be
          forwarded to, or are best directed at, the relevant Operator.
        </p>
      </Section>

      <Section heading="11. How to exercise your rights">
        <p>
          Contact us at <strong>[privacy@dnconsultancy.co.ke]</strong>. We will respond within the
          timeframes set by the Act. We may need to verify your identity before acting on a request.
        </p>
      </Section>

      <Section heading="12. Personal data breaches (Section 43)">
        <p>
          Where a personal data breach is likely to result in a risk to your rights and freedoms, we
          will notify the ODPC without undue delay and, where feasible, within 72 hours of becoming
          aware of it, and will inform affected data subjects where required.
        </p>
      </Section>

      <Section heading="13. Cookies and local storage">
        <p>
          Ratiba uses your browser’s local storage to hold authentication tokens that keep you
          signed in. We do not use third-party advertising or tracking cookies.
        </p>
      </Section>

      <Section heading="14. Children’s data">
        <p>
          Ratiba is a professional aviation tool intended for use by adults. It is not directed at
          children, and we do not knowingly collect children’s personal data.
        </p>
      </Section>

      <Section heading="15. Changes to this policy">
        <p>
          We may update this Privacy Policy from time to time. Material changes will be reflected by
          updating the “Last updated” date above and, where appropriate, by additional notice.
        </p>
      </Section>

      <Section heading="16. Complaints">
        <p>
          If you believe your data-protection rights have been infringed, you may lodge a complaint
          with the Office of the Data Protection Commissioner (ODPC), Kenya —{" "}
          <span className="font-mono">www.odpc.go.ke</span>.
        </p>
      </Section>

      <Section heading="17. Contact us">
        <p>
          DN Consultancy — Ratiba. Email: <strong>[privacy@dnconsultancy.co.ke]</strong>. Postal
          address: <strong>[address to be inserted]</strong>.
        </p>
      </Section>
    </LegalShell>
  );
}
