import { useEffect, useState } from "react";

export default function IntersectionView() {
  const [currentSignal, setCurrentSignal] = useState("north");
  const [countdown, setCountdown] = useState(25);
  const [cycleLimit, setCycleLimit] = useState(25);

  // Fetch current active lane from backend
  useEffect(() => {
    const fetchActiveLane = async () => {
      try {
        const res = await fetch("http://127.0.0.1:5000/traffic");
        const data = await res.json();

        // Find lane with highest vehicle count
        const maxLane = Object.keys(data).reduce((a, b) =>
          data[a].vehicles > data[b].vehicles ? a : b
        );

        const newLane = maxLane.toLowerCase();
        const backendGreenTime = data[maxLane].green_time;

        if (newLane !== currentSignal) {
          setCurrentSignal(newLane);
          setCountdown(backendGreenTime);
          setCycleLimit(backendGreenTime);
        } else if (backendGreenTime > cycleLimit) {
          setCountdown((prev) => Math.max(prev, prev + (backendGreenTime - cycleLimit)));
          setCycleLimit(backendGreenTime);
        }
      } catch (err) {
        console.error("Error fetching traffic data:", err);
      }
    };

    // Fetch immediately and then every 3 seconds
    fetchActiveLane();
    const interval = setInterval(fetchActiveLane, 3000);

    return () => clearInterval(interval);
  }, [currentSignal, cycleLimit]);

  // Countdown timer for current signal
  useEffect(() => {
    if (countdown <= 0) return;

    const timer = setInterval(() => {
      setCountdown((prev) => prev - 1);
    }, 1000);

    return () => clearInterval(timer);
  }, [countdown]);

  const getSignalState = (direction) => {
    if (direction === currentSignal) return "green";
    return "red";
  };

  return (
    <div className="intersection-view">
      <h3>🚦 LIVE INTERSECTION CONTROL</h3>

      <div className="intersection-diagram">
        {/* Horizontal Road */}
        <div className="road horizontal"></div>

        {/* Vertical Road */}
        <div className="road vertical"></div>

        {/* Traffic Signals */}
        <div className="signal north">
          <div className={`light red ${getSignalState("north") === "red" ? "active" : ""}`}></div>
          <div className={`light yellow ${getSignalState("north") === "yellow" ? "active" : ""}`}></div>
          <div className={`light green ${getSignalState("north") === "green" ? "active" : ""}`}></div>
        </div>

        <div className="signal south">
          <div className={`light red ${getSignalState("south") === "red" ? "active" : ""}`}></div>
          <div className={`light yellow ${getSignalState("south") === "yellow" ? "active" : ""}`}></div>
          <div className={`light green ${getSignalState("south") === "green" ? "active" : ""}`}></div>
        </div>

        <div className="signal east">
          <div className={`light red ${getSignalState("east") === "red" ? "active" : ""}`}></div>
          <div className={`light yellow ${getSignalState("east") === "yellow" ? "active" : ""}`}></div>
          <div className={`light green ${getSignalState("east") === "green" ? "active" : ""}`}></div>
        </div>

        <div className="signal west">
          <div className={`light red ${getSignalState("west") === "red" ? "active" : ""}`}></div>
          <div className={`light yellow ${getSignalState("west") === "yellow" ? "active" : ""}`}></div>
          <div className={`light green ${getSignalState("west") === "green" ? "active" : ""}`}></div>
        </div>

        {/* Center countdown display */}
        <div style={{
          position: "absolute",
          top: "50%",
          left: "50%",
          transform: "translate(-50%, -50%)",
          background: "rgba(0, 0, 0, 0.8)",
          color: "#00ffff",
          padding: "8px 16px",
          borderRadius: "8px",
          border: "1px solid rgba(0, 255, 255, 0.5)",
          fontSize: "18px",
          fontWeight: "bold",
          textAlign: "center",
          textShadow: "0 0 10px rgba(0, 255, 255, 0.8)"
        }}>
          {countdown}s
        </div>
      </div>

      <div style={{
        marginTop: "20px",
        textAlign: "center",
        color: "#94a3b8",
        fontSize: "14px"
      }}>
        Active: <span style={{ color: "#22c55e", fontWeight: "bold" }}>
          {currentSignal.toUpperCase()} LANE
        </span>
      </div>
    </div>
  );
}
