"use client";

import { useEffect, useRef } from "react";
import { gsap } from "gsap";
import { ScrollTrigger } from "gsap/ScrollTrigger";
import { TID } from "@/constants/landingTestIds";

export default function SceneReveal() {
  const sectionRef = useRef<HTMLElement>(null);
  const imgRef = useRef<HTMLImageElement>(null);
  const lightRef = useRef<HTMLDivElement>(null);
  const flashRef = useRef<HTMLDivElement>(null);
  const linesRef = useRef<HTMLElement[]>([]);
  linesRef.current = [];

  const addLine = (el: HTMLElement | null) => {
    if (el && !linesRef.current.includes(el)) linesRef.current.push(el);
  };

  useEffect(() => {
    gsap.registerPlugin(ScrollTrigger);
    const ctx = gsap.context(() => {
      const tl = gsap.timeline({
        scrollTrigger: {
          trigger: sectionRef.current,
          start: "top top", end: "+=220%",
          scrub: 0.7, pin: true, pinSpacing: true,
        },
      });

      tl.fromTo(imgRef.current, { scale: 1.08, opacity: 0.4 }, { scale: 1, opacity: 1, ease: "power1.out" }, 0);
      tl.fromTo(lightRef.current, { scale: 0.4, opacity: 0.25 }, { scale: 1.4, opacity: 0.95, ease: "power2.out" }, 0.1);
      tl.to(flashRef.current, { opacity: 1, ease: "power3.in" }, 0.6);

      linesRef.current.forEach((el, i) => {
        tl.fromTo(el,
          { opacity: 0, y: 24, filter: "blur(8px)" },
          { opacity: 1, y: 0, filter: "blur(0px)", duration: 1, ease: "power2.out" },
          1 + i * 0.6
        );
      });
    }, sectionRef);
    return () => ctx.revert();
  }, []);

  const lines = [
    { id: TID.scene5Line1, text: "Walk in" },
    { id: TID.scene5Line1 + "-b", text: "prepared.", accent: true },
    { id: TID.scene5Line2, text: "Practice real interviews." },
    { id: TID.scene5Line3, text: "Receive instant feedback." },
    { id: TID.scene5Line4, text: "Build confidence before it matters." },
  ];

  return (
    <section ref={sectionRef} data-testid={TID.scene5Section} className="relative h-screen w-full overflow-hidden bg-black">
      <img ref={imgRef} src="/scenes/scene5_door.png" alt="" aria-hidden="true" className="scene-img" />
      <div className="absolute inset-0 bg-black/30" />
      <div ref={lightRef} className="absolute inset-0 door-light" style={{ transformOrigin: "center" }} />
      <div ref={flashRef} className="absolute inset-0 opacity-0"
        style={{ background: "radial-gradient(circle at center, rgba(255,236,196,1) 0%, rgba(245,158,11,0.9) 35%, rgba(15,10,5,1) 90%)" }} />
      <div className="relative z-20 h-full flex flex-col items-center justify-center text-center px-6">

        <div className="flex flex-wrap items-center justify-center gap-x-5 gap-y-2 mb-12">
          {lines.slice(0, 2).map((l) => (
            <p key={l.id} ref={addLine} data-testid={l.id}
              className={`font-display font-extrabold tracking-[-0.04em] leading-[1] text-[clamp(56px,9vw,140px)] ${l.accent ? "text-orange-500" : "text-white"}`}
              style={{ opacity: 0 }}>
              {l.text}
            </p>
          ))}
        </div>
        <div className="space-y-5 max-w-2xl">
          {lines.slice(2).map((l) => (
            <p key={l.id} ref={addLine} data-testid={l.id}
              className="font-display font-bold text-[clamp(20px,2.2vw,30px)] text-white/90 tracking-tight"
              style={{ opacity: 0 }}>
              {l.text}
            </p>
          ))}
        </div>
      </div>
    </section>
  );
}
