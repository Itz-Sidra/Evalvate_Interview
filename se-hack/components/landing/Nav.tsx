"use client";

import { TID } from "@/constants/landingTestIds";

export default function Nav() {
  const onStart = () => {
    document.getElementById("final-cta")?.scrollIntoView({ behavior: "smooth" });
  };

  return (
    <nav className="fixed top-0 left-0 right-0 z-[150] px-8 md:px-12 py-6 flex items-center justify-between mix-blend-difference">
      <a href="#top" data-testid={TID.navLogo} className="flex items-center gap-2 group">
        <span className="font-display font-extrabold text-[24px] tracking-tight text-white">evalvate</span>
      </a>
      <div className="flex items-center gap-3">

        <button onClick={() => window.location.href = '/login'} className="btn-ghost">
          Login
        </button>
        <button data-testid={TID.navStartCta} onClick={onStart} className="btn-primary" style={{ padding: '10px 24px', fontSize: '14px' }}>
          Get Started
        </button>
      </div>
    </nav>
  );
}
