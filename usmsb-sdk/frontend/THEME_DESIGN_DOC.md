# 前端主题系统重构 - 浅色模式设计文档

## 一、概述

本文档描述了 USMSB 前端项目的主题系统重构方案，重点解决浅色模式下颜色混乱、不一致的问题，同时确保深色模式（Cyberpunk 风格）不受影响。

### 设计目标
1. 建立统一的浅色模式设计系统
2. 保持深色模式的 Cyberpunk 风格不变
3. 所有页面（官网、文档、后台）支持深浅模式切换
4. 确保浅色/深色模式切换的一致性和可维护性

---

## 二、颜色系统

### 2.1 浅色模式设计系统

#### CSS 变量定义（index.css）

```css
:root {
  /* 背景色 */
  --bg-primary: #ffffff;      /* 主背景 - 纯白 */
  --bg-secondary: #f8fafc;    /* 次背景 - 极浅灰 */
  --bg-tertiary: #f1f5f9;    /* 第三背景 - 浅灰 */
  --bg-card: #ffffff;        /* 卡片背景 */
  
  /* 文字色 */
  --text-primary: #0f172a;    /* 主要文字 - 深蓝黑 */
  --text-secondary: #475569;  /* 次要文字 - 中灰 */
  --text-muted: #94a3b8;     /* 弱化文字 */
  
  /* 边框色 */
  --border-color: #e2e8f0;
  
  /* 强调色 - 柔和色调 */
  --accent-primary: #0ea5e9;   /* 蓝色 */
  --accent-secondary: #8b5cf6; /* 紫色 */
  --accent-success: #22c55e;   /* 绿色 */
  --accent-warning: #f59e0b;   /* 橙色 */
  --accent-danger: #ef4444;    /* 红色 */
  
  /* 阴影 */
  --shadow-sm: 0 1px 2px rgba(0, 0, 0, 0.05);
  --shadow-md: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
  --shadow-lg: 0 10px 15px -3px rgba(0, 0, 0, 0.1);
}
```

#### Tailwind 语义颜色配置（tailwind.config.js）

```javascript
colors: {
  // 浅色模式语义颜色
  light: {
    bg: {
      primary: '#ffffff',
      secondary: '#f8fafc',
      tertiary: '#f1f5f9',
      card: '#ffffff',
    },
    text: {
      primary: '#0f172a',
      secondary: '#475569',
      muted: '#94a3b8',
    },
    border: '#e2e8f0',
  },
  // ... 深色模式颜色配置保持不变
}
```

### 2.2 深色模式设计系统（Cyberpunk）

深色模式保持原有的 Cyberpunk 风格：

```css
.dark {
  --neon-blue: #00f5ff;
  --neon-purple: #bf00ff;
  --neon-pink: #ff00ff;
  --neon-green: #00ff88;
  --cyber-dark: #0a0a0f;
  --cyber-card: #0d0d14;
  --cyber-border: #1a1a2e;
}
```

---

## 三、使用规范

### 3.1 浅色模式颜色映射

| 旧样式 | 新样式 | 使用场景 |
|--------|--------|----------|
| `text-secondary-900` | `text-light-text-primary` | 标题、重要文字 |
| `text-secondary-800` | `text-light-text-primary` | 强调文字 |
| `text-secondary-700` | `text-light-text-secondary` | 正文 |
| `text-secondary-600` | `text-light-text-secondary` | 次要文字 |
| `text-secondary-500` | `text-light-text-muted` | 辅助文字 |
| `text-secondary-400` | `text-light-text-muted` | 弱化文字 |
| `bg-secondary-50` | `bg-light-bg-secondary` | 页面背景 |
| `bg-secondary-100` | `bg-light-bg-tertiary` | 卡片背景 |
| `bg-white` | `bg-white` | 保持不变 |
| `border-secondary-200` | `border-light-border` | 边框 |

### 3.2 深色模式颜色映射

深色模式保持使用原有的 Cyberpunk 变量：

| 样式 | 使用场景 |
|------|----------|
| `dark:text-neon-blue` | 主强调色文字 |
| `dark:text-neon-purple` | 次强调色文字 |
| `dark:text-neon-green` | 成功状态 |
| `dark:text-neon-pink` | 危险/错误状态 |
| `dark:bg-cyber-dark` | 页面背景 |
| `dark:bg-cyber-card` | 卡片背景 |
| `dark:border-neon-blue/20` | 边框 |

### 3.3 组件样式模式

每个组件应同时定义浅色和深色模式样式：

```tsx
// 示例：Button 组件
className={`
  /* 浅色模式 */
  bg-primary-600 text-white
  hover:bg-primary-700
  
  /* 深色模式 */
  dark:bg-gradient-to-r dark:from-neon-blue/20 dark:to-neon-purple/20
  dark:border dark:border-neon-blue dark:text-neon-blue
  dark:hover:shadow-[0_0_20px_rgba(0,245,255,0.4)]
`}
```

---

## 四、修改的文件清单

### 4.1 核心配置文件

| 文件 | 修改内容 |
|------|----------|
| `src/index.css` | CSS 变量定义、组件基础样式 |
| `tailwind.config.js` | 添加 `light` 语义颜色配置 |

### 4.2 布局组件

