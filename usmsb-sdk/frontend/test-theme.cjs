/**
 * 主题系统测试脚本
 * 验证浅色模式重构是否符合设计文档规范
 */

const fs = require('fs');
const path = require('path');

const testResults = {
  passed: [],
  failed: [],
  warnings: []
};

function log(message, type = 'info') {
  const prefix = {
    info: 'ℹ',
    pass: '✓',
    fail: '✗',
    warn: '⚠'
  }[type];
  console.log(`${prefix} ${message}`);
}

function test(condition, testName, details = '') {
  if (condition) {
    testResults.passed.push(testName);
    log(`${testName}`, 'pass');
    if (details) log(`  ${details}`, 'info');
  } else {
    testResults.failed.push(testName);
    log(`${testName}`, 'fail');
    if (details) log(`  ${details}`, 'info');
  }
}

// 读取文件内容
function readFile(filePath) {
  try {
    return fs.readFileSync(filePath, 'utf8');
  } catch (e) {
    return null;
  }
}

console.log('\n========================================');
console.log('   主题系统测试 - 按设计文档验证');
console.log('========================================\n');

// ============================================
// 测试 1: CSS 变量定义验证
// ============================================
log('测试 1: CSS 变量定义 (index.css)', 'info');

const indexCss = readFile(path.join(__dirname, 'src/index.css'));

test(
  indexCss.includes('--bg-primary: #ffffff'),
  '1.1 背景主色变量定义正确',
  '--bg-primary: #ffffff'
);

test(
  indexCss.includes('--bg-secondary: #f0f9ff'),
  '1.2 背景次色变量定义正确',
  '--bg-secondary: #f0f9ff'
);

test(
  indexCss.includes('--bg-tertiary: #e0f2fe'),
  '1.3 背景第三色变量定义正确',
  '--bg-tertiary: #e0f2fe'
);

test(
  indexCss.includes('--text-primary: #1e3a8a'),
  '1.4 文字主色变量定义正确',
  '--text-primary: #1e3a8a'
);

test(
  indexCss.includes('--text-secondary: #1d4ed8'),
  '1.5 文字次色变量定义正确',
  '--text-secondary: #1d4ed8'
);

test(
  indexCss.includes('--text-muted: #3b82f6'),
  '1.6 文字弱化色变量定义正确',
  '--text-muted: #3b82f6'
);

test(
  indexCss.includes('--border-color: #bfdbfe'),
  '1.7 边框色变量定义正确',
  '--border-color: #bfdbfe'
);

test(
  indexCss.includes('--accent-primary: #2563eb'),
  '1.8 主强调色变量定义正确',
  '--accent-primary: #2563eb'
);

test(
  indexCss.includes('--accent-secondary: #7c3aed'),
  '1.9 次强调色变量定义正确',
  '--accent-secondary: #7c3aed'
);

// ============================================
// 测试 2: Tailwind 配置验证
// ============================================
log('\n测试 2: Tailwind 配置 (tailwind.config.js)', 'info');

const tailwindConfig = readFile(path.join(__dirname, 'tailwind.config.js'));

test(
  tailwindConfig.includes("light: {"),
  '2.1 浅色模式语义颜色配置存在',
  'light: {'
);

test(
  tailwindConfig.includes("bg: {"),
  '2.2 背景语义颜色配置存在',
  'bg: {'
);

test(
  tailwindConfig.includes("text: {"),
  '2.3 文字语义颜色配置存在',
  'text: {'
);

test(
  tailwindConfig.includes("primary: '#ffffff'"),
  '2.4 浅色 bg-primary 颜色正确',
  "primary: '#ffffff'"
);

test(
  tailwindConfig.includes("secondary: '#f0f9ff'"),
  '2.5 浅色 bg-secondary 颜色正确',
  "secondary: '#f0f9ff'"
);

test(
  tailwindConfig.includes("tertiary: '#e0f2fe'"),
  '2.6 浅色 bg-tertiary 颜色正确',
  "tertiary: '#e0f2fe'"
);

test(
  tailwindConfig.includes("primary: '#1e3a8a'"),
  '2.7 浅色 text-primary 颜色正确',
  "primary: '#1e3a8a'"
);

test(
  tailwindConfig.includes("secondary: '#1d4ed8'"),
  '2.8 浅色 text-secondary 颜色正确',
  "secondary: '#1d4ed8'"
);

test(
  tailwindConfig.includes("muted: '#3b82f6'"),
  '2.9 浅色 text-muted 颜色正确',
  "muted: '#3b82f6'"
);

