import Link from "next/link";

type PolicySection = {
  heading: string;
  paragraphs?: string[];
  bullets?: string[];
};

type PolicyDocument = {
  eyebrow: string;
  title: string;
  intro: string;
  sections: PolicySection[];
};

const documents: Record<string, PolicyDocument> = {
  terms: {
    eyebrow: "WORKBIT POLICIES",
    title: "Terms of Service",
    intro:
      "These Terms explain the rules for using WorkBit, buying an earning package, completing offers, and using your wallet. Please read them before creating an account or using the service.",
    sections: [
      {
        heading: "1. Who operates WorkBit",
        paragraphs: [
          "WorkBit is operated under the name WorkBit Ltd, USA (\"WorkBit\", \"we\", \"us\", or \"our\"). These Terms apply to the WorkBit website, account features, wallet, and offer catalog.",
        ],
      },
      {
        heading: "2. Your account",
        paragraphs: [
          "Provide accurate registration information, keep your sign-in details secure, and use only an account that belongs to you. Email verification and an active account are required for earning and withdrawal features. You are responsible for activity carried out through your account.",
          "You must be at least 18 years old, or the age of majority where you live if it is higher, to use WorkBit. Do not create an account if you are not legally eligible to participate.",
        ],
      },
      {
        heading: "3. Packages and access",
        paragraphs: [
          "WorkBit's package catalog displays each package's current price and access duration. Choose a package, pay its displayed BDT amount through the listed bKash or Nagad account, and submit the transaction reference. Package access starts after administrator approval. A renewal made before the current package expires extends from its existing expiry date; otherwise, the new term starts when the purchase is approved.",
          "Buying a package gives access to eligible earning features during its term; it does not guarantee that offers will be available, completed, approved, or produce a particular amount of earnings. Package catalog and prices may change. Review the purchase screen before paying.",
        ],
      },
      {
        heading: "4. Wallet, deposits, and payments",
        paragraphs: [
          "Package payments are made only for a selected package; standalone wallet deposits and wallet-funded package purchases are not available. The BDT amount and USD/BDT exchange rate are fixed on your payment request so the administrator can verify the amount you were asked to send. Keep your transaction reference until the request is reviewed.",
        ],
      },
      {
        heading: "5. Offers and rewards",
        paragraphs: [
          "Offer availability, eligibility, instructions, and rewards are determined by each offer provider and may vary by country, device, and time. Read the full provider requirements before starting. A displayed amount is not a promise of payment: a provider must report a valid completion and WorkBit must validate it before a reward is recorded.",
          "The default reward policy allocates 80% of eligible provider payout to the user and 20% to WorkBit. WorkBit may configure different percentages or other policy limits; the applicable reward details are shown where available. Development/demo offers are identified as such and do not create real rewards.",
        ],
      },
      {
        heading: "6. Fair use and prohibited activity",
        bullets: [
          "Complete offers honestly and follow the provider's terms, eligibility rules, and instructions.",
          "Do not use bots, fabricated completion evidence, multiple accounts, identity or location spoofing, or other methods to manipulate offers or rewards.",
          "Do not interfere with WorkBit, another user's account, a provider's systems, or payment and verification processes.",
        ],
        paragraphs: [
          "We may investigate suspicious activity, pause a reward or transaction while reviewing it, and restrict or close accounts when we reasonably identify fraud, abuse, or a material breach of these Terms. Where a provider reverses or rejects a conversion, the related reward may be denied or reversed.",
        ],
      },
      {
        heading: "7. Withdrawals",
        paragraphs: [
          "Withdrawals are available only from withdrawable earning balance, not deposit balance. Requests are subject to account verification, the minimum and methods shown in the app, administrator review, and the Withdrawal Policy. Current manual payout methods and exchange rates may change.",
        ],
      },
      {
        heading: "8. Third-party services",
        paragraphs: [
          "Offers and payment services may be provided by third parties and are subject to their own terms and privacy notices. WorkBit cannot guarantee a third party's availability, decision, or processing time. Your use of a third-party service is also governed by its terms.",
        ],
      },
      {
        heading: "9. Service availability and changes",
        paragraphs: [
          "We may update, suspend, or discontinue parts of the service, package catalog, or offer catalog. We will make reasonable efforts to communicate material changes when appropriate. Changes do not alter transaction snapshots already recorded in your account.",
        ],
      },
      {
        heading: "10. Disclaimers and liability",
        paragraphs: [
          "WorkBit is provided subject to applicable law and may be unavailable or interrupted. Nothing in these Terms excludes rights or remedies that cannot lawfully be excluded. To the extent permitted by applicable law, WorkBit is not liable for indirect or consequential loss arising from use of the service or a third-party provider.",
        ],
      },
      {
        heading: "11. Applicable law and contact",
        paragraphs: [
          "These Terms are intended to operate consistently with applicable United States law and any mandatory consumer protections that apply where you live. WorkBit Ltd, USA is the named operator. For account or policy questions, use the support contact provided by WorkBit in your account communications.",
        ],
      },
      {
        heading: "12. Updates to these Terms",
        paragraphs: [
          "We may revise these Terms as the service changes. The updated version and its effective date will be published on this page. Continued use after an update takes effect means you accept the revised Terms, to the extent permitted by law.",
        ],
      },
    ],
  },
  privacy: {
    eyebrow: "WORKBIT POLICIES",
    title: "Privacy Policy",
    intro:
      "This Privacy Policy describes how WorkBit Ltd, USA handles information when you create an account, use the wallet, or interact with offer features.",
    sections: [
      {
        heading: "1. Information we collect",
        bullets: [
          "Account details: your name, email address, country, mobile number, referral details, and account status.",
          "Profile details you choose to provide, such as an avatar or time zone.",
          "Wallet and transaction records: balances, deposits, package purchases, rewards, withdrawals, payment methods, references, statuses, and review notes.",
          "Offer activity and security records: offer identifiers, click and conversion references, timestamps, IP address, browser or device information, and relevant request logs.",
          "Messages or information you send to WorkBit support.",
        ],
      },
      {
        heading: "2. How we use information",
        bullets: [
          "Create and secure accounts, verify email addresses, and provide the service.",
          "Record package, deposit, wallet, reward, and withdrawal activity and support administrator review.",
          "Validate offer activity, apply reward rules, investigate suspected abuse, and maintain accurate transaction records.",
          "Communicate account, security, transaction, and policy updates.",
          "Meet applicable legal obligations and protect WorkBit, users, and service providers.",
        ],
      },
      {
        heading: "3. Offers and third-party sharing",
        paragraphs: [
          "When third-party offer providers are enabled, information needed to identify and validate an offer interaction may be sent to the relevant provider, and we may receive conversion or reversal information from that provider. Providers handle information under their own privacy notices. WorkBit's current offer catalog is development-only; demo activity does not create real rewards, and production provider availability depends on integrations being configured and approved.",
          "We may also share limited information with service providers that help operate WorkBit, when needed to process a transaction, or when disclosure is required by law. We do not sell personal information.",
        ],
      },
      {
        heading: "4. Payments and sensitive details",
        paragraphs: [
          "Payment references and transaction details are used to match and review deposits and package payments. Mobile-banking payout destinations are encrypted for storage and shown in masked form in user-facing records. Authorized administrators may access a destination when needed to review or process a withdrawal.",
        ],
      },
      {
        heading: "5. Cookies and technical data",
        paragraphs: [
          "WorkBit uses an essential session cookie to keep you signed in and may process technical request data, such as IP address and browser information, to operate the service and protect accounts. Your browser can provide controls for cookies, but disabling essential cookies may prevent sign-in features from working.",
        ],
      },
      {
        heading: "6. Retention and security",
        paragraphs: [
          "We keep account, security, and transaction records for as long as reasonably needed to provide the service, resolve disputes, prevent abuse, and meet applicable legal or accounting obligations. Retention periods can differ by record type.",
          "We use safeguards intended to protect information. No online service or storage method can be guaranteed completely secure.",
        ],
      },
      {
        heading: "7. Your choices and privacy rights",
        paragraphs: [
          "Depending on where you live, you may have rights to request access to, correction of, deletion of, or a copy of certain personal information, or to object to or limit certain processing. We may need to verify your identity and retain some records where law or legitimate transaction needs require it. Use the support contact provided in your account communications to submit a privacy request.",
        ],
      },
      {
        heading: "8. Children",
        paragraphs: [
          "WorkBit is not intended for anyone under 18 or below the applicable age of majority. We do not knowingly invite children to use earning features. If you believe a child has created an account, contact WorkBit using the support contact provided in account communications.",
        ],
      },
      {
        heading: "9. International processing",
        paragraphs: [
          "WorkBit is operated under the name WorkBit Ltd, USA. Depending on the services in use, information may be processed in the United States or other countries where WorkBit or its service providers operate. Privacy protections can differ by location; applicable legal safeguards will apply where required.",
        ],
      },
      {
        heading: "10. Changes and contact",
        paragraphs: [
          "We may update this Policy and publish the new version and effective date on this page. WorkBit Ltd, USA is the named operator. For privacy questions or requests, use the support contact provided by WorkBit in your account communications.",
        ],
      },
    ],
  },
  "reward-policy": {
    eyebrow: "HOW REWARDS WORK",
    title: "Reward Policy",
    intro:
      "This policy explains when offer activity can become a WorkBit reward, how the user share is calculated, and why a displayed offer amount is not guaranteed income.",
    sections: [
      {
        heading: "1. Who can earn",
        paragraphs: [
          "You need a verified email, an active account, and an approved earning package that has not expired to use earning features. Package access lasts for the duration displayed for the package when you purchase it.",
        ],
      },
      {
        heading: "2. Before you start an offer",
        bullets: [
          "Check the offer's country, device, eligibility, instructions, and any provider-specific restrictions.",
          "Complete the stated requirements honestly and only once, unless the provider explicitly says otherwise.",
          "Do not use VPNs, bots, fabricated information, multiple accounts, or other methods to disguise identity or activity.",
          "Keep any confirmation the provider supplies until your activity has been resolved.",
        ],
      },
      {
        heading: "3. Provider verification comes first",
        paragraphs: [
          "A click or task submission is not itself a reward. The provider must report a valid conversion, and WorkBit must validate it and apply the active reward policy. A provider may take time to report activity, reject an ineligible conversion, or later reverse a conversion. WorkBit cannot guarantee that a particular task will be approved or when a provider will respond.",
          "Only reward decisions recorded as approved and credited in your account ledger count as available earnings. Pending, rejected, reversed, or demo activity is not withdrawable.",
        ],
      },
      {
        heading: "4. Reward share",
        paragraphs: [
          "The current default policy allocates 80% of eligible provider payout to the user and 20% to WorkBit. The policy applied to a conversion may be configured by WorkBit and can include limits, rounding, or other eligibility rules. Where provided, the offer's displayed user reward is an estimate or catalog value; the validated ledger decision is the record of the amount actually credited.",
        ],
      },
      {
        heading: "5. Development/demo offers",
        paragraphs: [
          "The current offer catalog is development-only. Offers labelled as demo or development samples are for testing and do not create real rewards. Live provider offers and reward posting depend on WorkBit completing provider integration, approval, and configuration; a provider's name or credentials listed in a configuration example do not mean that provider is live.",
        ],
      },
      {
        heading: "6. Reversals, disputes, and abuse",
        paragraphs: [
          "If a provider rejects or reverses a conversion, or WorkBit identifies a validation, duplicate, or fraud issue, the reward may be denied, held for review, or reversed. WorkBit may request relevant information to review a dispute. Submitting false evidence or attempting to manipulate a provider's tracking may lead to account restrictions under the Terms of Service.",
          "For a reward question, provide the offer name and any available activity or conversion reference using the support contact in your account communications.",
        ],
      },
      {
        heading: "7. No earnings promise",
        paragraphs: [
          "Offer availability and results vary. WorkBit does not promise a minimum number of offers, reward amount, hourly rate, or income. A package purchase provides time-limited access to eligible features; it is not an investment and does not guarantee a return.",
        ],
      },
      {
        heading: "8. Policy changes",
        paragraphs: [
          "Reward rules may change as provider requirements or WorkBit features change. The policy in effect for a reward decision is applied to that decision; approved transactions remain recorded in your wallet ledger.",
        ],
      },
    ],
  },
  "withdrawal-policy": {
    eyebrow: "GETTING PAID",
    title: "Withdrawal Policy",
    intro:
      "This policy describes how WorkBit withdrawal requests are submitted and reviewed. Withdrawal availability depends on verified account status, withdrawable earnings, configured payout settings, and administrator review.",
    sections: [
      {
        heading: "1. Eligible balance",
        paragraphs: [
          "Only available earning balance can be withdrawn. Deposit balance is reserved for package purchases and renewals and is not withdrawable. Pending, rejected, reversed, or otherwise unapproved rewards are not part of withdrawable earnings.",
        ],
      },
      {
        heading: "2. Minimum and currency",
        paragraphs: [
          "Wallets and withdrawal requests are denominated in USD. The current minimum is configured by WorkBit and defaults to $5 USD; check the withdrawal screen for the amount currently in force. You cannot request more than your available withdrawable balance.",
        ],
      },
      {
        heading: "3. Available payout methods and conversion",
        paragraphs: [
          "The current manual payout flow supports bKash or Nagad mobile-banking details for a BDT payout. WorkBit must configure the USD/BDT exchange rate before requests can be submitted. The rate and estimated BDT payout are recorded when you submit the request; later rate changes do not change that request's snapshot.",
        ],
      },
      {
        heading: "4. Account and request requirements",
        bullets: [
          "Your account must be active and your email verified.",
          "Enter a payout destination that belongs to you and is accurate.",
          "Only one withdrawal can be pending or processing for your account at a time.",
          "Requests are unavailable if secure payout storage or the administrator-managed exchange rate is not configured.",
        ],
      },
      {
        heading: "5. Review and processing",
        paragraphs: [
          "Withdrawal requests are manually reviewed. When you submit a request, the requested amount is reserved from your available wallet balance. An administrator may approve it for processing, reject it and release the reserved amount back to your wallet, or mark it completed after payout. Processing times can vary; WorkBit does not promise a fixed payout timeline.",
          "WorkBit may ask for information needed to verify a request or investigate suspected errors or abuse. Keep your account and payout details secure.",
        ],
      },
      {
        heading: "6. Fees, taxes, and errors",
        paragraphs: [
          "Any applicable payout-provider charges will be shown where WorkBit can determine them before processing; third-party charges may also apply. You are responsible for determining whether rewards or payouts are taxable where you live. Contact support promptly if you think a request or payout record is incorrect.",
        ],
      },
      {
        heading: "7. Contact and updates",
        paragraphs: [
          "For a withdrawal question, include the request reference and contact WorkBit using the support contact provided in your account communications. WorkBit Ltd, USA may update this policy as payout methods and legal requirements change; the current version is published on this page.",
        ],
      },
    ],
  },
};

