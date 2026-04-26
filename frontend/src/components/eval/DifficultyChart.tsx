"use client";

import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Legend,
} from "recharts";

interface Datum {
  bucket: string;
  v1: number;
  v2: number;
}

interface Props {
  data: Datum[];
}

export function DifficultyChart({ data }: Props) {
  return (
    <div className="border-t border-border pt-6">
      <div className="marker mb-3">/chart · by difficulty</div>
      <h3 className="text-base font-semibold tracking-tight text-ink mb-5">
        Correctness por dificuldade
      </h3>
      <div className="h-64">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={data} margin={{ top: 5, right: 12, bottom: 0, left: 0 }}>
            <CartesianGrid
              strokeDasharray="0"
              stroke="rgba(255,255,255,0.04)"
              vertical={false}
            />
            <XAxis
              dataKey="bucket"
              stroke="#5d5f68"
              fontSize={11}
              tickLine={false}
              axisLine={{ stroke: "rgba(255,255,255,0.08)" }}
            />
            <YAxis
              domain={[0, 1]}
              stroke="#5d5f68"
              fontSize={11}
              tickLine={false}
              axisLine={{ stroke: "rgba(255,255,255,0.08)" }}
              tickFormatter={(v) => `${(v * 100).toFixed(0)}%`}
            />
            <Tooltip
              cursor={{ fill: "rgba(255,255,255,0.03)" }}
              contentStyle={{
                background: "#0f0f12",
                border: "1px solid rgba(255,255,255,0.12)",
                borderRadius: 2,
                fontSize: 12,
                fontFamily: "var(--font-jetbrains), monospace",
              }}
              formatter={(v: number) => `${(v * 100).toFixed(1)}%`}
            />
            <Legend
              wrapperStyle={{
                fontSize: 11,
                paddingTop: 12,
                fontFamily: "var(--font-jetbrains), monospace",
                textTransform: "uppercase",
                letterSpacing: "0.14em",
              }}
              iconType="square"
              iconSize={8}
            />
            <Bar dataKey="v1" name="v1" fill="rgba(255,255,255,0.18)" />
            <Bar dataKey="v2" name="v2" fill="rgba(255,255,255,0.92)" />
          </BarChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
