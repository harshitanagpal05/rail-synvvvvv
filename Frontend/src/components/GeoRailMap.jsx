import React, { useState, useEffect } from 'react';
import LocoCockpitModal from './LocoCockpitModal';
import { playAlarmSound } from '../utils/audio';

// Exact Indian Railway Division Coordinates (Lat, Long)
const STATIONS = {
  Delhi: { lat: 28.6139, lon: 77.2090, label: 'New Delhi (NDLS)', code: 'NDLS', zone: 'NR' },
  Jaipur: { lat: 26.9124, lon: 75.7873, label: 'Jaipur Jn (JP)', code: 'JP', zone: 'NWR' },
  Kota: { lat: 25.2138, lon: 75.8648, label: 'Kota Jn (KOTA)', code: 'KOTA', zone: 'WCR' },
  Ratlam: { lat: 23.3315, lon: 75.0367, label: 'Ratlam Jn (RTM)', code: 'RTM', zone: 'WR' },
  Vadodara: { lat: 22.3072, lon: 73.1812, label: 'Vadodara Jn (BRC)', code: 'BRC', zone: 'WR' },
  Mumbai: { lat: 19.0760, lon: 72.8777, label: 'Mumbai Central (MMCT)', code: 'BCT', zone: 'WR' },
  
  Allahabad: { lat: 25.4358, lon: 81.8463, label: 'Prayagraj Jn (PRYJ)', code: 'PRYJ', zone: 'NCR' },
  'Mughal Sarai': { lat: 25.2815, lon: 83.1186, label: 'Pt. Deen Dayal (DDU)', code: 'DDU', zone: 'ECR' },
  Dhanbad: { lat: 23.7915, lon: 86.4304, label: 'Dhanbad Jn (DHN)', code: 'DHN', zone: 'ECR' },
  Howrah: { lat: 22.5958, lon: 88.3113, label: 'Howrah Jn (HWH)', code: 'HWH', zone: 'ER' },
  
  Renigunta: { lat: 13.6366, lon: 79.5222, label: 'Renigunta Jn (RU)', code: 'RU', zone: 'SCR' },
  Guntakal: { lat: 15.1674, lon: 77.3824, label: 'Guntakal Jn (GTL)', code: 'GTL', zone: 'SCR' },
  Solapur: { lat: 17.6599, lon: 75.9064, label: 'Solapur (SUR)', code: 'SUR', zone: 'CR' },
  Pune: { lat: 18.5204, lon: 73.8567, label: 'Pune Jn (PUNE)', code: 'PUNE', zone: 'CR' },
  
  Agra: { lat: 27.1767, lon: 78.0081, label: 'Agra Cantt (AGC)', code: 'AGC', zone: 'NCR' },
  Jhansi: { lat: 25.4484, lon: 78.5685, label: 'VGL Jhansi (VGLJ)', code: 'VGLJ', zone: 'NCR' },
  Bhopal: { lat: 23.2599, lon: 77.4126, label: 'Bhopal Jn (BPL)', code: 'BPL', zone: 'WCR' },
  Nagpur: { lat: 21.1458, lon: 79.0882, label: 'Nagpur Jn (NGP)', code: 'NGP', zone: 'CR' },
  Balharshah: { lat: 19.8510, lon: 79.3510, label: 'Balharshah (BPQ)', code: 'BPQ', zone: 'CR' },
  Vijayawada: { lat: 16.5062, lon: 80.6480, label: 'Vijayawada Jn (BZA)', code: 'BZA', zone: 'SCR' },
  Chennai: { lat: 13.0827, lon: 80.2707, label: 'Chennai Central (MAS)', code: 'MAS', zone: 'SR' },
  
  Kharagpur: { lat: 22.3302, lon: 87.3237, label: 'Kharagpur Jn (KGP)', code: 'KGP', zone: 'SER' },
  Tatanagar: { lat: 22.7925, lon: 86.1843, label: 'Tatanagar Jn (TATA)', code: 'TATA', zone: 'SER' },
  Bilaspur: { lat: 22.0797, lon: 82.1409, label: 'Bilaspur Jn (BSP)', code: 'BSP', zone: 'SECR' },
  Raipur: { lat: 21.2514, lon: 81.6296, label: 'Raipur Jn (R)', code: 'R', zone: 'SECR' },
  Bhusaval: { lat: 21.0455, lon: 75.8011, label: 'Bhusaval Jn (BSL)', code: 'BSL', zone: 'CR' },
  Bhubaneswar: { lat: 20.2961, lon: 85.8245, label: 'Bhubaneswar (BBS)', code: 'BBS', zone: 'ECoR' },
  Visakhapatnam: { lat: 17.6868, lon: 83.2185, label: 'Visakhapatnam (VSKP)', code: 'VSKP', zone: 'ECoR' },
};

