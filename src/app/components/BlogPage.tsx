import React, { useState, useEffect, useRef } from "react";
import { motion, useInView } from "motion/react";
import {
  ArrowRight,
  Clock,
  Grid3X3,
  List,
  BookOpen,
  TrendingUp,
  Users,
  ChevronRight,
  Zap,
} from "lucide-react";
import "./blog.css";

/* ─── Data ─────────────────────────────────────────────── */
const CATEGORIES = [
  "All",
  "Design",
  "Technology",
  "Strategy",
  "Branding",
  "Motion",
  "Typography",
  "UX",
];

const TICKER_ITEMS = [
  "Design Systems",
  "Motion Design",
  "UX Research",
  "Brand Identity",
  "Typography",
  "AI & Design",
  "Creative Direction",
  "Web Experience",
  "Visual Language",
  "Product Design",
  "Interaction Design",
  "Interface Futures",
];

interface Post {
  id: number;
  title: string;
  excerpt: string;
  category: string;
  author: string;
  date: string;
  readTime: number;
  image: string;
  likes: number;
}

const POSTS: Post[] = [
  {
    id: 1,
    title:
      "The Architecture of Perception: How Visual Hierarchy Reshapes Thought",
    excerpt:
      "Exploring the deep connection between spatial design and cognitive processing — and why the best interfaces feel inevitable.",
    category: "Design",
    author: "Aria Nakamura",
    date: "Apr 12, 2026",
    readTime: 7,
    likes: 84,
    image:
      "https://images.unsplash.com/photo-1764258560292-ba76effe9797?crop=entropy&cs=tinysrgb&fit=max&fm=jpg&ixid=M3w3Nzg4Nzd8MHwxfHNlYXJjaHwxfHxmdXR1cmlzdGljJTIwZGVzaWduJTIwY3JlYXRpdmUlMjBhYnN0cmFjdHxlbnwxfHx8fDE3NzYzNTc4NjZ8MA&ixlib=rb-4.1.0&q=80&w=1080",
  },
  {
    id: 2,
    title: "Brutalism's Digital Renaissance: Raw Structure in a Polished World",
    excerpt:
      "Why designers are deliberately breaking conventions — and how controlled chaos creates unforgettable experiences.",
    category: "Design",
    author: "Marcus Chen",
    date: "Apr 8, 2026",
    readTime: 5,
    likes: 61,
    image:
      "https://images.unsplash.com/photo-1543829285-a3b7157052a7?crop=entropy&cs=tinysrgb&fit=max&fm=jpg&ixid=M3w3Nzg4Nzd8MHwxfHNlYXJjaHwxfHxtb2Rlcm4lMjBhcmNoaXRlY3R1cmUlMjBtaW5pbWFsaXN0JTIwZGFya3xlbnwxfHx8fDE3NzYzNTc4NjV8MA&ixlib=rb-4.1.0&q=80&w=1080",
  },
  {
    id: 3,
    title: "Neural Interfaces & the Future of Creative Tools",
    excerpt:
      "As AI becomes co-creator, the tools we use to think and make are undergoing a profound transformation.",
    category: "Technology",
    author: "Zara Williams",
    date: "Apr 5, 2026",
    readTime: 9,
    likes: 112,
    image:
      "https://images.unsplash.com/photo-1735713212083-82eafc42bf64?crop=entropy&cs=tinysrgb&fit=max&fm=jpg&ixid=M3w3Nzg4Nzd8MHwxfHNlYXJjaHwxfHx0ZWNobm9sb2d5JTIwY2lyY3VpdCUyMGJvYXJkJTIwbmVvbiUyMGdsb3d8ZW58MXx8fHwxNzc2MzU3ODY2fDA&ixlib=rb-4.1.0&q=80&w=1080",
  },
  {
    id: 4,
    title: "Crafting Brand Souls: Identity Systems That Actually Work",
    excerpt:
      "Great brands aren't built in a day — they're built in obsessive iterations of purpose, form, and feeling.",
    category: "Branding",
    author: "Lena Okonkwo",
    date: "Apr 1, 2026",
    readTime: 6,
    likes: 74,
    image:
      "https://images.unsplash.com/photo-1763236605962-798f9de97410?crop=entropy&cs=tinysrgb&fit=max&fm=jpg&ixid=M3w3Nzg4Nzd8MHwxfHNlYXJjaHwxfHxicmFuZGluZyUyMGlkZW50aXR5JTIwZGVzaWduJTIwc3R1ZGlvfGVufDF8fHx8MTc3NjM1Nzg2Nnww&ixlib=rb-4.1.0&q=80&w=1080",
  },
  {
    id: 5,
    title: "The Grammar of Motion: Principles for Meaningful Animation",
    excerpt:
      "Animation is a language. Learning its grammar separates interfaces that merely move from ones that communicate.",
    category: "Motion",
    author: "Soren Kim",
    date: "Mar 28, 2026",
    readTime: 8,
    likes: 98,
    image:
      "https://images.unsplash.com/photo-1764258559785-6229d5f9e50e?crop=entropy&cs=tinysrgb&fit=max&fm=jpg&ixid=M3w3Nzg4Nzd8MHwxfHNlYXJjaHwxfHxtb3Rpb24lMjBncmFwaGljcyUyMGRpZ2l0YWwlMjBhcnQlMjBkYXJrfGVufDF8fHx8MTc3NjM1Nzg2Nnww&ixlib=rb-4.1.0&q=80&w=1080",
  },
  {
    id: 6,
    title: "Type as Texture: When Letters Become Architecture",
    excerpt:
      "The most expressive typographers treat letterforms not as vehicles for words, but as spatial elements in their own right.",
    category: "Typography",
    author: "Amara Diallo",
    date: "Mar 24, 2026",
    readTime: 4,
    likes: 47,
    image:
      "https://images.unsplash.com/photo-1775135595202-3848db75a2dc?crop=entropy&cs=tinysrgb&fit=max&fm=jpg&ixid=M3w3Nzg4Nzd8MHwxfHNlYXJjaHwxfHx0eXBvZ3JhcGh5JTIwY3JlYXRpdmUlMjBsZXR0ZXJpbmclMjBhcnR8ZW58MXx8fHwxNzc2MzU3ODY3fDA&ixlib=rb-4.1.0&q=80&w=1080",
  },
  {
    id: 7,
    title: "Beyond the Screen: Designing for Ambient Intelligence",
    excerpt:
      "As computing dissolves into the environment, UX designers must reimagine space, time, and presence.",
    category: "UX",
    author: "Rio Tanaka",
    date: "Mar 20, 2026",
    readTime: 11,
    likes: 133,
    image:
      "https://images.unsplash.com/photo-1772272935464-2e90d8218987?crop=entropy&cs=tinysrgb&fit=max&fm=jpg&ixid=M3w3Nzg4Nzd8MHwxfHNlYXJjaHwxfHx1aSUyMHV4JTIwcHJvZHVjdCUyMGRlc2lnbiUyMGludGVyZmFjZXxlbnwxfHx8fDE3NzYzNTc4Njd8MA&ixlib=rb-4.1.0&q=80&w=1080",
  },
  {
    id: 8,
    title: "Strategic Silence: Why Less Content Wins the Attention War",
    excerpt:
      "Content saturation has created a paradox — the brands that say less are heard more. A deep-dive into editorial restraint.",
    category: "Strategy",
    author: "Nadia Cross",
    date: "Mar 17, 2026",
    readTime: 6,
    likes: 58,
    image:
      "https://images.unsplash.com/photo-1562619425-c307bb83bc42?crop=entropy&cs=tinysrgb&fit=max&fm=jpg&ixid=M3w3Nzg4Nzd8MHwxfHNlYXJjaHwxfHxzcGFjZSUyMGNvc21vcyUyMGdhbGF4eSUyMG5lYnVsYSUyMGRhcmt8ZW58MXx8fHwxNzc2MzU3ODY3fDA&ixlib=rb-4.1.0&q=80&w=1080",
  },
];

