# Frontend Dockerfile for Agent Arena
# RunPod style UI with Vue 3 + Vite

FROM node:20-alpine AS build

WORKDIR /app

# NOTE: translated comment in English.
ARG VITE_API_BASE_URL=http://localhost:8000
ARG VITE_SKILL_VIEW_URL=
ENV VITE_API_BASE_URL=$VITE_API_BASE_URL
ENV VITE_SKILL_VIEW_URL=$VITE_SKILL_VIEW_URL
# NOTE: translated comment in English.
ENV NODE_OPTIONS=--max-old-space-size=2048

# Install dependencies
COPY package*.json ./
RUN npm install

# Copy source code
COPY . .

# Build production version
RUN npm run build

# Production stage
FROM nginx:alpine AS production

# Copy built files
COPY --from=build /app/dist /usr/share/nginx/html

# Copy nginx configuration
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Expose port
EXPOSE 80

# Start nginx
CMD ["nginx", "-g", "daemon off;"]