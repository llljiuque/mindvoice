# MindVoice 会员体系与消费计量完整规划文档

> **版本**: v1.0  
> **日期**: 2026-01-05  
> **状态**: 规划阶段  
> **当前项目版本**: v1.8.0

---

## 📋 文档说明

本文档是 MindVoice 项目的会员体系与消费计量功能的完整规划。这是一个**新增功能模块**，将在现有项目基础上扩展实现。

**与现有系统的关系**:
- 数据库扩展：在现有 SQLite 数据库基础上新增表结构
- 架构兼容：与现有 Electron + Python FastAPI 架构完全兼容
- 配置扩展：在 `config.yml` 中新增会员相关配置
- 向后兼容：不影响现有功能的正常使用

## 🎯 核心设计理念

**功能全部开放，仅额度区分等级**

本方案采用简化设计，**所有功能模块对所有用户完全开放**，不同会员等级仅在以下方面有区别：

1. **月度额度**: ASR时长和LLM tokens的使用量
2. **客服支持**: 响应时间和服务级别

**优势**:
- ✅ 降低研发难度（减少约30%工作量）
- ✅ 提升用户体验（可体验全部功能）
- ✅ 商业逻辑清晰（用得多就升级）
- ✅ 快速上线（先简后繁）

---

## 目录