export function PolicyPage({ policy }: { policy: keyof typeof documents }) {
  const document = documents[policy];

  return (
    <main className="landing policy-page">
      <header className="landing-nav">
        <Link className="brand landing-brand" href="/">
          <i>W</i> WorkBit
        </Link>
        <nav aria-label="Policy navigation">
          <Link href="/terms">Terms</Link>
          <Link href="/privacy">Privacy</Link>
          <Link href="/reward-policy">Reward policy</Link>
          <Link href="/withdrawal-policy">Withdrawal policy</Link>
        </nav>
        <div className="nav-actions">
          <Link className="text-link" href="/">
            Back to home
          </Link>
        </div>
      </header>

      <section className="policy-hero">
        <span className="eyebrow">{document.eyebrow}</span>
        <h1>{document.title}</h1>
        <p>{document.intro}</p>
        <small>WorkBit Ltd, USA · Last updated October 11, 2026</small>
      </section>

      <article className="policy-content">
        {document.sections.map((section) => (
          <section key={section.heading}>
            <h2>{section.heading}</h2>
            {section.paragraphs?.map((paragraph) => (
              <p key={paragraph}>{paragraph}</p>
            ))}
            {section.bullets && (
              <ul>
                {section.bullets.map((bullet) => (
                  <li key={bullet}>{bullet}</li>
                ))}
              </ul>
            )}
          </section>
        ))}
        <nav className="policy-related" aria-label="Related WorkBit policies">
          <span>Related policies</span>
          <Link href="/terms">Terms of Service</Link>
          <Link href="/privacy">Privacy Policy</Link>
          <Link href="/reward-policy">Reward Policy</Link>
          <Link href="/withdrawal-policy">Withdrawal Policy</Link>
        </nav>
      </article>

      <footer className="landing-footer">
        <Link className="brand landing-brand" href="/">
          <i>W</i> WorkBit
        </Link>
        <span>Work. Complete. Earn.</span>
        <nav aria-label="Legal and information">
          <Link href="/terms">Terms</Link>
          <Link href="/privacy">Privacy</Link>
          <Link href="/reward-policy">Reward policy</Link>
          <Link href="/withdrawal-policy">Withdrawal policy</Link>
        </nav>
        <small>Rewards are subject to offer eligibility, provider validation, and applicable policy.</small>
      </footer>
    </main>
  );
}
