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
    <div className="rounded-xl border border-border bg-bg-panel/60 p-5">
      <h3 className="text-sm font-medium mb-4">Correctness por dificuldade</h3>
      <div className="h-64">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={data} margin={{ top: 5, right: 12, bottom: 0, left: 0 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.06)" />
            <XAxis
              dataKey="bucket"
              stroke="#6b6b7d"
              fontSize={11}
              tickLine={false}
              axisLine={{ stroke: "rgba(255,255,255,0.08)" }}
            />
            <YAxis
              domain={[0, 1]}
              stroke="#6b6b7d"
              fontSize={11}
              tickLine={false}
              axisLine={{ stroke: "rgba(255,255,255,0.08)" }}
              tickFormatter={(v) => `${(v * 100).toFixed(0)}%`}
            />
            <Tooltip
              contentStyle={{
                background: "#14141f",
                border: "1px solid rgba(255,255,255,0.12)",
                borderRadius: 8,
                fontSize: 12,
              }}
              formatter={(v: number) => `${(v * 100).toFixed(1)}%`}
            />
            <Legend wrapperStyle={{ fontSize: 12 }} iconType="circle" />
            <Bar dataKey="v1" name="v1" fill="#6b6b7d" radius={[6, 6, 0, 0]} />
            <Bar dataKey="v2" name="v2" fill="#2dd4bf" radius={[6, 6, 0, 0]} />
          </BarChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
