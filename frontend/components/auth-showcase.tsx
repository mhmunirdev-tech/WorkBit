import Image from "next/image";
import Link from "next/link";
import { ShieldCheck, UsersRound, Zap } from "lucide-react";

export function AuthShowcase() {
  return (
    <aside className="auth-showcase" aria-label="WorkBit welcome">
      <Link className="brand auth-showcase-brand" href="/"><i>W</i> WorkBit</Link>
      <div className="auth-hero-art">
        <Image
          src="/images/auth-background.png"
          alt="A WorkBit member working at a laptop, with secure account and community symbols"
          width={1536}
          height={1024}
          priority
          unoptimized
          sizes="(max-width: 700px) 100vw, 50vw"
        />
      </div>
      <div className="auth-showcase-copy">
        <span className="auth-showcase-mark">WORK SMARTER</span>
        <h2>Your journey <span>begins here.</span></h2>
        <p>Make your ideas a reality with a community built around progress and rewards.</p>
      </div>
      <div className="auth-benefits">
        <div><Zap aria-hidden="true" /><span><strong>Fast &amp; Easy</strong><small>Get started in minutes</small></span></div>
        <div><ShieldCheck aria-hidden="true" /><span><strong>Secure</strong><small>Your data is safe</small></span></div>
        <div><UsersRound aria-hidden="true" /><span><strong>Grow Together</strong><small>Build your future</small></span></div>
      </div>
    </aside>
  );
}
