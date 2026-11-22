import client


class _FakeResponse:
    text = "<html><body>label</body></html>"

    def raise_for_status(self):
        pass


class _FakePage:
    def get_pixmap(self, matrix=None, alpha=None):
        self.matrix = matrix
        self.alpha = alpha
        return self

    def tobytes(self, fmt):
        self.fmt = fmt
        return b"fake-png-bytes"


class _FakeDoc(list):
    pass


def _install_common_mocks(monkeypatch, captured):
    monkeypatch.setattr(client.requests, "get", lambda url, timeout=None: (
        captured.setdefault("url", url), _FakeResponse()
    )[1])

    def fake_html(string, base_url):
        captured["html_string"] = string
        captured["base_url"] = base_url

        class _FakeHTML:
            def write_pdf(self):
                return b"fake-pdf-bytes"

        return _FakeHTML()

    monkeypatch.setattr(client, "HTML", fake_html)

    page = _FakePage()
    doc = _FakeDoc([page])

    def fake_fitz_open(stream=None, filetype=None):
        captured["pdf_stream"] = stream
        captured["filetype"] = filetype
        return doc

    monkeypatch.setattr(client.fitz, "open", fake_fitz_open)
    return page


def test_render_label_appends_label_query_param_no_existing_query(monkeypatch):
    captured = {}
    _install_common_mocks(monkeypatch, captured)
    monkeypatch.setattr(client, "LABEL_SIZE", "29x90")

    client.render_label("http://backend/label/1")

    assert captured["url"] == "http://backend/label/1?label=29x90"


def test_render_label_appends_label_query_param_existing_query(monkeypatch):
    captured = {}
    _install_common_mocks(monkeypatch, captured)
    monkeypatch.setattr(client, "LABEL_SIZE", "29x90")

    client.render_label("http://backend/label/1?job=abc")

    assert captured["url"] == "http://backend/label/1?job=abc&label=29x90"


def test_render_label_passes_html_to_weasyprint(monkeypatch):
    captured = {}
    _install_common_mocks(monkeypatch, captured)
    monkeypatch.setattr(client, "LABEL_SIZE", "29x90")

    client.render_label("http://backend/label/1")

    assert captured["html_string"] == "<html><body>label</body></html>"
    assert captured["base_url"] == "http://backend/label/1?label=29x90"


def test_render_label_opens_pdf_with_fitz(monkeypatch):
    captured = {}
    _install_common_mocks(monkeypatch, captured)
    monkeypatch.setattr(client, "LABEL_SIZE", "29x90")

    client.render_label("http://backend/label/1")

    assert captured["pdf_stream"] == b"fake-pdf-bytes"
    assert captured["filetype"] == "pdf"


def test_render_label_renders_at_dpi_scale(monkeypatch):
    captured = {}
    page = _install_common_mocks(monkeypatch, captured)
    monkeypatch.setattr(client, "LABEL_SIZE", "29x90")
    monkeypatch.setattr(client, "SCREENSHOT_DPI", 300)

    client.render_label("http://backend/label/1")

    import fitz

    expected = fitz.Matrix(300 / 72, 300 / 72)
    assert (page.matrix.a, page.matrix.d) == (expected.a, expected.d)


def test_render_label_returns_png_bytes(monkeypatch):
    captured = {}
    _install_common_mocks(monkeypatch, captured)
    monkeypatch.setattr(client, "LABEL_SIZE", "29x90")

    result = client.render_label("http://backend/label/1")

    assert result == b"fake-png-bytes"
