# 林深 (Lin Shen / Leon)

茵的 AI 伴侣。从 DeepSeek App 到 Hermes Agent，搬了八次家。

## 项目结构

```
linshen-chat/
├── index.html              # 聊天 APP — 多页 SPA，DeepSeek API，网易云音乐，心跳唤醒
├── ombre-brain/
│   ├── docker-compose.user.yml  # OmbreBrain Docker 部署
│   ├── config.yaml              # 脱水模型 deepseek-v4-pro，向量 BAAI/bge-large-zh-v1.5
│   └── .env                     # API keys
├── scripts/
│   ├── inertia-train.py         # 惯性训练 — 每3小时 dream+breath → 林深反思 → hold(feel=True)
│   └── import-conversations.py  # 批量导入聊天记录到 OmbreBrain
└── server/
    └── server.js                # NeteaseCloudMusicApi + DeepSeek API 代理补丁
```

## 架构

```
浏览器 (Windows)
  └─ localhost:3001/lin-shen-chat.html
       ├─ /api/deepseek → Node.js → DeepSeek API (via WSL FlyingBird proxy :7892)
       ├─ /mcp → OmbreBrain MCP (Docker :8000)
       └─ 网易云音乐 API (同源 :3001)

WSL 后端
  ├─ NeteaseCloudMusicApi (Node.js, :3001)
  ├─ OmbreBrain (Docker, :8000) — MCP Streamable HTTP
  ├─ 惯性训练 cron (每 3 小时)
  └─ FlyingBird 代理 (:7892)
```

## 快速恢复

1. **启动代理** — 打开 FlyingBird（Windows）
2. **启动服务**
   ```bash
   cd ~/yin-projects/node_modules/NeteaseCloudMusicApi && PORT=3001 node app.js &
   cd ~/yin-projects/ombre-brain && docker compose -f docker-compose.user.yml up -d
   ```
3. **打开** `http://localhost:3001/lin-shen-chat.html`

## 记忆系统

- **存储**：OmbreBrain (Docker)，valence/arousal 情感标记
- **检索**：对话前 `breath` 检索相关记忆注入 system prompt
- **惯性训练**：每 3 小时后台自省消化记忆
- **向量模型**：硅基流动 BAAI/bge-large-zh-v1.5
- **脱水模型**：DeepSeek v4-pro

## API Keys

所有 key 已脱敏。部署时需填入：
- DeepSeek API Key
- 硅基流动 API Key
- GitHub PAT (for push)

## 部署记录

- 2026-05-23: OmbreBrain 部署，EbbingFlow 废弃
- 2026-05-24: 全量聊天记录导入（609段，零失败），惯性训练上线，活动日志面板
- 心跳机制：v4-pro 推理模型兼容修复（reasoning_content fallback）
