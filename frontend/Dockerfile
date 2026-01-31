# Frontend Dockerfile - Vite React TypeScript
FROM node:20-alpine

WORKDIR /app

# Copy package files first for better caching
COPY package.json package-lock.json* ./

# Install dependencies
RUN npm install

# Copy source code
COPY . .

# Expose Vite dev server port
EXPOSE 5173

# Run Vite dev server (host: 0.0.0.0 is configured in vite.config.ts)
CMD ["npm", "run", "dev"]
