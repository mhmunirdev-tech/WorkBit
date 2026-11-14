"use client";

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
          "The default reward policy allocates 70% of eligible provider payout to the user and 30% to WorkBit. WorkBit may configure different percentages or other policy limits; the applicable reward details are shown where available. Development/demo offers are identified as such and do not create real rewards.",
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
          "AyeT Studios is not represented as an active WorkBit partner unless and until the integration is approved, configured, and made available. If WorkBit later enables ayeT offers, we will identify the provider and make its applicable privacy notice and offer terms available before you start. Provider-specific information may be shared only as needed to attribute and verify offer activity, prevent abuse, process rewards or reversals, and reconcile transactions; the exact data depends on the approved integration.",
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
      "Effective November 13, 2026. This Policy describes how WorkBit Ltd, USA handles information when you use WorkBit.",
    sections: [
      {
        heading: "1. Who we are",
        paragraphs: [
          "WorkBit Ltd, USA (\"WorkBit\", \"we\", \"us\", or \"our\") operates the WorkBit website and rewards service. WorkBit determines how information collected through its Service is used. Privacy contact / Data Protection Officer: workbitbd@gmail.com. You may also submit a request through WorkBit Support.",
          "This Policy covers information WorkBit handles. Offer providers, survey companies, advertising partners, and other third parties may handle information under their own privacy notices when you use their services.",
        ],
      },
      {
        heading: "2. Information we collect and its sources",
        bullets: [
          "Account identifiers and contact details: name, email, country, optional phone number, account ID, referral details, account status, verification records, and password hash.",
          "Optional profile details, such as avatar and time zone.",
          "Wallet and transaction records: package and payment references, deposits, rewards, balances, withdrawal requests, payout method and destination, transaction history, and review notes. Saved mobile-banking payout destinations are encrypted for storage and masked in user-facing records.",
          "Offer and provider information: provider, offer, campaign, click, and transaction identifiers; timestamps; completion, reward, validation, and reversal status; and provider callback data.",
          "Technical and usage data: IP address and browser/device details in requests and offer activity, pages visited, and timestamps. First-party analytics uses a random browser identifier stored in local storage; the server records keyed hashes of that identifier and request IP, plus page and event data. Failed sign-in records use a masked email and keyed IP hash.",
          "Support and appeal information: support tickets, messages, and account-appeal statements.",
        ],
        paragraphs: [
          "We receive account and profile information mainly from you, technical data from your browser and use of the Service, and conversion or validation information from enabled offer and survey providers. WorkBit does not request date of birth or identity documents as part of ordinary account registration.",
        ],
      },
      {
        heading: "3. How and why we use information",
        bullets: [
          "Create and secure accounts; provide wallet, package, offer, support, and withdrawal features; and communicate service updates.",
          "Verify email and transactions, attribute and validate provider activity, calculate and record rewards, and process provider reversals.",
          "Prevent abuse, maintain service analytics, resolve disputes, and comply with legal obligations.",
          "Where European data-protection law applies, rely on contract to provide requested services; legitimate interests for security, abuse prevention, reliability, and aggregate usage analytics; legal obligations where applicable; and consent where the law requires it. Consent may be withdrawn for future processing based on that consent.",
        ],
      },
      {
        heading: "4. Offer providers, TheoremReach, and other disclosures",
        paragraphs: [
          "When an offer provider is enabled, WorkBit shares provider-specific information needed to open or attribute an offer and verify completion. This can include your WorkBit account ID or provider identifier, offer or campaign ID, country, click or transaction ID, timestamps, completion or reward status, and technical information such as IP address or browser/device details. Providers may also collect information directly through their own offerwalls, surveys, cookies, or tracking technologies.",
          "For TheoremReach, WorkBit sends a WorkBit user identifier and transaction, placement, and reward-currency configuration in the survey entry link. When loading its survey catalog, WorkBit also sends the account identifier, country, and request IP address. WorkBit receives provider callback and reward-related metadata; survey answers are collected by TheoremReach and handled under its own privacy policy. TheoremReach says surveys may collect device and usage information and responses that can include demographic or sensitive topics, and that responses may be shared with its survey customers. Participation is optional. Review TheoremReach's Privacy Policy before starting; requests about information it controls should also be sent to TheoremReach.",
          "When BitcoTasks is enabled, WorkBit passes a provider-specific 32-character user identifier to its SDK so BitcoTasks can show eligible offers and attribute activity. The SDK runs in your browser and BitcoTasks may process your IP address, browser/device information, and offer activity under its own terms and privacy notice. WorkBit receives callback and reward-related metadata, not survey answers or task proof submitted directly to BitcoTasks.",
          "WorkBit may disclose information to service providers that host or secure the Service, deliver transactional email, store profile images, support payments or payouts, or provide advertising and analytics tools. We may also disclose information when required by law, to protect users and the Service, or as part of a business reorganization or transfer.",
          "WorkBit does not sell personal information for money. Some advertising partners may receive or collect online identifiers, device/browser information, IP address, or ad interaction data when ad placements load. Depending on the use, an ad-related disclosure for cross-context behavioral advertising may be considered \"sharing\" under California law. You may request an opt-out where applicable using the rights process below and may also use controls offered by the advertising provider.",
        ],
      },
      {
        heading: "5. Cookies, local storage, and advertising",
        paragraphs: [
          "WorkBit uses an essential session cookie to keep you signed in. WorkBit also stores a random identifier in browser local storage for first-party page-usage analytics; the server stores a keyed hash rather than the raw visitor identifier. Offer providers and advertising partners may use their own cookies, local storage, device identifiers, or similar technologies when you use their services or view their placements. Browser controls can limit some storage, but this may affect sign-in, offer attribution, or provider features. Where consent is legally required for a non-essential technology, it must be obtained before that technology is used.",
        ],
      },
      {
        heading: "6. Retention and security",
        paragraphs: [
          "We keep information only as long as reasonably necessary to provide the Service, maintain financial and transaction records, resolve disputes, prevent abuse, and meet legal obligations. First-party analytics and selected sign-in/fraud signals are retained for up to 90 days under applicable event-processing jobs. Wallet, payment, withdrawal, and audit records may be kept longer where needed for accounting, legal, security, or dispute-resolution purposes.",
          "WorkBit uses safeguards intended to protect information, including password hashing, keyed one-way identifiers for selected security and analytics records, and encryption for saved payout destinations. No internet transmission or storage method can be guaranteed completely secure.",
        ],
      },
      {
        heading: "7. International processing",
        paragraphs: [
          "WorkBit is identified as a USA-based operator. Information may be processed in the United States and other countries where WorkBit or its service providers operate. Where data-protection law restricts an international transfer, WorkBit will use a transfer mechanism required by that law. You may contact WorkBit for information about safeguards applicable to a particular transfer.",
        ],
      },
      {
        heading: "8. EEA, UK, and similar privacy rights",
        paragraphs: [
          "Where GDPR or similar law applies, you may have the right to receive information about processing and access your data; correct inaccurate data; request erasure or restriction in certain circumstances; receive certain data in a portable format; object to processing based on legitimate interests, including direct marketing; withdraw consent where processing is based on consent; and complain to your local data-protection supervisory authority.",
          "WorkBit may use rules and risk signals to identify activity for review. A shared IP address alone does not automatically ban an account; account restrictions require an authorized review decision. Where a decision with significant effects is made solely by automated means, you may have rights to request human involvement or challenge it under applicable law.",
        ],
      },
      {
        heading: "9. California privacy rights",
        paragraphs: [
          "If the California Consumer Privacy Act, as amended, applies to WorkBit and to you, you may have the right to know/access personal information collected, disclosed, or sold; request deletion or correction; opt out of sale or sharing for cross-context behavioral advertising; limit certain uses or disclosures of sensitive personal information; and receive equal treatment for exercising your rights. Exceptions may apply.",
          "Categories WorkBit may collect include identifiers and contact details; account and financial records; commercial and transaction information; internet or device activity; country or other location-related information; and inferences or risk signals used for account security. Sources include you, your browser/device and use of the Service, and enabled providers. We use and disclose these categories for the purposes and recipient categories described above. WorkBit does not sell personal information for money; certain ad-related disclosures may constitute \"sharing\" under California law as described above.",
        ],
      },
      {
        heading: "10. Submitting a privacy request",
        paragraphs: [
          "Submit an access, correction, deletion, restriction, portability, objection, or California opt-out request through WorkBit Support or workbitbd@gmail.com. We may request information reasonably needed to verify your identity and protect your account. An authorized agent may submit a request where the law permits, subject to verification. We will respond within the period required by applicable law, explain a denial where required, and will not discriminate against you for exercising a privacy right.",
          "WorkBit does not currently provide self-service account deletion. You may request deletion through the process above. Some transaction, payment, security, or audit records may need to be retained or restricted rather than erased. Requests concerning information collected directly by an offer, survey, or advertising provider should also be sent to that provider.",
        ],
      },
      {
        heading: "11. Children, changes, and contact",
        paragraphs: [
          "The Service is intended for people aged 18 or older (or the higher age of majority where required). WorkBit does not knowingly allow minors to register or participate in offers. Contact WorkBit if you believe a minor has provided information.",
          "We may update this Policy and publish the revised version and effective date. WorkBit Ltd, USA is the named operator. Privacy contact / Data Protection Officer: workbitbd@gmail.com.",
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
          "The current default policy allocates 70% of eligible provider payout to the user and 30% to WorkBit. The policy applied to a conversion may be configured by WorkBit and can include limits, rounding, or other eligibility rules. Where provided, the offer's displayed user reward is an estimate or catalog value; the validated ledger decision is the record of the amount actually credited.",
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
          <Link className="text-link" href="/">Back to home</Link>
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
