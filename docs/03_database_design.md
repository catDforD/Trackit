# Trackit 数据库设计教程

## 概述

本文档详细讲解Trackit项目中的数据库设计，包括SQLite schema设计原则、表结构、索引优化以及数据访问层的实现。

**学习目标**:
- 理解为什么选择SQLite
- 掌握习惯追踪数据的schema设计
- 学习如何为时序数据设计索引
- 了解Repository模式的数据访问层

---

## 为什么选择SQLite?

### 优势

1. **轻量级**: 无需独立服务器，嵌入式数据库
2. **零配置**: 无需安装和设置，开箱即用
3. **单一文件**: 所有数据存储在一个文件中，便于备份和迁移
4. **事务支持**: 支持ACID事务，数据安全有保障
5. **Python原生支持**: Python标准库内置sqlite3模块

### 适用场景

Trackit这样的个人习惯追踪应用非常适合SQLite：
- 数据量适中（个人使用，百万级记录以下）
- 单用户应用（无需处理并发写入）
- 需要结构化查询和聚合
- 部署简单（用户无需配置数据库服务器）

### 何时需要升级?

如果你需要以下功能，考虑升级到PostgreSQL/MySQL：
- 多用户并发写入
- 千万级以上数据量
- 需要复杂的分析查询
- 需要水平扩展

---

## 数据库Schema设计

### 表1: entries（习惯记录表）

这是核心表，存储用户的所有习惯记录。

```sql
CREATE TABLE entries (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    date DATE NOT NULL,
    raw_input TEXT NOT NULL,
    category VARCHAR(50),
    mood VARCHAR(20),
    metrics_json TEXT,
    note TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
```

### 字段说明

| 字段 | 类型 | 说明 | 示例 |
|------|------|------|------|
| `id` | INTEGER | 主键，自增 | 1, 2, 3... |
| `timestamp` | DATETIME | 记录时间戳 | 2026-01-10 08:30:00 |
| `date` | DATE | 日期（用于查询） | 2026-01-10 |
| `raw_input` | TEXT | 用户原始输入 | "今天跑了5公里" |
| `category` | VARCHAR(50) | 习惯类别 | "运动"、"学习"、"睡眠" |
| `mood` | VARCHAR(20) | 情绪标签 | "positive"、"neutral" |
| `metrics_json` | TEXT | JSON格式的指标 | {"distance_km": 5.0} |
| `note` | TEXT | 额外备注 | NULL或备注文字 |
| `created_at` | DATETIME | 记录创建时间 | 2026-01-10 08:30:00 |

### 设计决策

#### 1. 为什么同时有`date`和`timestamp`?

- `timestamp`: 精确到秒的记录时间，用于排序和分析
- `date`: 仅日期部分，用于按天查询和分组

```python
# 按日期查询时更高效
SELECT * FROM entries WHERE date = '2026-01-10'

# 按时间排序时使用timestamp
SELECT * FROM entries ORDER BY timestamp DESC
```

#### 2. 为什么`metrics`存储为JSON?

灵活性！不同类别有不同的指标：

```json
// 运动
{"distance_km": 5.0, "duration_min": 30}

// 学习
{"pages": 20, "duration_min": 120}

// 睡眠
{"sleep_hours": 7.5, "wake_time": "06:30"}
```

如果每个指标都作为独立列，表会有太多NULL值。

#### 3. 为什么保留`raw_input`?

- 用户可能想查看原始记录
- 调试时有用
- 未来可以用LLM重新分析

---

### 表2: weekly_reports（周报缓存表）

为了性能，生成的周报会被缓存。

```sql
CREATE TABLE weekly_reports (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    week_iso VARCHAR(10) UNIQUE,
    report_json TEXT NOT NULL,
    generated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
```

### 字段说明

| 字段 | 类型 | 说明 |
|------|------|------|
| `week_iso` | VARCHAR(10) | ISO周格式，如"2026-W02" |
| `report_json` | TEXT | 完整的周报数据（JSON） |
| `generated_at` | DATETIME | 生成时间 |

### 为什么需要缓存表?

生成周报需要：
1. 查询7天的数据
2. 计算统计指标
3. LLM生成洞察（昂贵！）

缓存后，用户多次查看同一周报只需查询一次，大大降低成本和延迟。

---

## 索引设计

索引是查询性能的关键！

```sql
-- 按日期查询的索引
CREATE INDEX idx_entries_date ON entries(date);

-- 按类别过滤的索引
CREATE INDEX idx_entries_category ON entries(category);

-- 按情绪分析的索引
CREATE INDEX idx_entries_mood ON entries(mood);
```

### 索引使用示例

```sql
-- 查询某天的所有记录（使用idx_entries_date）
SELECT * FROM entries WHERE date = '2026-01-10';

-- 查询运动类记录（使用idx_entries_category）
SELECT * FROM entries WHERE category = '运动';

-- 查询正面情绪记录（使用idx_entries_mood）
SELECT * FROM entries WHERE mood = 'positive';
```

### 何时需要索引?

**需要索引的情况**:
- 频繁用于WHERE子句的列
- 用于JOIN的列
- 用于ORDER BY的列

**不需要索引的情况**:
- 很少查询的列
- 数据量很小的表
- 频繁更新的列（写入性能损失）

---

## Repository模式

### 什么是Repository模式?

Repository模式将数据访问逻辑封装在单独的类中，业务代码通过Repository与数据库交互。

**好处**:
- 业务逻辑和数据访问分离
- 易于测试（可以mock Repository）
- 统一的接口

### HabitRepository实现