/* ─── Animated Counter ──────────────────────────────────── */
function AnimCounter({
  value,
  suffix = "",
}: {
  value: number;
  suffix?: string;
}) {
  const ref = useRef<HTMLSpanElement>(null);
  const inView = useInView(ref, { once: true });
  const [count, setCount] = useState(0);

  useEffect(() => {
    if (!inView) return;
    const duration = 1600;
    const start = Date.now();
    const run = () => {
      const elapsed = Date.now() - start;
      const p = Math.min(elapsed / duration, 1);
      const eased = 1 - Math.pow(1 - p, 3);
      setCount(Math.floor(eased * value));
      if (p < 1) requestAnimationFrame(run);
      else setCount(value);
    };
    requestAnimationFrame(run);
  }, [inView, value]);

  return (
    <span ref={ref}>
      {count}
      {suffix}
    </span>
  );
}

/* ─── Tilt Card ─────────────────────────────────────────── */
function TiltCard({
  children,
  className = "",
  style,
  onClick,
}: {
  children: React.ReactNode;
  className?: string;
  style?: React.CSSProperties;
  onClick?: () => void;
}) {
  const innerRef = useRef<HTMLDivElement>(null);

  const onMove = (e: React.MouseEvent<HTMLDivElement>) => {
    const el = innerRef.current?.parentElement;
    if (!el) return;
    const r = el.getBoundingClientRect();
    const x = (e.clientX - r.left) / r.width - 0.5;
    const y = (e.clientY - r.top) / r.height - 0.5;
    if (innerRef.current) {
      innerRef.current.style.transform = `rotateX(${-y * 9}deg) rotateY(${x * 9}deg)`;
    }
  };

  const onLeave = () => {
    if (innerRef.current) {
      innerRef.current.style.transform = `rotateX(0deg) rotateY(0deg)`;
    }
  };

  return (
    <div
      style={{ perspective: "1100px", ...style }}
      onMouseMove={onMove}
      onMouseLeave={onLeave}
      onClick={onClick}
      className={className}
    >
      <div
        ref={innerRef}
        style={{
          transformStyle: "preserve-3d",
          transition: "transform 0.45s cubic-bezier(0.34,1.56,0.64,1)",
          height: "100%",
        }}
      >
        {children}
      </div>
    </div>
  );
}

/* ─── Category chip (used in featured) ─────────────────── */
function Chip({
  label,
  outline,
}: {
  label: string;
  outline?: boolean;
}) {
  return (
    <span
      style={{
        padding: "5px 12px",
        borderRadius: "999px",
        background: outline
          ? "transparent"
          : "rgba(243,198,35,0.12)",
        border: `1px solid ${outline ? "rgba(255,255,255,0.1)" : "rgba(243,198,35,0.22)"}`,
        color: outline ? "rgba(255,255,255,0.4)" : "#f3c623",
        fontFamily: "'Syne', sans-serif",
        fontSize: "10px",
        fontWeight: 800,
        letterSpacing: "0.12em",
        textTransform: "uppercase" as const,
      }}
    >
      {label}
    </span>
  );
}

