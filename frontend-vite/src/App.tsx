import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { 
  TrendingUp, 
  Users, 
  DollarSign, 
  ShieldCheck, 
  BarChart2, 
  PieChart, 
  Calendar,
  Music
} from 'lucide-react';
import { 
  XAxis, 
  YAxis, 
  CartesianGrid, 
  Tooltip, 
  ResponsiveContainer, 
  AreaChart, 
  Area 
} from 'recharts';
import { motion, AnimatePresence } from 'framer-motion';

const API_BASE = "http://localhost:8000/api";

const App: React.FC = () => {
  const [kpis, setKpis] = useState<any>(null);
  const [trends, setTrends] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchData = async () => {
      try {
        const [kpiRes, trendRes] = await Promise.all([
          axios.get(`${API_BASE}/dashboard/kpis`),
          axios.get(`${API_BASE}/dashboard/trends`)
        ]);
        setKpis(kpiRes.data);
        setTrends(trendRes.data);
        setLoading(false);
      } catch (err) {
        console.error("API error:", err);
        setLoading(false);
      }
    };
    fetchData();
  }, []);

  if (loading) return (
    <div className="h-screen w-full flex items-center justify-center bg-sakura-50">
      <motion.div 
        animate={{ rotate: 360 }}
        transition={{ repeat: Infinity, duration: 2, ease: "linear" }}
        className="w-12 h-12 border-4 border-sakura-400 border-t-transparent rounded-full"
      />
    </div>
  );

  return (
    <div className="min-h-screen bg-slate-50 flex">
      {/* Sidebar */}
      <aside className="w-64 bg-white border-r border-sakura-100 p-6 flex flex-col gap-8">
        <div className="flex items-center gap-3">
          <div className="p-2 bg-sakura-100 rounded-xl">
            <span className="text-2xl">🌸</span>
          </div>
          <h1 className="text-xl font-bold text-sakura-800">KKBOX Churn</h1>
        </div>
        
        <nav className="flex flex-col gap-2">
          <button className="flex items-center gap-3 p-3 bg-sakura-50 text-sakura-600 rounded-lg font-medium transition-all">
            <TrendingUp size={20} />
            통합 대시보드
          </button>
          <button className="flex items-center gap-3 p-3 text-slate-500 hover:bg-slate-50 rounded-lg transition-all">
            <Users size={20} />
            고위험군 관리
          </button>
          <button className="flex items-center gap-3 p-3 text-slate-500 hover:bg-slate-50 rounded-lg transition-all">
            <BarChart2 size={20} />
            마케팅 시뮬레이터
          </button>
        </nav>

        <div className="mt-auto p-4 bg-gradient-to-br from-sakura-50 to-spring-50 rounded-2xl border border-sakura-100">
          <div className="flex items-center gap-2 mb-2">
            <Music size={16} className="text-sakura-400" />
            <span className="text-xs font-bold text-sakura-600">Now Playing</span>
          </div>
          <p className="text-sm font-medium text-sakura-800">벚꽃 엔딩</p>
          <p className="text-[10px] text-sakura-400">Busker Busker</p>
        </div>
      </aside>

      {/* Main Content */}
      <main className="flex-1 p-8 overflow-y-auto">
        <header className="flex justify-between items-center mb-8">
          <div>
            <h2 className="text-2xl font-bold text-slate-800">이탈 방어 모니터링</h2>
            <p className="text-slate-500">실시간 데이터 분석 및 예측</p>
          </div>
          <div className="flex items-center gap-4 bg-white p-2 rounded-xl border border-slate-200">
            <Calendar size={18} className="text-slate-400 ml-2" />
            <span className="text-sm font-medium text-slate-600 uppercase">2026-04-02</span>
            <div className="w-8 h-8 rounded-full bg-sakura-100" />
          </div>
        </header>

        {/* KPI Cards */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
          <AnimatePresence>
            {[
              { title: "고위험 유저", val: kpis?.today.high_risk_users, delta: kpis?.deltas.users, icon: Users, color: "sakura" },
              { title: "매출 위기 총액", val: `₩${Math.round(kpis?.today.revenue_at_risk).toLocaleString()}`, delta: kpis?.deltas.revenue, icon: DollarSign, color: "slate" },
              { title: "이탈 방어 성공률", val: `${kpis?.today.defense_rate}%`, delta: kpis?.deltas.defense_rate, icon: ShieldCheck, color: "spring" }
            ].map((card, i) => (
              <motion.div 
                key={i}
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: i * 0.1 }}
                whileHover={{ y: -5 }}
                className="bg-white p-6 rounded-2xl border border-slate-100 shadow-sm transition-shadow hover:shadow-md"
              >
                <div className="flex justify-between items-start mb-4">
                  <div className={`p-3 bg-${card.color}-50 rounded-lg`}>
                    <card.icon className={`text-${card.color}-500`} size={24} />
                  </div>
                  <span className={`text-xs font-bold px-2 py-1 rounded-full ${card.delta >= 0 ? 'bg-red-50 text-red-500' : 'bg-green-50 text-green-500'}`}>
                    {card.delta >= 0 ? '+' : ''}{card.delta.toLocaleString()}
                  </span>
                </div>
                <h3 className="text-slate-500 text-sm font-medium mb-1">{card.title}</h3>
                <p className="text-2xl font-bold text-slate-800">{card.val}</p>
              </motion.div>
            ))}
          </AnimatePresence>
        </div>

        {/* Charts Section */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          <div className="lg:col-span-2 bg-white p-6 rounded-2xl border border-slate-100 shadow-sm">
            <div className="flex items-center justify-between mb-6">
              <h3 className="font-bold text-slate-800">이탈 위험 유저 추이 (7일)</h3>
              <div className="flex gap-4">
                <div className="flex items-center gap-2">
                  <div className="w-3 h-3 rounded-full bg-sakura-400" />
                  <span className="text-xs text-slate-400">고위험 유저</span>
                </div>
                <div className="flex items-center gap-2">
                  <div className="w-3 h-3 rounded-full bg-spring-400" />
                  <span className="text-xs text-slate-400">방어 성공 유저</span>
                </div>
              </div>
            </div>
            <div className="h-[300px]">
              <ResponsiveContainer width="100%" height="100%">
                <AreaChart data={trends}>
                  <defs>
                    <linearGradient id="colorHigh" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="#F472A8" stopOpacity={0.1}/>
                      <stop offset="95%" stopColor="#F472A8" stopOpacity={0}/>
                    </linearGradient>
                    <linearGradient id="colorDef" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="#55A83A" stopOpacity={0.1}/>
                      <stop offset="95%" stopColor="#55A83A" stopOpacity={0}/>
                    </linearGradient>
                  </defs>
                  <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#f1f5f9" />
                  <XAxis dataKey="date" axisLine={false} tickLine={false} tick={{fontSize: 12, fill: '#94a3b8'}} dy={10} />
                  <YAxis axisLine={false} tickLine={false} tick={{fontSize: 12, fill: '#94a3b8'}} />
                  <Tooltip 
                    contentStyle={{ borderRadius: '12px', border: 'none', boxShadow: '0 10px 15px -3px rgba(0,0,0,0.1)' }}
                  />
                  <Area type="monotone" dataKey="high_risk_users" stroke="#F472A8" strokeWidth={3} fillOpacity={1} fill="url(#colorHigh)" />
                  <Area type="monotone" dataKey="defended_users" stroke="#55A83A" strokeWidth={3} fillOpacity={1} fill="url(#colorDef)" />
                </AreaChart>
              </ResponsiveContainer>
            </div>
          </div>

          <div className="bg-white p-6 rounded-2xl border border-slate-100 shadow-sm">
            <h3 className="font-bold text-slate-800 mb-6">주요 이탈 위험군 사유</h3>
            <div className="flex flex-col gap-6">
              {[
                { label: "💳 멤버십 직접해지", value: 45, color: "bg-sakura-400" },
                { label: "🔥 자동결제 미등록", value: 30, color: "bg-spring-400" },
                { label: "🎧 활동성 저하", value: 15, color: "bg-amber-400" },
                { label: "❓ 기타", value: 10, color: "bg-slate-300" }
              ].map((item, i) => (
                <div key={i}>
                  <div className="flex justify-between mb-2">
                    <span className="text-xs font-semibold text-slate-600">{item.label}</span>
                    <span className="text-xs font-bold text-slate-400">{item.value}%</span>
                  </div>
                  <div className="w-full bg-slate-100 h-2 rounded-full overflow-hidden">
                    <motion.div 
                      initial={{ width: 0 }}
                      animate={{ width: `${item.value}%` }}
                      className={`h-full ${item.color}`}
                    />
                  </div>
                </div>
              ))}
            </div>
            
            <div className="mt-8 p-4 bg-slate-50 rounded-xl border border-slate-100">
              <h4 className="text-xs font-bold text-slate-800 mb-2 flex items-center gap-1">
                <PieChart size={14} className="text-sakura-400" />
                분석 인사이트
              </h4>
              <p className="text-[11px] text-slate-500 leading-relaxed">
                현재 <span className="font-bold text-sakura-600">멤버십 직접해지</span> 대상이 가장 많습니다. 해지 페이지 내 프로모션 노출 강화를 권장합니다.
              </p>
            </div>
          </div>
        </div>
      </main>
    </div>
  );
};

export default App;
