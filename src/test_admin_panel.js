const { chromium } = require('playwright');

(async () => {
  const browser = await chromium.launch({
    headless: true,
    executablePath: '/Users/gujun/Library/Caches/ms-playwright/chromium_headless_shell-1217/chrome-headless-shell-mac-x64/chrome-headless-shell'
  });
  const context = await browser.newContext();
  const page = await context.newPage();

  console.log('=== Browser Automation Test ===\n');

  // Step 1 & 2: Navigate to localhost:3000
  console.log('1. Navigating to http://localhost:3000...');
  await page.goto('http://localhost:3000', { waitUntil: 'networkidle' });

  // Step 3: Wait 2 seconds for app to load
  console.log('2. Waiting 2 seconds for app to fully load...');
  await page.waitForTimeout(2000);

  // Step 4: Set admin auth in localStorage
  console.log('3. Setting admin auth data in localStorage...');
  const authData = {
    state: {
      address: '0x382B71e8b425CFAaD1B1C6D970481F440458Abf8',
      chainId: 84532,
      isConnected: true,
      bindingType: 'wallet',
      userRole: 'superadmin',
      did: 'did:vibe:0x382b71e8b425cfaad1b1c6d970481f440458abf8',
      sessionId: 'test-session-id',
      accessToken: 'test-access-token',
      agentId: 'human_user-1774262249.904061',
      stake: 0,
      reputation: 0.5,
      vibeBalance: 10000,
      stakedAmount: 0,
      lockedAmount: 0,
      stakeStatus: 'none',
      stakeRequired: false,
      permissions: [],
      votingPower: 0,
      agentWallets: [],
      currentAgentWallet: null
    }
  };

  await page.evaluate((data) => {
    localStorage.setItem('usmsb-auth', JSON.stringify(data));
  }, authData);

  console.log('   Auth data set successfully.');

  // Step 5: Navigate to /admin
  console.log('4. Navigating to http://localhost:3000/admin...');
  await page.goto('http://localhost:3000/admin', { waitUntil: 'networkidle' });

  // Step 6: Wait 3 seconds
  console.log('5. Waiting 3 seconds for admin page to load...');
  await page.waitForTimeout(3000);

  // Step 7: Report findings
  console.log('\n=== Test Results ===\n');

  // Current URL
  const currentUrl = page.url();
  console.log(`Current URL: ${currentUrl}`);

  // Page title
  const title = await page.title();
  console.log(`Page title: ${title}`);

  // Visible text on page
  const bodyText = await page.evaluate(() => document.body.innerText);
  console.log(`\nVisible text on page (first 2000 chars):\n${bodyText.substring(0, 2000)}`);

  // Check for admin dashboard elements
  console.log('\n=== Admin Dashboard Elements Check ===');

  // Look for common admin dashboard elements
  const selectors = [
    { name: 'Admin text', selector: 'text=/admin/i' },
    { name: 'Dashboard', selector: 'text=/dashboard/i' },
    { name: 'Sidebar', selector: '[class*="sidebar" i], [class*="side-bar" i]' },
    { name: 'Navigation', selector: 'nav' },
    { name: 'Heading', selector: 'h1, h2, h3' },
    { name: 'Table', selector: 'table' },
    { name: 'Button', selector: 'button' },
  ];

  for (const item of selectors) {
    try {
      const element = await page.$(item.selector);
      if (element) {
        const text = await element.innerText().catch(() => '');
        console.log(`Found ${item.name}: "${text.substring(0, 100)}"`);
      } else {
        console.log(`Not found: ${item.name}`);
      }
    } catch (e) {
      console.log(`Error checking ${item.name}: ${e.message}`);
    }
  }

  // Check localStorage to confirm auth
  const storedAuth = await page.evaluate(() => {
    const auth = localStorage.getItem('usmsb-auth');
    return auth ? JSON.parse(auth) : null;
  });

  console.log('\n=== Auth State Verification ===');
  if (storedAuth && storedAuth.state) {
    console.log(`User role: ${storedAuth.state.userRole}`);
    console.log(`Address: ${storedAuth.state.address}`);
    console.log(`Is connected: ${storedAuth.state.isConnected}`);
  } else {
    console.log('Auth data not found in localStorage');
  }

  // Check for any console errors
  console.log('\n=== Console Errors ===');
  const logs = [];
  page.on('console', msg => {
    if (msg.type() === 'error') {
      logs.push(msg.text());
    }
  });

  await browser.close();
  console.log('\nTest complete.');
})();
