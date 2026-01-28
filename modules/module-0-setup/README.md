# Module 0 – Environment Setup (Zero to Ready)

## Objective
Get participants to a working environment with minimal friction.

## Learning Outcomes
By the end of this module, participants will be able to:
- Deploy all required Azure resources using a one-click Bicep template
- Configure environment variables for the workshop
- Validate their setup with a health-check notebook
- Troubleshoot common setup issues

## Prerequisites
- Azure subscription with Owner or Contributor role
- VS Code with Python extension installed
- Python 3.11+ installed locally
- Git installed

## Topics Covered
1. Azure resource deployment (Bicep)
2. Environment variable configuration
3. SDK installation and verification
4. Connection testing for all services

## Azure Resources Deployed
| Resource | Purpose |
|----------|---------|
| Azure OpenAI | GPT-4.1, GPT-4.1-mini, text-embedding-3-large |
| Azure AI Search | Vector + semantic search |
| Azure AI Services | Document Intelligence + Content Understanding |
| Azure AI Foundry | Hub + Project for agent orchestration |
| Storage Account | Document and figure storage |

## Estimated Time
- Deployment: 10-15 minutes
- Configuration: 5 minutes
- Validation: 5 minutes
- **Total: ~20 minutes**

## Files in This Module
| File | Description |
|------|-------------|
| `setup.ipynb` | Interactive setup wizard |
| `health-check.ipynb` | Validate all connections |

## Quick Start
1. Open `setup.ipynb`
2. Follow the interactive prompts
3. Run `health-check.ipynb` to verify

## Troubleshooting
Common issues and solutions will be documented in the notebooks.

---

**Next Module**: [Module 1 – The Problem with Naive RAG](../module-1-naive-rag/README.md)
