import React from 'react';
import {
  AbsoluteFill,
  Easing,
  interpolate,
  spring,
  useCurrentFrame,
  useVideoConfig,
} from 'remotion';

export type Segment = {
  start: number;
  end: number;
  kind: 'timeline' | 'scan' | 'resection' | 'quote' | 'points';
  title?: string;
  sub?: string;
  quote?: string;
  labels?: string[];
  marker?: string;
  points?: string[];
  lines?: {text: string; color?: 'gold' | 'white'; at?: number}[];
  footer?: string;
};

export type OverlayProps = {
  fps: number;
  durationInFrames: number;
  width: number;
  height: number;
  gold: string;
  goldLight: string;
  segments: Segment[];
};

const FONT = '"Microsoft YaHei","PingFang SC","Noto Sans CJK SC",sans-serif';
const SHADOW = '2px 3px 0 rgba(0,0,0,0.9), 0 0 18px rgba(0,0,0,0.35)';

type Common = {
  seg: Segment;
  p: number;
  local: number;
  fps: number;
  dur: number;
  gold: string;
  goldLight: string;
};

const Rise: React.FC<{
  frame: number;
  fps: number;
  delay?: number;
  y?: number;
  children: React.ReactNode;
  style?: React.CSSProperties;
}> = ({frame, fps, delay = 0, y = 28, children, style}) => {
  const s = spring({frame: frame - delay, fps, config: {damping: 21, stiffness: 92, mass: 0.9}});
  return (
    <div style={{opacity: s, transform: `translateY(${(1 - s) * y}px)`, ...style}}>
      {children}
    </div>
  );
};

const float = (frame: number, amp = 3) => Math.sin(frame / 22) * amp;

const Timeline: React.FC<Common> = ({seg, p, local, gold}) => {
    const labels = seg.labels ?? ['0 年', '5 年', '10 年'];
    const r = 8 + 30 * p;
    const pink = Math.round(176 - 104 * p);
    return (
      <div style={{position: 'absolute', top: 320, width: '100%'}}>
        <svg viewBox="0 0 720 200" width="100%" height="200" style={{overflow: 'visible'}}>
          <defs>
            <linearGradient id="gut" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor="#f7d0d0" />
              <stop offset="100%" stopColor="#e79b9b" />
            </linearGradient>
            <radialGradient id="polyp">
              <stop offset="0%" stopColor="#f4a6a6" />
              <stop offset="100%" stopColor="#c44c4c" />
            </radialGradient>
          </defs>
          <g style={{filter: 'drop-shadow(0 10px 18px rgba(0,0,0,0.28))', transform: `translateY(${float(local)}px)`}}>
            <rect x="120" y="30" width="500" height="150" rx="75" fill="url(#gut)"
              stroke="rgba(255,235,235,0.95)" strokeWidth="4" />
            <path d="M170 108 Q370 42 570 108" fill="none" stroke="rgba(198,110,110,0.55)" strokeWidth="5" />
            <circle cx="370" cy="105" r={r} fill="url(#polyp)"
              stroke="rgba(255,240,240,0.95)" strokeWidth="3" />
          </g>
        </svg>
        <div style={{position: 'absolute', top: 260, left: 110, width: 500, height: 7,
          background: 'rgba(255,255,255,0.35)', borderRadius: 4}} />
        <div style={{position: 'absolute', top: 260, left: 110, width: 500 * p, height: 7,
          background: gold, borderRadius: 4, boxShadow: `0 0 14px ${gold}66`}} />
        {[110, 360, 610].map((x, i) => {
          const on = p >= [0, 0.5, 0.97][i];
          return (
            <div key={i}>
              <div style={{position: 'absolute', top: 252, left: x - 10, width: 22, height: 22,
                borderRadius: 11, background: on ? gold : 'rgba(150,160,172,0.9)',
                boxShadow: on ? `0 0 16px ${gold}` : 'none'}} />
              <div style={{position: 'absolute', top: 286, left: x - 45, width: 90,
                textAlign: 'center', fontSize: 24, color: on ? gold : 'rgba(200,208,216,0.8)',
                textShadow: SHADOW}}>{labels[i] ?? ''}</div>
            </div>
          );
        })}
      </div>
    );
  };

