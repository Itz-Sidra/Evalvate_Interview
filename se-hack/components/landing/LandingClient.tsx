"use client";

import { useEffect, useRef } from "react";
import { gsap } from "gsap";
import { ScrollTrigger } from "gsap/ScrollTrigger";
import Lenis from "lenis";
import { TID } from "@/constants/landingTestIds";
import Nav from "@/components/landing/Nav";
import SceneCurtain from "@/components/landing/SceneCurtain";
import ScenePinned from "@/components/landing/ScenePinned";
import SceneReveal from "@/components/landing/SceneReveal";
import ProductShowcase from "@/components/landing/ProductShowcase";
import FinalCTA from "@/components/landing/FinalCTA";

import "./landing.css";

gsap.registerPlugin(ScrollTrigger);

export default function LandingClient() {
  const progressRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    // Initialize Lenis
    const lenis = new Lenis({
      duration: 1.4,
      easing: (t) => Math.min(1, 1.001 - Math.pow(2, -10 * t)),
    });

    function raf(time: number) {
      lenis.raf(time);
      requestAnimationFrame(raf);
    }
    requestAnimationFrame(raf);

    // Initialize GSAP progress bar
    const ctx = gsap.context(() => {
      gsap.to(progressRef.current, {
        scaleX: 1,
        ease: "none",
        scrollTrigger: {
          trigger: document.body,
          start: "top top",
          end: "bottom bottom",
          scrub: 0.2,
        },
      });
    });

    return () => {
      lenis.destroy();
      ctx.revert();
    };
  }, []);

  return (
    <div className="landing-page">
      <div className="grain" />
      <main className="relative bg-[#050505] text-white">
        <div className="fixed top-0 left-0 right-0 h-[2px] z-[200] bg-white/5">
          <div ref={progressRef} className="h-full bg-gradient-to-r from-orange-500 via-orange-400 to-orange-300 origin-left scale-x-0" />
        </div>
        <Nav />
        <SceneCurtain />
        <ScenePinned
          testId={TID.scene2Section}
          image="/scenes/scene2_waiting_room.png"
          eyebrow="Preparation"
          lines={[
            { id: TID.scene2Line1, text: "Master your next" },
            { id: TID.scene2Line1 + "-b", text: "technical interview.", accent: true },
            { id: TID.scene2Line2, text: "Practice with AI tailored to your role." },
            { id: TID.scene2Line3, text: "Get real-time feedback." },
            { id: TID.scene2Line4, text: "Nail your dream job.", emphasize: true },
          ]}
          align="left"
        />
        <ScenePinned
          testId={TID.scene3Section}
          image="/scenes/scene3_hands.png"
          eyebrow="Performance"
          lines={[
            { id: TID.scene3Line1, text: "Go beyond just answering questions." },
            { id: TID.scene3Line2, text: "Analyze your pacing and tone." },
            { id: TID.scene3Line3, text: "Read facial expressions." },
            { id: TID.scene3Line4, text: "Quantify your confidence.", accent: true, emphasize: true },
          ]}
          align="right"
          imageScale={1.15}
        />
        <ScenePinned
          testId={TID.scene4Section}
          image="/scenes/scene4_walk.png"
          eyebrow="Results"
          lines={[
            { id: TID.scene4Line1, text: "The moment always arrives." },
            { id: TID.scene4Line2, text: "Walk in ready.", accent: true, emphasize: true, large: true },
          ]}
          align="center"
          tall
        />
        <SceneReveal />
        <ProductShowcase />
        <FinalCTA />

      </main>
    </div>
  );
}
