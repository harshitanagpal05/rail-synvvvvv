import React from 'react';

export default function NetworkMap({ networkData }) {
  if (!networkData || !networkData.corridors) {
    return <div className="p-8 text-center text-on-surface-variant">Loading National Network...</div>;
  }

  const getStatusColor = (status) => {
    switch (status) {
      case 'CLEAR': return 'bg-emerald-500 shadow-[0_0_10px_rgba(16,185,129,0.5)]';
      case 'AT_RISK': return 'bg-amber-500 shadow-[0_0_15px_rgba(245,158,11,0.8)] animate-pulse';
      case 'LIVE_DEFECT': return 'bg-rose-500 shadow-[0_0_20px_rgba(244,63,94,1)] animate-ping';
      case 'UNDER_BLOCK': return 'bg-rose-600 pattern-diagonal-lines pattern-rose-500 pattern-bg-rose-800 pattern-size-2 pattern-opacity-100';
      default: return 'bg-surface-variant';
    }
  };

  const getStatusText = (status) => {
    switch (status) {
      case 'CLEAR': return 'Track Clear';
      case 'AT_RISK': return 'High Risk Warning';
      case 'LIVE_DEFECT': return 'Emergency Defect Reported';
      case 'UNDER_BLOCK': return 'Maintenance Block Active';
      default: return 'Unknown';
    }
  };

  return (
    <div className="bg-surface-container-low rounded-2xl p-6 border border-outline-variant/30 flex flex-col gap-6 w-full relative overflow-hidden">
      {/* Background aesthetic */}
      <div className="absolute top-0 right-0 w-64 h-64 bg-primary/5 rounded-full blur-3xl -translate-y-1/2 translate-x-1/3"></div>
      
      <div className="flex justify-between items-end relative z-10">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-[10px] font-bold bg-primary/10 text-primary border border-primary/20 animate-pulse">
              <span className="w-1.5 h-1.5 rounded-full bg-primary"></span>
              REAL-TIME OPEN-METEO SYNCED
            </span>
          </div>
          <h2 className="text-xl font-bold tracking-tight text-on-surface flex items-center gap-2">
            <span className="material-symbols-outlined text-primary">satellite_alt</span>
            National Railway Command Center
          </h2>
          <p className="text-on-surface-variant text-sm mt-1">Live pan-India corridor health & clearance monitoring</p>
        </div>
        
        <div className="flex gap-4 text-xs font-medium bg-surface-container p-2 rounded-lg border border-outline-variant/50">
          <div className="flex items-center gap-1.5"><div className="w-2.5 h-2.5 rounded-full bg-emerald-500"></div> Clear</div>
          <div className="flex items-center gap-1.5"><div className="w-2.5 h-2.5 rounded-full bg-amber-500"></div> Risk Detected</div>
          <div className="flex items-center gap-1.5"><div className="w-2.5 h-2.5 rounded-full bg-rose-600 pattern-diagonal-lines pattern-rose-400 pattern-bg-rose-600 pattern-size-1"></div> Under Block</div>
        </div>
      </div>

      <div className="grid grid-cols-2 gap-4 relative z-10">
        {networkData.corridors.map(c => (
          <div key={c.id} className="bg-surface-container rounded-xl p-4 border border-outline-variant/30 transition-all hover:border-primary/40 hover:shadow-lg hover:shadow-primary/5">
            <div className="flex justify-between items-center mb-4">
              <h3 className="font-bold text-on-surface text-sm uppercase tracking-wider">{c.name}</h3>
              <span className={`text-[10px] uppercase font-bold px-2 py-1 rounded-md tracking-wider ${
                c.status === 'CLEAR' ? 'bg-emerald-500/10 text-emerald-400' : 
                c.status === 'AT_RISK' ? 'bg-amber-500/10 text-amber-400' : 
                'bg-rose-500/10 text-rose-400'
              }`}>
                {getStatusText(c.status)}
              </span>
            </div>
            
            {/* Visual Track Line */}
            <div className="relative h-2 bg-surface-variant rounded-full mb-6 mt-2 overflow-visible flex items-center">
              {c.segments && c.segments.length > 0 ? (
                c.segments.map((seg, i) => (
                  <div 
                    key={seg.segment_id} 
                    className={`h-full ${getStatusColor(seg.status)}`}
                    style={{ width: `${100 / c.segments.length}%` }}
                    title={`${seg.division}: ${getStatusText(seg.status)} (Risk: ${Math.round(seg.risk*100)}%)`}
                  ></div>
                ))
              ) : (
                <div className="w-full h-full bg-emerald-500 rounded-full"></div>
              )}
              
              {/* Nodes for divisions */}
              {c.divisions && c.divisions.map((div, i) => {
                const weather = c.division_weather ? c.division_weather[div] : null;
                return (
                  <div 
                    key={i} 
                    className="absolute w-3 h-3 rounded-full bg-surface border-2 border-outline-variant -translate-y-1/2 group cursor-pointer"
                    style={{ left: `${(i / (c.divisions.length - 1)) * 100}%`, top: '50%', transform: 'translate(-50%, -50%)' }}
                  >
                    {/* Tooltip on hover */}
                    <div className="hidden group-hover:flex flex-col absolute bottom-5 left-1/2 -translate-x-1/2 bg-surface-container-highest border border-outline-variant p-2 rounded-lg text-[10px] text-on-surface shadow-xl whitespace-nowrap z-50 pointer-events-none">
                      <div className="font-bold flex items-center gap-1">
                        <span>{div} Division</span>
                        {weather?.is_raining && <span className="text-primary animate-pulse">🌧️ Heavy Rain</span>}
                      </div>
                      {weather && (
                        <div className="text-on-surface-variant flex gap-2 mt-0.5">
                          <span>🌡️ {weather.temp}°C</span>
                          <span>💧 {weather.rain_mm} mm</span>
                          <span>☁️ {weather.desc}</span>
                        </div>
                      )}
                    </div>

                    {/* Rain indicator dot */}
                    {weather?.is_raining && (
                      <span className="absolute -top-3 left-1/2 -translate-x-1/2 text-[10px] animate-bounce">
                        🌧️
                      </span>
                    )}

                    <span className="absolute top-4 left-1/2 -translate-x-1/2 text-[9px] font-medium text-on-surface-variant whitespace-nowrap">
                      {div} {weather ? `(${Math.round(weather.temp)}°)` : ''}
                    </span>
                  </div>
                );
              })}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
