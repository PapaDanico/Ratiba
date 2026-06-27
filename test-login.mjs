import { chromium } from 'playwright';

(async () => {
  const browser = await chromium.launch({
    headless: false,
  });
  const page = await browser.newPage();

  const email = `tester-${Date.now()}@example.com`;
  const password = 'TestPass123';

  console.log('🌍 Opening landing page...');
  await page.goto('http://localhost:3001/', { waitUntil: 'networkidle' });
  console.log('✓ Landing page loaded');

  // Check landing page background
  const landingBg = await page.evaluate(() => {
    return window.getComputedStyle(document.querySelector('div').parentElement).backgroundColor;
  });
  console.log(`  Landing page background: ${landingBg}`);

  console.log('\n📝 Opening login page...');
  await page.goto('http://localhost:3001/login', { waitUntil: 'networkidle' });
  console.log('✓ Login page loaded');

  // Check login page background
  const loginBg = await page.evaluate(() => {
    return window.getComputedStyle(document.querySelector('main')).backgroundColor;
  });
  console.log(`  Login page background: ${loginBg}`);

  console.log('\n🔐 Testing account creation flow...');

  // Switch to create mode
  await page.click('[data-testid="tab-create"]');
  console.log('  ✓ Switched to create mode');

  // Fill form
  await page.fill('[data-testid="create-name"]', 'Test User');
  await page.fill('[data-testid="create-email"]', email);
  await page.fill('[data-testid="create-password"]', password);
  console.log(`  ✓ Form filled (email: ${email})`);

  // Wait for any error messages
  const errorElement = page.locator('[role="alert"]');
  const errorListener = page.on('console', msg => {
    if (msg.type() === 'error') {
      console.log(`  ⚠️  Console error: ${msg.text()}`);
    }
  });

  console.log('  Submitting form...');
  await page.click('[data-testid="create-submit"]');

  // Wait for navigation or error
  let success = false;
  let errorMsg = null;

  try {
    await page.waitForURL('/app/**', { timeout: 15000 }).catch(() => {});
    success = page.url().includes('/app');
  } catch (e) {
    console.log(`  Navigation timeout: ${e.message}`);
  }

  // Check for error messages
  const errorText = await errorElement.textContent().catch(() => null);
  if (errorText) {
    errorMsg = errorText;
    console.log(`  ❌ Form error: ${errorMsg}`);
  }

  if (success) {
    console.log(`  ✅ Login successful! Navigated to: ${page.url()}`);
  } else {
    console.log(`  Current page: ${page.url()}`);
  }

  console.log('\n✅ Test complete');
  await browser.close();
})().catch(err => {
  console.error('❌ Test failed:', err.message);
  process.exit(1);
});