```python
class HabitRepository:
    def __init__(self, db_path: str = "data/trackit.db"):
        self.db_path = db_path

    def add_entry(self, raw_input, category, mood, metrics, note=None):
        """添加记录"""
        # ... SQL INSERT ...

    def get_entries_by_date(self, date):
        """按日期查询"""
        # ... SQL SELECT ...

    def get_statistics(self):
        """获取统计信息"""
        # ... SQL聚合查询 ...
```

### 使用示例

```python
# 创建repository
repo = HabitRepository("data/trackit.db")

# 添加记录
entry_id = repo.add_entry(
    raw_input="今天跑了5公里",
    category="运动",
    mood="positive",
    metrics={"distance_km": 5.0}
)

# 查询记录
entries = repo.get_entries_by_date("2026-01-10")
for entry in entries:
    print(f"{entry['category']}: {entry['metrics']}")
```

---

## 常用查询模式

### 1. 按日期范围查询

```python
def get_entries_by_week(self, week_iso: str):
    # 解析ISO周，获取日期范围
    year, week = map(int, week_iso.split("-W"))
    start_date = datetime.strptime(f"{year}-{week}-1", "%Y-%W-%w").date()
    end_date = start_date + timedelta(days=6)

    # 查询
    cursor.execute("""
        SELECT * FROM entries
        WHERE date >= ? AND date <= ?
        ORDER BY timestamp ASC
    """, (start_date, end_date))
```

### 2. 统计聚合查询

```python
def get_statistics(self):
    # 总记录数
    cursor.execute("SELECT COUNT(*) FROM entries")

    # 按类别统计
    cursor.execute("""
        SELECT category, COUNT(*) as count
        FROM entries
        GROUP BY category
    """)

    # 情绪分布
    cursor.execute("""
        SELECT mood, COUNT(*) as count
        FROM entries
        GROUP BY mood
    """)
```

### 3. 最新记录查询

```python
def get_recent_entries(self, limit=10):
    cursor.execute("""
        SELECT * FROM entries
        ORDER BY timestamp DESC
        LIMIT ?
    """, (limit,))
```

---

## 数据完整性

### 使用Context Manager

确保数据库连接正确关闭：

```python
@contextmanager
def _get_connection(self):
    conn = sqlite3.connect(self.db_path)
    try:
        yield conn
        conn.commit()
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.close()
```

### 使用示例

```python
with self._get_connection() as conn:
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM entries")
    results = cursor.fetchall()
# 连接自动关闭，事务自动提交或回滚
```

---

## 性能优化技巧

### 1. 使用事务批量插入

```python
# 慢：每次插入都是一个事务
for entry in entries:
    repo.add_entry(entry)  # N次事务

# 快：一个事务完成所有插入
with self._get_connection() as conn:
    cursor = conn.cursor()
    for entry in entries:
        cursor.execute("INSERT INTO entries ...", entry)
```

### 2. 只查询需要的字段

```python
# 慢：查询所有字段
SELECT * FROM entries

# 快：只查询需要的字段
SELECT id, category, mood FROM entries
```

### 3. 使用LIMIT分页

```python
# 分页查询
page = 1
per_page = 20
offset = (page - 1) * per_page

cursor.execute("""
    SELECT * FROM entries
    ORDER BY timestamp DESC
    LIMIT ? OFFSET ?
""", (per_page, offset))
```

---

## 测试数据库代码

### 使用临时文件测试

```python
import tempfile
import unittest

class TestDatabase(unittest.TestCase):
    def setUp(self):
        # 创建临时数据库
        self.temp_db = tempfile.NamedTemporaryFile(delete=False)
        self.db_path = self.temp_db.name
        self.repo = HabitRepository(self.db_path)

    def tearDown(self):
        # 清理临时文件
        os.remove(self.db_path)

    def test_add_entry(self):
        entry_id = self.repo.add_entry(
            raw_input="测试",
            category="其他",
            mood="neutral",
            metrics={}
        )
        self.assertGreater(entry_id, 0)
```

### 运行测试

```bash
python -m unittest tests.test_database -v
```

---

## 数据库迁移策略

### 未来如何修改Schema?

```python
def migrate_add_new_column():
    conn = sqlite3.connect("data/trackit.db")
    cursor = conn.cursor()

    # 添加新列（如果不存在）
    cursor.execute("""
        ALTER TABLE entries
        ADD COLUMN tags TEXT
    """)

    conn.commit()
    conn.close()
```

### 更好的做法：版本管理

```python
SCHEMA_VERSION = 2

def migrate_to_v2():
    """从v1迁移到v2"""
    if get_current_version() < 2:
        # 执行迁移
        add_tags_column()
        update_schema_version(2)
```

---

## 总结

本教程涵盖了：

1. ✅ 为什么选择SQLite
2. ✅ 核心表设计（entries, weekly_reports）
3. ✅ 字段设计决策和理由
4. ✅ 索引设计和优化
5. ✅ Repository模式实现
6. ✅ 常用查询模式
7. ✅ 性能优化技巧
8. ✅ 测试方法

### 下一步学习

- `docs/02_llm_integration_guide.md` - 如何集成Claude API
- `docs/04_prompt_engineering.md` - 如何设计有效的Prompt
- `docs/01_project_architecture.md` - 整体架构设计

---

## 参考资源

- [SQLite官方文档](https://www.sqlite.org/docs.html)
- [Python sqlite3模块](https://docs.python.org/3/library/sqlite3.html)
- [SQLite索引最佳实践](https://www.sqlite.org/optoverview.html)
