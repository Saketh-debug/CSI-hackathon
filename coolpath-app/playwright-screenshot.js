import { chromium } from 'playwright';

(async () => {
  const browser = await chromium.launch({ headless: true }); 
  const page = await browser.newPage();
  
  await page.setViewportSize({ width: 1440, height: 900 });

  const routes = [
    { path: '/', name: 'home' },
    { path: '/dashboard', name: 'dashboard' },
    { path: '/heatmap', name: 'heatmap' },
    { path: '/canopy', name: 'canopy' },
    { path: '/router', name: 'router' },
    { path: '/messaging', name: 'messaging' },
  ];

  for (const route of routes) {
    console.log(`Testing route: ${route.path}`);
    await page.goto(`http://localhost:5173${route.path}`, { waitUntil: 'networkidle' });
    await page.waitForTimeout(1000); 
    await page.screenshot({ path: `c:/Users/Saketh/Desktop/Reiteration-CSI/react-${route.name}.png`, fullPage: false });
    console.log(`Saved screenshot to react-${route.name}.png`);
  }

  console.log('All routes tested and captured.');
  await browser.close();
  process.exit(0);
})();
