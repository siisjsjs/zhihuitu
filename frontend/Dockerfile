FROM node:22-alpine AS build

# 国内构建慢时：docker compose build --build-arg USE_CN_MIRROR=1 frontend
ARG USE_CN_MIRROR=0

WORKDIR /app/frontend

COPY frontend/package*.json ./
RUN if [ "$USE_CN_MIRROR" = "1" ]; then npm config set registry https://registry.npmmirror.com; fi \
    && npm ci

COPY frontend .
COPY chart-templates /app/chart-templates

RUN npm run build

FROM nginx:1.27-alpine

COPY deploy/nginx/default.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/frontend/dist /usr/share/nginx/html

EXPOSE 80
