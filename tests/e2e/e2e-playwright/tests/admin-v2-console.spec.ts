import { test, expect, type Page } from '@playwright/test'

const adminToken = process.env.ADMIN_TOKEN || 'test-admin-token'

const commercialAndAdminRoutes = [
  '/clients',
  '/models',
  '/backends',
  '/plugins',
  '/saas',
]

async function resolveAdminBasePath(page: Page) {
  for (const candidate of ['/static/admin-v2/index.html', '/admin-v2']) {
    await page.goto(candidate)
    const main = page.locator('main')
    try {
      await expect(main).toBeVisible({ timeout: 5000 })
      return page.url().includes('/static/admin-v2') ? '/static/admin-v2' : '/admin-v2'
    } catch {
      continue
    }
  }

  throw new Error('admin-v2 shell did not mount on /static/admin-v2/index.html or /admin-v2')
}

async function bootstrapAdminV2(page: Page) {
  await page.addInitScript(token => {
    window.localStorage.setItem('adminToken', token)
  }, adminToken)

  await page.request.post('/admin/onboarding/status', {
    headers: { 'X-Admin-Token': adminToken, 'Content-Type': 'application/json' },
    data: { is_finished: true },
  })

  return resolveAdminBasePath(page)
}

async function navigateInApp(page: Page, basePath: string, path: string) {
  const target = path === '/' ? basePath : `${basePath}${path}`
  await page.evaluate(url => {
    window.history.pushState({}, '', url)
    window.dispatchEvent(new PopStateEvent('popstate'))
  }, target)

  const heading = page.locator('main h1').first()
  await expect(heading).toBeVisible({ timeout: 15000 })
  await expect(page.locator('text=Página não encontrada')).toHaveCount(0)
  await expect(page.locator('text=Ops! Algo deu errado.')).toHaveCount(0)
}

async function collectPublishedConsoleRoutes(page: Page, basePath: string) {
  const hrefs = await page.locator('aside nav a[href]').evaluateAll((links) =>
    links
      .map((link) => link.getAttribute('href') || '')
      .filter((href) => href.startsWith('/'))
  )

  const routes = new Set<string>(['/'])
  for (const href of hrefs) {
    if (!href.startsWith(basePath)) {
      continue
    }
    const route = href.slice(basePath.length) || '/'
    routes.add(route.startsWith('/') ? route : `/${route}`)
  }
  return [...routes]
}

test.describe.serial('Admin V2 Full-Stack Console', () => {
  test('loads authenticated shell and operational chrome', async ({ page }) => {
    await bootstrapAdminV2(page)

    await expect(page.locator('aside nav')).toBeVisible()
    await expect(page.locator('text=Online')).toBeVisible()
    await expect(page.locator('main h1').first()).toBeVisible()
  })

  test('navigates every published console route without placeholders', async ({ page }) => {
    const basePath = await bootstrapAdminV2(page)
    const routeMatrix = await collectPublishedConsoleRoutes(page, basePath)

    for (const path of routeMatrix) {
      await navigateInApp(page, basePath, path)
    }
  })

  test('keeps commercial and admin control pages mounted in the published console', async ({ page }) => {
    const basePath = await bootstrapAdminV2(page)

    for (const path of commercialAndAdminRoutes) {
      await navigateInApp(page, basePath, path)
      await expect(page.locator('main')).toBeVisible()
    }
  })
})
