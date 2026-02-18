# USMSB 前端 UI/UX 规范检查报告

**项目:** USMSB SDK Frontend  
**测试日期:** 2026-02-16  
**测试人员:** UI Tester  
**测试范围:** 样式规范、响应式设计、国际化、可访问性

---

## 一、样式规范检查

### 1.1 Tailwind 配置分析

**文件:** `tailwind.config.js`

#### 优点
- 定义了完整的 primary (蓝色系) 和 secondary (灰色系) 颜色变量
- 使用标准的 50-900 色阶系统
- content 配置正确指向源文件

#### 问题

| 级别 | 问题 | 描述 |
|------|------|------|
| CRITICAL | 缺少响应式断点自定义配置 | 未扩展 screens 配置 |
| CRITICAL | 缺少深色模式配置 | 未设置 darkMode: 'class' |
| WARNING | 缺少字体大小扩展配置 | 未定义自定义 fontSize |
| WARNING | 缺少间距自定义配置 | 未扩展 spacing |
| WARNING | 缺少阴影自定义配置 | 未扩展 boxShadow |
| INFO | 缺少动画配置 | 未定义自定义 animation |

### 1.2 颜色主题一致性

#### 已使用颜色
- **primary:** #0ea5e9 (蓝色 - 主品牌色)
- **secondary:** #64748b (灰色 - 辅助色)
- **green:** #22c55e (成功状态)
- **red:** #ef4444 (错误状态)
- **yellow:** #eab308 (警告状态)
- **purple:** #a855f7 (特殊标记)

#### 问题

| 级别 | 问题 | 建议 |
|------|------|------|
| WARNING | 代码中存在硬编码颜色值 | 使用 CSS 变量替代 #fff, #e2e8f0 等 |
| WARNING | Tooltip 组件使用内联样式 | 统一使用 Tailwind 类 |
| INFO | 缺少语义化颜色变量 | 添加 success, warning, error, info |

### 1.3 字体大小规范

#### 已使用字体大小
| 类名 | 大小 | 使用场景 |
|------|------|----------|
| text-xs | 12px | 辅助文本、标签 |
| text-sm | 14px | 次要文本 |
| text-base | 16px | 正文（默认） |
| text-lg | 18px | 小标题 |
| text-xl | 20px | 副标题 |
| text-2xl | 24px | 页面标题 |

#### 问题
- INFO: 未定义 line-height 自定义值
- INFO: 缺少超大标题样式 (text-3xl ~ text-6xl)

### 1.4 间距规范

#### 已使用间距
- **Padding:** p-1 ~ p-6 (4px ~ 24px)
- **Gap:** gap-1 ~ gap-6
- **Space:** space-y-4, space-y-6
- **Margin:** m-1, mt-2, mb-4 等

#### 问题
- INFO: 缺少统一间距变量定义
- INFO: 部分 margin 值不一致

### 1.5 组件样式检查

#### 按钮样式一致性

**定义样式 (index.css):**
```css
.btn { @apply px-4 py-2 rounded-lg font-medium transition-colors duration-200; }
.btn-primary { @apply bg-primary-600 text-white hover:bg-primary-700; }
.btn-secondary { @apply bg-secondary-200 text-secondary-800 hover:bg-secondary-300; }
```

**问题:**

| 级别 | 问题 | 位置 |
|------|------|------|
| CRITICAL | 按钮样式不一致 | Header.tsx 使用 "px-4 py-2 bg-primary-600..." |
| CRITICAL | 按钮样式不一致 | PublishService.tsx 使用 "btn btn-primary" |
| CRITICAL | 按钮样式不一致 | ConnectButton.tsx 使用 "px-6 py-3 bg-primary-600" |
| WARNING | 无 :active 状态 | index.css |
| WARNING | 无 :focus-visible 状态 | index.css |
| WARNING | 无 :disabled 详细样式 | index.css |
| WARNING | 缺少 outline 按钮 | - |
| WARNING | 缺少 ghost 按钮 | - |
| WARNING | 缺少 danger 按钮 | - |

#### 表单元素样式

**定义样式 (index.css):**
```css
.input { @apply w-full px-3 py-2 border border-secondary-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500; }
.label { @apply block text-sm font-medium text-secondary-700 mb-1; }
```

**问题:**

