FROM node:22-slim

WORKDIR /app

COPY package.json package-lock.json* ./

RUN npm ci

COPY . .

EXPOSE 5173

# Vite dev server — bind to 0.0.0.0 so it's reachable from the host
CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0"]
