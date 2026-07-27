"use client";

import { useEffect, useRef } from "react";
import { gsap } from "gsap";
import { ScrollTrigger } from "gsap/ScrollTrigger";

export default function ScenePinned({
  testId, image, eyebrow, lines = [], align = "left", tall = false, imageScale = 1.08,
}: {
  testId: string; image: string; eyebrow?: string; lines?: any[]; align?: string; tall?: boolean; imageScale?: number;
}) {
  const sectionRef = useRef<HTMLElement>(null);
  const imgRef = useRef<HTMLImageElement>(null);
  const linesRef = useRef<HTMLElement[]>([]);
  linesRef.current = [];

  const addLine = (el: HTMLElement | null) => {
    if (el && !linesRef.current.includes(el)) linesRef.current.push(el);
  };

  useEffect(() => {
    gsap.registerPlugin(ScrollTrigger);
    const ctx = gsap.context(() => {
      gsap.fromTo(imgRef.current, { scale: imageScale, y: "-3%", opacity: 0 }, {
        scale: 1, y: "3%", opacity: 1, ease: "none",
        scrollTrigger: { trigger: sectionRef.current, start: "top bottom", end: "bottom top", scrub: true },
      });

      const tl = gsap.timeline({
        scrollTrigger: {
          trigger: sectionRef.current,
          start: "top top",
          end: tall ? "+=180%" : "+=160%",
          scrub: 0.6, pin: true, pinSpacing: true,
        },
      });

      const total = linesRef.current.length;
      linesRef.current.forEach((el, i) => {
        tl.fromTo(el,
          { opacity: 0, y: 30, filter: "blur(8px)" },
          { opacity: 1, y: 0, filter: "blur(0px)", duration: 1, ease: "power2.out" },
          i * 1.2
        );
        if (i < total - 1) {
          tl.to(el, { opacity: 0.18, filter: "blur(2px)", duration: 0.8, ease: "power1.in" }, i * 1.2 + 0.9);
        }
      });
      tl.to(sectionRef.current, { opacity: 0, duration: 1, ease: "power2.inOut" }, total * 1.2);
    }, sectionRef);
    return () => ctx.revert();
  }, [imageScale, tall]);

  const alignClass =
    align === "right" ? "items-end text-right pr-[8vw]" :
    align === "center" ? "items-center text-center" :
    "items-start text-left pl-[8vw]";

  return (
    <section ref={sectionRef} data-testid={testId} className="relative h-screen w-full overflow-hidden">
      <img ref={imgRef} src={image} alt="" aria-hidden="true" className="scene-img" />
      <div className="absolute inset-0 bg-[#050505]/45" />
      <div className="absolute inset-0"
        style={{
          background:
            align === "right" ? "linear-gradient(270deg, rgba(5,5,5,0.92) 0%, rgba(5,5,5,0.4) 50%, transparent 100%)" :
            align === "center" ? "linear-gradient(180deg, rgba(5,5,5,0.5) 0%, rgba(5,5,5,0.35) 50%, rgba(5,5,5,0.9) 100%)" :
            "linear-gradient(90deg, rgba(5,5,5,0.92) 0%, rgba(5,5,5,0.4) 50%, transparent 100%)",
        }} />
      <div className="vignette" />
      <div className={`relative z-10 h-full flex flex-col justify-center ${alignClass}`}>
        <div className="max-w-2xl">
          <div className="space-y-7">
            {lines.map((l) => (
              <p
                key={l.id}
                ref={addLine}
                data-testid={l.id}
                className={`font-display font-extrabold tracking-[-0.035em] leading-[1.05] ${
                  l.large ? "text-[clamp(48px,7vw,96px)]" :
                  l.emphasize ? "text-[clamp(32px,4.4vw,64px)]" :
                  "text-[clamp(26px,3.4vw,52px)]"
                } ${l.accent ? "text-amber-400" : "text-white"}`}
                style={{ opacity: 0 }}
              >
                {l.text}
              </p>
            ))}
          </div>
        </div>
      </div>

    </section>
  );
}
