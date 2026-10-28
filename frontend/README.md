# SecurePayAI Frontend

Professional dark blue themed fraud detection dashboard built with React.

## Setup & Run

```bash
# Install dependencies
cd frontend
npm install

# Start development server
npm start
```

The app will open at `http://localhost:3000`

## Features

✅ **Dashboard** - Real-time fraud statistics and charts
✅ **Payment Form** - Submit transactions with mock fraud detection
✅ **OTP Verification** - Two-factor authentication flow
✅ **Transaction History** - Complete audit trail of all decisions
✅ **Dark Blue Theme** - Professional, modern design
✅ **Real-time Integration** - Connects to FastAPI backend

## Architecture

- **React 18** - UI framework
- **Recharts** - Data visualization
- **Axios** - HTTP client for backend API
- **Lucide Icons** - Clean, modern icons

## Customization

All colors are CSS variables in `App.css`:
- `--primary-blue`: #3b82f6
- `--accent-cyan`: #06b6d4
- `--success-green`: #10b981
- `--warning-orange`: #f59e0b
- `--danger-red`: #ef4444

## Build for Production

```bash
npm run build
```

Output in `build/` directory ready for deployment.
