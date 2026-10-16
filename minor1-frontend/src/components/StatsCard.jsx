export default function StatsCard({ title, value, unit }) {
  const getIcon = (title) => {
    switch (title) {
      case "Active Signal": return "🚦";
      case "Green Time Left": return "⏱️";
      case "Total Vehicles": return "🚗";
      case "System Mode": return "🤖";
      default: return "📊";
    }
  };

  return (
    <div className="stats-card">
      <h3>{getIcon(title)} {title}</h3>
      <div className="value">
        {value}
        {unit && <span className="unit">{unit}</span>}
      </div>
    </div>
  );
}
