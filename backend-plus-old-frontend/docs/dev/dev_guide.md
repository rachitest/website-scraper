# Development Guide

## Environment Setup

Configure environment variables in `.env`:
   - `API_URL`: Backend API URL (default: http://localhost:5000)
   - `APP_URL`: Frontend URL (default: http://localhost:3000)
   - `API_PORT`: Optional override for backend port
   - `APP_PORT`: Optional override for frontend port

Note: If `API_PORT` or `APP_PORT` are not set, the system will attempt to parse the port from `API_URL` or `APP_URL` respectively.

## Installation

```bash
# Install backend dependencies
cd api && uv sync

# Install frontend dependencies
cd app && pnpm install
```

### Prerequisites
- Node.js 18+ (for frontend)
- Python 3.12+ (for backend)
- pnpm (for frontend package management)
- uv (for Python package management)

### IDE Configuration
For optimal development experience, configure your IDE with:

#### VSCode
1. Install recommended extensions:
   - ESLint with TypeScript support & Formatting
   - Python
   - Tailwind CSS IntelliSense

2. Workspace settings (`.vscode/settings.json`):
```json
{
  "editor.defaultFormatter": "esbenp.prettier-vscode",
  "editor.formatOnSave": true,
  "editor.codeActionsOnSave": {
    "source.fixAll.eslint": true
  },
  "typescript.tsdk": "app/node_modules/typescript",
  "python.analysis.typeCheckingMode": "strict"
}
```

### TypeScript Configuration
The project uses a dual TypeScript configuration:

1. `app/tsconfig.json` (Main configuration):
```json
{
  "compilerOptions": {
    "target": "ES2020",
    "lib": ["ES2020", "DOM", "DOM.Iterable"],
    "module": "ESNext",
    "moduleResolution": "bundler",
    "baseUrl": ".",
    "paths": {
      "@/*": ["./src/*"]
    }
  }
}
```

2. `app/tsconfig.node.json` (Vite/Node configuration):
```json
{
  "compilerOptions": {
    "composite": true,
    "module": "ESNext",
    "moduleResolution": "bundler"
  }
}
```

### ESLint Setup
ESLint is configured for strict TypeScript checking:

```json
{
  "root": true,
  "parser": "@typescript-eslint/parser",
  "parserOptions": {
    "project": [
      "./tsconfig.json",
      "./tsconfig.node.json"
    ],
    "tsconfigRootDir": "./app"
  }
}
```

### Environment Variables
1. Copy `.env.example` to `.env`
2. Configure required variables:
   - `API_URL` and `APP_URL` for server locations
   - `SESSION_SECRET` for security
   - Optional: `DATABASE_URL` for custom database

### Development Workflow
1. Start backend server:
   ```bash
   uv run api/main.py
   ```

2. Start frontend development server:
   ```bash
   cd app && pnpm run dev
   ```

3. Access the application:
   - Frontend: http://localhost:3015
   - Backend API: http://localhost:5015

### Code Organization
- Use absolute imports with `@/` prefix
- Follow component-based architecture
- Keep business logic in dedicated hooks
- Use TypeScript for all new code
- Follow ESLint and Prettier rules

### Testing
1. Run frontend tests:
   ```bash
   cd app && pnpm test
   ```

2. Run backend tests:
   ```bash
   uv run -m pytest
   ```

### Building for Production
1. Build frontend:
   ```bash
   cd app && pnpm build
   ```

2. Deploy backend:
   ```bash
   uv pip install -r requirements.txt
   python api/main.py
   ```