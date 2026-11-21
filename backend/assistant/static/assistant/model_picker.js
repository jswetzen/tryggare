// Loads the provider's models from the unsaved Base URL and API key fields, so
// an admin can pick a model before saving. The key never comes back from the server.
// Without JS the plain text input stays; this script swaps it for the select.
(function () {
  "use strict";

  function init(picker) {
    var input = picker.querySelector("input");
    var button = picker.querySelector(".llm-load-models");
    var select = picker.querySelector("select");
    var status = picker.querySelector(".llm-model-status");
    var form = picker.closest("form");
    var label = button.textContent;

    function field(name) {
      var el = form.elements[name];
      return el ? el.value : "";
    }

    function option(value, text, disabled) {
      var o = document.createElement("option");
      o.value = value;
      o.textContent = text;
      o.disabled = !!disabled;
      return o;
    }

    function fill(models) {
      var current = input.value;
      var ids = models.slice();
      // A saved choice the provider no longer lists must not vanish silently.
      if (current && ids.indexOf(current) === -1) {
        ids.unshift(current);
      }
      select.textContent = "";
      if (!ids.length) {
        var ph = option("", select.dataset.placeholder, true);
        ph.selected = true;
        select.appendChild(ph);
        return;
      }
      ids.forEach(function (id) {
        select.appendChild(option(id, id));
      });
      select.value = current || ids[0];
      if (!current) {
        input.value = select.value;
      }
    }

    function load() {
      var body = new FormData();
      body.append("csrfmiddlewaretoken", field("csrfmiddlewaretoken"));
      body.append("base_url", field("base_url"));
      body.append("api_key", field("api_key"));
      button.disabled = true;
      button.textContent = button.dataset.loadingLabel;
      status.textContent = "";
      fetch(input.dataset.modelsUrl, {
        method: "POST",
        body: body,
        credentials: "same-origin",
      })
        .then(function (response) {
          return response.json().catch(function () {
            return {};
          });
        })
        .then(function (data) {
          if (data.models) {
            picker.classList.remove("is-manual");
            fill(data.models);
            status.textContent = data.models.length
              ? status.dataset.foundTemplate.replace("%(count)s", data.models.length)
              : status.dataset.empty;
          } else {
            // Only a provider that cannot list needs the free-text field.
            picker.classList.toggle("is-manual", data.code === "models_not_supported");
            status.textContent = data.error || status.dataset.failed;
          }
        })
        .catch(function () {
          status.textContent = status.dataset.failed;
        })
        .finally(function () {
          button.disabled = false;
          button.textContent = label;
        });
    }

    fill([]);
    picker.classList.add("is-enhanced");
    select.addEventListener("change", function () {
      input.value = select.value;
    });
    button.addEventListener("click", load);
    if (field("base_url").trim()) {
      load();
    }
  }

  document.addEventListener("DOMContentLoaded", function () {
    document.querySelectorAll(".llm-model-picker").forEach(init);
  });
})();
