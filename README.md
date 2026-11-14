# AeroAgri — Satellite Agricultural Geomap & Earth Observation Cockpit
### NASA Space Apps Challenge • Frontend

[![Vite](https://img.shields.io/badge/Vite-5.4-646CFF?style=flat&logo=vite&logoColor=white)](https://vitejs.dev/)
[![Leaflet](https://img.shields.io/badge/Leaflet-1.9.4-199900?style=flat&logo=leaflet&logoColor=white)](https://leafletjs.com/)
[![Node.js](https://img.shields.io/badge/Node.js-%3E%3D18.0-339933?style=flat&logo=node.js&logoColor=white)](https://nodejs.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

An interactive, high-performance satellite sky-view geomap and remote sensing cockpit built with **Vite** and **Leaflet**. Designed for the **NASA Space Apps Challenge**, AeroAgri bridges Earth Observation (EO) satellite data with precision agricultural telemetry, enabling real-time monitoring of crop canopy health, soil moisture indices, and irrigation canal networks.

---

## Table of Contents

- [Overview & Science Context](#overview--science-context)
- [Key Features](#key-features)
- [System Requirements](#system-requirements)
- [Universal Installation Guide](#universal-installation-guide)
  - [Step 0: Install Node.js (If Not Already Installed)](#step-0-install-nodejs-if-not-already-installed)
  - [Step 1: Clone the Repository & Checkout Branch](#step-1-clone-the-repository--checkout-branch)
  - [Step 2: Install Dependencies](#step-2-install-dependencies)
  - [Step 3: Run the Development Server](#step-3-run-the-development-server)
  - [Step 4: Building for Production](#step-4-building-for-production)
- [Project Directory Structure](#project-directory-structure)
- [Earth Observation & Datasets](#earth-observation--datasets)
- [Available Scripts](#available-scripts)
- [Troubleshooting & FAQs](#troubleshooting--faqs)
- [Contributing & License](#contributing--license)

---

## Overview & Science Context

AeroAgri is structured around two complementary geospatial scopes:

1. **🇮🇳 Mandya District Agro-Basin Focus (Karnataka, India)**:
   - Known as the *"Sugar City"* (*Sakkare Nagara*) of Karnataka and a vital agricultural powerhouse in the Kaveri River basin.
   - Tracks sugarcane (*Co 86032, Co 62175*), Sona Masuri paddy, and ragi (*GPU 28*) across 7 taluks.
   - Monitors hydrological feeding from the historic **Visvesvaraya Canal (VC Canal)** originating at **Krishna Raja Sagara (KRS) Dam**.
   - Integrates ground telemetric sensor nodes (soil moisture, precipitation, and temperature).

2. **🌐 Global Agricultural Breadbaskets Explorer**:
   - Macro-level monitoring across major food granaries: US Midwestern Corn Belt, Ukrainian Chornozem Belt, Argentine Pampas, Nile Delta, and the Australian Wheatbelt.
   - Comparative NDVI (*Normalized Difference Vegetation Index*) and NDWI (*Normalized Difference Water Index*) metrics.

---

## Key Features

- 🛰️ **Multi-Source Satellite Base Layers**: Instant toggling between high-resolution ESRI World Imagery, OpenStreetMap Humanitarian, CartoDB Dark Matter, and Topographic elevation.
- 🌾 **Interactive Agronomic Polygons**: Micro-zone vector boundaries detailing acreage, dominant cultivars, irrigation sources, and soil profiles.
- 📡 **Telemetry Station Overlay**: Live IoT field sensor nodes with interactive inspection popups displaying root-zone moisture, ambient temperature, and telemetry timestamps.
- ⚡ **Zero-Latency Rendering**: Ultra-responsive canvas and SVG map layers powered by Leaflet and Vite HMR (Hot Module Replacement).
- 🎛️ **Dual-Scope HUD Cockpit**: Sleek dark-mode heads-up display with one-touch toggle between regional Mandya and global breadbaskets.

---

## System Requirements

This project is built using standard web technologies and runs identically across all major operating systems.

- **Operating System**: Windows 10/11, macOS (Intel or Apple Silicon), or Linux (Ubuntu, Debian, Fedora, Arch, etc.).
- **Node.js**: Version `18.0.0` or higher (`20.x LTS` recommended).
- **Package Manager**: `npm` (bundled with Node.js), `pnpm`, or `yarn`.
- **Browser**: Any modern browser (Google Chrome, Mozilla Firefox, Microsoft Edge, Safari, Brave, Opera).

---

## Universal Installation Guide

### Step 0: Install Node.js (If Not Already Installed)

Verify if Node.js is already installed by opening your terminal or command prompt:

```bash
node -v
npm -v
```

If neither command is recognized, install Node.js for your operating system:

<details>
<summary><b>Windows Installation Instructions</b></summary>

- **Method A (winget - Recommended)**:
  Open PowerShell or Windows Terminal and run:
  ```powershell
  winget install OpenJS.NodeJS.LTS
  ```
  Restart your terminal after installation.

- **Method B (Official Installer)**:
  Download the LTS Windows Installer (`.msi`) from [nodejs.org](https://nodejs.org/) and follow the setup wizard.
</details>

<details>
<summary><b>macOS Installation Instructions</b></summary>

- **Method A (Homebrew - Recommended)**:
  Open Terminal and run:
  ```bash
  brew install node
  ```

- **Method B (Official Package)**:
  Download the macOS installer (`.pkg`) from [nodejs.org](https://nodejs.org/).
</details>

<details>
<summary><b>Linux Installation Instructions</b></summary>

- **Ubuntu / Debian**:
  ```bash
  curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
  sudo apt-get install -y nodejs
  ```

- **Fedora / RHEL**:
  ```bash
  sudo dnf install nodejs
  ```

- **Arch Linux**:
  ```bash
  sudo pacman -S nodejs npm
  ```

- **Using NVM (Node Version Manager - All Unix/macOS)**:
  ```bash
  curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.39.7/install.sh | bash
  source ~/.bashrc # or ~/.zshrc
  nvm install --lts
  nvm use --lts
  ```
</details>

---

### Step 1: Clone the Repository & Checkout Branch

Clone the repository and switch to the `frontend` branch:

```bash
git clone https://github.com/SamarthHK/Space-Apps-challenge.git
cd Space-Apps-challenge
git checkout frontend
```

*Or clone the branch directly in one step:*
```bash
git clone -b frontend https://github.com/SamarthHK/Space-Apps-challenge.git
cd Space-Apps-challenge
```

---

### Step 2: Install Dependencies

Inside the project directory, run:

```bash
npm install
```

*(Optional alternatives: `pnpm install` or `yarn install` if preferred).*

---

### Step 3: Run the Development Server

Start the local Vite development server:

```bash
npm run dev
```

Once running, the terminal will display the local URL:

```text
  VITE v5.4.11  ready in 240 ms

  ➜  Local:   http://localhost:5173/
  ➜  Network: use --host to expose
```

Open your browser and navigate to **[http://localhost:5173/](http://localhost:5173/)**. The map and HUD cockpit will load immediately.

---

### Step 4: Building for Production

To create an optimized, minified production build:

```bash
npm run build
```

The compiled assets will be output to the `dist/` folder. You can test the production build locally with:

```bash
npm run preview
```

---

## Project Directory Structure

```text
Space-Apps-challenge/ (branch: frontend)
├── index.html              # Main HTML entry point & HUD header template
├── package.json            # Project dependencies & npm scripts
├── package-lock.json       # Exact locked dependency tree
├── vite.config.js          # Vite build & dev-server configuration
├── .gitignore              # Git ignore rules for node_modules & build artifacts
├── README.md               # Project documentation & installation instructions
└── src/
    ├── main.js             # Main Leaflet map initialisation, layers, and HUD logic
    ├── style.css           # Custom dark-theme HUD styles and responsive CSS
    └── data/
        ├── mandyaData.js      # Mandya district taluk boundaries, crops & canal data
        ├── agriZones.js       # Global agricultural breadbasket coordinate datasets
        └── sensorStations.js  # Telemetric IoT soil & weather monitoring nodes
```

---

## Earth Observation & Datasets

| Dataset / Portal | Provider / Agency | Application in AeroAgri |
| :--- | :--- | :--- |
| **[ISRO Bhuvan](https://bhuvan.nrsc.gov.in/)** | NRSC / ISRO | Thematic LULC, FASAL crop acreage, and Kaveri basin irrigation canal network. |
| **[Sentinel-2 (Copernicus)](https://dataspace.copernicus.eu/)** | European Space Agency (ESA) | 10-meter multispectral optical imagery for NDVI & NDWI vegetation analysis. |
| **[KSNDMC](https://ksndmc.org/)** | Karnataka State Natural Disaster Monitoring Centre | Telemetric precipitation and agro-meteorological station records across Mandya. |
| **[ESRI World Imagery](https://www.arcgis.com/home/item.html?id=10df2279f9684e4a9f6a7f08febac2a9)** | ESRI / Maxar / Earthstar Geographics | Ultra-high-resolution aerial & satellite base map layer. |
| **[OpenStreetMap](https://www.openstreetmap.org/)** | OpenStreetMap Foundation | Cartographic road and administrative boundary reference layer. |

---

## Available Scripts

| Command | Description |
| :--- | :--- |
| `npm run dev` | Starts the Vite dev server with instant Hot Module Replacement (HMR) at `localhost:5173`. |
| `npm run build` | Compiles and tree-shakes the JavaScript and CSS into the production-ready `dist/` directory. |
| `npm run preview` | Spins up a local static server to preview the built `dist/` files prior to deployment. |

---

## Troubleshooting & FAQs

### Q: Port 5173 is already in use
**Solution**: Specify a different port when launching Vite:
```bash
npm run dev -- --port 3000
```
Or allow Vite to automatically increment to the next available port (`5174`).

### Q: PowerShell Execution Policy error on Windows
If you encounter `File ...\npm.ps1 cannot be loaded because running scripts is disabled`:
**Solution**: Run PowerShell as Administrator or bypass for the current session:
```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
npm run dev
```

### Q: Map tiles fail to load or appear gray
**Solution**: Check your internet connection. Leaflet fetches satellite tiles dynamically over HTTPS from ESRI, OpenStreetMap, and CartoDB tile servers. If behind a proxy, configure your proxy settings in npm and your browser.

---

## Contributing & License

Developed for the **NASA Space Apps Challenge**.
Released under the **MIT License**.
