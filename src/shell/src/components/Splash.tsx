import { useState, useEffect } from "react";

interface SplashProps {
  onComplete: () => void;
}

export default function Splash({ onComplete }: SplashProps) {
  const [progress, setProgress] = useState(0);

  useEffect(() => {
    const duration = 3000; // 3 seconds
    const interval = 50; // Update every 50ms
    const steps = duration / interval;

    let currentStep = 0;
    const timer = setInterval(() => {
      currentStep++;
      setProgress((currentStep / steps) * 100);

      if (currentStep >= steps) {
        clearInterval(timer);
        onComplete();
      }
    }, interval);

    return () => clearInterval(timer);
  }, [onComplete]);

  return (
    <div className="splash">
      <div className="splash-content">
        <img
          src="/src/assets/images/logo-with-text.jpg"
          alt="Lucy OS Logo"
          className="logo"
        />
        <h1 className="tagline">Lucy OS v0.2.0</h1>
        <p className="subtitle">Rooted in Origins, Powered by AI</p>
        <div className="loading-bar">
          <div className="loading-fill" style={{ width: `${progress}%` }} />
        </div>
        <p className="loading-text">Initializing...</p>
      </div>

      <style>{`
        .splash {
          position: fixed;
          top: 0;
          left: 0;
          width: 100%;
          height: 100%;
          background: linear-gradient(135deg, #1a1a2e 0%, #16213e 50%, #0f3460 100%);
          display: flex;
          justify-content: center;
          align-items: center;
          z-index: 9999;
        }

        .splash-content {
          text-align: center;
          color: #e0e0e0;
        }

        .logo {
          width: 200px;
          height: auto;
          margin-bottom: 2rem;
          animation: fadeIn 1s ease-in;
        }

        .tagline {
          font-size: 2.5rem;
          font-weight: bold;
          margin: 0 0 0.5rem 0;
          background: linear-gradient(90deg, #6366f1, #a855f7);
          -webkit-background-clip: text;
          -webkit-text-fill-color: transparent;
          background-clip: text;
          animation: slideUp 0.8s ease-out;
        }

        .subtitle {
          font-size: 1.2rem;
          color: #a0a0a0;
          margin: 0 0 2rem 0;
          animation: slideUp 0.8s ease-out 0.2s backwards;
        }

        .loading-bar {
          width: 300px;
          height: 4px;
          background: #2d2d2d;
          border-radius: 2px;
          overflow: hidden;
          margin: 0 auto 1rem auto;
          animation: fadeIn 0.5s ease-out 0.4s backwards;
        }

        .loading-fill {
          height: 100%;
          background: linear-gradient(90deg, #6366f1, #a855f7);
          transition: width 0.05s linear;
        }

        .loading-text {
          font-size: 0.9rem;
          color: #666;
          margin: 0;
          animation: fadeIn 0.5s ease-out 0.5s backwards;
        }

        @keyframes fadeIn {
          from {
            opacity: 0;
          }
          to {
            opacity: 1;
          }
        }

        @keyframes slideUp {
          from {
            opacity: 0;
            transform: translateY(20px);
          }
          to {
            opacity: 1;
            transform: translateY(0);
          }
        }
      `}</style>
    </div>
  );
}