// Canvas projection bounds
const MAP_CONFIG = {
  minLon: 70.0,
  maxLon: 91.0,
  minLat: 11.0,
  maxLat: 31.0,
  width: 900,
  height: 820,
  padding: 50,
};

function project(lat, lon) {
  const { minLon, maxLon, minLat, maxLat, width, height, padding } = MAP_CONFIG;
  const x = padding + ((lon - minLon) / (maxLon - minLon)) * (width - 2 * padding);
  const y = padding + ((maxLat - lat) / (maxLat - minLat)) * (height - 2 * padding);
  return { x, y };
}

// Live Simulated Moving Trains with route waypoints
const SIMULATED_TRAINS = [
  {
    id: '12951',
    name: 'Mumbai Rajdhani',
    type: 'rajdhani',
    speed: '128 km/h',
    corridorId: 'delhi_mumbai',
    route: ['Delhi', 'Kota', 'Ratlam', 'Vadodara', 'Mumbai'],
    speedFactor: 0.04,
  },
  {
    id: '12301',
    name: 'Howrah Rajdhani',
    type: 'rajdhani',
    speed: '130 km/h',
    corridorId: 'delhi_howrah',
    route: ['Delhi', 'Allahabad', 'Mughal Sarai', 'Dhanbad', 'Howrah'],
    speedFactor: 0.035,
  },
  {
    id: '12622',
    name: 'Tamil Nadu Express',
    type: 'superfast',
    speed: '115 km/h',
    corridorId: 'delhi_chennai',
    route: ['Delhi', 'Agra', 'Jhansi', 'Bhopal', 'Nagpur', 'Vijayawada', 'Chennai'],
    speedFactor: 0.025,
  },
  {
    id: '12859',
    name: 'Gitanjali Express',
    type: 'superfast',
    speed: '110 km/h',
    corridorId: 'howrah_mumbai',
    route: ['Howrah', 'Kharagpur', 'Tatanagar', 'Bilaspur', 'Nagpur', 'Bhusaval', 'Mumbai'],
    speedFactor: 0.03,
  },
  {
    id: '12841',
    name: 'Coromandel Express',
    type: 'superfast',
    speed: '120 km/h',
    corridorId: 'howrah_chennai',
    route: ['Howrah', 'Kharagpur', 'Bhubaneswar', 'Visakhapatnam', 'Vijayawada', 'Chennai'],
    speedFactor: 0.032,
  },
  {
    id: 'BTPN-88',
    name: 'Petroleum Freight Rake',
    type: 'freight',
    speed: '65 km/h',
    corridorId: 'chennai_mumbai',
    route: ['Chennai', 'Renigunta', 'Guntakal', 'Solapur', 'Pune', 'Mumbai'],
    speedFactor: 0.015,
  },
];

