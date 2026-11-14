(function () {
  "use strict";

  function setBackgroundPriority(value) {
    const field = document.getElementById("id_background_visual_priority");
    if (field) field.value = value;
  }

  function bindBackgroundPriority() {
    const colorField = document.getElementById("id_background_color");
    const imageField = document.getElementById("id_background_image");

    if (colorField) {
      ["input", "change"].forEach(function (eventName) {
        colorField.addEventListener(eventName, function () {
          setBackgroundPriority("color");
        });
      });
    }

    if (imageField) {
      imageField.addEventListener("change", function () {
        if (imageField.files && imageField.files.length > 0) {
          setBackgroundPriority("image");
        }
      });
    }
  }

  function initShadowBuilder() {
    const field = document.getElementById("id_box_shadows");
    const radiusField = document.getElementById("id_box_shadow_radius");
    if (!field || !radiusField || field.dataset.shadowBuilderReady === "1") return;

    const radiusFormRow = radiusField.closest(".form-row");
    if (radiusFormRow) {
      radiusFormRow.classList.add("multi-shadow-radius-json-field");
    }

    field.dataset.shadowBuilderReady = "1";

    let shadows = [];
    try {
      const parsed = JSON.parse(field.value || "[]");
      if (Array.isArray(parsed)) shadows = parsed.slice(0, 5);
    } catch (_) {
      shadows = [];
    }

    const defaults = {
      color: "#000000",
      opacity: 20,
      x: 0,
      y: 10,
      blur: 30,
      spread: 0,
      inset: false
    };

    shadows = shadows.map(function (item) {
      return Object.assign({}, defaults, item);
    });

    const wrapper = document.createElement("div");
    wrapper.className = "multi-shadow-builder";

    const heading = document.createElement("div");
    heading.className = "multi-shadow-heading";
    heading.textContent = "Multi Shadow Builder";

    const description = document.createElement("p");
    description.className = "multi-shadow-description";
    description.textContent =
      "Add up to 5 shadows. All enabled shadows are applied together.";

    const radiusControl = document.createElement("div");
    radiusControl.className = "multi-shadow-global-radius";
    const radiusLabel = document.createElement("label");
    radiusLabel.className = "multi-shadow-control";
    const radiusCaption = document.createElement("span");
    radiusCaption.textContent = "Global Shadow Radius";
    const radiusInput = document.createElement("input");
    radiusInput.type = "range";
    radiusInput.min = "0";
    radiusInput.max = "100";
    radiusInput.step = "1";
    radiusInput.value = String(Math.max(0, Math.min(100, Number(radiusField.value) || 0)));
    const radiusValue = document.createElement("strong");
    radiusValue.className = "multi-shadow-radius-value";
    radiusValue.textContent = radiusInput.value + "px";
    radiusLabel.append(radiusCaption, radiusInput, radiusValue);
    radiusControl.appendChild(radiusLabel);
    const list = document.createElement("div");
    list.className = "multi-shadow-list";

    const addButton = document.createElement("button");
    addButton.type = "button";
    addButton.className = "button multi-shadow-add";
    addButton.textContent = "+ Add Shadow";

    const previewLabel = document.createElement("div");
    previewLabel.className = "multi-shadow-preview-label";
    previewLabel.textContent = "Live Preview";

    const preview = document.createElement("div");
    preview.className = "multi-shadow-preview-stage";

    const previewBox = document.createElement("div");
    previewBox.className = "multi-shadow-preview-box";
    previewBox.textContent = "Popup Preview";
    preview.appendChild(previewBox);

    const help = document.createElement("p");
    help.className = "multi-shadow-help";
    help.textContent = "Changes are saved with the Central Popup settings.";

    wrapper.append(
      heading,
      description,
      radiusControl,
      list,
      addButton,
      previewLabel,
      preview,
      help
    );

    field.insertAdjacentElement("afterend", wrapper);
    field.classList.add("multi-shadow-json-field");

    function makeControl(labelText, input, className) {
      const label = document.createElement("label");
      label.className = "multi-shadow-control " + (className || "");
      const caption = document.createElement("span");
      caption.textContent = labelText;
      label.append(caption, input);
      return label;
    }

    function makeInput(type, value, min, max, step) {
      const input = document.createElement("input");
      input.type = type;
      input.value = value;
      if (min !== undefined) input.min = min;
      if (max !== undefined) input.max = max;
      if (step !== undefined) input.step = step;
      return input;
    }

    function updateStoredValue() {
      field.value = JSON.stringify(shadows);
      field.dispatchEvent(new Event("change", { bubbles: true }));
    }

    function updatePreview() {
      const cssShadows = shadows.map(function (shadow) {
        const color = String(shadow.color || "#000000");
        const opacity = Math.max(0, Math.min(100, Number(shadow.opacity) || 0)) / 100;
        const hex = color.replace("#", "");
        const validHex = /^[0-9a-fA-F]{6}$/.test(hex) ? hex : "000000";
        const red = parseInt(validHex.slice(0, 2), 16);
        const green = parseInt(validHex.slice(2, 4), 16);
        const blue = parseInt(validHex.slice(4, 6), 16);

        return [
          shadow.inset ? "inset" : "",
          (Number(shadow.x) || 0) + "px",
          (Number(shadow.y) || 0) + "px",
          Math.max(0, Number(shadow.blur) || 0) + "px",
          (Number(shadow.spread) || 0) + "px",
          "rgba(" + red + ", " + green + ", " + blue + ", " + opacity + ")"
        ].filter(Boolean).join(" ");
      });

      previewBox.style.boxShadow = cssShadows.length
        ? cssShadows.join(", ")
        : "0 8px 24px rgba(0,0,0,.12)";
    }

    function render() {
      list.replaceChildren();

      shadows.forEach(function (shadow, index) {
        const card = document.createElement("div");
        card.className = "multi-shadow-card";

        const top = document.createElement("div");
        top.className = "multi-shadow-card-top";

        const title = document.createElement("strong");
        title.textContent = "Shadow " + (index + 1);

        const remove = document.createElement("button");
        remove.type = "button";
        remove.className = "button multi-shadow-remove";
        remove.textContent = "Remove";
        remove.addEventListener("click", function () {
          shadows.splice(index, 1);
          updateStoredValue();
          render();
        });

        top.append(title, remove);

        const grid = document.createElement("div");
        grid.className = "multi-shadow-grid";

        const color = makeInput("color", shadow.color);
        color.addEventListener("input", function () {
          shadow.color = color.value;
          updateStoredValue();
          updatePreview();
        });

        const opacity = makeInput("number", shadow.opacity, 0, 100, 1);
        opacity.addEventListener("input", function () {
          shadow.opacity = Number(opacity.value);
          updateStoredValue();
          updatePreview();
        });

        const x = makeInput("number", shadow.x, -500, 500, 1);
        x.addEventListener("input", function () {
          shadow.x = Number(x.value);
          updateStoredValue();
          updatePreview();
        });

        const y = makeInput("number", shadow.y, -500, 500, 1);
        y.addEventListener("input", function () {
          shadow.y = Number(y.value);
          updateStoredValue();
          updatePreview();
        });

        const blur = makeInput("number", shadow.blur, 0, 500, 1);
        blur.addEventListener("input", function () {
          shadow.blur = Number(blur.value);
          updateStoredValue();
          updatePreview();
        });

        const spread = makeInput("number", shadow.spread, -500, 500, 1);
        spread.addEventListener("input", function () {
          shadow.spread = Number(spread.value);
          updateStoredValue();
          updatePreview();
        });

        const inset = document.createElement("input");
        inset.type = "checkbox";
        inset.checked = Boolean(shadow.inset);
        inset.addEventListener("change", function () {
          shadow.inset = inset.checked;
          updateStoredValue();
          updatePreview();
        });

        grid.append(
          makeControl("Color", color),
          makeControl("Opacity (%)", opacity),
          makeControl("X Offset (px)", x),
          makeControl("Y Offset (px)", y),
          makeControl("Blur (px)", blur),
          makeControl("Spread (px)", spread),
          makeControl("Inner Shadow", inset, "multi-shadow-inset")
        );

        card.append(top, grid);
        list.appendChild(card);
      });

      addButton.disabled = shadows.length >= 5;
      addButton.textContent = shadows.length >= 5
        ? "Maximum 5 Shadows"
        : "+ Add Shadow";

      updateStoredValue();
      updatePreview();
    }

    radiusInput.addEventListener("input", function () {
      const value = Math.max(0, Math.min(100, Number(radiusInput.value) || 0));
      radiusField.value = String(value);
      radiusValue.textContent = value + "px";
      radiusField.dispatchEvent(new Event("change", { bubbles: true }));
      updatePreview();
    });

    addButton.addEventListener("click", function () {
      if (shadows.length >= 5) return;
      shadows.push(Object.assign({}, defaults));
      render();
    });

    render();
  }

  function init() {
    bindBackgroundPriority();
    initShadowBuilder();
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
