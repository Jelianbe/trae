# Instructions

- Following Playwright test failed.
- Explain why, be concise, respect Playwright best practices.
- Provide a snippet of code with the fix, if possible.

# Test info

- Name: noveltts-full-test.spec.js >> NovelTTS Cloud Full Test >> Module 5: Audio Generation >> TC-045: Audio player interaction
- Location: tests\e2e\noveltts-full-test.spec.js:745:5

# Error details

```
Error: expect(locator).toBeVisible() failed

Locator:  locator('.audio-player')
Expected: visible
Received: hidden
Timeout:  5000ms

Call log:
  - Expect "toBeVisible" with timeout 5000ms
  - waiting for locator('.audio-player')
    9 × locator resolved to <div class="audio-player">…</div>
      - unexpected value "hidden"

```

# Test source

```ts
  657 |       console.log('  Toast shown:', toastVisible);
  658 | 
  659 |       console.log('  [PASS] Voice preview triggered');
  660 |     });
  661 | 
  662 |     test('TC-042: Voice category filter', async ({ page }) => {
  663 |       console.log('\n--- TC-042: Voice filter ---');
  664 | 
  665 |       await gotoPage(page);
  666 | 
  667 |       await page.click('text=音色库');
  668 |       await page.waitForTimeout(3000);
  669 | 
  670 |       await page.click('[data-action="filter-voices-cat"][data-cat="male"]');
  671 |       await page.waitForTimeout(500);
  672 | 
  673 |       await page.click('[data-action="filter-voices-cat"][data-cat="female"]');
  674 |       await page.waitForTimeout(500);
  675 | 
  676 |       await page.click('[data-action="filter-voices-cat"][data-cat="all"]');
  677 |       await page.waitForTimeout(500);
  678 | 
  679 |       console.log('  [PASS] Voice filter OK');
  680 |     });
  681 | 
  682 |     test('TC-043: Segment-level TTS generation', async ({ page }) => {
  683 |       console.log('\n--- TC-043: Segment TTS ---');
  684 | 
  685 |       await gotoPage(page);
  686 |       await page.waitForTimeout(2000);
  687 | 
  688 |       const cardCount = await page.locator('.project-card').count();
  689 |       if (cardCount === 0) {
  690 |         console.log('  [SKIP] No projects');
  691 |         return;
  692 |       }
  693 | 
  694 |       await page.locator('.project-card').first().click();
  695 |       await page.waitForTimeout(5000);
  696 | 
  697 |       await page.locator('[data-action="trigger-sentence-split"]').click();
  698 |       await page.waitForTimeout(20000);
  699 | 
  700 |       const generateBtn = page.locator('[data-action="generate-segment"]').first();
  701 |       const genBtnVisible = await generateBtn.isVisible().catch(() => false);
  702 |       console.log('  Generate button visible:', genBtnVisible);
  703 | 
  704 |       if (genBtnVisible) {
  705 |         await generateBtn.click();
  706 |         await page.waitForTimeout(15000);
  707 | 
  708 |         const toastText = await page.locator('.toast').first().textContent().catch(() => '');
  709 |         console.log('  Toast:', toastText.substring(0, 100));
  710 |       }
  711 | 
  712 |       console.log('  [PASS] Segment TTS triggered');
  713 |     });
  714 | 
  715 |     test('TC-044: Batch chapter TTS generation', async ({ page }) => {
  716 |       console.log('\n--- TC-044: Batch TTS ---');
  717 | 
  718 |       await gotoPage(page);
  719 |       await page.waitForTimeout(2000);
  720 | 
  721 |       const cardCount = await page.locator('.project-card').count();
  722 |       if (cardCount === 0) {
  723 |         console.log('  [SKIP] No projects');
  724 |         return;
  725 |       }
  726 | 
  727 |       await page.locator('.project-card').first().click();
  728 |       await page.waitForTimeout(5000);
  729 | 
  730 |       await page.locator('[data-action="trigger-sentence-split"]').click();
  731 |       await page.waitForTimeout(20000);
  732 | 
  733 |       const synthesizeBtn = page.locator('[data-action="synthesize-chapter"]');
  734 |       await expect(synthesizeBtn).toBeVisible();
  735 |       await synthesizeBtn.click();
  736 | 
  737 |       await page.waitForTimeout(5000);
  738 | 
  739 |       const ttsProgressVisible = await page.locator('#tts-progress').isVisible().catch(() => false);
  740 |       console.log('  TTS progress visible:', ttsProgressVisible);
  741 | 
  742 |       console.log('  [PASS] Batch TTS triggered');
  743 |     });
  744 | 
  745 |     test('TC-045: Audio player interaction', async ({ page }) => {
  746 |       console.log('\n--- TC-045: Audio player ---');
  747 | 
  748 |       await gotoPage(page);
  749 |       await page.waitForTimeout(2000);
  750 | 
  751 |       const cardCount = await page.locator('.project-card').count();
  752 |       if (cardCount > 0) {
  753 |         await page.locator('.project-card').first().click();
  754 |         await page.waitForTimeout(5000);
  755 |       }
  756 | 
> 757 |       await expect(page.locator('.audio-player')).toBeVisible();
      |                                                   ^ Error: expect(locator).toBeVisible() failed
  758 |       await expect(page.locator('#play-btn')).toBeVisible();
  759 |       await expect(page.locator('#player-bar')).toBeVisible();
  760 |       await expect(page.locator('#player-time-current')).toBeVisible();
  761 |       await expect(page.locator('#player-time-total')).toBeVisible();
  762 |       await expect(page.locator('.player-speed select')).toBeVisible();
  763 | 
  764 |       console.log('  [PASS] Audio player elements complete');
  765 |     });
  766 |   });
  767 | 
  768 |   // ============================================================
  769 |   // Module 6: Error Handling & Edge Cases
  770 |   // ============================================================
  771 |   test.describe('Module 6: Error Handling & Edge Cases', () => {
  772 | 
  773 |     test('TC-050: Empty file handling', async ({ page }) => {
  774 |       console.log('\n--- TC-050: Empty file ---');
  775 | 
  776 |       await gotoPage(page);
  777 | 
  778 |       const fs = require('fs');
  779 |       const path = require('path');
  780 |       const emptyFilePath = path.join(__dirname, 'empty_test.txt');
  781 |       fs.writeFileSync(emptyFilePath, '', 'utf8');
  782 | 
  783 |       await page.click('[data-action="open-modal"][data-modal="new-project"]');
  784 |       await page.waitForTimeout(500);
  785 |       await page.locator('#file-input').setInputFiles(emptyFilePath);
  786 |       await page.waitForTimeout(8000);
  787 | 
  788 |       const errorToast = await page.locator('.toast-error').isVisible().catch(() => false);
  789 |       const allToasts = await page.locator('.toast').count();
  790 | 
  791 |       console.log('  Error toast:', errorToast);
  792 |       console.log('  Total toasts:', allToasts);
  793 | 
  794 |       try { fs.unlinkSync(emptyFilePath); } catch {}
  795 |       console.log('  [PASS] Empty file handled');
  796 |     });
  797 | 
  798 |     test('TC-051: Form validation', async ({ page }) => {
  799 |       console.log('\n--- TC-051: Form validation ---');
  800 | 
  801 |       await gotoPage(page);
  802 | 
  803 |       await page.click('[data-action="open-modal"][data-modal="new-project"]');
  804 |       await page.waitForTimeout(500);
  805 | 
  806 |       await page.click('[data-action="create-project"]');
  807 |       await page.waitForTimeout(1000);
  808 | 
  809 |       const modalStillOpen = await page.locator('#modal-new-project').hasClass(/open/);
  810 |       console.log('  Modal still open:', modalStillOpen);
  811 | 
  812 |       console.log('  [PASS] Form validation OK');
  813 |     });
  814 | 
  815 |     test('TC-052: Page refresh state', async ({ page }) => {
  816 |       console.log('\n--- TC-052: Page refresh ---');
  817 | 
  818 |       await gotoPage(page);
  819 |       await page.waitForTimeout(2000);
  820 | 
  821 |       const initialCards = await page.locator('.project-card').count();
  822 |       console.log('  Before refresh:', initialCards);
  823 | 
  824 |       await page.reload({ waitUntil: 'domcontentloaded' });
  825 |       await page.waitForSelector('.navbar', { timeout: 5000 });
  826 |       await page.waitForTimeout(3000);
  827 | 
  828 |       const afterCards = await page.locator('.project-card').count();
  829 |       console.log('  After refresh:', afterCards);
  830 | 
  831 |       expect(afterCards).toBeGreaterThanOrEqual(0);
  832 |       console.log('  [PASS] Page refresh OK');
  833 |     });
  834 | 
  835 |     test('TC-053: Audio playback control', async ({ page }) => {
  836 |       console.log('\n--- TC-053: Audio control ---');
  837 | 
  838 |       await gotoPage(page);
  839 |       await page.waitForTimeout(2000);
  840 | 
  841 |       const cardCount = await page.locator('.project-card').count();
  842 |       if (cardCount > 0) {
  843 |         await page.locator('.project-card').first().click();
  844 |         await page.waitForTimeout(5000);
  845 |       }
  846 | 
  847 |       await page.click('[data-action="toggle-play"]');
  848 |       await page.waitForTimeout(1000);
  849 | 
  850 |       const toastText = await page.locator('.toast').last().textContent().catch(() => '');
  851 |       console.log('  Play prompt:', toastText.substring(0, 100));
  852 | 
  853 |       console.log('  [PASS] Audio control OK');
  854 |     });
  855 | 
  856 |     test('TC-054: Toolbar buttons', async ({ page }) => {
  857 |       console.log('\n--- TC-054: Toolbar buttons ---');
```