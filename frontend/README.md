# doThis Frontend

Next.js App Router UI for doThis.

## Setup
```bash
cd frontend
npm install
```

Create a frontend/.env.local file:
```
NEXT_PUBLIC_API_URL=http://localhost:8000
```

Start the dev server:
```bash
npm run dev
```

Open http://localhost:3000 in your browser.

## Scripts
```bash
npm run dev
npm run build
npm run start
npm run lint
```

## Notes
- The backend must be running for /api/analyze requests.
- UI reads results from localStorage and renders the analysis screen.
