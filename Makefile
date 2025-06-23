# Notion 同步工具 Makefile

.PHONY: help install install-dev test test-unit test-integration test-ui test-all
.PHONY: quality format lint type-check coverage clean run
.PHONY: build package docs

# 默认目标
.DEFAULT_GOAL := help

# 颜色定义
BLUE := \033[36m
GREEN := \033[32m
YELLOW := \033[33m
RED := \033[31m
RESET := \033[0m

# Python 解释器
PYTHON := python3
PIP := pip3

# 项目目录
SRC_DIR := src
TEST_DIR := tests
DOCS_DIR := docs

help: ## 显示帮助信息
	@echo "$(BLUE)Notion 同步工具 - 可用命令:$(RESET)"
	@echo ""
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "$(GREEN)%-20s$(RESET) %s\n", $$1, $$2}'

install: ## 安装项目依赖
	@echo "$(BLUE)安装项目依赖...$(RESET)"
	$(PIP) install -r requirements.txt

install-dev: ## 安装开发依赖
	@echo "$(BLUE)安装开发依赖...$(RESET)"
	$(PIP) install -r requirements.txt
	$(PIP) install -r requirements-test.txt

test: test-unit ## 运行默认测试 (单元测试)

test-unit: ## 运行单元测试
	@echo "$(BLUE)运行单元测试...$(RESET)"
	$(PYTHON) run_tests.py --unit

test-integration: ## 运行集成测试
	@echo "$(BLUE)运行集成测试...$(RESET)"
	$(PYTHON) run_tests.py --integration

test-ui: ## 运行 UI 测试
	@echo "$(BLUE)运行 UI 测试...$(RESET)"
	$(PYTHON) run_tests.py --ui

test-all: ## 运行所有测试
	@echo "$(BLUE)运行所有测试...$(RESET)"
	$(PYTHON) run_tests.py --all

test-quick: ## 快速测试
	@echo "$(BLUE)运行快速测试...$(RESET)"
	$(PYTHON) run_tests.py --quick

test-slow: ## 运行慢速测试
	@echo "$(BLUE)运行慢速测试...$(RESET)"
	pytest $(TEST_DIR) -v -m "slow"

test-network: ## 运行需要网络的测试
	@echo "$(BLUE)运行网络测试...$(RESET)"
	pytest $(TEST_DIR) -v -m "network"

quality: ## 运行代码质量检查
	@echo "$(BLUE)运行代码质量检查...$(RESET)"
	$(PYTHON) run_tests.py --quality

format: ## 格式化代码
	@echo "$(BLUE)格式化代码...$(RESET)"
	black $(SRC_DIR) $(TEST_DIR)
	isort $(SRC_DIR) $(TEST_DIR)

lint: ## 代码风格检查
	@echo "$(BLUE)检查代码风格...$(RESET)"
	flake8 $(SRC_DIR) $(TEST_DIR)

type-check: ## 类型检查
	@echo "$(BLUE)检查类型注解...$(RESET)"
	mypy $(SRC_DIR)

coverage: ## 生成覆盖率报告
	@echo "$(BLUE)生成覆盖率报告...$(RESET)"
	$(PYTHON) run_tests.py --coverage

clean: ## 清理临时文件
	@echo "$(BLUE)清理临时文件...$(RESET)"
	$(PYTHON) run_tests.py --clean
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	rm -rf .pytest_cache .mypy_cache .coverage htmlcov coverage.xml
	rm -rf build dist *.egg-info

run: ## 运行应用程序
	@echo "$(BLUE)启动 Notion 同步工具...$(RESET)"
	$(PYTHON) test_app.py

debug: ## 调试模式运行应用程序
	@echo "$(BLUE)调试模式启动...$(RESET)"
	DEBUG=true $(PYTHON) test_app.py

# 开发工作流
dev-setup: install-dev ## 设置开发环境
	@echo "$(GREEN)开发环境设置完成!$(RESET)"
	@echo "运行 'make test' 来验证安装"

dev-test: format lint type-check test-unit ## 开发测试流程
	@echo "$(GREEN)开发测试流程完成!$(RESET)"

ci-test: quality test-all coverage ## CI 测试流程
	@echo "$(GREEN)CI 测试流程完成!$(RESET)"

# 构建和打包
build: clean ## 构建项目
	@echo "$(BLUE)构建项目...$(RESET)"
	$(PYTHON) -m build

package: build ## 创建分发包
	@echo "$(BLUE)创建分发包...$(RESET)"
	$(PYTHON) setup.py sdist bdist_wheel

# 文档
docs: ## 生成文档
	@echo "$(BLUE)生成文档...$(RESET)"
	@echo "文档位于 $(DOCS_DIR) 目录"

docs-serve: ## 启动文档服务器
	@echo "$(BLUE)启动文档服务器...$(RESET)"
	@echo "在浏览器中打开 docs/用户手册.md"

# 数据库操作
db-init: ## 初始化数据库
	@echo "$(BLUE)初始化数据库...$(RESET)"
	$(PYTHON) -c "from src.notion_sync.models.database import DatabaseManager; DatabaseManager().init_database()"

db-reset: ## 重置数据库
	@echo "$(YELLOW)重置数据库...$(RESET)"
	@echo "$(RED)警告: 这将删除所有数据!$(RESET)"
	@read -p "确定要继续吗? [y/N] " confirm && [ "$$confirm" = "y" ]
	$(PYTHON) -c "from src.notion_sync.models.database import DatabaseManager; DatabaseManager().reset_database()"

# 配置管理
config-reset: ## 重置配置
	@echo "$(YELLOW)重置配置...$(RESET)"
	$(PYTHON) -c "from src.notion_sync.utils.config import ConfigManager; ConfigManager().reset_to_defaults()"

config-backup: ## 备份配置
	@echo "$(BLUE)备份配置...$(RESET)"
	$(PYTHON) -c "from src.notion_sync.utils.settings_manager import SettingsManager; from src.notion_sync.utils.config import ConfigManager; SettingsManager(ConfigManager()).create_backup()"

# 性能测试
benchmark: ## 运行性能测试
	@echo "$(BLUE)运行性能测试...$(RESET)"
	pytest $(TEST_DIR) -v --benchmark-only

profile: ## 性能分析
	@echo "$(BLUE)运行性能分析...$(RESET)"
	$(PYTHON) -m cProfile -o profile.stats test_app.py

# 安全检查
security: ## 安全检查
	@echo "$(BLUE)运行安全检查...$(RESET)"
	safety check
	bandit -r $(SRC_DIR)

# 依赖管理
deps-update: ## 更新依赖
	@echo "$(BLUE)更新依赖...$(RESET)"
	$(PIP) list --outdated
	@echo "运行 'pip install --upgrade <package>' 来更新特定包"

deps-check: ## 检查依赖
	@echo "$(BLUE)检查依赖...$(RESET)"
	$(PIP) check

# 版本管理
version: ## 显示版本信息
	@echo "$(BLUE)版本信息:$(RESET)"
	@$(PYTHON) -c "from src.notion_sync import __version__; print(f'Notion Sync v{__version__}')"
	@$(PYTHON) --version
	@$(PIP) --version

# 状态检查
status: ## 显示项目状态
	@echo "$(BLUE)项目状态:$(RESET)"
	@echo "Python: $$($(PYTHON) --version)"
	@echo "依赖: $$($(PIP) list | wc -l) 个包已安装"
	@echo "测试: $$(find $(TEST_DIR) -name 'test_*.py' | wc -l) 个测试文件"
	@echo "代码: $$(find $(SRC_DIR) -name '*.py' | xargs wc -l | tail -1)"

# 监控文件变化并自动测试
watch: ## 监控文件变化并自动运行测试
	@echo "$(BLUE)监控文件变化...$(RESET)"
	@echo "按 Ctrl+C 停止监控"
	@while true; do \
		inotifywait -r -e modify $(SRC_DIR) $(TEST_DIR) 2>/dev/null && \
		echo "$(YELLOW)检测到文件变化，运行测试...$(RESET)" && \
		make test-quick; \
	done

# 完整的开发周期
full-check: clean format lint type-check test-all coverage ## 完整检查
	@echo "$(GREEN)✅ 完整检查通过!$(RESET)"

# 发布准备
release-check: full-check security ## 发布前检查
	@echo "$(GREEN)✅ 发布检查完成!$(RESET)"
