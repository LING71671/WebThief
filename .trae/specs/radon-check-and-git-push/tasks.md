# Tasks

## Phase 1: Radon 代码质量检查

- [ ] Task 1: 安装并运行 radon 检查
  - [ ] SubTask 1.1: 确保 radon 已安装 (`pip install radon`)
  - [ ] SubTask 1.2: 运行圈复杂度检查 `radon cc webthief/interceptors/ -a`
  - [ ] SubTask 1.3: 运行可维护性指数检查 `radon mi webthief/interceptors/`
  - [ ] SubTask 1.4: 收集所有不合格的函数和文件列表

## Phase 2: 代码重写优化

- [ ] Task 2: 重写高复杂度函数
  - [ ] SubTask 2.1: 分析每个复杂度 > 10 的函数
  - [ ] SubTask 2.2: 重构函数，降低复杂度（提取子函数、简化条件逻辑）
  - [ ] SubTask 2.3: 验证重构后功能正常

- [ ] Task 3: 重写低可维护性文件
  - [ ] SubTask 3.1: 分析每个可维护性指数 < 20 的文件
  - [ ] SubTask 3.2: 重构代码，提高可维护性
  - [ ] SubTask 3.3: 验证重构后功能正常

## Phase 3: 重新验证代码质量

- [ ] Task 4: 重新运行 radon 检查
  - [ ] SubTask 4.1: 再次运行 `radon cc webthief/interceptors/ -a`
  - [ ] SubTask 4.2: 再次运行 `radon mi webthief/interceptors/`
  - [ ] SubTask 4.3: 确认所有指标达标（复杂度 A/B，可维护性 >= 20）

## Phase 4: README 更新

- [ ] Task 5: 更新 README.md
  - [ ] SubTask 5.1: 检查当前 README.md 是否需要更新
  - [ ] SubTask 5.2: 添加动画优化功能完整说明
  - [ ] SubTask 5.3: 添加新的 CLI 选项说明
  - [ ] SubTask 5.4: 添加使用示例

## Phase 5: Git 提交与推送

- [ ] Task 6: Git 提交
  - [ ] SubTask 6.1: 检查 git 状态 `git status`
  - [ ] SubTask 6.2: 添加所有更改 `git add .`
  - [ ] SubTask 6.3: 创建提交 `git commit -m "feat: add animation support optimization"`

- [ ] Task 7: GitHub 推送
  - [ ] SubTask 7.1: 检查远程仓库配置 `git remote -v`
  - [ ] SubTask 7.2: 推送到 GitHub `git push origin main`
  - [ ] SubTask 7.3: 验证推送成功

# Task Dependencies

- Task 2 depends on Task 1
- Task 3 depends on Task 1
- Task 4 depends on Task 2, Task 3
- Task 5 can be done in parallel with Task 4
- Task 6 depends on Task 4, Task 5
- Task 7 depends on Task 6
