export default function Header() {
  return (
    <header className="header">
      <h1>🚦 TrafficFlow AI Control Center</h1>
      <p>Real-time YOLOv3 Vehicle Detection & Traffic Management System</p>
      <div style={{
        display: "flex",
        alignItems: "center",
        gap: "20px",
        marginTop: "10px"
      }}>
        <span style={{
          color: "#22c55e",
          fontSize: "14px",
          fontWeight: "600",
          textTransform: "uppercase",
          letterSpacing: "1px"
        }}>
          ● System Online
        </span>
        <span style={{
          color: "#00ffff",
          fontSize: "12px",
          fontFamily: "monospace"
        }}>
          YOLOv3 Model Active
        </span>
      </div>
    </header>
  );
}
