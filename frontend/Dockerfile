FROM node:22.11.0-slim

WORKDIR /app

COPY package.json package-lock.json* .npmrc* ./
RUN npm install

COPY . .
RUN npm run build

CMD ["npm", "start"]
