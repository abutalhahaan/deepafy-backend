(function () {
  "use strict";

  function setBackgroundPriority(value) {
    const priorityField = document.getElementById(
      "id_background_visual_priority"
    );

    if (!priorityField) {
      return;
    }

    priorityField.value = value;
  }

  function bindBackgroundPriority() {
    const colorField = document.getElementById(
      "id_background_color"
    );

    const imageField = document.getElementById(
      "id_background_image"
    );

    if (colorField) {
      colorField.addEventListener("input", function () {
        setBackgroundPriority("color");
      });

      colorField.addEventListener("change", function () {
        setBackgroundPriority("color");
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

  function init() {
    bindBackgroundPriority();
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