| 级别 | 问题 | 位置 |
|------|------|------|
| CRITICAL | 表单元素不一致 | Settings.tsx select 使用 "input" 类 |
| CRITICAL | 表单元素不一致 | ActiveMatching.tsx textarea 使用 "input min-h-[80px]" |
| WARNING | 无 checkbox 自定义样式 | - |
| WARNING | 无 radio 自定义样式 | - |
| WARNING | 无 file input 样式 | - |
| WARNING | 无 error 状态 | - |
| WARNING | 无 success 状态 | - |

#### 卡片样式

**定义样式 (index.css):**
```css
.card { @apply bg-white rounded-xl shadow-sm border border-secondary-200 p-6; }
```

**问题:**
- INFO: 卡片样式基本一致
- WARNING: 存在变体卡片 (bg-blue-50, bg-green-50) 未统一
- INFO: 缺少卡片尺寸变体

---

## 二、响应式设计检查

### 2.1 断点使用情况

| 断点 | 宽度 | 使用情况 |
|------|------|----------|
| sm | 640px | 少量使用 (LanguageSwitcher) |
| md | 768px | 中等使用 (网格布局) |
| lg | 1024px | 大量使用 (侧边栏、网格) |
| xl | 1280px | **未使用** |
| 2xl | 1536px | **未使用** |

### 2.2 桌面端布局检查

**侧边栏:**
- 固定定位 (fixed)
- 展开宽度: 256px (w-64)
- 折叠宽度: 80px (w-20)
- 过渡动画: duration-300

**内容区域:**
- 响应式网格: grid-cols-1 md:grid-cols-2 lg:grid-cols-4
- 卡片布局: 基本响应式

**问题:**
- CRITICAL: 缺少 xl/2xl 断点处理
- WARNING: 侧边栏固定宽度，大屏幕可能过窄

### 2.3 移动端适配检查

**当前状态:**
- body 设置 min-width: 320px
- LanguageSwitcher 使用 hidden sm:inline 隐藏文本

**严重问题:**

| 问题 | 位置 | 影响 |
|------|------|------|
| Sidebar 无移动端汉堡菜单 | Sidebar.tsx | 移动端无法导航 |
| Header 搜索框固定宽度 w-96 | Header.tsx | 小屏幕溢出 |
| 表单在小屏幕可能溢出 | 多个页面 | 布局问题 |
| 图表组件无响应式处理 | Dashboard.tsx | 显示异常 |

**触摸友好性问题:**

| 问题 | 标准 | 当前状态 |
|------|------|----------|
| 按钮最小尺寸 | 44x44px | 部分不达标 |
| 触摸目标间距 | 8px+ | 未考虑 |

### 2.4 响应式问题汇总

```
+------------------------------------------+
| 检查项              | 桌面端 | 平板 | 移动端 |
|--------------------|--------|------|--------|
| 侧边栏导航          | OK     | OK   | FAIL   |
| 搜索框             | OK     | WARN | FAIL   |
| 统计卡片网格        | OK     | OK   | OK     |
| 图表显示           | OK     | WARN | FAIL   |
| 表单布局           | OK     | OK   | WARN   |
| 用户菜单           | OK     | OK   | WARN   |
+------------------------------------------+
```

---

## 三、国际化检查

### 3.1 i18n 配置

**依赖包:**
- i18next: ^25.8.7
- react-i18next: ^16.5.4
- i18next-browser-languagedetector: ^8.2.1

**支持语言:**

| 代码 | 语言 | 状态 |
|------|------|------|
| en | English | 支持 |
| zh | 中文 | 支持 |
| ja | 日本語 | 支持 |
| ko | 한국어 | 支持 |
| ru | Русский | 支持 |
| fr | Français | 支持 |
| de | Deutsch | 支持 |
| es | Español | 支持 |
| pt | Português | 支持 |

**优点:**
- 支持 9 种语言
- 使用语言自动检测
- 组件封装良好 (LanguageSwitcher)

### 3.2 语言切换功能

**LanguageSwitcher 组件:**
- 下拉菜单形式
- 显示国旗和语言名称
- 点击外部自动关闭
- 键盘支持基本

**问题:**
- WARNING: 切换后无持久化 (localStorage)
- INFO: 无语言偏好保存

### 3.3 翻译完整性检查

#### 翻译覆盖模块
- common: 通用文本
- nav: 导航
- dashboard: 仪表板
- agents: Agent 管理
- matching: 智能匹配
- settings: 设置
- onboarding: 引导流程
- publishService: 发布服务
- publishDemand: 发布需求
- simulations: 模拟
- analytics: 分析
- marketplace: 市场
- governance: 治理

