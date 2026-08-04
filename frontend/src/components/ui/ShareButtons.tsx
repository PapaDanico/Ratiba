/**
 * WhatsApp / SMS / Email share row. Deep links (wa.me / sms: / mailto:) that
 * open the user's own messaging app with `message` pre-filled — no server-side
 * channel or credentials needed. `phone`/`email` pre-address the recipient when
 * known; omit them to let the user pick (e.g. a pilot sharing their own roster).
 */

type ShareButtonsProps = {
  message: string;
  phone?: string | null;
  email?: string | null;
  subject?: string;
  testidPrefix: string;
};

export function ShareButtons({
  message,
  phone,
  email,
  subject = "Ratiba",
  testidPrefix,
}: ShareButtonsProps) {
  const waDigits = (phone ?? "").replace(/\D/g, ""); // wa.me wants digits only
  const smsPhone = (phone ?? "").replace(/\s/g, ""); // keep a leading +, drop spaces
  const body = encodeURIComponent(message);
  const whatsappHref = `https://wa.me/${waDigits}?text=${body}`;
  const smsHref = `sms:${smsPhone}?&body=${body}`;
  const emailHref = `mailto:${email ?? ""}?subject=${encodeURIComponent(subject)}&body=${body}`;
  const cls =
    "rounded border border-dn-navy-lt px-1 py-1 text-center text-[11px] text-dn-navy-deep " +
    "hover:border-dn-amber hover:text-dn-dark";

  return (
    <div className="grid grid-cols-3 gap-1">
      <a
        href={whatsappHref}
        target="_blank"
        rel="noopener noreferrer"
        className={cls}
        data-testid={`${testidPrefix}-whatsapp`}
      >
        WhatsApp
      </a>
      <a href={smsHref} className={cls} data-testid={`${testidPrefix}-sms`}>
        SMS
      </a>
      <a href={emailHref} className={cls} data-testid={`${testidPrefix}-email`}>
        Email
      </a>
    </div>
  );
}
