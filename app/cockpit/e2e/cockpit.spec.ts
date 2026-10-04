import { expect, test, type Page } from "@playwright/test";

const SHOTS = "../../.impeccable/review";

async function open(page: Page, query = "?preset=balanced", ready = ".rows .row") {
  const errors: string[] = [];
  page.on("console", (m) => {
    if (m.type() === "error" || m.type() === "warning") errors.push(m.text());
  });
  page.on("pageerror", (e) => errors.push(e.message));
  await page.goto(`/${query}`);
  await expect(page.locator(ready).first()).toBeVisible();
  return errors;
}

const topTen = (page: Page) => page.locator(".row .who-name").allInnerTexts();

test("loads with the real engine badge and no console errors", async ({ page }, info) => {
  const errors = await open(page);
  await expect(page.getByText("Real engine data")).toBeVisible();
  await expect(page.locator(".rows .row")).toHaveCount(10);
  await page.waitForTimeout(600);
  await page.screenshot({ path: `${SHOTS}/cockpit-${info.project.name}-start.png` });
  expect(errors).toEqual([]);
});

test("a weight change reorders the top 10 and updates the URL", async ({ page }) => {
  await open(page);
  const before = await topTen(page);
  await page.locator("#w-water").fill("40");
  await expect(page.locator(".change-cause")).toHaveText("Water weight 40%");
  const after = await topTen(page);
  expect(after).not.toEqual(before);
  await expect(page).toHaveURL(/w=water:40/);
  // new entries and moves stay labeled after motion settles
  await page.waitForTimeout(700);
  await expect(page.locator(".tag").first()).toBeVisible();
});

test("a gate control changes the exclusion count", async ({ page }) => {
  await open(page);
  const funnel = page.locator(".funnel strong");
  const before = await funnel.innerText();
  await page.getByLabel("Queue median wait at most", { exact: true }).fill("2");
  await expect(funnel).not.toHaveText(before);
  await expect(page.locator(".change-cause")).toContainText("Queue median wait at most");
});

test("preset and horizon switches move ranks", async ({ page }) => {
  await open(page);
  await page.getByRole("tab", { name: /Speed to power/ }).click();
  await expect(page.locator(".change-cause")).toHaveText("Preset: Speed to power");
  await page.getByRole("radio", { name: "2050" }).click();
  await expect(page.locator(".change-cause")).toHaveText("Horizon: 2050");
  await expect(page).toHaveURL(/preset=speed_to_power&h=2050/);
});

test("map county and shortlist row open the same finding", async ({ page }, info) => {
  await open(page);
  const first = (await topTen(page))[0]!;
  await page.locator(".row-btn").first().click();
  await expect(page.locator(".finding-head h2")).toContainText(first);
  await page.getByRole("button", { name: "Close finding" }).click();
  // click the same county on the map through its path
  const fips = new URL(page.url()).searchParams.get("c");
  expect(fips).toBeNull();
  await page.locator(".row-btn").first().click();
  const sel = new URL(page.url()).searchParams.get("c")!;
  await page.getByRole("button", { name: "Close finding" }).click();
  const idx = await page.evaluate(async (f) => {
    const d = await (await fetch("data/fixture.json")).json();
    return d.counties.fips.indexOf(f);
  }, sel);
  await page.locator(`path[data-i="${idx}"]`).dispatchEvent("click");
  await expect(page.locator(".finding-head h2")).toContainText(first);
  await expect(page.locator(".finding")).toContainText("Pillar contributions");
  await expect(page.locator(".finding")).toContainText("Evidence");
  await expect(page.locator(".finding")).toContainText("Coverage");
  await expect(page.locator(".finding")).toContainText("Hard gates");
  await expect(page.locator(".finding")).toContainText("Today and 2050");
  await page.waitForTimeout(900);
  await page.screenshot({ path: `${SHOTS}/cockpit-${info.project.name}-finding.png` });
});

test("a link opens the exact scenario and county", async ({ page }) => {
  await open(page, "?preset=sustainability_first&s=rcp45&c=51107");
  await expect(page.getByRole("tab", { name: /Sustainability first/ })).toHaveAttribute("aria-selected", "true");
  await expect(page.getByRole("radio", { name: "2050" })).toHaveAttribute("aria-checked", "true");
  await expect(page.locator(".finding-head h2")).toHaveText("Loudoun, VA");
});

test("unexpected link values are ignored with a notice", async ({ page }) => {
  const errors = await open(page, "?preset=nope&h=3000&w=water:abc&g=bogus:1&c=99999");
  await expect(page.locator(".notice")).toContainText("Ignored from the link");
  await expect(page.locator(".rows .row")).toHaveCount(10);
  expect(errors).toEqual([]);
});

