/**
 * Adds an ability for highlight rows by clicking.
 */
function init_highlights() {
  var assignees = document.querySelectorAll(".assignees > tbody > tr");
  var epics = document.querySelectorAll(".epics > tbody > tr");
  var stories = document.querySelectorAll(".stories > tbody > tr");

  function deselect(doc, className) {
    doc.querySelectorAll(`tr.${className}`).forEach((el) => {
      el.classList.remove(className);
    })
  }

  for (var i in assignees) {
    var assignee = assignees[i];

    if (
        assignee !== undefined
        && assignee.attributes !== undefined
        && assignee.attributes['data-assignee-id'] !== undefined
    ) {
      var assigneeId = assignee.attributes['data-assignee-id'];

      var listenerSelector = (
        `table.assignees [${assigneeId.name}="${assigneeId.value}"]`
      );

      document.querySelector(listenerSelector).onclick = function () {
        var attr = this.attributes['data-assignee-id'];
        var selector = (
          `table.component [${attr.name}="${attr.value}"]`
        );

        deselect(document, "highlighted-epic");
        deselect(document, "highlighted-story");

        this.classList.toggle("highlighted");

        document.querySelectorAll(selector).forEach((el) => {
          el.classList.toggle("highlighted");
        })
      }
    }
  }

  for (var i in epics) {
    var epic = epics[i];

    if (
        epic !== undefined
        && epic.attributes !== undefined
        && epic.attributes['data-epic-id'] !== undefined
    ) {
      var epicId = epic.attributes['data-epic-id'];

      var listenerSelector = (
        `table.epics [${epicId.name}="${epicId.value}"]`
      );

      document.querySelector(listenerSelector).onclick = function () {
        var attr = this.attributes['data-epic-id'];
        var selector = (
          `table.component [data-parent-id="${attr.value}"]`
        );

        deselect(document, "highlighted");
        deselect(document, "highlighted-story");

        this.classList.toggle("highlighted-epic");

        document.querySelectorAll(selector).forEach((el) => {
          el.classList.toggle("highlighted-epic");
        })
      }
    }
  }

  for (var i in stories) {
    var story = stories[i];

    if (
        story !== undefined
        && story.attributes !== undefined
        && story.attributes['data-story-id'] !== undefined
    ) {
      var storyId = story.attributes['data-story-id'];

      var listenerSelector = (
        `table.stories [${storyId.name}="${storyId.value}"]`
      );

      document.querySelector(listenerSelector).onclick = function () {
        var attr = this.attributes['data-story-id'];
        var selector = (
          `table.component [data-parent-id="${attr.value}"]`
        );

        deselect(document, "highlighted");
        deselect(document, "highlighted-epic");

        this.classList.toggle("highlighted-story");

        document.querySelectorAll(selector).forEach((el) => {
          el.classList.toggle("highlighted-story");
        })
      }
    }
  }
}

/**
 * Saves settings into local storage.
 */
function saveSettings(tableName, settingsJson) {
  localStorage.setItem(tableName, JSON.stringify(settingsJson));
}

/**
 * Returns settings json if exists else returns an empty object.
 */
function getSettings(tableName) {
  const data = localStorage.getItem(tableName);

  if (!data) {
    return JSON.constructor();
  }

  return JSON.parse(data);
}

/**
 * Adds an ability to control visibility of component issue rows
 * by clicking on version columns.
 */
