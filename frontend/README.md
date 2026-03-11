# Windows流媒体服务 - 前端项目

## 项目简介

这是Windows流媒体服务的前端项目，基于Vue 3 + Element Plus开发。

## 技术栈

- Vue 3.4+
- Vue Router 4.2+
- Pinia 2.1+
- Element Plus 2.5+
- Vite 5.0+
- ECharts 5.5+
- Axios 1.6+

## 项目结构

```
frontend/
├── src/
│   ├── api/              # API接口
│   ├── assets/           # 静态资源
│   ├── components/       # 公共组件
│   ├── router/           # 路由配置
│   ├── stores/           # 状态管理
│   ├── styles/           # 全局样式
│   ├── views/            # 页面组件
│   ├── App.vue           # 根组件
│   └── main.js           # 入口文件
├── index.html            # HTML模板
├── package.json          # 项目配置
└── vite.config.js        # Vite配置
```

## 安装依赖

```bash
cd frontend
npm install
```

## 开发运行

```bash
npm run dev
```

访问地址：http://localhost:5173

## 生产构建

```bash
npm run build
```

构建产物将输出到 `dist/` 目录。

## 功能模块

### 仪表盘
- 媒体文件统计
- 类型分布图表
- 质量分布图表
- 快捷操作入口

### 媒体库管理
- 媒体文件列表
- 文件搜索与筛选
- 文件详情查看
- 批量操作

### 扫描管理
- 扫描任务管理
- 监控路径配置
- 实时扫描进度

### 识别管理
- 待识别文件列表
- 批量识别
- 手动指定识别
- 识别结果确认

### 整理管理
- 待整理文件列表
- 整理预览
- 批量整理
- 整理规则配置

### 系统管理
- 服务状态监控
- 系统资源监控
- 配置管理
- 日志查看

## 开发说明

### API接口

所有API请求通过 `src/api/request.js` 统一封装，已配置：
- 请求拦截器：添加认证信息
- 响应拦截器：统一错误处理
- 自动重试机制

### 路由配置

路由配置在 `src/router/index.js` 中，支持：
- 懒加载
- 路由守卫
- 面包屑导航

### 状态管理

使用Pinia进行状态管理，stores目录下按模块划分：
- user - 用户状态
- media - 媒体库状态
- scan - 扫描状态
- recognition - 识别状态
- organize - 整理状态

### 样式规范

- 使用SCSS预处理器
- 遵循BEM命名规范
- 响应式设计
- 暗色主题支持

## 注意事项

1. 开发环境API代理已配置到 http://localhost:8000
2. 生产环境需要根据实际后端地址修改baseURL
3. 所有API调用需要替换为实际接口
4. WebSocket连接需要配合后端实现

## 许可证

MIT License
