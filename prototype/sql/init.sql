-- ============================================================
-- 移动运维工单智能答疑机器人 · MySQL 初始化脚本
-- 执行: python scripts/init_db.py
-- ============================================================

CREATE DATABASE IF NOT EXISTS dify_ops
  DEFAULT CHARACTER SET utf8mb4
  DEFAULT COLLATE utf8mb4_unicode_ci;

USE dify_ops;

-- ---------- 运维工单表 ----------
DROP TABLE IF EXISTS qa_logs;
DROP TABLE IF EXISTS work_orders;
DROP TABLE IF EXISTS corpus_raw;
DROP TABLE IF EXISTS corpus_clean;
DROP TABLE IF EXISTS high_freq_issues;

CREATE TABLE work_orders (
    id              BIGINT AUTO_INCREMENT PRIMARY KEY COMMENT '自增主键',
    order_no        VARCHAR(32)  NOT NULL UNIQUE COMMENT '工单编号',
    fault_type      VARCHAR(32)  NOT NULL DEFAULT '其他' COMMENT '故障类型(原始)',
    fault_category  VARCHAR(16)  NOT NULL DEFAULT '其他' COMMENT '正则分类: 数据库/服务器/网络/其他',
    description     TEXT         NOT NULL COMMENT '问题描述',
    submit_time     DATETIME     NOT NULL COMMENT '提交时间',
    status          VARCHAR(16)  NOT NULL DEFAULT '待处理' COMMENT '处理状态',
    is_duplicate    TINYINT(1)   NOT NULL DEFAULT 0 COMMENT '是否重复工单',
    created_at      TIMESTAMP    DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB COMMENT='模拟移动运维工单';

-- ---------- Dify 问答日志表 ----------
CREATE TABLE qa_logs (
    id              BIGINT AUTO_INCREMENT PRIMARY KEY,
    user_id         VARCHAR(64)  NOT NULL DEFAULT 'anonymous' COMMENT '调用方用户标识',
    question        TEXT         NOT NULL COMMENT '用户问题',
    answer          MEDIUMTEXT   COMMENT 'AI 回答',
    conversation_id VARCHAR(64)  COMMENT 'Dify 会话 ID',
    message_id      VARCHAR(64)  COMMENT 'Dify 消息 ID',
    retriever_resources JSON     COMMENT '引用片段 JSON',
    created_at      TIMESTAMP    DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_qa_created (created_at)
) ENGINE=InnoDB COMMENT='Dify 问答日志';

-- ---------- 语料原始/清洗表 ----------
CREATE TABLE corpus_raw (
    id          BIGINT AUTO_INCREMENT PRIMARY KEY,
    category    VARCHAR(32)  NOT NULL COMMENT '语料类别',
    question    TEXT         NOT NULL,
    answer      TEXT         NOT NULL,
    source_file VARCHAR(128),
    created_at  TIMESTAMP    DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB COMMENT='原始语料';

CREATE TABLE corpus_clean (
    id          BIGINT AUTO_INCREMENT PRIMARY KEY,
    category    VARCHAR(32)  NOT NULL,
    question    TEXT         NOT NULL,
    answer      TEXT         NOT NULL,
    dify_doc_name VARCHAR(128) COMMENT '上传 Dify 文档名',
    uploaded    TINYINT(1)   NOT NULL DEFAULT 0,
    created_at  TIMESTAMP    DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY uk_qa (category(16), question(128))
) ENGINE=InnoDB COMMENT='清洗后语料';

-- ---------- 高频问题汇总（推送知识库） ----------
CREATE TABLE high_freq_issues (
    id          BIGINT AUTO_INCREMENT PRIMARY KEY,
    category    VARCHAR(16)  NOT NULL,
    keyword_sig VARCHAR(128) NOT NULL COMMENT '问题特征签名',
    sample_desc TEXT         NOT NULL,
    hit_count   INT          NOT NULL DEFAULT 1,
    pushed_dify TINYINT(1)   NOT NULL DEFAULT 0,
    updated_at  TIMESTAMP    DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE KEY uk_sig (keyword_sig)
) ENGINE=InnoDB COMMENT='高频重复问题';

-- ---------- 模拟工单数据 ----------
INSERT INTO work_orders (order_no, fault_type, fault_category, description, submit_time, status) VALUES
('WO-20250601-001', '数据库', '数据库', 'MySQL从库Seconds_Behind_Master超过600秒，读接口偶发超时，请协助排查主从延迟原因。', '2025-06-01 08:15:00', '处理中'),
('WO-20250601-002', '数据库', '数据库', 'MySQL从库延迟告警，Seconds_Behind_Master大于600，多个查询变慢。', '2025-06-01 09:20:00', '待处理'),
('WO-20250601-003', '主机', '服务器', '订单服务主机CPU持续92%超20分钟，top显示java进程占满，需排查批任务是否重叠。', '2025-06-01 10:30:00', '处理中'),
('WO-20250601-004', '主机资源', '服务器', '服务器CPU 90%告警，/var/log磁盘也偏高，怀疑日志未切割。', '2025-06-01 11:00:00', '待处理'),
('WO-20250602-005', '网络', '网络', '多个营业厅反馈登录页面转圈后超时，网关5xx比例升高，疑似认证服务异常。', '2025-06-02 10:30:00', '处理中'),
('WO-20250602-006', '网络', '网络', '网点访问业务平台超时，ping网关正常，Traceroute在核心交换机有丢包。', '2025-06-02 11:15:00', '待处理'),
('WO-20250602-007', '基站', '网络', '某区县3个LTE基站退服，传输光路中断，现场反馈RRU链路Down。', '2025-06-02 14:00:00', '处理中'),
('WO-20250603-008', '流程', '其他', '工单流转卡在二线审批超过4小时，请确认ITSM流程节点配置。', '2025-06-03 09:00:00', '已关闭'),
('WO-20250603-009', '数据库', '数据库', 'Oracle表空间使用率95%，归档日志未清理导致写入失败。', '2025-06-03 15:40:00', '待处理'),
('WO-20250603-010', '主机', '服务器', 'Linux服务器内存swap使用90%，OOM killer杀掉了中间件进程。', '2025-06-03 16:20:00', '处理中');

-- ---------- 原始语料样本（供 data_clean 清洗演示） ----------
INSERT INTO corpus_raw (category, question, answer, source_file) VALUES
('服务器故障', 'CPU 一直 90% 怎么办？？', '  先看 top  找进程  ', 'raw_messy.txt'),
('服务器故障', 'CPU 一直 90% 怎么办？？', '  先看 top  找进程  ', 'raw_messy.txt'),
('数据库报错', 'MySQL  主从延迟  怎么查', 'show slave status 看 Seconds_Behind_Master', 'raw_messy.txt'),
('数据库报错', '!!!Oracle表空间满了!!!', '查 dba_data_files 使用率，清理归档日志', 'raw_messy.txt'),
('基站运维', 'LTE基站退服先查什么', '查传输光路、RRU链路、小区状态', 'raw_messy.txt'),
('工单流程', '工单挂起超过 SLA 怎么处理', '确认节点审批人、升级至二线并记录原因', 'raw_messy.txt');
