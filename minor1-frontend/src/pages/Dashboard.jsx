import { useEffect, useState } from "react";
import Header from "../components/Header";
import StatsCard from "../components/StatsCard";
import LaneCard from "../components/LaneCard";
import LiveFeed from "../components/LiveFeed";
import IntersectionView from "../components/IntersectionView";
import "../styles/dashboard.css";

export default function Dashboard() {
  const [lanes, setLanes] = useState({
    north: 0,
    south: 0,
    east: 0,
    west: 0,
  });
  const [laneData, setLaneData] = useState(null);

  const [greenLane, setGreenLane] = useState("north");
  const [greenTime, setGreenTime] = useState(0);
  const [cycleLimit, setCycleLimit] = useState(0);

  const highTrafficLanes = laneData
    ? Object.entries(laneData)
        .filter(([, value]) => value.density === "HIGH")
        .map(([lane]) => lane)
    : [];

  const trafficAlert = highTrafficLanes.length > 0
    ? `HIGH TRAFFIC: ${highTrafficLanes.join(", ")}`
    : "Traffic normal";

  // 🔁 Fetch backend data
  useEffect(() => {
    const interval = setInterval(async () => {
      try {
        const res = await fetch("http://127.0.0.1:5000/traffic");
        const data = await res.json();

        const newLanes = {
          north: data.North.vehicles,
          south: data.South.vehicles,
          east: data.East.vehicles,
          west: data.West.vehicles,
        };

        setLaneData(data);

        const maxLane = Object.keys(data).reduce((a, b) =>
          data[a].vehicles > data[b].vehicles ? a : b
        );

        const newGreenLane = maxLane.toLowerCase();
        const backendGreenTime = data[maxLane].green_time;

        setLanes(newLanes);

        if (newGreenLane !== greenLane) {
          setGreenLane(newGreenLane);
          setGreenTime(backendGreenTime);
          setCycleLimit(backendGreenTime);
        } else if (backendGreenTime > cycleLimit) {
          // Add time only when the AI model truly extends the current cycle.
          setGreenTime((prev) => prev + (backendGreenTime - cycleLimit));
          setCycleLimit(backendGreenTime);
        }

      } catch (err) {
        console.error(err);
      }
    }, 5000);  // Increased from 3000ms to 5000ms

    return () => clearInterval(interval);
  }, [greenLane, cycleLimit]);

  // ⏱ Timer
  useEffect(() => {
    if (greenTime <= 0) return;

    const timer = setInterval(() => {
      setGreenTime((prev) => prev - 1);
    }, 1000);

    return () => clearInterval(timer);
  }, [greenTime]);

  const getDensity = (laneKey, count) => {
    return laneData?.[laneKey]?.density || (count > 15 ? "HIGH" : count > 7 ? "MEDIUM" : "LOW");
  };

  return (
    <div className="dashboard">
      <Header />

      <div className="stats-row">
        <StatsCard title="Active Signal" value={greenLane.toUpperCase()} />
        <StatsCard title="Green Time Left" value={greenTime} unit="sec" />
        <StatsCard
          title="Total Vehicles"
          value={lanes.north + lanes.south + lanes.east + lanes.west}
        />
        <StatsCard title="Traffic Status" value={trafficAlert} />
      </div>

      <div className="lane-grid">
        <LaneCard lane="North Lane" vehicles={lanes.north} density={getDensity("North", lanes.north)} active={greenLane === "north"} />
        <LaneCard lane="South Lane" vehicles={lanes.south} density={getDensity("South", lanes.south)} active={greenLane === "south"} />
        <LaneCard lane="East Lane" vehicles={lanes.east} density={getDensity("East", lanes.east)} active={greenLane === "east"} />
        <LaneCard lane="West Lane" vehicles={lanes.west} density={getDensity("West", lanes.west)} active={greenLane === "west"} />

        <IntersectionView />
      </div>

      <LiveFeed />
    </div>
  );
}