| 文件 | 修改内容 |
|------|----------|
| `src/components/Layout.tsx` | 主布局背景 |
| `src/components/Header.tsx` | 顶部导航栏 |
| `src/components/Sidebar.tsx` | 侧边栏 |
| `src/components/MobileDrawer.tsx` | 移动端抽屉 |

### 4.3 基础 UI 组件

| 文件 | 修改内容 |
|------|----------|
| `src/components/ui/Button.tsx` | 按钮样式 |
| `src/components/ui/Input.tsx` | 输入框样式 |
| `src/components/ui/Modal.tsx` | 模态框样式 |
| `src/components/ui/Select.tsx` | 下拉选择框 |
| `src/components/ui/Badge.tsx` | 徽章样式 |
| `src/components/ui/EmptyState.tsx` | 空状态组件 |
| `src/components/ui/Tooltip.tsx` | 工具提示 |
| `src/components/ui/HelpSystem.tsx` | 帮助系统 |
| `src/components/ui/TourGuide.tsx` | 引导教程 |
| `src/components/ui/Select.tsx` | 选择组件 |

### 4.4 功能组件

| 文件 | 修改内容 |
|------|----------|
| `src/components/ThemeToggle.tsx` | 主题切换器 |
| `src/components/LanguageSwitcher.tsx` | 语言切换器 |
| `src/components/FeatureSpotlight.tsx` | 功能亮点 |
| `src/components/WelcomeGuide.tsx` | 欢迎引导 |
| `src/components/StakeGuideModal.tsx` | 质押指南弹窗 |
| `src/components/ErrorBoundary.tsx` | 错误边界 |
| `src/components/ArchitectureDiagram.tsx` | 架构图 |

### 4.5 页面组件

| 文件 | 修改内容 |
|------|----------|
| `src/pages/Dashboard.tsx` | 仪表板 |
| `src/pages/Settings.tsx` | 设置页 |
| `src/pages/Onboarding.tsx` | 引导页 |
| `src/pages/ActiveMatching.tsx` | 智能匹配 |
| `src/pages/Collaborations.tsx` | 协作 |
| `src/pages/Governance.tsx` | 治理 |
| `src/pages/Marketplace.tsx` | 市场 |
| `src/pages/Simulations.tsx` | 模拟 |
| `src/pages/NetworkExplorer.tsx` | 网络浏览器 |
| `src/pages/Agents.tsx` | Agent 列表 |
| `src/pages/AgentDetail.tsx` | Agent 详情 |
| `src/pages/DocsPage.tsx` | 文档页 |
| `src/pages/LegalPage.tsx` | 法律页面 |
| `src/pages/PublishDemand.tsx` | 发布需求 |
| `src/pages/PublishService.tsx` | 发布服务 |
| `src/pages/RegisterAgent.tsx` | 注册 Agent |
| `src/pages/Analytics.tsx` | 分析 |
| `src/pages/LandingPage.tsx` | 落地页 |

---

## 五、验证清单

### 5.1 深色模式验证

- [x] 全局背景显示 Cyberpunk 暗色
- [x] 霓虹色强调效果正常
- [x] 卡片发光效果正常
- [x] 按钮 hover 效果正常
- [x] 网格背景动画正常

### 5.2 浅色模式验证

- [x] 全局背景为浅灰色 (#f8fafc)
- [x] 卡片背景为白色
- [x] 文字颜色对比度正确
- [x] 边框颜色清晰
- [x] 按钮样式正常

### 5.3 模式切换验证

- [x] 主题切换器功能正常
- [x] 切换时无闪烁
- [x] 所有页面同步切换
- [x] 刷新后主题状态保持

---

## 六、维护指南

### 6.1 添加新颜色

如需添加新的语义颜色，在 `tailwind.config.js` 的 `light` 对象中扩展：

```javascript
light: {
  bg: {
    primary: '#ffffff',
    secondary: '#f8fafc',
    tertiary: '#f1f5f9',
    card: '#ffffff',
    // 新增
    hover: '#e2e8f0',
  },
  // ...
}
```

### 6.2 添加新组件

新组件需同时定义浅色和深色模式样式：

```tsx
const MyComponent = () => {
  return (
    <div className={`
      /* 浅色模式 */
      bg-white text-light-text-primary border-light-border
      
      /* 深色模式 */
      dark:bg-cyber-card dark:text-neon-blue dark:border-neon-blue/20
    `}>
      Content
    </div>
  )
}
```

---

## 七、附录

### A. 颜色对比表

| 场景 | 浅色模式 | 深色模式 |
|------|----------|----------|
| 页面背景 | #f8fafc | #0a0a0f |
| 卡片背景 | #ffffff | #0d0d14 |
| 主要文字 | #0f172a | #e5e7eb |
| 次要文字 | #475569 | #9ca3af |
| 边框 | #e2e8f0 | rgba(0,245,255,0.2) |
| 主强调 | #0ea5e9 | #00f5ff |
| 次强调 | #8b5cf6 | #bf00ff |

### B. 字体配置

- 主字体: Rajdhani
- 标题字体: Orbitron
- 代码字体: JetBrains Mono

---

**文档版本**: 1.0  
**更新时间**: 2026-02-22  
**维护团队**: USMSB Frontend Team
