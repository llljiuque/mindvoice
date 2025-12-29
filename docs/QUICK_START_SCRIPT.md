# 快速启动脚本说明

## 概述

`quick_start.sh` 是一个自动化部署脚本，用于快速设置和运行 macOS 语音桌面助手。

## 功能

脚本会自动完成以下任务：

1. **环境检查**
   - 检查 Python 3.9+ 是否安装
   - 检查系统依赖（pip3 等）
   - 验证 macOS 系统

2. **虚拟环境管理**
   - 自动创建虚拟环境（如果不存在）
   - 升级 pip 到最新版本
   - 管理依赖安装标记

3. **依赖安装**
   - 自动安装 `requirements.txt` 中的所有依赖
   - 智能跳过已安装的依赖（通过 `.installed` 标记）

4. **配置检查**
   - 检查配置文件是否存在
   - 自动创建配置目录
   - 复制示例配置文件（如果不存在）

5. **权限提醒**
   - 提醒用户授予麦克风权限

6. **验证安装**
   - 验证关键模块是否正确安装
   - 自动修复安装问题

7. **启动应用**
   - 启动主程序
   - 显示使用提示

## 使用方法

### 基本用法

```bash
# 一键部署和运行
./quick_start.sh
```

### 命令行选项

```bash
# 查看帮助信息
./quick_start.sh --help
./quick_start.sh -h

# 仅检查环境，不运行应用
./quick_start.sh --check-only

# 重新安装依赖
./quick_start.sh --reinstall

# 清理虚拟环境和缓存
./quick_start.sh --clean
```

## 脚本输出

脚本使用颜色编码的输出：

- 🔵 **蓝色 [INFO]**: 信息性消息
- 🟢 **绿色 [SUCCESS]**: 成功消息
- 🟡 **黄色 [WARNING]**: 警告消息
- 🔴 **红色 [ERROR]**: 错误消息

## 工作流程

```
开始
  ↓
检查 Python 环境
  ↓
检查系统依赖
  ↓
设置虚拟环境
  ↓
安装依赖
  ↓
检查配置
  ↓
检查权限
  ↓
验证安装
  ↓
启动应用
  ↓
结束
```

## 故障排除

### 问题：脚本无法执行

```bash
# 确保脚本有执行权限
chmod +x quick_start.sh
```

### 问题：Python 版本不兼容

脚本会检查 Python 版本，需要 3.9 或更高版本。如果版本过低，脚本会提示错误。

### 问题：依赖安装失败

```bash
# 清理并重新安装
./quick_start.sh --clean
./quick_start.sh
```

### 问题：虚拟环境损坏

```bash
# 清理虚拟环境
./quick_start.sh --clean

# 重新运行
./quick_start.sh
```

## 高级用法

### 在 CI/CD 中使用

```bash
# 仅检查环境
./quick_start.sh --check-only

# 检查退出码
if [ $? -eq 0 ]; then
    echo "环境检查通过"
else
    echo "环境检查失败"
    exit 1
fi
```

### 自定义 Python 路径

如果系统中有多个 Python 版本，可以修改脚本中的 `PYTHON_CMD` 变量：

```bash
# 编辑脚本
vim quick_start.sh

# 修改这一行
PYTHON_CMD="python3.11"  # 使用 Python 3.11
```

## 注意事项

1. **首次运行**：首次运行会创建虚拟环境并安装所有依赖，可能需要几分钟时间。

2. **权限要求**：脚本需要以下权限：
   - 读取项目文件
   - 创建虚拟环境目录
   - 安装 Python 包
   - 创建配置文件目录

3. **网络要求**：安装依赖需要网络连接。

4. **macOS 权限**：应用运行时需要麦克风权限，脚本会提醒但不会自动授予。

## 脚本维护

### 更新依赖

如果 `requirements.txt` 更新了，运行：

```bash
./quick_start.sh --reinstall
```

### 清理缓存

```bash
./quick_start.sh --clean
```

## 示例输出

```
[INFO] ==========================================
[INFO] macOS 语音桌面助手 - 快速启动
[INFO] ==========================================

[INFO] 检查 Python 环境...
[SUCCESS] Python 版本: 3.11.0
[INFO] 检查系统依赖...
[SUCCESS] 系统依赖检查通过
[INFO] 设置虚拟环境...
[INFO] 创建虚拟环境...
[SUCCESS] 虚拟环境创建成功
[INFO] 升级 pip...
[SUCCESS] 虚拟环境设置完成
[INFO] 安装项目依赖...
[SUCCESS] 依赖安装完成
[INFO] 检查配置...
[SUCCESS] 配置文件存在: /Users/username/.voice_assistant/config.json
[INFO] 检查 macOS 权限...
[INFO] 验证安装...
[SUCCESS] 所有关键模块验证通过

[SUCCESS] 所有检查完成，准备启动应用...

[INFO] 启动应用...
[INFO] ==========================================
[SUCCESS] macOS 语音桌面助手
[INFO] ==========================================
...
```
