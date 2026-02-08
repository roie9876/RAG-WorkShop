# Module 0 – Environment Setup (Zero to Ready)

## 🎯 Objective
Get participants to a working environment with minimal friction.

## Learning Outcomes
By the end of this module, participants will be able to:
- Deploy all required Azure resources using a one-click Bicep template
- Configure environment variables for the workshop
- Validate their setup with a health-check notebook
- Troubleshoot common setup issues

---

## 🚀 Quick Start

### Prerequisites
- Azure subscription (Owner or Contributor access)
- Python 3.11+
- VS Code with extensions:
  - [Python](https://marketplace.visualstudio.com/items?itemName=ms-python.python)
  - [Jupyter](https://marketplace.visualstudio.com/items?itemName=ms-toolsai.jupyter)
- Git

### Step 1: Clone the Repository
```bash
git clone https://github.com/roie9876/RAG-WorkShop.git
cd RAG-WorkShop
```

### Step 2: Install Python Dependencies
```bash
pip install -r requirements.txt
```

### Step 3: Setup Azure Resources & Validate

**Option A: Interactive Notebooks (Recommended for beginners)**

Open the interactive notebooks in this module:

1. **`setup.ipynb`** - Deploy Azure resources and configure environment
2. **`health-check.ipynb`** - Validate all connections

**Option B: Command Line (For advanced users)**

Run the deployment script directly from terminal:

```bash
cd infra

# Default deployment (region: swedencentral)
./deploy.sh

# Or customize with environment variables
RESOURCE_GROUP="my-rag-rg" LOCATION="westeurope" ./deploy.sh
```

The script will:
1. ✅ Check Azure CLI login (prompts `az login` if needed)
2. ✅ Create resource group
3. ✅ Deploy all Azure resources via Bicep
4. ✅ Generate `.env` file with all connection strings

> ⚠️ **Requires**: Azure CLI installed (`az --version`)

---

## 📁 Project Structure

```
RAG-WorkShop/
├── modules/                    # Workshop modules
│   ├── module-0-setup/         # Azure setup & validation ← YOU ARE HERE
│   ├── module-1-naive-rag/     # See RAG fail (motivation)
│   ├── module-2-doc-intelligence/  # Extract content
│   ├── module-3-content-understanding/  # Semantic extraction
│   ├── module-4-chunking/      # Chunking strategies
│   ├── module-5-search/        # Embeddings & search
│   ├── module-6-graphrag/      # Graph reasoning
│   └── module-7-pipeline/      # Full production pipeline
├── data/                       # Sample documents
│   ├── sample-pdfs/            # Metro station PDFs
│   └── sample-office/          # Word, Excel, PowerPoint
├── src/                        # Shared Python utilities
├── infra/                      # Azure deployment (Bicep)
└── requirements.txt            # Python dependencies
```

---

## ☁️ Azure Resources Deployed

### 🌍 Recommended Region: `swedencentral`

All required services are available in this region with full feature support, including **Content Understanding** (GA API `2025-11-01`).

| Resource | Purpose |
|----------|---------|
| Azure OpenAI | GPT-4.1, GPT-4.1-mini, text-embedding-3-large |
| Azure AI Search | Vector + semantic search |
| Azure AI Services | Document Intelligence + Content Understanding |
| Azure AI Foundry | Hub + Project for agent orchestration |
| Storage Account | Document and figure storage |

## ⏱️ Estimated Time
- Deployment: 10-15 minutes
- Configuration: 5 minutes
- Validation: 5 minutes
- **Total: ~20 minutes**

## 📂 Files in This Module
| File | Description |
|------|-------------|
| `setup.ipynb` | Interactive setup wizard - deploys Azure resources |
| `health-check.ipynb` | Validates all connections work |
| `cleanup.ipynb` | Remove resources when done (optional) |

## 🔧 Troubleshooting
Common issues and solutions are documented in the notebooks.

---

## Navigation

**Previous**: [Workshop Home](../../README.md)  
**Next**: [Module 1 – The Problem with Naive RAG](../module-1-naive-rag/README.md)
