---
name: "git-commit-message"
description: "自定义 AI 生成提交信息的风格。适用于 git commit、代码提交、版本控制等场景。"
alwaysApply: true
priority: "normal"
trigger:
  - "git commit"
  - "代码提交"
  - "版本控制"
scene: "git_message"
checkLogic:
  - "提交信息是否符合格式"
  - "是否包含类型前缀"
  - "是否有简洁的描述"
  - "是否有详细的正文（如果需要）"
enforcement: "不符合格式时提示修改"
---
# Git Commit Message 规范

## 规则内容
在此处编写规则，自定义 AI 生成提交信息的风格。

## 提交信息格式
采用 Conventional Commits 格式：

```
<type>(<scope>): <subject>

[optional body]

[optional footer(s)]
```

## Type 类型
- `feat`: 新功能
- `fix`: 修复 Bug
- `docs`: 文档更新
- `style`: 代码格式（不影响功能）
- `refactor`: 代码重构
- `perf`: 性能优化
- `test`: 测试相关
- `chore`: 构建/工具相关

## 示例

### 简单提交
```
feat(user): add password reset functionality
```

### 带正文的提交
```
fix(auth): resolve token expiration issue

The JWT token was expiring too quickly for long sessions.
Changed expiration from 1h to 24h.

Closes #123
```

### 带 Scope 的提交
```
feat(auth): add OAuth2 login support

- Google OAuth
- GitHub OAuth
- Microsoft OAuth

BREAKING CHANGE: Session handling changed
```

## AI 生成规则
1. 第一行不超过 72 字符
2. 使用祈使语气（Add, Fix, Update）
3. 不使用句号结尾
4. Body 部分解释"为什么"而非"是什么"
5. Footer 部分引用相关 Issue
