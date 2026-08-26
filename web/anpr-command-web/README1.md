# 🚔 TRACE-SIH — Next-Gen ANPR & Intelligent Traffic Surveillance Command Center

Welcome to **TRACE-SIH**, an enterprise-grade, full-stack Automatic Number Plate Recognition (ANPR) Command and Control Platform built for modern traffic surveillance, high-speed vehicle tracking, automated hot-listing, and real-time spatial analytics.

Designed specifically for Smart City infrastructures, law enforcement agencies, and highway authorities, TRACE-SIH transforms raw edge-camera detections into actionable intelligence through interactive map visualization, trajectory reconstruction, and instant security alerting.

---

## 📸 Key Platform Modules

### 1. 🛰️ Central Command Dashboard (`/`)
The primary operational hub designed for mission-critical monitoring:
- **Interactive GIS Map**: Powered by Leaflet, displaying live positions of camera nodes, active alerts, and vehicle detection markers.
- **Live ANPR Stream**: Real-time ticker showing plate numbers, confidence scores, camera locations, and detection timestamps.
- **Top Metrics Overview**: Instant counters for total daily detections, active watchlist matches, network camera status, and average system latency.

### 2. 🔍 Vehicle Trajectory Reconstruction (`/trajectory`)
Forensic path tracking across distributed camera networks:
- **Route Plotting**: Maps the chronological path of any vehicle across camera checkpoints with directional polylines.
- **Time-Stamped Waypoints**: Detailed log of exact detection times, speeds, and camera locations to accurately estimate vehicle direction and velocity.

### 3. 🚨 Real-Time Watchlist & Alert Center (`/alerts`)
Automated threat detection and emergency notification workflow:
- **Hotlist Matching**: Instant match alerts for stolen vehicles, wanted suspects, or flagged transport.
- **Alert Triage & Resolution**: Allows operators to review, acknowledge, dismiss, or escalate high-priority security notifications.
- **Custom Rule Engine**: Set up alerts by vehicle class, speed thresholds, or geo-fenced boundaries.

### 4. 🔬 Manual Review Workspace (`/review`)
Quality assurance tool for low-confidence or obstructed reads:
- **Crop Inspection**: View zoomed-in license plate crops alongside full camera snapshots.
- **Human-in-the-Loop Correction**: Easily edit and re-classify plate characters to maintain high dataset accuracy.

### 5. 📊 Traffic & Heatmap Analytics (`/analytics`)
Data-driven insights for urban planning and traffic management:
- **Spatial Heatmaps**: Density mapping highlighting high-traffic corridors and congestion bottlenecks.
- **Hourly Flow Charts**: Recharts-powered graphs comparing morning and evening peak traffic hours.
- **Travel Time Estimations**: Calculate average travel times between specific highway checkpoints.

### 6. 🖥️ Edge System & Camera Health (`/system`)
Infrastructure diagnostics and hardware monitoring:
- **Camera Network Grid**: Live operational state (`Online`, `Degraded`, `Offline`) across all edge devices.
- **System Metrics**: Latency checks, frame drop rates, bandwidth usage, and hardware heartbeats.

---

## 🏗️ Architecture & Technology Stack

| Layer | Component | Description |
| :--- | :--- | :--- |
| **Frontend Framework** | Next.js 14 (App Router) | React Server Components & client-side interactive UI using TypeScript |
| **Styling & UI** | Tailwind CSS + PostCSS | Custom glassmorphism dark-theme dashboard with responsive controls |
| **Mapping Engine** | Leaflet & React-Leaflet | Dynamic vector maps, custom markers, heatmaps, and route polylines |
| **Data Visualization** | Recharts | Smooth analytical graphs, traffic flow trends, and alert metrics |
| **Database & API** | Supabase & Next.js API Routes | PostgreSQL database for sightings, watchlist storage, and REST API endpoints |

---

## 📁 Repository Structure

