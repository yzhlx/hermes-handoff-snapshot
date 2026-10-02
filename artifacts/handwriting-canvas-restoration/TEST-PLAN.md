# Test plan and capability mapping

Formal stable discovery command:

```powershell
& $py -m unittest discover -s tests -p 'test_*.py' -v
```

This discovers `tests/test_ui_2_handwriting_entry.py` without a `tmp` path. It opens the formal root, not `learning-os-ui-prototype.html`, clicks the real entry, checks static JS HTTP headers, sends Pointer pen events, verifies default color and line width, exercises eraser/undo/redo/clear, checks re-entry listener behavior, reloads, and asserts draft restoration and no page errors.

Complementary recovered tests remain in `work/presentations/learning-os-ui/tmp/` and cover core, storage, API, static host, launcher units, Canvas model, prototype Canvas, responsive behavior, and the existing UI 2.0 product areas. The moved formal entry test has no duplicate Python source under `tmp`.

Critical formal entry regression was executed three consecutive times to check flakiness.