const Scan: React.FC<Common> = ({seg, p, local, fps, gold}) => {
    const sx = -110 + 220 * p;
    const sy = -40 + 30 * Math.sin(p * Math.PI);
    const mk = interpolate(p, [0.45, 0.7], [0, 1], {
      extrapolateLeft: 'clamp', extrapolateRight: 'clamp',
      easing: Easing.out(Easing.cubic),
    });
    return (
      <div style={{position: 'absolute', top: 300, width: '100%', display: 'flex',
        justifyContent: 'center'}}>
        <div style={{width: 350, height: 350, borderRadius: '50%', position: 'relative',
          background: 'radial-gradient(circle at 42% 38%, #d98086 0%, #a84a55 62%, #7d2f3a 100%)',
          border: '6px solid rgba(255,226,226,0.95)',
          boxShadow: '0 18px 44px rgba(0,0,0,0.4), inset 0 0 46px rgba(0,0,0,0.35)',
          transform: `translateY(${float(local, 4)}px)`}}>
          {[0, 1, 2, 3, 4].map((i) => (
            <div key={i} style={{position: 'absolute',
              left: 18 + i * 12, top: 18 + i * 12,
              right: 18 + i * 12, bottom: 18 + i * 12,
              borderRadius: '50%', border: '5px solid transparent',
              borderTopColor: 'rgba(240,170,170,0.28)',
              transform: `rotate(${i * 40}deg)`}} />
          ))}
          <div style={{position: 'absolute', left: 175 + sx - 28, top: 175 + sy - 28,
            width: 56, height: 56, borderRadius: '50%',
            background: 'radial-gradient(circle, rgba(255,252,230,0.95) 0%, rgba(255,245,200,0.18) 70%)',
            boxShadow: '0 0 30px rgba(255,246,210,0.75)'}} />
          <div style={{position: 'absolute', left: 215, top: 145, width: 56, height: 56,
            borderRadius: '50%', background: `rgba(240,92,92,${mk})`,
            border: `3px solid rgba(255,255,255,${mk})`, boxShadow: '0 0 22px rgba(240,92,92,0.6)'}} />
        </div>
        {seg.marker ? (
          <Rise frame={local} fps={fps} delay={Math.round(0.45 * 30)} y={16}
            style={{position: 'absolute', top: 40, left: 470, fontSize: 26,
              color: gold, textShadow: SHADOW, whiteSpace: 'nowrap'}}>
            {seg.marker}
          </Rise>
        ) : null}
      </div>
    );
  };

const Resection: React.FC<Common> = ({seg, p, local, fps, goldLight}) => {
    const half = 62 - 34 * interpolate(p, [0, 0.6], [0, 1], {
      extrapolateRight: 'clamp', easing: Easing.out(Easing.cubic),
    });
    const removed = p > 0.62;
    const pts = seg.points ?? [];
    return (
      <div style={{position: 'absolute', top: 300, width: '100%'}}>
        <svg viewBox="0 0 720 160" width="100%" height="160" style={{overflow: 'visible'}}>
          <defs>
            <linearGradient id="wall" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor="#f6cccc" />
              <stop offset="100%" stopColor="#e79b9b" />
            </linearGradient>
          </defs>
          <rect x="110" y="10" width="530" height="52" rx="24" fill="url(#wall)"
            style={{filter: 'drop-shadow(0 8px 16px rgba(0,0,0,0.3))'}} />
          {!removed ? (
            <circle cx="360" cy="10" r="34" fill="#d65858" stroke="rgba(255,220,220,0.95)" strokeWidth="3" />
          ) : (
            <path d="M330 18 Q360 34 390 18" fill="none" stroke="#c86e6e" strokeWidth="4" />
          )}
          <path d={`M${360 - half} -20 A ${half} ${half * 0.7} 0 0 1 ${360 + half} -20`}
            fill="none" stroke="rgba(235,240,245,0.95)" strokeWidth="6"
            transform="translate(0, 30)" />
          <line x1="360" y1={30 - half * 0.7} x2="360" y2="0" stroke="rgba(235,240,245,0.95)" strokeWidth="6" />
        </svg>
        <div style={{position: 'absolute', top: 150, width: '100%'}}>
          {pts.slice(0, 4).map((s, i) => (
            <Rise key={i} frame={local} fps={fps} delay={6 + i * 8} y={20}
              style={{margin: '0 auto 12px', width: 525, padding: '12px 0', borderRadius: 12,
                background: 'rgba(12,30,52,0.82)', textAlign: 'center', fontSize: 31,
                color: i === pts.length - 1 && pts.length > 1 ? goldLight : '#fff',
                textShadow: SHADOW}}>
              {s}
            </Rise>
          ))}
        </div>
      </div>
    );
  };

