# SvelteKit + Tailwind Web App Dockerfile
FROM node:22-alpine

# Set working directory
WORKDIR /app

# Install dependencies (will be overwritten by bind mount in dev, but needed for build)
COPY package.json package-lock.json* ./
RUN npm install

# Copy the rest of the app
COPY . .

# Build for production
RUN npm run build

# Expose port for SvelteKit (default 5173)
EXPOSE 5173

# Start the app (production)
CMD ["npm", "run", "preview", "--", "--host"]
