# Financial Services Plugins 复用清单

- 来源仓库：anthropics/financial-services-plugins
- 同步时间：2026-02-25 11:06:39
- MCP Servers：12
- Skills：53
- Prompt 模板：47

## 产物路径

- VS Code MCP 配置：.vscode/mcp.json
- 复用技能目录：.github/skills/fsp-*
- 复用提示模板：.github/prompts/financial-services-plugins/*.prompt.md

## MCP Server 列表

| Name | Type | URL |
| --- | --- | --- |
| aiera | http | https://mcp-pub.aiera.com |
| chronograph | http | https://ai.chronograph.pe/mcp |
| daloopa | http | https://mcp.daloopa.com/server/mcp |
| egnyte | http | https://mcp-server.egnyte.com/mcp |
| factset | http | https://mcp.factset.com/mcp |
| lseg | http | https://api.analytics.lseg.com/lfa/mcp |
| lseg-partner-built | http | https://api.analytics.lseg.com/lfa/mcp/server-cl |
| moodys | http | https://api.moodys.com/genai-ready-data/m1/mcp |
| morningstar | http | https://mcp.morningstar.com/mcp |
| mtnewswire | http | https://vast-mcp.blueskyapi.com/mtnewswires |
| pitchbook | http | https://premium.mcp.pitchbook.com/mcp |
| sp-global | http | https://kfinance.kensho.com/integrations/mcp |

## 注意

- 多数金融数据端点需要各自供应商订阅与凭证。
- 请勿在 mcp.json 中硬编码密钥，优先使用 VS Code 输入变量或环境变量。
- 若上游插件更新，重新执行：python tools/sync_financial_plugins_reuse.py
