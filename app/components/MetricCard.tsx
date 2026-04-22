type Props = {
  title: string;
  value: string | number | undefined;
};

export default function MetricCard({ title, value }: Props) {
  return (
    <div className="card" style={{ flex: 1 }}>
      <div style={{ fontSize: 12, opacity: 0.7 }}>{title}</div>
      <div style={{ fontSize: 20, fontWeight: "bold" }}>
        {value ?? "—"}
      </div>
    </div>
  );
}