/* ─── Post Card ─────────────────────────────────────────── */
function PostCard({
  post,
  wide,
  delay,
}: {
  post: Post;
  wide?: boolean;
  delay: number;
}) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 36 }}
      whileInView={{ opacity: 1, y: 0 }}
      viewport={{ once: true, margin: "-60px" }}
      transition={{ duration: 0.6, delay, ease: [0.25, 0.46, 0.45, 0.94] }}
      className={wide ? "span-2" : ""}
      style={{ gridColumn: wide ? "span 2" : undefined }}
    >
      <TiltCard style={{ height: "100%" }}>
        <div
          className="glass-card post-card-inner"
          style={{
            display: "flex",
            flexDirection: "column",
            height: "100%",
          }}
        >
          <div className="hud-tl" />
          <div className="hud-tr" />
          <div className="hud-bl" />
          <div className="hud-br" />
          <div className="holo-shimmer" />

          {/* Image */}
          <div
            className="pc-img-wrap"
            style={{ height: wide ? "270px" : "220px", flexShrink: 0 }}
          >
            <img src={post.image} alt={post.title} />
            {/* Overlay */}
            <div
              style={{
                position: "absolute",
                inset: 0,
                background:
                  "linear-gradient(to top, rgba(6,6,8,0.75) 0%, rgba(6,6,8,0.1) 50%, transparent 100%)",
                zIndex: 1,
              }}
            />
            {/* Category badge */}
            <span
              style={{
                position: "absolute",
                top: 16,
                left: 16,
                zIndex: 3,
                padding: "5px 11px",
                borderRadius: "999px",
                background: "rgba(243,198,35,0.14)",
                border: "1px solid rgba(243,198,35,0.26)",
                color: "#f3c623",
                fontFamily: "'Syne', sans-serif",
                fontSize: "9px",
                fontWeight: 800,
                letterSpacing: "0.14em",
                textTransform: "uppercase",
                backdropFilter: "blur(8px)",
              }}
            >
              {post.category}
            </span>
            {/* Read time */}
            <span
              style={{
                position: "absolute",
                bottom: 14,
                right: 14,
                zIndex: 3,
                display: "flex",
                alignItems: "center",
                gap: 4,
                padding: "5px 10px",
                borderRadius: "999px",
                background: "rgba(0,0,0,0.45)",
                border: "1px solid rgba(255,255,255,0.1)",
                color: "rgba(255,255,255,0.65)",
                fontSize: "10px",
                fontWeight: 500,
                backdropFilter: "blur(8px)",
              }}
            >
              <Clock size={10} />
              {post.readTime} min
            </span>
          </div>

          {/* Body */}
          <div
            style={{
              padding: "22px 22px 24px",
              display: "flex",
              flexDirection: "column",
              flex: 1,
            }}
          >
            {/* Meta */}
            <div
              style={{
                display: "flex",
                alignItems: "center",
                gap: 8,
                marginBottom: 12,
              }}
            >
              <div
                style={{
                  width: 26,
                  height: 26,
                  borderRadius: "50%",
                  background: "linear-gradient(135deg, #f3c623, #d49f10)",
                  color: "#060608",
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  fontFamily: "'Clash Display', sans-serif",
                  fontSize: "0.72rem",
                  fontWeight: 700,
                  flexShrink: 0,
                }}
              >
                {post.author[0]}
              </div>
              <span
                style={{
                  fontSize: "0.82rem",
                  fontWeight: 600,
                  color: "rgba(255,255,255,0.65)",
                }}
              >
                {post.author}
              </span>
              <span style={{ color: "rgba(255,255,255,0.25)", fontSize: 12 }}>
                ·
              </span>
              <span
                style={{
                  fontSize: "0.78rem",
                  color: "rgba(255,255,255,0.32)",
                }}
              >
                {post.date}
              </span>
            </div>

            {/* Title */}
            <h3
              style={{
                fontFamily: "'Clash Display', sans-serif",
                fontSize: wide ? "1.32rem" : "1.18rem",
                fontWeight: 700,
                lineHeight: 1.26,
                letterSpacing: "-0.01em",
                color: "#fff",
                marginBottom: 10,
              }}
            >
              {post.title}
            </h3>

            {/* Excerpt */}
            <p
              style={{
                fontSize: "0.87rem",
                color: "rgba(255,255,255,0.42)",
                lineHeight: 1.72,
                marginBottom: 20,
                flex: 1,
                display: "-webkit-box",
                WebkitLineClamp: 3,
                WebkitBoxOrient: "vertical" as const,
                overflow: "hidden",
                fontWeight: 300,
              }}
            >
              {post.excerpt}
            </p>

            {/* Footer */}
            <div
              style={{
                display: "flex",
                alignItems: "center",
                justifyContent: "space-between",
              }}
            >
              <button
                style={{
                  display: "inline-flex",
                  alignItems: "center",
                  gap: 6,
                  color: "#f3c623",
                  fontFamily: "'Syne', sans-serif",
                  fontSize: "0.82rem",
                  fontWeight: 700,
                  background: "none",
                  border: "none",
                  cursor: "pointer",
                  letterSpacing: "0.04em",
                  padding: 0,
                  transition: "gap 0.25s ease",
                }}
                onMouseEnter={(e) => {
                  (e.currentTarget as HTMLElement).style.gap = "12px";
                }}
                onMouseLeave={(e) => {
                  (e.currentTarget as HTMLElement).style.gap = "6px";
                }}
              >
                Read Article
                <ArrowRight size={13} />
              </button>

              {/* Likes */}
              <span
                style={{
                  fontSize: "0.77rem",
                  color: "rgba(255,255,255,0.3)",
                  padding: "4px 10px",
                  borderRadius: "999px",
                  border: "1px solid rgba(255,255,255,0.07)",
                  background: "rgba(255,255,255,0.02)",
                }}
              >
                {post.likes} likes
              </span>
            </div>
          </div>
        </div>
      </TiltCard>
    </motion.div>
  );
}