// ============================================
// 测试 3: 深色模式保持不变
// ============================================
log('\n测试 3: 深色模式保持不变', 'info');

test(
  indexCss.includes('--neon-blue: #00f5ff'),
  '3.1 深色模式霓虹蓝保持正确',
  '--neon-blue: #00f5ff'
);

test(
  indexCss.includes('--neon-purple: #bf00ff'),
  '3.2 深色模式霓虹紫保持正确',
  '--neon-purple: #bf00ff'
);

test(
  indexCss.includes('--neon-green: #00ff88'),
  '3.3 深色模式霓虹绿保持正确',
  '--neon-green: #00ff88'
);

test(
  indexCss.includes('--cyber-dark: #0a0a0f'),
  '3.4 深色模式 Cyber 暗色保持正确',
  '--cyber-dark: #0a0a0f'
);

test(
  indexCss.includes('--cyber-card: #0d0d14'),
  '3.5 深色模式 Cyber 卡片色保持正确',
  '--cyber-card: #0d0d14'
);

test(
  tailwindConfig.includes('cyber: {'),
  '3.6 Tailwind cyber 颜色配置保持',
  'cyber: {'
);

// ============================================
// 测试 4: 组件样式文件验证
// ============================================
log('\n测试 4: 核心组件样式验证', 'info');

const layoutCss = readFile(path.join(__dirname, 'src/components/Layout.tsx'));
test(
  layoutCss && layoutCss.includes('bg-light-bg-secondary'),
  '4.1 Layout 使用浅色背景语义颜色',
  'bg-light-bg-secondary'
);

const headerContent = readFile(path.join(__dirname, 'src/components/Header.tsx'));
test(
  headerContent && headerContent.includes('bg-white'),
  '4.2 Header 使用正确的浅色背景（白色）',
  'bg-white'
);

test(
  headerContent && headerContent.includes('border-light-border'),
  '4.3 Header 使用浅色边框语义颜色',
  'border-light-border'
);

const sidebarContent = readFile(path.join(__dirname, 'src/components/Sidebar.tsx'));
test(
  sidebarContent && sidebarContent.includes('bg-light-bg-secondary'),
  '4.4 Sidebar 使用浅色背景语义颜色',
  'bg-light-bg-secondary'
);

test(
  sidebarContent && sidebarContent.includes('text-light-text-primary'),
  '4.5 Sidebar 使用浅色文字语义颜色',
  'text-light-text-primary'
);

test(
  sidebarContent && sidebarContent.includes('text-light-text-muted'),
  '4.6 Sidebar 使用浅色弱化文字语义颜色',
  'text-light-text-muted'
);

// ============================================
// 测试 5: UI 组件验证
// ============================================
log('\n测试 5: UI 组件样式验证', 'info');

const buttonContent = readFile(path.join(__dirname, 'src/components/ui/Button.tsx'));
test(
  buttonContent && buttonContent.includes('text-light-text-secondary'),
  '5.1 Button 使用浅色文字语义颜色',
  'text-light-text-secondary'
);

const inputContent = readFile(path.join(__dirname, 'src/components/ui/Input.tsx'));
test(
  inputContent && inputContent.includes('text-light-text-primary'),
  '5.2 Input 使用浅色文字语义颜色',
  'text-light-text-primary'
);

test(
  inputContent && inputContent.includes('border-light-border'),
  '5.3 Input 使用浅色边框语义颜色',
  'border-light-border'
);

const modalContent = readFile(path.join(__dirname, 'src/components/ui/Modal.tsx'));
test(
  modalContent && modalContent.includes('border-light-border'),
  '5.4 Modal 使用浅色边框语义颜色',
  'border-light-border'
);

test(
  modalContent && modalContent.includes('text-light-text-primary'),
  '5.5 Modal 使用浅色文字语义颜色',
  'text-light-text-primary'
);

const selectContent = readFile(path.join(__dirname, 'src/components/ui/Select.tsx'));
test(
  selectContent && selectContent.includes('text-light-text-primary'),
  '5.6 Select 使用浅色文字语义颜色',
  'text-light-text-primary'
);

const emptyStateContent = readFile(path.join(__dirname, 'src/components/ui/EmptyState.tsx'));
test(
  emptyStateContent && emptyStateContent.includes('text-light-text-primary'),
  '5.7 EmptyState 使用浅色文字语义颜色',
  'text-light-text-primary'
);

test(
  emptyStateContent && emptyStateContent.includes('text-light-text-muted'),
  '5.8 EmptyState 使用浅色弱化文字语义颜色',
  'text-light-text-muted'
);

