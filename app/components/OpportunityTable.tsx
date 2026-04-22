type Props = {
  items: any[];
};

export default function OpportunityTable({ items }: Props) {
  return (
    <div className="card">
      <h3>Opportunities ({items.length})</h3>
      <table style={{ width: "100%", marginTop: 10 }}>
        <thead>
          <tr style={{ textAlign: "left", fontSize: 12, opacity: 0.7 }}>
            <th>Symbol</th>
            <th>Score</th>
            <th>Decision</th>
          </tr>
        </thead>
        <tbody>
          {items.map((o, i) => (
            <tr key={i} style={{ borderTop: "1px solid #222" }}>
              <td>{o.symbol || "N/A"}</td>
              <td>{o.score ?? "—"}</td>
              <td style={{
                color:
                  o.decision === "ENTER"
                    ? "#22c55e"
                    : o.decision === "REJECT"
                    ? "#ef4444"
                    : "#eab308",
              }}>
                {o.decision || "—"}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
