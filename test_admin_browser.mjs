import { chromium } from 'playwright';

const WALLET_ADDRESS = '0x382B71e8b425CFAaD1B1C6D970481F440458Abf8';

async function test() {
  console.log('Starting admin panel test...');

  const browser = await chromium.launch({ headless: false });
  const context = await browser.newContext();
  const page = await context.newPage();

  try {
    // 1. Clear localStorage
    console.log('1. Clearing localStorage...');
    await page.goto('http://localhost:3000');
    await page.evaluate(() => localStorage.clear());
    await page.waitForTimeout(1000);

    // 2. Check current auth state
    console.log('2. Checking localStorage...');
    const authData = await page.evaluate(() => {
      const data = localStorage.getItem('usmsb-auth');
      return data ? JSON.parse(data) : null;
    });
    console.log('   Auth state:', authData ? 'exists' : 'none');
    if (authData?.state?.userRole) {
      console.log('   userRole:', authData.state.userRole);
    }

    // 3. Navigate to admin
    console.log('3. Navigating to /admin...');
    await page.goto('http://localhost:3000/admin');
    await page.waitForTimeout(2000);
    console.log('   Current URL:', page.url());

    // 4. Check page content
    const bodyText = await page.locator('body').textContent();
    console.log('4. Page content preview:', bodyText?.slice(0, 200));

    // 5. Check if redirected
    if (page.url().includes('/admin')) {
      console.log('✓ Stayed on admin page');
    } else if (page.url().includes('/login')) {
      console.log('→ Redirected to login page');
      console.log('→ Need to login first');
    } else {
      console.log('→ Redirected to:', page.url());
    }

    // 6. Set mock auth data to test admin route
    console.log('5. Setting mock auth data...');
    await page.evaluate((wallet) => {
      localStorage.setItem('usmsb-auth', JSON.stringify({
        state: {
          address: wallet,
          chainId: 84532,
          isConnected: true,
          bindingType: 'wallet',
          userRole: 'superadmin',
          did: `did:vibe:${wallet}`,
          sessionId: 'test-session',
          accessToken: 'test-token',
          isConnected: true
        }
      }));
    }, WALLET_ADDRESS);
    console.log('   Set userRole=superadmin');

    // 7. Reload page to force Zustand to re-read localStorage
    console.log('6. Reloading page to rehydrate Zustand...');
    await page.reload({ waitUntil: 'networkidle' });
    await page.waitForTimeout(2000);

    // 8. Check auth state after reload
    console.log('7. Checking auth state after reload...');
    const authAfterReload = await page.evaluate(() => {
      const data = localStorage.getItem('usmsb-auth');
      return data ? JSON.parse(data) : null;
    });
    console.log('   userRole after reload:', authAfterReload?.state?.userRole);

    // 9. Navigate to admin
    console.log('8. Navigating to /admin...');
    await page.goto('http://localhost:3000/admin');
    await page.waitForTimeout(2000);
    console.log('   Current URL:', page.url());

    // 8. Check page content
    if (page.url().includes('/admin')) {
      console.log('✓ SUCCESS: Admin page accessible!');
      const h1 = await page.locator('h1').first().textContent().catch(() => 'no h1');
      console.log('   Page title:', h1);
    } else {
      console.log('✗ FAILED: Still redirected to:', page.url());

      // Debug: check the actual store values
      console.log('   Debug: checking store values...');
      const storeDebug = await page.evaluate(() => {
        // Try to read from React context or Zustand store
        const auth = localStorage.getItem('usmsb-auth');
        return {
          localStorageAuth: auth ? JSON.parse(auth) : null,
          currentUrl: window.location.href,
        };
      });
      console.log('   Store debug:', JSON.stringify(storeDebug, null, 2));
    }

  } catch (error) {
    console.error('Error:', error.message);
  } finally {
    await browser.close();
  }
}

test();