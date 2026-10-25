# SASES

**SASES** (Seed-Apollo Self-Evolving System) is a privacy-first, local-first AI self-evolving ecosystem.  
It combines autonomous seed iteration, credit systems, pollination mechanisms, contribution ranking, an extensible Harness runtime, AGI coordination, and distributed node services to create a personal AI service network.

> **One brain, many windows.**  
> SASES is designed to be lightweight, modular, and community-driven.

---

## ✨ Core Features

- **Seed Architecture**  
  Automatic generation, branching, synthesis, verification, backtracking, and knowledge accumulation.  
  Includes semantic deduplication for diverse seed generation.

- **Apollo Security Architecture**  
  Content safety scanning, tamper-proof state signatures, and risk control.

- **Root-Vein Architecture**  
  Multi-model routing, tool invocation, and future device I/O support.

- **Credit & Pollination System**  
  Earn credits by contributing seeds, manual pollination, or providing feedback. Credits are protected by HMAC state signatures.

- **Contribution Leaderboard**  
  A reputation-based ranking that rewards real contributions instead of simple credit accumulation.

- **Harness Runtime**  
  A modular runtime for mini-apps and tools. Developers can create Harness modules with a simple manifest and `run(params)` function.  
  Current examples: unit converter, calculator, text stats, JSON formatter, Base64 codec, string utils.

- **AGI Coordinator**  
  Accepts natural language tasks, selects the appropriate Harness tool via keyword matching or LLM reasoning, extracts parameters, and executes the task. Supports multimodal image input.

- **Space Service (Node as a Service)**  
  Register Harness modules and AGI services as discoverable space nodes. Supports local and remote invocation, reputation tracking, node synchronization, and mDNS-based local network discovery.

- **API Key Management**  
  Users can securely add, update, delete, and prioritize multiple API keys from different providers (DeepSeek, OpenAI, Moonshot, Zhipu, Qwen). Keys are encrypted at rest using Fernet encryption. The model router automatically selects the highest-priority active key and falls back to the system default if all user keys fail.

- **Unified SQLite Storage**  
  All persistent data (knowledge base, space nodes, seed pools, logs, user data, API keys) is stored in a single SQLite database for data integrity and transactional consistency.

---

## 🧱 Project Structure
sases/
├── app_full.py # Minimal FastAPI entry point
├── core/
│ ├── bootstrap.py # App creation, route registration, lifespan
│ ├── config.py # Exports grouped configuration
│ ├── config_models.py # Dataclass-based configuration groups
│ ├── db.py # Database initialization and connection
│ ├── auth_service.py # Authentication, credits, signatures, API keys
│ ├── knowledge_base.py # Knowledge base management
│ ├── contribution_log.py # Contribution logging and leaderboard
│ ├── seed_utils.py # Main utility facade (re-exports from utils)
│ ├── similarity.py # Semantic deduplication
│ ├── safety_scan.py # Content safety scanning
│ ├── encryption.py # Fernet encryption for API keys
│ ├── harness_loader.py # Scans and loads Harness modules
│ ├── harness_runtime.py # Harness runtime (tool listing/invocation)
│ ├── harness_models.py # Harness data models
│ ├── agi_coordinator.py # AGI task coordinator
│ ├── space_service.py # Space node service facade
│ ├── node_registry.py # Node registration and persistence
│ ├── sync_manager.py # Peer synchronization
│ ├── health_checker.py # Node health checks
│ ├── discovery.py # mDNS node discovery
│ ├── seed_store.py # Seed pool storage
│ ├── utils/
│ │ ├── code_utils.py # Code parsing/cleaning
│ │ ├── sandbox.py # Safe code execution
│ │ └── api_utils.py # API calling helpers
│ └── api_routes/
│ ├── auth_routes.py
│ ├── seed_routes.py
│ ├── credit_routes.py
│ ├── harness_routes.py
│ ├── agi_routes.py
│ └── space_routes.py
├── harness_modules/
│ ├── unit_converter/
│ ├── calculator/
│ ├── text_stats/
│ ├── json_formatter/
│ ├── base64_codec/
│ └── string_utils/
├── tests/ # 68 unit & integration tests
└── static/
├── index.html
├── style.css
├── favicon.svg
└── modules/
├── main.js
├── utils.js
├── auth.js
├── chat.js
├── contacts.js
├── discover.js
└── me.js

text

---

## 🚀 Quick Start

### 1. Install dependencies

```bash
pip install fastapi uvicorn openai chromadb rank_bm25 passlib[bcrypt] python-jose[cryptography] python-multipart scikit-learn httpx python-dotenv cryptography zeroconf
2. Configure environment variables
Create a .env file or set the following variables:

text
DEEPSEEK_API_KEY=your_deepseek_api_key
SASES_SECRET_KEY=your_jwt_secret
Optional:

text
MODEL_NAME=deepseek-v4-flash
SASES_PORT=8001
SASES_NODE_ID=node-001
SASES_NODE_NAME=My SASES Node
SASES_PEERS=http://other-node:8001
SASES_NODE_TOKEN=change-me
SASES_ENABLE_MDNS=true
3. Start the web service
bash
python -m uvicorn app_full:app --reload --port 8001
Visit http://127.0.0.1:8001/static/index.html to open the console.

🧪 Run Tests
bash
python -m pytest tests/ -v
All 68 unit tests should pass.

🎯 Current Status
Seed iteration loop with semantic deduplication

External seed submission and processing

Credit system with HMAC tamper detection

Pollination mechanism (manual and auto)

Contribution leaderboard

Harness runtime with six example modules

AGI coordinator with keyword matching, parameter extraction, and multimodal image support

Space service with node registration, remote invocation, peer synchronization, health checks, and mDNS discovery

API key management with encryption and multi-provider routing

Unified SQLite storage

Modular web frontend with WeChat-style bottom navigation

📜 License
This project is licensed under the Apache License 2.0.

🤝 Contributing
Contributions are welcome! Please read CONTRIBUTING.md before submitting a pull request.

📬 Contact
GitHub: SASESseed/sases

Hugging Face: BlossomArchitecture