#### 硬编码文本问题 (CRITICAL)

**Sidebar.tsx:**
```
Line 39-41: 快捷操作区域
- "发布我的服务" (应使用 t('sidebar.publishService'))
- "发布我的需求" (应使用 t('sidebar.publishDemand'))
- "快捷操作" (应使用 t('sidebar.quickActions'))
- "让AI Agent发现您" (应使用 t('sidebar.publishServiceDesc'))
- "让服务方找您" (应使用 t('sidebar.publishDemandDesc'))
```

**Header.tsx:**
```
Line 108-109: "VIBE staked"
Line 114: "Rep:"
Line 123: "Wallet Address"
Line 143-149: "Staked", "Reputation"
Line 159-167: "发布我的服务", "发布我的需求"
Line 175: "Profile Settings"
Line 182: "Disconnect Wallet"
Line 195: "Sign to Verify"
```

**Dashboard.tsx:**
```
Line 121-122: "发布我的服务", "发布我的需求"
Line 82-83: "Growing", "Stable", "Active", "No activity"
```

**PublishService.tsx / PublishDemand.tsx:**
```
- 标题和提示信息硬编码
- categories 数组全部硬编码中文
- 约 20+ 处硬编码/文件
```

**Agents.tsx:**
```
Line 119: "AI Agents"
Line 134: "Register AI Agent"
约 15+ 处硬编码
```

**ActiveMatching.tsx:**
```
useCaseExamples 数组全部硬编码中文
概念说明卡片全部硬编码
约 30+ 处硬编码
```

### 3.4 翻译问题统计

| 文件 | 硬编码数量 | 严重程度 |
|------|------------|----------|
| Sidebar.tsx | 5 | CRITICAL |
| Header.tsx | 12 | CRITICAL |
| Dashboard.tsx | 8 | CRITICAL |
| PublishService.tsx | 20+ | CRITICAL |
| PublishDemand.tsx | 20+ | CRITICAL |
| Agents.tsx | 15+ | CRITICAL |
| ActiveMatching.tsx | 30+ | CRITICAL |
| **总计** | **110+** | - |

---

## 四、可访问性检查

### 4.1 ARIA 属性检查

| 级别 | 问题 | 位置 | 建议 |
|------|------|------|------|
| CRITICAL | 侧边栏折叠按钮无 aria-expanded | Sidebar.tsx:60-65 | 添加 aria-expanded={sidebarOpen} |
| CRITICAL | 下拉菜单无 role="menu" | Header.tsx:120, ConnectButton.tsx:48 | 添加 role="menu" |
| CRITICAL | 菜单项无 role="menuitem" | 多处 | 添加 role="menuitem" |
| CRITICAL | 模态框无 aria-modal | Header.tsx:206-210 | 添加 aria-modal="true" |
| CRITICAL | 表单字段无 aria-describedby | 多个表单 | 添加关联描述 |
| CRITICAL | 错误提示无 role="alert" | 多处 | 添加 role="alert" |

### 4.2 语义化问题

| 问题 | 位置 | 建议 |
|------|------|------|
| 使用 div 代替 button | 多处点击元素 | 使用 <button> |
| 图标无 aria-label | 所有图标组件 | 添加 aria-label |
| 表格无 scope | 如有表格 | 添加 scope 属性 |

### 4.3 键盘导航

| 级别 | 问题 | 影响 |
|------|------|------|
| CRITICAL | 下拉菜单无法用键盘打开 | 无法访问菜单 |
| CRITICAL | 侧边栏导航无 focus 管理 | Tab 顺序混乱 |
| CRITICAL | 无 skip-to-content 链接 | 键盘用户效率低 |
| WARNING | Tab 顺序不明确 | 用户体验差 |

### 4.4 颜色对比度

**WCAG 2.1 标准:**
- 正常文本: 4.5:1
- 大文本: 3:1
- UI 组件: 3:1

**检查结果:**

| 颜色组合 | 对比度 | 结果 |
|----------|--------|------|
| primary-600 on white | 4.58:1 | PASS |
| secondary-500 on white | 4.52:1 | PASS |
| secondary-600 on white | 5.91:1 | PASS |
| primary-500 on white | 3.28:1 | PASS (小文本) |
| secondary-400 on white | 2.95:1 | **FAIL** |
| secondary-300 on white | 2.11:1 | **FAIL** |

