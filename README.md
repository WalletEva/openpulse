# OpenPulse

一个轻量化、跨平台、Agent-Native 的开源信息搜集聚合平台。

## 特性

- **Agent-Native**：内置 MCP Server，无缝对接 Hermes Agent、OpenClaw 等 AI 智能体
- **多源聚合**：支持 RSSHub（数百个国内外媒体源）、NewsAPI、GDELT、X/Twitter、YouTube 等
- **定时采集**：内置 APScheduler，支持 cron 定时和手动即时采集
- **双模存储**：SQLite（本地轻量）/ PostgreSQL（服务器扩展），通过 ORM 无缝切换
- **CLI + REST API + MCP**：三种接入方式，满足脚本、自动化、Agent 调用需求
- **跨平台部署**：Windows / Linux 均支持，Docker 一键部署

## 快速开始

### 安装

```bash
pip install openpulse
```

### 初始化

```bash
openpulse init
```

### 启动服务

```bash
openpulse serve
```

### 采集示例

```bash
# 立即采集路透社新闻
openpulse collect --source reuters --now

# 搜索 AI 相关文章
openpulse search "AI regulation" --lang en --limit 50
```

### Agent 接入（Hermes / OpenClaw）

在 Agent 的 MCP 配置中添加：

```yaml
# Hermes config.yaml
mcp:
  servers:
    - name: openpulse
      command: python
      args: ["-m", "openpulse.mcp_server"]
```

```json
// OpenClaw openclaw.json
{
  "mcp": {
    "servers": [
      {
        "name": "openpulse",
        "command": "python",
        "args": ["-m", "openpulse.mcp_server"]
      }
    ]
  }
}
```

## 开发

```bash
# 克隆仓库
git clone https://github.com/openpulse/openpulse.git
cd openpulse

# 安装开发依赖
pip install -e ".[dev]"

# 运行测试
pytest

# 代码检查
ruff check src/
```

## 部署

### Docker（本地）

```bash
docker run -v ~/.openpulse:/data -p 8000:8000 openpulse/openpulse:latest
```

### Docker Compose（服务器）

```yaml
services:
  openpulse:
    image: openpulse/openpulse:latest
    ports: ["8000:8000"]
    volumes: ["./data:/data"]
    environment:
      DATABASE_URL: postgresql://user:pass@postgres:5432/openpulse
    depends_on: [postgres, rsshub]

  postgres:
    image: postgres:16-alpine
    volumes: ["pgdata:/var/lib/postgresql/data"]
    environment:
      POSTGRES_DB: openpulse
      POSTGRES_USER: user
      POSTGRES_PASSWORD: pass

  rsshub:
    image: diygod/rsshub
    ports: ["1200:1200"]

volumes:
  pgdata:
```

## 文档

- [安装指南](docs/installation.md)
- [配置说明](docs/configuration.md)
- [API 参考](docs/api-reference.md)
- [Agent 集成](docs/agent-integration.md)
- [部署指南](docs/deployment.md)

## 许可证

MIT License