// ============================================
// 测试 6: 主题切换器验证
// ============================================
log('\n测试 6: 主题切换功能验证', 'info');

const themeToggleContent = readFile(path.join(__dirname, 'src/components/ThemeToggle.tsx'));
test(
  themeToggleContent && themeToggleContent.includes('bg-light-bg-tertiary'),
  '6.1 ThemeToggle 使用浅色背景语义颜色',
  'bg-light-bg-tertiary'
);

const storeContent = readFile(path.join(__dirname, 'src/store/index.ts'));
test(
  storeContent && storeContent.includes('themeMode'),
  '6.2 Store 包含 themeMode 状态',
  'themeMode'
);

test(
  storeContent && storeContent.includes('theme'),
  '6.3 Store 包含 theme 状态',
  'theme'
);

test(
  storeContent && storeContent.includes('setThemeMode'),
  '6.4 Store 包含 setThemeMode 方法',
  'setThemeMode'
);

test(
  storeContent && storeContent.includes('document.documentElement.classList.add'),
  '6.5 Store 应用主题到 document',
  'document.documentElement.classList.add'
);

test(
  storeContent && storeContent.includes('document.documentElement.classList.remove'),
  '6.6 Store 移除主题从 document',
  'document.documentElement.classList.remove'
);

// ============================================
// 测试 7: 页面组件验证
// ============================================
log('\n测试 7: 页面组件样式验证', 'info');

const dashboardContent = readFile(path.join(__dirname, 'src/pages/Dashboard.tsx'));
test(
  dashboardContent && dashboardContent.includes('text-light-text-primary'),
  '7.1 Dashboard 使用浅色文字语义颜色',
  'text-light-text-primary'
);

test(
  dashboardContent && dashboardContent.includes('text-light-text-muted'),
  '7.2 Dashboard 使用浅色弱化文字语义颜色',
  'text-light-text-muted'
);

const settingsContent = readFile(path.join(__dirname, 'src/pages/Settings.tsx'));
test(
  settingsContent && settingsContent.includes('text-light-text-primary'),
  '7.3 Settings 使用浅色文字语义颜色',
  'text-light-text-primary'
);

const onboardingContent = readFile(path.join(__dirname, 'src/pages/Onboarding.tsx'));
test(
  onboardingContent && onboardingContent.includes('text-light-text-primary'),
  '7.4 Onboarding 使用浅色文字语义颜色',
  'text-light-text-primary'
);

const landingPageContent = readFile(path.join(__dirname, 'src/pages/LandingPage.tsx'));
test(
  landingPageContent && landingPageContent.includes('text-light-text-primary'),
  '7.5 LandingPage 使用浅色文字语义颜色',
  'text-light-text-primary'
);

// ============================================
// 测试 8: 深色模式类名验证
// ============================================
log('\n测试 8: 深色模式样式保持验证', 'info');

test(
  buttonContent && buttonContent.includes('dark:text-neon-blue'),
  '8.1 Button 深色模式霓虹蓝文字',
  'dark:text-neon-blue'
);

test(
  headerContent && headerContent.includes('dark:bg-cyber-dark'),
  '8.2 Header 深色模式 Cyber 背景',
  'dark:bg-cyber-dark'
);

test(
  sidebarContent && sidebarContent.includes('dark:bg-cyber-card'),
  '8.3 Sidebar 深色模式 Cyber 卡片',
  'dark:bg-cyber-card'
);

test(
  indexCss && indexCss.includes('.dark .card {'),
  '8.4 深色模式卡片样式存在',
  '.dark .card {'
);

test(
  indexCss && indexCss.includes('.dark .input {'),
  '8.5 深色模式输入框样式存在',
  '.dark .input {'
);

test(
  indexCss && indexCss.includes('.dark .btn-primary {'),
  '8.6 深色模式按钮样式存在',
  '.dark .btn-primary {'
);

// ============================================
// 测试 9: 移动端组件验证
// ============================================
log('\n测试 9: 移动端组件验证', 'info');

const mobileDrawerContent = readFile(path.join(__dirname, 'src/components/MobileDrawer.tsx'));
test(
  mobileDrawerContent && mobileDrawerContent.includes('text-light-text-primary'),
  '9.1 MobileDrawer 使用浅色文字语义颜色',
  'text-light-text-primary'
);

test(
  mobileDrawerContent && mobileDrawerContent.includes('text-light-text-secondary'),
  '9.2 MobileDrawer 使用浅色次要文字语义颜色',
  'text-light-text-secondary'
);