---

## 五、改进建议

### 5.1 紧急修复 (P0) - 必须立即处理

#### 1. 完善翻译
```typescript
// 创建独立的翻译文件
// src/i18n/locales/en.json
// src/i18n/locales/zh.json

// 将所有硬编码文本移至翻译文件
// 示例:
// Sidebar.tsx
{ name: t('sidebar.publishService'), ... }

// 建立翻译键命名规范
// 模块.组件.元素: "sidebar.quickActions.publishService"
```

#### 2. 添加移动端导航
```tsx
// 建议实现:
// 1. 移动端汉堡菜单按钮
// 2. 抽屉式侧边栏 (Drawer)
// 3. 底部导航栏 (BottomNav)

// 移动端布局示例:
<div className="md:hidden">
  <button onClick={toggleMobileMenu}>
    <MenuIcon />
  </button>
  {mobileMenuOpen && (
    <MobileDrawer onClose={closeMobileMenu}>
      <Navigation />
    </MobileDrawer>
  )}
</div>
```

#### 3. 修复可访问性
```tsx
// 侧边栏按钮
<button
  onClick={() => setSidebarOpen(!sidebarOpen)}
  aria-expanded={sidebarOpen}
  aria-label="Toggle navigation menu"
>

// 下拉菜单
<div role="menu" aria-label="User menu">
  <button role="menuitem">Profile</button>
  <button role="menuitem">Settings</button>
</div>

// 添加 skip-to-content
<a href="#main-content" className="sr-only focus:not-sr-only">
  Skip to main content
</a>
```

### 5.2 短期改进 (P1) - 下一迭代处理

#### 1. 统一组件库

**Button 组件:**
```tsx
// src/components/ui/Button.tsx
interface ButtonProps {
  variant: 'primary' | 'secondary' | 'outline' | 'ghost' | 'danger';
  size: 'sm' | 'md' | 'lg';
  disabled?: boolean;
  loading?: boolean;
}

// 变体样式
const variants = {
  primary: 'bg-primary-600 text-white hover:bg-primary-700',
  secondary: 'bg-secondary-200 text-secondary-800 hover:bg-secondary-300',
  outline: 'border-2 border-primary-600 text-primary-600 hover:bg-primary-50',
  ghost: 'text-secondary-600 hover:bg-secondary-100',
  danger: 'bg-red-600 text-white hover:bg-red-700',
};

// 尺寸样式
const sizes = {
  sm: 'px-3 py-1.5 text-sm',
  md: 'px-4 py-2 text-base',
  lg: 'px-6 py-3 text-lg',
};
```

**Input 组件:**
```tsx
// src/components/ui/Input.tsx
interface InputProps {
  status?: 'default' | 'error' | 'success';
  disabled?: boolean;
}

const statusStyles = {
  default: 'border-secondary-300 focus:ring-primary-500',
  error: 'border-red-500 focus:ring-red-500',
  success: 'border-green-500 focus:ring-green-500',
};
```

#### 2. 完善 Tailwind 配置
```javascript
// tailwind.config.js
module.exports = {
  darkMode: 'class',
  theme: {
    extend: {
      screens: {
        'xs': '475px',
        '3xl': '1920px',
      },
      colors: {
        success: { /* 色阶 */ },
        warning: { /* 色阶 */ },
        error: { /* 色阶 */ },
      },
    },
  },
}
```

#### 3. 响应式优化
```tsx
// Header 搜索框
<div className="relative w-full md:w-64 lg:w-96">
  <Search className="..." />
  <input className="w-full ..." />
</div>
```

### 5.3 长期优化 (P2) - 后续版本

#### 1. 建立设计系统
- 创建 Design Tokens 文件
- 使用 Storybook 建立组件文档
- 编写设计规范文档

#### 2. 性能优化
- 组件懒加载
- 图片优化 (WebP, 响应式图片)
- CSS 优化 (PurgeCSS)

#### 3. 测试覆盖
- 添加视觉回归测试
- 添加可访问性测试 (jest-axe)
- 添加 E2E 测试

---

## 六、问题汇总表

### 6.1 严重问题 (CRITICAL)

