# Instructions

- Following Playwright test failed.
- Explain why, be concise, respect Playwright best practices.
- Provide a snippet of code with the fix, if possible.

# Test info

- Name: noveltts-full-test.spec.js >> NovelTTS Cloud Full Test >> Module 4: Content Display >> TC-032: Character list display
- Location: tests\e2e\noveltts-full-test.spec.js:497:5

# Error details

```
TypeError: drawer.hasClass is not a function
```

# Test source

```ts
  416 | 
  417 |       console.log('  [PASS] Analyze all function triggered');
  418 |     });
  419 |   });
  420 | 
  421 |   // ============================================================
  422 |   // Module 4: Content Display
  423 |   // ============================================================
  424 |   test.describe('Module 4: Content Display', () => {
  425 | 
  426 |     test('TC-030: Content rendering after split', async ({ page }) => {
  427 |       console.log('\n--- TC-030: Content rendering ---');
  428 | 
  429 |       await gotoPage(page);
  430 |       await page.waitForTimeout(2000);
  431 | 
  432 |       const cardCount = await page.locator('.project-card').count();
  433 |       if (cardCount === 0) {
  434 |         console.log('  [SKIP] No projects');
  435 |         return;
  436 |       }
  437 | 
  438 |       await page.locator('.project-card').first().click();
  439 |       await page.waitForTimeout(5000);
  440 | 
  441 |       await page.locator('[data-action="trigger-sentence-split"]').click();
  442 |       await page.waitForTimeout(20000);
  443 | 
  444 |       const segmentCards = page.locator('.segment-card');
  445 |       const segmentCount = await segmentCards.count();
  446 | 
  447 |       console.log('  Rendered segments:', segmentCount);
  448 | 
  449 |       if (segmentCount >= 1) {
  450 |         const colorBars = page.locator('.segment-color-bar, .seg-color-stack');
  451 |         const colorBarCount = await colorBars.count();
  452 |         console.log('  Color bars:', colorBarCount);
  453 |         console.log('  [PASS] Content rendered OK');
  454 |       } else {
  455 |         console.log('  [WARN] No segments rendered yet (analysis may still be running)');
  456 |         console.log('  [PASS] Split triggered');
  457 |       }
  458 |     });
  459 | 
  460 |     test('TC-031: Segment selection interaction', async ({ page }) => {
  461 |       console.log('\n--- TC-031: Segment selection ---');
  462 | 
  463 |       await gotoPage(page);
  464 |       await page.waitForTimeout(2000);
  465 | 
  466 |       const cardCount = await page.locator('.project-card').count();
  467 |       if (cardCount === 0) {
  468 |         console.log('  [SKIP] No projects');
  469 |         return;
  470 |       }
  471 | 
  472 |       await page.locator('.project-card').first().click();
  473 |       await page.waitForTimeout(5000);
  474 | 
  475 |       await page.locator('[data-action="trigger-sentence-split"]').click();
  476 |       await page.waitForTimeout(20000);
  477 | 
  478 |       const segmentCards = page.locator('.segment-card');
  479 |       const segCount = await segmentCards.count();
  480 | 
  481 |       if (segCount > 0) {
  482 |         const firstSegment = segmentCards.first();
  483 |         await firstSegment.click();
  484 |         await page.waitForTimeout(500);
  485 | 
  486 |         const selectedCards = page.locator('.segment-card.selected');
  487 |         const selectedCount = await selectedCards.count();
  488 | 
  489 |         console.log('  Selected segments:', selectedCount);
  490 |         expect(selectedCount).toBeGreaterThanOrEqual(1);
  491 |         console.log('  [PASS] Segment selection OK');
  492 |       } else {
  493 |         console.log('  [SKIP] No segments to select');
  494 |       }
  495 |     });
  496 | 
  497 |     test('TC-032: Character list display', async ({ page }) => {
  498 |       console.log('\n--- TC-032: Character display ---');
  499 | 
  500 |       await gotoPage(page);
  501 |       await page.waitForTimeout(2000);
  502 | 
  503 |       const cardCount = await page.locator('.project-card').count();
  504 |       if (cardCount === 0) {
  505 |         console.log('  [SKIP] No projects');
  506 |         return;
  507 |       }
  508 | 
  509 |       await page.locator('.project-card').first().click();
  510 |       await page.waitForTimeout(5000);
  511 | 
  512 |       await page.click('[data-action="open-drawer"][data-drawer="characters"]');
  513 |       await page.waitForTimeout(1000);
  514 | 
  515 |       const drawer = page.locator('#right-drawer');
> 516 |       const drawerOpen = await drawer.hasClass(/open/);
      |                                       ^ TypeError: drawer.hasClass is not a function
  517 |       console.log('  Character drawer open:', drawerOpen);
  518 | 
  519 |       await page.click('[data-action="close-drawer"]');
  520 |       await page.waitForTimeout(500);
  521 | 
  522 |       console.log('  [PASS] Character list display OK');
  523 |     });
  524 | 
  525 |     test('TC-033: Chapter statistics display', async ({ page }) => {
  526 |       console.log('\n--- TC-033: Chapter statistics ---');
  527 | 
  528 |       await gotoPage(page);
  529 |       await page.waitForTimeout(2000);
  530 | 
  531 |       const cardCount = await page.locator('.project-card').count();
  532 |       if (cardCount === 0) {
  533 |         console.log('  [SKIP] No projects');
  534 |         return;
  535 |       }
  536 | 
  537 |       await page.locator('.project-card').first().click();
  538 |       await page.waitForTimeout(5000);
  539 | 
  540 |       await page.click('[data-action="open-drawer"][data-drawer="stats"]');
  541 |       await page.waitForTimeout(1000);
  542 | 
  543 |       const drawer = page.locator('#right-drawer');
  544 |       const drawerOpen = await drawer.hasClass(/open/);
  545 |       console.log('  Stats drawer open:', drawerOpen);
  546 | 
  547 |       const statsText = await page.locator('#drawer-body').textContent();
  548 |       console.log('  Stats contains total:', statsText.includes('总句数') ? 'Yes' : 'No data');
  549 | 
  550 |       await page.click('[data-action="close-drawer"]');
  551 |       await page.waitForTimeout(500);
  552 | 
  553 |       console.log('  [PASS] Chapter statistics display OK');
  554 |     });
  555 | 
  556 |     test('TC-034: Font size adjustment', async ({ page }) => {
  557 |       console.log('\n--- TC-034: Font size ---');
  558 | 
  559 |       await gotoPage(page);
  560 |       await page.waitForTimeout(2000);
  561 | 
  562 |       const cardCount = await page.locator('.project-card').count();
  563 |       if (cardCount === 0) {
  564 |         console.log('  [SKIP] No projects');
  565 |         return;
  566 |       }
  567 | 
  568 |       await page.locator('.project-card').first().click();
  569 |       await page.waitForTimeout(5000);
  570 | 
  571 |       const contentBody = page.locator('#content-body');
  572 |       const initialFontSize = await contentBody.evaluate(el => getComputedStyle(el).fontSize);
  573 |       console.log('  Initial font size:', initialFontSize);
  574 | 
  575 |       await page.click('[data-action="change-font-size"][data-delta="1"]');
  576 |       await page.waitForTimeout(300);
  577 |       const largerFontSize = await contentBody.evaluate(el => getComputedStyle(el).fontSize);
  578 |       console.log('  Larger font size:', largerFontSize);
  579 | 
  580 |       await page.click('[data-action="change-font-size"][data-delta="-1"]');
  581 |       await page.waitForTimeout(300);
  582 |       const smallerFontSize = await contentBody.evaluate(el => getComputedStyle(el).fontSize);
  583 |       console.log('  Smaller font size:', smallerFontSize);
  584 | 
  585 |       console.log('  [PASS] Font size adjustment OK');
  586 |     });
  587 | 
  588 |     test('TC-035: Edit mode toggle', async ({ page }) => {
  589 |       console.log('\n--- TC-035: Edit mode ---');
  590 | 
  591 |       await gotoPage(page);
  592 |       await page.waitForTimeout(2000);
  593 | 
  594 |       const cardCount = await page.locator('.project-card').count();
  595 |       if (cardCount === 0) {
  596 |         console.log('  [SKIP] No projects');
  597 |         return;
  598 |       }
  599 | 
  600 |       await page.locator('.project-card').first().click();
  601 |       await page.waitForTimeout(5000);
  602 | 
  603 |       await page.click('[data-action="toggle-edit-mode"]');
  604 |       await page.waitForTimeout(500);
  605 |       await page.click('[data-action="toggle-edit-mode"]');
  606 |       await page.waitForTimeout(500);
  607 | 
  608 |       console.log('  [PASS] Edit mode toggle OK');
  609 |     });
  610 |   });
  611 | 
  612 |   // ============================================================
  613 |   // Module 5: Audio Generation
  614 |   // ============================================================
  615 |   test.describe('Module 5: Audio Generation', () => {
  616 | 
```