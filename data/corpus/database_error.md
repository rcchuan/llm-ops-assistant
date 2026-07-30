# 数据库报错运维手册

## Q: MySQL 主从延迟告警（Seconds_Behind_Master 过大）怎么处理？

**结论**：主从同步存在延迟，需先确认延迟秒数并排查慢 SQL 与大事务。

**排查步骤**：
1. 在从库执行 show slave status，查看 Seconds_Behind_Master、Slave_IO_Running、Slave_SQL_Running
2. 查主库 binlog 与从库 relay log 是否正常推进
3. 定位正在执行的大事务或慢 SQL（processlist、慢日志）
4. 评估是否可暂停非核心 ETL 或拆分批量 UPDATE

**升级条件**：延迟持续超过 30 分钟且影响核心读业务，升级二线 DBA。

**常用命令**：show slave status; show processlist;

---

## Q: Oracle 表空间使用率 95% 告警如何处理？

**结论**：表空间或归档区满会导致无法写入，需立即释放或扩容。

**排查步骤**：
1. 查询 dba_tablespace_usage_metrics 或 dba_data_files 确认满的空间名
2. 检查 ARCHIVELOG 是否未备份导致归档堆积
3. 清理过期备份、临时表或扩容数据文件
4. 核对近期是否有大批量导入未分批

**升级条件**：生产库无法写入且 15 分钟内无法释放，升级 DBA 并走应急变更。

---

## Q: 数据库连接池耗尽导致业务超时？

**结论**：连接泄漏或突发流量导致池满，需看活跃连接与等待队列。

**排查步骤**：
1. 查看应用连接池监控（active/idle/wait）
2. 数据库侧 show processlist 统计按用户/来源 IP 的连接数
3. 检查是否有长事务未提交占用连接
4. 临时调大 max_connections 需评估数据库负载

**升级条件**：连接数持续打满且重启应用无效，联合 DBA 与应用二线排查。