| # | 问题 | 位置 | 影响 | 优先级 |
|---|------|------|------|--------|
| 1 | 翻译不完整，中英混杂 | 多个文件 | 国际化失效 | P0 |
| 2 | 移动端导航缺失 | Sidebar.tsx | 移动端不可用 | P0 |
| 3 | ARIA 属性缺失 | 全局 | 可访问性不合规 | P0 |
| 4 | 键盘导航不完整 | Header, Sidebar | 可访问性问题 | P0 |
| 5 | 按钮样式不统一 | 多个文件 | 视觉一致性差 | P1 |
| 6 | 表单组件不统一 | 多个文件 | 维护困难 | P1 |
| 7 | 深色模式未实现 | tailwind.config.js | 用户体验 | P2 |
| 8 | 缺少响应式断点 | Layout | 大屏幕体验 | P2 |

### 6.2 警告问题 (WARNING)

| # | 问题 | 位置 | 建议 |
|---|------|------|------|
| 1 | 硬编码颜色值 | 多处 | 使用 CSS 变量 |
| 2 | 颜色对比度不足 | secondary-400 | 加深颜色 |
| 3 | 无按钮状态样式 | index.css | 添加 hover/active/focus |
| 4 | 语言切换无持久化 | LanguageSwitcher | 使用 localStorage |
| 5 | 缺少按钮变体 | index.css | 添加 outline/ghost/danger |
| 6 | 图标无 aria-label | 图标组件 | 添加无障碍标签 |

### 6.3 信息类问题 (INFO)

| # | 问题 | 建议 |
|---|------|------|
| 1 | 缺少字体大小扩展 | 添加 3xl-6xl |
| 2 | 缺少间距变量 | 定义 spacing scale |
| 3 | 缺少阴影变量 | 定义 boxShadow scale |
| 4 | 缺少动画配置 | 添加 transition 配置 |
| 5 | 无面包屑组件 | 添加 Breadcrumb 组件 |

---

## 七、ASCII 界面设计建议

### 7.1 建议的移动端导航结构

```
移动端布局:
+----------------------------------+
|  [H] USMSB SDK          [User]  |  <- Header with hamburger
+----------------------------------+
|                                  |
|      Main Content Area           |
|                                  |
|                                  |
+----------------------------------+
| [Home] [Agents] [Match] [More]  |  <- Bottom navigation
+----------------------------------+

Hamburger Menu (opened):
+------------------+
| USMSB SDK    [X] |
+------------------+
| > Dashboard      |
| > Agents         |
| > Matching       |
| > Network        |
| > Collaborations |
| > Simulations    |
| > Analytics      |
| > Marketplace    |
| > Governance     |
+------------------+
| > Settings       |
+------------------+
```

### 7.2 建议的按钮变体系统

```
Primary:    [====== Action ======]  (solid blue)
Secondary:  [====== Action ======]  (solid gray)
Outline:    [====== Action ======]  (border only)
Ghost:          Action               (no border)
Danger:     [====== Action ======]  (solid red)
Disabled:   [====== Action ======]  (grayed out)

Sizes:
Small:      [=== Action ===]
Default:    [==== Action ====]
Large:      [===== Action =====]
```

### 7.3 建议的表单状态样式

```
Default:    [_________________]     (gray border)
Focused:    [_________________]     (blue ring)
Error:      [_________________]     (red border) + Error message
Success:    [_________________]     (green border) + Check icon
Disabled:   [_________________]     (gray background)
```

---

## 八、总结

### 评分

| 维度 | 评分 | 说明 |
|------|------|------|
| 样式规范 | 6/10 | 基础配置完成，但缺少扩展 |
| 组件一致性 | 5/10 | 存在较多不一致 |
| 响应式设计 | 4/10 | 移动端支持不足 |
| 国际化 | 5/10 | 框架完整，翻译不完整 |
| 可访问性 | 3/10 | ARIA 和键盘导航缺失 |
| **总体** | **4.6/10** | 需要大量改进 |

### 优先修复顺序

1. **翻译完整性** (P0) - 110+ 处硬编码文本
2. **移动端导航** (P0) - 无汉堡菜单
3. **ARIA 属性** (P0) - 可访问性合规
4. **组件统一** (P1) - Button, Input 组件
5. **响应式优化** (P1) - 搜索框、图表
6. **设计系统** (P2) - 长期维护

---

**报告生成时间:** 2026-02-16  
**测试工具:** 代码审查 + 手动检查  
**下一步:** 等待 team-lead 分配修复任务
