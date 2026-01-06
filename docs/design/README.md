# 技术设计与架构

本目录包含 MindVoice 的技术设计文档、架构说明和技术规范。

## 📚 文档列表

### 核心架构
- [系统架构](SYSTEM_ARCHITECTURE.md) - 整体系统架构设计，技术栈选型

### 数据存储
- [数据库设计](DATABASE_SCHEMA.md) - 数据库表结构和字段说明
- [数据库版本](DATABASE_VERSION.md) - 数据库版本管理和迁移记录
- [跨平台存储](CROSS_PLATFORM_STORAGE.md) - 多平台数据存储方案

### 功能设计
- [图片处理](IMAGE_HANDLING.md) - 图片上传、存储和恢复规范
- [双向翻译](TRANSLATION_BIDIRECTIONAL.md) - 实时语音翻译技术实现
- [自动保存服务](AutoSaveService_技术文档.md) - 自动保存服务设计和实现

### 前端技术
- [状态管理](状态管理_简洁版.md) - React 状态管理方案

## 🎯 推荐阅读顺序

1. **了解项目**: [系统架构](SYSTEM_ARCHITECTURE.md)
2. **数据设计**: [数据库设计](DATABASE_SCHEMA.md) → [跨平台存储](CROSS_PLATFORM_STORAGE.md)
3. **核心功能**: [图片处理](IMAGE_HANDLING.md) → [双向翻译](TRANSLATION_BIDIRECTIONAL.md)
4. **前端实现**: [状态管理](状态管理_简洁版.md) → [自动保存服务](AutoSaveService_技术文档.md)

## 🔙 返回

[返回文档中心](../README.md)

