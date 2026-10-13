# 源表分组对应已有需求

默认不创建、删除或去重需求。源表正常下载为XLSX，目标定位到实际数据表而不是Wiki标识。

```bash
python scripts/run.py export-sheet --url "源电子表格链接" --output "私有任务目录/source.xlsx"
python scripts/run.py read --url "目标链接，带真实table参数" --output "私有任务目录/before.json"
python scripts/run.py map --source-xlsx "私有任务目录/source.xlsx" --sheet "实际工作表名" --snapshot "私有任务目录/before.json" --output "私有任务目录/plan.json" --group-column B --title-column C --description-column D
```

本参考命令假定在安装的Skill目录运行；仓库根目录把`scripts/`换成`skills/feishu-bitable-browser/scripts/`。链接没有table参数时加`--table-id`，ID从实际目标页面选择取得。

按实际表结构改列参数、`--header-row`及字段名。默认字段“业务模块”“需求标题”“需求描述”可以用`--field`、`--title-field`、`--description-field`改为真实名称。

分组仅在实际合并区内继承；行没有标题和描述则跳过。`--group-label full-cell`默认保留整个分组单元格；确认首行是名称而后续是目标/data备注时明确用`first-line`，不要静默改变口径。

匹配顺序：标题+完整描述 → 非空完整描述 → 标题。只消除空白差异，不用模糊相似度强制对应。源行和目标记录需一一唯一对应。`issues`及`unused_source_rows`不为空时默认`ready: false`和exit 2停止；用户明确接受局部交付后才用`--allow-partial`，并报告未覆盖项。

审查plan的目标、字段、记录数、源行号、新模块与变化数量后：

```bash
python scripts/run.py apply --plan "私有任务目录/plan.json"
```

这是不登录、不写入的dry run。用户已要求执行具体改动后加`--commit`。执行会保存before，核对当前旧值与内容，补缺失选项并刷新确认，试写一条并刷新确认，再每批最多50条字段级更新，最后刷新全量核验。最多支持5000条完整可读记录，不自动截断。

独立运行目录保存plan、旧值、分阶段回执、after-refresh与verification；快照文件拒绝覆盖，只有journal会更新。

结果未知或journal标记`needs_reconciliation`时，先`read`到新文件，对照已提交值和旧值。针对实际剩余对象重新生成计划，不能重跑整份旧apply。并发旧值不一致正是停止信号。

Verify检查记录ID、全部预期分类、旧选项、无关业务字段和字段定义。平台自动修改时间/修改人可按实际系统字段排除；业务或公式差异逐项核对，不为通过任意忽略。

恢复需独立明确授权，只还原本次旧值；先确认未被后续用户修改。不要覆盖整个Base。新增选项有新引用时保留。
