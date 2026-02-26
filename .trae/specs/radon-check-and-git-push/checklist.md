# Checklist

## Phase 1: Radon 代码质量检查

- [ ] radon 已安装
  - [ ] `pip install radon` 执行成功
  - [ ] `radon --version` 显示版本信息

- [ ] 圈复杂度检查完成
  - [ ] `radon cc webthief/interceptors/ -a` 执行成功
  - [ ] 所有函数复杂度等级为 A 或 B
  - [ ] 没有函数的复杂度等级为 C, D, E, F

- [ ] 可维护性指数检查完成
  - [ ] `radon mi webthief/interceptors/` 执行成功
  - [ ] 所有文件可维护性指数 >= 20
  - [ ] 没有文件的可维护性指数 < 20

## Phase 2: 代码重写优化

- [ ] 高复杂度函数已重写
  - [ ] 所有复杂度 > 10 的函数已识别
  - [ ] 所有复杂度 > 10 的函数已重构
  - [ ] 重构后的函数复杂度 <= 10
  - [ ] 重构后的函数功能正常

- [ ] 低可维护性文件已重写
  - [ ] 所有可维护性指数 < 20 的文件已识别
  - [ ] 所有可维护性指数 < 20 的文件已重构
  - [ ] 重构后的文件可维护性指数 >= 20
  - [ ] 重构后的文件功能正常

## Phase 3: 重新验证代码质量

- [ ] 圈复杂度重新检查通过
  - [ ] 重新运行 `radon cc webthief/interceptors/ -a`
  - [ ] 所有函数复杂度等级为 A 或 B

- [ ] 可维护性指数重新检查通过
  - [ ] 重新运行 `radon mi webthief/interceptors/`
  - [ ] 所有文件可维护性指数 >= 20

## Phase 4: README 更新

- [ ] README.md 已更新
  - [ ] 动画优化功能说明已添加
  - [ ] 新的 CLI 选项已说明
  - [ ] 使用示例已提供
  - [ ] 文档格式正确

## Phase 5: Git 提交与推送

- [ ] Git 提交完成
  - [ ] `git status` 显示所有更改
  - [ ] `git add .` 成功执行
  - [ ] `git commit` 成功执行
  - [ ] 提交信息描述清晰

- [ ] GitHub 推送完成
  - [ ] `git remote -v` 显示正确的远程仓库
  - [ ] `git push origin main` 成功执行
  - [ ] GitHub 上能看到新的提交

## 验收标准

- [ ] 所有新动画模块通过 radon 代码质量检查
- [ ] 所有函数圈复杂度等级为 A 或 B
- [ ] 所有文件可维护性指数 >= 20
- [ ] README.md 已更新
- [ ] 所有更改已提交到 git
- [ ] 所有更改已推送到 GitHub