const Quote: React.FC<Common> = ({seg, local, fps, dur, goldLight}) => {
    const rows = seg.lines ?? [];
    return (
      <div style={{position: 'absolute', top: 280, width: '100%'}}>
        {rows.slice(0, 5).map((row, i) => {
          const delay = Math.round((row.at ?? 0.05 + i * 0.18) * dur);
          const s = spring({frame: local - delay, fps, config: {damping: 20, stiffness: 88, mass: 0.9}});
          const scale = 0.94 + 0.06 * s;
          return (
            <div key={i} style={{marginTop: i === 0 ? 0 : 28, textAlign: 'center',
              fontSize: 41, fontWeight: 800,
              color: row.color === 'gold' ? goldLight : '#fff',
              textShadow: SHADOW, opacity: s,
              transform: `translateY(${(1 - s) * 22}px) scale(${scale})`}}>
              {row.text}
            </div>
          );
        })}
        {seg.footer ? (
          <Rise frame={local} fps={fps} delay={Math.round(0.5 * 30)}
            style={{textAlign: 'center', marginTop: 90, fontSize: 34, color: '#e2eaf0', textShadow: SHADOW}}>
            {seg.footer}
          </Rise>
        ) : null}
      </div>
    );
  };

const Points: React.FC<Common> = ({seg, local, fps, goldLight}) => (<>
  {(seg.points ?? []).slice(0, 5).map((s, i) => (
    <Rise key={i} frame={local} fps={fps} delay={4 + i * 8} y={22}
      style={{position: 'absolute', top: 380 + i * 84, left: 105, width: 525,
        padding: '12px 0', borderRadius: 12, background: 'rgba(12,30,52,0.82)',
        textAlign: 'center', fontSize: 31,
        color: i === (seg.points ?? []).length - 1 ? goldLight : '#fff',
        textShadow: SHADOW}}>
      {s}
    </Rise>
  ))}
</>);

export const Overlay: React.FC<OverlayProps> = (props) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  const t = frame / fps;
  const seg = props.segments.find((s) => t >= s.start && t < s.end);
  if (!seg) {
    return <AbsoluteFill style={{backgroundColor: 'transparent'}} />;
  }
  const local = frame - Math.round(seg.start * fps);
  const dur = Math.max(1, (seg.end - seg.start) * fps);
  const p = interpolate(local, [0, dur], [0, 1], {
    extrapolateLeft: 'clamp', extrapolateRight: 'clamp',
    easing: Easing.bezier(0.22, 1, 0.36, 1),
  });
  const enter = spring({frame: local, fps, config: {damping: 24, stiffness: 76, mass: 1}});
  const out = interpolate(local, [dur - 10, dur], [1, 0], {
    extrapolateLeft: 'clamp', extrapolateRight: 'clamp',
  });
  const alpha = Math.min(enter, out);
  const common: Common = {
    seg, p, local, fps, dur,
    gold: props.gold, goldLight: props.goldLight,
  };

  return (
    <AbsoluteFill style={{backgroundColor: 'transparent', fontFamily: FONT, opacity: alpha}}>
      {seg.title ? (
        <Rise frame={local} fps={fps} y={18}
          style={{position: 'absolute', top: 128, width: '100%', textAlign: 'center',
            fontSize: 52, fontWeight: 800, color: props.gold, textShadow: SHADOW}}>
          {seg.title}
        </Rise>
      ) : null}
      {seg.sub ? (
        <Rise frame={local} fps={fps} delay={4}
          style={{position: 'absolute', top: 210, width: '100%', textAlign: 'center',
            fontSize: 28, fontWeight: 700, color: '#e2eaf0', textShadow: SHADOW}}>
          {seg.sub}
        </Rise>
      ) : null}
      {seg.kind === 'timeline' ? <Timeline {...common} /> : null}
      {seg.kind === 'scan' ? <Scan {...common} /> : null}
      {seg.kind === 'resection' ? <Resection {...common} /> : null}
      {seg.kind === 'quote' ? <Quote {...common} /> : null}
      {seg.kind === 'points' ? <Points {...common} /> : null}
      {seg.quote && seg.kind !== 'quote' ? (
        <Rise frame={local} fps={fps} delay={10}
          style={{position: 'absolute', top: 690, width: '100%', textAlign: 'center',
            fontSize: 38, fontWeight: 800, color: props.goldLight, textShadow: SHADOW}}>
          {seg.quote}
        </Rise>
      ) : null}
    </AbsoluteFill>
  );
};