function init_version_columns() {
  var versions = document.querySelectorAll(".issues th.version");
  var settings = getSettings("components");
  const collapsedClassName = "collapsed";

  for (var i in versions) {
    var version = versions[i];

    if (
        version !== undefined
        && version.attributes !== undefined
        && version.attributes['data-version-id'] !== undefined
    ) {
      var versionId = version.attributes['data-version-id'];
      var componentId = version.attributes['data-component-id'];

      var listenerSelector = (
        `table.component [${versionId.name}="${versionId.value}"]`
        +`[${componentId.name}="${componentId.value}"] > span.collapse`
      );

      document.querySelector(listenerSelector).onclick = function () {
        var versionAttr = this.parentNode.attributes['data-version-id'];
        var componentAttr = this.parentNode.attributes['data-component-id'];
        
        var selector = (
          `table.component [data-version-ids="${versionAttr.value}"]`
          +`[data-component-id="${componentAttr.value}"]`
        );

        this.classList.toggle("up");
        this.parentNode.classList.toggle(collapsedClassName);

        var isVersionCollapsed = this.parentNode.classList.contains(
          collapsedClassName
        )

        if (!settings[componentAttr.value]) {
          settings[componentAttr.value] = JSON.constructor();
        }

        settings[componentAttr.value][versionAttr.value] = isVersionCollapsed;
        saveSettings("components", settings)

        document.querySelectorAll(selector).forEach((el) => {
          el.classList.toggle(collapsedClassName);
        })
      }
    }
  }
}

/**
 * Collapses version column and hides related rows.
 */
function setVersionCollapsed(componentId, versionId, collapsed = true) {
  var versionColumnsSelector = (
    `.issues th.version[data-component-id="${componentId}"]`
    + `[data-version-id="${versionId}"]`
  )
  var versionRowsSelector = (
    `table.component [data-component-id="${componentId}"]`
    + `[data-version-ids="${versionId}"]`
  );

  document.querySelectorAll(versionColumnsSelector).forEach((column) => {
    if (collapsed) {  
      column.classList.add("collapsed");
      column.querySelector("span.collapse").classList.add("up");
    } else {
      column.classList.remove("collapsed");
      column.querySelector("span.collapse").classList.remove("up");
    }
  });

  document.querySelectorAll(versionRowsSelector).forEach((row) => {
    if (collapsed) {  
      row.classList.add("collapsed");
    } else {
      row.classList.remove("collapsed");
    }
  });
}

/**
 * Hides version column and hides related rows.
 */
function setVersionHidden(versionId, hidden = true) {
  var versionColumnsSelector = (
    `.issues [data-version-id="${versionId}"]`
  )
  var versionRowsSelector = (
    `table.component [data-version-ids="${versionId}"]`
  );

  document.querySelectorAll(versionColumnsSelector).forEach((column) => {
    if (hidden) {  
      column.classList.add("hidden");
    } else {
      column.classList.remove("hidden");
    }
  });

  document.querySelectorAll(versionRowsSelector).forEach((row) => {
    if (hidden) {  
      row.classList.add("hidden");
    } else {
      row.classList.remove("hidden");
    }
  });
}

/**
 * Applyes stored settings for "components" table.
 */
function applyComponentTableSettings() {
  const componentSettings = getSettings("components");
  const versionSettings = getSettings("versions");

  for (var componentId in componentSettings) {
    for (var versionId in componentSettings[componentId]) {
      setVersionCollapsed(
        componentId,
        versionId,
        componentSettings[componentId][versionId],
      );
    }
  }

  for (var versionId in versionSettings) {
    setVersionHidden(
      versionId,
      !versionSettings[versionId],
    );
  }
}

/**
 * Initializes checkboxes in Versions table.
 */
function init_version_selector() {
  var checkboxes = document.querySelectorAll(
    "table.versions input[type=checkbox]"
  )
  let settings = getSettings("versions");

  checkboxes.forEach(function(checkbox) {
    var attr = checkbox.attributes["data-version-id"];
    var isChecked = true;

    // set initial state -- displayed
    if (settings[attr.value] != undefined) {
      isChecked = settings[attr.value];
    }

    checkbox.checked = isChecked;

    checkbox.addEventListener("change", function() {
      settings[attr.value] = this.checked;
      saveSettings("versions", settings);
      setVersionHidden(attr.value, !this.checked);
    });
  });
}

/**
 * Initializes all action parts.
 */
function init_reports() {
  init_highlights();
  init_version_selector();
  init_version_columns();

  applyComponentTableSettings();
}

document.addEventListener("DOMContentLoaded", init_reports)

export { init_reports };
