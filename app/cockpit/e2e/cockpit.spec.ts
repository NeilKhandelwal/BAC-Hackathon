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

test("loads real engine data without a data badge, and no console errors", async ({ page }, info) => {
  const errors = await open(page);
  // the badge warns only about synthetic data; the engine export is the normal case
  await expect(page.locator(".badge-data")).toHaveCount(0);
  await expect(page.getByText("Real engine data")).toHaveCount(0);
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

test.describe("rank stability outcome bars", () => {
  test("replace the barcode and pillar strip, with a persistent legend", async ({ page }) => {
    await open(page);
    await expect(page.locator(".outcome-wrap .outcome")).toHaveCount(10);
    await expect(page.locator(".barcode, svg.barcode, .barcode-empty")).toHaveCount(0);
    await expect(page.locator(".stack, .stack-seg")).toHaveCount(0);
    await expect(page.getByText(/Barcodes show/)).toHaveCount(0);
    const legend = page.locator(".stab-legend");
    await expect(legend).toBeVisible();
    await expect(legend).toContainText("Top 3");
    await expect(legend).toContainText("Ranks 4–10");
    await expect(legend).toContainText("Outside top 10");
    await expect(legend).toContainText("2,000 weight scenarios");
    await expect(page.locator(".row .stab-share").first()).toHaveText(/^Top 10 in (\d+%|>99%|<1%)$/);
  });

  test("segments cover the whole bar and match the tooltip counts", async ({ page }) => {
    await open(page);
    await page.waitForTimeout(400);
    const bars = page.locator(".row .outcome-wrap .outcome");
    for (let k = 0; k < 10; k++) {
      const bar = bars.nth(k);
      const seg = await bar.evaluate((el) => {
        const segs = [...el.querySelectorAll<HTMLElement>(".outcome-seg")];
        const total = el.getBoundingClientRect().width;
        const sum = segs.reduce((a, s) => a + s.getBoundingClientRect().width, 0);
        return { total, sum, grow: segs.reduce((a, s) => a + Number(s.style.flexGrow), 0) };
      });
      expect(Math.abs(seg.sum - seg.total)).toBeLessThan(1); // segments fill 100% of the bar
      expect(seg.grow).toBe(2000); // flex weights are the draw counts
      const tipId = await bar.getAttribute("aria-describedby");
      const rows = page.locator(`[id="${tipId}"] tbody tr`);
      await expect(rows).toHaveCount(3);
      const cells = await rows.evaluateAll((trs) =>
        trs.map((tr) => [tr.querySelector("th")!.textContent!.trim(), ...[...tr.querySelectorAll("td")].map((td) => td.textContent!.trim())]),
      );
      expect(cells.map((c) => c[0])).toEqual(["Top 3", "Ranks 4–10", "Outside top 10"]);
      const counts = cells.map((c) => Number(c[1]!.replace(/,/g, "")));
      const pcts = cells.map((c) => parseFloat(c[2]!));
      expect(counts.reduce((a, b) => a + b, 0)).toBe(2000);
      expect(Math.round(pcts.reduce((a, b) => a + b, 0) * 10)).toBe(1000);
      expect(counts[0]!).toBeLessThanOrEqual(counts[0]! + counts[1]!); // top 3 within top 10
      expect(seg.grow).toBe(counts.reduce((a, b) => a + b, 0));
    }
  });

  test("tooltip opens on hover, keyboard focus, and tap", async ({ page }, info) => {
    await open(page);
    const bar = page.locator(".row .outcome-wrap .outcome").first();
    await expect(bar).toBeVisible();
    const tip = page.locator(`[id="${await bar.getAttribute("aria-describedby")}"]`);
    await expect(tip).toHaveAttribute("role", "tooltip");
    await expect(tip).toBeHidden();
    // hover
    await bar.hover();
    await expect(tip).toBeVisible();
    await expect(tip).toContainText("Rank across 2,000 weight scenarios");
    await page.mouse.move(5, 5);
    await expect(tip).toBeHidden();
    // keyboard: Tab from the row button reaches the bar
    await page.locator(".row-btn").first().focus();
    await page.keyboard.press("Tab");
    await expect(bar).toBeFocused();
    await expect(tip).toBeVisible();
    await expect(bar).toHaveAttribute("aria-label", /Rank stability for .+: top 10 in/);
    await page.keyboard.press("Escape");
    await expect(tip).toBeHidden();
    await page.locator("#county-search").focus();
    // tap: the tooltip stays open and the county is selected, as a row click always did
    await bar.click();
    await page.mouse.move(5, 5);
    await expect(tip).toBeVisible();
    await expect(page.locator(".finding-head h2")).toBeVisible();
    await page.waitForTimeout(500);
    await page.screenshot({ path: `${SHOTS}/stability/tooltip-${info.project.name}.png` });
    await page.locator(".topbar .brand").click();
    await expect(tip).toBeHidden();
  });

  test("clicking the label still selects the county", async ({ page }) => {
    await open(page);
    const name = (await topTen(page))[1]!;
    // the label lets clicks through to the row button underneath
    await page.locator(".row .stab-share").nth(1).click({ force: true });
    await expect(page.locator(".finding-head h2")).toContainText(name);
  });

  test("unavailable stability renders cleanly", async ({ page }) => {
    // On the committed engine export these gates leave 8 counties, fewer than
    // the top 10, so rank stability cannot be computed.
    await open(page, "?preset=balanced&g=min_population:50000,min_fiber_share_locations:0.6,max_grid_co2_lb_mwh:400");
    const rows = await page.locator(".rows .row").count();
    expect(rows).toBeGreaterThan(0);
    expect(rows).toBeLessThanOrEqual(10);
    await expect(page.locator(".stab-legend")).toContainText("not computed");
    await expect(page.locator(".row .outcome-empty")).toHaveCount(rows);
    await expect(page.locator(".row .outcome-wrap")).toHaveCount(0); // no tooltip trigger without data
    await expect(page.locator(".row .stab-share").first()).toHaveText("Not computed");
  });
});

test.describe("map zoom and pan", () => {
  const scale = (page: Page) =>
    page.locator(".map .zoom").evaluate((g) => new DOMMatrixReadOnly(getComputedStyle(g).transform).a);

  test("wheel and pinch zoom around the pointer, drag pans, buttons step", async ({ page }) => {
    await open(page);
    const map = page.locator(".map");
    const box = (await map.boundingBox())!;
    const cx = box.x + box.width / 2;
    const cy = box.y + box.height / 2;
    expect(await scale(page)).toBeCloseTo(1, 3);
    await expect(page.getByRole("button", { name: "Zoom out" })).toBeDisabled();

    // scroll wheel zooms in and the page does not scroll
    await page.mouse.move(cx, cy);
    await page.mouse.wheel(0, -400);
    await expect.poll(() => scale(page)).toBeGreaterThan(1.5);
    expect(await page.evaluate(() => window.scrollY)).toBe(0);
    await expect(page.getByRole("button", { name: "Show all counties" })).toBeVisible();

    // trackpad pinch arrives as ctrl+wheel
    const before = await scale(page);
    await page.keyboard.down("Control");
    await page.mouse.wheel(0, -60);
    await page.keyboard.up("Control");
    await expect.poll(() => scale(page)).toBeGreaterThan(before);

    // drag pans, and the release does not select a county
    const t0 = await page.locator(".map .zoom").evaluate((g) => new DOMMatrixReadOnly(getComputedStyle(g).transform).e);
    await page.mouse.move(cx, cy);
    await page.mouse.down();
    await page.mouse.move(cx + 120, cy + 40, { steps: 6 });
    await page.mouse.up();
    const t1 = await page.locator(".map .zoom").evaluate((g) => new DOMMatrixReadOnly(getComputedStyle(g).transform).e);
    expect(t1).not.toBeCloseTo(t0, 0);
    await expect(page.locator(".finding-head")).toHaveCount(0);

    // a plain click still selects
    await page.mouse.click(cx, cy);
    await expect.poll(() => new URL(page.url()).searchParams.get("c")).not.toBeNull();

    // buttons step the zoom and stop at the limits
    await page.getByRole("button", { name: "Show all counties" }).click();
    await expect.poll(() => scale(page)).toBeCloseTo(1, 2);
    await page.getByRole("button", { name: "Zoom in" }).click();
    await expect.poll(() => scale(page)).toBeCloseTo(1.6, 1);
    await page.getByRole("button", { name: "Zoom out" }).click();
    await expect.poll(() => scale(page)).toBeCloseTo(1, 2);
    await expect(page.getByRole("button", { name: "Zoom out" })).toBeDisabled();
  });

  test("Reset demo returns the map to the full view", async ({ page }) => {
    await open(page);
    await page.getByRole("button", { name: "Zoom in" }).click();
    await page.getByRole("button", { name: "Zoom in" }).click();
    await expect.poll(() => scale(page)).toBeGreaterThan(2);
    await page.getByRole("button", { name: "Reset demo" }).click();
    await expect.poll(() => scale(page)).toBeCloseTo(1, 2);
  });
});

test.describe("compare picker", () => {
  test("quick picks offer the current #1 and Loudoun, and search finds any county", async ({ page }) => {
    await open(page);
    const names = await topTen(page);
    // view the #3 county
    await page.locator(".row-btn").nth(2).click();
    const trigger = page.getByRole("button", { name: "Compare with…" });
    await expect(trigger).toHaveAttribute("aria-expanded", "false");
    await trigger.click();
    const dialog = page.getByRole("dialog", { name: /Compare .+ with another county/ });
    await expect(dialog).toBeVisible();
    const first = dialog.getByRole("button", { name: new RegExp(`#1 · ${names[0]}`) });
    await expect(first).toBeVisible();
    await expect(first).toBeFocused(); // focus moves into the picker
    await expect(dialog.getByRole("button", { name: /Loudoun, VA.*Industry benchmark/ })).toBeVisible();

    // quick pick: the current leader
    await first.click();
    await expect(dialog).toBeHidden();
    await expect(page).toHaveURL(/cmp=/);
    await expect(page.getByRole("button", { name: new RegExp(`vs ${names[0]}`) })).toBeFocused();
    await expect(page.locator(".cmp-legend")).toContainText(names[0]!);

    // search by FIPS
    await page.getByRole("button", { name: new RegExp(`vs ${names[0]}`) }).click();
    await dialog.getByLabel("Any county").fill("17007");
    await dialog.getByRole("button", { name: "Compare", exact: true }).click();
    await expect(page.getByRole("button", { name: /vs Boone, IL/ })).toBeVisible();
    await expect(page).toHaveURL(/cmp=17007/);

    // the Loudoun quick pick
    await page.getByRole("button", { name: /vs Boone, IL/ }).click();
    await dialog.getByRole("button", { name: /Loudoun, VA/ }).click();
    await expect(page).toHaveURL(/cmp=51107/);

    // stop comparing
    await page.getByRole("button", { name: /vs Loudoun, VA/ }).click();
    await dialog.getByRole("button", { name: "Stop comparing" }).click();
    await expect(page).not.toHaveURL(/cmp=/);
    await expect(page.getByRole("button", { name: "Compare with…" })).toBeVisible();
  });

  test("the leader is offered the runner-up, and bad input explains itself", async ({ page }) => {
    await open(page);
    const names = await topTen(page);
    await page.locator(".row-btn").first().click();
    await page.getByRole("button", { name: "Compare with…" }).click();
    const dialog = page.getByRole("dialog");
    await expect(dialog.getByRole("button", { name: new RegExp(`#2 · ${names[1]}`) })).toBeVisible();
    await expect(dialog.getByRole("button", { name: /#1 ·/ })).toHaveCount(0);
    await dialog.getByLabel("Any county").fill("zzzz");
    await dialog.getByRole("button", { name: "Compare", exact: true }).click();
    await expect(dialog.getByRole("alert")).toHaveText(/No county matches/);
    // Escape closes and returns focus to the trigger
    await page.keyboard.press("Escape");
    await expect(dialog).toBeHidden();
    await expect(page.getByRole("button", { name: "Compare with…" })).toBeFocused();
  });

  test("a press outside closes the picker", async ({ page }, info) => {
    await open(page);
    await page.locator(".row-btn").nth(1).click();
    await page.getByRole("button", { name: "Compare with…" }).click();
    await expect(page.getByRole("dialog")).toBeVisible();
    await page.waitForTimeout(300);
    await page.screenshot({ path: `${SHOTS}/compare/picker-${info.project.name}.png` });
    await page.locator(".topbar .brand").click();
    await expect(page.getByRole("dialog")).toBeHidden();
  });
});

test("pillar table headers and floor flags are not clipped", async ({ page }) => {
  // Pottawatomie, KS against Grant, WA: Community sits below the floor
  await open(page, "?preset=balanced&c=20149&cmp=53025");
  await expect(page.locator(".contrib")).toBeVisible();
  const heads = await page.$$eval(".contrib thead th", (ths) =>
    ths.map((t) => ({ text: t.textContent, fits: t.scrollWidth <= t.clientWidth })),
  );
  for (const h of heads) expect(h, `${h.text} overflows its column`).toEqual({ text: h.text, fits: true });
  const flags = page.locator(".contrib .pillar-flag");
  if (await flags.count()) {
    const clipped = await flags.evaluateAll((els) => els.filter((e) => e.scrollWidth > e.clientWidth).length);
    expect(clipped).toBe(0);
    await expect(flags.first()).toHaveText("Below floor");
  }
});