test(
  mobileDrawerContent && mobileDrawerContent.includes('text-light-text-muted'),
  '9.3 MobileDrawer 使用浅色弱化文字语义颜色',
  'text-light-text-muted'
);

test(
  mobileDrawerContent && mobileDrawerContent.includes('bg-light-bg-tertiary'),
  '9.4 MobileDrawer 使用浅色背景语义颜色',
  'bg-light-bg-tertiary'
);

// ============================================
// 测试 10: 其他组件验证
// ============================================
log('\n测试 10: 其他组件验证', 'info');

const languageSwitcherContent = readFile(path.join(__dirname, 'src/components/LanguageSwitcher.tsx'));
test(
  languageSwitcherContent && languageSwitcherContent.includes('text-light-text-secondary'),
  '10.1 LanguageSwitcher 使用浅色文字语义颜色',
  'text-light-text-secondary'
);

const helpSystemContent = readFile(path.join(__dirname, 'src/components/ui/HelpSystem.tsx'));
test(
  helpSystemContent && helpSystemContent.includes('text-light-text-primary'),
  '10.2 HelpSystem 使用浅色文字语义颜色',
  'text-light-text-primary'
);

test(
  helpSystemContent && helpSystemContent.includes('border-light-border'),
  '10.3 HelpSystem 使用浅色边框语义颜色',
  'border-light-border'
);

const errorBoundaryContent = readFile(path.join(__dirname, 'src/components/ErrorBoundary.tsx'));
test(
  errorBoundaryContent && errorBoundaryContent.includes('bg-light-bg-secondary'),
  '10.4 ErrorBoundary 使用浅色背景语义颜色',
  'bg-light-bg-secondary'
);

// ============================================
// 测试结果汇总
// ============================================
console.log('\n========================================');
console.log('              测试结果汇总');
console.log('========================================\n');

const totalTests = testResults.passed.length + testResults.failed.length;
const passRate = ((testResults.passed.length / totalTests) * 100).toFixed(1);

console.log(`总计测试: ${totalTests}`);
console.log(`通过: ${testResults.passed.length} ✓`);
console.log(`失败: ${testResults.failed.length} ✗`);
console.log(`通过率: ${passRate}%\n`);

if (testResults.failed.length > 0) {
  console.log('失败的测试:');
  testResults.failed.forEach((test, index) => {
    console.log(`  ${index + 1}. ${test}`);
  });
  console.log('');
}

console.log('========================================\n');

if (testResults.failed.length === 0) {
  console.log('🎉 所有测试通过！主题系统符合设计文档规范。\n');
  
  // 额外检查：浅色模式中不应出现的深色样式组合
  console.log('========================================');
  console.log('   额外检查：浅色模式样式冲突检测');
  console.log('========================================\n');
  
  const filesToCheck = [
    'src/components/Layout.tsx',
    'src/components/Sidebar.tsx', 
    'src/components/Header.tsx',
    'src/pages/Dashboard.tsx',
    'src/pages/Settings.tsx',
    'src/components/ui/Button.tsx',
    'src/components/ui/Input.tsx',
    'src/components/ui/Modal.tsx',
  ];
  
  let hasIssues = false;
  
  filesToCheck.forEach(file => {
    const content = readFile(path.join(__dirname, file));
    if (!content) return;
    
    // 检查浅色模式下不应该出现的深色背景组合
    const problematicPatterns = [
      // 深色背景 + 白色文字在浅色模式下会看不清
      { pattern: /bg-secondary-900[^\/]*text-white(?!.*dark:)/g, desc: '深色背景+白色文字' },
      { pattern: /bg-secondary-800[^\/]*text-white(?!.*dark:)/g, desc: '深色背景+白色文字' },
      // 只有 dark: 前缀但没有浅色模式样式
    ];
    
    problematicPatterns.forEach(({ pattern, desc }) => {
      const matches = content.match(pattern);
      if (matches && matches.length > 0) {
        matches.forEach(match => {
          console.log(`⚠️  ${file}: 发现潜在问题 - ${desc}`);
          console.log(`   ${match.substring(0, 80)}...`);
          hasIssues = true;
        });
      }
    });
  });
  
  if (!hasIssues) {
    console.log('✓ 未发现浅色模式样式冲突问题\n');
  }
  
  process.exit(hasIssues ? 1 : 0);
} else {
  console.log(`⚠️  有 ${testResults.failed.length} 个测试失败，请检查。\n`);
  process.exit(1);
}
