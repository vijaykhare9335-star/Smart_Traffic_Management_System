export default function LiveFeed() {
  return (
    <div className="live-feed">
      <div className="live-header">
        <h2>🔴 LIVE CAMERA FEEDS</h2>
        <span className="live-badge">● RECORDING</span>
      </div>

      <div className="feed-grid">
        <CameraBox title="CAM - NORTH" lane="North" />
        <CameraBox title="CAM - SOUTH" lane="South" />
        <CameraBox title="CAM - EAST" lane="East" />
        <CameraBox title="CAM - WEST" lane="West" />
      </div>
    </div>
  );
}

function CameraBox({ title, lane }) {
  return (
    <div className="camera-box">
      <div className="camera-header">
        <span>{title}</span>
        <span className="rec-dot">● REC</span>
      </div>

      {/* ✅ MJPEG STREAM WITH YOLO OVERLAYS */}
      <div className="camera-feed">
        <img
          src={`http://127.0.0.1:5000/video/${lane}`}
          alt={title}
          style={{
            width: "100%",
            height: "100%",
            objectFit: "cover",
          }}
        />
        {/* YOLO Detection Overlay Info */}
        <div style={{
          position: "absolute",
          bottom: "8px",
          left: "8px",
          background: "rgba(0, 0, 0, 0.7)",
          color: "#00ffff",
          padding: "4px 8px",
          borderRadius: "4px",
          fontSize: "12px",
          fontFamily: "monospace",
          border: "1px solid rgba(0, 255, 255, 0.3)"
        }}>
          YOLOv3 Active
        </div>
      </div>
    </div>
  );
}