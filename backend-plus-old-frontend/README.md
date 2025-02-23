# Website Scraper v0.0.1 - Experimental

You can experiment with the deployed version of this app at [https://webentityscraper.iocloudhost.net/](https://webentityscraper.iocloudhost.net/).

A modern, full-stack web application with type safe JavaScript frontend and Python backend.

## Quick Start

1. Setup local environment variables:
```bash
cp .env.example .env
```

2. Install dependencies:
```bash
# Backend (using uv package manager)
cd api && uv sync

# Frontend (using pnpm)
cd app && pnpm install
```

3. Start the servers:
```bash
# Terminal 1: Start backend (default: http://localhost:5015)
uv run api/main.py

# Terminal 2: Start frontend (default: http://localhost:3015)
cd app && pnpm run dev
```

## Tech Stack

### Backend (Python)
- **Flask**: Web framework with factory pattern setup
- **SQLAlchemy**: ORM with connection pooling
- **uv**: Fast Python package installer and resolver
- **CORS**: Cross-Origin Resource Sharing support
- **python-dotenv**: Environment variable management

### Frontend (TypeScript)
- **React 18**: UI library with hooks
- **Vite**: Build tool and dev server
- **TypeScript**: Static typing
- **TailwindCSS**: Utility-first CSS
- **ESLint**: Linting with strict TypeScript rules
- **pnpm**: Fast, disk space efficient package manager

## Configuration Files

### Backend
- `api/main.py`: Application factory and server setup
- `api/__init__.py`: Core initialization and database setup
- `.env`: Environment variables (from .env.example template)

### Frontend
- `app/vite.config.ts`: Vite configuration with env and proxy setup
- `app/tsconfig.json`: TypeScript configuration for app
- `app/tsconfig.node.json`: TypeScript configuration for Vite
- `app/.eslintrc.json`: ESLint configuration with TypeScript support

## Environment Variables

```bash
# Application URLs and Ports
API_URL=http://localhost:5015    # Backend URL
APP_URL=http://localhost:3015    # Frontend URL
# API_PORT=5015                  # Optional: Override API port
# APP_PORT=3015                  # Optional: Override APP port

# Security
SESSION_SECRET=your_secret_here  # Session encryption key

# Database (Optional)
# DATABASE_URL=your_db_url       # Default: SQLite
```

## Development Tools

### ESLint Configuration
The project uses a strict TypeScript-enabled ESLint configuration:
- TypeScript parser with project references
- React and React Hooks plugins
- Strict type checking rules

Key files:
```
app/
├── .eslintrc.json     # ESLint config
├── tsconfig.json      # Main TS config
└── tsconfig.node.json # Vite/Node TS config
```

### Environment Configuration
- Uses `.env` for environment variables
- Vite loads variables from parent directory
- Both frontend and backend share the same env file
- Automatic port detection from URLs

## Available Endpoints

Backend (default: http://localhost:5015):
- `/api/health` - Health check endpoint
- `/api/v1/*` - REST API endpoints
- `/trpc/*` - tRPC endpoints
- `/graphql` - GraphQL endpoint

Frontend (default: http://localhost:3015):
- Main application interface
- Dark/light mode toggle
- Responsive design

## Documentation

- [API Documentation](docs/api.md) - Backend API endpoints and usage
- [Frontend Guide](docs/frontend.md) - Frontend architecture and components
- [Integration Guide](docs/integration.md) - Frontend-Backend integration guide
- [Development Guide](docs/dev_guide.md) - Development workflow and best practices
- [Repository Rules](docs/repo_rules.md) - Code organization and type safety

## Project Structure

```
.
├── api/                 # Backend Python application
│   ├── __init__.py     # Core initialization
│   ├── main.py         # Application factory
│   ├── routes/         # API endpoints
│   └── utils/          # Helper functions
├── app/                # Frontend React application
│   ├── src/            # Source code
│   ├── public/         # Static files
│   └── vite.config.ts  # Vite configuration
├── docs/               # Documentation
├── .env.example        # Environment template
└── README.md          # This file