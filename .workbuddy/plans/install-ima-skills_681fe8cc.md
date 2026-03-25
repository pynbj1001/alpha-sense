---
name: install-ima-skills
overview: 从 https://app-dl.ima.qq.com/skills/ima-skills-1.0.5.zip 下载 ima 技能包并解压到 skills/ 目录下
todos:
  - id: download-zip
    content: 下载 ima-skills-1.0.5.zip 到临时目录
    status: completed
  - id: extract-to-skills
    content: 解压 zip 包到 skills/ 目录生成 ima-note/ 子目录
    status: completed
    dependencies:
      - download-zip
  - id: verify-installation
    content: 验证 SKILL.md 存在及安装完整性
    status: completed
    dependencies:
      - extract-to-skills
  - id: update-lock-file
    content: 更新 skills-lock.json 记录 ima-note 技能来源
    status: completed
    dependencies:
      - verify-installation
  - id: cleanup-and-notify
    content: 清理临时文件并提醒用户配置 API Key
    status: completed
    dependencies:
      - update-lock-file
---

## Product Overview

安装腾讯 ima（im.qq.com）AI 技能包到现有投资研究框架的 `skills/` 目录下。

## Core Features

- 从指定下载地址获取 ima-skills-1.0.5.zip 压缩包
- 解压到 `skills/` 目录，生成 `skills/ima-note/` 子目录（包含 SKILL.md、references/api.md 等）
- 验证安装完整性（SKILL.md 存在且格式正确）
- 更新 `skills-lock.json` 记录外部技能来源信息
- 提醒用户配置 API Key（获取地址：https://ima.qq.com/agent-interface）

## Tech Stack

- **下载工具**: curl（Windows PowerShell 内置 Invoke-WebRequest 备选）
- **解压工具**: PowerShell Expand-Archive
- **文件操作**: PowerShell 原生命令

## Implementation Details

### 安装步骤

1. 下载 zip 包到临时目录（`$env:TEMP\ima-skills-1.0.5.zip`）
2. 解压 zip 包内容到 `skills/` 目录（解压后得到 `skills/ima-note/` 子目录）
3. 验证 `skills/ima-note/SKILL.md` 文件存在
4. 更新 `skills-lock.json`，添加 ima-note 条目（sourceType: "url", source: 下载地址, version: "1.0.5"）
5. 清理临时 zip 文件

### 目录结构变更

```
skills/
├── ima-note/          # [NEW] ima AI 技能包（从 zip 解压）
│   ├── SKILL.md       # 技能定义文件
│   └── references/    # 参考资料（含 api.md 等）
skills-lock.json       # [MODIFY] 添加 ima-note 外部技能记录
```

### Blast radius control

- 仅新增 `skills/ima-note/` 目录，不修改任何现有技能
- 仅追加 `skills-lock.json` 中的 skills 条目，不删除现有 tushare 记录
- 不修改 AGENTS.md 或投研路由，ima 技能独立存在

## Agent Extensions

### Skill

- **browser-automation**
- Purpose: 在需要时打开 API Key 获取页面，辅助用户完成配置
- Expected outcome: 用户成功获取并配置 ima API Key