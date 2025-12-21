FROM node:22-slim

WORKDIR /app

# Install git and other potential build dependencies if needed
# Debian-based images generally cover most needs, but sometimes git is needed for deps
RUN apt-get update && apt-get install -y git && rm -rf /var/lib/apt/lists/*

COPY package.json package-lock.json ./

# Force a clean install and rebuild of native modules
RUN npm install

COPY . .

# Build the application
RUN npm run build

# Expose port
EXPOSE 3000

# Set environment variables
ENV HOST=0.0.0.0
ENV PORT=3000

# Run the application
CMD ["node", ".output/server/index.mjs"]
