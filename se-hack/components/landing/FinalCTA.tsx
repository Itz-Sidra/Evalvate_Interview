"use client";

import { useEffect, useRef } from "react";
import { gsap } from "gsap";
import { ScrollTrigger } from "gsap/ScrollTrigger";
import { ArrowRight } from "lucide-react";
import { TID } from "@/constants/landingTestIds";
import { useRouter } from "next/navigation";

export default function FinalCTA() {
  const sectionRef = useRef<HTMLElement>(null);
  const headingRef = useRef<HTMLHeadingElement>(null);
  const ctaRef = useRef<HTMLDivElement>(null);
  const router = useRouter();

  useEffect(() => {
    gsap.registerPlugin(ScrollTrigger);
    const ctx = gsap.context(() => {
      gsap.from(headingRef.current, {
        opacity: 0, y: 60, duration: 1.4, ease: "expo.out",
        scrollTrigger: { trigger: sectionRef.current, start: "top 75%" },
      });
      gsap.from(ctaRef.current, {
        opacity: 0, y: 24, duration: 1, delay: 0.2, ease: "expo.out",
        scrollTrigger: { trigger: sectionRef.current, start: "top 75%" },
      });
    }, sectionRef);
    return () => ctx.revert();
  }, []);

  return (
    <section id="final-cta" ref={sectionRef}
      className="relative bg-[#050505] py-40 px-6 md:px-12 overflow-hidden">
      <div className="absolute -bottom-40 left-1/2 -translate-x-1/2 w-[140vmin] h-[80vmin] door-light opacity-25 blur-3xl pointer-events-none" />
      <div className="absolute inset-0 opacity-[0.04] pointer-events-none"
        style={{
          backgroundImage: "linear-gradient(rgba(255,255,255,1) 1px, transparent 1px), linear-gradient(90deg, rgba(255,255,255,1) 1px, transparent 1px)",
          backgroundSize: "80px 80px",
        }} />
      <div className="relative max-w-5xl mx-auto text-center">

        <h2 ref={headingRef}
          className="font-display font-extrabold text-[clamp(56px,10vw,160px)] leading-[0.92] tracking-[-0.05em] text-white">
          The door <br />
          <span className="text-orange-500">opens once.</span>
        </h2>
        <p className="mt-10 max-w-xl mx-auto text-white/55 text-[17px] leading-relaxed">
          You don't get a second take. But you can rehearse the take until it feels like memory. Walk in different.
        </p>
        <div ref={ctaRef} className="mt-14 flex flex-col sm:flex-row items-center justify-center gap-5">
          <a
            href="/api/auth/google"
            className="btn-primary inline-flex items-center gap-2"
            data-testid={TID.finalCta}
          >
            Start Your Interview
            <ArrowRight strokeWidth={2} className="w-4 h-4" />
          </a>
        </div>
      </div>
    </section>
  );
}
