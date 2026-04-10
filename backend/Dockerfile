# Stage 1: Node.js for Claude Code CLI
FROM node:20-slim AS node-base

# Install Claude Code CLI globally
RUN npm install -g @anthropic-ai/claude-code

# Stage 2: Python app + Node runtime
FROM python:3.12-slim

# Install Node.js runtime (needed for Claude CLI)
COPY --from=node-base /usr/local/bin/node /usr/local/bin/node
COPY --from=node-base /usr/local/lib/node_modules /usr/local/lib/node_modules
COPY --from=node-base /usr/local/bin/npx /usr/local/bin/npx

# Symlink claude CLI
RUN ln -s /usr/local/lib/node_modules/@anthropic-ai/claude-code/cli.js /usr/local/bin/claude && \
    chmod +x /usr/local/bin/claude

WORKDIR /app

# Python deps
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Playwright browser for itch.io posting
RUN playwright install chromium && playwright install-deps chromium

# App code
COPY . .

# SQLite data directory (mount as volume for persistence)
RUN mkdir -p /app/data
ENV DATABASE_URL=sqlite+aiosqlite:///./data/mina_agent.db

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
