# Git 工作流约束

> **核心原则：一个提交 = 一个完整的、可独立回退的逻辑单元。**
>
> 提交不是 Ctrl+S。不要改一行交一行。

---

## 1. 什么时候才能提交？

**必须满足以下所有条件：**

- [ ] 当前功能/修复的 **所有代码改动** 已完成
- [ ] 已通过相关测试（`python -m unittest` 或手动验证）
- [ ] 没有已知的 bug 或未完成的代码片段
- [ ] 提交信息能说清楚"做了什么、为什么做"

**绝对不要：**
- 改了一行就 `git commit`（碎片化）
- 把提交当"保存进度"（这是 `git stash` 的事）
- 提交包含 `print`/`console.log` 调试代码的半成品
- 临下班/临时走开随便交一版

---

## 2. 正确的工作流

```
修改代码 ──→ 测试验证 ──→ 确认无误 ──→ 一次性提交
                              │
                              └── 有问题？继续改，不提交
```

### 中途需要切换任务怎么办？

用 `git stash` 暂存，**不要用 WIP 提交**：

```bash
# 保存当前进度
git stash push -m "WIP: 正在重构 TTS 模块"

# 切去干别的事...

# 回来恢复
git stash pop
```

---

## 3. 提交信息规范（Conventional Commits）

```
<type>: <简短描述>

<详细说明（可选）>
```

| Type | 用途 |
|---|---|
| `feat` | 新功能 |
| `fix` | 修 bug |
| `docs` | 文档/注释 |
| `refactor` | 重构（不改功能） |
| `test` | 测试 |
| `chore` | 杂项（依赖、脚本） |
| `style` | 格式（空格、缩进） |

**示例：**

```bash
# ✅ 好的提交
git commit -m "feat: 添加 CosyVoice TTS 插件支持"
git commit -m "fix: 修复 WebRTC 在 Firefox 上断连问题"
git commit -m "docs: 补充 Windows 安装指南"

# ❌ 坏的提交
git commit -m "改了点东西"
git commit -m "fix bug"
git commit -m "wip"
git commit -m "."
```

---

## 4. 每次提交的粒度

一个好的提交应该：

- **能一句话说清楚做了什么**
- **可以安全地 `git revert` 而不影响其他功能**
- **review 的人看这一个 commit 就能理解改动意图**

反例：
- 一个提交改了 20 个不相关的文件 → 拆成多个提交
- 三个不同的 bug 修在同一个提交里 → 拆开，方便回退

---

## 5. 如果不小心交了碎片提交怎么办？

### 情况 A：还没 push

```bash
# 把最近 3 个小提交合并成 1 个
git reset --soft HEAD~3
git commit -m "feat: 完整实现 XXX 功能"
```

### 情况 B：已经 push 了

```bash
# 交互式 rebase 合并（会改写历史，确保队友知晓）
git rebase -i HEAD~3
# 把后面的 commit 标记为 squash 或 fixup
git push --force-with-lease
```

### 情况 C：想撤销最近一次提交但保留改动

```bash
git reset --soft HEAD~1   # 改动回到暂存区，继续改
```

---

## 6. 推送纪律

- **push 之前先想清楚**：这个提交能独立回退吗？
- **push 之后尽量不 force push**（除非在个人分支且队友知晓）
- 合并到 `main` 之前做一次 squash merge，把碎片压成干净的提交历史

---

## 7. AGENTS.md 约束

本文件是 AGENTS.md 的补充约束。所有修改必须遵守 AGENTS.md 中规定的规则，
**且不得在未通过测试前提交任何代码。**

---

> **记住这句话：改完、测好、确认没问题了，再交。交了就别后悔，因为不该有"我先随便交一版"这种事。**