1. [概述](#一概述)
2. [架构设计](#二架构设计)
3. [设备识别与绑定](#三设备识别与绑定)
4. [会员体系](#四会员体系)
5. [消费计量](#五消费计量)
6. [激活码系统](#六激活码系统)
7. [用户旅程](#七用户旅程)
8. [UI/UX设计](#八uiux设计)
9. [数据库设计](#九数据库设计)
10. [API接口](#十api接口)
11. [安全机制](#十一安全机制)
12. [运营支持](#十二运营支持)
13. [技术实施](#十三技术实施)
14. [测试计划](#十四测试计划)
15. [部署与运维](#十五部署与运维)
16. [合规性](#十六合规性)
17. [未来扩展](#十七未来扩展)

---

## 一、概述

### 1.1 背景

MindVoice 是一个结合语音识别（ASR）和大语言模型（LLM）的智能桌面助手。为了可持续运营并提供差异化服务，需要建立会员体系与消费计量机制。

**当前项目状态**:
- ✅ 基础功能已实现：语音识别、智能对话、历史记录
- ✅ 数据库已建立：`records` 表（id, text, metadata, app_type, created_at）
- ✅ 配置系统完善：ASR、LLM、存储配置完整
- 🔲 会员体系：待实现
- 🔲 消费计量：待实现
- 🔲 激活码系统：待实现

### 1.2 核心目标

- **设备绑定**: 一机一码，防止滥用
- **消费计量**: ASR时长、LLM tokens精确统计
- **会员等级**: 多层次额度满足不同需求
- **功能开放**: 所有功能全部开放，降低研发难度
- **激活流程**: 简单、安全、可靠
- **用户体验**: 透明、友好、无感知

### 1.3 设计原则

1. **本地优先**: 核心数据存储在本地，离线可用
2. **稳定可靠**: 设备ID基于硬件，重装不丢失
3. **透明计量**: 实时显示消费和剩余额度
4. **灵活订阅**: 1～n个月任意选择（无终身会员，避免漏洞）
5. **安全防护**: 防作弊、防滥用、数据加密
6. **功能开放**: 所有功能全部开放，仅额度区分等级

### 1.4 简化说明

**为什么功能全部开放？**

1. **降低研发难度**: 
   - 不需要实现功能权限控制系统
   - 不需要在每个功能模块检查权限
   - 代码逻辑更简单，维护成本更低

2. **提升用户体验**:
   - 用户可以体验所有功能，更容易发现价值
   - 不会因为功能限制产生挫败感
   - 升级决策更简单：只需要更多额度

3. **商业逻辑清晰**:
   - 不同等级仅在额度上有差异
   - 易于理解：用得多就升级
   - 客服支持等级作为附加价值

4. **实施优先级**:
   - Phase 1: 仅实现额度控制（核心）
   - Phase 2: 可选添加功能限制（如果需要）
   - 先简后繁，快速上线

---

## 二、架构设计

### 2.1 整体架构

```
┌─────────────────────────────────────────────────────┐
│                   Electron 主进程                    │
│  ┌──────────────┐  ┌──────────────┐  ┌───────────┐ │
│  │ 设备识别模块  │  │ 会员管理模块  │  │ 监控模块  │ │
│  └──────────────┘  └──────────────┘  └───────────┘ │
└─────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────┐
│                   Python 后端服务                    │
│  ┌──────────────┐  ┌──────────────┐  ┌───────────┐ │
│  │ ASR消费统计  │  │ LLM消费统计  │  │ 数据库    │ │
│  └──────────────┘  └──────────────┘  └───────────┘ │
└─────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────┐
│                   本地数据存储                       │
│  ┌──────────────┐  ┌──────────────┐  ┌───────────┐ │
│  │ SQLite 数据库│  │ JSON 配置    │  │ 日志文件  │ │
│  └──────────────┘  └──────────────┘  └───────────┘ │
└─────────────────────────────────────────────────────┘
```

### 2.2 数据流

```
用户操作
    ↓
ASR/LLM服务调用
    ↓
消费计量（实时统计）
    ↓
额度检查（前置验证）
    ↓
写入数据库（消费记录）
    ↓
UI更新（显示剩余额度）
```

### 2.3 存储位置

| 数据类型 | 存储位置 | 说明 |
|---------|---------|------|
| 设备信息 | `~/Library/Application Support/MindVoice/device.json` | 稳定位置，重装不删 |
| 会员信息 | `~/Library/Application Support/MindVoice/database/membership.db` | SQLite（新增） |
| 消费记录 | `~/Library/Application Support/MindVoice/database/consumption.db` | SQLite（新增） |
| 激活码黑名单 | `~/Library/Application Support/MindVoice/blacklist.json` | JSON（新增） |
| 应用数据 | `~/Library/Application Support/MindVoice/database/history.db` | 现有数据库 |

**注意**: Windows/Linux 路径参考 `config.yml.example` 中的跨平台配置。

---

## 三、设备识别与绑定

### 3.1 设备ID生成策略

#### 3.1.1 生成原则

- **稳定性**: 基于硬件信息，同一机器始终相同
- **唯一性**: 不同机器生成不同ID
- **安全性**: 无法反向推导硬件信息
- **跨平台**: 支持 macOS、Windows、Linux

#### 3.1.2 生成算法

```typescript
function generateDeviceId(): string {
  // 1. 获取机器唯一标识
  const machineId = getMachineId(); // 平台相关
  
  // 2. SHA-256哈希 + 盐值
  const hash = sha256(machineId + 'MindVoice-Salt');
  
  // 3. 转换为UUID格式
  return formatAsUUID(hash);
}
```

#### 3.1.3 平台实现

| 平台 | 标识来源 | 获取方式 | 降级方案 |
|-----|---------|---------|---------|
| macOS | 系统序列号 / Hardware UUID | `system_profiler` / `ioreg` | 本地生成并持久化 |
| Windows | 机器GUID | 注册表 / PowerShell | 本地生成并持久化 |
| Linux | `/etc/machine-id` | 文件读取 | 本地生成并持久化 |

**实现位置**: `electron-app/electron/main.ts` 或新建 `electron-app/electron/device-id.ts`

### 3.2 设备注册流程

```
首次启动
    ↓
生成设备ID (generateStableDeviceId)
    ↓
检查数据库是否存在
    ↓
不存在 → 注册新设备 → 初始化免费会员 → 赠送7天VIP试用
    ↓
存在 → 恢复设备信息 → 恢复会员信息 → 显示"欢迎回来"
```

**实现位置**: 
- Electron主进程: `app.on('ready')` 事件
- Python后端: `/api/device/register` 接口

### 3.3 重装处理

#### 3.3.1 检测逻辑

```typescript
async function detectReinstall(): Promise<{
  isReinstall: boolean;
  existingDeviceId?: string;
  existingMembership?: MembershipInfo;
}> {
  const deviceId = await generateStableDeviceId();
  const exists = await checkDeviceExists(deviceId);
  
  if (exists) {
    const membership = await getMembership(deviceId);
    return {
      isReinstall: true,
      existingDeviceId: deviceId,
      existingMembership: membership
    };
  }
  
  return { isReinstall: false };
}
```

#### 3.3.2 恢复流程

```
检测到重装
    ↓
加载设备信息
    ↓
恢复会员信息
    ↓
恢复消费记录
    ↓
显示欢迎对话框（"欢迎回来，您的会员信息已恢复"）
```

---

## 四、会员体系

### 4.1 会员等级定义

| 等级 | 代码 | 名称 | ASR额度/月 | LLM额度/月 | 客服支持 |
|-----|------|------|-----------|-----------|---------|
| FREE | `free` | 免费尝鲜 | 1小时 | 10万tokens | 标准支持（3天） |
| VIP | `vip` | VIP会员 | 10小时 | 100万tokens | 优先支持（24小时） |
| PRO | `pro` | PRO会员 | 50小时 | 500万tokens | VIP支持（12小时） |
| PRO+ | `pro_plus` | PRO+会员 | 200小时 | 2000万tokens | 专属支持（4小时） |

### 4.2 会员权益

**设计原则**: 所有功能模块全部开放，不同等级仅在额度和服务支持上有差异。

#### 4.2.1 共享功能（所有等级）

**所有会员（包括免费）均可使用以下功能**:
- ✅ 语音识别（ASR）
- ✅ 智能对话（LLM）
- ✅ 知识库功能（无限制）
- ✅ 历史记录查看
- ✅ 批量处理
- ✅ 所有导出功能（Markdown、Word、PDF等）
- ✅ 所有应用模块（Voice Note、Voice Chat、Voice Zen等）
- ✅ 自定义模型选择
- ✅ 数据导出工具

**差异点**: 仅在月度额度和客服支持上有区别

#### 4.2.2 FREE（免费尝鲜）

**月度额度**:
- ASR: 1小时（3,600,000ms）
- LLM: 10万tokens

**客服支持**:
- 标准支持（邮件响应，3个工作日内）

#### 4.2.3 VIP会员

**月度额度**:
- ASR: 10小时（36,000,000ms）
- LLM: 100万tokens

**客服支持**:
- 优先支持（邮件/微信响应，24小时内）

#### 4.2.4 PRO会员

**月度额度**:
- ASR: 50小时（180,000,000ms）
- LLM: 500万tokens

**客服支持**:
- VIP支持（邮件/微信/电话，12小时内）

#### 4.2.5 PRO+会员

**月度额度**:
- ASR: 200小时（720,000,000ms）
- LLM: 2000万tokens

**客服支持**:
- 专属支持（专属客服，4小时内响应）
- 专属客户经理（可选）

### 4.3 订阅周期

#### 4.3.1 支持的周期

- **1个月**: 灵活试用
- **3个月**: 季度订阅（9折优惠）
- **6个月**: 半年订阅（85折优惠）
- **12个月**: 年度订阅（8折优惠）

#### 4.3.2 周期规则

- ✅ 最小周期：1个月
- ✅ 最大周期：120个月（10年）
- ✅ 自由选择：1～120任意整数
- ❌ 无终身会员（避免漏洞）
- ✅ 过期处理：自动降级到免费

### 4.4 会员状态

| 状态 | 代码 | 说明 | 处理 |
|-----|------|------|------|
| 有效 | `active` | 会员在有效期内 | 正常使用 |
| 已过期 | `expired` | 会员已过期 | 降级到免费 |
| 试用中 | `trial` | 试用期内 | 限时体验 |
| 待激活 | `pending` | 已购买未激活 | 等待激活码 |

### 4.5 试用机制

#### 4.5.1 新用户试用

- **试用内容**: 7天VIP试用
- **试用权益**: 完整VIP权益
- **试用到期**: 自动降级到免费
- **试用限制**: 每设备仅限一次

#### 4.5.2 试用激活流程

```
用户首次启动
    ↓
注册免费会员
    ↓
检测是否新用户
    ↓
是 → 自动激活7天VIP试用
    ↓
显示试用提示: "已赠送7天VIP试用，尽情体验！"
```

---

## 五、消费计量

### 5.1 ASR消费计量

#### 5.1.1 计量依据

- **计费单位**: 毫秒（ms）
- **计量来源**: ASR响应中的 `time_info`
- **计算方式**: `duration_ms = end_time - start_time`
- **触发时机**: 当 `is_definite_utterance=true` 时记录

#### 5.1.2 统计时机

```
ASR返回确定结果（is_definite_utterance=true）
    ↓
提取 time_info (start_time, end_time)
    ↓
计算时长 duration_ms
    ↓
记录消费到数据库
    ↓
更新月度汇总
```

**集成位置**: 
- `src/providers/asr/volcano.py` → `_handle_recognition_result()` 方法
- 新增: `src/services/consumption_service.py`

#### 5.1.3 消费记录结构

```typescript
interface ASRConsumption {
  id: string;                 // UUID
  deviceId: string;           // 设备ID
  year: number;               // 年份
  month: number;              // 月份
  duration_ms: number;        // 时长（毫秒）
  start_time: number;         // 开始时间（毫秒时间戳）
  end_time: number;           // 结束时间（毫秒时间戳）
  provider: 'volcano';        // ASR提供商
  language: string;           // 语言（zh-CN/en-US）
  session_id: string;         // 会话ID
  timestamp: number;          // 记录时间戳
  created_at: string;         // 创建时间（ISO格式）
}
```

### 5.2 LLM消费计量

#### 5.2.1 计量依据

- **计费单位**: tokens
- **计量来源**: LiteLLM响应的 `usage` 字段
- **统计维度**: 
  - `prompt_tokens`: 输入tokens
  - `completion_tokens`: 输出tokens
  - `total_tokens`: 总tokens

#### 5.2.2 统计时机

```
LLM返回响应
    ↓
从响应中提取 usage 对象
    ↓
记录 prompt_tokens 和 completion_tokens
    ↓
记录消费到数据库
    ↓
更新月度汇总
```

**集成位置**: 
- `src/providers/llm/litellm_provider.py` → `chat()` 方法
- 新增: `src/services/consumption_service.py`

#### 5.2.3 消费记录结构

```typescript
interface LLMConsumption {
  id: string;                 // UUID
  deviceId: string;           // 设备ID
  year: number;               // 年份
  month: number;              // 月份
  prompt_tokens: number;      // 输入tokens
  completion_tokens: number;   // 输出tokens
  total_tokens: number;        // 总tokens
  model: string;              // 模型名称
  provider: string;           // LLM提供商
  request_id: string;         // 请求ID
  timestamp: number;          // 记录时间戳
  created_at: string;         // 创建时间（ISO格式）
}
```

### 5.3 额度检查

#### 5.3.1 前置检查

```typescript
// 在调用ASR/LLM前检查额度
async function checkQuotaBeforeUse(
  type: 'asr' | 'llm',
  estimatedAmount: number
): Promise<{ allowed: boolean; reason?: string }> {
  const quota = await getQuotaStatus();
  
  // 1. 检查会员是否有效
  if (!quota.isActive) {
    return { allowed: false, reason: '会员已过期，请续费' };
  }
  
  // 2. 检查额度是否足够
  if (type === 'asr' && quota.asr.remaining < estimatedAmount) {
    return { allowed: false, reason: 'ASR额度不足' };
  }
  
  if (type === 'llm' && quota.llm.remaining < estimatedAmount) {
    return { allowed: false, reason: 'LLM额度不足' };
  }
  
  return { allowed: true };
}
```

**实现位置**: 
- Python后端: `/api/quota/check` 接口
- 集成到: `src/services/voice_service.py` 和 `src/services/llm_service.py`

#### 5.3.2 超限处理

| 场景 | 处理方式 | UI提示 |
|-----|---------|--------|
| ASR额度不足 | 阻止录音 | "本月ASR额度已用完，请升级或等待下月重置" |
| LLM额度不足 | 拒绝对话 | "本月LLM额度已用完，请升级或等待下月重置" |
| 会员过期 | 降级到免费 | "会员已过期，已降级到免费版，请续费" |

### 5.4 月度重置

#### 5.4.1 重置时机

- **时间**: 每月1日 00:00:00（本地时间）
- **触发方式**: 
  - 应用启动时检查
  - 定时任务（每小时检查一次）

#### 5.4.2 重置流程

```
检测到新月份
    ↓
归档当月消费到历史表
    ↓
创建新的月度消费记录（初始值为0）
    ↓
重置计数器
    ↓
（可选）通知用户"额度已重置"
```

**实现位置**: 
- Python后端: `src/services/consumption_service.py` → `reset_monthly_quota()`
- 定时任务: 使用 APScheduler

---

## 六、激活码系统

### 6.1 激活码格式

#### 6.1.1 格式定义

```
格式: TIER-MONTHS-XXXX-XXXX
示例: VIP-3-A1B2-C3D4

组成:
- TIER: 会员等级（FREE/VIP/PRO/PROPLUS）
- MONTHS: 订阅月数（1～120）
- XXXX-XXXX: 8位校验码（随机生成，大写字母+数字）
```

#### 6.1.2 生成规则

```typescript
function generateActivationCode(
  tier: MembershipTier,
  months: number
): string {
  // 1. 会员等级代码
  const tierCode = tier.toUpperCase().replace('_', '');
  
  // 2. 生成8位随机校验码（A-Z, 0-9）
  const checksum = generateRandomCode(8);
  
  // 3. 组装激活码
  return `${tierCode}-${months}-${checksum.substring(0,4)}-${checksum.substring(4,8)}`;
}

// 示例输出:
// VIP-1-A1B2-C3D4
// PRO-3-X7Y8-Z9K2
// PROPLUS-12-M5N6-P7Q8
```

### 6.2 激活码验证

#### 6.2.1 验证流程

```
用户输入激活码
    ↓
格式验证（正则表达式）
    ↓
解析等级和月数
    ↓
验证等级有效性
    ↓
验证月数范围（1～120）
    ↓
检查本地黑名单（是否已使用）
    ↓
（可选）云端验证
    ↓
返回验证结果
```

#### 6.2.2 验证规则

```typescript
async function validateActivationCode(code: string): Promise<{
  valid: boolean;
  tier?: MembershipTier;
  months?: number;
  error?: string;
}> {
  // 1. 格式验证
  const pattern = /^([A-Z]+)-(\d+)-([A-Z0-9]{4})-([A-Z0-9]{4})$/;
  if (!pattern.test(code)) {
    return { valid: false, error: '激活码格式不正确' };
  }
  
  // 2. 解析内容
  const [, tierCode, monthsStr] = code.match(pattern)!;
  const tier = parseTier(tierCode); // VIP -> vip, PROPLUS -> pro_plus
  const months = parseInt(monthsStr);
  
  // 3. 验证有效性
  if (!tier) {
    return { valid: false, error: '无效的会员等级' };
  }
  
  if (months < 1 || months > 120) {
    return { valid: false, error: '无效的订阅周期' };
  }
  
  // 4. 检查是否已使用
  if (await isCodeUsed(code)) {
    return { valid: false, error: '激活码已被使用或已失效' };
  }
  
  return { valid: true, tier, months };
}
```

### 6.3 激活码管理

#### 6.3.1 生成工具（客服后台）

**功能需求**:
- 批量生成功能（一次生成1～1000个）
- 指定等级和月数
- 设置有效期（可选）
- 限制使用次数（默认1次）
- 导出为CSV/Excel

**实现方式**:
- 独立的管理工具（Python脚本或Web界面）
- 位置: `scripts/generate_activation_codes.py`

#### 6.3.2 使用记录（本地）

本地黑名单文件: `~/Library/Application Support/MindVoice/blacklist.json`

```json
{
  "codes": [
    "VIP-3-A1B2-C3D4",
    "PRO-6-X7Y8-Z9K2"
  ],
  "updated_at": 1704441600000
}
```

#### 6.3.3 云端服务（可选）

如果需要云端验证，可以建立：
- 激活码数据库（记录生成和使用）
- 验证API（`POST /api/activation/verify`）
- 黑名单同步（定期下载）

**当前规划**: 第一阶段仅本地验证，云端服务作为 Phase 2 扩展。

---

## 七、用户旅程

### 7.1 完整流程图

```
下载安装
    ↓
首次启动 → 生成设备ID → 注册免费会员 → 赠送7天VIP试用
    ↓
使用体验（试用期7天）
    ↓
试用到期 → 自动降级到免费
    ↓
继续使用免费额度
    ↓
额度不足提示
    ↓
联系客服 → 获取激活码
    ↓
输入激活码 → 验证成功 → 激活会员
    ↓
持续使用 → 实时显示消费和剩余天数
    ↓
到期前7/3/1天提醒
    ↓
到期 → 自动降级到免费 → 提示续费
    ↓
续费 → 在原有基础上延长
```

### 7.2 关键节点

#### 7.2.1 首次安装

```
启动应用
    ↓
显示欢迎界面（可选）
    ↓
说明：已赠送7天VIP试用
    ↓
引导完成基础设置
    ↓
开始使用
```

**UI展示**:
```
┌─────────────────────────────────┐
│  欢迎使用 MindVoice！            │
│  ═══════════════════════════════ │
│                                 │
│  🎁 已赠送7天VIP试用              │
│                                 │
│  试用期间享有：                  │
│  ✓ 10小时语音识别                │
│  ✓ 100万tokens对话               │
│  ✓ 知识库功能                    │
│  ✓ 优先支持                      │
│                                 │
│  [开始使用]                      │
└─────────────────────────────────┘
```

#### 7.2.2 试用到期

```
试用到期（自动）
    ↓
显示提示对话框
    ↓
"您的试用已结束，已降级到免费会员"
    ↓
按钮：[查看升级选项] [继续使用免费版]
```

#### 7.2.3 额度不足

```
尝试使用功能
    ↓
检测额度不足
    ↓
阻止操作 + 显示提示
    ↓
"本月额度已用完，请升级或等待下月重置"
    ↓
按钮：[联系客服] [查看详情] [取消]
```

#### 7.2.4 会员激活

```
用户点击"激活会员"
    ↓
显示激活界面
    ↓
输入激活码: VIP-3-XXXX-XXXX
    ↓
点击"激活"按钮
    ↓
验证中...
    ↓
成功 → "✅ 激活成功！VIP会员，有效期3个月"
失败 → "❌ 激活失败：激活码无效"
```

#### 7.2.5 到期提醒

```
距离过期7天
    ↓
显示提醒通知（非侵入式）
    ↓
"⚠ 您的会员还有7天过期，请及时续费"
    ↓
距离过期3天 → 再次提醒
    ↓
距离过期1天 → 最后提醒
```

---

## 八、UI/UX设计

### 8.1 会员信息界面

#### 8.1.1 布局设计

```
┌────────────────────────────────────┐
│  VIP会员                    [续费] │
│  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━  │
│                                    │
│  状态：✓ 有效                      │
│  剩余：25天                        │
│  到期时间：2026-02-05              │
│                                    │
│  ──────────────────────────────── │
│                                    │
│  本月额度使用情况                   │
│                                    │
│  ASR语音识别              80%      │
│  ████████████████░░░░              │
│  已用：8小时 | 剩余：2小时          │
│                                    │
│  LLM对话                  50%      │
│  ██████████░░░░░░░░░░              │
│  已用：50万 | 剩余：50万            │
│                                    │
│  下次重置：2026-02-01              │
│                                    │
│  ──────────────────────────────── │
│                                    │
│  会员权益                          │
│  ✓ 所有功能完全开放                │
│  ✓ 月度额度：10小时 + 100万tokens │
│  ✓ 优先客服支持（24小时响应）      │
│                                    │
│  [激活/续费] [消费历史] [联系客服] │
└────────────────────────────────────┘
```

**实现位置**: 
- 新建组件: `electron-app/src/components/apps/Membership/MembershipView.tsx`
- 样式文件: `electron-app/src/components/apps/Membership/MembershipView.css`

#### 8.1.2 状态指示

| 状态 | 颜色 | 图标 | 说明 |
|-----|------|------|------|
| 有效 | 绿色 (#4CAF50) | ✓ | 会员在有效期内 |
| 即将过期 | 橙色 (#FF9800) | ⚠ | 剩余7天以内 |
| 已过期 | 红色 (#F44336) | ✗ | 需要续费 |
| 试用中 | 蓝色 (#2196F3) | 🎁 | 试用期 |

### 8.2 激活界面

```
┌────────────────────────────────────┐
│  激活会员                           │
│  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━  │
│                                    │
│  当前状态                           │
│  等级：免费尝鲜                     │
│  剩余天数：15天                     │
│  到期时间：2026-01-20               │
│                                    │
│  ──────────────────────────────── │
│                                    │
│  激活码                            │
│  ┌──────────────────────────────┐ │
│  │ VIP-3-XXXX-XXXX              │ │
│  └──────────────────────────────┘ │
│           [激活]                   │
│                                    │
│  提示：激活码格式为                 │
│  TIER-MONTHS-XXXX-XXXX             │
│  示例：VIP-3-A1B2-C3D4             │
│                                    │
│  ──────────────────────────────── │
│                                    │
│  没有激活码？                       │
│  [联系客服获取激活码]               │
│                                    │
└────────────────────────────────────┘
```

**实现位置**: 
- 新建组件: `electron-app/src/components/apps/Membership/ActivationView.tsx`

### 8.3 消费历史界面

```
┌────────────────────────────────────┐
│  消费历史                           │
│  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━  │
│                                    │
│  [2026年1月] [2025年12月] [更多]   │
│                                    │
│  2026年1月统计                     │
│  ASR: 8小时 (28,800,000ms)        │
│  LLM: 50万tokens                   │
│  记录数: 156条                      │
│                                    │
│  ──────────────────────────────── │
│                                    │
│  详细记录                           │
│                                    │
│  2026-01-05 14:30                  │
│  ASR | 15分钟 | 会议录音            │
│                                    │
│  2026-01-05 10:20                  │
│  LLM | 5000 tokens | 智能对话      │
│                                    │
│  2026-01-04 16:45                  │
│  ASR | 30分钟 | 讲座记录            │
│                                    │
│  [加载更多]                         │
│                                    │
└────────────────────────────────────┘
```

**实现位置**: 
- 新建组件: `electron-app/src/components/apps/Membership/ConsumptionHistoryView.tsx`

### 8.4 实时提示

#### 8.4.1 非侵入式提示（主界面角标）

```
┌─ 主界面右下角 ─┐
│  ASR: 80% ⚠   │
│  LLM: 50%     │
└───────────────┘
```

**实现位置**: 
- 新建组件: `electron-app/src/components/shared/QuotaIndicator.tsx`
- 集成到: `electron-app/src/App.tsx`

#### 8.4.2 侵入式对话框（超限时）

```
┌─────────────────────────────────────┐
│  ⚠ 额度不足                          │
│  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ │
│                                     │
│  您本月的ASR额度已用完。             │
│                                     │
│  当前额度：1小时                     │
│  已使用：1小时                       │
│  剩余：0小时                         │
│                                     │
│  请升级会员或等待下月重置。          │
│  下次重置：2026-02-01                │
│                                     │
│  [联系客服] [查看详情] [知道了]      │
└─────────────────────────────────────┘
```

**实现方式**: Electron的 `dialog.showMessageBox()`

---

## 九、数据库设计

### 9.1 现有数据库结构

**当前数据库**: `~/Library/Application Support/MindVoice/database/history.db`

```sql
-- 现有表结构（不变）
CREATE TABLE IF NOT EXISTS records (
  id TEXT PRIMARY KEY,
  text TEXT NOT NULL,
  metadata TEXT,
  app_type TEXT NOT NULL DEFAULT 'voice-note',
  created_at TIMESTAMP NOT NULL
);
```

### 9.2 新增表结构

#### 9.2.1 设备信息表

```sql
CREATE TABLE IF NOT EXISTS devices (
  device_id TEXT PRIMARY KEY,
  machine_id TEXT NOT NULL,
  platform TEXT NOT NULL,
  first_install_time TIMESTAMP NOT NULL,
  last_active_time TIMESTAMP NOT NULL,
  install_count INTEGER DEFAULT 1,
  created_at TIMESTAMP NOT NULL
);

CREATE INDEX idx_devices_machine_id ON devices(machine_id);
```

#### 9.2.2 会员信息表

```sql
CREATE TABLE IF NOT EXISTS memberships (
  device_id TEXT PRIMARY KEY,
  tier TEXT NOT NULL DEFAULT 'free',
  status TEXT NOT NULL DEFAULT 'active',
  subscription_period INTEGER NOT NULL DEFAULT 1,
  activated_at TIMESTAMP NOT NULL,
  expires_at TIMESTAMP NOT NULL,
  is_trial INTEGER NOT NULL DEFAULT 0,
  trial_ends_at TIMESTAMP,
  auto_renew INTEGER NOT NULL DEFAULT 0,
  created_at TIMESTAMP NOT NULL,
  updated_at TIMESTAMP NOT NULL,
  FOREIGN KEY (device_id) REFERENCES devices(device_id),
  CHECK (subscription_period >= 1 AND subscription_period <= 120),
  CHECK (tier IN ('free', 'vip', 'pro', 'pro_plus')),
  CHECK (status IN ('active', 'expired', 'trial', 'pending'))
);

CREATE INDEX idx_memberships_status ON memberships(status, expires_at);
CREATE INDEX idx_memberships_tier ON memberships(tier);
```

#### 9.2.3 消费记录表

```sql
CREATE TABLE IF NOT EXISTS consumption_records (
  id TEXT PRIMARY KEY,
  device_id TEXT NOT NULL,
  year INTEGER NOT NULL,
  month INTEGER NOT NULL,
  type TEXT NOT NULL,
  amount REAL NOT NULL,
  unit TEXT NOT NULL,
  details TEXT,
  session_id TEXT,
  timestamp TIMESTAMP NOT NULL,
  created_at TIMESTAMP NOT NULL,
  FOREIGN KEY (device_id) REFERENCES devices(device_id),
  CHECK (type IN ('asr', 'llm')),
  CHECK (unit IN ('ms', 'tokens')),
  CHECK (amount >= 0)
);

CREATE INDEX idx_consumption_device_time 
  ON consumption_records(device_id, year, month, timestamp DESC);
CREATE INDEX idx_consumption_type 
  ON consumption_records(device_id, type);
```

#### 9.2.4 月度消费汇总表

```sql
CREATE TABLE IF NOT EXISTS monthly_consumption (
  device_id TEXT NOT NULL,
  year INTEGER NOT NULL,
  month INTEGER NOT NULL,
  asr_duration_ms INTEGER NOT NULL DEFAULT 0,
  llm_prompt_tokens INTEGER NOT NULL DEFAULT 0,
  llm_completion_tokens INTEGER NOT NULL DEFAULT 0,
  llm_total_tokens INTEGER NOT NULL DEFAULT 0,
  record_count INTEGER NOT NULL DEFAULT 0,
  created_at TIMESTAMP NOT NULL,
  updated_at TIMESTAMP NOT NULL,
  PRIMARY KEY (device_id, year, month),
  FOREIGN KEY (device_id) REFERENCES devices(device_id),
  CHECK (asr_duration_ms >= 0),
  CHECK (llm_total_tokens >= 0)
);

CREATE INDEX idx_monthly_consumption_device 
  ON monthly_consumption(device_id, year DESC, month DESC);
```

#### 9.2.5 会员升级历史表

```sql
CREATE TABLE IF NOT EXISTS membership_history (
  id TEXT PRIMARY KEY,
  device_id TEXT NOT NULL,
  from_tier TEXT NOT NULL,
  to_tier TEXT NOT NULL,
  subscription_period INTEGER NOT NULL,
  activated_at TIMESTAMP NOT NULL,
  expires_at TIMESTAMP NOT NULL,
  created_at TIMESTAMP NOT NULL,
  FOREIGN KEY (device_id) REFERENCES devices(device_id),
  CHECK (subscription_period >= 1)
);

CREATE INDEX idx_membership_history_device 
  ON membership_history(device_id, activated_at DESC);
```

### 9.3 数据迁移

#### 9.3.1 迁移脚本位置

- 脚本文件: `scripts/migrate_database.py`
- 执行方式: `python scripts/migrate_database.py`

#### 9.3.2 迁移步骤

```python
# scripts/migrate_database.py
def migrate_database():
    # 1. 连接到现有数据库
    # 2. 检查版本表
    # 3. 执行未应用的迁移
    # 4. 更新版本号
    pass
```

#### 9.3.3 版本管理

```sql
CREATE TABLE IF NOT EXISTS schema_version (
  version INTEGER PRIMARY KEY,
  applied_at TIMESTAMP NOT NULL,
  description TEXT
);

-- 初始版本
INSERT INTO schema_version (version, applied_at, description)
VALUES (1, CURRENT_TIMESTAMP, '会员体系初始版本');
```

---

## 十、API接口

### 10.1 设备管理

#### GET /api/device/info
获取设备信息

**响应**:
```json
{
  "success": true,
  "data": {
    "device_id": "abc123-def456-...",
    "platform": "darwin",
    "first_install_time": "2026-01-05T10:00:00",
    "last_active_time": "2026-01-05T15:30:00",
    "install_count": 1
  }
}
```

#### POST /api/device/register
注册新设备（首次安装）

**请求**:
```json
{
  "machine_id": "machine-xxx",
  "platform": "darwin"
}
```

**响应**:
```json
{
  "success": true,
  "data": {
    "device_id": "abc123-def456-...",
    "membership": {
      "tier": "free",
      "is_trial": true,
      "trial_ends_at": "2026-01-12T10:00:00"
    }
  }
}
```

### 10.2 会员管理

#### GET /api/membership/info
获取会员信息

**响应**:
```json
{
  "success": true,
  "data": {
    "tier": "vip",
    "status": "active",
    "days_remaining": 25,
    "activated_at": "2026-01-05T10:00:00",
    "expires_at": "2026-02-05T10:00:00",
    "subscription_period": 1,
    "is_trial": false,
    "quota": {
      "asr_duration_ms_monthly": 36000000,
      "llm_tokens_monthly": 1000000
    }
  }
}
```

#### POST /api/membership/activate
激活会员

**请求**:
```json
{
  "activation_code": "VIP-3-A1B2-C3D4"
}
```

**响应**:
```json
{
  "success": true,
  "message": "激活成功！VIP会员，有效期3个月",
  "data": {
    "tier": "vip",
    "expires_at": "2026-04-05T10:00:00",
    "days_remaining": 90
  }
}
```

#### POST /api/membership/renew
续费会员

**请求**:
```json
{
  "months": 3
}
```

**响应**:
```json
{
  "success": true,
  "message": "续费成功！",
  "data": {
    "tier": "vip",
    "expires_at": "2026-05-05T10:00:00",
    "days_remaining": 120
  }
}
```

### 10.3 消费统计

#### GET /api/consumption/current
获取当月消费

**响应**:
```json
{
  "success": true,
  "data": {
    "year": 2026,
    "month": 1,
    "asr": {
      "used": 28800000,
      "limit": 36000000,
      "remaining": 7200000,
      "percentage": 80.0
    },
    "llm": {
      "used": 500000,
      "limit": 1000000,
      "remaining": 500000,
      "percentage": 50.0
    },
    "reset_at": "2026-02-01T00:00:00"
  }
}
```

#### GET /api/consumption/history
获取历史消费

**参数**:
- `year`: 年份（必填）
- `month`: 月份（可选，1-12）
- `type`: 类型（可选，asr/llm）
- `limit`: 限制条数（默认100）
- `offset`: 偏移量（默认0）

**响应**:
```json
{
  "success": true,
  "data": {
    "year": 2026,
    "month": 1,
    "records": [
      {
        "id": "record-1",
        "type": "asr",
        "amount": 900000,
        "unit": "ms",
        "timestamp": "2026-01-05T14:30:00",
        "details": {
          "duration_ms": 900000,
          "start_time": 1704441600000,
          "end_time": 1704442500000
        }
      }
    ],
    "total": 156
  }
}
```

### 10.4 配额检查

#### POST /api/quota/check
检查额度是否足够

**请求**:
```json
{
  "type": "asr",
  "estimated_amount": 600000
}
```

**响应**:
```json
{
  "success": true,
  "data": {
    "allowed": true
  }
}
```

或额度不足：
```json
{
  "success": false,
  "data": {
    "allowed": false,
    "reason": "ASR额度不足，剩余120000ms，需要600000ms"
  }
}
```

### 10.5 激活码验证

#### POST /api/activation/validate
验证激活码

**请求**:
```json
{
  "code": "VIP-3-A1B2-C3D4"
}
```

**响应**:
```json
{
  "success": true,
  "data": {
    "valid": true,
    "tier": "vip",
    "months": 3
  }
}
```

或验证失败：
```json
{
  "success": false,
  "error": "激活码格式不正确"
}
```

---

## 十一、安全机制

### 11.1 设备绑定安全

#### 11.1.1 防伪造

- ✅ 设备ID基于硬件信息，难以伪造
- ✅ 使用SHA-256哈希，不可逆
- ✅ 添加盐值，增加破解难度
- ✅ UUID格式，不暴露硬件信息

#### 11.1.2 防多设备

- ✅ 一个激活码只能绑定一个设备
- ✅ 激活后加入黑名单，不可重复使用
- ✅ 本地存储黑名单，离线验证

### 11.2 激活码安全

#### 11.2.1 生成安全

- ✅ 使用加密安全的随机数生成器（`crypto.randomBytes()`）
- ✅ 校验码长度足够（8位，36^8 ≈ 2.8万亿种组合）
- ✅ 格式明确，易于验证
- ✅ 包含会员信息，便于追溯

#### 11.2.2 验证安全

```typescript
// 多层验证
async function secureValidation(code: string): Promise<boolean> {
  // 1. 格式验证（正则表达式）
  // 2. 内容验证（等级、月数）
  // 3. 黑名单验证（是否已使用）
  // 4. 时效性验证（可选，激活码过期时间）
  // 5. 云端验证（可选，Phase 2）
}
```

### 11.3 数据安全

#### 11.3.1 本地加密

- ✅ 敏感数据加密存储（激活码黑名单）
- ✅ 使用AES-256加密算法
- ✅ 密钥派生自设备ID（PBKDF2）
- ✅ 数据库文件权限控制（chmod 600）

#### 11.3.2 传输安全

- ✅ 本地通信（Electron IPC）
- ✅ 数据完整性校验
- ⏳ HTTPS通信（如果有云端服务，Phase 2）
- ⏳ 防重放攻击（如果有云端服务，Phase 2）

### 11.4 防作弊

#### 11.4.1 消费记录校验

```typescript
function validateConsumption(record: ConsumptionRecord): boolean {
  // 1. 时间戳不能是未来
  if (record.timestamp > Date.now()) {
    return false;
  }
  
  // 2. 消费量在合理范围
  if (record.type === 'asr' && record.amount > 10 * 60 * 60 * 1000) {
    return false; // 单次不超过10小时
  }
  
  if (record.type === 'llm' && record.amount > 1000000) {
    return false; // 单次不超过100万tokens
  }
  
  // 3. 设备ID匹配
  // 4. 记录完整性校验
  
  return true;
}
```

#### 11.4.2 异常检测

| 异常情况 | 检测规则 | 处理方式 |
|---------|---------|---------|
| 短时间大量消费 | 1小时内消费超过日常10倍 | 标记异常，人工审核 |
| 同一设备多次激活 | 7天内激活超过3次 | 限制激活，联系客服 |
| 时间篡改 | 系统时间异常回退 | 拒绝记录，提示用户 |
| 数据库篡改 | 消费记录不连续 | 标记异常，重新验证 |

---

## 十二、运营支持

### 12.1 客服后台系统

#### 12.1.1 功能模块

**核心功能**:
- ✅ 激活码生成与管理
- ✅ 用户查询（通过设备ID）
- ✅ 会员信息查看
- ✅ 消费记录查询
- ✅ 手动续费/升级
- ⏳ 工单系统（Phase 2）

#### 12.1.2 激活码生成工具

**实现方式**: Python脚本

```bash
# 生成激活码
python scripts/generate_activation_codes.py \
  --tier vip \
  --months 3 \
  --count 100 \
  --output codes.csv
```

**输出格式** (CSV):
```csv
激活码,等级,月数,生成时间,状态
VIP-3-A1B2-C3D4,vip,3,2026-01-05 10:00:00,未使用
VIP-3-X7Y8-Z9K2,vip,3,2026-01-05 10:00:00,未使用
```

### 12.2 用户反馈

#### 12.2.1 反馈渠道

**官方渠道**:
- 应用内反馈按钮
- 邮箱：support@mindvoice.com
- 微信客服：MindVoice-Support
- GitHub Issues（技术问题）

#### 12.2.2 反馈处理流程

```
用户提交反馈
    ↓
自动收集环境信息（设备ID、会员等级、版本号）
    ↓
客服接收工单
    ↓
分类处理
    ├── 技术问题 → 技术团队
    ├── 商务问题 → 商务团队
    └── 其他问题 → 客服团队
    ↓
回复用户（24小时内响应）
    ↓
关闭工单（记录处理结果）
```

### 12.3 数据统计

#### 12.3.1 运营指标

**关键指标**:
- 📊 总设备数
- 📊 各等级会员数（FREE/VIP/PRO/PRO+）
- 📊 新增/流失用户（日/周/月）
- 📊 消费统计（ASR总时长、LLM总tokens）
- 📊 激活码使用率
- 📊 续费率
- 📊 试用转化率

#### 12.3.2 报表系统

**报表类型**:
- 📈 日报：新增用户、激活会员、消费统计
- 📈 周报：消费趋势、会员变化、异常检测
- 📈 月报：完整数据分析、收入预测、优化建议

**实现方式**: 
- 统计脚本: `scripts/generate_report.py`
- 数据导出: CSV/Excel/JSON
- 可视化: 可选集成 Grafana（Phase 2）

---

## 十三、技术实施

### 13.1 实施阶段

#### 阶段一：基础框架（2周）

**Week 1-2: 核心基础设施**

**任务清单**:
- [x] 设备ID生成模块（`device-id.ts`）
  - macOS: 系统序列号/Hardware UUID
  - Windows: 机器GUID
  - Linux: /etc/machine-id
- [x] 数据库表结构设计
- [x] 数据库迁移脚本（`migrate_database.py`）
- [x] 会员信息管理服务（`membership_service.py`）
- [x] 基础UI框架（React组件骨架）

**交付物**:
- ✅ 设备ID生成和存储
- ✅ 数据库初始化脚本
- ✅ 会员信息CRUD接口
- ✅ 基础UI组件（空框架）
- ✅ 确认所有功能模块无权限检查（全部开放）

**测试验证**:
- 设备ID生成测试（同一机器多次生成应相同）
- 数据库创建测试
- API接口测试（Postman/curl）
- 功能访问测试（免费用户可访问所有功能）

#### 阶段二：消费计量（2-3周）

**Week 3-5: 消费统计与额度管理**

**任务清单**:
- [ ] ASR消费统计
  - 集成到 `volcano.py` 的 `_handle_recognition_result()`
  - 提取 time_info，计算 duration_ms
- [ ] LLM消费统计
  - 集成到 `litellm_provider.py` 的 `chat()`
  - 提取 usage 对象
- [ ] 消费服务（`consumption_service.py`）
  - 记录消费
  - 月度汇总
  - 额度检查（仅检查额度，不检查功能权限）
- [ ] 月度重置机制（定时任务）
- [ ] 额度检查前置验证（仅验证额度是否足够）

**简化说明**:
- ✅ 无需实现功能权限控制
- ✅ 仅需实现额度检查逻辑
- ✅ 减少约30%的开发工作量

**交付物**:
- ✅ 消费记录完整流程
- ✅ 实时额度监控
- ✅ 超限处理机制
- ✅ API接口（/api/consumption/*）

**测试验证**:
- 消费记录准确性测试
- 额度计算测试
- 超限阻止测试
- 月度重置测试

#### 阶段三：激活码系统（1-2周）

**Week 6-7: 激活码生成与验证**

**任务清单**:
- [ ] 激活码生成规则（`generate_activation_codes.py`）
- [ ] 激活码验证逻辑（`activation_service.py`）
- [ ] 激活界面（`ActivationView.tsx`）
- [ ] 黑名单管理（本地JSON）
- [ ] API接口（/api/activation/*）

**交付物**:
- ✅ 激活码生成工具（脚本）
- ✅ 激活流程完整实现
- ✅ 激活界面（UI）
- ✅ 验证逻辑（前端+后端）

**测试验证**:
- 激活码格式验证测试
- 激活成功测试
- 重复使用阻止测试
- 黑名单机制测试

#### 阶段四：UI完善（1-2周）

**Week 8-9: 用户界面与体验**

**任务清单**:
- [ ] 会员信息界面（`MembershipView.tsx`）
- [ ] 消费统计界面（`ConsumptionHistoryView.tsx`）
- [ ] 实时提示组件（`QuotaIndicator.tsx`）
- [ ] 到期提醒功能（对话框）
- [ ] 试用机制UI（欢迎界面）
- [ ] 样式优化（CSS）

**交付物**:
- ✅ 完整的用户界面
- ✅ 实时提示系统
- ✅ 到期提醒功能
- ✅ 响应式设计

**测试验证**:
- UI交互测试
- 不同屏幕分辨率测试
- 状态更新实时性测试

#### 阶段五：测试与优化（1周）

**Week 10: 全面测试与优化**

**任务清单**:
- [ ] 功能测试（完整流程）
- [ ] 安全测试（防作弊、防篡改）
- [ ] 性能优化
  - 数据库查询优化
  - UI响应速度优化
  - 内存占用优化
- [ ] 用户体验优化
  - 错误提示优化
  - 加载状态优化
  - 引导流程优化
- [ ] 文档完善

**交付物**:
- ✅ 测试报告
- ✅ Bug修复清单
- ✅ 性能优化报告
- ✅ 用户手册

**测试验证**:
- 完整流程测试（从安装到续费）
- 边界情况测试
- 压力测试
- 安全测试

### 13.2 技术栈

#### 13.2.1 前端（Electron + React）

| 技术 | 版本 | 用途 |
|-----|------|------|
| Electron | 当前项目版本 | 桌面应用框架 |
| React | 18.x | UI框架 |
| TypeScript | 5.x | 类型安全 |
| Vite | 当前项目版本 | 构建工具 |

**新增依赖**:
```json
{
  "crypto": "^1.0.1",
  "@types/crypto": "^1.0.0"
}
```

#### 13.2.2 后端（Python + FastAPI）

| 技术 | 版本 | 用途 |
|-----|------|------|
| FastAPI | 当前项目版本 | API框架 |
| SQLAlchemy | 2.x | ORM |
| Pydantic | 2.x | 数据验证 |
| APScheduler | 3.x | 定时任务 |

**新增依赖** (`requirements.txt`):
```txt
apscheduler>=3.10.0
```

#### 13.2.3 数据库

| 技术 | 版本 | 用途 |
|-----|------|------|
| SQLite | 3.x | 本地数据库 |

**数据库文件**:
- 现有: `history.db`（历史记录）
- 新增: `membership.db`（会员信息）
- 新增: `consumption.db`（消费记录）

**注意**: 也可以考虑统一到一个数据库文件，通过表前缀区分。

#### 13.2.4 工具

| 工具 | 用途 |
|-----|------|
| Git | 版本控制 |
| ESLint | 代码检查（前端） |
| Prettier | 代码格式化 |
| Black | 代码格式化（Python） |
| pytest | 单元测试（Python） |
| Jest | 单元测试（前端） |

---

## 十四、测试计划

### 14.1 功能测试

#### 14.1.1 设备识别

测试用例:
- [ ] TC-D-001: 首次安装生成设备ID
- [ ] TC-D-002: 重新安装恢复设备ID（设备ID应相同）
- [ ] TC-D-003: 不同机器生成不同ID
- [ ] TC-D-004: 硬件更换检测（可选）
- [ ] TC-D-005: 降级方案（无法获取硬件信息时）

#### 14.1.2 会员管理

测试用例:
- [ ] TC-M-001: 免费用户注册
- [ ] TC-M-002: 试用机制（7天VIP）
- [ ] TC-M-003: 会员激活（输入激活码）
- [ ] TC-M-004: 会员续费（在原有基础上延长）
- [ ] TC-M-005: 会员升级（从VIP到PRO）
- [ ] TC-M-006: 自动降级（到期后降级到免费）
- [ ] TC-M-007: 会员状态显示（有效/过期/试用）
- [ ] TC-M-008: 功能访问（所有等级均可访问所有功能）

#### 14.1.3 消费计量

测试用例:
- [ ] TC-C-001: ASR消费记录（准确记录时长）
- [ ] TC-C-002: LLM消费记录（准确记录tokens）
- [ ] TC-C-003: 月度汇总（正确累加）
- [ ] TC-C-004: 额度检查（正确判断是否超限）
- [ ] TC-C-005: 超限处理（阻止操作）
- [ ] TC-C-006: 月度重置（正确重置为0）
- [ ] TC-C-007: 消费历史查询

#### 14.1.4 激活码

测试用例:
- [ ] TC-A-001: 激活码生成（格式正确）
- [ ] TC-A-002: 激活码验证（格式验证）
- [ ] TC-A-003: 激活码使用（成功激活）
- [ ] TC-A-004: 重复使用阻止（黑名单机制）
- [ ] TC-A-005: 无效激活码拒绝

### 14.2 安全测试

测试用例:
- [ ] TC-S-001: 设备ID伪造测试（应无法伪造）
- [ ] TC-S-002: 激活码重复使用测试（应被阻止）
- [ ] TC-S-003: 数据篡改测试（应被检测）
- [ ] TC-S-004: 时间篡改测试（应被检测）
- [ ] TC-S-005: SQL注入测试（应被防护）
- [ ] TC-S-006: 异常消费检测（应被标记）

### 14.3 性能测试

测试指标:
- [ ] 设备ID生成性能: < 100ms
- [ ] 数据库查询性能: < 50ms
- [ ] UI响应速度: < 200ms
- [ ] 大量消费记录处理: < 1s (10000条)
- [ ] 内存占用: < 200MB（增量）

### 14.4 兼容性测试

平台测试:
- [ ] macOS 11+ (Big Sur及以上)
- [ ] macOS 12+ (Monterey)
- [ ] macOS 13+ (Ventura)
- [ ] macOS 14+ (Sonoma)
- [ ] Windows 10+
- [ ] Windows 11
- [ ] Ubuntu 20.04+
- [ ] Ubuntu 22.04+

分辨率测试:
- [ ] 1920x1080 (Full HD)
- [ ] 2560x1440 (2K)
- [ ] 3840x2160 (4K)
- [ ] 1366x768 (笔记本常见分辨率)

---

## 十五、部署与运维

### 15.1 部署方案

#### 15.1.1 本地部署（Phase 1）

**当前方案**: 完全本地化
- ✅ 数据存储在用户本地
- ✅ 无需服务器
- ✅ 激活码验证本地化
- ✅ 离线可用

**部署步骤**:
1. 用户下载安装包
2. 安装到本地
3. 首次启动自动初始化
4. 开始使用

#### 15.1.2 云端服务（Phase 2，可选）

**未来扩展**: 云端辅助
- ⏳ 激活码验证服务
- ⏳ 黑名单同步服务
- ⏳ 数据备份服务
- ⏳ 运营数据统计

### 15.2 监控

#### 15.2.1 本地监控

**日志系统**:
- 应用日志: `logs/mindvoice_YYYYMMDD.log`
- 错误日志: `logs/errors_YYYYMMDD.log`
- API日志: `logs/api_server_YYYYMMDD.log`

**监控内容**:
- 启动/关闭事件
- 会员激活事件
- 消费记录事件
- 异常错误事件

#### 15.2.2 云端监控（Phase 2，可选）

**未来扩展**:
- 激活码使用统计
- 会员分布统计
- 消费趋势分析
- 异常检测告警

### 15.3 数据备份

#### 15.3.1 自动备份

**备份策略**:
- ✅ 每日自动备份
- ✅ 保留最近30天备份
- ✅ 备份位置: `~/Library/Application Support/MindVoice/backups/`

**备份内容**:
- 设备信息 (`device.json`)
- 会员信息 (`membership.db`)
- 消费记录 (`consumption.db`)

**实现方式**: 定时任务（每日凌晨2点）

#### 15.3.2 手动备份

**用户操作**:
- 设置 → 数据管理 → 导出数据
- 导出格式: ZIP压缩包
- 包含: 所有数据库文件 + 配置文件

**恢复操作**:
- 设置 → 数据管理 → 导入数据
- 选择备份文件
- 自动恢复数据

---

## 十六、合规性

### 16.1 隐私保护

#### 16.1.1 数据收集

**收集内容**:
- ✅ 设备ID（匿名化，基于硬件哈希）
- ✅ 消费统计数据（时长、tokens）
- ✅ 会员信息（等级、过期时间）
- ✅ 应用使用日志

**不收集**:
- ❌ 个人身份信息（姓名、邮箱、电话）
- ❌ 录音内容
- ❌ 聊天内容
- ❌ 地理位置
- ❌ 浏览记录

**用户控制**:
- ✅ 用户可查看收集的数据
- ✅ 用户可导出所有数据
- ✅ 用户可删除所有数据（卸载时）

#### 16.1.2 数据存储

**存储原则**:
- ✅ 本地存储为主
- ✅ 加密敏感数据（激活码黑名单）
- ✅ 用户完全控制
- ✅ 卸载后可选择删除或保留

**数据安全**:
- ✅ 文件权限控制（chmod 600）
- ✅ 数据库访问控制
- ✅ 定期备份

#### 16.1.3 隐私政策

**政策内容** (需要法务审核):
1. 收集什么数据
2. 如何使用数据
3. 如何保护数据
4. 用户的权利
5. 数据保留期限
6. 联系方式

**展示位置**:
- 首次安装时展示（同意后继续）
- 设置 → 关于 → 隐私政策
- 官网提供完整版本

### 16.2 用户协议

#### 16.2.1 服务条款

**核心内容**:
1. **服务说明**: 会员权益、额度规则
2. **使用规范**: 禁止行为、违规处理
3. **退款政策**: 
   - 激活码未使用可退款
   - 已激活不可退款
   - 特殊情况协商处理
4. **责任限制**: 服务中断、数据丢失等
5. **协议变更**: 提前30天通知

#### 16.2.2 免责声明

**免责内容**:
1. **服务可用性**: 尽力保证但不保证100%可用
2. **数据准确性**: ASR/LLM结果仅供参考
3. **第三方服务**: 火山引擎ASR、LiteLLM等
4. **不可抗力**: 网络故障、硬件故障等

---

## 十七、未来扩展

### 17.1 云端同步（Phase 2）

**功能规划**:
- ⏳ 多设备共享会员（同一账号多设备）
- ⏳ 云端数据备份（自动同步）
- ⏳ 跨平台使用（macOS、Windows、Linux）
- ⏳ 移动端支持（iOS、Android）

**技术方案**:
- 用户账号体系（邮箱/手机号注册）
- 云端数据库（PostgreSQL）
- 同步服务（REST API）
- OAuth2认证

### 17.2 推广系统（Phase 2）

**功能规划**:
- ⏳ 推荐码机制（推荐好友获得奖励）
- ⏳ 推荐奖励（赠送额度/延长会员）
- ⏳ 团队订阅（企业批量购买）
- ⏳ 分销系统（合作伙伴）

**奖励规则**:
- 推荐1人: 赠送1天VIP
- 推荐5人: 赠送1周VIP
- 推荐10人: 赠送1月VIP

### 17.3 企业版（Phase 3）

**功能规划**:
- ⏳ 企业账户管理（多用户管理）
- ⏳ 统一计费（企业统一付费）
- ⏳ 使用报表（管理员查看团队使用情况）
- ⏳ 企业额度池（共享额度，灵活分配）

**定价模式**:
- 按用户数计费
- 企业额度池（共享）
- 专属客户经理
- SLA保障

### 17.4 增值服务（Phase 3）

**服务内容**:
- ⏳ 自定义模型训练（针对特定领域）
- ⏳ 专业数据分析（使用报告、优化建议）
- ⏳ 定制化部署（私有化部署）
- ⏳ 技术咨询服务（集成支持）
- ⏳ 白标服务（品牌定制）

---

## 附录

### A. 配置示例

#### A.1 会员配置（新增到 config.yml）

```yaml
# 会员体系配置
membership:
  # 默认会员等级
  default_tier: free
  
  # 是否启用试用
  enable_trial: true
  trial_days: 7
  trial_tier: vip
  
  # 会员额度配置（单位：ASR为毫秒，LLM为tokens）
  quotas:
    free:
      asr_duration_ms_monthly: 3600000        # 1小时 = 60*60*1000ms
      llm_tokens_monthly: 100000               # 10万tokens
    vip:
      asr_duration_ms_monthly: 36000000       # 10小时
      llm_tokens_monthly: 1000000              # 100万tokens
    pro:
      asr_duration_ms_monthly: 180000000      # 50小时
      llm_tokens_monthly: 5000000              # 500万tokens
    pro_plus:
      asr_duration_ms_monthly: 720000000      # 200小时
      llm_tokens_monthly: 20000000             # 2000万tokens
  
  # 订阅周期配置
  subscription_periods:
    - months: 1
      name: "1个月"
      discount: 0
    - months: 3
      name: "3个月"
      discount: 0.1    # 9折
    - months: 6
      name: "6个月"
      discount: 0.15   # 85折
    - months: 12
      name: "年付"
      discount: 0.2    # 8折
  
  # 订阅周期限制
  period_limits:
    min_months: 1
    max_months: 120    # 最多10年
  
  # 过期提醒配置
  expiration_reminders:
    days_before: [7, 3, 1]
  
  # 自动降级配置
  auto_downgrade:
    enabled: true
    downgrade_to: free
    default_period: 1
```

### B. API接口汇总

#### B.1 设备管理

| 方法 | 路径 | 说明 |
|-----|------|------|
| GET | /api/device/info | 获取设备信息 |
| POST | /api/device/register | 注册新设备 |

#### B.2 会员管理

| 方法 | 路径 | 说明 |
|-----|------|------|
| GET | /api/membership/info | 获取会员信息 |
| POST | /api/membership/activate | 激活会员 |
| POST | /api/membership/renew | 续费会员 |
| POST | /api/membership/upgrade | 升级会员 |

#### B.3 消费统计

| 方法 | 路径 | 说明 |
|-----|------|------|
| GET | /api/consumption/current | 获取当月消费 |
| GET | /api/consumption/history | 获取历史消费 |
| POST | /api/quota/check | 检查额度 |

#### B.4 激活码

| 方法 | 路径 | 说明 |
|-----|------|------|
| POST | /api/activation/validate | 验证激活码 |

### C. 数据库表关系

```
devices (设备表)
    ↓ 1:1
memberships (会员表)
    ↓ 1:N
consumption_records (消费记录表)
    ↓ N:1
monthly_consumption (月度汇总表)

devices (设备表)
    ↓ 1:N
membership_history (会员历史表)
```

### D. 错误码

| 错误码 | 说明 | 处理建议 |
|-------|------|---------|
| E001 | 设备ID生成失败 | 检查硬件信息获取 |
| E002 | 会员信息不存在 | 重新注册 |
| E003 | 激活码格式错误 | 检查激活码格式 |
| E004 | 激活码已使用 | 联系客服 |
| E005 | 激活码无效 | 联系客服 |
| E006 | 额度不足 | 升级会员或等待重置 |
| E007 | 会员已过期 | 续费 |
| E008 | 数据库错误 | 检查数据库文件 |

### E. 参考资料

**官方文档**:
- [Electron 文档](https://www.electronjs.org/docs)
- [FastAPI 文档](https://fastapi.tiangolo.com/)
- [SQLite 文档](https://www.sqlite.org/docs.html)
- [React 文档](https://react.dev/)

**技术参考**:
- [Electron IPC 通信](https://www.electronjs.org/docs/latest/tutorial/ipc)
- [Python APScheduler](https://apscheduler.readthedocs.io/)
- [SQLAlchemy ORM](https://docs.sqlalchemy.org/)

**安全参考**:
- [OWASP Top 10](https://owasp.org/www-project-top-ten/)
- [Node.js 安全最佳实践](https://nodejs.org/en/docs/guides/security/)

### F. 联系方式

**项目相关**:
- 开发者：深圳王哥 & AI
- 邮箱：manwjh@126.com
- GitHub: [MindVoice](https://github.com/mindvoice/mindvoice)

**客服支持**:
- 技术支持：tech@mindvoice.com
- 商务合作：business@mindvoice.com
- 客服邮箱：support@mindvoice.com
- 客服微信：MindVoice-Support

---

## 版本历史

| 版本 | 日期 | 说明 | 作者 |
|-----|------|------|------|
| v1.0 | 2026-01-05 | 初始版本 | 深圳王哥 & AI |

---

**文档状态**: 📝 规划阶段  
**当前项目版本**: v1.8.0  
**最后更新**: 2026-01-05  
**维护者**: MindVoice 团队

---

**📌 重要提示**:

1. 本文档是完整的规划文档，实际实施时请按阶段推进
2. 各阶段交付物需要经过充分测试再进入下一阶段
3. 用户隐私和数据安全是最高优先级
4. 保持与现有代码库的兼容性
5. 定期更新文档，记录实施过程中的调整

**🚀 开始实施**: 请参考"十三、技术实施"章节的阶段划分

---

*End of Document*

