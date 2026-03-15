# Print page sizing problems

## The problem

The label print page rendered by the web app is the wrong size. Playwright screenshots it
and passes the PNG to brother_ql, which expects exactly **306 × 991 px (portrait)** for the
29×90mm die-cut label at 300 DPI.

The page is currently rendering in landscape orientation and at the wrong dimensions, so
`client.py` has to forcibly rotate and resize the image before printing. This is a lossy
hack — it stretches or squashes whatever the page renders.

## The right fix: size the `.label` element correctly in CSS

The `.label` div is what Playwright screenshots. It should be sized to match the physical
label dimensions in CSS pixels, taking `device_scale_factor` into account.

`client.py` uses `device_scale_factor = SCREENSHOT_DPI / 96` (default: `300 / 96 ≈ 3.125`).
At that scale factor, a CSS pixel equals `3.125` device pixels. So to get a 306 × 991 device
pixel screenshot, the `.label` element should be:

```
CSS width  = 306  / 3.125 = 97.9 px  → use 98px
CSS height = 991  / 3.125 = 317.1 px → use 317px
```

In your stylesheet:

```css
.label {
  width: 98px;
  height: 317px;
  overflow: hidden;
  /* remove any margin/padding that would affect the screenshot size */
  margin: 0;
  padding: 0;
}
```

## Alternative: use a fixed viewport size

If you'd rather work in round numbers, set the Playwright viewport to match the label and
set `device_scale_factor=1`, then size `.label` directly in device pixels:

```python
# client.py — in render_label()
page = await browser.new_page(viewport={"width": 306, "height": 991}, device_scale_factor=1)
```

```css
.label {
  width: 306px;
  height: 991px;
}
```

## Orientation

The label is **portrait** (narrow side = 29mm = 306 px, long side = 90mm = 991 px).
Make sure the page/element is portrait, not landscape. If the page is designed landscape
(e.g. `width: 317px; height: 98px`) that's the root cause of the wrong dimensions.

## Verify

Once the page is sized correctly, the workaround in `client.py` (`image.rotate(90,
expand=True).resize((306, 991), ...)`) can be removed and replaced with just:

```python
image = Image.open(io.BytesIO(png_bytes))
# no resize needed if page is sized correctly
```