test("gates that exclude every county show a recovery hint", async ({ page }) => {
  await open(page, "?preset=balanced&g=min_population:50000,min_fiber_share_locations:0.8,max_grid_co2_lb_mwh:200", ".empty");
  await expect(page.getByText("No county passes these gates.")).toBeVisible();
  await expect(page.locator(".empty")).toContainText("Relax it in the gate list");
});

test("all-zero weights fall back to equal weights", async ({ page }) => {
  const zero = "energy_carbon:0,water:0,climate_resilience:0,grid_infrastructure:0,land:0,community:0,permitting:0,cost:0";
  await open(page, `?preset=balanced&w=${zero}`);
  await expect(page.getByText(/Every weight is zero/)).toBeVisible();
  await expect(page.locator(".rows .row")).toHaveCount(10);
});

test("Reset demo returns to the same starting state every time", async ({ page }) => {
  await open(page);
  await page.waitForTimeout(400);
  const start = await topTen(page);
  const startShare = await page.locator(".stab-share").allInnerTexts();
  await page.locator("#w-land").fill("45");
  await page.getByRole("tab", { name: /Sustainability first/ }).click();
  await page.locator(".row-btn").nth(2).click();
  for (let k = 0; k < 2; k++) {
    await page.getByRole("button", { name: "Reset demo" }).click();
    await expect(page).toHaveURL(/\?preset=balanced$/);
    expect(await topTen(page)).toEqual(start);
    await expect(page.locator(".tag")).toHaveCount(0);
    await expect(page.locator(".finding-head")).toHaveCount(0);
    await page.waitForTimeout(400);
    expect(await page.locator(".stab-share").allInnerTexts()).toEqual(startShare);
  }
});

test("keyboard reaches and operates the core controls", async ({ page }) => {
  await open(page);
  await page.keyboard.press("Tab"); // first preset tab
  await expect(page.getByRole("tab", { name: "Balanced" })).toBeFocused();
  await page.keyboard.press("ArrowRight");
  await expect(page.getByRole("tab", { name: /Speed to power/ })).toBeFocused();
  await expect(page.getByRole("tab", { name: /Speed to power/ })).toHaveAttribute("aria-selected", "true");
  // weights: focus a slider and press arrows
  await page.locator("#w-water").focus();
  const v0 = Number(await page.locator("#w-water").inputValue());
  await page.keyboard.press("ArrowRight");
  await page.keyboard.press("ArrowRight");
  expect(Number(await page.locator("#w-water").inputValue())).toBe(v0 + 2);
  // shortlist rows are buttons
  await page.locator(".row-btn").first().focus();
  await page.keyboard.press("Enter");
  await expect(page.locator(".finding-head h2")).toBeVisible();
  // focus is visible
  const outline = await page.locator(".row-btn").first().evaluate((el) => getComputedStyle(el).outlineStyle);
  expect(outline).not.toBe("none");
  // county search by FIPS
  await page.locator("#county-search").fill("51107");
  await page.keyboard.press("Enter");
  await expect(page.locator(".finding-head h2")).toHaveText("Loudoun, VA");
});

test("reduced motion makes changes instant", async ({ browser }, info) => {
  const ctx = await browser.newContext({ reducedMotion: "reduce", viewport: info.project.use.viewport });
  const page = await ctx.newPage();
  await open(page);
  expect(await page.evaluate(() => getComputedStyle(document.documentElement).getPropertyValue("--t-move").trim())).toMatch(/^0m?s$/);
  await page.locator("#w-water").fill("40");
  await expect(page.locator(".change-cause")).toHaveText("Water weight 40%");
  const running = await page.evaluate(() => document.getAnimations().filter((a) => a.playState === "running").length);
  expect(running).toBe(0);
  await expect(page.locator(".tag").first()).toBeVisible();
  await ctx.close();
});

test("nothing overflows or clips at this viewport", async ({ page }) => {
  await open(page, "?preset=balanced&c=51107");
  const { sw, iw } = await page.evaluate(() => ({ sw: document.documentElement.scrollWidth, iw: window.innerWidth }));
  expect(sw).toBeLessThanOrEqual(iw);
  for (const name of ["Reset demo", "Close finding"]) {
    const box = await page.getByRole("button", { name }).boundingBox();
    expect(box).not.toBeNull();
    expect(box!.x + box!.width).toBeLessThanOrEqual(iw);
  }
  // smallest rendered text is at least 12px
  const minFont = await page.evaluate(() => {
    let m = 99;
    for (const el of document.querySelectorAll<HTMLElement>("body *")) {
      if (!el.childNodes.length || ![...el.childNodes].some((n) => n.nodeType === 3 && n.textContent!.trim())) continue;
      if (el.closest("svg")) continue;
      const r = el.getBoundingClientRect();
      if (!r.width) continue;
      m = Math.min(m, parseFloat(getComputedStyle(el).fontSize));
    }
    return m;
  });
  expect(minFont).toBeGreaterThanOrEqual(12);
});
