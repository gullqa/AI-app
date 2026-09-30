# Intel Analyst · 专业领域情报分析工具

按"领域包"（默认内置碳中和三条主线：政策与气候治理 / 碳市场与碳资产 / 减碳技术与能源转型，可自行扩展）定时采集公开信息 → 相关性打分去重 →
Claude 按分析师角色与框架出**带来源引用、区分事实与判断**的简报 → 推送到飞书 / 企业微信；
飞书里还能直接 @机器人 基于情报库问答。可在任意云服务器 Docker 运行。

```
数据源(RSS/arXiv) → 关键词打分+去重(SQLite) → Claude 分析 → 飞书卡片 / 企微 markdown
                                              ↘ /ask、飞书对话问答
```

## 快速开始
```bash
cd intel-analyst && cp .env.example .env   # 填 ANTHROPIC_API_KEY 等
pip install -r requirements.txt
python -m intel.cli domains
python -m intel.cli run carbon_market            # 只生成，不推送
python -m intel.cli run carbon_market --send     # 生成并推送
python -m intel.cli ask carbon_market "EU ETS 碳价近期为什么波动"
python -m pytest
```
不配置 `ANTHROPIC_API_KEY` 时退化为离线关键词速览，便于先调数据源。

## 云服务器部署
```bash
docker compose up -d --build     # 服务在 :8000，定时任务随服务启动，数据在 ./data
```
API（需请求头 `X-Token: $INTEL_API_TOKEN`）：`POST /run/{domain}?send=true`、`GET /briefing/{domain}`、`POST /ask {"q": "..."}`。
`/health` 无需鉴权。生产环境请放在 HTTPS 反代（Caddy/Nginx）之后。

## 接入飞书
1. **仅推送**：群 → 设置 → 群机器人 → 自定义机器人，把 webhook 填入 `FEISHU_WEBHOOK`（若开启签名校验，填 `FEISHU_WEBHOOK_SECRET`）。
2. **对话问答**：开放平台建自建应用 → 开启机器人能力 → 权限加 `im:message`、`im:message:send_as_bot` →
   事件订阅请求地址填 `https://你的域名/feishu/event`，订阅 `im.message.receive_v1`，
   把 App ID / Secret / Verification Token 填进 `.env`（**Encrypt Key 需留空**，暂未实现加密事件）。
   群里 @机器人 或私聊：`/域`、`/简报 carbon_market`、`/刷新 carbon_market`、`carbon_market CCER 重启有什么进展？`

## 接入微信
- **企业微信群机器人**（推荐，官方支持）：群 → 添加群机器人，webhook 填 `WECOM_WEBHOOK`，自动分段推送。
- 个人微信无官方机器人接口，第三方协议方案有封号风险，故未内置；如需双向对话，
  可用企业微信"自建应用"回调（需实现消息加解密），`intel/chat.py` 的 `handle()` 已与渠道解耦，直接复用。

## 新增一个领域
在 `config/domains.yaml` 复制一段：改 `keywords`（关键词: 权重）、`sources`（`rss` 或 `arxiv`）、
`analyst_role`、`framework`、`schedule`（cron）、`channels`。无需改代码。

## 注意
- 简报只依据入库条目，结论带 `[编号]` 引用；仍应对关键结论回看原文。
- 抓取请遵守各站点条款；付费/需登录来源请用官方 API 或订阅 RSS。
- 相关度目前是关键词加权，是最容易升级的环节（如换 embedding 检索）。