export default function GeoRailMap({ networkData, onSelectStation }) {
  const [selectedStation, setSelectedStation] = useState(null);
  const [hoveredStation, setHoveredStation] = useState(null);
  const [hoveredCorridor, setHoveredCorridor] = useState(null);
  const [showTrains, setShowTrains] = useState(true);
  const [showWeather, setShowWeather] = useState(true);
  const [filterStatus, setFilterStatus] = useState('ALL');
  const [trainProgress, setTrainProgress] = useState(0);
  const [cockpitTrain, setCockpitTrain] = useState(null);

  // Animate trains along their tracks
  useEffect(() => {
    const interval = setInterval(() => {
      setTrainProgress((prev) => (prev + 0.005) % 1.0);
    }, 60);
    return () => clearInterval(interval);
  }, []);

  if (!networkData || !networkData.corridors) {
    return (
      <div className="h-96 flex items-center justify-center bg-surface-container-low rounded-2xl border border-outline-variant/30 text-on-surface-variant">
        <div className="flex flex-col items-center gap-2">
          <div className="w-8 h-8 border-2 border-primary border-t-transparent rounded-full animate-spin"></div>
          <p className="text-xs uppercase tracking-widest font-mono">Initializing National Rail GIS Engine...</p>
        </div>
      </div>
    );
  }

  // Create lookup for corridor status and weather
  const corridorMap = {};
  const divisionWeatherMap = {};
  networkData.corridors.forEach((c) => {
    corridorMap[c.id] = c;
    if (c.division_weather) {
      Object.assign(divisionWeatherMap, c.division_weather);
    }
  });

  // Calculate current animated positions of moving trains
  const getTrainPosition = (train) => {
    const waypoints = train.route.map((name) => {
      const s = STATIONS[name];
      return s ? project(s.lat, s.lon) : { x: 0, y: 0 };
    });

    if (waypoints.length < 2) return { x: 0, y: 0, angle: 0 };

    // Total route progress loop (t = 0 to 1)
    const t = (trainProgress * (train.speedFactor / 0.03)) % 1.0;
    const totalSegments = waypoints.length - 1;
    const currentSegIndex = Math.min(Math.floor(t * totalSegments), totalSegments - 1);
    const segT = (t * totalSegments) - currentSegIndex;

    const p1 = waypoints[currentSegIndex];
    const p2 = waypoints[currentSegIndex + 1];

    const x = p1.x + (p2.x - p1.x) * segT;
    const y = p1.y + (p2.y - p1.y) * segT;
    const angle = Math.atan2(p2.y - p1.y, p2.x - p1.x) * (180 / Math.PI);

    return { x, y, angle };
  };

  const getStatusColor = (status) => {
    switch (status) {
      case 'CLEAR':
        return '#10b981'; // emerald-500
      case 'AT_RISK':
        return '#f59e0b'; // amber-500
      case 'UNDER_BLOCK':
        return '#ef4444'; // red-500
      case 'LIVE_DEFECT':
        return '#f43f5e'; // rose-500
      default:
        return '#64748b'; // slate-500
    }
  };

  return (
    <div className="relative bg-surface-container-low rounded-2xl border border-outline-variant/30 overflow-hidden shadow-2xl flex flex-col">
      {/* Top HUD Controls Bar */}
      <div className="p-4 bg-surface-container/80 backdrop-blur-md border-b border-outline-variant/30 flex flex-wrap items-center justify-between gap-4 z-20">
        <div className="flex items-center gap-3">
          <div className="w-9 h-9 rounded-xl bg-primary/10 border border-primary/20 flex items-center justify-center text-primary">
            <span className="material-symbols-outlined text-lg">public</span>
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h2 className="font-bold text-on-surface text-base tracking-tight">
                National Railway Geographic Operations Map
              </h2>
              <span className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full text-[10px] font-bold bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 font-mono animate-pulse">
                <span className="w-1.5 h-1.5 rounded-full bg-emerald-400"></span>
                LIVE GIS V4.2
              </span>
            </div>
            <p className="text-xs text-on-surface-variant font-mono">
              Golden Quadrilateral & Diagonals Network · 6 Corridors · 120+ Monitored Segments
            </p>
          </div>
        </div>

        {/* Filter Controls */}
        <div className="flex items-center gap-2">
          <button
            onClick={() => setShowTrains(!showTrains)}
            className={`px-2.5 py-1.5 rounded-lg text-xs font-medium border transition-all flex items-center gap-1.5 ${
              showTrains
                ? 'bg-primary/10 text-primary border-primary/30 shadow-sm'
                : 'bg-surface text-on-surface-variant border-outline-variant/50 hover:text-on-surface'
            }`}
            title="Toggle Live Animated Trains"
          >
            <span className="material-symbols-outlined text-sm">train</span>
            Trains {showTrains ? 'ON' : 'OFF'}
          </button>

          <button
            onClick={() => setShowWeather(!showWeather)}
            className={`px-2.5 py-1.5 rounded-lg text-xs font-medium border transition-all flex items-center gap-1.5 ${
              showWeather
                ? 'bg-cyan-500/10 text-cyan-400 border-cyan-500/30 shadow-sm'
                : 'bg-surface text-on-surface-variant border-outline-variant/50 hover:text-on-surface'
            }`}
            title="Toggle Open-Meteo Weather Overlay"
          >
            <span className="material-symbols-outlined text-sm">thermostat</span>
            Weather {showWeather ? 'ON' : 'OFF'}
          </button>

          <div className="h-4 w-px bg-outline-variant/50 mx-1"></div>

          {/* Status Filter */}
          <div className="flex bg-surface rounded-lg p-0.5 border border-outline-variant/50 text-[11px] font-medium">
            {['ALL', 'BLOCKS', 'RISK'].map((st) => (
              <button
                key={st}
                onClick={() => setFilterStatus(st)}
                className={`px-2 py-1 rounded-md transition-all ${
                  filterStatus === st
                    ? 'bg-surface-container-highest text-primary font-bold shadow-xs'
                    : 'text-on-surface-variant hover:text-on-surface'
                }`}
              >
                {st}
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* Main Map Canvas Area */}
      <div className="relative w-full overflow-hidden flex justify-center items-center py-4 bg-[#0a0f18] min-h-[620px]">
        {/* SVG Decorative Grid & Radar Circles */}
        <svg
          viewBox={`0 0 ${MAP_CONFIG.width} ${MAP_CONFIG.height}`}
          className="w-full max-w-[860px] h-auto select-none"
          style={{ filter: 'drop-shadow(0 0 20px rgba(0,0,0,0.8))' }}
        >
          <defs>
            {/* Glow Filters */}
            <filter id="glow-emerald" x="-20%" y="-20%" width="140%" height="140%">
              <feGaussianBlur stdDeviation="3" result="blur" />
              <feComposite in="SourceGraphic" in2="blur" operator="over" />
            </filter>
            <filter id="glow-red" x="-30%" y="-30%" width="160%" height="160%">
              <feGaussianBlur stdDeviation="4" result="blur" />
              <feComposite in="SourceGraphic" in2="blur" operator="over" />
            </filter>
            <filter id="glow-amber" x="-20%" y="-20%" width="140%" height="140%">
              <feGaussianBlur stdDeviation="3.5" result="blur" />
              <feComposite in="SourceGraphic" in2="blur" operator="over" />
            </filter>

            {/* Block Pattern (Hazard Stripes) */}
            <pattern id="hazard-stripes" width="10" height="10" patternUnits="userSpaceOnUse" patternTransform="rotate(45)">
              <rect width="5" height="10" fill="#ef4444" fillOpacity="0.8" />
              <rect x="5" width="5" height="10" fill="#7f1d1d" fillOpacity="0.9" />
            </pattern>

            {/* Gradients */}
            <radialGradient id="center-radar" cx="50%" cy="50%" r="50%">
              <stop offset="0%" stopColor="#38bdf8" stopOpacity="0.06" />
              <stop offset="100%" stopColor="#38bdf8" stopOpacity="0" />
            </radialGradient>
          </defs>

          {/* Coordinate Grid Background */}
          <g opacity="0.08" stroke="#94a3b8" strokeWidth="1">
            {Array.from({ length: 9 }).map((_, i) => (
              <line key={`v-${i}`} x1={i * 100 + 50} y1="0" x2={i * 100 + 50} y2={MAP_CONFIG.height} />
            ))}
            {Array.from({ length: 8 }).map((_, i) => (
              <line key={`h-${i}`} x1="0" y1={i * 100 + 50} x2={MAP_CONFIG.width} y2={i * 100 + 50} />
            ))}
          </g>

          {/* Center Zero-Mile Radar Circle around Nagpur */}
          {(() => {
            const ngp = project(STATIONS.Nagpur.lat, STATIONS.Nagpur.lon);
            return (
              <g>
                <circle cx={ngp.x} cy={ngp.y} r="220" fill="url(#center-radar)" />
                <circle cx={ngp.x} cy={ngp.y} r="220" stroke="#38bdf8" strokeWidth="1" strokeDasharray="4 6" opacity="0.15" />
                <circle cx={ngp.x} cy={ngp.y} r="140" stroke="#38bdf8" strokeWidth="1" strokeDasharray="3 4" opacity="0.2" />
                <circle cx={ngp.x} cy={ngp.y} r="70" stroke="#38bdf8" strokeWidth="1" opacity="0.25" />
                <text x={ngp.x + 10} y={ngp.y - 10} fill="#38bdf8" opacity="0.3" fontSize="9" fontFamily="monospace">
                  CENTRAL RADAR: NGP ZERO-MILE
                </text>
              </g>
            );
          })()}

          {/* Corridor Track Polylines */}
          {networkData.corridors.map((c) => {
            const divs = c.divisions;
            const points = divs
              .map((name) => {
                const s = STATIONS[name];
                if (!s) return null;
                const p = project(s.lat, s.lon);
                return `${p.x},${p.y}`;
              })
              .filter(Boolean)
              .join(' ');

            const isHovered = hoveredCorridor === c.id;
            const status = c.status || 'CLEAR';

            // Check if status matches active filter
            if (filterStatus === 'BLOCKS' && status !== 'UNDER_BLOCK') return null;
            if (filterStatus === 'RISK' && status !== 'AT_RISK' && status !== 'LIVE_DEFECT') return null;

            const strokeColor = getStatusColor(status);

            return (
              <g
                key={c.id}
                onMouseEnter={() => setHoveredCorridor(c.id)}
                onMouseLeave={() => setHoveredCorridor(null)}
                className="cursor-pointer transition-all duration-300"
              >
                {/* Outer Glow Path */}
                <polyline
                  points={points}
                  fill="none"
                  stroke={strokeColor}
                  strokeWidth={isHovered ? 8 : status === 'LIVE_DEFECT' ? 7 : 5}
                  strokeOpacity={isHovered ? 0.9 : status === 'CLEAR' ? 0.5 : 0.8}
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  filter={status === 'CLEAR' ? 'url(#glow-emerald)' : 'url(#glow-red)'}
                />

                {/* Main Track Backbone (Railway Tie dashes) */}
                <polyline
                  points={points}
                  fill="none"
                  stroke="#ffffff"
                  strokeWidth={2}
                  strokeDasharray={status === 'UNDER_BLOCK' ? '4 3' : '8 4'}
                  strokeOpacity={isHovered ? 0.95 : 0.75}
                  strokeLinecap="round"
                  strokeLinejoin="round"
                />

                {/* Animated pulse if LIVE_DEFECT */}
                {status === 'LIVE_DEFECT' && (
                  <polyline
                    points={points}
                    fill="none"
                    stroke="#f43f5e"
                    strokeWidth={4}
                    strokeDasharray="12 12"
                    strokeOpacity={0.8}
                    className="animate-pulse"
                  />
                )}
              </g>
            );
          })}

          {/* Moving Trains on Tracks */}
          {showTrains &&
            SIMULATED_TRAINS.map((train) => {
              const pos = getTrainPosition(train);
              return (
                <g
                  key={train.id}
                  transform={`translate(${pos.x}, ${pos.y}) rotate(${pos.angle})`}
                  onClick={() => {
                    playAlarmSound('click');
                    setCockpitTrain(train);
                  }}
                  className="cursor-pointer group"
                >
                  {/* Train Blip Glow */}
                  <circle r="9" fill={train.type === 'rajdhani' ? '#38bdf8' : '#a855f7'} opacity="0.3" className="animate-ping" />
                  
                  {/* Train Body (Streamlined icon) */}
                  <rect
                    x="-8"
                    y="-4"
                    width="16"
                    height="8"
                    rx="3"
                    fill={train.type === 'rajdhani' ? '#0284c7' : train.type === 'freight' ? '#d97706' : '#7c3aed'}
                    stroke="#ffffff"
                    strokeWidth="1.5"
                    filter="drop-shadow(0 0 4px rgba(0,0,0,0.8))"
                    className="transition-transform group-hover:scale-125"
                  />

                  {/* Front Headlight Beam */}
                  <polygon points="8,-2 18,-6 18,6 8,2" fill="#fef08a" opacity="0.4" />

                  {/* Train Label (Counter-rotated so text is always right-side up) */}
                  <g transform={`rotate(${-pos.angle}) translate(0, -10)`}>
                    <rect x="-35" y="-9" width="70" height="12" rx="3" fill="#0f172a" fillOpacity="0.9" stroke="#06b6d4" strokeWidth="0.8" />
                    <text textAnchor="middle" y="0" fill="#f8fafc" fontSize="8" fontWeight="bold" fontFamily="monospace">
                      {train.id} {train.name.split(' ')[0]}
                    </text>
                  </g>
                </g>
              );
            })}

          {/* Station Nodes */}
          {Object.entries(STATIONS).map(([name, data]) => {
            const { x, y } = project(data.lat, data.lon);
            const weather = divisionWeatherMap[name];
            const isHovered = hoveredStation === name;
            const isSelected = selectedStation === name;
            const isRain = weather?.is_raining;

            // Highlight major metro junctions
            const isMetro = ['Delhi', 'Mumbai', 'Chennai', 'Howrah', 'Nagpur'].includes(name);

            return (
              <g
                key={name}
                transform={`translate(${x}, ${y})`}
                onMouseEnter={() => setHoveredStation(name)}
                onMouseLeave={() => setHoveredStation(null)}
                onClick={() => {
                  setSelectedStation(name);
                  if (onSelectStation) onSelectStation(name);
                }}
                className="cursor-pointer group"
              >
                {/* Metro Ring Indicator */}
                {isMetro && (
                  <circle r="12" fill="none" stroke="#38bdf8" strokeWidth="1" strokeDasharray="3 3" opacity="0.6" className="animate-spin" style={{ animationDuration: '12s' }} />
                )}

                {/* Rain Ripple */}
                {isRain && (
                  <circle r="16" fill="none" stroke="#60a5fa" strokeWidth="1.5" opacity="0.7" className="animate-ping" />
                )}

                {/* Station Node Body */}
                <circle
                  r={isMetro ? 6 : 4.5}
                  fill={isMetro ? '#0284c7' : '#1e293b'}
                  stroke={isMetro ? '#38bdf8' : '#94a3b8'}
                  strokeWidth={isMetro ? 2 : 1.5}
                  className="transition-all duration-200 group-hover:scale-125"
                />
                <circle r={isMetro ? 2.5 : 1.5} fill="#ffffff" />

                {/* Rain Cloud Emoji above Station */}
                {isRain && showWeather && (
                  <text x="0" y="-12" textAnchor="middle" fontSize="11" className="animate-bounce">
                    🌧️
                  </text>
                )}

                {/* Station Label & Live Temp */}
                <g transform="translate(0, 14)">
                  <text
                    textAnchor="middle"
                    fill={isMetro ? '#f8fafc' : '#cbd5e1'}
                    fontSize={isMetro ? 9.5 : 8}
                    fontWeight={isMetro ? 'bold' : '500'}
                    className="select-none tracking-tight font-sans"
                    style={{ textShadow: '0 2px 4px #000000' }}
                  >
                    {name}
                    {showWeather && weather && (
                      <tspan fill="#38bdf8" fontWeight="bold">
                        {' '}{Math.round(weather.temp)}°
                      </tspan>
                    )}
                  </text>
                </g>
              </g>
            );
          })}
        </svg>

        {/* Floating Station Inspector Card (on hover/click) */}
        {hoveredStation && (
          <div
            className="absolute top-6 right-6 w-72 bg-surface-container/95 backdrop-blur-xl border border-primary/30 rounded-xl p-4 shadow-2xl z-30 transition-all animate-in fade-in slide-in-from-top-2"
          >
            <div className="flex items-start justify-between">
              <div>
                <span className="text-[10px] font-mono font-bold uppercase tracking-wider text-primary">
                  {STATIONS[hoveredStation]?.zone} RAILWAY · DIVISION HQ
                </span>
                <h3 className="font-bold text-on-surface text-base">
                  {STATIONS[hoveredStation]?.label || hoveredStation}
                </h3>
              </div>
              <span className="px-2 py-0.5 rounded bg-surface border border-outline-variant font-mono text-xs font-bold text-on-surface">
                {STATIONS[hoveredStation]?.code}
              </span>
            </div>

            {/* Weather Metrics */}
            {divisionWeatherMap[hoveredStation] && (
              <div className="mt-3 p-2.5 rounded-lg bg-surface/80 border border-outline-variant/40 flex items-center justify-between text-xs">
                <div className="flex items-center gap-2">
                  <span className="text-xl">
                    {divisionWeatherMap[hoveredStation].is_raining ? '🌧️' : '☀️'}
                  </span>
                  <div>
                    <div className="font-bold text-on-surface">
                      {divisionWeatherMap[hoveredStation].temp}°C
                    </div>
                    <div className="text-[10px] text-on-surface-variant capitalize">
                      {divisionWeatherMap[hoveredStation].desc}
                    </div>
                  </div>
                </div>
                <div className="text-right">
                  <div className="font-mono text-cyan-400 font-bold">
                    {divisionWeatherMap[hoveredStation].rain_mm} mm
                  </div>
                  <div className="text-[10px] text-on-surface-variant font-mono">Live Precip.</div>
                </div>
              </div>
            )}

            {/* Quick Stats */}
            <div className="mt-3 grid grid-cols-2 gap-2 text-[11px] font-mono">
              <div className="p-2 rounded bg-surface/50 border border-outline-variant/30">
                <span className="text-on-surface-variant block text-[10px]">COORDINATES</span>
                <span className="font-bold text-on-surface">
                  {STATIONS[hoveredStation]?.lat.toFixed(2)}°N, {STATIONS[hoveredStation]?.lon.toFixed(2)}°E
                </span>
              </div>
              <div className="p-2 rounded bg-surface/50 border border-outline-variant/30">
                <span className="text-on-surface-variant block text-[10px]">TRACK STATUS</span>
                <span className="font-bold text-emerald-400 flex items-center gap-1">
                  <span className="w-1.5 h-1.5 rounded-full bg-emerald-400"></span>
                  OPERATIONAL
                </span>
              </div>
            </div>

            <p className="mt-2.5 text-[10px] text-on-surface-variant italic">
              Live weather metrics synchronized from Open-Meteo REST API.
            </p>
          </div>
        )}
      </div>

      {/* Real-Time CRIS / COCC Central Ticker */}
      <div className="bg-[#050811] px-4 py-2 border-t border-slate-800 flex items-center gap-3 text-[11px] font-mono overflow-hidden">
        <div className="flex items-center gap-1.5 text-cyan-400 font-bold shrink-0">
          <span className="w-2 h-2 rounded-full bg-cyan-400 animate-ping"></span>
          COCC TELEMETRY:
        </div>
        <div className="truncate text-slate-300">
          [LIVE STREAM] Track Recording Car TRC-99 streaming · 120 segments monitored via Weibull AFT · Kavach UHF 457MHz linked with {SIMULATED_TRAINS.length} express rakes · Open-Meteo weather synced · 💡 Click any moving train on the map to launch the Loco Pilot Cab HUD!
        </div>
      </div>

      {/* Bottom Corridor Legend & Quick Stats */}
      <div className="p-3 bg-surface-container/90 border-t border-outline-variant/30 flex flex-wrap items-center justify-between gap-4 text-xs font-mono">
        <div className="flex items-center gap-4">
          <span className="text-on-surface-variant font-bold">STATUS LEGEND:</span>
          <div className="flex items-center gap-1.5">
            <span className="w-3 h-1 rounded-full bg-emerald-500 shadow-[0_0_8px_#10b981]"></span>
            <span className="text-emerald-400 font-medium">Clear Section</span>
          </div>
          <div className="flex items-center gap-1.5">
            <span className="w-3 h-1 rounded-full bg-amber-500 shadow-[0_0_8px_#f59e0b]"></span>
            <span className="text-amber-400 font-medium">Elevated Risk (&gt;40%)</span>
          </div>
          <div className="flex items-center gap-1.5">
            <span className="w-3 h-1 rounded-full bg-rose-500 shadow-[0_0_8px_#ef4444]"></span>
            <span className="text-rose-400 font-medium">Under Possession Block</span>
          </div>
        </div>

        <div className="flex items-center gap-3 text-on-surface-variant">
          <span>Active Trains: <strong className="text-on-surface">{SIMULATED_TRAINS.length}</strong></span>
          <span>·</span>
          <span>National Junctions: <strong className="text-on-surface">{Object.keys(STATIONS).length}</strong></span>
          <span>·</span>
          <span>GIS Projection: <strong className="text-primary">Equirectangular WGS84</strong></span>
        </div>
      </div>

      {/* Loco Pilot Cockpit Modal */}
      {cockpitTrain && (
        <LocoCockpitModal
          train={cockpitTrain}
          onClose={() => setCockpitTrain(null)}
        />
      )}
    </div>
  );
}
