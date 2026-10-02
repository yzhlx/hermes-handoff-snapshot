# Root cause

The complete handwriting Canvas still existed in `outputs/learning-os-ui-prototype.html`. The formal UI 2.0 root did not mount Canvas DOM, include `learning-os-canvas-model.js`, include a controller, or present a Canvas entry.

The old handwriting, responsive-handwriting, and world-canvas browser regressions targeted the prototype URL. Therefore those legacy tests could be green while the formal product page had no Canvas. This was an entry/UI integration omission, not evidence that the Canvas implementation had been deleted.

The prior restoration stage recorded a genuine formal-root RED result before the product changes. The current fixed state was not deliberately broken again and no artificial "red test" commit was created.