```text
anpr-command-web/
├── public/                 # Static assets, camera icons, and mock datasets
├── src/
│   ├── app/
│   │   ├── page.tsx        # Command Center Central Dashboard
│   │   ├── alerts/         # Watchlist & Emergency Alert Interface
│   │   ├── analytics/      # Traffic Analytics & Spatial Heatmaps
│   │   ├── review/         # Manual Plate Verification Workspace
│   │   ├── system/         # Infrastructure & Camera Health Dashboard
│   │   ├── trajectory/     # Vehicle Trajectory Reconstruction Page
│   │   └── api/            # Serverless API Endpoints
│   │       ├── alerts/     # Threat management & acknowledgment endpoints
│   │       ├── analytics/  # Aggregated heatmap & summary metrics
│   │       ├── anpr/       # Live detection ingest pipeline
│   │       ├── cameras/    # Camera node status & metadata
│   │       ├── health/     # System diagnostic health check
│   │       ├── plates/     # Forensic license plate search engine
│   │       ├── review/     # Manual crop review update endpoints
│   │       ├── sightings/  # Sightings feed query & filtering API
│   │       ├── trajectory/ # Vehicle path reconstruction algorithm
│   │       └── watchlist/  # Hotlisted plate management
│   ├── components/         # Modular UI Components (MapView, Sidebar, TopBar, etc.)
│   └── lib/                # Database clients, analytical helpers, & TypeScript types
├── tailwind.config.ts      # Tailwind UI Theme Customization
└── package.json            # Project dependencies and script commands
```

---

## ⚡ Quick Start & Development Setup

### 1. Prerequisites
Ensure you have the following installed on your local machine:
- **Node.js**: `v18.0.0` or higher
- **npm**: `v9.0.0` or higher (or `yarn` / `pnpm`)
- **Git**

### 2. Installation
Clone the repository and install all required node modules:

```bash
git clone https://github.com/Komali0208/TRACE-SIH.git
cd TRACE-SIH
npm install
```

### 3. Environment Setup
Create a `.env.local` file in the root directory:

```env
NEXT_PUBLIC_SUPABASE_URL=https://your-supabase-instance.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=your-anon-key-here
```

### 4. Running the Development Server
Launch the application locally in development mode:

```bash
npm run dev
```

Open [http://localhost:3000](http://localhost:3000) in your browser to access the TRACE-SIH Command Center.

---

## 🔌 API Reference Guide

### Detection Ingest & Query
- `POST /api/anpr` — Receive incoming ANPR edge camera payloads.
- `GET /api/sightings` — Query vehicle detection history with date and location filters.
- `GET /api/plates/search` — Perform exact or fuzzy searches on plate numbers.

### Surveillance & Intelligence
- `GET /api/trajectory/[plate]` — Fetch ordered geospatial checkpoints for trajectory plotting.
- `GET /api/watchlist` — Retrieve active hotlisted plates.
- `POST /api/watchlist` — Add a new license plate to the security watchlist.

### Analytics & Diagnostics
- `GET /api/analytics/summary` — Retrieve system-wide statistical counts.
- `GET /api/analytics/heatmap` — Obtain spatial density points for traffic flow.
- `GET /api/cameras` — Check online status of all registered ANPR camera units.
- `GET /api/health` — Returns system uptime and API status.

---

## 🛠️ Build & Production Deployment

To compile and verify the production build locally:

```bash
# Build production bundle
npm run build

# Start production server
npm run start
```

---

## 🤝 Contributing & Guidelines

1. Fork the project repository.
2. Create your feature branch (`git checkout -b feature/AmazingFeature`).
3. Commit your changes (`git commit -m 'Add AmazingFeature'`).
4. Push to the branch (`git push origin feature/AmazingFeature`).
5. Open a Pull Request on GitHub.

---

## 📜 License

This project is licensed under the MIT License — see the [LICENSE](LICENSE) file for details.
