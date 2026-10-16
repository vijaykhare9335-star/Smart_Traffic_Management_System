export default function LaneCard({ lane, density, vehicles, active }) {
  return (
    <div className={`lane-card ${active ? "active" : ""}`}>
      <h3>
        {lane}
        {active && <span style={{ color: "#22c55e", marginLeft: "8px" }}>🟢</span>}
      </h3>

      <div className="vehicle-count">{vehicles}</div>

      <span className={`density ${density.toLowerCase()}`}>
        {density.toUpperCase()} TRAFFIC
      </span>

      <div style={{
        marginTop: "16px",
        display: "grid",
        gridTemplateColumns: "1fr 1fr",
        gap: "8px",
        fontSize: "12px",
        color: "#94a3b8"
      }}>
        <div>🚗 Cars: {Math.floor(vehicles * 0.6)}</div>
        <div>🏍 Bikes: {Math.floor(vehicles * 0.2)}</div>
        <div>🚚 Trucks: {Math.floor(vehicles * 0.15)}</div>
        <div>🚌 Buses: {Math.floor(vehicles * 0.05)}</div>
      </div>

      {active && (
        <div style={{
          marginTop: "12px",
          padding: "6px 12px",
          background: "rgba(34, 197, 94, 0.2)",
          border: "1px solid rgba(34, 197, 94, 0.3)",
          borderRadius: "20px",
          color: "#22c55e",
          fontSize: "11px",
          fontWeight: "600",
          textAlign: "center",
          textTransform: "uppercase",
          letterSpacing: "0.5px"
        }}>
          🚦 GREEN SIGNAL ACTIVE
        </div>
      )}
    </div>
  );
}
