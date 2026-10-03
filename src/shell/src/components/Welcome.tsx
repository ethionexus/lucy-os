import { useState, useRef, useEffect } from "react";

interface WelcomeProps {
  onComplete: () => void;
}

// The lucy-intro media asset, served from public/media/.
const INTRO_VIDEO = "/media/lucy-intro.mp4";

// Glassmorphism slides showcasing Dinknesh (Lucy) history, mirroring the
// obsidian/gold Calamares installer slideshow. Shown automatically when the
// lucy-intro media asset is not available (e.g. before the video is added).
const SLIDES = [
  {
    kicker: "1974 · Hadar, Ethiopia",
    title: "Dinknesh",
    amharic: "ድንቅነሽ",
    body: "A 3.2-million-year-old Australopithecus afarensis skeleton — the most complete early hominin fossil ever found, illuminating the origins of humankind.",
  },
  {
    kicker: "The Name",
    title: "Lucy",
    amharic: "",
    body: "Named for the Beatles' \"Lucy in the Sky with Diamonds\", played at camp the night of her discovery. She became a global icon of human origins.",
  },
  {
    kicker: "Rooted in Origins",
    title: "Lucy OS",
    amharic: "",
    body: "Like Dinknesh revealed our past, Lucy OS illuminates your workflow — an AI-native desktop, rooted in openness and powered by offline intelligence.",
  },
];

export default function Welcome({ onComplete }: WelcomeProps) {
  const [mode, setMode] = useState<"loading" | "video" | "slides">("loading");
  const [slide, setSlide] = useState(0);
  const videoRef = useRef<HTMLVideoElement>(null);

  // Advance the glassmorphism slideshow when the media asset is unavailable.
  useEffect(() => {
    if (mode !== "slides") return;
    const t = setInterval(() => setSlide((s) => (s + 1) % SLIDES.length), 5000);
    return () => clearInterval(t);
  }, [mode]);

  const finish = () => {
    try {
      localStorage.setItem("lucy.welcomed", "1");
    } catch {
      /* storage unavailable — non-fatal */
    }
    onComplete();
  };

  return (
    <div className="welcome" role="dialog" aria-label="Lucy OS Welcome">
      {/* Background media: lucy-intro, or an obsidian gradient. */}
      <video
        ref={videoRef}
        className={mode === "video" ? "welcome-video show" : "welcome-video"}
        src={INTRO_VIDEO}
        autoPlay
        muted
        playsInline
        onCanPlay={() => setMode("video")}
        onError={() => setMode("slides")}
        onEnded={finish}
      />

      {/* Smooth glassmorphism overlay */}
      <div className="welcome-glass">
        {mode === "loading" && <p className="welcome-loading">Loading…</p>}

        {mode === "video" && (
          <div className="welcome-slide">
            <p className="welcome-kicker">Welcome to</p>
            <h1 className="welcome-title">Lucy OS</h1>
            <p className="welcome-body">Rooted in Origins, Powered by AI</p>
          </div>
        )}

        {mode === "slides" && (
          <div className="welcome-slide" key={slide}>
            <p className="welcome-kicker">{SLIDES[slide].kicker}</p>
            <h1 className="welcome-title">
              {SLIDES[slide].title}
              {SLIDES[slide].amharic && (
                <span className="welcome-amharic"> {SLIDES[slide].amharic}</span>
              )}
            </h1>
            <p className="welcome-body">{SLIDES[slide].body}</p>
            <div className="welcome-dots">
              {SLIDES.map((_, i) => (
                <span key={i} className={i === slide ? "dot active" : "dot"} />
              ))}
            </div>
          </div>
        )}

        <div className="welcome-actions">
          <button type="button" className="glass-btn ghost" onClick={finish}>
            Skip
          </button>
          <button type="button" className="glass-btn" onClick={finish}>
            Get Started
          </button>
        </div>
      </div>

      <style>{`
        .welcome {
          position: fixed;
          inset: 0;
          z-index: 10000;
          overflow: hidden;
          background: radial-gradient(ellipse at 50% 40%, #1c1712 0%, #0b0a08 70%);
        }
        .welcome-video {
          position: absolute;
          inset: 0;
          width: 100%;
          height: 100%;
          object-fit: cover;
          opacity: 0;
          transition: opacity 1.2s ease;
        }
        .welcome-video.show { opacity: 0.5; }
        .welcome-glass {
          position: relative;
          z-index: 2;
          min-height: 100vh;
          display: flex;
          flex-direction: column;
          align-items: center;
          justify-content: center;
          padding: 2rem;
          background: linear-gradient(180deg, rgba(11,10,8,0.15) 0%, rgba(11,10,8,0.72) 100%);
          backdrop-filter: blur(16px) saturate(150%);
          -webkit-backdrop-filter: blur(16px) saturate(150%);
        }
        .welcome-slide {
          max-width: 46rem;
          text-align: center;
          padding: 2.75rem 3rem;
          border-radius: 1.5rem;
          background: rgba(255,255,255,0.06);
          border: 1px solid rgba(212,175,55,0.28);
          box-shadow: 0 10px 40px rgba(0,0,0,0.5), inset 0 1px 0 rgba(255,255,255,0.09);
          backdrop-filter: blur(20px) saturate(170%);
          -webkit-backdrop-filter: blur(20px) saturate(170%);
          animation: slideUp 0.7s ease both;
        }
        @keyframes slideUp {
          from { opacity: 0; transform: translateY(26px); }
          to { opacity: 1; transform: translateY(0); }
        }
        .welcome-kicker {
          text-transform: uppercase;
          letter-spacing: 0.32em;
          font-size: 0.78rem;
          color: #d4af37;
          margin: 0 0 0.8rem;
        }
        .welcome-title {
          font-size: 3rem;
          font-weight: 700;
          margin: 0 0 1rem;
          background: linear-gradient(135deg, #f7e8c3 0%, #d4af37 55%, #b8860b 100%);
          -webkit-background-clip: text;
          background-clip: text;
          color: transparent;
        }
        .welcome-amharic {
          font-size: 1.6rem;
          vertical-align: middle;
        }
        .welcome-body {
          color: rgba(255,255,255,0.84);
          line-height: 1.75;
          font-size: 1.04rem;
          margin: 0;
        }
        .welcome-dots {
          display: flex;
          gap: 0.5rem;
          justify-content: center;
          margin-top: 1.5rem;
        }
        .dot {
          width: 8px;
          height: 8px;
          border-radius: 50%;
          background: rgba(255,255,255,0.22);
          transition: background 0.3s;
        }
        .dot.active { background: #d4af37; }
        .welcome-actions {
          display: flex;
          gap: 1rem;
          margin-top: 2.5rem;
        }
        .glass-btn {
          padding: 0.7rem 1.7rem;
          border-radius: 999px;
          border: 1px solid rgba(212,175,55,0.5);
          background: rgba(212,175,55,0.18);
          color: #f7e8c3;
          font-size: 1rem;
          cursor: pointer;
          backdrop-filter: blur(8px);
          -webkit-backdrop-filter: blur(8px);
          transition: background 0.2s, transform 0.15s;
        }
        .glass-btn:hover { background: rgba(212,175,55,0.34); transform: translateY(-1px); }
        .glass-btn.ghost {
          background: rgba(255,255,255,0.06);
          border-color: rgba(255,255,255,0.2);
          color: rgba(255,255,255,0.86);
        }
        .glass-btn.ghost:hover { background: rgba(255,255,255,0.13); }
        .welcome-loading { color: rgba(255,255,255,0.45); }
      `}</style>
    </div>
  );
}
