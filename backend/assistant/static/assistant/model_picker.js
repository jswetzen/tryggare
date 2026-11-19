// Loads the provider's models from the unsaved Base URL and API key fields, so
// an admin can pick a model before saving. The key never comes back from the server.
(function () {
  "use strict";

  function init(picker) {
    var input = picker.querySelector("input");
    var button = picker.querySelector(".llm-load-models");
    var choice = picker.querySelector(".llm-model-choice");
    var select = choice.querySelector("select");
    var status = picker.querySelector(".llm-model-status");
    var form = picker.closest("form");
    var label = button.textContent;

    function field(name) {
      var el = form.elements[name];
      return el ? el.value : "";
    }

    function show(models) {
      select.textContent = "";
      models.forEach(function (id) {
        var option = document.createElement("option");
        option.value = id;
        option.textContent = id;
        option.selected = id === input.value;
        select.appendChild(option);
      });
      choice.hidden = models.length === 0;
      status.textContent = models.length
        ? status.dataset.foundTemplate.replace("%(count)s", models.length)
        : status.dataset.empty;
      if (models.length && !input.value) {
        input.value = select.value;
      }
    }

    select.addEventListener("change", function () {
      input.value = select.value;
    });

    button.addEventListener("click", function () {
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
            show(data.models);
          } else {
            choice.hidden = true;
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
    });
  }

  document.addEventListener("DOMContentLoaded", function () {
    document.querySelectorAll(".llm-model-picker").forEach(init);
  });
})();
