-- ============================================================
-- llm-ops-assistant · MySQL 数据库与用户初始化脚本
-- 用途：从 GitHub 克隆后，首次部署时创建项目专用数据库和用户
-- 执行：mysql -u root -p < deployment/init_database.sql
-- ============================================================

-- 创建项目数据库
CREATE DATABASE IF NOT EXISTS dify_ops
  DEFAULT CHARACTER SET utf8mb4
  DEFAULT COLLATE utf8mb4_unicode_ci;

-- 创建项目专用用户（按需修改密码）
CREATE USER IF NOT EXISTS 'llm_ops_app'@'%'
  IDENTIFIED BY 'CHANGE_ME_IN_PRODUCTION';

-- 授权该用户仅访问 dify_ops 库
GRANT ALL PRIVILEGES ON dify_ops.* TO 'llm_ops_app'@'%';
FLUSH PRIVILEGES;

-- 完成提示
SELECT '数据库 dify_ops 和用户 llm_ops_app 已就绪' AS status;