/* ─── Main Blog Page ────────────────────────────────────── */
export function BlogPage() {
  const [activeCategory, setActiveCategory] = useState("All");
  const [viewMode, setViewMode] = useState<"grid" | "list">("grid");
  const [email, setEmail] = useState("");
  const [subscribed, setSubscribed] = useState(false);

  const featured = POSTS[0];
  const gridPosts = POSTS.slice(1);
  const filteredPosts =
    activeCategory === "All"
      ? gridPosts
      : gridPosts.filter((p) => p.category === activeCategory);

  const tickerItems = [...TICKER_ITEMS, ...TICKER_ITEMS];

  return (
    <div className="blog-page">
      {/* ── Global overlays ── */}
      <div className="scan-beam" />
      <div className="scanlines" />

      {/* ── Background ── */}
      <div
        style={{ position: "fixed", inset: 0, pointerEvents: "none", zIndex: 0 }}
      >
        <div className="cyber-grid" />
        {/* Orbs */}
        <div
          className="bg-orb"
          style={{
            width: 700,
            height: 700,
            background:
              "radial-gradient(circle, rgba(243,198,35,0.16), transparent 70%)",
            top: -200,
            left: -150,
            animationDelay: "0s",
          }}
        />
        <div
          className="bg-orb"
          style={{
            width: 550,
            height: 550,
            background:
              "radial-gradient(circle, rgba(120,80,255,0.12), transparent 70%)",
            top: "30%",
            right: -150,
            animationDelay: "-6s",
          }}
        />
        <div
          className="bg-orb"
          style={{
            width: 450,
            height: 450,
            background:
              "radial-gradient(circle, rgba(243,198,35,0.08), transparent 70%)",
            bottom: "15%",
            left: "25%",
            animationDelay: "-11s",
          }}
        />
        <div
          className="bg-orb"
          style={{
            width: 380,
            height: 380,
            background:
              "radial-gradient(circle, rgba(0,200,180,0.07), transparent 70%)",
            bottom: -80,
            right: "10%",
            animationDelay: "-17s",
          }}
        />
        {/* Noise */}
        <div
          style={{
            position: "absolute",
            inset: 0,
            opacity: 0.025,
            backgroundImage: `url("data:image/svg+xml,%3Csvg viewBox='0 0 256 256' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='n'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.85' numOctaves='4' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23n)'/%3E%3C/svg%3E")`,
            backgroundSize: "128px",
          }}
        />
      </div>

      {/* ════════════════════════════════
          HERO
      ════════════════════════════════ */}
      <header
        style={{
          position: "relative",
          zIndex: 2,
          maxWidth: 1280,
          margin: "0 auto",
          padding: "130px 48px 80px",
          display: "flex",
          alignItems: "flex-end",
          justifyContent: "space-between",
          gap: 40,
        }}
      >
        <div style={{ flex: 1 }}>
          {/* Badge */}
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6 }}
            style={{
              display: "inline-flex",
              alignItems: "center",
              gap: 9,
              padding: "8px 18px",
              borderRadius: 999,
              background: "rgba(243,198,35,0.09)",
              border: "1px solid rgba(243,198,35,0.22)",
              color: "#f3c623",
              fontFamily: "'Syne', sans-serif",
              fontSize: 11,
              fontWeight: 700,
              letterSpacing: "0.14em",
              textTransform: "uppercase",
              marginBottom: 32,
            }}
          >
            <span className="pulse-dot" />
            Ideas & Insights
          </motion.div>

          {/* Title */}
          <div style={{ marginBottom: 28 }}>
            {["Where", "Ideas", "Live."].map((word, i) => (
              <motion.div
                key={word}
                initial={{ opacity: 0, x: -40 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ duration: 0.7, delay: 0.15 + i * 0.12, ease: [0.25, 0.46, 0.45, 0.94] }}
                className="glitch-host"
                style={{
                  display: "block",
                  fontFamily: "'Clash Display', sans-serif",
                  fontSize: "clamp(4.2rem, 9vw, 8.8rem)",
                  lineHeight: 0.92,
                  letterSpacing: "-0.03em",
                  fontWeight: 700,
                  color: i === 1 ? "transparent" : "#fff",
                  WebkitTextStroke:
                    i === 1 ? "2px #f3c623" : undefined,
                  textShadow:
                    i === 1 ? "0 0 80px rgba(243,198,35,0.28)" : undefined,
                }}
              >
                {word}
                {i === 1 && (
                  <>
                    <span className="glitch-a" style={{ WebkitTextStroke: "2px #f3c623" }}>{word}</span>
                    <span className="glitch-b" style={{ color: "#9b6bff", WebkitTextStroke: "none" }}>{word}</span>
                  </>
                )}
              </motion.div>
            ))}
          </div>

          {/* Subtitle */}
          <motion.p
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.7, delay: 0.58 }}
            style={{
              fontSize: "1.05rem",
              color: "rgba(255,255,255,0.62)",
              lineHeight: 1.78,
              maxWidth: 520,
              marginBottom: 44,
              fontWeight: 300,
            }}
          >
            Design philosophy, creative trends, studio stories & strategic
            thinking — curated for builders and makers.
          </motion.p>

          {/* Stats */}
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.7, delay: 0.72 }}
            style={{ display: "flex", alignItems: "center", gap: 24 }}
          >
            {[
              { icon: BookOpen, value: 48, label: "Articles", suffix: "" },
              { icon: TrendingUp, value: 7, label: "Topics", suffix: "" },
              { icon: Users, value: 12, label: "Readers", suffix: "k" },
            ].map(({ icon: Icon, value, label, suffix }, i) => (
              <React.Fragment key={label}>
                {i > 0 && (
                  <div
                    style={{
                      width: 1,
                      height: 40,
                      background: "rgba(255,255,255,0.08)",
                    }}
                  />
                )}
                <div style={{ display: "flex", flexDirection: "column", gap: 4 }}>
                  <div style={{ display: "flex", alignItems: "baseline", gap: 2 }}>
                    <span
                      style={{
                        fontFamily: "'Clash Display', sans-serif",
                        fontSize: "1.8rem",
                        fontWeight: 700,
                        color: "#fff",
                        lineHeight: 1,
                      }}
                    >
                      <AnimCounter value={value} suffix={suffix} />
                    </span>
                  </div>
                  <span
                    style={{
                      fontSize: "0.76rem",
                      color: "rgba(255,255,255,0.35)",
                      fontFamily: "'Syne', sans-serif",
                      fontWeight: 600,
                      letterSpacing: "0.08em",
                      textTransform: "uppercase",
                    }}
                  >
                    {label}
                  </span>
                </div>
              </React.Fragment>
            ))}
          </motion.div>
        </div>

        {/* Scroll cue */}
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 1.2 }}
          style={{
            display: "flex",
            flexDirection: "column",
            alignItems: "center",
            gap: 10,
            color: "rgba(255,255,255,0.3)",
            fontSize: "0.7rem",
            fontFamily: "'Syne', sans-serif",
            fontWeight: 700,
            letterSpacing: "0.1em",
            textTransform: "uppercase",
            flexShrink: 0,
          }}
        >
          <div className="scroll-cue-line" />
          <span>Scroll</span>
        </motion.div>
      </header>

      {/* ── Animated line ── */}
      <div style={{ maxWidth: 1280, margin: "0 auto", padding: "0 48px" }}>
        <div className="anim-line" />
      </div>

      {/* ════════════════════════════════
          TICKER
      ════════════════════════════════ */}
      <div
        className="ticker-outer"
        style={{
          padding: "28px 0",
          borderBottom: "1px solid rgba(255,255,255,0.05)",
          borderTop: "1px solid rgba(255,255,255,0.05)",
          margin: "32px 0 0",
          position: "relative",
          zIndex: 2,
        }}
      >
        <div className="ticker-track">
          {tickerItems.map((item, i) => (
            <div
              key={`${item}-${i}`}
              style={{
                display: "inline-flex",
                alignItems: "center",
                gap: 24,
                padding: "0 32px",
              }}
            >
              <span
                style={{
                  fontFamily: "'Syne', sans-serif",
                  fontSize: "0.78rem",
                  fontWeight: 700,
                  color: "rgba(255,255,255,0.35)",
                  letterSpacing: "0.1em",
                  textTransform: "uppercase",
                  whiteSpace: "nowrap",
                }}
              >
                {item}
              </span>
              <Zap
                size={10}
                style={{ color: "#f3c623", opacity: 0.5, flexShrink: 0 }}
              />
            </div>
          ))}
        </div>
      </div>

      {/* ════════════════════════════════
          FILTERS
      ════════════════════════════════ */}
      <div
        style={{
          position: "relative",
          zIndex: 2,
          maxWidth: 1280,
          margin: "0 auto",
          padding: "40px 48px 32px",
        }}
      >
        <div
          style={{
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
            gap: 20,
            flexWrap: "wrap",
          }}
        >
          {/* Pills */}
          <div style={{ display: "flex", flexWrap: "wrap", gap: 8 }}>
            {CATEGORIES.map((cat) => (
              <button
                key={cat}
                className={`cat-pill ${activeCategory === cat ? "cat-pill-active" : ""}`}
                onClick={() => setActiveCategory(cat)}
              >
                <span
                  style={{
                    width: 5,
                    height: 5,
                    borderRadius: "50%",
                    background: "currentColor",
                    opacity: 0.5,
                    flexShrink: 0,
                  }}
                />
                {cat}
              </button>
            ))}
          </div>

          {/* View toggle */}
          <div style={{ display: "flex", gap: 6, flexShrink: 0 }}>
            <button
              className={`view-btn ${viewMode === "grid" ? "view-btn-active" : ""}`}
              onClick={() => setViewMode("grid")}
              title="Grid view"
            >
              <Grid3X3 size={14} />
            </button>
            <button
              className={`view-btn ${viewMode === "list" ? "view-btn-active" : ""}`}
              onClick={() => setViewMode("list")}
              title="List view"
            >
              <List size={14} />
            </button>
          </div>
        </div>
      </div>

      {/* ════════════════════════════════
          FEATURED POST
      ════════════════════════════════ */}
      <section
        style={{
          position: "relative",
          zIndex: 2,
          maxWidth: 1280,
          margin: "0 auto 64px",
          padding: "0 48px",
        }}
      >
        {/* Label */}
        <div
          style={{
            display: "flex",
            alignItems: "center",
            gap: 8,
            marginBottom: 20,
          }}
        >
          <svg width="11" height="11" viewBox="0 0 12 12">
            <polygon
              points="6,1 7.5,4.5 11,5 8.5,7.5 9.2,11 6,9.3 2.8,11 3.5,7.5 1,5 4.5,4.5"
              fill="#f3c623"
            />
          </svg>
          <span
            style={{
              fontFamily: "'Syne', sans-serif",
              fontSize: "0.76rem",
              fontWeight: 700,
              color: "#f3c623",
              letterSpacing: "0.14em",
              textTransform: "uppercase",
            }}
          >
            Featured Story
          </span>
        </div>

        <motion.div
          initial={{ opacity: 0, y: 40 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true, margin: "-80px" }}
          transition={{ duration: 0.8, ease: [0.25, 0.46, 0.45, 0.94] }}
        >
          <div
            className="glass-card feat-glass"
            style={{ borderRadius: 28, overflow: "hidden" }}
          >
            <div className="hud-tl" />
            <div className="hud-tr" />
            <div className="hud-bl" />
            <div className="hud-br" />
            <div className="holo-shimmer" />

            <div className="feat-card-grid">
              {/* Image side */}
              <div className="feat-img-wrap">
                <img src={featured.image} alt={featured.title} />
                {/* Overlay */}
                <div
                  style={{
                    position: "absolute",
                    inset: 0,
                    background:
                      "linear-gradient(to right, rgba(6,6,8,0.35) 0%, transparent 60%), linear-gradient(to top, rgba(6,6,8,0.5) 0%, transparent 50%)",
                    zIndex: 1,
                  }}
                />
                {/* Bokeh */}
                <div
                  style={{
                    position: "absolute",
                    width: 320,
                    height: 320,
                    borderRadius: "50%",
                    background: "rgba(243,198,35,0.22)",
                    filter: "blur(28px)",
                    top: -80,
                    left: -80,
                    zIndex: 0,
                    mixBlendMode: "overlay",
                    pointerEvents: "none",
                  }}
                />
                <div
                  style={{
                    position: "absolute",
                    width: 200,
                    height: 200,
                    borderRadius: "50%",
                    background: "rgba(120,80,255,0.18)",
                    filter: "blur(22px)",
                    bottom: -40,
                    right: -30,
                    zIndex: 0,
                    mixBlendMode: "overlay",
                    pointerEvents: "none",
                  }}
                />
                {/* Category label */}
                <div
                  style={{
                    position: "absolute",
                    top: 24,
                    left: 24,
                    zIndex: 4,
                    padding: "8px 14px",
                    borderRadius: 999,
                    background: "rgba(243,198,35,0.15)",
                    border: "1px solid rgba(243,198,35,0.3)",
                    color: "#f3c623",
                    fontFamily: "'Syne', sans-serif",
                    fontSize: 10,
                    fontWeight: 800,
                    letterSpacing: "0.15em",
                    textTransform: "uppercase",
                    backdropFilter: "blur(8px)",
                  }}
                >
                  {featured.category}
                </div>
                {/* Read time */}
                <div
                  style={{
                    position: "absolute",
                    bottom: 24,
                    right: 24,
                    zIndex: 4,
                    display: "flex",
                    alignItems: "center",
                    gap: 5,
                    padding: "6px 12px",
                    borderRadius: 999,
                    background: "rgba(0,0,0,0.45)",
                    border: "1px solid rgba(255,255,255,0.12)",
                    color: "rgba(255,255,255,0.7)",
                    fontSize: 11,
                    fontWeight: 500,
                    backdropFilter: "blur(8px)",
                  }}
                >
                  <Clock size={11} />
                  {featured.readTime} min read
                </div>
              </div>

              {/* Content side */}
              <div
                style={{
                  padding: "52px 48px",
                  display: "flex",
                  flexDirection: "column",
                  justifyContent: "center",
                  background:
                    "linear-gradient(135deg, rgba(255,255,255,0.02), transparent)",
                }}
              >
                {/* Chips */}
                <div style={{ display: "flex", gap: 8, marginBottom: 22 }}>
                  <Chip label={featured.category} />
                  <Chip label="Featured" outline />
                </div>

                {/* Title */}
                <h2
                  style={{
                    fontFamily: "'Clash Display', sans-serif",
                    fontSize: "clamp(1.9rem, 3.2vw, 3rem)",
                    fontWeight: 700,
                    lineHeight: 1.07,
                    letterSpacing: "-0.02em",
                    color: "#fff",
                    marginBottom: 18,
                  }}
                >
                  {featured.title}
                </h2>

                {/* Excerpt */}
                <p
                  style={{
                    fontSize: "1rem",
                    color: "rgba(255,255,255,0.58)",
                    lineHeight: 1.8,
                    marginBottom: 38,
                    fontWeight: 300,
                  }}
                >
                  {featured.excerpt}
                </p>

                {/* Author + CTA */}
                <div
                  style={{
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "space-between",
                    gap: 20,
                  }}
                >
                  <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
                    <div
                      style={{
                        width: 42,
                        height: 42,
                        borderRadius: "50%",
                        background: "linear-gradient(135deg, #f3c623, #d49f10)",
                        color: "#060608",
                        display: "flex",
                        alignItems: "center",
                        justifyContent: "center",
                        fontFamily: "'Clash Display', sans-serif",
                        fontSize: "1rem",
                        fontWeight: 700,
                      }}
                    >
                      {featured.author[0]}
                    </div>
                    <div>
                      <div
                        style={{
                          fontSize: "0.9rem",
                          fontWeight: 600,
                          color: "#fff",
                        }}
                      >
                        {featured.author}
                      </div>
                      <div
                        style={{
                          fontSize: "0.78rem",
                          color: "rgba(255,255,255,0.35)",
                          marginTop: 2,
                        }}
                      >
                        {featured.date}
                      </div>
                    </div>
                  </div>

                  <button
                    style={{
                      display: "inline-flex",
                      alignItems: "center",
                      gap: 8,
                      padding: "13px 24px",
                      borderRadius: 999,
                      background: "linear-gradient(135deg, #f3c623, #d49f10)",
                      color: "#060608",
                      fontFamily: "'Syne', sans-serif",
                      fontSize: "0.88rem",
                      fontWeight: 800,
                      letterSpacing: "0.03em",
                      border: "none",
                      cursor: "pointer",
                      boxShadow: "0 8px 28px rgba(243,198,35,0.32)",
                      transition:
                        "transform 0.3s cubic-bezier(0.34,1.56,0.64,1), box-shadow 0.3s ease",
                    }}
                    onMouseEnter={(e) => {
                      const el = e.currentTarget as HTMLElement;
                      el.style.transform = "translateY(-2px) scale(1.04)";
                      el.style.boxShadow = "0 14px 36px rgba(243,198,35,0.42)";
                    }}
                    onMouseLeave={(e) => {
                      const el = e.currentTarget as HTMLElement;
                      el.style.transform = "none";
                      el.style.boxShadow = "0 8px 28px rgba(243,198,35,0.32)";
                    }}
                  >
                    Read Story
                    <ArrowRight size={15} />
                  </button>
                </div>
              </div>
            </div>
          </div>
        </motion.div>
      </section>

      {/* ════════════════════════════════
          POSTS GRID
      ════════════════════════════════ */}
      <section
        style={{
          position: "relative",
          zIndex: 2,
          maxWidth: 1280,
          margin: "0 auto",
          padding: "0 48px 100px",
        }}
      >
        {/* Header */}
        <div
          style={{
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
            marginBottom: 32,
          }}
        >
          <h2
            style={{
              fontFamily: "'Clash Display', sans-serif",
              fontSize: "2.1rem",
              fontWeight: 700,
              letterSpacing: "-0.02em",
              color: "#fff",
            }}
          >
            Latest Articles
          </h2>
          <span
            style={{
              fontSize: "0.82rem",
              color: "rgba(255,255,255,0.32)",
              fontFamily: "'Syne', sans-serif",
              fontWeight: 600,
              padding: "6px 14px",
              borderRadius: 999,
              border: "1px solid rgba(255,255,255,0.07)",
              background: "rgba(255,255,255,0.02)",
            }}
          >
            {filteredPosts.length} articles
          </span>
        </div>

        {/* Grid */}
        {viewMode === "grid" ? (
          <div
            className="posts-grid"
            style={{
              display: "grid",
              gridTemplateColumns: "repeat(3, 1fr)",
              gap: 24,
            }}
          >
            {filteredPosts.map((post, i) => (
              <PostCard
                key={post.id}
                post={post}
                wide={i === 0 || i === 3}
                delay={i * 0.07}
              />
            ))}
          </div>
        ) : (
          <div
            className="list-view"
            style={{ display: "flex", flexDirection: "column", gap: 14 }}
          >
            {filteredPosts.map((post, i) => (
              <motion.div
                key={post.id}
                initial={{ opacity: 0, x: -30 }}
                whileInView={{ opacity: 1, x: 0 }}
                viewport={{ once: true }}
                transition={{ duration: 0.5, delay: i * 0.06 }}
              >
                <div
                  className="glass-card"
                  style={{ display: "flex", flexDirection: "row" }}
                >
                  <div className="hud-tl" />
                  <div className="hud-br" />
                  {/* Image */}
                  <div
                    className="pc-img-wrap"
                    style={{
                      width: 240,
                      flexShrink: 0,
                      borderRadius: "24px 0 0 24px",
                      minHeight: 160,
                    }}
                  >
                    <img src={post.image} alt={post.title} />
                    <div
                      style={{
                        position: "absolute",
                        inset: 0,
                        background:
                          "linear-gradient(to right, rgba(6,6,8,0) 70%, rgba(6,6,8,0.3) 100%)",
                        zIndex: 1,
                      }}
                    />
                    <span
                      style={{
                        position: "absolute",
                        top: 14,
                        left: 14,
                        zIndex: 3,
                        padding: "4px 10px",
                        borderRadius: 999,
                        background: "rgba(243,198,35,0.14)",
                        border: "1px solid rgba(243,198,35,0.24)",
                        color: "#f3c623",
                        fontFamily: "'Syne', sans-serif",
                        fontSize: 9,
                        fontWeight: 800,
                        letterSpacing: "0.12em",
                        textTransform: "uppercase",
                        backdropFilter: "blur(8px)",
                      }}
                    >
                      {post.category}
                    </span>
                  </div>
                  {/* Content */}
                  <div style={{ padding: "24px 28px", display: "flex", flexDirection: "column", justifyContent: "center", flex: 1 }}>
                    <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 10 }}>
                      <span style={{ fontSize: "0.8rem", color: "rgba(255,255,255,0.45)", fontWeight: 600 }}>{post.author}</span>
                      <span style={{ color: "rgba(255,255,255,0.2)" }}>·</span>
                      <span style={{ fontSize: "0.77rem", color: "rgba(255,255,255,0.3)" }}>{post.date}</span>
                      <span style={{ display: "flex", alignItems: "center", gap: 4, fontSize: "0.77rem", color: "rgba(255,255,255,0.3)", marginLeft: "auto" }}>
                        <Clock size={11} /> {post.readTime} min
                      </span>
                    </div>
                    <h3 style={{ fontFamily: "'Clash Display', sans-serif", fontSize: "1.2rem", fontWeight: 700, letterSpacing: "-0.01em", color: "#fff", marginBottom: 8, lineHeight: 1.28 }}>{post.title}</h3>
                    <p style={{ fontSize: "0.86rem", color: "rgba(255,255,255,0.4)", lineHeight: 1.7, fontWeight: 300, display: "-webkit-box", WebkitLineClamp: 2, WebkitBoxOrient: "vertical" as const, overflow: "hidden" }}>{post.excerpt}</p>
                    <button
                      style={{ display: "inline-flex", alignItems: "center", gap: 6, color: "#f3c623", fontFamily: "'Syne', sans-serif", fontSize: "0.82rem", fontWeight: 700, background: "none", border: "none", cursor: "pointer", letterSpacing: "0.04em", padding: 0, marginTop: 14, width: "fit-content", transition: "gap 0.25s" }}
                      onMouseEnter={e => { (e.currentTarget as HTMLElement).style.gap = "12px"; }}
                      onMouseLeave={e => { (e.currentTarget as HTMLElement).style.gap = "6px"; }}
                    >
                      Read Article <ArrowRight size={13} />
                    </button>
                  </div>
                </div>
              </motion.div>
            ))}
          </div>
        )}
      </section>

      {/* ════════════════════════════════
          NEWSLETTER
      ════════════════════════════════ */}
      <section
        style={{
          position: "relative",
          zIndex: 2,
          maxWidth: 1280,
          margin: "0 auto",
          padding: "0 48px 120px",
        }}
      >
        <motion.div
          initial={{ opacity: 0, y: 50 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true, margin: "-80px" }}
          transition={{ duration: 0.8, ease: [0.25, 0.46, 0.45, 0.94] }}
        >
          <div
            style={{
              position: "relative",
              padding: "80px 64px",
              borderRadius: 32,
              background: "rgba(255,255,255,0.025)",
              backdropFilter: "blur(32px)",
              border: "1px solid rgba(255,255,255,0.07)",
              overflow: "hidden",
              textAlign: "center",
            }}
          >
            {/* Background glows */}
            <div
              style={{
                position: "absolute",
                width: 500,
                height: 500,
                borderRadius: "50%",
                background: "rgba(243,198,35,0.1)",
                filter: "blur(80px)",
                top: -150,
                left: -100,
                pointerEvents: "none",
              }}
            />
            <div
              style={{
                position: "absolute",
                width: 400,
                height: 400,
                borderRadius: "50%",
                background: "rgba(120,80,255,0.07)",
                filter: "blur(80px)",
                bottom: -100,
                right: -60,
                pointerEvents: "none",
              }}
            />
            {/* Shimmer */}
            <div className="holo-shimmer" />

            {/* HUD corners */}
            <div className="hud-tl" style={{ opacity: 0.5 }} />
            <div className="hud-tr" style={{ opacity: 0.5 }} />
            <div className="hud-bl" style={{ opacity: 0.5 }} />
            <div className="hud-br" style={{ opacity: 0.5 }} />

            <div style={{ position: "relative", zIndex: 1 }}>
              {/* Badge */}
              <div
                style={{
                  display: "inline-flex",
                  alignItems: "center",
                  gap: 7,
                  padding: "7px 16px",
                  borderRadius: 999,
                  background: "rgba(243,198,35,0.1)",
                  border: "1px solid rgba(243,198,35,0.22)",
                  color: "#f3c623",
                  fontFamily: "'Syne', sans-serif",
                  fontSize: 11,
                  fontWeight: 700,
                  letterSpacing: "0.12em",
                  textTransform: "uppercase",
                  marginBottom: 28,
                }}
              >
                <ChevronRight size={11} />
                Weekly Digest
              </div>

              {/* Title */}
              <h2
                style={{
                  fontFamily: "'Clash Display', sans-serif",
                  fontSize: "clamp(2rem, 4vw, 3.6rem)",
                  fontWeight: 700,
                  letterSpacing: "-0.02em",
                  color: "#fff",
                  marginBottom: 16,
                }}
              >
                Never miss an insight.
              </h2>

              {/* Subtitle */}
              <p
                style={{
                  color: "rgba(255,255,255,0.55)",
                  fontSize: "1rem",
                  lineHeight: 1.72,
                  marginBottom: 40,
                  fontWeight: 300,
                  maxWidth: 440,
                  margin: "0 auto 40px",
                }}
              >
                Get the best ideas, delivered every Tuesday — no noise, all
                signal.
              </p>

              {/* Form */}
              {subscribed ? (
                <motion.div
                  initial={{ opacity: 0, scale: 0.9 }}
                  animate={{ opacity: 1, scale: 1 }}
                  style={{
                    display: "inline-flex",
                    alignItems: "center",
                    gap: 10,
                    padding: "14px 28px",
                    borderRadius: 999,
                    background: "rgba(243,198,35,0.12)",
                    border: "1px solid rgba(243,198,35,0.28)",
                    color: "#f3c623",
                    fontFamily: "'Syne', sans-serif",
                    fontWeight: 700,
                    fontSize: "0.95rem",
                  }}
                >
                  <span
                    style={{
                      width: 8,
                      height: 8,
                      borderRadius: "50%",
                      background: "#f3c623",
                    }}
                  />
                  You're in. See you Tuesday.
                </motion.div>
              ) : (
                <div
                  className="nl-form-row"
                  style={{
                    display: "flex",
                    alignItems: "center",
                    gap: 12,
                    maxWidth: 480,
                    margin: "0 auto 16px",
                  }}
                >
                  <input
                    className="nl-input"
                    type="email"
                    placeholder="your@email.com"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    onKeyDown={(e) => {
                      if (e.key === "Enter" && email) setSubscribed(true);
                    }}
                  />
                  <button
                    onClick={() => email && setSubscribed(true)}
                    style={{
                      padding: "14px 26px",
                      borderRadius: 999,
                      border: "none",
                      background: "linear-gradient(135deg, #f3c623, #d49f10)",
                      color: "#060608",
                      fontFamily: "'Syne', sans-serif",
                      fontSize: "0.9rem",
                      fontWeight: 800,
                      cursor: "pointer",
                      whiteSpace: "nowrap",
                      boxShadow: "0 8px 28px rgba(243,198,35,0.32)",
                      transition:
                        "transform 0.3s cubic-bezier(0.34,1.56,0.64,1), box-shadow 0.3s ease",
                    }}
                    onMouseEnter={(e) => {
                      const el = e.currentTarget as HTMLElement;
                      el.style.transform = "translateY(-2px) scale(1.04)";
                      el.style.boxShadow = "0 16px 40px rgba(243,198,35,0.42)";
                    }}
                    onMouseLeave={(e) => {
                      const el = e.currentTarget as HTMLElement;
                      el.style.transform = "none";
                      el.style.boxShadow = "0 8px 28px rgba(243,198,35,0.32)";
                    }}
                  >
                    Subscribe
                  </button>
                </div>
              )}

              <p
                style={{
                  fontSize: "0.76rem",
                  color: "rgba(255,255,255,0.28)",
                  fontWeight: 300,
                  marginTop: subscribed ? 16 : 0,
                }}
              >
                No spam. Unsubscribe any time.
              </p>
            </div>
          </div>
        </motion.div>
      </section>
    </div>
  );
}
