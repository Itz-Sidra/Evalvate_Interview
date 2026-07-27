"use client";

import { useEffect, useRef } from "react";
import { gsap } from "gsap";
import { ScrollTrigger } from "gsap/ScrollTrigger";
import { TID } from "@/constants/landingTestIds";

export default function SceneCurtain() {
  const sectionRef = useRef<HTMLElement>(null);
  const logoRef = useRef<HTMLHeadingElement>(null);
  const leftRef = useRef<HTMLDivElement>(null);
  const rightRef = useRef<HTMLDivElement>(null);
  const subRef = useRef<HTMLParagraphElement>(null);
  const scrollHintRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    gsap.registerPlugin(ScrollTrigger);
    const ctx = gsap.context(() => {
      gsap.from(logoRef.current, { opacity: 0, y: 30, duration: 1.6, ease: "expo.out", delay: 0.3 });
      gsap.from(subRef.current, { opacity: 0, y: 12, duration: 1.4, ease: "expo.out", delay: 0.9 });
      gsap.fromTo(scrollHintRef.current, { opacity: 0 }, { opacity: 1, duration: 1.2, delay: 1.6, ease: "power2.out" });

      const tl = gsap.timeline({
        scrollTrigger: {
          trigger: sectionRef.current,
          start: "top top",
          end: "+=120%",
          scrub: 0.8,
          pin: true,
          pinSpacing: true,
        },
      });

      tl.to(logoRef.current, { scale: 1.15, opacity: 0, ease: "power2.in" }, 0)
        .to(subRef.current, { opacity: 0, ease: "power1.out" }, 0)
        .to(leftRef.current, { xPercent: -100, ease: "power2.inOut" }, 0)
        .to(rightRef.current, { xPercent: 100, ease: "power2.inOut" }, 0)
        .to(sectionRef.current, { opacity: 0, ease: "power2.inOut" }, 0.5);
    }, sectionRef);
    return () => ctx.revert();
  }, []);

  return (
    <section ref={sectionRef} className="relative h-screen w-full overflow-hidden" id="top">
      <div className="absolute inset-0 z-30 flex flex-col items-center justify-center pointer-events-none">

        <h1
          ref={logoRef}
          data-testid={TID.curtainLogo}
          className="font-display font-extrabold text-[clamp(64px,14vw,220px)] leading-none tracking-tight text-white amber-glow"
        >
          evalvate
        </h1>
        <p ref={subRef} className="mt-8 max-w-xl text-center text-white/55 font-mono text-[12px] tracking-[0.25em] uppercase">
          interview preparation platform
        </p>

      </div>
      <div ref={leftRef} data-testid={TID.curtainLeft}
        className="absolute top-0 left-0 w-1/2 h-full z-20 bg-[#050505]"
        style={{ backgroundImage: "linear-gradient(90deg, #000 0%, #050505 70%, #0a0a0a 100%)", boxShadow: "inset -1px 0 0 rgba(245,158,11,0.06)" }} />
      <div ref={rightRef} data-testid={TID.curtainRight}
        className="absolute top-0 right-0 w-1/2 h-full z-20 bg-[#050505]"
        style={{ backgroundImage: "linear-gradient(270deg, #000 0%, #050505 70%, #0a0a0a 100%)", boxShadow: "inset 1px 0 0 rgba(245,158,11,0.06)" }} />
      <div className="absolute inset-0 z-0 flex items-center justify-center">
        <div className="w-[60vmin] h-[60vmin] rounded-full door-light opacity-40 blur-3xl" />
      </div>
    </section>
  );
}
