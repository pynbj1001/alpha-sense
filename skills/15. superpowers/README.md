# Superpowers — 技能库（本地归档版）

> 源仓库：https://github.com/obra/superpowers  
> 归档日期：2026-02-26  
> 版本：v4.3.1+（基于网页读取归档，非 git clone）

---

## 什么是 Superpowers

Superpowers 是一套完整的 **AI 编程代理工作流框架**，核心思想是把"最佳实践"封装成可复用的 **Skills（技能单元）**，让 AI 代理在任何任务前自动调用对应技能，而不是凭感觉乱来。

### 哲学
- **Test-Driven Development（TDD）** — 先写测试，永远先写
- **Systematic over ad-hoc** — 过程优于直觉
- **Complexity reduction** — 简单是首要目标
- **Evidence over claims** — 先验证再声明

---

## 核心工作流（7步）

| # | 技能 | 触发时机 | 核心目的 |
|---|------|---------|--------|
| 1 | `brainstorming` | 一切编码之前 | 提炼需求、探索方案、获得设计批准 |
| 2 | `using-git-worktrees` | 设计批准后 | 创建隔离工作空间 |
| 3 | `writing-plans` | 有设计文档后 | 拆解成 2-5 分钟粒度的任务 |
| 4 | `subagent-driven-development` | 有计划后 | 每任务派新子代理双阶段审查 |
| 5 | `test-driven-development` | 实现中 | RED-GREEN-REFACTOR 铁律 |
| 6 | `requesting-code-review` | 任务间 | 按严重级别报告问题 |
| 7 | `finishing-a-development-branch` | 任务全完 | 验证→合并/PR/保留 |

---

## 技能目录

```
skills/
├── brainstorming/           # 头脑风暴 → 设计文档
├── writing-plans/           # 实现计划撰写
├── executing-plans/         # 批次执行计划（并行session）
├── subagent-driven-development/  # 子代理驱动开发（当前session）
├── test-driven-development/ # TDD 铁律
├── systematic-debugging/    # 系统化调试（4阶段）
├── verification-before-completion/ # 完成前强制验证
├── writing-skills/          # 如何编写新技能（元技能）
└── using-superpowers/       # 如何使用技能系统（入口技能）
```

---

## 与投研框架的集成

见 [INTEGRATION.md](./INTEGRATION.md) — 把 Superpowers 的方法论移植到投研分析流程中。

---

## 一句话总结

> 技能是"强制工作流，不是建议"。代理在任何任务前**必须**调用相关技能。
