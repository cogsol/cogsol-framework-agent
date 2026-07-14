# Cogsol Framework Agent

## Setup

- Install CogSol Framework from: https://github.com/Pyxis-Cognitive-Solutions/cogsol-framework
  Verify with `cogsol-admin` — it should print the list of available commands.
- Configure credentials by running `cogsol-admin credentials-setup`. This is interactive:
  it asks for `client_id`, `client_secret` and `tenant_api_key`, saves them at the user
  level, and checks connectivity against the CogSol API. If you don't have tenant
  credentials yet, get them at https://onboarding.cogsol.ai.
  - `.env` / `.env.example` are **not** the primary credential mechanism — they only hold
    optional project-level overrides (`COGSOL_API_KEY`, `COGSOL_AUTH_CLIENT_ID`,
    `COGSOL_AUTH_SECRET`). Most projects don't need a `.env` file at all.
- Migrate data app first: `python manage.py migrate data`.
- Migrate agents app next: `python manage.py migrate`.
- Ingest documents for Cogsol Framework Docs topic:

  `python manage.py ingest "Cogsol Framework Docs" ./data/CogsolFrameworkDocs --pattern "*.txt" --ingestion-config CogsolFrameworkIngestionConfig`

- Ingest documents for Content API Models topic:

  `python manage.py ingest "Cogsol APIs Docs\Cognitive API Models" ./data/CogsolAPIsDocs/CognitiveModels --pattern "*.txt" --chunking "langchain"`

- Ingest documents for Cognitive API Models topic:

  `python manage.py ingest "Cogsol APIs Docs\Content API Models" ./data/CogsolAPIsDocs/ContentModels --pattern "*.txt" --chunking "langchain"`

- Ingest documents for Cogsol APIs Docs topic:

  `python manage.py ingest "Cogsol APIs Docs" ./data/CogsolAPIsDocs/cognitive.txt --chunking "langchain"`

  `python manage.py ingest "Cogsol APIs Docs" ./data/CogsolAPIsDocs/content.txt --chunking "langchain"`

## Running the Agent

- Start chat with the agent: `python manage.py chat --agent CogsolFrameworkAgent`.

## MCP Server

- Install MCP support: `python -m pip install mcp`.
- Run the server over stdio: `python mcp_server.py`.
- Tool available: `ask_cogsol_framework` with params `question` and optional `reset`.
- Example MCP config (for clients that accept JSON server definitions):

```json
{
  "mcpServers": {
    "cogsol-framework": {
      "command": "python",
      "args": ["mcp_server.py"],
      "cwd": "c:\\CogSol\\AgentesPrueba\\cogsol-framework-agent"
    }
  }
}
```
